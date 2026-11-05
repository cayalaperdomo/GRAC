@app.route('/dofa/new', methods=['GET', 'POST'])
@login_required
def dofa_new():
    user = User.query.get(session.get('user_id'))

    if user.role not in ('admin', 'auditor') and not verificar_permiso(user, "DOFA"):
        flash("No tiene permiso para acceder al módulo DOFA.", "danger")
        return redirect(url_for('menu'))

    if user.role == 'auditor':
        flash("Perfil auditor: solo lectura.", "warning")
        return redirect(url_for('dofa_list'))

    if request.method == 'POST':
        titulo = (request.form.get('titulo') or "DOFA").strip()
        fecha_str = (request.form.get('fecha') or "").strip()

        try:
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date() if fecha_str else date.today()
        except Exception:
            fecha = date.today()

        dofa = DofaAnalisis(
            titulo=titulo,
            fecha=fecha,
            fortalezas=request.form.get('fortalezas') or "",
            debilidades=request.form.get('debilidades') or "",
            oportunidades=request.form.get('oportunidades') or "",
            amenazas=request.form.get('amenazas') or "",
            estrategias_fo=request.form.get('estrategias_fo') or "",
            estrategias_fa=request.form.get('estrategias_fa') or "",
            estrategias_do=request.form.get('estrategias_do') or "",
            estrategias_da=request.form.get('estrategias_da') or "",
            creado_por=user.username
        )
        db.session.add(dofa)
        db.session.commit()
        flash("DOFA guardado correctamente.", "success")
        return redirect(url_for('dofa_list'))

    f, d, o, a = _autollenar_dofa_desde_contexto()

    content = render_template_string("""
    <div class="dofa-shell">

      <div class="dofa-header-card">
        <div class="dofa-header-overlay">
          <div class="dofa-header-text">
            <h3 class="dofa-title m-0">Nuevo DOFA</h3>
            <div class="dofa-subtitle">
              Matriz 2x2 con fortalezas, oportunidades, debilidades, amenazas y estrategias FO / FA / DO / DA
            </div>
          </div>
        </div>
      </div>

      <div class="dofa-header-actions">
        <a href="{{ url_for('dofa_list') }}"
           class="btn rounded-pill px-5 fw-bold dofa-back-btn">
          ⬅ Volver al Listado DOFA
        </a>

      </div>

      <form method="POST" class="dofa-card">
        <div class="dofa-card-body">

          <div class="row g-3">
            <div class="col-md-8">
              <label class="form-label fw-semibold">Título</label>
              <input type="text" name="titulo" class="form-control" value="DOFA">
            </div>
            <div class="col-md-4">
              <label class="form-label fw-semibold">Fecha</label>
              <input type="date" name="fecha" class="form-control" value="{{ today }}">
            </div>
          </div>

          <hr class="my-4">

          <div class="row g-3">
            <div class="col-md-6">
              <div class="quad quad-f">
                <div class="quad-h">✅ Fortalezas</div>
                <textarea name="fortalezas" class="form-control quad-ta" rows="7" placeholder="- ...">{{ f }}</textarea>
              </div>
            </div>

            <div class="col-md-6">
              <div class="quad quad-o">
                <div class="quad-h">🌟 Oportunidades</div>
                <textarea name="oportunidades" class="form-control quad-ta" rows="7" placeholder="- ...">{{ o }}</textarea>
              </div>
            </div>

            <div class="col-md-6">
              <div class="quad quad-d">
                <div class="quad-h">⚠️ Debilidades</div>
                <textarea name="debilidades" class="form-control quad-ta" rows="7" placeholder="- ...">{{ d }}</textarea>
              </div>
            </div>

            <div class="col-md-6">
              <div class="quad quad-a">
                <div class="quad-h">🛡️ Amenazas</div>
                <textarea name="amenazas" class="form-control quad-ta" rows="7" placeholder="- ...">{{ a }}</textarea>
              </div>
            </div>
          </div>

          <hr class="my-4">


          <div class="dofa-ai-panel">
            <div class="dofa-ai-copy">
              <div class="dofa-ai-title">✨ Generación de estrategias con IA</div>
              <div class="dofa-ai-help">
                La IA utiliza el contenido actual de Fortalezas, Oportunidades, Debilidades y Amenazas.
                El resultado se coloca en campos editables: puede ajustarlo, reemplazarlo o ingresar
                las estrategias manualmente.
              </div>
            </div>
            <button type="button"
                    class="btn dofa-ai-btn"
                    data-no-progress="true"
                    onclick="generarEstrategiasDofaIA(this, 'cE')">
              <span class="dofa-ai-btn-label">🧠 Generar FO / FA / DO / DA con IA</span>
            </button>
          </div>
          <div class="dofa-ai-status" role="status" aria-live="polite"></div>

          <div class="accordion dofa-accordion" id="accEstrategias">
            <div class="accordion-item">
              <h2 class="accordion-header" id="hE">
                <button class="accordion-button collapsed fw-semibold" type="button"
                        data-bs-toggle="collapse" data-bs-target="#cE" aria-expanded="false" aria-controls="cE">
                  🧠 Estrategias FO / FA / DO / DA (opcional)
                </button>
              </h2>
              <div id="cE" class="accordion-collapse collapse" aria-labelledby="hE" data-bs-parent="#accEstrategias">
                <div class="accordion-body">

                  <div class="row g-3">
                    <div class="col-md-6">
                      <label class="form-label fw-semibold">FO (Fortalezas + Oportunidades)</label>
                      <textarea name="estrategias_fo" class="form-control" rows="4"></textarea>
                    </div>
                    <div class="col-md-6">
                      <label class="form-label fw-semibold">FA (Fortalezas + Amenazas)</label>
                      <textarea name="estrategias_fa" class="form-control" rows="4"></textarea>
                    </div>
                    <div class="col-md-6">
                      <label class="form-label fw-semibold">DO (Debilidades + Oportunidades)</label>
                      <textarea name="estrategias_do" class="form-control" rows="4"></textarea>
                    </div>
                    <div class="col-md-6">
                      <label class="form-label fw-semibold">DA (Debilidades + Amenazas)</label>
                      <textarea name="estrategias_da" class="form-control" rows="4"></textarea>
                    </div>
                  </div>

                </div>
              </div>
            </div>
          </div>

          <div class="dofa-bottom-actions">
            <button class="btn btn-success rounded-pill px-4 fw-bold">
              💾 Guardar DOFA
            </button>
            <a href="{{ url_for('dofa_list') }}"
               class="btn rounded-pill px-4 fw-bold dofa-cancel-btn">
              Cancelar
            </a>
          </div>

        </div>
      </form>

    </div>


    <script>
    (function () {
      if (window.__GRAC_DOFA_AI_READY__) return;
      window.__GRAC_DOFA_AI_READY__ = true;

      function showStrategySection(collapseId) {
        const collapseElement = document.getElementById(collapseId);
        if (!collapseElement) return;

        try {
          if (window.bootstrap && window.bootstrap.Collapse) {
            window.bootstrap.Collapse
              .getOrCreateInstance(collapseElement, {toggle: false})
              .show();
          } else {
            collapseElement.classList.add('show');
          }
        } catch (_error) {
          collapseElement.classList.add('show');
        }

        const toggle = document.querySelector('[data-bs-target="#' + collapseId + '"]');
        if (toggle) {
          toggle.classList.remove('collapsed');
          toggle.setAttribute('aria-expanded', 'true');
        }
      }

      function setDofaAiStatus(statusElement, message, kind) {
        if (!statusElement) return;
        statusElement.textContent = message || '';
        statusElement.className = 'dofa-ai-status is-visible ' + (kind || 'is-info');
      }

      window.generarEstrategiasDofaIA = async function (button, collapseId) {
        const form = button ? button.closest('form') : null;
        const panel = button ? button.closest('.dofa-ai-panel') : null;
        const statusElement = panel && panel.nextElementSibling &&
          panel.nextElementSibling.classList.contains('dofa-ai-status')
            ? panel.nextElementSibling
            : null;

        if (!form) {
          setDofaAiStatus(statusElement, 'No se encontró el formulario de la matriz DOFA.', 'is-error');
          return;
        }

        const names = [
          'fortalezas',
          'oportunidades',
          'debilidades',
          'amenazas',
          'estrategias_fo',
          'estrategias_fa',
          'estrategias_do',
          'estrategias_da'
        ];

        const fields = {};
        names.forEach(function (name) {
          fields[name] = form.querySelector('[name="' + name + '"]');
        });

        const sourceLabels = {
          fortalezas: 'Fortalezas',
          oportunidades: 'Oportunidades',
          debilidades: 'Debilidades',
          amenazas: 'Amenazas'
        };

        const missing = Object.keys(sourceLabels).filter(function (name) {
          return !fields[name] || !String(fields[name].value || '').trim();
        });

        if (missing.length) {
          setDofaAiStatus(
            statusElement,
            'Complete los cuatro cuadrantes. Falta información en: ' +
              missing.map(function (name) { return sourceLabels[name]; }).join(', ') + '.',
            'is-error'
          );
          return;
        }

        const strategyNames = [
          'estrategias_fo',
          'estrategias_fa',
          'estrategias_do',
          'estrategias_da'
        ];
        const hasExistingStrategies = strategyNames.some(function (name) {
          return fields[name] && String(fields[name].value || '').trim();
        });

        if (
          hasExistingStrategies &&
          !window.confirm(
            'Ya existen estrategias registradas. La generación con IA reemplazará temporalmente ' +
            'el contenido actual de FO, FA, DO y DA. Podrá editarlo antes de guardar. ¿Desea continuar?'
          )
        ) {
          return;
        }

        const originalHtml = button.innerHTML;
        button.disabled = true;
        button.innerHTML =
          '<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>Generando...';
        setDofaAiStatus(
          statusElement,
          'Analizando la matriz y construyendo estrategias FO, FA, DO y DA...',
          'is-info'
        );

        const payload = {
          fortalezas: fields.fortalezas.value,
          oportunidades: fields.oportunidades.value,
          debilidades: fields.debilidades.value,
          amenazas: fields.amenazas.value
        };

        try {
          const response = await fetch("{{ url_for('dofa_generar_estrategias_ia') }}", {
            method: 'POST',
            credentials: 'same-origin',
            cache: 'no-store',
            headers: {
              'Content-Type': 'application/json',
              'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify(payload)
          });

          let data = {};
          try {
            data = await response.json();
          } catch (_jsonError) {
            data = {};
          }

          if (!response.ok || !data.ok) {
            throw new Error(
              data.message || 'No fue posible generar las estrategias con IA.'
            );
          }

          const strategies = data.estrategias || {};
          const labels = {
            estrategias_fo: 'FO',
            estrategias_fa: 'FA',
            estrategias_do: 'DO',
            estrategias_da: 'DA'
          };

          strategyNames.forEach(function (name) {
            if (!fields[name] || !String(strategies[name] || '').trim()) {
              throw new Error('La IA no devolvió una estrategia válida para ' + labels[name] + '.');
            }
          });

          strategyNames.forEach(function (name) {
            fields[name].value = strategies[name];
            fields[name].dispatchEvent(new Event('input', {bubbles: true}));
          });

          showStrategySection(collapseId);
          setDofaAiStatus(
            statusElement,
            data.message ||
              'Estrategias generadas. Puede editarlas antes de guardar la matriz DOFA.',
            'is-success'
          );

          if (fields.estrategias_fo) {
            setTimeout(function () {
              fields.estrategias_fo.focus();
              fields.estrategias_fo.scrollIntoView({behavior: 'smooth', block: 'center'});
            }, 250);
          }
        } catch (error) {
          setDofaAiStatus(
            statusElement,
            error && error.message
              ? error.message
              : 'No fue posible generar las estrategias con IA.',
            'is-error'
          );
        } finally {
          button.disabled = false;
          button.innerHTML = originalHtml;
        }
      };
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

      .dofa-shell{
        width:96%;
        max-width:1450px;
        margin:10px auto 24px auto;
      }

      .dofa-header-card{
        background:
          linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.24);
        color:#ffffff;
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .dofa-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 26%),
          repeating-linear-gradient(
            135deg,
            rgba(255,255,255,.05) 0px,
            rgba(255,255,255,.05) 1px,
            transparent 1px,
            transparent 15px
          );
      }

      .dofa-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        padding:0;
        position:relative;
        z-index:1;
      }

      .dofa-header-overlay::before{
        content:"🧩";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:#ffffff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.5rem;
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .dofa-header-text::before{
        content:"SGSI · Análisis DOFA";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
      }

      .dofa-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        margin:0 !important;
      }

      .dofa-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
      }

      .dofa-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px;
      }

      .dofa-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .dofa-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .dofa-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .dofa-card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .dofa-card-body{
        padding:16px 18px;
      }

      .dofa-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .dofa-card .form-control,
      .dofa-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:37px;
        font-size:.80rem;
        background:#f8fafc;
        box-shadow:none;
      }

      .dofa-card textarea{
        min-height:70px;
        resize:vertical;
      }

      .dofa-card .form-control:focus,
      .dofa-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .18rem rgba(63,134,214,.18);
      }

      .quad{
        border-radius:16px;
        padding:12px;
        border:1px solid #dbe6f4;
        box-shadow:0 8px 18px rgba(15,23,42,.08);
      }

      .quad-h{
        font-weight:950;
        font-size:.86rem;
        margin-bottom:8px;
        color:#0f172a;
      }

      .quad-ta{
        background:rgba(255,255,255,.92) !important;
        border-radius:12px;
      }

      .quad-f{ background:rgba(25,135,84,.10); }
      .quad-o{ background:rgba(13,110,253,.10); }
      .quad-d{ background:rgba(255,193,7,.14); }
      .quad-a{ background:rgba(220,53,69,.10); }

      .dofa-accordion .accordion-item{
        border-radius:14px !important;
        overflow:hidden;
        border:1px solid #dbe6f4;
        box-shadow:0 6px 14px rgba(15,23,42,.06);
      }

      .dofa-accordion .accordion-button{
        font-size:.84rem;
        font-weight:900;
        color:#0b4a8f;
        background:#eef5ff;
      }

      .dofa-accordion .accordion-button:not(.collapsed){
        color:#062b55;
        background:#dbeafe;
        box-shadow:none;
      }


      .dofa-ai-panel{
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:18px;
        padding:13px 15px;
        margin-bottom:10px;
        border:1px solid #b9d5f4;
        border-radius:14px;
        background:linear-gradient(135deg,#eef6ff,#f8fbff);
        box-shadow:0 6px 14px rgba(15,72,133,.08);
      }

      .dofa-ai-copy{
        min-width:0;
      }

      .dofa-ai-title{
        color:#0b4a8f;
        font-size:.86rem;
        font-weight:950;
        margin-bottom:3px;
      }

      .dofa-ai-help{
        color:#516174;
        font-size:.76rem;
        line-height:1.35;
      }

      .dofa-ai-btn{
        flex:0 0 auto;
        border:none;
        border-radius:10px !important;
        padding:9px 16px !important;
        color:#ffffff !important;
        background:linear-gradient(135deg,#6f42c1,#3b82f6);
        font-size:.78rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(76,81,191,.20);
      }

      .dofa-ai-btn:hover,
      .dofa-ai-btn:focus{
        color:#ffffff !important;
        transform:translateY(-1px);
        box-shadow:0 10px 19px rgba(76,81,191,.26);
      }

      .dofa-ai-btn:disabled{
        opacity:.75;
        transform:none;
      }

      .dofa-ai-status{
        display:none;
        margin:0 0 12px 0;
        padding:9px 12px;
        border-radius:10px;
        font-size:.76rem;
        font-weight:700;
      }

      .dofa-ai-status.is-visible{
        display:block;
      }

      .dofa-ai-status.is-info{
        color:#0b4a8f;
        background:#eaf4ff;
        border:1px solid #b9d5f4;
      }

      .dofa-ai-status.is-success{
        color:#166534;
        background:#ecfdf3;
        border:1px solid #a7e2bd;
      }

      .dofa-ai-status.is-error{
        color:#991b1b;
        background:#fff1f2;
        border:1px solid #fecdd3;
      }

      .dofa-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:18px;
        flex-wrap:wrap;
      }

      .dofa-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 24px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .dofa-bottom-actions .btn-primary,
      .dofa-bottom-actions .btn-success{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .dofa-bottom-actions .btn-danger{
        border:none;
        background:linear-gradient(135deg,#b91c1c,#ef4444);
        color:#fff;
      }

      .dofa-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .dofa-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      @media (max-width:992px){
        .dofa-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .dofa-header-card{
          min-height:88px;
        }

        .dofa-title{
          font-size:1.2rem;
        }

        .dofa-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){

        .dofa-ai-panel{
          align-items:stretch;
          flex-direction:column;
          gap:10px;
        }

        .dofa-ai-btn{
          width:100%;
        }

        .dofa-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .dofa-header-overlay::before{
          margin:0;
        }

        .dofa-bottom-actions .btn,
        .dofa-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """, today=date.today().strftime("%Y-%m-%d"), f=f, d=d, o=o, a=a)

    return render_template_string(BASE, content=content)


# =================================
# Listado DOFA
# =================================

@app.route('/dofa/list')
@login_required
def dofa_list():
    user = User.query.get(session.get('user_id'))

    if user.role not in ('admin', 'auditor') and not verificar_permiso(user, "DOFA"):
        flash("No tiene permiso para acceder al módulo DOFA.", "danger")
        return redirect(url_for('menu'))

    read_only = (user.role == 'auditor')
    rows = DofaAnalisis.query.order_by(DofaAnalisis.fecha.desc(), DofaAnalisis.id.desc()).all()

    content = render_template_string("""
    <div class="dofalist-shell">

      <div class="dofalist-header-card">
        <div class="dofalist-header-overlay">
          <div class="dofalist-header-text">
            <h3 class="dofalist-title m-0">Listado DOFA</h3>
            <div class="dofalist-subtitle">
              Consulta, visualización y gestión de matrices DOFA según el perfil del usuario
            </div>
          </div>
        </div>
      </div>

      <div class="dofalist-header-actions">
        <div class="d-flex gap-2 flex-wrap justify-content-center">

          {% if not read_only %}
            <a href="{{ url_for('dofa_new') }}"
               class="btn btn-info text-white rounded-pill px-4 fw-semibold"
               onclick="showLoader()">
              ➕ Nuevo
            </a>
          {% endif %}
        </div>
      </div>

      <div class="dofalist-search-card">
        <div class="dofalist-search-body">
          <div class="row g-2 align-items-center">
            <div class="col-md-8">
              <div class="input-group">
                <span class="input-group-text bg-white">🔎</span>
                <input id="qDofa"
                       class="form-control"
                       placeholder="Buscar por título, creado por, fecha..."
                       autocomplete="off">
              </div>
            </div>
            <div class="col-md-4 text-md-end">
              <span class="badge rounded-pill bg-dark-subtle text-dark px-3 py-2">
                Total: <span id="cntDofa">{{ rows|length }}</span>
              </span>
            </div>
          </div>
        </div>
      </div>

      <div class="dofalist-table-card">
        <div class="dofalist-table-card-body">
          <div class="dofalist-table-wrap">
            <div class="table-responsive">
              <table class="table table-hover align-middle mb-0 dofalist-table" id="tblDofa">
                <thead class="table-light">
                  <tr>
                    <th style="width:80px;">ID</th>
                    <th>Título</th>
                    <th style="width:140px;">Fecha</th>
                    <th style="width:180px;">Creado por</th>
                    <th class="text-end" style="width:320px;">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {% for r in rows %}
                    <tr class="dofa-row"
                        data-search="{{ (r.id|string) ~ ' ' ~ (r.titulo or '') ~ ' ' ~ (r.creado_por or '') ~ ' ' ~ (r.fecha|string) | lower }}">
                      <td class="text-muted">#{{ r.id }}</td>
                      <td class="fw-semibold">{{ r.titulo }}</td>
                      <td>{{ r.fecha }}</td>
                      <td>{{ r.creado_por or "" }}</td>
                      <td class="text-end">

                        <a class="btn btn-sm btn-outline-info rounded-pill"
                           href="{{ url_for('dofa_view', dofa_id=r.id) }}"
                           onclick="showLoader()">
                          👁 Ver
                        </a>

                        {% if not read_only %}
                          <a class="btn btn-sm btn-outline-primary rounded-pill"
                             href="{{ url_for('dofa_edit', dofa_id=r.id) }}"
                             onclick="showLoader()">
                            ✏️ Editar
                          </a>

                          <form method="POST"
                                action="{{ url_for('dofa_delete', dofa_id=r.id) }}"
                                style="display:inline"
                                onsubmit="return confirm('¿Eliminar este DOFA?');">
                            <button class="btn btn-sm btn-outline-danger rounded-pill">
                              🗑 Eliminar
                            </button>
                          </form>
                        {% endif %}
                      </td>
                    </tr>
                  {% endfor %}

                  {% if not rows %}
                    <tr>
                      <td colspan="5" class="text-center text-muted py-5">
                        No hay DOFAs registrados.
                        {% if not read_only %}
                          <div class="mt-3">
                            <a href="{{ url_for('dofa_new') }}"
                               class="btn btn-info text-white rounded-pill px-4 fw-semibold"
                               onclick="showLoader()">
                              ➕ Crear el primero
                            </a>
                          </div>
                        {% endif %}
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

      .dofalist-shell{
        width:96%;
        max-width:1450px;
        margin:10px auto 24px auto;
      }

      /* =========================
         HERO SGSI UNIFICADO
      ========================== */
      .dofalist-header-card{
        background:
          linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.24);
        color:#ffffff;
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .dofalist-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 26%),
          repeating-linear-gradient(
            135deg,
            rgba(255,255,255,.05) 0px,
            rgba(255,255,255,.05) 1px,
            transparent 1px,
            transparent 15px
          );
      }

      .dofalist-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        padding:0;
        position:relative;
        z-index:1;
      }

      .dofalist-header-overlay::before{
        content:"📊";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:#ffffff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.5rem;
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .dofalist-header-text::before{
        content:"SGSI · Listado DOFA";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
      }

      .dofalist-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        margin:0 !important;
      }

      .dofalist-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
      }

      /* =========================
         ACCIONES
      ========================== */
      .dofalist-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px;
      }

      .dofalist-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .dofalist-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .dofalist-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         CARDS
      ========================== */
      .dofalist-search-card,
      .dofalist-table-card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .dofalist-search-card{
        margin-bottom:14px;
      }

      .dofalist-search-body,
      .dofalist-table-card-body{
        padding:14px 16px;
      }

      /* =========================
         FORMULARIO BÚSQUEDA
      ========================== */
      .dofalist-search-body .form-control{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:36px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .dofalist-search-body .btn{
        border-radius:10px;
        font-size:.80rem;
        font-weight:900;
      }

      /* =========================
         TABLA SGSI
      ========================== */
      .dofalist-table-wrap{
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
        overflow:auto;
      }

      .dofalist-table{
        margin-bottom:0;
        font-size:.80rem;
      }

      .dofalist-table thead th{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff;
        font-weight:900;
        text-align:center;
        padding:10px;
      }

      .dofalist-table td{
        vertical-align:middle;
        padding:9px;
        border-bottom:1px solid #e5edf7;
      }

      .dofalist-table tbody tr:nth-child(even){
        background:#f8fbff;
      }

      .dofalist-table tbody tr:hover{
        background:#eef6ff;
      }

      /* =========================
         RESPONSIVE
      ========================== */
      @media (max-width:992px){
        .dofalist-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .dofalist-header-card{
          min-height:88px;
        }

        .dofalist-title{
          font-size:1.2rem;
        }

        .dofalist-search-body,
        .dofalist-table-card-body{
          padding:12px;
        }
      }

      @media (max-width:768px){
        .dofalist-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .dofalist-header-overlay::before{
          margin:0;
        }

        .dofalist-header-actions .btn{
          width:100%;
        }
      }
    </style>

    <script>
      (function(){
        const q = document.getElementById("qDofa");
        const rows = Array.from(document.querySelectorAll("#tblDofa .dofa-row"));
        const cnt = document.getElementById("cntDofa");
        if(!q || !rows.length || !cnt) return;

        function apply(){
          const s = (q.value || "").toLowerCase().trim();
          let vis = 0;
          rows.forEach(tr => {
            const hay = (tr.getAttribute("data-search") || "");
            const show = (!s || hay.includes(s));
            tr.style.display = show ? "" : "none";
            if(show) vis++;
          });
          cnt.textContent = vis;
        }
        q.addEventListener("input", apply);
        apply();
      })();
    </script>
    """, rows=rows, read_only=read_only)

    return render_template_string(BASE, content=content)


# =================================
# Ver DOFA
# =================================

@app.route('/dofa/<int:dofa_id>')
@login_required
def dofa_view(dofa_id):
    user = User.query.get(session.get('user_id'))

    if user.role not in ('admin', 'auditor') and not verificar_permiso(user, "DOFA"):
        flash("No tiene permiso para acceder al módulo DOFA.", "danger")
        return redirect(url_for('menu'))

    read_only = (user.role == 'auditor')
    r = DofaAnalisis.query.get_or_404(dofa_id)

    content = render_template_string("""
    <div class="dofaview-shell">

      <div class="dofaview-header-card">
        <div class="dofaview-header-overlay">
          <div class="dofaview-header-text">
            <h3 class="dofaview-title m-0">Ver DOFA</h3>
            <div class="dofaview-subtitle">
              {{ r.titulo }} • {{ r.fecha }}
              {% if r.creado_por %} • Creado por: {{ r.creado_por }}{% endif %}
            </div>
          </div>
        </div>
      </div>

      <div class="dofaview-header-actions">
        <div class="d-flex gap-2 flex-wrap justify-content-center">
          <a href="{{ url_for('dofa_list') }}"
             class="btn rounded-pill px-4 fw-semibold dofaview-back-btn"
             onclick="showLoader()">
            ⬅ Volver al Listado DOFA
          </a>

          {% if not read_only %}
            <a href="{{ url_for('dofa_edit', dofa_id=r.id) }}"
               class="btn btn-info text-white rounded-pill px-4 fw-semibold"
               onclick="showLoader()">
              ✏️ Editar
            </a>
          {% endif %}
        </div>
      </div>

      <div class="dofaview-card">
        <div class="dofaview-card-body">

          <div class="row g-3">

            <div class="col-md-6">
              <div class="quad quad-f">
                <div class="quad-h">✅ Fortalezas</div>
                <div class="quad-box">{{ (r.fortalezas or '') }}</div>
              </div>
            </div>

            <div class="col-md-6">
              <div class="quad quad-o">
                <div class="quad-h">🌟 Oportunidades</div>
                <div class="quad-box">{{ (r.oportunidades or '') }}</div>
              </div>
            </div>

            <div class="col-md-6">
              <div class="quad quad-d">
                <div class="quad-h">⚠️ Debilidades</div>
                <div class="quad-box">{{ (r.debilidades or '') }}</div>
              </div>
            </div>

            <div class="col-md-6">
              <div class="quad quad-a">
                <div class="quad-h">🛡️ Amenazas</div>
                <div class="quad-box">{{ (r.amenazas or '') }}</div>
              </div>
            </div>

          </div>

          <hr class="my-4">

          <div class="accordion dofaview-accordion" id="accEstrategiasVer">
            <div class="accordion-item">
              <h2 class="accordion-header" id="hEV">
                <button class="accordion-button collapsed fw-semibold"
                        type="button"
                        data-bs-toggle="collapse"
                        data-bs-target="#cEV"
                        aria-expanded="false"
                        aria-controls="cEV">
                  🧠 Estrategias FO / FA / DO / DA
                </button>
              </h2>
              <div id="cEV"
                   class="accordion-collapse collapse"
                   aria-labelledby="hEV"
                   data-bs-parent="#accEstrategiasVer">
                <div class="accordion-body">

                  <div class="row g-3">
                    <div class="col-md-6">
                      <div class="strat">
                        <div class="strat-h">FO (Fortalezas + Oportunidades)</div>
                        <div class="strat-box">{{ r.estrategias_fo or '' }}</div>
                      </div>
                    </div>

                    <div class="col-md-6">
                      <div class="strat">
                        <div class="strat-h">FA (Fortalezas + Amenazas)</div>
                        <div class="strat-box">{{ r.estrategias_fa or '' }}</div>
                      </div>
                    </div>

                    <div class="col-md-6">
                      <div class="strat">
                        <div class="strat-h">DO (Debilidades + Oportunidades)</div>
                        <div class="strat-box">{{ r.estrategias_do or '' }}</div>
                      </div>
                    </div>

                    <div class="col-md-6">
                      <div class="strat">
                        <div class="strat-h">DA (Debilidades + Amenazas)</div>
                        <div class="strat-box">{{ r.estrategias_da or '' }}</div>
                      </div>
                    </div>
                  </div>

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

      .dofaview-shell{
        width:96%;
        max-width:1450px;
        margin:10px auto 24px auto;
      }

      .dofaview-header-card{
        background:
          linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.24);
        color:#ffffff;
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .dofaview-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 26%),
          repeating-linear-gradient(
            135deg,
            rgba(255,255,255,.05) 0px,
            rgba(255,255,255,.05) 1px,
            transparent 1px,
            transparent 15px
          );
      }

      .dofaview-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        padding:0;
        position:relative;
        z-index:1;
      }

      .dofaview-header-overlay::before{
        content:"🧩";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:#ffffff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.5rem;
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .dofaview-header-text::before{
        content:"SGSI · Detalle DOFA";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
      }

      .dofaview-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        margin:0 !important;
      }

      .dofaview-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
      }

      .dofaview-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px;
      }

      .dofaview-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .dofaview-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .dofaview-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .dofaview-card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .dofaview-card-body{
        padding:16px 18px;
      }

      .quad{
        border-radius:16px;
        padding:12px;
        border:1px solid #dbe6f4;
        box-shadow:0 8px 18px rgba(15,23,42,.08);
      }

      .quad-h{
        font-weight:950;
        font-size:.86rem;
        margin-bottom:8px;
        color:#0f172a;
      }

      .quad-box{
        background:rgba(255,255,255,.92);
        border-radius:12px;
        padding:10px 12px;
        min-height:130px;
        white-space:pre-wrap;
        font-size:.80rem;
        line-height:1.38;
        color:#101827;
      }

      .quad-f{ background:rgba(25,135,84,.10); }
      .quad-o{ background:rgba(13,110,253,.10); }
      .quad-d{ background:rgba(255,193,7,.14); }
      .quad-a{ background:rgba(220,53,69,.10); }

      .strat{
        border-radius:14px;
        border:1px solid #dbe6f4;
        background:#f8fbff;
        padding:12px;
        box-shadow:0 6px 14px rgba(15,23,42,.06);
      }

      .strat-h{
        font-weight:950;
        font-size:.86rem;
        margin-bottom:8px;
        color:#0b4a8f;
      }

      .strat-box{
        background:rgba(255,255,255,.92);
        border-radius:12px;
        padding:10px 12px;
        white-space:pre-wrap;
        min-height:95px;
        font-size:.80rem;
        line-height:1.38;
        color:#101827;
      }

      .dofaview-accordion .accordion-item{
        border-radius:14px !important;
        overflow:hidden;
        border:1px solid #dbe6f4;
        box-shadow:0 6px 14px rgba(15,23,42,.06);
      }

      .dofaview-accordion .accordion-button{
        font-size:.84rem;
        font-weight:900;
        color:#0b4a8f;
        background:#eef5ff;
      }

      .dofaview-accordion .accordion-button:not(.collapsed){
        color:#062b55;
        background:#dbeafe;
        box-shadow:none;
      }

      @media (max-width:992px){
        .dofaview-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .dofaview-header-card{
          min-height:88px;
        }

        .dofaview-title{
          font-size:1.2rem;
        }

        .dofaview-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .dofaview-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .dofaview-header-overlay::before{
          margin:0;
        }

        .dofaview-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """, r=r, read_only=read_only)

    return render_template_string(BASE, content=content)


# =================================
# Editar DOFA
# =================================

@app.route('/dofa/<int:dofa_id>/edit', methods=['GET', 'POST'])
@login_required
def dofa_edit(dofa_id):
    user = User.query.get(session.get('user_id'))

    if user.role not in ('admin', 'auditor') and not verificar_permiso(user, "DOFA"):
        flash("No tiene permiso para acceder al módulo DOFA.", "danger")
        return redirect(url_for('menu'))

    if user.role == 'auditor':
        flash("Perfil auditor: solo lectura.", "warning")
        return redirect(url_for('dofa_view', dofa_id=dofa_id))

    r = DofaAnalisis.query.get_or_404(dofa_id)

    if request.method == 'POST':
        r.titulo = (request.form.get('titulo') or r.titulo).strip()

        fecha_str = (request.form.get('fecha') or "").strip()
        try:
            r.fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date() if fecha_str else r.fecha
        except Exception:
            pass

        r.fortalezas = request.form.get('fortalezas') or ""
        r.oportunidades = request.form.get('oportunidades') or ""
        r.debilidades = request.form.get('debilidades') or ""
        r.amenazas = request.form.get('amenazas') or ""

        r.estrategias_fo = request.form.get('estrategias_fo') or ""
        r.estrategias_fa = request.form.get('estrategias_fa') or ""
        r.estrategias_do = request.form.get('estrategias_do') or ""
        r.estrategias_da = request.form.get('estrategias_da') or ""

        db.session.commit()
        flash("DOFA actualizado correctamente.", "success")
        return redirect(url_for('dofa_view', dofa_id=r.id))

    content = render_template_string("""
    <div class="dofaedit-shell">

      <div class="dofaedit-header-card">
        <div class="dofaedit-header-overlay">
          <div class="dofaedit-header-text">
            <h3 class="dofaedit-title m-0">Editar DOFA</h3>
            <div class="dofaedit-subtitle">
              {{ r.titulo }} • {{ r.fecha }}
            </div>
          </div>
        </div>
      </div>

      <div class="dofaedit-header-actions">
        <div class="d-flex gap-2 flex-wrap justify-content-center">
          <a href="{{ url_for('dofa_list') }}"
             class="btn rounded-pill px-4 fw-semibold dofaedit-back-btn"
             onclick="showLoader()">
            ⬅ Volver al Listado DOFA
          </a>
        </div>
      </div>

      <form method="POST" class="dofaedit-card">
        <div class="dofaedit-card-body">

          <div class="row g-3">
            <div class="col-md-8">
              <label class="form-label fw-semibold">Título</label>
              <input type="text" name="titulo" class="form-control" value="{{ r.titulo }}">
            </div>
            <div class="col-md-4">
              <label class="form-label fw-semibold">Fecha</label>
              <input type="date" name="fecha" class="form-control" value="{{ r.fecha }}">
            </div>
          </div>

          <hr class="my-4">

          <div class="row g-3">
            <div class="col-md-6">
              <div class="quad quad-f">
                <div class="quad-h">✅ Fortalezas</div>
                <textarea name="fortalezas" class="form-control quad-ta" rows="7" placeholder="- ...">{{ r.fortalezas or "" }}</textarea>
              </div>
            </div>

            <div class="col-md-6">
              <div class="quad quad-o">
                <div class="quad-h">🌟 Oportunidades</div>
                <textarea name="oportunidades" class="form-control quad-ta" rows="7" placeholder="- ...">{{ r.oportunidades or "" }}</textarea>
              </div>
            </div>

            <div class="col-md-6">
              <div class="quad quad-d">
                <div class="quad-h">⚠️ Debilidades</div>
                <textarea name="debilidades" class="form-control quad-ta" rows="7" placeholder="- ...">{{ r.debilidades or "" }}</textarea>
              </div>
            </div>

            <div class="col-md-6">
              <div class="quad quad-a">
                <div class="quad-h">🛡️ Amenazas</div>
                <textarea name="amenazas" class="form-control quad-ta" rows="7" placeholder="- ...">{{ r.amenazas or "" }}</textarea>
              </div>
            </div>
          </div>

          <hr class="my-4">


          <div class="dofa-ai-panel">
            <div class="dofa-ai-copy">
              <div class="dofa-ai-title">✨ Generación y actualización con IA</div>
              <div class="dofa-ai-help">
                La IA toma los cuatro cuadrantes tal como aparecen en esta edición. Las estrategias
                generadas quedan completamente editables y también pueden escribirse manualmente.
              </div>
            </div>
            <button type="button"
                    class="btn dofa-ai-btn"
                    data-no-progress="true"
                    onclick="generarEstrategiasDofaIA(this, 'cEE')">
              <span class="dofa-ai-btn-label">🧠 Generar o regenerar con IA</span>
            </button>
          </div>
          <div class="dofa-ai-status" role="status" aria-live="polite"></div>

          <div class="accordion dofaedit-accordion" id="accEstrategiasEdit">
            <div class="accordion-item">
              <h2 class="accordion-header" id="hEE">
                <button class="accordion-button collapsed fw-semibold"
                        type="button"
                        data-bs-toggle="collapse"
                        data-bs-target="#cEE"
                        aria-expanded="false"
                        aria-controls="cEE">
                  🧠 Estrategias FO / FA / DO / DA
                </button>
              </h2>
              <div id="cEE"
                   class="accordion-collapse collapse"
                   aria-labelledby="hEE"
                   data-bs-parent="#accEstrategiasEdit">
                <div class="accordion-body">

                  <div class="row g-3">
                    <div class="col-md-6">
                      <label class="form-label fw-semibold">FO (Fortalezas + Oportunidades)</label>
                      <textarea name="estrategias_fo" class="form-control" rows="4">{{ r.estrategias_fo or "" }}</textarea>
                    </div>

                    <div class="col-md-6">
                      <label class="form-label fw-semibold">FA (Fortalezas + Amenazas)</label>
                      <textarea name="estrategias_fa" class="form-control" rows="4">{{ r.estrategias_fa or "" }}</textarea>
                    </div>

                    <div class="col-md-6">
                      <label class="form-label fw-semibold">DO (Debilidades + Oportunidades)</label>
                      <textarea name="estrategias_do" class="form-control" rows="4">{{ r.estrategias_do or "" }}</textarea>
                    </div>

                    <div class="col-md-6">
                      <label class="form-label fw-semibold">DA (Debilidades + Amenazas)</label>
                      <textarea name="estrategias_da" class="form-control" rows="4">{{ r.estrategias_da or "" }}</textarea>
                    </div>
                  </div>

                </div>
              </div>
            </div>
          </div>

          <div class="dofaedit-bottom-actions">
            <button class="btn btn-success rounded-pill px-4 fw-semibold">
              💾 Guardar cambios
            </button>

            <a href="{{ url_for('dofa_view', dofa_id=r.id) }}"
               class="btn rounded-pill px-4 fw-semibold dofaedit-cancel-btn"
               onclick="showLoader()">
              Cancelar
            </a>
          </div>

        </div>
      </form>

    </div>


    <script>
    (function () {
      if (window.__GRAC_DOFA_AI_READY__) return;
      window.__GRAC_DOFA_AI_READY__ = true;

      function showStrategySection(collapseId) {
        const collapseElement = document.getElementById(collapseId);
        if (!collapseElement) return;

        try {
          if (window.bootstrap && window.bootstrap.Collapse) {
            window.bootstrap.Collapse
              .getOrCreateInstance(collapseElement, {toggle: false})
              .show();
          } else {
            collapseElement.classList.add('show');
          }
        } catch (_error) {
          collapseElement.classList.add('show');
        }

        const toggle = document.querySelector('[data-bs-target="#' + collapseId + '"]');
        if (toggle) {
          toggle.classList.remove('collapsed');
          toggle.setAttribute('aria-expanded', 'true');
        }
      }

      function setDofaAiStatus(statusElement, message, kind) {
        if (!statusElement) return;
        statusElement.textContent = message || '';
        statusElement.className = 'dofa-ai-status is-visible ' + (kind || 'is-info');
      }

      window.generarEstrategiasDofaIA = async function (button, collapseId) {
        const form = button ? button.closest('form') : null;
        const panel = button ? button.closest('.dofa-ai-panel') : null;
        const statusElement = panel && panel.nextElementSibling &&
          panel.nextElementSibling.classList.contains('dofa-ai-status')
            ? panel.nextElementSibling
            : null;

        if (!form) {
          setDofaAiStatus(statusElement, 'No se encontró el formulario de la matriz DOFA.', 'is-error');
          return;
        }

        const names = [
          'fortalezas',
          'oportunidades',
          'debilidades',
          'amenazas',
          'estrategias_fo',
          'estrategias_fa',
          'estrategias_do',
          'estrategias_da'
        ];

        const fields = {};
        names.forEach(function (name) {
          fields[name] = form.querySelector('[name="' + name + '"]');
        });

        const sourceLabels = {
          fortalezas: 'Fortalezas',
          oportunidades: 'Oportunidades',
          debilidades: 'Debilidades',
          amenazas: 'Amenazas'
        };

        const missing = Object.keys(sourceLabels).filter(function (name) {
          return !fields[name] || !String(fields[name].value || '').trim();
        });

        if (missing.length) {
          setDofaAiStatus(
            statusElement,
            'Complete los cuatro cuadrantes. Falta información en: ' +
              missing.map(function (name) { return sourceLabels[name]; }).join(', ') + '.',
            'is-error'
          );
          return;
        }

        const strategyNames = [
          'estrategias_fo',
          'estrategias_fa',
          'estrategias_do',
          'estrategias_da'
        ];
        const hasExistingStrategies = strategyNames.some(function (name) {
          return fields[name] && String(fields[name].value || '').trim();
        });

        if (
          hasExistingStrategies &&
          !window.confirm(
            'Ya existen estrategias registradas. La generación con IA reemplazará temporalmente ' +
            'el contenido actual de FO, FA, DO y DA. Podrá editarlo antes de guardar. ¿Desea continuar?'
          )
        ) {
          return;
        }

        const originalHtml = button.innerHTML;
        button.disabled = true;
        button.innerHTML =
          '<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>Generando...';
        setDofaAiStatus(
          statusElement,
          'Analizando la matriz y construyendo estrategias FO, FA, DO y DA...',
          'is-info'
        );

        const payload = {
          fortalezas: fields.fortalezas.value,
          oportunidades: fields.oportunidades.value,
          debilidades: fields.debilidades.value,
          amenazas: fields.amenazas.value
        };

        try {
          const response = await fetch("{{ url_for('dofa_generar_estrategias_ia') }}", {
            method: 'POST',
            credentials: 'same-origin',
            cache: 'no-store',
            headers: {
              'Content-Type': 'application/json',
              'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify(payload)
          });

          let data = {};
          try {
            data = await response.json();
          } catch (_jsonError) {
            data = {};
          }

          if (!response.ok || !data.ok) {
            throw new Error(
              data.message || 'No fue posible generar las estrategias con IA.'
            );
          }

          const strategies = data.estrategias || {};
          const labels = {
            estrategias_fo: 'FO',
            estrategias_fa: 'FA',
            estrategias_do: 'DO',
            estrategias_da: 'DA'
          };

          strategyNames.forEach(function (name) {
            if (!fields[name] || !String(strategies[name] || '').trim()) {
              throw new Error('La IA no devolvió una estrategia válida para ' + labels[name] + '.');
            }
          });

          strategyNames.forEach(function (name) {
            fields[name].value = strategies[name];
            fields[name].dispatchEvent(new Event('input', {bubbles: true}));
          });

          showStrategySection(collapseId);
          setDofaAiStatus(
            statusElement,
            data.message ||
              'Estrategias generadas. Puede editarlas antes de guardar la matriz DOFA.',
            'is-success'
          );

          if (fields.estrategias_fo) {
            setTimeout(function () {
              fields.estrategias_fo.focus();
              fields.estrategias_fo.scrollIntoView({behavior: 'smooth', block: 'center'});
            }, 250);
          }
        } catch (error) {
          setDofaAiStatus(
            statusElement,
            error && error.message
              ? error.message
              : 'No fue posible generar las estrategias con IA.',
            'is-error'
          );
        } finally {
          button.disabled = false;
          button.innerHTML = originalHtml;
        }
      };
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

      .dofaedit-shell{
        width:96%;
        max-width:1450px;
        margin:10px auto 24px auto;
      }

      .dofaedit-header-card{
        background:
          linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.24);
        color:#ffffff;
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .dofaedit-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 26%),
          repeating-linear-gradient(
            135deg,
            rgba(255,255,255,.05) 0px,
            rgba(255,255,255,.05) 1px,
            transparent 1px,
            transparent 15px
          );
      }

      .dofaedit-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        padding:0;
        position:relative;
        z-index:1;
      }

      .dofaedit-header-overlay::before{
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
        font-size:1.5rem;
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .dofaedit-header-text::before{
        content:"SGSI · Edición DOFA";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
      }

      .dofaedit-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        margin:0 !important;
      }

      .dofaedit-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
      }

      .dofaedit-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px;
      }

      .dofaedit-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .dofaedit-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .dofaedit-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .dofaedit-light-btn{
        background:rgba(255,255,255,.14);
        color:#ffffff;
        border:1px solid rgba(255,255,255,.65);
      }

      .dofaedit-light-btn:hover{
        background:rgba(255,255,255,.22);
        color:#ffffff;
      }

      .dofaedit-card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .dofaedit-card-body{
        padding:16px 18px;
      }

      .dofaedit-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .dofaedit-card .form-control,
      .dofaedit-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:37px;
        font-size:.80rem;
        background:#f8fafc;
        box-shadow:none;
      }

      .dofaedit-card textarea{
        min-height:70px;
        resize:vertical;
      }

      .dofaedit-card .form-control:focus,
      .dofaedit-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .18rem rgba(63,134,214,.18);
      }

      .quad{
        border-radius:16px;
        padding:12px;
        border:1px solid #dbe6f4;
        box-shadow:0 8px 18px rgba(15,23,42,.08);
      }

      .quad-h{
        font-weight:950;
        font-size:.86rem;
        margin-bottom:8px;
        color:#0f172a;
      }

      .quad-ta{
        background:rgba(255,255,255,.92) !important;
        border-radius:12px;
      }

      .quad-f{ background:rgba(25,135,84,.10); }
      .quad-o{ background:rgba(13,110,253,.10); }
      .quad-d{ background:rgba(255,193,7,.14); }
      .quad-a{ background:rgba(220,53,69,.10); }

      .dofaedit-accordion .accordion-item{
        border-radius:14px !important;
        overflow:hidden;
        border:1px solid #dbe6f4;
        box-shadow:0 6px 14px rgba(15,23,42,.06);
      }

      .dofaedit-accordion .accordion-button{
        font-size:.84rem;
        font-weight:900;
        color:#0b4a8f;
        background:#eef5ff;
      }

      .dofaedit-accordion .accordion-button:not(.collapsed){
        color:#062b55;
        background:#dbeafe;
        box-shadow:none;
      }


      .dofa-ai-panel{
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:18px;
        padding:13px 15px;
        margin-bottom:10px;
        border:1px solid #b9d5f4;
        border-radius:14px;
        background:linear-gradient(135deg,#eef6ff,#f8fbff);
        box-shadow:0 6px 14px rgba(15,72,133,.08);
      }

      .dofa-ai-copy{
        min-width:0;
      }

      .dofa-ai-title{
        color:#0b4a8f;
        font-size:.86rem;
        font-weight:950;
        margin-bottom:3px;
      }

      .dofa-ai-help{
        color:#516174;
        font-size:.76rem;
        line-height:1.35;
      }

      .dofa-ai-btn{
        flex:0 0 auto;
        border:none;
        border-radius:10px !important;
        padding:9px 16px !important;
        color:#ffffff !important;
        background:linear-gradient(135deg,#6f42c1,#3b82f6);
        font-size:.78rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(76,81,191,.20);
      }

      .dofa-ai-btn:hover,
      .dofa-ai-btn:focus{
        color:#ffffff !important;
        transform:translateY(-1px);
        box-shadow:0 10px 19px rgba(76,81,191,.26);
      }

      .dofa-ai-btn:disabled{
        opacity:.75;
        transform:none;
      }

      .dofa-ai-status{
        display:none;
        margin:0 0 12px 0;
        padding:9px 12px;
        border-radius:10px;
        font-size:.76rem;
        font-weight:700;
      }

      .dofa-ai-status.is-visible{
        display:block;
      }

      .dofa-ai-status.is-info{
        color:#0b4a8f;
        background:#eaf4ff;
        border:1px solid #b9d5f4;
      }

      .dofa-ai-status.is-success{
        color:#166534;
        background:#ecfdf3;
        border:1px solid #a7e2bd;
      }

      .dofa-ai-status.is-error{
        color:#991b1b;
        background:#fff1f2;
        border:1px solid #fecdd3;
      }

      .dofaedit-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:18px;
        flex-wrap:wrap;
      }

      .dofaedit-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 24px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .dofaedit-bottom-actions .btn-primary,
      .dofaedit-bottom-actions .btn-success{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .dofaedit-bottom-actions .btn-danger{
        border:none;
        background:linear-gradient(135deg,#b91c1c,#ef4444);
        color:#fff;
      }

      .dofaedit-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .dofaedit-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      @media (max-width:992px){
        .dofaedit-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .dofaedit-header-card{
          min-height:88px;
        }

        .dofaedit-title{
          font-size:1.2rem;
        }

        .dofaedit-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){

        .dofa-ai-panel{
          align-items:stretch;
          flex-direction:column;
          gap:10px;
        }

        .dofa-ai-btn{
          width:100%;
        }

        .dofaedit-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .dofaedit-header-overlay::before{
          margin:0;
        }

        .dofaedit-bottom-actions .btn,
        .dofaedit-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """, r=r)

    return render_template_string(BASE, content=content)


# =================================
# Eliminar DOFA
# =================================

@app.route('/dofa/<int:dofa_id>/delete', methods=['POST'])
@login_required
def dofa_delete(dofa_id):
    user = User.query.get(session.get('user_id'))

    if user.role not in ('admin', 'auditor') and not verificar_permiso(user, "DOFA"):
        flash("No tiene permiso para acceder al módulo DOFA.", "danger")
        return redirect(url_for('menu'))

    if user.role == 'auditor':
        flash("Perfil auditor: solo lectura.", "warning")
        return redirect(url_for('dofa_list'))

    r = DofaAnalisis.query.get_or_404(dofa_id)
    db.session.delete(r)
    db.session.commit()
    flash("DOFA eliminado correctamente.", "success")
    return redirect(url_for('dofa_list'))


# ==========================================================================================================================================
#                                                               Fin Módulo DOFA
# ==========================================================================================================================================

# ==========================================================================================================================================
#                                                               Módulo de Listado de Documentos Maestros
# ==========================================================================================================================================

DOCS_ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "xls", "xlsx"}

def docs_allowed_file(filename: str) -> bool:
    if not filename:
        return False
    ext = os.path.splitext(filename)[1].lower().strip()
    if not ext:
        return False
    return ext[1:] in DOCS_ALLOWED_EXTENSIONS

def docs_unique_store_name(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower().strip()
    return f"{uuid.uuid4().hex}{ext}"

def fmt_kb(size):
    if not size:
        return "0 KB"
    return f"{round(size / 1024, 1)} KB"


# ========================================
# ENTRADA DIRECTA — Listado Maestro de Documentos
# ========================================
@app.route('/docs_menu')
@login_required
def docs_menu():
    user = User.query.get(session.get('user_id'))

    if user.role not in ('admin', 'auditor') and not verificar_permiso(user, "Listado Maestro de Documentos"):
        flash("No tiene permiso para acceder al listado maestro de documentos.", "danger")
        return redirect(url_for('menu'))

    return redirect(url_for('docs_matriz'))



# ========================================
# Configuración de tipos documentales
# ========================================
@app.route('/docs_tipos_config', methods=['GET', 'POST'])
@login_required
def docs_tipos_config():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede configurar los tipos de documentos.", "danger")
        return redirect(url_for('docs_menu'))

    if user.role != 'admin' and not verificar_permiso(user, "Listado Maestro de Documentos"):
        flash("No tiene permiso para agregar configuraciones al listado maestro de documentos.", "danger")
        return redirect(url_for('docs_menu'))

    if request.method == 'POST':
        rid = request.form.get('id', type=int)

        nombre = (request.form.get('nombre') or '').strip()
        descripcion = (request.form.get('descripcion') or '').strip()
        min_meses_revision = request.form.get('min_meses_revision', type=int) or 0

        if not nombre:
            flash("El nombre del tipo de documento es obligatorio.", "danger")
            return redirect(url_for('docs_tipos_config'))

        if rid:
            item = DocTipoDocumento.query.get(rid)
            if not item:
                flash("Registro no encontrado.", "danger")
                return redirect(url_for('docs_tipos_config'))
        else:
            item = DocTipoDocumento()
            db.session.add(item)

        item.nombre = nombre
        item.descripcion = descripcion
        item.min_meses_revision = min_meses_revision

        db.session.commit()
        flash("Tipo de documento guardado correctamente.", "success")
        return redirect(url_for('docs_tipos_config'))

    edit_id   = request.args.get('edit', type=int)
    edit_item = DocTipoDocumento.query.get(edit_id) if edit_id else None
    items     = DocTipoDocumento.query.order_by(DocTipoDocumento.id.desc()).all()

    html = """
    <div class="doccfg-shell">

      <div class="doccfg-header-card">
        <div class="doccfg-header-overlay">
          <div class="doccfg-header-text">
            <h3 class="doccfg-title m-0">Configuración Nombre de Documentos</h3>
            <div class="doccfg-subtitle">
              Administración de tipos documentales, descripción y periodicidad mínima de revisión
            </div>
          </div>
        </div>
      </div>

      <div class="doccfg-header-actions">
        <a href="{{ url_for('docs_menu') }}"
           class="btn rounded-pill px-5 fw-bold doccfg-back-btn">
          ⬅ Volver al Menú Listado Maestro
        </a>
      </div>

      <div class="doccfg-form-card">
        <div class="doccfg-form-card-body">
          <form method="post">
            {% if edit_item %}
              <input type="hidden" name="id" value="{{ edit_item.id }}">
            {% endif %}

            <div class="row g-3">
              <div class="col-md-6">
                <label class="form-label">Tipo de documento</label>
                <input type="text"
                       name="nombre"
                       class="form-control"
                       value="{{ edit_item.nombre if edit_item else '' }}"
                       required>
              </div>

              <div class="col-md-6">
                <label class="form-label">Descripción</label>
                <input type="text"
                       name="descripcion"
                       class="form-control"
                       value="{{ edit_item.descripcion if edit_item else '' }}">
              </div>

              <div class="col-md-4">
                <label class="form-label">Mínimo tiempo de revisión (meses)</label>
                <input type="number"
                       name="min_meses_revision"
                       class="form-control"
                       min="0"
                       value="{{ edit_item.min_meses_revision if edit_item and edit_item.min_meses_revision is not none else 0 }}">
                <small class="text-muted">Ejemplo: 12 = revisar al menos una vez al año.</small>
              </div>
            </div>

            <div class="doccfg-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                {{ 'Guardar cambios' if edit_item else 'Agregar' }}
              </button>

              {% if edit_item %}
                <a href="{{ url_for('docs_tipos_config') }}"
                   class="btn rounded-pill px-4 fw-bold doccfg-cancel-btn">
                  Cancelar
                </a>
              {% endif %}
            </div>
          </form>
        </div>
      </div>

      <div class="doccfg-table-card">
        <div class="doccfg-table-card-body">
          <div class="doccfg-table-wrap">
            <div class="table-responsive">
              <table class="table table-bordered table-sm align-middle doccfg-table mb-0">
                <thead class="table-secondary">
                  <tr class="text-center">
                    <th>Tipo de documento</th>
                    <th>Descripción</th>
                    <th>Mín. revisión (meses)</th>
                    <th style="width:18%">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {% for it in items %}
                    <tr>
                      <td>{{ it.nombre }}</td>
                      <td>{{ it.descripcion or '—' }}</td>
                      <td class="text-center">
                        {{ it.min_meses_revision if it.min_meses_revision is not none else '0' }}
                      </td>
                      <td class="text-center">
                        <a href="{{ url_for('docs_tipos_config', edit=it.id) }}"
                           class="btn btn-warning btn-sm rounded-pill px-3">
                          Editar
                        </a>
                        <a href="{{ url_for('docs_tipos_delete', id=it.id) }}"
                           class="btn btn-danger btn-sm rounded-pill px-3"
                           onclick="return confirm('¿Eliminar este tipo de documento?');">
                          Eliminar
                        </a>
                      </td>
                    </tr>
                  {% endfor %}

                  {% if items|length == 0 %}
                    <tr>
                      <td colspan="4" class="text-center text-muted py-4">
                        Sin tipos configurados
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

      .doccfg-shell{
        width:96%;
        max-width:1400px;
        margin:10px auto 24px auto;
      }

      /* =========================
         HERO SGSI
      ========================== */
      .doccfg-header-card{
        background:
          linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.24);
        color:#ffffff;
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .doccfg-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 26%),
          repeating-linear-gradient(
            135deg,
            rgba(255,255,255,.05) 0px,
            rgba(255,255,255,.05) 1px,
            transparent 1px,
            transparent 15px
          );
      }

      .doccfg-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        padding:0;
        position:relative;
        z-index:1;
      }

      .doccfg-header-overlay::before{
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
        font-size:1.5rem;
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .doccfg-header-text::before{
        content:"SGSI · Configuración Documental";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
      }

      .doccfg-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        margin:0 !important;
      }

      .doccfg-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
      }

      /* =========================
         ACCIONES
      ========================== */
      .doccfg-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px;
      }

      .doccfg-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .doccfg-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .doccfg-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         CARDS
      ========================== */
      .doccfg-form-card,
      .doccfg-table-card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .doccfg-form-card{
        margin-bottom:14px;
      }

      .doccfg-form-card-body,
      .doccfg-table-card-body{
        padding:14px 16px;
      }

      /* =========================
         FORMULARIO
      ========================== */
      .doccfg-form-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .doccfg-form-card .form-control,
      .doccfg-form-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:36px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .doccfg-form-card .form-control:focus,
      .doccfg-form-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .18rem rgba(63,134,214,.18);
      }

      /* =========================
         BOTONES
      ========================== */
      .doccfg-bottom-actions{
        display:flex;
        justify-content:flex-start;
        gap:10px;
        flex-wrap:wrap;
        margin-top:16px;
      }

      .doccfg-bottom-actions .btn{
        border-radius:10px !important;
        min-height:36px;
        padding:7px 20px !important;
        font-size:.80rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .doccfg-bottom-actions .btn-primary,
      .doccfg-bottom-actions .btn-success{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .doccfg-bottom-actions .btn-danger{
        border:none;
        background:linear-gradient(135deg,#b91c1c,#ef4444);
        color:#fff;
      }

      .doccfg-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .doccfg-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         TABLA SGSI
      ========================== */
      .doccfg-table-wrap{
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
        overflow:auto;
      }

      .doccfg-table{
        margin-bottom:0;
        font-size:.80rem;
      }

      .doccfg-table thead th{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff;
        font-weight:900;
        text-align:center;
        padding:10px;
      }

      .doccfg-table td{
        padding:9px;
        border-bottom:1px solid #e5edf7;
      }

      .doccfg-table tbody tr:nth-child(even){
        background:#f8fbff;
      }

      .doccfg-table tbody tr:hover{
        background:#eef6ff;
      }

      /* =========================
         RESPONSIVE
      ========================== */
      @media (max-width:992px){
        .doccfg-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .doccfg-header-card{
          min-height:88px;
        }

        .doccfg-title{
          font-size:1.2rem;
        }

        .doccfg-form-card-body,
        .doccfg-table-card-body{
          padding:12px;
        }

        .doccfg-bottom-actions{
          justify-content:center;
        }
      }

      @media (max-width:768px){
        .doccfg-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .doccfg-header-overlay::before{
          margin:0;
        }

        .doccfg-header-actions .btn,
        .doccfg-bottom-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(html, edit_item=edit_item, items=items)
    return render_template_string(BASE, content=Markup(inner))


# =========================
# Borrado tipos de documentos
# =========================
@app.route('/docs_tipos/delete/<int:id>')
@login_required
def docs_tipos_delete(id):
    item = DocTipoDocumento.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash("Tipo de documento eliminado.", "success")
    return redirect(url_for('docs_tipos_config'))


# =========================
# Agregar documentos
# =========================
@app.route('/docs/new', methods=['GET', 'POST'])
@login_required
def docs_new():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede agregar registros.", "danger")
        return redirect(url_for('docs_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Listado Maestro de Documentos"):
        flash("No tiene permiso para agregar configuraciones al listado maestro de documentos.", "danger")
        return redirect(url_for('docs_matriz'))

    tipos = DocTipoDocumento.query.order_by(DocTipoDocumento.nombre.asc()).all()

    if request.method == 'POST':
        tipo_id = request.form.get('tipo_id', type=int)
        codigo  = (request.form.get('codigo') or '').strip()
        inicial = (request.form.get('inicial') or '').strip()
        tipo_texto = (request.form.get('tipo_texto') or '').strip()
        num1   = request.form.get('num1', type=int)
        num2   = request.form.get('num2', type=int)
        num3   = request.form.get('num3', type=int)
        nombre_documento = (request.form.get('nombre_documento') or '').strip()
        version = request.form.get('version', type=int) or 1
        fecha_creacion_raw = (request.form.get('fecha_creacion') or '').strip()
        fecha_ultima_revision_raw = (request.form.get('fecha_ultima_revision') or '').strip()

        fecha_creacion = parse_fecha_flexible(fecha_creacion_raw)
        fecha_ultima_revision = parse_fecha_flexible(fecha_ultima_revision_raw)

        if not fecha_creacion:
            fecha_creacion = date.today()

        if not fecha_ultima_revision:
            fecha_ultima_revision = fecha_creacion

        estado  = (request.form.get('estado') or '').strip()
        control_cambios = (request.form.get('control_cambios') or '').strip()
        observaciones   = (request.form.get('observaciones') or '').strip()

        if not tipo_id or not nombre_documento:
            flash("Tipo de documento y nombre del documento son obligatorios.", "danger")
            return redirect(url_for('docs_new'))

        ultimo = DocMaestroDocumento.query.order_by(DocMaestroDocumento.item.desc()).first()
        next_item = (ultimo.item + 1) if ultimo and ultimo.item else 1

        doc = DocMaestroDocumento(
            item=next_item,
            tipo_id=tipo_id,
            codigo=codigo,
            inicial=inicial,
            tipo_texto=tipo_texto,
            num1=num1,
            num2=num2,
            num3=num3,
            nombre_documento=nombre_documento,
            version=version,
            fecha_creacion=fecha_creacion,
            fecha_ultima_revision=fecha_ultima_revision,
            estado=estado,
            control_cambios=control_cambios,
            observaciones=observaciones
        )

        db.session.add(doc)
        db.session.flush()

        os.makedirs(app.config['UPLOAD_DOCS_DIR'], exist_ok=True)

        fmain = request.files.get('archivo')
        if fmain and fmain.filename:
            orig = secure_filename(fmain.filename).strip()

            if not docs_allowed_file(orig):
                db.session.rollback()
                flash(f"Tipo de archivo no permitido: {orig}. Solo PDF, Word, Excel.", "danger")
                return redirect(url_for('docs_new'))

            store_name = docs_unique_store_name(orig)
            path = os.path.join(app.config['UPLOAD_DOCS_DIR'], store_name)
            fmain.save(path)

            doc.filename = store_name
            doc.original_name = orig
            doc.mime = fmain.mimetype or 'application/octet-stream'
            doc.size = os.path.getsize(path)

        db.session.commit()
        flash("Documento guardado correctamente.", "success")
        return redirect(url_for('docs_matriz'))

    html = """
    <div class="docsadd-shell">

      <div class="docsadd-header-card">
        <div class="docsadd-header-overlay">
          <div class="docsadd-header-text">
            <h3 class="docsadd-title m-0">Agregar Documento al Listado Maestro</h3>
            <div class="docsadd-subtitle">
              Registro y control de documentos del SGSI
            </div>
          </div>
        </div>
      </div>

      <div class="docsadd-header-actions">
        <a href="{{ url_for('docs_matriz') }}"
           class="btn rounded-pill px-5 fw-bold docsadd-back-btn">
          ⬅ Volver a la Matriz
        </a>
      </div>

      <div class="docsadd-form-card">
        <div class="docsadd-form-card-body">
          <form method="post" enctype="multipart/form-data">

            <div class="row g-3">

              <div class="col-md-4">
                <label class="form-label">Tipo de documento</label>
                <select name="tipo_id" class="form-select" required>
                  <option value="">-- Seleccione --</option>
                  {% for t in tipos %}
                    <option value="{{ t.id }}">{{ t.nombre }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Código</label>
                <input type="text" name="codigo" class="form-control">
              </div>

              <div class="col-md-4">
                <label class="form-label">Inicial</label>
                <input type="text" name="inicial" class="form-control">
              </div>

              <div class="col-md-4">
                <label class="form-label">Tipo</label>
                <input type="text" name="tipo_texto" class="form-control">
              </div>

              <div class="col-md-2">
                <label class="form-label">#1</label>
                <input type="number" name="num1" class="form-control">
              </div>

              <div class="col-md-2">
                <label class="form-label">#2</label>
                <input type="number" name="num2" class="form-control">
              </div>

              <div class="col-md-2">
                <label class="form-label">#3</label>
                <input type="number" name="num3" class="form-control">
              </div>

              <div class="col-md-6">
                <label class="form-label">Nombre del documento</label>
                <input type="text" name="nombre_documento" class="form-control" required>
              </div>

              <div class="col-md-6">
                <label class="form-label">Documento principal (PDF, Word, Excel)</label>
                <input type="file" name="archivo" class="form-control"
                       accept=".pdf,.doc,.docx,.xls,.xlsx">
              </div>

              <div class="col-md-2">
                <label class="form-label">Versión</label>
                <input type="number" name="version" class="form-control" min="1" value="1">
              </div>

              <div class="col-md-3">
                <label class="form-label">Fecha creación documento</label>
                <input type="date" name="fecha_creacion" class="form-control">
              </div>

              <div class="col-md-3">
                <label class="form-label">Fecha última revisión</label>
                <input type="date" name="fecha_ultima_revision" class="form-control">
              </div>

              <div class="col-md-3">
                <label class="form-label">Estado</label>
                <select name="estado" class="form-select">
                  <option value="">-- Seleccione --</option>
                  <option value="Vigente">Vigente</option>
                  <option value="Versión obsoleta">Versión obsoleta</option>
                </select>
              </div>

              <div class="col-md-12">
                <label class="form-label">Control de cambios</label>
                <textarea name="control_cambios" class="form-control" rows="2"></textarea>
              </div>

              <div class="col-md-12">
                <label class="form-label">Observaciones</label>
                <textarea name="observaciones" class="form-control" rows="2"></textarea>
              </div>

            </div>

            <div class="docsadd-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar
              </button>
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

      .docsadd-shell{
        width:96%;
        max-width:1450px;
        margin:10px auto 24px auto;
      }

      .docsadd-header-card{
        background:
          linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.24);
        color:#ffffff;
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .docsadd-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 26%),
          repeating-linear-gradient(
            135deg,
            rgba(255,255,255,.05) 0px,
            rgba(255,255,255,.05) 1px,
            transparent 1px,
            transparent 15px
          );
      }

      .docsadd-header-overlay{
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

      .docsadd-header-overlay::before{
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
        font-size:1.5rem;
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .docsadd-header-text::before{
        content:"SGSI · Agregar Documento";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
      }

      .docsadd-title{
        color:#ffffff!important;
        font-weight:950;
        font-size:1.32rem;
        margin:0 !important;
      }

      .docsadd-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
      }

      .docsadd-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px;
      }

      .docsadd-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .docsadd-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .docsadd-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .docsadd-form-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .docsadd-form-card-body{
        padding:16px 18px;
      }

      .docsadd-form-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .docsadd-form-card .form-control,
      .docsadd-form-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:37px;
        font-size:.80rem;
        background:#f8fafc;
        box-shadow:none;
      }

      .docsadd-form-card textarea.form-control{
        min-height:70px;
        resize:vertical;
      }

      .docsadd-form-card .form-control:focus,
      .docsadd-form-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .18rem rgba(63,134,214,.18);
      }

      .docsadd-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin-top:18px;
      }

      .docsadd-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 24px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .docsadd-bottom-actions .btn-primary,
      .docsadd-bottom-actions .btn-success{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .docsadd-bottom-actions .btn-danger{
        border:none;
        background:linear-gradient(135deg,#b91c1c,#ef4444);
        color:#fff;
      }

      @media (max-width:992px){
        .docsadd-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .docsadd-header-card{
          min-height:88px;
        }

        .docsadd-title{
          font-size:1.2rem;
        }

        .docsadd-form-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .docsadd-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .docsadd-header-overlay::before{
          margin:0;
        }

        .docsadd-header-actions .btn,
        .docsadd-bottom-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(html, tipos=tipos)
    return render_template_string(BASE, content=Markup(inner))


def meses_entre(d_inicio: date, d_fin: date) -> int:
    anios = d_fin.year - d_inicio.year
    meses = d_fin.month - d_inicio.month
    total = anios * 12 + meses
    if d_fin.day < d_inicio.day:
        total -= 1
    return total

def parse_fecha_flexible(value) -> date | None:
    if value is None:
        return None

    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value

    s = str(value).strip()
    if not s or s in ("—", "-", "N/A", "NA", "None", "null"):
        return None

    s = s.replace("T", " ")
    if " " in s:
        s = s.split(" ")[0].strip()

    formatos = ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y")
    for fmt in formatos:
        try:
            return dt.datetime.strptime(s, fmt).date()
        except Exception:
            pass

    return None

def fmt_fecha(value) -> str:
    d = parse_fecha_flexible(value)
    return d.strftime("%Y-%m-%d") if d else "—"

def calcular_estado_revision(doc: 'DocMaestroDocumento', tipo: 'DocTipoDocumento'):
    d_rev = parse_fecha_flexible(doc.fecha_ultima_revision)
    if not d_rev:
        d_rev = parse_fecha_flexible(doc.fecha_creacion)

    if not d_rev:
        return {"texto": "Sin fecha", "badge": "bg-secondary"}

    min_meses = getattr(tipo, 'min_meses_revision', 0) or 0
    if min_meses <= 0:
        return {"texto": "Sin config", "badge": "bg-secondary"}

    hoy = date.today()
    diff_meses = meses_entre(d_rev, hoy)
    if diff_meses < 0:
        diff_meses = 0

    if diff_meses >= min_meses:
        return {"texto": "Vencido", "badge": "bg-danger"}

    if diff_meses == (min_meses - 1):
        return {"texto": "Cercano", "badge": "bg-warning text-dark"}

    return {"texto": "Adecuado", "badge": "bg-success"}


# =========================
# Matriz de documentos
# =========================
@app.route('/docs/matriz')
@login_required
def docs_matriz():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Listado Maestro de Documentos"):
            flash("No tiene permiso para ver el listado maestro de documentos.", "danger")
            return redirect(url_for('menu'))
        read_only = False

    filtro_estado_revision = (request.args.get('estado_revision') or '').strip()
    filtro_estado = (request.args.get('estado') or '').strip()
    filtro_tipo_documento = (request.args.get('tipo_documento') or '').strip()

    query = (
        DocMaestroDocumento.query
        .options(
            selectinload(DocMaestroDocumento.evidencias),
            selectinload(DocMaestroDocumento.tipo)
        )
    )

    if filtro_estado:
        query = query.filter(DocMaestroDocumento.estado == filtro_estado)

    if filtro_tipo_documento:
        query = query.filter(
            DocMaestroDocumento.tipo.has(nombre=filtro_tipo_documento)
        )

    query = query.order_by(DocMaestroDocumento.item.asc())
    items = query.all()

    if filtro_estado_revision:
        items = [
            doc for doc in items
            if (
                calcular_estado_revision(doc, doc.tipo)
                and (calcular_estado_revision(doc, doc.tipo).get('texto') or '').strip().lower() == filtro_estado_revision.lower()
            )
        ]

    opciones_estado = [
        x[0] for x in db.session.query(DocMaestroDocumento.estado)
        .filter(DocMaestroDocumento.estado.isnot(None))
        .filter(DocMaestroDocumento.estado != '')
        .distinct()
        .order_by(DocMaestroDocumento.estado.asc())
        .all()
    ]

    opciones_tipo_documento = sorted({
        doc.tipo.nombre.strip()
        for doc in (
            DocMaestroDocumento.query
            .options(selectinload(DocMaestroDocumento.tipo))
            .all()
        )
        if doc.tipo and doc.tipo.nombre and doc.tipo.nombre.strip()
    })

    estados_revision_detectados = []
    for doc in (
        DocMaestroDocumento.query
        .options(selectinload(DocMaestroDocumento.tipo))
        .all()
    ):
        est = calcular_estado_revision(doc, doc.tipo)
        texto = (est.get('texto') or '').strip() if est else ''
        if texto and texto not in estados_revision_detectados:
            estados_revision_detectados.append(texto)

    opciones_estado_revision = sorted(estados_revision_detectados)
    total_filtrados = len(items)
    total_general = DocMaestroDocumento.query.count()

    html = """
    <div class="docmat-shell">

      <div class="docmat-header-card">
        <div class="docmat-header-overlay">
          <div class="docmat-header-text">
            <h3 class="docmat-title m-0">Listado Maestro de Documentos</h3>
            <div class="docmat-subtitle">
              Visualización resumida del listado maestro documental del SGSI
            </div>
          </div>
        </div>
      </div>

      <div class="docmat-header-actions">

        {% if not read_only %}
          <a href="{{ url_for('docs_new') }}"
             class="btn btn-primary rounded-pill px-4 fw-bold">
            ➕ Agregar Documento
          </a>

          <a href="{{ url_for('docs_tipos_config') }}"
             class="btn btn-primary rounded-pill px-4 fw-bold">
            🔩 Configurar Tipos de Documentos
          </a>
        {% else %}
          <button class="btn btn-secondary rounded-pill px-4 fw-bold" disabled>
            ➕ Agregar Documento
          </button>

          <button class="btn btn-secondary rounded-pill px-4 fw-bold" disabled>
            🔩 Configurar Tipos de Documentos
          </button>
        {% endif %}
      </div>

      <div class="docmat-filter-card">
        <div class="docmat-filter-body">
          <form method="get" action="{{ url_for('docs_matriz') }}">
            <div class="row g-2 align-items-end">

              <div class="col-md-3">
                <label class="form-label fw-bold">Estado revisión</label>
                <select name="estado_revision" class="form-select rounded-3">
                  <option value="">Todos</option>
                  {% for op in opciones_estado_revision %}
                    <option value="{{ op }}" {% if filtro_estado_revision == op %}selected{% endif %}>{{ op }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label fw-bold">Estado</label>
                <select name="estado" class="form-select rounded-3">
                  <option value="">Todos</option>
                  {% for op in opciones_estado %}
                    <option value="{{ op }}" {% if filtro_estado == op %}selected{% endif %}>{{ op }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label fw-bold">Tipo de documento</label>
                <select name="tipo_documento" class="form-select rounded-3">
                  <option value="">Todos</option>
                  {% for op in opciones_tipo_documento %}
                    <option value="{{ op }}" {% if filtro_tipo_documento == op %}selected{% endif %}>{{ op }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-3">
                <div class="d-flex gap-2 flex-wrap">
                  <button type="submit" class="btn btn-primary rounded-pill px-4 fw-bold">Filtrar</button>
                  <a href="{{ url_for('docs_matriz') }}" class="btn btn-secondary rounded-pill px-4 fw-bold">Limpiar</a>
                </div>
              </div>

            </div>
          </form>
        </div>
      </div>

      <div class="docmat-card">
        <div class="docmat-topbar">
          <div>
            <h5 class="docmat-top-title mb-1">Resumen de documentos</h5>
            <div class="docmat-top-note">
              La matriz muestra los campos principales. Para consultar toda la información usa el botón <strong>Ver detalle</strong>.
            </div>
          </div>
          <div class="docmat-counter-badge">
            Registros filtrados: {{ total_filtrados }} | Total general: {{ total_general }}
          </div>
        </div>

        <div class="docmat-card-body">
          <div class="docmat-table-wrap">
            <div class="table-responsive">
              <table class="table table-bordered table-hover align-middle docmat-table mb-0">
                <colgroup>
                  <col style="width: 6%;">
                  <col style="width: 15%;">
                  <col style="width: 11%;">
                  <col style="width: 30%;">
                  <col style="width: 7%;">
                  <col style="width: 11%;">
                  <col style="width: 9%;">
                  <col style="width: 9%;">
                  <col style="width: 14%;">
                </colgroup>

                <thead>
                  <tr>
                    <th>Ítem</th>
                    <th>Tipo de documento</th>
                    <th>Código</th>
                    <th>Nombre del documento</th>
                    <th>Versión</th>
                    <th>Última revisión</th>
                    <th>Estado revisión</th>
                    <th>Estado</th>
                    <th class="docmat-col-acciones">Acciones</th>
                  </tr>
                </thead>

                <tbody>
                  {% for doc in items %}
                    {% set tipo = doc.tipo %}
                    {% set est = calcular_estado_revision(doc, tipo) %}
                    <tr>
                      <td class="text-center">{{ doc.item or '—' }}</td>
                      <td>{{ tipo.nombre if tipo else '—' }}</td>
                      <td>{{ doc.codigo or '—' }}</td>
                      <td class="docmat-cell-main">
                        <div class="docmat-main-text">{{ doc.nombre_documento or '—' }}</div>
                      </td>
                      <td class="text-center">{{ doc.version or '—' }}</td>
                      <td class="text-center">{{ fmt_fecha(doc.fecha_ultima_revision) }}</td>

                      <td class="text-center">
                        {% if est and est.get('badge') and est.get('texto') %}
                          <span class="badge {{ est.get('badge') }}">{{ est.get('texto') }}</span>
                        {% else %}
                          <span class="badge bg-secondary">—</span>
                        {% endif %}
                      </td>

                      <td class="text-center">{{ doc.estado or '—' }}</td>

                      <td class="text-center docmat-col-acciones">
                        <div class="docmat-actions-wrap">
                          <a href="{{ url_for('docs_detalle', id=doc.id) }}"
                             class="btn btn-info btn-sm rounded-pill docmat-btn-action fw-bold text-white">
                            Ver detalle
                          </a>

                          {% if not read_only %}
                            <a href="{{ url_for('docs_edit', id=doc.id) }}"
                               class="btn btn-warning btn-sm rounded-pill docmat-btn-action fw-bold">
                              Editar
                            </a>

                            <a href="{{ url_for('docs_delete', id=doc.id) }}"
                               class="btn btn-danger btn-sm rounded-pill docmat-btn-action fw-bold"
                               onclick="return confirm('¿Eliminar este documento del listado maestro?');">
                              Eliminar
                            </a>
                          {% else %}
                            <span class="badge bg-secondary docmat-badge-readonly">Solo lectura</span>
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

      .docmat-shell{
        width:96%;
        max-width:1650px;
        margin:10px auto 24px auto;
      }

      .docmat-header-card{
        background:linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.24);
        color:#fff;
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .docmat-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 26%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 15px);
      }

      .docmat-header-overlay{
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

      .docmat-header-overlay::before{
        content:"📄";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:#fff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.5rem;
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .docmat-header-text::before{
        content:"SGSI · Matriz Documental";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
      }

      .docmat-title{
        color:#fff !important;
        font-weight:950;
        font-size:1.32rem;
        margin:0 !important;
      }

      .docmat-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
      }

      .docmat-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px;
      }

      .docmat-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .docmat-back-btn{
        background:#fff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .docmat-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .docmat-filter-card,
      .docmat-card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:visible;
      }

      .docmat-filter-card{
        margin-bottom:14px;
      }

      .docmat-filter-body{
        padding:14px 16px;
      }

      .docmat-filter-body .form-label{
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
        font-weight:800;
      }

      .docmat-filter-body .form-select,
      .docmat-filter-body .form-control{
        min-height:36px;
        height:36px;
        font-size:.80rem;
        border:1px solid #d9e3f0;
        border-radius:9px;
        background:#f8fafc;
        box-shadow:none;
      }

      .docmat-filter-body .btn{
        border-radius:10px !important;
        min-height:36px;
        padding:7px 18px !important;
        font-size:.80rem;
        font-weight:900;
      }

      .docmat-filter-body .form-select:focus,
      .docmat-filter-body .form-control:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .18rem rgba(63,134,214,.18);
      }

      .docmat-topbar{
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:12px;
        padding:14px 16px 0 16px;
        flex-wrap:wrap;
      }

      .docmat-top-title{
        color:#0f172a;
        font-weight:950;
        font-size:.94rem;
      }

      .docmat-top-note{
        color:#475569;
        font-size:.78rem;
        margin-top:3px;
      }

      .docmat-counter-badge{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        color:#fff;
        font-weight:900;
        border-radius:999px;
        padding:7px 14px;
        font-size:.78rem;
        box-shadow:0 8px 16px rgba(15,23,42,.16);
      }

      .docmat-card-body{
        padding:12px 16px 16px 16px;
      }

      .docmat-table-wrap{
        max-height:70vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#fff;
      }

      .docmat-table{
        min-width:1500px;
        table-layout:fixed;
        margin-bottom:0;
        border-collapse:separate;
        border-spacing:0;
      }

      .docmat-table thead th{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#fff;
        font-weight:900;
        text-align:center;
        vertical-align:middle;
        border-right:1px solid rgba(255,255,255,.28);
      }

      .docmat-table th,
      .docmat-table td{
        vertical-align:top;
        font-size:.68rem;
        padding:9px 8px;
        white-space:normal;
        word-break:break-word;
        overflow-wrap:anywhere;
      }

      .docmat-table td{
        color:#101827;
        border-right:1px solid #dce6f3;
        border-bottom:1px solid #dce6f3;
        background:#fff;
      }

      .docmat-table tbody tr:nth-child(even) td{
        background:#f8fbff;
      }

      .docmat-table tbody tr:hover td{
        background:#eef6ff;
      }

      .docmat-cell-main .docmat-main-text{
        font-weight:900;
        color:#0f172a;
        line-height:1.35;
      }

      .docmat-col-acciones,
      .docmat-table th.docmat-col-acciones,
      .docmat-table td.docmat-col-acciones{
        min-width:190px !important;
        width:190px !important;
        text-align:center;
        vertical-align:middle;
      }

      .docmat-actions-wrap{
        display:flex;
        flex-direction:column;
        gap:6px;
        align-items:center;
        justify-content:center;
      }

      .docmat-btn-action{
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

      .docmat-badge-readonly{
        font-size:.70rem;
        padding:5px 10px;
        border-radius:999px;
        white-space:nowrap;
        font-weight:900;
      }

      .docmat-table-wrap::-webkit-scrollbar{
        height:11px;
        width:11px;
      }

      .docmat-table-wrap::-webkit-scrollbar-track{
        background:#dbe4f0;
        border-radius:12px;
      }

      .docmat-table-wrap::-webkit-scrollbar-thumb{
        background:linear-gradient(180deg,#5aa3ea,#3f86d6);
        border-radius:12px;
        border:2px solid #dbe4f0;
      }

      .docmat-table-wrap{
        scrollbar-width:thin;
        scrollbar-color:#3f86d6 #dbe4f0;
      }

      @media (max-width:992px){
        .docmat-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .docmat-header-card{
          min-height:88px;
        }

        .docmat-title{
          font-size:1.2rem;
        }

        .docmat-filter-body,
        .docmat-card-body{
          padding:12px;
        }

        .docmat-topbar{
          padding:12px 14px 0 14px;
        }
      }

      @media (max-width:768px){
        .docmat-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .docmat-header-overlay::before{
          margin:0;
        }

        .docmat-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(
        html,
        items=items,
        read_only=read_only,
        calcular_estado_revision=calcular_estado_revision,
        fmt_fecha=fmt_fecha,
        opciones_estado_revision=opciones_estado_revision,
        opciones_estado=opciones_estado,
        opciones_tipo_documento=opciones_tipo_documento,
        filtro_estado_revision=filtro_estado_revision,
        filtro_estado=filtro_estado,
        filtro_tipo_documento=filtro_tipo_documento,
        total_filtrados=total_filtrados,
        total_general=total_general
    )
    return render_template_string(BASE, content=Markup(inner))


# =========================
# Archivo real documento principal
# =========================
@app.route('/docs/file/<int:id>')
@login_required
def docs_file(id):
    doc = DocMaestroDocumento.query.get_or_404(id)

    if not doc.filename:
        abort(404)

    path = os.path.join(app.config['UPLOAD_DOCS_DIR'], doc.filename)
    if not os.path.isfile(path):
        abort(404)

    return send_file(
        path,
        mimetype=doc.mime or 'application/octet-stream',
        as_attachment=False,
        download_name=doc.original_name or doc.filename,
        conditional=True
    )


# =========================
# Detalle documento maestro
# =========================
@app.route('/docs/detalle/<int:id>')
@login_required
def docs_detalle(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Listado Maestro de Documentos"):
            flash("No tiene permiso para ver el detalle del documento.", "danger")
            return redirect(url_for('docs_matriz'))
        read_only = False

    doc = (
        DocMaestroDocumento.query
        .options(selectinload(DocMaestroDocumento.evidencias), selectinload(DocMaestroDocumento.tipo))
        .get_or_404(id)
    )

    tipo = doc.tipo
    est = calcular_estado_revision(doc, tipo)

    html = """
    <div class="docdet-shell">

      <div class="docdet-header-card">
        <div class="docdet-header-overlay">
          <div class="docdet-header-text">
            <h3 class="docdet-title m-0">Detalle del Documento Maestro</h3>
            <div class="docdet-subtitle">
              Consulta completa del registro en modo solo lectura
            </div>
          </div>
        </div>
      </div>

      <div class="docdet-header-actions">
        <a href="{{ url_for('docs_matriz') }}"
           class="btn rounded-pill px-4 fw-bold docdet-back-btn">
          ⬅ Volver a la Matriz
        </a>

        {% if not read_only %}
          <a href="{{ url_for('docs_edit', id=doc.id) }}"
             class="btn btn-warning rounded-pill px-4 fw-bold">
            Editar registro
          </a>
        {% endif %}
      </div>

      <div class="docdet-card">
        <div class="docdet-card-body">

          <div class="docdet-section">
            <div class="docdet-section-title">Información principal</div>
            <div class="row g-3">
              <div class="col-md-2">
                <div class="docdet-field">
                  <div class="docdet-label">Ítem</div>
                  <div class="docdet-value">{{ doc.item or '—' }}</div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="docdet-field">
                  <div class="docdet-label">Tipo de documento</div>
                  <div class="docdet-value">{{ tipo.nombre if tipo else '—' }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="docdet-field">
                  <div class="docdet-label">Código</div>
                  <div class="docdet-value">{{ doc.codigo or '—' }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="docdet-field">
                  <div class="docdet-label">Inicial</div>
                  <div class="docdet-value">{{ doc.inicial or '—' }}</div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="docdet-field">
                  <div class="docdet-label">Tipo</div>
                  <div class="docdet-value">{{ doc.tipo_texto or '—' }}</div>
                </div>
              </div>

              <div class="col-md-2">
                <div class="docdet-field">
                  <div class="docdet-label">#1</div>
                  <div class="docdet-value">{{ doc.num1 if doc.num1 is not none else '—' }}</div>
                </div>
              </div>

              <div class="col-md-2">
                <div class="docdet-field">
                  <div class="docdet-label">#2</div>
                  <div class="docdet-value">{{ doc.num2 if doc.num2 is not none else '—' }}</div>
                </div>
              </div>

              <div class="col-md-2">
                <div class="docdet-field">
                  <div class="docdet-label">#3</div>
                  <div class="docdet-value">{{ doc.num3 if doc.num3 is not none else '—' }}</div>
                </div>
              </div>

              <div class="col-md-12">
                <div class="docdet-field">
                  <div class="docdet-label">Nombre del documento</div>
                  <div class="docdet-value docdet-value-lg">{{ doc.nombre_documento or '—' }}</div>
                </div>
              </div>
            </div>
          </div>

          <div class="docdet-section">
            <div class="docdet-section-title">Control documental</div>

            <div class="row g-3 mb-1">
              <div class="col-md-2">
                <div class="docdet-field docdet-field-mini">
                  <div class="docdet-label">Versión</div>
                  <div class="docdet-value docdet-value-compact">{{ doc.version or '—' }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="docdet-field docdet-field-mini">
                  <div class="docdet-label">Fecha creación</div>
                  <div class="docdet-value docdet-value-compact">{{ fmt_fecha(doc.fecha_creacion) }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="docdet-field docdet-field-mini">
                  <div class="docdet-label">Última revisión</div>
                  <div class="docdet-value docdet-value-compact">{{ fmt_fecha(doc.fecha_ultima_revision) }}</div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="docdet-field docdet-field-mini">
                  <div class="docdet-label">Tipo documental</div>
                  <div class="docdet-value docdet-value-compact">{{ tipo.nombre if tipo else '—' }}</div>
                </div>
              </div>
            </div>

            <div class="row g-3 justify-content-center">
              <div class="col-md-3 col-lg-3">
                <div class="docdet-field docdet-field-status">
                  <div class="docdet-label">Estado</div>
                  <div class="docdet-value docdet-value-compact">{{ doc.estado or '—' }}</div>
                </div>
              </div>

              <div class="col-md-3 col-lg-3">
                <div class="docdet-field docdet-field-status">
                  <div class="docdet-label">Estado revisión</div>
                  <div class="docdet-value docdet-value-compact">
                    {% if est and est.get('badge') and est.get('texto') %}
                      <span class="badge {{ est.get('badge') }}">{{ est.get('texto') }}</span>
                    {% else %}
                      <span class="badge bg-secondary">—</span>
                    {% endif %}
                  </div>
                </div>
              </div>
            </div>

            <div class="row g-3 mt-1">
              <div class="col-md-12">
                <div class="docdet-field">
                  <div class="docdet-label">Control de cambios</div>
                  <div class="docdet-value">{{ doc.control_cambios or '—' }}</div>
                </div>
              </div>

              <div class="col-md-12">
                <div class="docdet-field">
                  <div class="docdet-label">Observaciones</div>
                  <div class="docdet-value">{{ doc.observaciones or '—' }}</div>
                </div>
              </div>
            </div>
          </div>

          <div class="docdet-section">
            <div class="docdet-section-title">Archivos asociados</div>

            {% if doc.filename %}
              <div class="docdet-ev-grid mb-3">
                <div class="docdet-file-card">
                  <div class="docdet-file-left">
                    <div class="docdet-file-icon">DOC</div>
                    <div class="docdet-file-meta">
                      <div class="docdet-file-label">Documento principal</div>
                      <a href="{{ url_for('docs_file', id=doc.id) }}"
                         target="_blank"
                         class="docdet-file-name">
                        {{ doc.original_name or doc.filename }}
                      </a>
                      <div class="docdet-file-size">
                        {{ fmt_kb(doc.size) }}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            {% endif %}

            {% if doc.evidencias %}
              <div class="docdet-ev-grid">
                {% for ev in doc.evidencias %}
                  <div class="docdet-file-card">
                    <div class="docdet-file-left">
                      <div class="docdet-file-icon">PDF</div>
                      <div class="docdet-file-meta">
                        <div class="docdet-file-label">Evidencia</div>
                        <a href="{{ url_for('docs_evidencia_view', evi_id=ev.id) }}"
                           class="docdet-file-name">
                          {{ ev.original_name or ev.filename }}
                        </a>
                        <div class="docdet-file-size">{{ fmt_kb(ev.size) }}</div>
                      </div>
                    </div>
                  </div>
                {% endfor %}
              </div>
            {% elif not doc.filename %}
              <div class="docdet-empty-box">
                No hay archivos asociados para este documento.
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

      .docdet-shell{
        width:96%;
        max-width:1250px;
        margin:10px auto 24px auto;
      }

      .docdet-header-card{
        background:linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.24);
        color:#fff;
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .docdet-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 26%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 15px);
      }

      .docdet-header-overlay{
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

      .docdet-header-overlay::before{
        content:"📄";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:#fff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.5rem;
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .docdet-header-text::before{
        content:"SGSI · Detalle Documental";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
      }

      .docdet-title{
        color:#fff !important;
        font-weight:950;
        font-size:1.32rem;
        margin:0 !important;
      }

      .docdet-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
      }

      .docdet-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px;
      }

      .docdet-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .docdet-back-btn{
        background:#fff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .docdet-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .docdet-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        overflow:hidden;
        border:1px solid rgba(219,230,244,.9);
      }

      .docdet-card-body{
        padding:16px 18px;
      }

      .docdet-section{
        margin-bottom:14px;
        background:#fff;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:8px 7px;
        box-shadow:0 8px 18px rgba(15,23,42,.08);
      }

      .docdet-section:last-child{
        margin-bottom:0;
      }

      .docdet-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:0 0 12px 0;
      }

      .docdet-field{
        background:linear-gradient(180deg,#f8fbff 0%,#ffffff 100%);
        border:1px solid #dbe6f4;
        border-radius:14px;
        padding:12px;
        height:100%;
        display:flex;
        flex-direction:column;
        justify-content:flex-start;
      }

      .docdet-field-mini{
        min-height:76px;
      }

      .docdet-field-status{
        min-height:44px;
        max-width:220px;
        margin:0 auto;
        padding:10px 12px;
        justify-content:center;
        align-items:center;
        text-align:center;
      }

      .docdet-label{
        font-size:.70rem;
        font-weight:900;
        text-transform:uppercase;
        letter-spacing:.35px;
        color:#0b4a8f;
        margin-bottom:6px;
      }

      .docdet-value{
        color:#101827;
        font-size:.82rem;
        line-height:1.38;
        word-break:break-word;
      }

      .docdet-value-lg{
        font-size:.90rem;
        font-weight:900;
        color:#0f172a;
        line-height:1.35;
      }

      .docdet-value-compact{
        font-weight:900;
        font-size:.78rem;
        line-height:1.15;
      }

      .docdet-value .badge,
      .docdet-value-compact .badge{
        font-size:.70rem;
        padding:4px 10px;
        border-radius:999px;
        white-space:nowrap;
        display:inline-block;
        font-weight:900;
      }

      .docdet-section .row.g-3{
        --bs-gutter-x:.8rem;
        --bs-gutter-y:.8rem;
      }

      .docdet-ev-grid{
        display:grid;
        gap:10px;
      }

      .docdet-file-card{
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

      .docdet-file-left{
        display:flex;
        align-items:center;
        gap:7px;
        min-width:0;
      }

      .docdet-file-icon{
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

      .docdet-file-meta{
        min-width:0;
      }

      .docdet-file-label{
        font-size:.70rem;
        color:#475569;
        font-weight:900;
      }

      .docdet-file-name{
        display:block;
        font-size:.78rem;
        font-weight:900;
        color:#1d4ed8;
        text-decoration:none;
        word-break:break-word;
      }

      .docdet-file-name:hover{
        text-decoration:underline;
      }

      .docdet-file-size{
        font-size:.70rem;
        color:#475569;
        margin-top:2px;
      }

      .docdet-empty-box{
        background:rgba(255,255,255,.75);
        border:1px dashed #cfd8e3;
        border-radius:14px;
        padding:8px 7px;
        text-align:center;
        color:#475569;
        font-size:.80rem;
      }

      @media (max-width:992px){
        .docdet-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .docdet-header-card{
          min-height:88px;
        }

        .docdet-title{
          font-size:1.2rem;
        }

        .docdet-card-body{
          padding:8px 7px;
        }

        .docdet-section{
          padding:12px;
        }
      }

      @media (max-width:768px){
        .docdet-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .docdet-header-overlay::before{
          margin:0;
        }

        .docdet-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(
        html,
        doc=doc,
        tipo=tipo,
        est=est,
        read_only=read_only,
        fmt_fecha=fmt_fecha,
        fmt_kb=fmt_kb
    )
    return render_template_string(BASE, content=Markup(inner))

# =========================
# Editar documento
# =========================
@app.route('/docs/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def docs_edit(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede editar registros.", "danger")
        return redirect(url_for('docs_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Listado Maestro de Documentos"):
        flash("No tiene permiso para editar documentos del listado maestro.", "danger")
        return redirect(url_for('docs_matriz'))

    doc = DocMaestroDocumento.query.get_or_404(id)
    tipos = DocTipoDocumento.query.order_by(DocTipoDocumento.nombre.asc()).all()

    if request.method == 'POST':
        tipo_id  = request.form.get('tipo_id', type=int)
        codigo   = (request.form.get('codigo') or '').strip()
        inicial  = (request.form.get('inicial') or '').strip()
        tipo_texto = (request.form.get('tipo_texto') or '').strip()
        num1     = request.form.get('num1', type=int)
        num2     = request.form.get('num2', type=int)
        num3     = request.form.get('num3', type=int)
        nombre_documento = (request.form.get('nombre_documento') or '').strip()
        version  = request.form.get('version', type=int) or 1

        fecha_creacion_raw = (request.form.get('fecha_creacion') or '').strip()
        fecha_ultima_revision_raw = (request.form.get('fecha_ultima_revision') or '').strip()

        fecha_creacion = parse_fecha_flexible(fecha_creacion_raw)
        fecha_ultima_revision = parse_fecha_flexible(fecha_ultima_revision_raw)

        estado = (request.form.get('estado') or '').strip()
        control_cambios = (request.form.get('control_cambios') or '').strip()
        observaciones = (request.form.get('observaciones') or '').strip()

        quitar_archivo = (request.form.get('quitar_archivo') or '').strip() == '1'

        if not tipo_id or not nombre_documento:
            flash("Tipo de documento y nombre del documento son obligatorios.", "danger")
            return redirect(url_for('docs_edit', id=id))

        doc.tipo_id = tipo_id
        doc.codigo = codigo
        doc.inicial = inicial
        doc.tipo_texto = tipo_texto
        doc.num1 = num1
        doc.num2 = num2
        doc.num3 = num3
        doc.nombre_documento = nombre_documento
        doc.version = version
        doc.fecha_creacion = fecha_creacion
        doc.fecha_ultima_revision = fecha_ultima_revision
        doc.estado = estado
        doc.control_cambios = control_cambios
        doc.observaciones = observaciones

        os.makedirs(app.config['UPLOAD_DOCS_DIR'], exist_ok=True)

        if quitar_archivo and doc.filename:
            try:
                ruta_actual = os.path.join(app.config['UPLOAD_DOCS_DIR'], doc.filename)
                if os.path.exists(ruta_actual):
                    os.remove(ruta_actual)
            except Exception:
                pass

            doc.filename = None
            doc.original_name = None
            doc.mime = None
            doc.size = None

        fmain = request.files.get('archivo')
        if fmain and fmain.filename:
            orig = secure_filename(fmain.filename).strip()

            if not docs_allowed_file(orig):
                flash(f"Tipo de archivo no permitido: {orig}. Solo PDF, Word, Excel.", "danger")
                return redirect(url_for('docs_edit', id=id))

            if doc.filename:
                try:
                    ruta_anterior = os.path.join(app.config['UPLOAD_DOCS_DIR'], doc.filename)
                    if os.path.exists(ruta_anterior):
                        os.remove(ruta_anterior)
                except Exception:
                    pass

            store_name = docs_unique_store_name(orig)
            path = os.path.join(app.config['UPLOAD_DOCS_DIR'], store_name)
            fmain.save(path)

            doc.filename = store_name
            doc.original_name = orig
            doc.mime = fmain.mimetype or 'application/octet-stream'
            doc.size = os.path.getsize(path)

        db.session.commit()
        flash("Documento actualizado correctamente.", "success")
        return redirect(url_for('docs_matriz'))

    html = """
    <div class="docsedit-shell">

      <div class="docsedit-header-card">
        <div class="docsedit-header-overlay">
          <div class="docsedit-header-text">
            <h3 class="docsedit-title m-0">Editar Documento del Listado Maestro</h3>
            <div class="docsedit-subtitle">
              Actualización y control del documento registrado
            </div>
          </div>
        </div>
      </div>

      <div class="docsedit-header-actions">
        <a href="{{ url_for('docs_matriz') }}"
           class="btn rounded-pill px-5 fw-bold docsedit-back-btn">
          ⬅ Volver a la Matriz
        </a>
      </div>

      <div class="docsedit-form-card">
        <div class="docsedit-form-card-body">
          <form method="post" enctype="multipart/form-data">

            <div class="row g-3">

              <div class="col-md-4">
                <label class="form-label">Tipo de documento</label>
                <select name="tipo_id" class="form-select" required>
                  <option value="">-- Seleccione --</option>
                  {% for t in tipos %}
                    <option value="{{ t.id }}" {% if doc.tipo_id == t.id %}selected{% endif %}>{{ t.nombre }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Código</label>
                <input type="text" name="codigo" class="form-control" value="{{ doc.codigo or '' }}">
              </div>

              <div class="col-md-4">
                <label class="form-label">Inicial</label>
                <input type="text" name="inicial" class="form-control" value="{{ doc.inicial or '' }}">
              </div>

              <div class="col-md-4">
                <label class="form-label">Tipo</label>
                <input type="text" name="tipo_texto" class="form-control" value="{{ doc.tipo_texto or '' }}">
              </div>

              <div class="col-md-2">
                <label class="form-label">#1</label>
                <input type="number" name="num1" class="form-control" value="{{ doc.num1 if doc.num1 is not none else '' }}">
              </div>

              <div class="col-md-2">
                <label class="form-label">#2</label>
                <input type="number" name="num2" class="form-control" value="{{ doc.num2 if doc.num2 is not none else '' }}">
              </div>

              <div class="col-md-2">
                <label class="form-label">#3</label>
                <input type="number" name="num3" class="form-control" value="{{ doc.num3 if doc.num3 is not none else '' }}">
              </div>

              <div class="col-md-6">
                <label class="form-label">Nombre del documento</label>
                <input type="text" name="nombre_documento" class="form-control" value="{{ doc.nombre_documento or '' }}" required>
              </div>

              <div class="col-md-2">
                <label class="form-label">Versión</label>
                <input type="number" name="version" class="form-control" min="1" value="{{ doc.version or 1 }}">
              </div>

              <div class="col-md-3">
                <label class="form-label">Fecha creación documento</label>
                <input type="date" name="fecha_creacion" class="form-control" value="{{ fmt_fecha(doc.fecha_creacion) if fmt_fecha(doc.fecha_creacion) != '—' else '' }}">
              </div>

              <div class="col-md-3">
                <label class="form-label">Fecha última revisión</label>
                <input type="date" name="fecha_ultima_revision" class="form-control" value="{{ fmt_fecha(doc.fecha_ultima_revision) if fmt_fecha(doc.fecha_ultima_revision) != '—' else '' }}">
              </div>

              <div class="col-md-4">
                <label class="form-label">Estado</label>
                <select name="estado" class="form-select">
                  <option value="">-- Seleccione --</option>
                  <option value="Vigente" {% if doc.estado == 'Vigente' %}selected{% endif %}>Vigente</option>
                  <option value="Versión obsoleta" {% if doc.estado == 'Versión obsoleta' %}selected{% endif %}>Versión obsoleta</option>
                </select>
              </div>

              <div class="col-md-12">
                <label class="form-label">Control de cambios</label>
                <textarea name="control_cambios" class="form-control" rows="2">{{ doc.control_cambios or '' }}</textarea>
              </div>

              <div class="col-md-12">
                <label class="form-label">Observaciones</label>
                <textarea name="observaciones" class="form-control" rows="2">{{ doc.observaciones or '' }}</textarea>
              </div>

              <div class="col-md-12">
                <label class="form-label">Reemplazar archivo principal (PDF, Word, Excel)</label>
                <input type="file" name="archivo" class="form-control" accept=".pdf,.doc,.docx,.xls,.xlsx">
              </div>

              <div class="col-md-12">
                <div class="docsedit-file-box">
                  <div><strong>Archivo actual:</strong>
                    {% if doc.original_name %}
                      {{ doc.original_name }}{% if doc.size %} ({{ fmt_kb(doc.size) }}){% endif %}
                    {% else %}
                      Sin archivo cargado
                    {% endif %}
                  </div>

                  {% if doc.original_name %}
                    <div class="form-check mt-2">
                      <input class="form-check-input" type="checkbox" name="quitar_archivo" id="quitar_archivo" value="1">
                      <label class="form-check-label" for="quitar_archivo">
                        Quitar archivo actual
                      </label>
                    </div>
                  {% endif %}
                </div>
              </div>

            </div>

            <div class="docsedit-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar cambios
              </button>
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

      .docsedit-shell{
        width:96%;
        max-width:1450px;
        margin:10px auto 24px auto;
      }

      /* =========================
         HERO SGSI
      ========================== */
      .docsedit-header-card{
        background:
          linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.24);
        color:#ffffff;
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .docsedit-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 26%),
          repeating-linear-gradient(
            135deg,
            rgba(255,255,255,.05) 0px,
            rgba(255,255,255,.05) 1px,
            transparent 1px,
            transparent 15px
          );
      }

      .docsedit-header-overlay{
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

      .docsedit-header-overlay::before{
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
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .docsedit-header-text::before{
        content:"SGSI · Edición Documental";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
      }

      .docsedit-title{
        color:#ffffff!important;
        font-weight:950;
        font-size:1.32rem;
        margin:0 !important;
      }

      .docsedit-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
      }

      /* =========================
         BOTONES HEADER
      ========================== */
      .docsedit-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px;
      }

      .docsedit-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .docsedit-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .docsedit-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         FORM CARD
      ========================== */
      .docsedit-form-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .docsedit-form-card-body{
        padding:16px 18px;
      }

      .docsedit-form-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .docsedit-form-card .form-control,
      .docsedit-form-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:37px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .docsedit-form-card textarea.form-control{
        min-height:80px;
      }

      .docsedit-form-card .form-control:focus,
      .docsedit-form-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .18rem rgba(63,134,214,.18);
      }

      /* =========================
         FILE BOX
      ========================== */
      .docsedit-file-box{
        border:1px solid #dbe6f4;
        background:linear-gradient(180deg,#ffffff 0%,#f8fbff 100%);
        border-radius:14px;
        padding:12px 14px;
        box-shadow:0 6px 14px rgba(15,23,42,.08);
        font-size:.82rem;
      }

      /* =========================
         BOTONES ABAJO
      ========================== */
      .docsedit-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin-top:18px;
      }

      .docsedit-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 24px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .docsedit-bottom-actions .btn-primary,
      .docsedit-bottom-actions .btn-success{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .docsedit-bottom-actions .btn-danger{
        border:none;
        background:linear-gradient(135deg,#b91c1c,#ef4444);
        color:#fff;
      }

      /* =========================
         RESPONSIVE
      ========================== */
      @media (max-width:992px){
        .docsedit-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .docsedit-header-card{
          min-height:88px;
        }

        .docsedit-title{
          font-size:1.2rem;
        }

        .docsedit-form-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .docsedit-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .docsedit-header-overlay::before{
          margin:0;
        }

        .docsedit-header-actions .btn,
        .docsedit-bottom-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(
        html,
        doc=doc,
        tipos=tipos,
        fmt_fecha=fmt_fecha,
        fmt_kb=fmt_kb
    )
    return render_template_string(BASE, content=Markup(inner))




# ==========================================================================================================================================
#                                                               Fin Módulo de Listado de Doucmentos Maestros
# ==========================================================================================================================================

# ==========================================================================================================================================
#                                                               Módulo Registro de Comunicaciones
# ==========================================================================================================================================

def resumir_com_texto(valor, limite=120):
    if not valor:
        return '—'
    txt = str(valor).strip()
    if len(txt) <= limite:
        return txt
    return txt[:limite].rstrip() + '...'


# =========================
# ENTRADA DIRECTA — Registro de Comunicaciones
# =========================
@app.route('/comunicaciones_menu')
@login_required
def comunicaciones_menu():
    user = User.query.get(session.get('user_id'))

    if user.role not in ('admin', 'auditor') and not verificar_permiso(user, "Registro de Comunicaciones"):
        flash("No tiene permiso para acceder al registro de comunicaciones.", "danger")
        return redirect(url_for('menu'))

    return redirect(url_for('comunicaciones_matriz'))


# =========================
# Agregar / Editar Registro
# =========================
@app.route('/comunicaciones/new', methods=['GET', 'POST'])
@app.route('/comunicaciones/<int:reg_id>/edit', methods=['GET', 'POST'])
@login_required
def comunicaciones_new(reg_id=None):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede agregar registros.", "danger")
        return redirect(url_for('comunicaciones_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Registro de Comunicaciones"):
        flash("No tiene permiso para agregar registro de comunicaciones.", "danger")
        return redirect(url_for('comunicaciones_matriz'))

    registro = MatrizComunicacionRegistro.query.get(reg_id) if reg_id else None

    if request.method == 'POST':
        proceso      = (request.form.get('proceso') or '').strip()
        informacion  = (request.form.get('informacion') or '').strip()
        remitente    = (request.form.get('remitente') or '').strip()
        medio        = (request.form.get('medio') or '').strip()
        frecuencia   = (request.form.get('frecuencia') or '').strip()
        destinatario = (request.form.get('destinatario') or '').strip()
        tipo_com     = (request.form.get('tipo_comunicacion') or '').strip()

        if not all([proceso, informacion, remitente, medio, frecuencia, destinatario, tipo_com]):
            flash("Todos los campos son obligatorios.", "danger")
            return redirect(request.url)

        if not registro:
            registro = MatrizComunicacionRegistro()

        registro.proceso           = proceso
        registro.informacion       = informacion
        registro.remitente         = remitente
        registro.medio             = medio
        registro.frecuencia        = frecuencia
        registro.destinatario      = destinatario
        registro.tipo_comunicacion = tipo_com

        db.session.add(registro)
        db.session.commit()
        flash("Registro de matriz de comunicaciones guardado correctamente.", "success")
        return redirect(url_for('comunicaciones_matriz'))

    html = """
    <div class="com-shell">

      <div class="com-header-card">
        <div class="com-header-overlay">
          <div class="com-header-text">
            <h3 class="com-title m-0">
              {% if registro %}
                Editar Registro de Comunicaciones
              {% else %}
                Agregar Registro de Comunicaciones
              {% endif %}
            </h3>
            <div class="com-subtitle">
              Gestión de comunicaciones internas y externas del SGSI
            </div>
          </div>
        </div>
      </div>

      <div class="com-header-actions">
        <a href="{{ url_for('comunicaciones_matriz') }}"
           class="btn rounded-pill px-4 fw-bold com-back-btn">
          ⬅ Volver a la Matriz
        </a>

      </div>

      <div class="com-card">
        <div class="com-card-body">

          <form method="post">
            <div class="row g-3">

              <div class="col-md-4">
                <label class="form-label fw-bold">Proceso</label>
                <input type="text"
                       name="proceso"
                       class="form-control"
                       value="{{ registro.proceso if registro else '' }}"
                       required>
              </div>

              <div class="col-md-8">
                <label class="form-label fw-bold">Información (¿Qué comunica?)</label>
                <textarea name="informacion"
                          class="form-control"
                          rows="2"
                          required>{{ registro.informacion if registro else '' }}</textarea>
              </div>

              <div class="col-md-4">
                <label class="form-label fw-bold">Remitente (¿Quién comunica?)</label>
                <input type="text"
                       name="remitente"
                       class="form-control"
                       value="{{ registro.remitente if registro else '' }}"
                       required>
              </div>

              <div class="col-md-4">
                <label class="form-label fw-bold">Medio (¿Cómo comunica?)</label>
                <input type="text"
                       name="medio"
                       class="form-control"
                       value="{{ registro.medio if registro else '' }}"
                       required>
              </div>

              <div class="col-md-4">
                <label class="form-label fw-bold">Frecuencia (¿Cuándo comunica?)</label>
                <input type="text"
                       name="frecuencia"
                       class="form-control"
                       value="{{ registro.frecuencia if registro else '' }}"
                       required>
              </div>

              <div class="col-md-6">
                <label class="form-label fw-bold">Destinatario (¿A quién comunica?)</label>
                <input type="text"
                       name="destinatario"
                       class="form-control"
                       value="{{ registro.destinatario if registro else '' }}"
                       required>
              </div>

              <div class="col-md-6">
                <label class="form-label fw-bold">Tipo de comunicación</label>
                <select name="tipo_comunicacion" class="form-select" required>
                  <option value="">-- Seleccione --</option>
                  <option value="Interna"
                    {% if registro and registro.tipo_comunicacion == 'Interna' %}selected{% endif %}>
                    Interna
                  </option>
                  <option value="Externa"
                    {% if registro and registro.tipo_comunicacion == 'Externa' %}selected{% endif %}>
                    Externa
                  </option>
                </select>
              </div>

            </div>

            <div class="com-bottom-actions">
              <button type="submit" class="btn btn-success rounded-pill px-4 fw-bold">
                {% if registro %}Guardar Cambios{% else %}Guardar{% endif %}
              </button>

              <a href="{{ url_for('comunicaciones_matriz') }}"
                 class="btn rounded-pill px-4 fw-bold com-cancel-btn">
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

      .com-shell{
        width:96%;
        max-width:1300px;
        margin:10px auto 24px auto;
      }

      .com-header-card{
        background:
          linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.24);
        color:#ffffff;
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .com-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 26%),
          repeating-linear-gradient(
            135deg,
            rgba(255,255,255,.05) 0px,
            rgba(255,255,255,.05) 1px,
            transparent 1px,
            transparent 15px
          );
      }

      .com-header-overlay{
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

      .com-header-overlay::before{
        content:"💬";
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
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .com-header-text::before{
        content:"SGSI · Comunicaciones";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
      }

      .com-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        margin:0 !important;
      }

      .com-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
      }

      .com-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px;
      }

      .com-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .com-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .com-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .com-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .com-card-body{
        padding:16px 18px;
      }

      .com-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .com-card .form-control,
      .com-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:37px;
        font-size:.80rem;
        background:#f8fafc;
        box-shadow:none;
      }

      .com-card textarea{
        min-height:70px;
        resize:vertical;
      }

      .com-card .form-control:focus,
      .com-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .18rem rgba(63,134,214,.18);
      }

      .com-card .row{
        row-gap:10px;
      }

      .com-card .mb-3{
        margin-bottom:.70rem !important;
      }

      .com-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:18px;
        flex-wrap:wrap;
      }

      .com-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 24px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .com-bottom-actions .btn-primary,
      .com-bottom-actions .btn-success{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .com-bottom-actions .btn-danger{
        border:none;
        background:linear-gradient(135deg,#b91c1c,#ef4444);
        color:#fff;
      }

      .com-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .com-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      @media (max-width:992px){
        .com-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .com-header-card{
          min-height:88px;
        }

        .com-title{
          font-size:1.2rem;
        }

        .com-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .com-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .com-header-overlay::before{
          margin:0;
        }

        .com-bottom-actions .btn,
        .com-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(html, registro=registro)
    return render_template_string(BASE, content=Markup(inner))


# =========================
# Matriz
# =========================
@app.route('/comunicaciones_matriz')
@login_required
def comunicaciones_matriz():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Registro de Comunicaciones"):
            flash("No tiene permiso para ver los registros de comunicaciones.", "danger")
            return redirect(url_for('menu'))
        read_only = False

    registros = MatrizComunicacionRegistro.query.order_by(
        MatrizComunicacionRegistro.proceso.asc()
    ).all()

    html = """
    <div class="com-matrix-shell">

      <div class="com-matrix-header-card">
        <div class="com-matrix-header-overlay">
          <div class="com-matrix-header-text">
            <h3 class="com-matrix-title m-0">Registro de Comunicaciones</h3>
            <div class="com-matrix-subtitle">
              Visualización resumida de comunicaciones internas y externas del SGSI
            </div>
          </div>
        </div>
      </div>

      <div class="com-matrix-header-actions">

        {% if not read_only %}
          <a href="{{ url_for('comunicaciones_new') }}"
             class="btn btn-primary rounded-pill px-4 fw-bold">
            ➕ Agregar Registro
          </a>
        {% else %}
          <button class="btn btn-secondary rounded-pill px-4 fw-bold" disabled>
            ➕ Agregar Registro
          </button>
        {% endif %}
      </div>

      <div class="com-matrix-card">
        <div class="com-matrix-topbar">
          <div>
            <h5 class="com-matrix-top-title mb-1">Resumen de registros</h5>
            <div class="com-matrix-top-note">
              La matriz presenta únicamente los campos más importantes. Para revisar el registro completo usa el botón <strong>Ver detalle</strong>.
            </div>
          </div>
          <div class="com-matrix-counter-badge">
            Total registros: {{ registros|length }}
          </div>
        </div>

        <div class="com-matrix-card-body">
          <div class="com-matrix-table-wrap">
            <div class="table-responsive">
              <table class="table table-bordered table-hover align-middle com-matrix-table mb-0">

                <colgroup>
                  <col style="width: 18%;">
                  <col style="width: 28%;">
                  <col style="width: 16%;">
                  <col style="width: 14%;">
                  <col style="width: 10%;">
                  <col style="width: 14%;">
                </colgroup>

                <thead>
                  <tr>
                    <th>Proceso</th>
                    <th>Información</th>
                    <th>Remitente</th>
                    <th>Frecuencia</th>
                    <th>Tipo</th>
                    <th class="com-col-acciones">Acciones</th>
                  </tr>
                </thead>

                <tbody>
                  {% for r in registros %}
                  <tr>
                    <td class="com-cell-main">
                      <div class="com-main-text">{{ r.proceso or '—' }}</div>
                    </td>

                    <td>{{ resumir_com_texto(r.informacion, 150) }}</td>

                    <td>{{ r.remitente or '—' }}</td>

                    <td>{{ r.frecuencia or '—' }}</td>

                    <td class="text-center">
                      {% if r.tipo_comunicacion == 'Interna' %}
                        <span class="badge bg-primary">Interna</span>
                      {% else %}
                        <span class="badge bg-success">Externa</span>
                      {% endif %}
                    </td>

                    <td class="text-center com-col-acciones">
                      <div class="com-actions-wrap">
                        <a href="{{ url_for('comunicaciones_detalle', id=r.id) }}"
                           class="btn btn-info btn-sm rounded-pill com-btn-action fw-bold text-white">
                          Ver detalle
                        </a>

                        {% if not read_only %}
                          <a href="{{ url_for('comunicaciones_new', reg_id=r.id) }}"
                             class="btn btn-warning btn-sm rounded-pill com-btn-action fw-bold">
                            Editar
                          </a>

                          <a href="{{ url_for('comunicaciones_delete', id=r.id) }}"
                             class="btn btn-danger btn-sm rounded-pill com-btn-action fw-bold"
                             onclick="return confirm('¿Eliminar este registro?');">
                            Eliminar
                          </a>
                        {% else %}
                          <span class="badge bg-secondary com-badge-readonly">Solo lectura</span>
                        {% endif %}
                      </div>
                    </td>
                  </tr>
                  {% endfor %}

                  {% if registros|length == 0 %}
                  <tr>
                    <td colspan="6" class="text-center text-muted py-5">
                      Sin registros de comunicaciones
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

      .com-matrix-shell{
        width:96%;
        max-width:1600px;
        margin:10px auto 24px auto;
      }

      /* =========================
         HERO SGSI
      ========================== */
      .com-matrix-header-card{
        background:
          linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.24);
        color:#ffffff;
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .com-matrix-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 26%),
          repeating-linear-gradient(
            135deg,
            rgba(255,255,255,.05) 0px,
            rgba(255,255,255,.05) 1px,
            transparent 1px,
            transparent 15px
          );
      }

      .com-matrix-header-overlay{
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

      .com-matrix-header-overlay::before{
        content:"📊";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:#ffffff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.5rem;
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .com-matrix-header-text::before{
        content:"SGSI · Matriz de Comunicaciones";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
      }

      .com-matrix-title{
        color:#ffffff!important;
        font-weight:950;
        font-size:1.32rem;
        margin:0 !important;
      }

      .com-matrix-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
      }

      /* =========================
         BOTONES HEADER
      ========================== */
      .com-matrix-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px;
      }

      .com-matrix-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .com-matrix-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .com-matrix-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         CARD
      ========================== */
      .com-matrix-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .com-matrix-topbar{
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:12px;
        padding:14px 16px 0 16px;
        flex-wrap:wrap;
      }

      .com-matrix-top-title{
        color:#0f172a;
        font-weight:950;
        font-size:.92rem;
      }

      .com-matrix-top-note{
        color:#475569;
        font-size:.78rem;
        margin-top:3px;
      }

      .com-matrix-counter-badge{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        color:#fff;
        font-weight:900;
        border-radius:999px;
        padding:7px 14px;
        font-size:.78rem;
        box-shadow:0 8px 16px rgba(15,23,42,.16);
      }

      .com-matrix-card-body{
        padding:12px 16px 16px 16px;
      }

      /* =========================
         TABLA SGSI
      ========================== */
      .com-matrix-table-wrap{
        max-height:70vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
      }

      .com-matrix-table{
        min-width:1200px;
        table-layout:fixed;
        margin-bottom:0;
      }

      .com-matrix-table thead th{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff;
        font-weight:900;
        text-align:center;
        vertical-align:middle;
      }

      .com-matrix-table th,
      .com-matrix-table td{
        vertical-align:top;
        font-size:.78rem;
        padding:9px 8px;
        white-space:normal;
        word-break:break-word;
      }

      .com-matrix-table tbody tr:nth-child(even){
        background:#f8fbff;
      }

      .com-matrix-table tbody tr:hover{
        background:#eef6ff;
      }

      .com-cell-main .com-main-text{
        font-weight:900;
        color:#0f172a;
      }

      /* =========================
         ACCIONES
      ========================== */
      .com-col-acciones{
        min-width:180px !important;
        width:180px !important;
        text-align:center;
      }

      .com-actions-wrap{
        display:flex;
        flex-direction:column;
        gap:6px;
        align-items:center;
        justify-content:center;
      }

      .com-btn-action{
        min-width:105px;
        max-width:120px;
        padding:4px 12px !important;
        font-size:.64rem !important;
        font-weight:900;
        border-radius:999px !important;
      }

      .com-badge-readonly{
        font-size:.70rem;
        padding:5px 10px;
        border-radius:999px;
        font-weight:900;
      }

      /* =========================
         RESPONSIVE
      ========================== */
      @media (max-width:992px){
        .com-matrix-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .com-matrix-header-card{
          min-height:88px;
        }

        .com-matrix-title{
          font-size:1.2rem;
        }

        .com-matrix-card-body{
          padding:12px;
        }

        .com-matrix-topbar{
          padding:12px 14px 0 14px;
        }
      }

      @media (max-width:768px){
        .com-matrix-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .com-matrix-header-overlay::before{
          margin:0;
        }

        .com-matrix-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(
        html,
        registros=registros,
        read_only=read_only,
        resumir_com_texto=resumir_com_texto
    )
    return render_template_string(BASE, content=Markup(inner))


# =========================
# Eliminar documento
# =========================
@app.route('/docs/delete/<int:id>')
@login_required
def docs_delete(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede eliminar registros.", "danger")
        return redirect(url_for('docs_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Listado Maestro de Documentos"):
        flash("No tiene permiso para eliminar documentos del listado maestro.", "danger")
        return redirect(url_for('docs_matriz'))

    doc = DocMaestroDocumento.query.get_or_404(id)

    if getattr(doc, 'evidencias', None):
        for ev in doc.evidencias:
            try:
                if getattr(ev, 'filename', None):
                    ruta_ev = os.path.join(app.config['UPLOAD_DOCS_DIR'], ev.filename)
                    if os.path.exists(ruta_ev):
                        os.remove(ruta_ev)
            except Exception:
                pass
            db.session.delete(ev)

    if doc.filename:
        try:
            ruta = os.path.join(app.config['UPLOAD_DOCS_DIR'], doc.filename)
            if os.path.exists(ruta):
                os.remove(ruta)
        except Exception:
            pass

    db.session.delete(doc)
    db.session.commit()

    flash("Documento eliminado correctamente.", "success")
    return redirect(url_for('docs_matriz'))


# =========================
# Detalle registro comunicaciones
# =========================
@app.route('/comunicaciones/detalle/<int:id>')
@login_required
def comunicaciones_detalle(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Registro de Comunicaciones"):
            flash("No tiene permiso para ver el detalle del registro.", "danger")
            return redirect(url_for('comunicaciones_matriz'))
        read_only = False

    r = MatrizComunicacionRegistro.query.get_or_404(id)

    html = """
    <div class="comdet-shell">

      <div class="comdet-header-card">
        <div class="comdet-header-overlay">
          <div class="comdet-header-text">
            <h3 class="comdet-title m-0">Detalle del Registro de Comunicaciones</h3>
            <div class="comdet-subtitle">
              Consulta completa del registro en modo solo lectura
            </div>
          </div>
        </div>
      </div>

      <div class="comdet-header-actions">
        <a href="{{ url_for('comunicaciones_matriz') }}"
           class="btn rounded-pill px-4 fw-bold comdet-back-btn">
          ⬅ Volver a la Matriz
        </a>

        {% if not read_only %}
          <a href="{{ url_for('comunicaciones_new', reg_id=r.id) }}"
             class="btn btn-warning rounded-pill px-4 fw-bold">
            Editar registro
          </a>
        {% endif %}
      </div>

      <div class="comdet-card">
        <div class="comdet-card-body">

          <div class="comdet-section">
            <div class="comdet-section-title">Información principal</div>
            <div class="row g-3">

              <div class="col-md-6">
                <div class="comdet-field">
                  <div class="comdet-label">Proceso</div>
                  <div class="comdet-value comdet-value-lg">{{ r.proceso or '—' }}</div>
                </div>
              </div>

              <div class="col-md-6">
                <div class="comdet-field">
                  <div class="comdet-label">Tipo de comunicación</div>
                  <div class="comdet-value">
                    {% if r.tipo_comunicacion == 'Interna' %}
                      <span class="badge bg-primary">Interna</span>
                    {% else %}
                      <span class="badge bg-success">Externa</span>
                    {% endif %}
                  </div>
                </div>
              </div>

              <div class="col-md-12">
                <div class="comdet-field">
                  <div class="comdet-label">Información (¿Qué comunica?)</div>
                  <div class="comdet-value">{{ r.informacion or '—' }}</div>
                </div>
              </div>

            </div>
          </div>

          <div class="comdet-section">
            <div class="comdet-section-title">Flujo de comunicación</div>
            <div class="row g-3">

              <div class="col-md-6">
                <div class="comdet-field">
                  <div class="comdet-label">Remitente (¿Quién comunica?)</div>
                  <div class="comdet-value">{{ r.remitente or '—' }}</div>
                </div>
              </div>

              <div class="col-md-6">
                <div class="comdet-field">
                  <div class="comdet-label">Destinatario (¿A quién comunica?)</div>
                  <div class="comdet-value">{{ r.destinatario or '—' }}</div>
                </div>
              </div>

              <div class="col-md-6">
                <div class="comdet-field">
                  <div class="comdet-label">Medio (¿Cómo comunica?)</div>
                  <div class="comdet-value">{{ r.medio or '—' }}</div>
                </div>
              </div>

              <div class="col-md-6">
                <div class="comdet-field">
                  <div class="comdet-label">Frecuencia (¿Cuándo comunica?)</div>
                  <div class="comdet-value">{{ r.frecuencia or '—' }}</div>
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

      .comdet-shell{
        width:96%;
        max-width:1250px;
        margin:10px auto 24px auto;
      }

      .comdet-header-card{
        background:linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.24);
        color:#fff;
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .comdet-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 26%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 15px);
      }

      .comdet-header-overlay{
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

      .comdet-header-overlay::before{
        content:"💬";
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
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .comdet-header-text::before{
        content:"SGSI · Detalle de Comunicación";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
      }

      .comdet-title{
        color:#fff !important;
        font-weight:950;
        font-size:1.32rem;
        margin:0 !important;
      }

      .comdet-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
      }

      .comdet-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px;
      }

      .comdet-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .comdet-back-btn{
        background:#fff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .comdet-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .comdet-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        overflow:hidden;
        border:1px solid rgba(219,230,244,.9);
      }

      .comdet-card-body{
        padding:16px 18px;
      }

      .comdet-section{
        margin-bottom:14px;
        background:#fff;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:8px 7px;
        box-shadow:0 8px 18px rgba(15,23,42,.08);
      }

      .comdet-section:last-child{
        margin-bottom:0;
      }

      .comdet-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:0 0 12px 0;
      }

      .comdet-field{
        background:linear-gradient(180deg,#f8fbff 0%,#ffffff 100%);
        border:1px solid #dbe6f4;
        border-radius:14px;
        padding:12px;
        height:100%;
      }

      .comdet-label{
        font-size:.70rem;
        font-weight:900;
        text-transform:uppercase;
        letter-spacing:.35px;
        color:#0b4a8f;
        margin-bottom:6px;
      }

      .comdet-value{
        color:#101827;
        font-size:.82rem;
        line-height:1.38;
        white-space:pre-wrap;
        word-break:break-word;
      }

      .comdet-value-lg{
        font-size:.90rem;
        font-weight:900;
        color:#0f172a;
      }

      @media (max-width:992px){
        .comdet-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .comdet-header-card{
          min-height:88px;
        }

        .comdet-title{
          font-size:1.2rem;
        }

        .comdet-card-body{
          padding:8px 7px;
        }

        .comdet-section{
          padding:12px;
        }
      }

      @media (max-width:768px){
        .comdet-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .comdet-header-overlay::before{
          margin:0;
        }

        .comdet-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(html, r=r, read_only=read_only)
    return render_template_string(BASE, content=Markup(inner))


# =========================
# Eliminación Registro
# =========================
@app.route('/comunicaciones/delete')
@login_required
def comunicaciones_delete():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor' or (
        user.role != 'admin' and not verificar_permiso(user, "Registro de Comunicaciones")
    ):
        flash("No tiene permiso para eliminar registros de comunicaciones.", "danger")
        return redirect(url_for('comunicaciones_matriz'))

    rid = request.args.get('id', type=int)
    reg = MatrizComunicacionRegistro.query.get(rid)

    if not reg:
        flash("Registro no encontrado.", "danger")
        return redirect(url_for('comunicaciones_matriz'))

    db.session.delete(reg)
    db.session.commit()
    flash("Registro eliminado correctamente.", "success")
    return redirect(url_for('comunicaciones_matriz'))


# ==========================================================================================================================================
#                                                               Fin Módulo Matriz de Comunicaciones
# ==========================================================================================================================================

# ==========================================================================================================================================
#                                                               Módulo Requisitos Legales
# ==========================================================================================================================================

def resumir_texto_req(valor, limite=120):
    if not valor:
        return '—'
    txt = str(valor).strip()
    if len(txt) <= limite:
        return txt
    return txt[:limite].rstrip() + '...'


# =========================
# ENTRADA DIRECTA — Requisitos Legales
# =========================
@app.route('/requisitos_menu')
@login_required
def requisitos_menu():
    user = User.query.get(session.get('user_id'))

    if user.role not in ('admin', 'auditor') and not verificar_permiso(user, "Requisitos Legales"):
        flash("No tiene permiso para acceder al módulo de requisitos legales.", "danger")
        return redirect(url_for('menu'))

    return redirect(url_for('req_legal_matriz'))


# ==========================
# Agregar Requisitos legales
# ==========================
@app.route('/requisito_legal/new', methods=['GET', 'POST'])
@login_required
def requisito_legal_new():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede agregar registros.", "danger")
        return redirect(url_for('req_legal_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Requisitos Legales"):
        flash("No tiene permiso para agregar requisitos legales.", "danger")
        return redirect(url_for('req_legal_matriz'))

    if request.method == 'POST':
        codigo = (request.form.get('codigo') or '').strip()
        requisito = (request.form.get('requisito') or '').strip()
        tipo_ley = (request.form.get('tipo_ley') or '').strip()
        entidad_emisora = (request.form.get('entidad_emisora') or '').strip()
        descripcion_alcance = (request.form.get('descripcion_alcance') or '').strip()
        responsable = (request.form.get('responsable') or '').strip()
        evidencia_cumplimiento = (request.form.get('evidencia_cumplimiento') or '').strip()
        ESTADOS_PERMITIDOS = ["Cumple", "Parcial", "No cumple"]
        estado = (request.form.get('estado') or '').strip()

        fecha_str = (request.form.get('fecha_revision') or '').strip()
        fecha_revision = None
        if fecha_str:
            try:
                fecha_revision = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            except ValueError:
                flash("Fecha de revisión inválida.", "danger")
                return redirect(url_for('requisito_legal_new'))

        if not all([codigo, requisito, tipo_ley, entidad_emisora, descripcion_alcance, responsable, estado]):
            flash("Campos obligatorios: ID, Requisito, Tipo de Ley/Norma, Entidad Emisora, Descripción/Alcance, Responsable y Estado.", "danger")
            return redirect(url_for('requisito_legal_new'))

        if estado not in ESTADOS_PERMITIDOS:
            flash("Estado inválido. Debe ser: Cumple, Parcial o No cumple.", "danger")
            return redirect(url_for('requisito_legal_new'))

        it = RequisitoLegal(
            codigo=codigo,
            requisito=requisito,
            tipo_ley=tipo_ley,
            entidad_emisora=entidad_emisora,
            descripcion_alcance=descripcion_alcance,
            responsable=responsable,
            evidencia_cumplimiento=evidencia_cumplimiento,
            estado=estado,
            fecha_revision=fecha_revision
        )
        db.session.add(it)
        db.session.commit()
        flash("Requisito legal registrado.", "success")
        return redirect(url_for('req_legal_matriz'))

    html = """
    <div class="reqadd-shell">

      <div class="reqadd-header-card">
        <div class="reqadd-header-overlay">
          <div class="reqadd-header-text">
            <h3 class="reqadd-title m-0">Agregar Requisito Legal</h3>
            <div class="reqadd-subtitle">
              Registro de requisitos legales, contractuales y regulatorios aplicables al SGSI
            </div>
          </div>
        </div>
      </div>

      <div class="reqadd-header-actions">
        <a href="{{ url_for('req_legal_matriz') }}"
           class="btn rounded-pill px-4 fw-bold reqadd-back-btn">
          ⬅ Volver a la Matriz
        </a>
      </div>

      <div class="reqadd-card">
        <div class="reqadd-card-body">
          <form method="post">

            <div class="row g-3">

              <div class="col-md-3">
                <label class="form-label">ID (alfanumérico)</label>
                <input name="codigo" class="form-control" required>
              </div>

              <div class="col-md-9">
                <label class="form-label">Requisito Legal / Contractual</label>
                <textarea name="requisito" class="form-control" rows="2" required></textarea>
              </div>

              <div class="col-md-4">
                <label class="form-label">Tipo de Ley / Norma</label>
                <input name="tipo_ley" class="form-control" required>
              </div>

              <div class="col-md-4">
                <label class="form-label">Entidad Emisora</label>
                <input name="entidad_emisora" class="form-control" required>
              </div>

              <div class="col-md-4">
                <label class="form-label">Responsable</label>
                <input name="responsable" class="form-control" required>
              </div>

              <div class="col-md-12">
                <label class="form-label">Descripción / Alcance</label>
                <textarea name="descripcion_alcance" class="form-control" rows="2" required></textarea>
              </div>

              <div class="col-md-6">
                <label class="form-label">Evidencia de Cumplimiento</label>
                <textarea name="evidencia_cumplimiento" class="form-control" rows="2"></textarea>
              </div>

              <div class="col-md-3">
                <label class="form-label">Estado</label>
                <select name="estado" class="form-select" required>
                  <option value="">-- Seleccione --</option>
                  <option value="Cumple">Cumple</option>
                  <option value="Parcial">Parcial</option>
                  <option value="No cumple">No cumple</option>
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">Fecha de Revisión</label>
                <input type="date" name="fecha_revision" class="form-control">
              </div>

            </div>

            <div class="reqadd-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar
              </button>

              <a href="{{ url_for('req_legal_matriz') }}"
                 class="btn rounded-pill px-4 fw-bold reqadd-cancel-btn">
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

      .reqadd-shell{
        width:96%;
        max-width:1350px;
        margin:10px auto 24px auto;
      }

      /* =========================
         HERO SGSI
      ========================== */
      .reqadd-header-card{
        background:linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.24);
        color:#fff;
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .reqadd-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 26%),
          repeating-linear-gradient(
            135deg,
            rgba(255,255,255,.05) 0px,
            rgba(255,255,255,.05) 1px,
            transparent 1px,
            transparent 15px
          );
      }

      .reqadd-header-overlay{
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

      .reqadd-header-overlay::before{
        content:"📝";
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
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .reqadd-header-text::before{
        content:"SGSI · Requerimiento";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
      }

      .reqadd-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        margin:0 !important;
      }

      .reqadd-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
      }

      /* =========================
         BOTONES HEADER
      ========================== */
      .reqadd-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px;
      }

      .reqadd-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .reqadd-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .reqadd-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         CARD
      ========================== */
      .reqadd-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .reqadd-card-body{
        padding:16px 18px;
      }

      /* =========================
         SECCIONES
      ========================== */
      .reqadd-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:10px 0 10px;
      }

      /* =========================
         FORMULARIOS
      ========================== */
      .reqadd-card .form-label{
        font-weight:800;
        font-size:.78rem;
        color:#101827;
        margin-bottom:4px;
      }

      .reqadd-card .form-control,
      .reqadd-card .form-select{
        border-radius:10px;
        border:1px solid #cfd8e3;
        min-height:32px;
        font-size:.82rem;
        background:#f8fbff;
      }

      .reqadd-card textarea.form-control{
        min-height:85px;
      }

      .reqadd-card .form-control:focus,
      .reqadd-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 0.2rem rgba(63,134,214,.15);
        background:#ffffff;
      }

      /* =========================
         BOTONES INFERIORES
      ========================== */
      .reqadd-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin-top:20px;
      }

      .reqadd-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .reqadd-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .reqadd-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         RESPONSIVE
      ========================== */
      @media (max-width:992px){
        .reqadd-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .reqadd-header-card{
          min-height:88px;
        }

        .reqadd-title{
          font-size:1.2rem;
        }

        .reqadd-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .reqadd-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .reqadd-header-overlay::before{
          margin:0;
        }

        .reqadd-header-actions .btn,
        .reqadd-bottom-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(html)
    return render_template_string(BASE, content=Markup(inner))


# =========================
# Matriz Requisitos legales
# =========================
@app.route('/req_legal_matriz')
@login_required
def req_legal_matriz():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Requisitos Legales"):
            flash("No tiene permiso para ver la matriz.", "danger")
            return redirect(url_for('menu'))
        read_only = False

    items = RequisitoLegal.query.order_by(RequisitoLegal.codigo.asc()).all()

    html = """
    <div class="req-shell">

      <div class="req-header-card">
        <div class="req-header-overlay">
          <div class="req-header-text">
            <h3 class="req-title m-0">Requisitos Legales</h3>
            <div class="req-subtitle">
              Visualización resumida de requisitos legales y contractuales
            </div>
          </div>
        </div>
      </div>

      <div class="req-header-actions">

        {% if not read_only %}
          <a href="{{ url_for('requisito_legal_new') }}"
             class="btn btn-primary rounded-pill px-4 fw-bold">
            ➕ Agregar Registro
          </a>
        {% else %}
          <button class="btn btn-secondary rounded-pill px-4 fw-bold" disabled>
            ➕ Agregar Registro
          </button>
        {% endif %}
      </div>

      <div class="req-card">
        <div class="req-topbar">
          <div>
            <h5 class="req-top-title mb-1">Resumen</h5>
            <div class="req-top-note">
              Usa <strong>Ver detalle</strong> para ver toda la información.
            </div>
          </div>
          <div class="req-counter-badge">
            Total: {{ items|length }}
          </div>
        </div>

        <div class="req-card-body">
          <div class="req-table-wrap">
            <table class="table table-bordered table-hover align-middle req-table mb-0">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Requisito</th>
                  <th>Tipo</th>
                  <th>Responsable</th>
                  <th>Estado</th>
                  <th class="req-col-acciones">Acciones</th>
                </tr>
              </thead>

              <tbody>
              {% for it in items %}
                <tr>
                  <td>{{ it.codigo }}</td>
                  <td>{{ resumir_texto_req(it.requisito, 140) }}</td>
                  <td>{{ it.tipo_ley }}</td>
                  <td>{{ it.responsable }}</td>
                  <td class="text-center">
                    {% if it.estado == 'Cumple' %}
                      <span class="badge bg-success">Cumple</span>
                    {% elif it.estado == 'Parcial' %}
                      <span class="badge bg-warning text-dark">Parcial</span>
                    {% elif it.estado == 'No cumple' %}
                      <span class="badge bg-danger">No cumple</span>
                    {% else %}
                      <span class="badge bg-secondary">{{ it.estado or '—' }}</span>
                    {% endif %}
                  </td>

                  <td class="text-center req-col-acciones">
                    <div class="req-actions-wrap">
                      <a href="{{ url_for('req_legal_detalle', id=it.id) }}"
                         class="btn btn-info btn-sm rounded-pill req-btn-action text-white fw-bold">
                        Ver detalle
                      </a>

                      {% if not read_only %}
                        <a href="{{ url_for('requisito_legal_edit', id=it.id) }}"
                           class="btn btn-warning btn-sm rounded-pill req-btn-action fw-bold">
                          Editar
                        </a>

                        <a href="{{ url_for('requisito_legal_delete', id=it.id) }}"
                           class="btn btn-danger btn-sm rounded-pill req-btn-action fw-bold"
                           onclick="return confirm('¿Eliminar registro?');">
                          Eliminar
                        </a>
                      {% else %}
                        <span class="badge bg-secondary req-badge-readonly">Solo lectura</span>
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

    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .req-shell{
        width:96%;
        max-width:1500px;
        margin:10px auto 24px auto;
      }

      .req-header-card{
        background:linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.24);
        color:#fff;
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .req-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 26%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 15px);
      }

      .req-header-overlay{
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

      .req-header-overlay::before{
        content:"⚖️";
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
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .req-header-text::before{
        content:"SGSI · Requerimientos";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
      }

      .req-title{
        color:#fff !important;
        font-weight:950;
        font-size:1.32rem;
        margin:0 !important;
      }

      .req-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
      }

      .req-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px;
      }

      .req-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .req-back-btn{
        background:#fff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .req-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .req-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .req-topbar{
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:12px;
        padding:14px 16px 0 16px;
        flex-wrap:wrap;
      }

      .req-top-title{
        color:#0f172a;
        font-weight:950;
        font-size:.92rem;
      }

      .req-top-note{
        color:#475569;
        font-size:.78rem;
        margin-top:3px;
      }

      .req-counter-badge{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        color:#fff;
        font-weight:900;
        border-radius:999px;
        padding:7px 14px;
        font-size:.78rem;
        box-shadow:0 8px 16px rgba(15,23,42,.16);
      }

      .req-card-body{
        padding:12px 16px 16px 16px;
      }

      .req-table-wrap{
        max-height:70vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#fff;
      }

      .req-table{
        min-width:1100px;
        table-layout:fixed;
        margin-bottom:0;
      }

      .req-table thead th{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#fff;
        font-weight:900;
        text-align:center;
        vertical-align:middle;
      }

      .req-table th,
      .req-table td{
        vertical-align:top;
        font-size:.78rem;
        padding:9px 8px;
        white-space:normal;
        word-break:break-word;
        overflow-wrap:anywhere;
      }

      .req-table td{
        border-bottom:1px solid #e5edf7;
      }

      .req-table tbody tr:nth-child(even){
        background:#f8fbff;
      }

      .req-table tbody tr:hover{
        background:#eef6ff;
      }

      .req-col-acciones{
        min-width:180px !important;
        width:180px !important;
      }

      .req-table th.req-col-acciones,
      .req-table td.req-col-acciones{
        min-width:180px !important;
        width:180px !important;
        text-align:center;
        vertical-align:middle;
      }

      .req-actions-wrap{
        display:flex;
        flex-direction:column;
        gap:6px;
        align-items:center;
        justify-content:center;
      }

      .req-btn-action{
        min-width:105px;
        max-width:120px;
        font-size:.64rem !important;
        padding:4px 12px !important;
        line-height:1.2;
        text-align:center;
        white-space:nowrap;
        border-radius:999px !important;
        font-weight:900;
      }

      .req-badge-readonly{
        font-size:.70rem;
        padding:5px 10px;
        border-radius:999px;
        white-space:nowrap;
        font-weight:900;
      }

      @media (max-width:992px){
        .req-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .req-header-card{
          min-height:88px;
        }

        .req-title{
          font-size:1.2rem;
        }

        .req-card-body{
          padding:12px;
        }

        .req-topbar{
          padding:12px 14px 0 14px;
        }
      }

      @media (max-width:768px){
        .req-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .req-header-overlay::before{
          margin:0;
        }

        .req-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(
        html,
        items=items,
        read_only=read_only,
        resumir_texto_req=resumir_texto_req
    )
    return render_template_string(BASE, content=Markup(inner))


# =========================
# Detalle Requisito legal
# =========================
@app.route('/req_legal_detalle/<int:id>')
@login_required
def req_legal_detalle(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Requisitos Legales"):
            flash("No tiene permiso para ver el detalle del requisito legal.", "danger")
            return redirect(url_for('req_legal_matriz'))
        read_only = False

    it = RequisitoLegal.query.get_or_404(id)

    def ffecha(v):
        if not v:
            return '—'
        try:
            return v.strftime('%Y-%m-%d')
        except Exception:
            return str(v)

    html = """
    <div class="reqdet-shell">

      <div class="reqdet-header-card">
        <div class="reqdet-header-overlay">
          <div class="reqdet-header-text">
            <h3 class="reqdet-title m-0">Detalle del Requisito Legal</h3>
            <div class="reqdet-subtitle">
              Consulta completa del registro en modo solo lectura
            </div>
          </div>
        </div>
      </div>

      <div class="reqdet-header-actions">
        <a href="{{ url_for('req_legal_matriz') }}"
           class="btn rounded-pill px-4 fw-bold reqdet-back-btn">
          ⬅ Volver a la Matriz
        </a>

        {% if not read_only %}
          <a href="{{ url_for('requisito_legal_edit', id=it.id) }}"
             class="btn btn-warning rounded-pill px-4 fw-bold">
            Editar registro
          </a>
        {% endif %}
      </div>

      <div class="reqdet-card">
        <div class="reqdet-card-body">

          <div class="reqdet-section">
            <div class="reqdet-section-title">Información general</div>
            <div class="row g-3">

              <div class="col-md-3">
                <div class="reqdet-field">
                  <div class="reqdet-label">ID</div>
                  <div class="reqdet-value">{{ it.codigo or '—' }}</div>
                </div>
              </div>

              <div class="col-md-5">
                <div class="reqdet-field">
                  <div class="reqdet-label">Tipo de Ley / Norma</div>
                  <div class="reqdet-value">{{ it.tipo_ley or '—' }}</div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="reqdet-field">
                  <div class="reqdet-label">Entidad Emisora</div>
                  <div class="reqdet-value">{{ it.entidad_emisora or '—' }}</div>
                </div>
              </div>

              <div class="col-md-12">
                <div class="reqdet-field">
                  <div class="reqdet-label">Requisito Legal / Contractual</div>
                  <div class="reqdet-value reqdet-value-lg">{{ it.requisito or '—' }}</div>
                </div>
              </div>

            </div>
          </div>

          <div class="reqdet-section">
            <div class="reqdet-section-title">Cumplimiento y seguimiento</div>
            <div class="row g-3">

              <div class="col-md-4">
                <div class="reqdet-field">
                  <div class="reqdet-label">Responsable</div>
                  <div class="reqdet-value">{{ it.responsable or '—' }}</div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="reqdet-field">
                  <div class="reqdet-label">Estado</div>
                  <div class="reqdet-value">
                    {% if it.estado == 'Cumple' %}
                      <span class="badge bg-success">Cumple</span>
                    {% elif it.estado == 'Parcial' %}
                      <span class="badge bg-warning text-dark">Parcial</span>
                    {% elif it.estado == 'No cumple' %}
                      <span class="badge bg-danger">No cumple</span>
                    {% else %}
                      <span class="badge bg-secondary">{{ it.estado or '—' }}</span>
                    {% endif %}
                  </div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="reqdet-field">
                  <div class="reqdet-label">Fecha de Revisión</div>
                  <div class="reqdet-value">{{ ffecha(it.fecha_revision) }}</div>
                </div>
              </div>

            </div>
          </div>

          <div class="reqdet-section">
            <div class="reqdet-section-title">Descripción y evidencias</div>
            <div class="row g-3">

              <div class="col-md-12">
                <div class="reqdet-field">
                  <div class="reqdet-label">Descripción / Alcance</div>
                  <div class="reqdet-value">{{ it.descripcion_alcance or '—' }}</div>
                </div>
              </div>

              <div class="col-md-12">
                <div class="reqdet-field">
                  <div class="reqdet-label">Evidencia de Cumplimiento</div>
                  <div class="reqdet-value">{{ it.evidencia_cumplimiento or '—' }}</div>
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

      .reqdet-shell{
        width:96%;
        max-width:1250px;
        margin:10px auto 24px auto;
      }

      .reqdet-header-card{
        background:linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.24);
        color:#fff;
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .reqdet-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 26%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 15px);
      }

      .reqdet-header-overlay{
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

      .reqdet-header-overlay::before{
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
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .reqdet-header-text::before{
        content:"SGSI · Detalle de Requerimiento";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
      }

      .reqdet-title{
        color:#fff !important;
        font-weight:950;
        font-size:1.32rem;
        margin:0 !important;
      }

      .reqdet-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
      }

      .reqdet-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px;
      }

      .reqdet-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .reqdet-back-btn{
        background:#fff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .reqdet-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .reqdet-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        overflow:hidden;
        border:1px solid rgba(219,230,244,.9);
      }

      .reqdet-card-body{
        padding:16px 18px;
      }

      .reqdet-section{
        margin-bottom:14px;
        background:#fff;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:8px 7px;
        box-shadow:0 8px 18px rgba(15,23,42,.08);
      }

      .reqdet-section:last-child{
        margin-bottom:0;
      }

      .reqdet-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:0 0 12px 0;
      }

      .reqdet-field{
        background:linear-gradient(180deg,#f8fbff 0%,#ffffff 100%);
        border:1px solid #dbe6f4;
        border-radius:14px;
        padding:12px;
        min-height:100%;
      }

      .reqdet-label{
        font-size:.70rem;
        font-weight:900;
        text-transform:uppercase;
        letter-spacing:.35px;
        color:#0b4a8f;
        margin-bottom:6px;
      }

      .reqdet-value{
        color:#101827;
        font-size:.82rem;
        line-height:1.38;
        white-space:pre-wrap;
        word-break:break-word;
      }

      .reqdet-value-lg{
        font-size:.90rem;
        font-weight:900;
        color:#0f172a;
      }

      .reqdet-value .badge{
        font-size:.70rem;
        padding:5px 10px;
        border-radius:999px;
        white-space:nowrap;
        display:inline-block;
        font-weight:900;
      }

      @media (max-width:992px){
        .reqdet-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .reqdet-header-card{
          min-height:88px;
        }

        .reqdet-title{
          font-size:1.2rem;
        }

        .reqdet-card-body{
          padding:8px 7px;
        }

        .reqdet-section{
          padding:12px;
        }
      }

      @media (max-width:768px){
        .reqdet-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .reqdet-header-overlay::before{
          margin:0;
        }

        .reqdet-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(html, it=it, read_only=read_only, ffecha=ffecha)
    return render_template_string(BASE, content=Markup(inner))


# =========================
# Editar Requisitos legales
# =========================
@app.route('/requisito_legal/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def requisito_legal_edit(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede editar.", "danger")
        return redirect(url_for('req_legal_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Requisitos Legales"):
        flash("No tiene permiso para editar requisitos legales.", "danger")
        return redirect(url_for('req_legal_matriz'))

    it = RequisitoLegal.query.get_or_404(id)

    if request.method == 'POST':
        it.codigo = (request.form.get('codigo') or '').strip()
        it.requisito = (request.form.get('requisito') or '').strip()
        it.tipo_ley = (request.form.get('tipo_ley') or '').strip()
        it.entidad_emisora = (request.form.get('entidad_emisora') or '').strip()
        it.descripcion_alcance = (request.form.get('descripcion_alcance') or '').strip()
        it.responsable = (request.form.get('responsable') or '').strip()
        it.evidencia_cumplimiento = (request.form.get('evidencia_cumplimiento') or '').strip()
        it.estado = (request.form.get('estado') or '').strip()

        fecha_str = (request.form.get('fecha_revision') or '').strip()
        if fecha_str:
            try:
                it.fecha_revision = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            except ValueError:
                flash("Fecha de revisión inválida.", "danger")
                return redirect(url_for('requisito_legal_edit', id=id))
        else:
            it.fecha_revision = None

        db.session.commit()
        flash("Requisito legal actualizado.", "success")
        return redirect(url_for('req_legal_matriz'))

    html = """
    <div class="reqedit-shell">

      <div class="reqedit-header-card">
        <div class="reqedit-header-overlay">
          <div class="reqedit-header-text">
            <h3 class="reqedit-title m-0">Editar Requisito Legal</h3>
            <div class="reqedit-subtitle">
              Actualización y seguimiento del cumplimiento de requisitos legales del SGSI
            </div>
          </div>
        </div>
      </div>

      <div class="reqedit-header-actions">
        <a href="{{ url_for('req_legal_matriz') }}"
           class="btn rounded-pill px-4 fw-bold reqedit-back-btn">
          ⬅ Volver a la Matriz
        </a>

      </div>

      <div class="reqedit-card">
        <div class="reqedit-card-body">

          <form method="post">

            <div class="row g-3">

              <div class="col-md-3">
                <label class="form-label">ID (alfanumérico)</label>
                <input name="codigo" class="form-control" value="{{ it.codigo or '' }}" required>
              </div>

              <div class="col-md-9">
                <label class="form-label">Requisito Legal / Contractual</label>
                <textarea name="requisito" class="form-control" rows="2" required>{{ it.requisito or '' }}</textarea>
              </div>

              <div class="col-md-4">
                <label class="form-label">Tipo de Ley / Norma</label>
                <input name="tipo_ley" class="form-control" value="{{ it.tipo_ley or '' }}" required>
              </div>

              <div class="col-md-4">
                <label class="form-label">Entidad Emisora</label>
                <input name="entidad_emisora" class="form-control" value="{{ it.entidad_emisora or '' }}" required>
              </div>

              <div class="col-md-4">
                <label class="form-label">Responsable</label>
                <input name="responsable" class="form-control" value="{{ it.responsable or '' }}" required>
              </div>

              <div class="col-md-12">
                <label class="form-label">Descripción / Alcance</label>
                <textarea name="descripcion_alcance" class="form-control" rows="2" required>{{ it.descripcion_alcance or '' }}</textarea>
              </div>

              <div class="col-md-6">
                <label class="form-label">Evidencia de Cumplimiento</label>
                <textarea name="evidencia_cumplimiento" class="form-control" rows="2">{{ it.evidencia_cumplimiento or '' }}</textarea>
              </div>

              <div class="col-md-3">
                <label class="form-label">Estado</label>
                <select name="estado" class="form-select" required>
                  <option value="">-- Seleccione --</option>
                  <option value="Cumple" {% if it.estado=='Cumple' %}selected{% endif %}>Cumple</option>
                  <option value="Parcial" {% if it.estado=='Parcial' %}selected{% endif %}>Parcial</option>
                  <option value="No cumple" {% if it.estado=='No cumple' %}selected{% endif %}>No cumple</option>
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">Fecha de Revisión</label>
                <input type="date" name="fecha_revision" class="form-control"
                       value="{{ it.fecha_revision.strftime('%Y-%m-%d') if it.fecha_revision else '' }}">
              </div>

            </div>

            <div class="reqedit-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar cambios
              </button>

              <a href="{{ url_for('req_legal_matriz') }}"
                 class="btn rounded-pill px-4 fw-bold reqedit-cancel-btn">
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

      .reqedit-shell{
        width:96%;
        max-width:1350px;
        margin:10px auto 24px auto;
      }

      /* 🔷 HEADER SGSI UNIFICADO */
      .reqedit-header-card{
        background:linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.24);
        color:#fff;
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .reqedit-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 26%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 15px);
      }

      .reqedit-header-overlay{
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

      .reqedit-header-overlay::before{
        content:"✏️";
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
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .reqedit-header-text::before{
        content:"SGSI · Edición de Requerimiento";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
      }

      .reqedit-title{
        color:#ffffff!important;
        font-weight:950;
        font-size:1.32rem;
        margin:0 !important;
      }

      .reqedit-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
      }

      /* 🔘 BOTONES */
      .reqedit-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px;
      }

      .reqedit-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .reqedit-back-btn{
        background:#fff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .reqedit-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* 📦 CARD */
      .reqedit-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        overflow:hidden;
        border:1px solid rgba(219,230,244,.9);
      }

      .reqedit-card-body{
        padding:16px 18px;
      }

      /* 🧾 FORM */
      .reqedit-card .form-label{
        font-weight:800;
        color:#0b4a8f;
        font-size:.78rem;
        margin-bottom:4px;
      }

      .reqedit-card .form-control,
      .reqedit-card .form-select{
        border-radius:10px;
        border:1px solid #dbe6f4;
        min-height:40px;
        font-size:.82rem;
        background:#f8fbff;
      }

      .reqedit-card textarea.form-control{
        min-height:90px;
      }

      .reqedit-card .form-control:focus,
      .reqedit-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 0.15rem rgba(63,134,214,.18);
        background:#fff;
      }

      /* 🔽 BOTONES INFERIORES */
      .reqedit-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:20px;
        flex-wrap:wrap;
      }

      .reqedit-bottom-actions .btn{
        border-radius:10px;
        padding:8px 20px;
        font-size:.82rem;
        font-weight:900;
      }

      .reqedit-cancel-btn{
        background:#fff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .reqedit-cancel-btn:hover{
        background:#f1f5f9;
      }

      /* 📱 RESPONSIVE */
      @media (max-width:992px){
        .reqedit-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .reqedit-header-card{
          min-height:88px;
        }

        .reqedit-title{
          font-size:1.2rem;
        }

        .reqedit-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .reqedit-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .reqedit-header-overlay::before{
          margin:0;
        }

        .reqedit-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(html, it=it)
    return render_template_string(BASE, content=Markup(inner))


# =========================
# Eliminar Requisito legal
# =========================
@app.route('/requisito_legal/delete/<int:id>')
@login_required
def requisito_legal_delete(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede eliminar.", "danger")
        return redirect(url_for('req_legal_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Requisitos Legales"):
        flash("No tiene permiso para eliminar requisitos legales.", "danger")
        return redirect(url_for('req_legal_matriz'))

    it = RequisitoLegal.query.get_or_404(id)
    db.session.delete(it)
    db.session.commit()
    flash("Requisito legal eliminado.", "success")
    return redirect(url_for('req_legal_matriz'))


# ==========================================================================================================================================
#                                                               Fin del Módulo Requisitos Legales
# ==========================================================================================================================================


# ============================================================================================================================================
#                                                               Módulo Gestión de Activos
# ============================================================================================================================================


# =========================
# Dueños de la Información (en Gestión de Activos)
# =========================
@app.route('/duenos_info', methods=['GET', 'POST'])
@login_required
def duenos_info():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso_activos(user, "Dueños de Información"):
            flash("No tiene permiso para ver la gestión de activos.", "danger")
            return redirect(url_for('proveedores_menu'))
        read_only = False

    # 3) Definir si es solo lectura (auditor)
    solo_lectura = (user.role == 'auditor')
    
    # Listas para selects
    areas = AreaEmpresa.query.order_by(AreaEmpresa.area.asc()).all()

    # 🚫 Si es auditor, ignoramos cualquier POST (no puede crear/editar)
    if request.method == 'POST' and solo_lectura:
        flash("El rol Auditor no puede modificar los dueños de la información.", "danger")
        return redirect(url_for('duenos_info'))

    if request.method == 'POST':
        rid = request.form.get('id', type=int)

        area_id = request.form.get('area_id', type=int)
        dueno_nombre = (request.form.get('dueno_nombre') or "").strip()
        dueno_cargo  = (request.form.get('dueno_cargo')  or "").strip()
        custodio_nombre = (request.form.get('custodio_nombre') or "").strip()
        custodio_cargo  = (request.form.get('custodio_cargo')  or "").strip()

        if not (area_id and dueno_nombre and dueno_cargo and custodio_nombre and custodio_cargo):
            flash("Todos los campos son obligatorios.", "danger")
            return redirect(url_for('duenos_info'))

        if rid:
            item = DuenoInformacion.query.get(rid)
            if not item:
                flash("Registro no encontrado.", "danger")
                return redirect(url_for('duenos_info'))
        else:
            item = DuenoInformacion()
            db.session.add(item)  # lo añadimos ya para poder hacer flush si hace falta (nuevo)

        # Asignar campos base
        item.area_id = area_id
        item.dueno_nombre = dueno_nombre
        item.dueno_cargo  = dueno_cargo
        item.custodio_nombre = custodio_nombre
        item.custodio_cargo  = custodio_cargo

        # PDFs existentes
        pdfs_guardados = [f for f in (item.acuerdos_pdf.split(',') if item.acuerdos_pdf else []) if f]

        # Leer nuevos PDFs (múltiple) → el name del input es 'acuerdos_pdf'
        files = request.files.getlist('acuerdos_pdf')

        # Validar TODOS antes de guardar
        for f in files:
            if f and f.filename and not allowed_pdf(f.filename):
                flash("Solo se permiten archivos PDF.", "danger")
                return redirect(url_for('duenos_info'))

        # Si es un registro nuevo y aún no tiene ID, hacemos flush para disponer de item.id
        if not rid:
            db.session.flush()  # NO commit aquí, solo flush asigna el ID

        from werkzeug.utils import secure_filename
        for f in files:
            if f and f.filename:
                raw = secure_filename(f.filename)
                filename = f"owner_{item.id}_{raw}"  # prefijo con ID para evitar colisiones
                dst = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                if filename not in pdfs_guardados:
                    f.save(dst)
                    pdfs_guardados.append(filename)

        # Persistir lista final (existentes + nuevos)
        item.acuerdos_pdf = ",".join(pdfs_guardados)

        # Un solo commit al final
        db.session.commit()

        flash("Guardado correctamente.", "success")
        return redirect(url_for('duenos_info'))
    
    # GET
    edit_id = request.args.get('edit', type=int)
    edit_item = DuenoInformacion.query.get(edit_id) if edit_id else None
    items = DuenoInformacion.query.order_by(DuenoInformacion.id.desc()).all()

    html = """
    <div class="duenos-shell">

      <!-- CABECERA -->
      <div class="duenos-header-card">
        <div class="duenos-header-overlay">
          <div class="duenos-header-text">
            <h3 class="duenos-title m-0">Dueños de la Información</h3>
            <div class="duenos-subtitle">
              Gestión de dueños, custodios y acuerdos de asignación y responsabilidad de la información
            </div>
          </div>
        </div>
      </div>

      <!-- FORMULARIO CREAR / EDITAR -->
      {% if not solo_lectura %}
      <div class="duenos-card mb-3">
        <div class="duenos-card-body">

          <form method="post" action="{{ url_for('duenos_info') }}" enctype="multipart/form-data">
            {% if edit_item %}
              <input type="hidden" name="id" value="{{ edit_item.id }}">
            {% endif %}

            <div class="row g-3">

              <div class="col-md-4">
                <label class="form-label">Área</label>
                <select name="area_id" class="form-select" required>
                  <option value="">-- Seleccione --</option>
                  {% for a in areas %}
                    <option value="{{ a.id }}" {% if edit_item and edit_item.area_id==a.id %}selected{% endif %}>
                      {{ a.area }}
                    </option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Nombre del dueño de la información</label>
                <input type="text"
                       name="dueno_nombre"
                       class="form-control"
                       required
                       value="{{ edit_item.dueno_nombre if edit_item else '' }}">
              </div>

              <div class="col-md-4">
                <label class="form-label">Cargo del dueño de la información</label>
                <input type="text"
                       name="dueno_cargo"
                       class="form-control"
                       required
                       value="{{ edit_item.dueno_cargo if edit_item else '' }}">
              </div>

              <div class="col-md-4">
                <label class="form-label">Nombre del custodio</label>
                <input type="text"
                       name="custodio_nombre"
                       class="form-control"
                       required
                       value="{{ edit_item.custodio_nombre if edit_item else '' }}">
              </div>

              <div class="col-md-4">
                <label class="form-label">Cargo del custodio</label>
                <input type="text"
                       name="custodio_cargo"
                       class="form-control"
                       required
                       value="{{ edit_item.custodio_cargo if edit_item else '' }}">
              </div>

              <div class="col-md-4">
                <label class="form-label">Acuerdo de Asignación y Responsabilidad (PDF)</label>
                <input
                  type="file"
                  id="acuerdos_pdf"
                  name="acuerdos_pdf"
                  accept=".pdf"
                  multiple
                  class="form-control"
                  onchange="acumularArchivosPDF(this)"
                >
                <small class="text-muted">
                  Puedes seleccionar varios a la vez o ir agregando en varias rondas.
                </small>

                <!-- Lista visual de archivos NUEVOS -->
                <div id="lista_pdf_nuevos" class="mt-2"></div>

                <input type="hidden" id="acuerdos_pdf_buffer_flag" value="1">
              </div>

            </div>

            {% if edit_item and edit_item.acuerdos_pdf %}
              <div class="row mt-3">
                <div class="col-12">
                  <label class="form-label">Archivos cargados</label>
                  <div class="duenos-files-box">
                    {% for file in edit_item.acuerdos_pdf.split(',') if file %}
                      <div class="d-flex align-items-center justify-content-between mb-1"
                           id="pdf-{{ edit_item.id }}-{{ loop.index }}">
                        <a href="{{ url_for('vista_evidencia', filename=file, next='duenos_info') }}"
                           class="text-truncate me-2"
                           style="max-width:260px;"
                           title="{{ file }}">
                          📎 {{ file }}
                        </a>

                        <button type="button"
                                class="btn btn-link text-danger p-0"
                                onclick="deleteOwnerPdf({{ edit_item.id }}, '{{ file }}', 'pdf-{{ edit_item.id }}-{{ loop.index }}')">
                          🗑️
                        </button>
                      </div>
                    {% endfor %}
                  </div>
                </div>
              </div>
            {% endif %}

            <div class="duenos-bottom-actions">
              <button type="submit" class="btn btn-success rounded-pill px-4 fw-bold">
                {% if edit_item %}Guardar cambios{% else %}Agregar{% endif %}
              </button>

              {% if edit_item %}
                <a href="{{ url_for('duenos_info') }}"
                   class="btn rounded-pill px-4 fw-bold duenos-cancel-btn">
                  Cancelar
                </a>
              {% endif %}
            </div>

          </form>

        </div>
      </div>
      {% endif %}

      <!-- TABLA -->
      <div class="duenos-card">
        <div class="duenos-card-body">

          <div class="duenos-table-wrap">
            <div class="table-responsive">
              <table class="table table-bordered table-sm align-middle duenos-table mb-0">
                <thead class="table-secondary">
                  <tr class="text-center">
                    <th>Área</th>
                    <th>Dueño de la información</th>
                    <th>Cargo (Dueño)</th>
                    <th>Custodio</th>
                    <th>Cargo (Custodio)</th>
                    <th>Acuerdos (PDF)</th>
                    <th style="width:16%">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {% for it in items %}
                  <tr>
                    <td>{{ it.area.area if it.area else '—' }}</td>
                    <td><b>{{ it.dueno_nombre }}</b></td>
                    <td>{{ it.dueno_cargo }}</td>
                    <td>{{ it.custodio_nombre }}</td>
                    <td>{{ it.custodio_cargo }}</td>
                    <td class="small">
                      {% if it.acuerdos_pdf %}
                        {% for file in it.acuerdos_pdf.split(',') if file %}
                          <div>
                            <a href="{{ url_for('vista_evidencia', filename=file, next='duenos_info') }}">
                              📄 {{ file }}
                            </a>
                          </div>
                        {% endfor %}
                      {% else %}
                        <span class="text-muted">—</span>
                      {% endif %}
                    </td>
                    <td class="text-center">
                      {% if not solo_lectura %}
                        <a href="{{ url_for('duenos_info', edit=it.id) }}"
                           class="btn btn-warning btn-sm rounded-pill px-3">
                          Editar
                        </a>
                        <a href="{{ url_for('duenos_info_delete', id=it.id) }}"
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
                      <td colspan="7" class="text-center text-muted py-4">
                        Sin registros
                      </td>
                    </tr>
                  {% endif %}
                </tbody>
              </table>
            </div>
          </div>

          {% with msgs = get_flashed_messages(with_categories=true) %}
            {% if msgs %}
              <div class="mt-3">
                {% for cat, msg in msgs %}
                  <div class="alert alert-{{ 'warning' if cat=='message' else cat }} alert-dismissible fade show" role="alert">
                    {{ msg }}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                  </div>
                {% endfor %}
              </div>
            {% endif %}
          {% endwith %}

        </div>
      </div>

    </div>

    <script>
      let pdfBufferDT = new DataTransfer();

      function renderListaNuevos() {
        const cont = document.getElementById('lista_pdf_nuevos');
        if (!cont) return;
        cont.innerHTML = '';

        for (let i = 0; i < pdfBufferDT.files.length; i++) {
          const f = pdfBufferDT.files[i];
          const row = document.createElement('div');
          row.className = 'd-flex align-items-center justify-content-between mb-1';
          row.innerHTML = `
            <span class="text-truncate" style="max-width:260px;">📎 ${f.name}</span>
            <button type="button" class="btn btn-link text-danger p-0" onclick="removeFromBuffer(${i})">🗑️</button>
          `;
          cont.appendChild(row);
        }

        if (pdfBufferDT.files.length === 0) {
          cont.innerHTML = '<div class="text-muted small">No hay archivos nuevos seleccionados</div>';
        }
      }

      function acumularArchivosPDF(inputEl) {
        for (const f of inputEl.files) {
          pdfBufferDT.items.add(f);
        }
        inputEl.files = pdfBufferDT.files;
        renderListaNuevos();
      }

      function removeFromBuffer(index) {
        const tmp = new DataTransfer();
        for (let i = 0; i < pdfBufferDT.files.length; i++) {
          if (i !== index) tmp.items.add(pdfBufferDT.files[i]);
        }
        pdfBufferDT = tmp;
        const inputEl = document.getElementById('acuerdos_pdf');
        if (inputEl) inputEl.files = pdfBufferDT.files;
        renderListaNuevos();
      }

      async function deleteOwnerPdf(ownerId, filename, elementId) {
        if (!confirm('¿Eliminar este PDF?')) return;

        try {
          const url = `/duenos_info/delete_file/${ownerId}/${encodeURIComponent(filename)}`;
          const res = await fetch(url, { method: 'POST' });

          if (res.ok) {
            const row = document.getElementById(elementId);
            if (row) row.remove();
          } else {
            alert('Error al eliminar el PDF.');
          }
        } catch (e) {
          alert('Error de conexión al eliminar el PDF.');
        }
      }

      window.addEventListener('DOMContentLoaded', renderListaNuevos);
    </script>

    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .duenos-shell{
        width:96%;
        max-width:1600px;
        margin:10px auto 24px auto;
      }

      .duenos-header-card{
        background:linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.24);
        color:#fff;
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .duenos-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 26%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 15px);
      }

      .duenos-header-overlay{
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

      .duenos-header-overlay::before{
        content:"👤";
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
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .duenos-header-text{
        max-width:1100px;
        width:100%;
        transform:none;
      }

      .duenos-header-text::before{
        content:"SGSI · Dueños de Información";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
      }

      .duenos-title{
        color:#fff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.08;
        text-shadow:0 3px 10px rgba(0,0,0,.32);
        margin:0 !important;
      }

      .duenos-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .duenos-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin:10px 0 12px;
        flex-wrap:wrap;
      }

      .duenos-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .duenos-back-btn{
        background:#fff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .duenos-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .duenos-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        overflow:hidden;
        border:1px solid rgba(219,230,244,.9);
      }

      .duenos-card-body{
        padding:16px 18px;
      }

      .duenos-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .duenos-card .form-control,
      .duenos-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:37px;
        font-size:.80rem;
        background:#f8fafc;
        box-shadow:none;
      }

      .duenos-card .form-control:focus,
      .duenos-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .18rem rgba(63,134,214,.18);
        background:#fff;
      }

      .duenos-files-box{
        border:1px solid #dbe6f4;
        border-radius:14px;
        padding:12px;
        background:linear-gradient(180deg,#fff 0%,#f8fbff 100%);
        box-shadow:0 6px 14px rgba(15,23,42,.08);
      }

      .duenos-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:18px;
        flex-wrap:wrap;
      }

      .duenos-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .duenos-cancel-btn{
        background:#fff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .duenos-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .duenos-table-wrap{
        max-height:70vh;
        overflow:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#fff;
      }

      .duenos-table{
        width:100%;
        min-width:1200px;
        table-layout:auto;
        margin-bottom:0;
      }

      .duenos-table th,
      .duenos-table td{
        white-space:normal;
        word-break:break-word;
        vertical-align:top;
        font-size:.78rem;
        padding:9px 8px;
      }

      .duenos-table thead th{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#fff !important;
        font-weight:900;
        text-align:center;
      }

      .duenos-table td{
        border-bottom:1px solid #e5edf7;
      }

      .duenos-table tbody tr:nth-child(even){
        background:#f8fbff;
      }

      .duenos-table tbody tr:hover{
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

      .duenos-card .btn{
        box-shadow:0 4px 10px rgba(0,0,0,.08);
        font-weight:900;
        font-size:.78rem;
      }

      @media (max-width:992px){
        .duenos-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .duenos-header-card{
          min-height:88px;
        }

        .duenos-title{
          font-size:1.2rem;
        }

        .duenos-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .duenos-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .duenos-header-overlay::before{
          margin:0;
        }

        .duenos-header-actions .btn,
        .duenos-bottom-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(
        html,
        items=items,
        edit_item=edit_item,
        areas=areas,
        solo_lectura=solo_lectura
    )
    return render_template_string(BASE, content=Markup(inner))


@app.route('/duenos_info/delete')
@login_required
def duenos_info_delete():
    if user.role == 'auditor' or (
        user.role != 'admin'
        and not verificar_permiso_activos(user, "Dueños de Información")
    ):
        flash("No tiene permiso para eliminar dueños de información.", "danger")
        return redirect(url_for('activos_menu'))
    
    rid = request.args.get('id', type=int)
    it = DuenoInformacion.query.get(rid)
    if it:
        # Borrar archivos físicos
        if it.acuerdos_pdf:
            for fname in it.acuerdos_pdf.split(','):
                fp = os.path.join(app.config['UPLOAD_FOLDER'], fname)
                try:
                    if os.path.isfile(fp):
                        os.remove(fp)
                except Exception:
                    pass
        db.session.delete(it)
        db.session.commit()
        flash("Eliminado correctamente.", "success")
    else:
        flash("Registro no encontrado.", "danger")
    return redirect(url_for('duenos_info'))

@app.route('/vista_evidencia/<path:filename>')
@login_required
def vista_evidencia(filename):
    ext = os.path.splitext(filename)[1].lower()
    is_pdf = ext == '.pdf'
    is_office = ext in {'.doc', '.docx', '.xls', '.xlsx'}

    # 1) Determinar a dónde volver (lee ?next=...)
    next_ep = request.args.get('next')  # p.ej. 'duenos_info', 'declaracion_aplicabilidad', etc.
    # Opcional: etiqueta de botón
    back_label_map = {
        'duenos_info': '⬅ Volver a Dueños de la Información',
        'declaracion_aplicabilidad': '⬅ Volver a SoA',
        'soa': '⬅ Volver a SoA',
        'activos_menu': '⬅ Volver a Gestión de Activos',
        'menu': '⬅ Volver al menú principal',
    }
    # Whitelist de endpoints permitidos a los que volver:
    allowed_back = set(back_label_map.keys())

    if next_ep in allowed_back:
        back_url = url_for(next_ep)
        back_label = back_label_map[next_ep]
    else:
        # fallback: intentar referrer o menú
        back_url = request.referrer or url_for('menu')
        back_label = '⬅ Volver'

    pdf_converted = None
    if is_office:
        # genera PDF si hace falta (asegúrate de tener CONVERTED_FOLDER y ensure_pdf_from_office)
        pdf_converted = ensure_pdf_from_office(filename)

    inner_html = """
    <div class="container my-3">
      <!-- Barra superior -->
      <div class="d-flex justify-content-between align-items-center mb-2">
        <a href="{{ back_url }}" class="btn btn-secondary rounded-pill px-4 py-2">
          {{ back_label }}
        </a>
        <div class="small text-muted text-truncate">Archivo: {{ filename }}</div>
      </div>

      <!-- Contenedor del visor -->
      <div class="card shadow-sm">
        <div class="card-body p-2">
          {% if is_pdf %}
            <div class="pdf-container">
              <iframe id="pdfFrame"
                      src="{{ url_for('ver_evidencia', filename=filename) }}#zoom=page-width"
                      title="Visor PDF"></iframe>
            </div>

          {% elif pdf_converted %}
            <div class="pdf-container">
              <iframe id="pdfFrame"
                      src="{{ url_for('ver_evidencia_convertido', filename=pdf_converted) }}#zoom=page-width"
                      title="Visor PDF (convertido)"></iframe>
            </div>
            <div class="mt-2 text-center">
              <a class="btn btn-outline-primary rounded-pill px-4"
                 href="{{ url_for('ver_evidencia', filename=filename) }}" target="_blank" rel="noopener">
                Abrir archivo original
              </a>
            </div>

          {% elif is_office %}
            <div class="alert alert-warning m-2">
              No fue posible generar una vista previa interna del archivo Office.
              Verifica que LibreOffice esté instalado en el servidor.
            </div>
            <div class="text-center mb-2">
              <a class="btn btn-outline-primary rounded-pill px-4"
                 href="{{ url_for('ver_evidencia', filename=filename) }}" target="_blank" rel="noopener">
                Abrir/descargar archivo original
              </a>
            </div>

          {% else %}
            <div class="alert alert-info m-2">
              Este tipo de archivo (<b>{{ ext }}</b>) no se puede previsualizar. Puedes abrirlo/descargarlo.
            </div>
            <div class="text-center mb-2">
              <a class="btn btn-outline-primary rounded-pill px-4"
                 href="{{ url_for('ver_evidencia', filename=filename) }}" target="_blank" rel="noopener">
                Abrir archivo
              </a>
            </div>
          {% endif %}
        </div>
      </div>
    </div>

    <style>
      /* Altura razonable dentro del layout, sin salirse */
      .pdf-container {
        height: min(82vh, 1000px);
        min-height: 600px;
        width: 100%;
      }
      .pdf-container iframe {
        width: 100%;
        height: 100%;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        background: #fff;
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
    <style>
          body {
            background-image: url('/static/img/ccsgsi.jpg'); /* Usa tu imagen */
            background-size: cover;       /* 🔹 ocupa toda la pantalla */
            background-position: center;  /* 🔹 centrada */
            background-attachment: fixed; /* 🔹 efecto de fondo fijo elegante */
            background-repeat: no-repeat;
          }

          /* Fondo suave en las tarjetas para que se lean bien */
          .card {
            background: rgba(255, 255, 255, 0.85) !important;
            backdrop-filter: blur(4px);
          }
        </style>
    """

    return render_template_string(
        BASE,
        content=Markup(render_template_string(
            inner_html,
            filename=filename,
            ext=ext,
            is_pdf=is_pdf,
            is_office=is_office,
            pdf_converted=pdf_converted,
            back_url=back_url,
            back_label=back_label
        ))
    )


@app.route('/duenos_info/delete_file/<int:owner_id>/<path:filename>', methods=['POST'])
@login_required
def duenos_info_delete_file(owner_id, filename):
    it = DuenoInformacion.query.get(owner_id)
    if not it:
        flash("Registro no encontrado.", "danger")
        return redirect(url_for('duenos_info'))

    lst = [f for f in (it.acuerdos_pdf.split(',') if it.acuerdos_pdf else []) if f]
    if filename in lst:
        # borrar físicamente
        fp = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        try:
            if os.path.isfile(fp):
                os.remove(fp)
        except Exception:
            pass
        # actualizar campo
        lst.remove(filename)
        it.acuerdos_pdf = ",".join(lst)
        db.session.add(it)
        db.session.commit()
        flash("Archivo eliminado.", "success")
    else:
        flash("Archivo no encontrado en el registro.", "warning")

    return redirect(url_for('duenos_info'))

# =========================
# ENTRADA DIRECTA — Inventario de Información
# =========================
@app.route('/inventario_informacion_menu')
@login_required
def inventario_informacion_menu():
    user = User.query.get(session.get('user_id'))

    if user.role not in ('admin', 'auditor') and not verificar_permiso(user, "Gestión de Activos de Información"):
        flash("No tiene permiso para acceder al módulo de inventarios de Información.", "danger")
        return redirect(url_for('activos_menu'))

    return redirect(url_for('inventario_informacion'))


# =========================
# Agregar — Inventario de Información
# =========================
@app.route('/inventario_informacion/new', methods=['GET', 'POST'])
@login_required
def inventario_informacion_new():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede agregar registros.", "danger")
        return redirect(url_for('inventario_informacion'))

    if user.role != 'admin' and not verificar_permiso(user, "Gestión de Activos de Información"):
        flash("No tiene permiso para agregar registros de activos.", "danger")
        return redirect(url_for('inventario_informacion'))
    
    conf_opts = ValoracionConfidencialidad.query.order_by(ValoracionConfidencialidad.nivel_num.asc()).all()
    inte_opts = ValoracionIntegridad.query.order_by(ValoracionIntegridad.nivel_num.asc()).all()
    disp_opts = ValoracionDisponibilidad.query.order_by(ValoracionDisponibilidad.nivel_num.asc()).all()
    crit_opts = ValoracionCriticidadActivo.query.order_by(ValoracionCriticidadActivo.nivel_num.asc()).all()
    areas = AreaEmpresa.query.order_by(AreaEmpresa.area.asc()).all()

    duenos_info_opts = (
        DuenoInformacion.query
        .order_by(DuenoInformacion.dueno_nombre.asc())
        .all()
    )

    if request.method == 'POST':
        area_id = request.form.get('area_id', type=int)
        division = (request.form.get('division') or "").strip()
        proceso = (request.form.get('proceso') or "").strip()
        nombre_activo = (request.form.get('nombre_activo') or "").strip()
        descripcion = (request.form.get('descripcion') or "").strip()

        formato = request.form.get('formato') or "Digital"
        ubicacion_digital = (request.form.get('ubicacion_digital') or "").strip()
        accesos_autorizados = (request.form.get('accesos_autorizados') or "").strip()

        lectura = request.form.get('lectura') or "No"
        escritura = request.form.get('escritura') or "No"
        eliminacion = request.form.get('eliminacion') or "No"

        propietario = (request.form.get('propietario') or "").strip()

        try:
            c_nivel = int(request.form.get('c_nivel') or 0)
            i_nivel = int(request.form.get('i_nivel') or 0)
            d_nivel = int(request.form.get('d_nivel') or 0)
        except ValueError:
            c_nivel = i_nivel = d_nivel = 0

        info_personal = request.form.get('info_personal') or "No"
        info_regulada = request.form.get('info_regulada') or "No"
        info_sensible = request.form.get('info_sensible') or "No"
        info_sensible_clientes = request.form.get('info_sensible_clientes') or "No"

        observaciones = (request.form.get('observaciones') or "").strip()

        if not (area_id and proceso and nombre_activo and descripcion and propietario):
            flash("Campos obligatorios: Área, Proceso, Nombre del Activo, Descripción y Propietario.", "danger")
            return redirect(url_for('inventario_informacion_new'))

        for n in (c_nivel, i_nivel, d_nivel):
            if n < 1 or n > 5:
                flash("Los niveles numéricos deben estar entre 1 y 5.", "danger")
                return redirect(url_for('inventario_informacion_new'))

        valor_activo = round((c_nivel + i_nivel + d_nivel) / 3)

        conf_row = ValoracionConfidencialidad.query.filter_by(nivel_num=c_nivel).first()
        etiqueta_conf_num = c_nivel
        etiqueta_conf_texto = conf_row.clasificacion if conf_row else f"Nivel {c_nivel}"

        crit_row = ValoracionCriticidadActivo.query.filter_by(nivel_num=valor_activo).first()
        criticidad_num = valor_activo
        criticidad_texto = crit_row.nivel_texto if crit_row else f"Nivel {valor_activo}"

        it = InventarioInformacion(
            area_id=area_id,
            division=division,
            proceso=proceso,
            nombre_activo=nombre_activo,
            descripcion=descripcion,
            formato=formato,
            ubicacion_digital=ubicacion_digital,
            accesos_autorizados=accesos_autorizados,
            lectura=lectura,
            escritura=escritura,
            eliminacion=eliminacion,
            propietario=propietario,
            c_nivel=c_nivel,
            i_nivel=i_nivel,
            d_nivel=d_nivel,
            valor_activo=valor_activo,
            criticidad_num=criticidad_num,
            criticidad_texto=criticidad_texto,
            etiqueta_conf_num=etiqueta_conf_num,
            etiqueta_conf_texto=etiqueta_conf_texto,
            info_personal=info_personal,
            info_regulada=info_regulada,
            info_sensible=info_sensible,
            info_sensible_clientes=info_sensible_clientes,
            observaciones=observaciones
        )
        db.session.add(it)
        db.session.commit()
        flash("Activo de información creado.", "success")
        return redirect(url_for('inventario_informacion'))

    html = """
    <div class="invinfo-shell">

      <div class="invinfo-header-card">
        <div class="invinfo-header-overlay">
          <div class="invinfo-header-text">
            <h3 class="invinfo-title m-0">Registro — Inventario de Información</h3>
            <div class="invinfo-subtitle">
              Registro y clasificación de activos de información del Sistema de Gestión de Seguridad de la Información
            </div>
          </div>
        </div>
      </div>

      <div class="invinfo-header-actions">
        <a href="{{ url_for('inventario_informacion') }}"
           class="btn rounded-pill px-4 fw-bold invinfo-back-btn">
          ⬅ Volver a la Matriz
        </a>

      </div>

      <div class="invinfo-card">
        <div class="invinfo-card-body">
          <form method="post">
            <div class="row g-3">

              <div class="col-md-3">
                <label class="form-label">Área</label>
                <select name="area_id" id="area_id" class="form-select" required>
                  <option value="">-- Seleccione --</option>
                  {% for a in areas %}
                    <option value="{{ a.id }}">{{ a.area }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">División</label>
                <select name="division" id="division" class="form-select">
                  <option value="">-- Seleccione --</option>
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">Proceso</label>
                <input type="text" name="proceso" class="form-control" required>
              </div>

              <div class="col-md-3">
                <label class="form-label">Nombre del Activo</label>
                <input type="text" name="nombre_activo" class="form-control" required>
              </div>

              <div class="col-md-3">
                <label class="form-label">Propietario</label>
                <select name="propietario" class="form-select" required>
                  <option value="">-- Seleccione cargo del dueño de información --</option>
                  {% for d in duenos_info_opts %}
                    <option value="{{ d.dueno_cargo }}">
                      {{ d.dueno_cargo }}{% if d.dueno_nombre %} — {{ d.dueno_nombre }}{% endif %}{% if d.area %} ({{ d.area.area }}){% endif %}
                    </option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-12">
                <label class="form-label">Descripción</label>
                <textarea name="descripcion" class="form-control" rows="2" required></textarea>
              </div>

              <div class="col-md-3">
                <label class="form-label">Formato</label>
                <select name="formato" class="form-select">
                  <option value="Digital">Digital</option>
                  <option value="Físico">Físico</option>
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">Ubicación Digital</label>
                <input type="text" name="ubicacion_digital" class="form-control">
              </div>

              <div class="col-md-6">
                <label class="form-label">Accesos Autorizados</label>
                <input type="text" name="accesos_autorizados" class="form-control">
              </div>

              <div class="col-md-2">
                <label class="form-label">Lectura / Consulta</label>
                <select name="lectura" class="form-select">
                  <option value="Sí">Sí</option>
                  <option value="No">No</option>
                </select>
              </div>

              <div class="col-md-2">
                <label class="form-label">Escritura</label>
                <select name="escritura" class="form-select">
                  <option value="Sí">Sí</option>
                  <option value="No">No</option>
                </select>
              </div>

              <div class="col-md-2">
                <label class="form-label">Eliminación</label>
                <select name="eliminacion" class="form-select">
                  <option value="Sí">Sí</option>
                  <option value="No">No</option>
                </select>
              </div>

              <div class="col-md-2">
                <label class="form-label">Clasificación Confidencialidad</label>
                <select name="c_nivel" class="form-select">
                  {% for o in conf_opts %}
                    <option value="{{ o.nivel_num }}">{{ o.nivel_num }} — {{ o.clasificacion }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-2">
                <label class="form-label">Clasificación Integridad</label>
                <select name="i_nivel" class="form-select">
                  {% for o in inte_opts %}
                    <option value="{{ o.nivel_num }}">{{ o.nivel_num }} — {{ o.nivel }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-2">
                <label class="form-label">Clasificación Disponibilidad</label>
                <select name="d_nivel" class="form-select">
                  {% for o in disp_opts %}
                    <option value="{{ o.nivel_num }}">{{ o.nivel_num }} — {{ o.nivel }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-2">
                <label class="form-label">¿Es Información Personal?</label>
                <select name="info_personal" class="form-select">
                  <option value="Sí">Sí</option>
                  <option value="No">No</option>
                </select>
              </div>

              <div class="col-md-2">
                <label class="form-label">¿Regulada por legislación?</label>
                <select name="info_regulada" class="form-select">
                  <option value="Sí">Sí</option>
                  <option value="No">No</option>
                </select>
              </div>

              <div class="col-md-2">
                <label class="form-label">¿Información sensible de la Compañía?</label>
                <select name="info_sensible" class="form-select">
                  <option value="Sí">Sí</option>
                  <option value="No">No</option>
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">¿Información sensible de Clientes?</label>
                <select name="info_sensible_clientes" class="form-select">
                  <option value="Sí">Sí</option>
                  <option value="No">No</option>
                </select>
              </div>

              <div class="col-md-12">
                <label class="form-label">Observaciones</label>
                <textarea name="observaciones" class="form-control" rows="2"></textarea>
              </div>

            </div>

            <div class="invinfo-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar
              </button>
              <a href="{{ url_for('inventario_informacion') }}"
                 class="btn rounded-pill px-4 fw-bold invinfo-cancel-btn">
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

      .invinfo-shell{
        width:96%;
        max-width:1500px;
        margin:10px auto 24px auto;
      }

      .invinfo-header-card{
        background:linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.24);
        color:#fff;
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
      }

      .invinfo-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 26%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 15px);
      }

      .invinfo-header-overlay{
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

      .invinfo-header-overlay::before{
        content:"📚";
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
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .invinfo-header-text::before{
        content:"SGSI · Inventario de Información";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
      }

      .invinfo-title{
        color:#fff !important;
        font-weight:950;
        font-size:1.32rem;
        margin:0 !important;
      }

      .invinfo-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
      }

      .invinfo-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px;
      }

      .invinfo-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .invinfo-back-btn{
        background:#fff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .invinfo-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .invinfo-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        overflow:hidden;
        border:1px solid rgba(219,230,244,.9);
      }

      .invinfo-card-body{
        padding:16px 18px;
      }

      .invinfo-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .invinfo-card .form-control,
      .invinfo-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:37px;
        font-size:.80rem;
        background:#f8fafc;
        box-shadow:none;
      }

      .invinfo-card textarea.form-control{
        min-height:70px;
        resize:vertical;
      }

      .invinfo-card .form-control:focus,
      .invinfo-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .18rem rgba(63,134,214,.18);
        background:#fff;
      }

      .invinfo-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:18px;
        flex-wrap:wrap;
      }

      .invinfo-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .invinfo-cancel-btn{
        background:#fff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .invinfo-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      @media (max-width:992px){
        .invinfo-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .invinfo-header-card{
          min-height:88px;
        }

        .invinfo-title{
          font-size:1.2rem;
        }

        .invinfo-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .invinfo-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .invinfo-header-overlay::before{
          margin:0;
        }

        .invinfo-header-actions .btn,
        .invinfo-bottom-actions .btn{
          width:100%;
        }
      }
    </style>

    <script>
      function cargarDivisionesPorArea() {
        const areaSel = document.getElementById('area_id');
        const divSel  = document.getElementById('division');

        if (!areaSel || !divSel) return;

        const areaId = areaSel.value;
        divSel.innerHTML = '<option value="">-- Seleccione --</option>';

        if (!areaId) return;

        fetch(`/areas/${areaId}/divisiones_json`)
          .then(r => r.json())
          .then(data => {
            if (!data.divisiones || data.divisiones.length === 0) {
              divSel.innerHTML = '<option value="">(Sin divisiones para esta área)</option>';
              return;
            }

            divSel.innerHTML = '<option value="">-- Seleccione --</option>';
            data.divisiones.forEach(d => {
              const opt = document.createElement('option');
              opt.value = d.nombre;
              opt.textContent = d.nombre;
              divSel.appendChild(opt);
            });
          })
          .catch(err => {
            console.error('Error cargando divisiones:', err);
            divSel.innerHTML = '<option value="">Error cargando divisiones</option>';
          });
      }

      document.addEventListener('DOMContentLoaded', () => {
        const areaSel = document.getElementById('area_id');
        if (areaSel) {
          areaSel.addEventListener('change', cargarDivisionesPorArea);
        }
      });
    </script>
    """
    inner = render_template_string(
        html,
        conf_opts=conf_opts,
        inte_opts=inte_opts,
        disp_opts=disp_opts,
        crit_opts=crit_opts,
        areas=areas,
        duenos_info_opts=duenos_info_opts
    )
    return render_template_string(BASE, content=Markup(inner))


# =========================
# EDICIÓN — Inventario de Información
# =========================
