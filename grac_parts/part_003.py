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
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

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


      /* GRAC v10 — Centro de Control: misma barra de iconos y expansión que el menú global. */
      :root {
        --grac-rail-width:64px;
        --grac-menu-expanded-width:245px;
        --sgsi-sidebar-w:var(--grac-rail-width);
      }
      .sgsi-layout,
      body.sgsi-menu-collapsed .sgsi-layout {
        grid-template-columns:var(--grac-rail-width) minmax(0,1fr) !important;
        gap:16px !important;
      }
      body.grac-menu-pinned .sgsi-layout {
        grid-template-columns:var(--grac-menu-expanded-width) minmax(0,1fr) !important;
      }
      #sgsiLocalMenu {
        box-sizing:border-box !important;
        position:sticky !important;
        top:var(--arky-topbar-h,58px) !important;
        width:var(--grac-rail-width) !important;
        height:calc(100vh - var(--arky-topbar-h,58px)) !important;
        z-index:150 !important;
        transition:width .22s ease !important;
      }
      #sgsiLocalMenu .sgsi-leftnav-card,
      body.sgsi-menu-collapsed #sgsiLocalMenu .sgsi-leftnav-card {
        box-sizing:border-box !important;
        width:var(--grac-rail-width) !important;
        height:100% !important;
        max-height:100% !important;
        padding:8px 5px !important;
        opacity:1 !important;
        transform:none !important;
        pointer-events:auto !important;
        overflow-y:auto !important;
        overflow-x:hidden !important;
        scrollbar-width:none;
        transition:width .22s ease !important;
      }
      #sgsiLocalMenu:is(:hover, :has(:focus-visible)),
      body.grac-menu-pinned #sgsiLocalMenu,
      #sgsiLocalMenu:is(:hover, :has(:focus-visible)) .sgsi-leftnav-card,
      body.grac-menu-pinned #sgsiLocalMenu .sgsi-leftnav-card {
        width:var(--grac-menu-expanded-width) !important;
      }
      #sgsiLocalMenu:is(:hover, :has(:focus-visible)) .sgsi-leftnav-card,
      body.grac-menu-pinned #sgsiLocalMenu .sgsi-leftnav-card {
        scrollbar-width:thin;
      }
      #sgsiLocalMenu .sgsi-leftnav-card::-webkit-scrollbar {width:0 !important;}
      #sgsiLocalMenu:is(:hover, :has(:focus-visible)) .sgsi-leftnav-card::-webkit-scrollbar,
      body.grac-menu-pinned #sgsiLocalMenu .sgsi-leftnav-card::-webkit-scrollbar {width:6px !important;}
      #sgsiLocalMenu .sgsi-leftnav-link,
      #sgsiLocalMenu a.sgsi-panel-control-btn,
      #sgsiLocalMenu button.sgsi-root-toggle {
        box-sizing:border-box !important;
        width:46px !important;
        max-width:46px !important;
        min-width:46px !important;
        min-height:38px !important;
        height:38px !important;
        margin:0 auto !important;
        padding:0 !important;
        display:flex !important;
        align-items:center !important;
        justify-content:center !important;
        gap:0 !important;
        overflow:hidden !important;
      }
      #sgsiLocalMenu .sgsi-leftnav-link > i {
        box-sizing:border-box !important;
        flex:0 0 20px !important;
        width:20px !important;
        text-align:center !important;
        font-size:1.05rem !important;
      }
      #sgsiLocalMenu .sgsi-leftnav-link > span,
      #sgsiLocalMenu .sgsi-dropdown-item > span {
        display:none !important;
      }
      #sgsiLocalMenu .sgsi-root-toggle::after,
      #sgsiLocalMenu .sgsi-node-toggle::after {
        display:none !important;
      }
      #sgsiLocalMenu .sgsi-panel.sgsi-open {
        display:none !important;
      }
      #sgsiLocalMenu:is(:hover, :has(:focus-visible)) .sgsi-panel.sgsi-open,
      body.grac-menu-pinned #sgsiLocalMenu .sgsi-panel.sgsi-open {
        display:block !important;
      }
      #sgsiLocalMenu:is(:hover, :has(:focus-visible)) .sgsi-leftnav-link,
      #sgsiLocalMenu:is(:hover, :has(:focus-visible)) a.sgsi-panel-control-btn,
      body.grac-menu-pinned #sgsiLocalMenu .sgsi-leftnav-link,
      body.grac-menu-pinned #sgsiLocalMenu a.sgsi-panel-control-btn {
        width:100% !important;
        max-width:100% !important;
        min-width:0 !important;
        margin:0 !important;
        padding:0 8px !important;
        justify-content:flex-start !important;
        gap:7px !important;
      }
      #sgsiLocalMenu:is(:hover, :has(:focus-visible)) .sgsi-leftnav-link > span,
      #sgsiLocalMenu:is(:hover, :has(:focus-visible)) .sgsi-dropdown-item > span,
      body.grac-menu-pinned #sgsiLocalMenu .sgsi-leftnav-link > span,
      body.grac-menu-pinned #sgsiLocalMenu .sgsi-dropdown-item > span {
        display:block !important;
        min-width:0 !important;
        flex:1 1 auto !important;
        white-space:normal !important;
      }
      #sgsiLocalMenu:is(:hover, :has(:focus-visible)) .sgsi-root-toggle::after,
      #sgsiLocalMenu:is(:hover, :has(:focus-visible)) .sgsi-node-toggle::after,
      body.grac-menu-pinned #sgsiLocalMenu .sgsi-root-toggle::after,
      body.grac-menu-pinned #sgsiLocalMenu .sgsi-node-toggle::after {
        display:block !important;
      }
      #sgsiLocalMenu .sgsi-leftnav-arrow,
      body.sgsi-menu-collapsed #sgsiLocalMenu .sgsi-leftnav-arrow {
        right:-11px !important;
        pointer-events:auto !important;
        transition:right .22s ease !important;
      }
      #sgsiLocalMenu:is(:hover, :has(:focus-visible)) .sgsi-leftnav-arrow,
      body.grac-menu-pinned #sgsiLocalMenu .sgsi-leftnav-arrow {
        right:-12px !important;
      }
      #sgsiLocalMenu .sgsi-arrow-icon {transform:none !important;}
      body.grac-menu-pinned #sgsiLocalMenu .sgsi-arrow-icon {transform:rotate(180deg) !important;}
      @media(max-width:1200px) {
        .sgsi-layout,
        body.sgsi-menu-collapsed .sgsi-layout {
          grid-template-columns:var(--grac-rail-width) minmax(0,1fr) !important;
        }
        body.grac-menu-pinned .sgsi-layout {
          grid-template-columns:var(--grac-rail-width) minmax(0,1fr) !important;
        }
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

      });
    </script>

    <script id="grac-hover-menu-v11">
      (function(){
        // El menú se controla únicamente con hover/foco: sin flecha de fijación.
        var menu = document.getElementById('sgsiGlobalMenu') || document.getElementById('sgsiLocalMenu');
        if (!menu) return;
        document.body.classList.remove('grac-menu-pinned', 'sgsi-menu-collapsed');
        // Elimina cualquier preferencia previa de fijación de la versión anterior.
        try {sessionStorage.removeItem('grac_menu_pinned_v10');} catch(e) {}
        // Conserva los nombres accesibles de los iconos cuando está contraído.
        menu.querySelectorAll('a,button').forEach(function(control){
          var labelNode = control.querySelector('span');
          var name = labelNode ? labelNode.textContent.trim() : '';
          if(name){
            control.setAttribute('aria-label',name);
            control.setAttribute('title',name);
          }
        });
      })();
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


def alert_metric_value(metric_key):
    """Obtiene datos de los módulos reales; no utiliza cifras escritas en la regla."""
    metric_key = str(metric_key or "").strip()
    if metric_key == "risks_outside_appetite_inclusive":
        risks = _dashboard_active_risks()
        try:
            cfg = MetricConfigRiesgos.query.first()
            appetite = _dashboard_risk_rank(
                getattr(cfg, "apetito_residual_definido", "") if cfg else ""
            ) or 2
        except Exception:
            appetite = 2
        # Regla corporativa: residual MAYOR O IGUAL al apetito.
        return float(sum(
            1 for risk in risks
            if _dashboard_risk_rank(getattr(risk, "riesgo_residual", "")) >= appetite
        ))
    if metric_key == "vulnerabilities_overdue_count":
        return alert_vulnerabilities_overdue_count()
    if metric_key == "documents_overdue_count":
        return alert_documents_overdue_count()
    if metric_key == "documents_due_soon_count":
        return alert_documents_due_soon_count()
    if metric_key == "wazuh_high_count":
        model = globals().get("WazuhAlert")
        if not model:
            return 0.0
        since = datetime.utcnow() - datetime_module.timedelta(hours=24)
        return float(model.query.filter(model.rule_level >= 10, model.synced_at >= since).count())
    if metric_key == "firewall_critical_count":
        model = globals().get("FirewallGovFinding")
        if not model:
            return 0.0
        try:
            rows = model.query.filter(model.active.is_(True)).all()
            return float(sum(
                1 for row in rows
                if alert_plain(getattr(row, "severity", "")) in {"critica", "critical"}
                and alert_plain(getattr(row, "status", ""))
                not in {"resuelto", "resuelta", "cerrado", "cerrada"}
            ))
        except Exception:
            db.session.rollback()
            return 0.0
    if metric_key in {"bcp_backups_failed_count", "bcp_systems_without_drp_count"}:
        calculator = globals().get("bcp_metricas_actuales")
        if not calculator:
            return 0.0
        try:
            data = calculator() or {}
            key = "backups_fallidos" if metric_key == "bcp_backups_failed_count" else "sistemas_sin_drp"
            return float(data.get(key, 0) or 0)
        except Exception:
            return 0.0
    return float(_dashboard_metric_value(metric_key) or 0)


def alert_format_number(value):
    number = float(value or 0)
    return str(int(number)) if number.is_integer() else f"{number:.2f}"


_SMTP_LETSENCRYPT_Y_CHAIN_CACHE = None
_SMTP_LETSENCRYPT_Y_CHAIN_LOCK = threading.Lock()
_SMTP_LETSENCRYPT_Y_CHAIN_CERTS = (
    {
        "url": "https://letsencrypt.org/certs/gen-y/int-yr1.pem",
        "subject_cn": "YR1",
        "issuer_cn": "Root YR",
        "serial": "A20253F15F2691C05DC1CE13B9BCCA4E",
        "sha256": None,
    },
    {
        "url": "https://letsencrypt.org/certs/gen-y/int-yr2.pem",
        "subject_cn": "YR2",
        "issuer_cn": "Root YR",
        "serial": "4EBD24947E24D394802D84A52FD5B319",
        "sha256": "238B85A0099C65B970477D5724F1A1D475CE5058CFFE4EFA8733899BDB863C47",
    },
    {
        "url": "https://letsencrypt.org/certs/gen-y/root-yr-by-x1.pem",
        "subject_cn": "Root YR",
        "issuer_cn": "ISRG Root X1",
        "serial": "F24B6D17F9D9AD7CB1C9FEA78782699F",
        "sha256": None,
    },
)


def _smtp_certificate_common_name(name):
    values = name.get_attributes_for_oid(NameOID.COMMON_NAME)
    return values[0].value if values else ""


def _smtp_letsencrypt_y_chain():
    """Descarga y valida la cadena oficial que el servidor SMTP omite.

    Los certificados se obtienen exclusivamente desde letsencrypt.org mediante
    HTTPS, se validan por identidad/serie y se conservan en memoria. Nunca se
    desactiva la verificación TLS ni se transmiten credenciales en este proceso.
    """
    global _SMTP_LETSENCRYPT_Y_CHAIN_CACHE
    if _SMTP_LETSENCRYPT_Y_CHAIN_CACHE:
        return _SMTP_LETSENCRYPT_Y_CHAIN_CACHE

    with _SMTP_LETSENCRYPT_Y_CHAIN_LOCK:
        if _SMTP_LETSENCRYPT_Y_CHAIN_CACHE:
            return _SMTP_LETSENCRYPT_Y_CHAIN_CACHE

        certificates = []
        for expected in _SMTP_LETSENCRYPT_Y_CHAIN_CERTS:
            response = requests.get(
                expected["url"],
                timeout=10,
                allow_redirects=False,
                headers={"User-Agent": "Arkyntech-GRAC/SMTP-Chain-Repair"},
            )
            response.raise_for_status()
            if len(response.content) > 32768:
                raise RuntimeError("El certificado intermedio descargado supera el tamaño permitido.")
            try:
                pem = response.content.decode("ascii").strip() + "\n"
                certificate = x509.load_pem_x509_certificate(pem.encode("ascii"))
            except Exception as exc:
                raise RuntimeError("Let’s Encrypt no devolvió un certificado PEM válido.") from exc

            subject_cn = _smtp_certificate_common_name(certificate.subject)
            issuer_cn = _smtp_certificate_common_name(certificate.issuer)
            serial = f"{certificate.serial_number:X}"
            fingerprint = certificate.fingerprint(hashes.SHA256()).hex().upper()
            if (
                subject_cn != expected["subject_cn"]
                or issuer_cn != expected["issuer_cn"]
                or serial != expected["serial"]
                or (expected["sha256"] and fingerprint != expected["sha256"])
            ):
                raise RuntimeError("La identidad del certificado intermedio descargado no coincide con la publicada.")
            certificates.append(pem)

        _SMTP_LETSENCRYPT_Y_CHAIN_CACHE = "".join(certificates)
        return _SMTP_LETSENCRYPT_Y_CHAIN_CACHE


def alert_smtp_ssl_context(host):
    """Contexto TLS estricto con soporte para la cadena incompleta de Arkyntech."""
    context_ssl = ssl.create_default_context()

    # Permite instalar una CA administrada por el cliente sin cambiar el código.
    custom_ca_file = (os.getenv("GRAC_SMTP_CA_FILE") or "").strip()
    if custom_ca_file:
        context_ssl.load_verify_locations(cafile=custom_ca_file)

    compatibility_enabled = str(
        os.getenv("GRAC_SMTP_LETSENCRYPT_Y_COMPAT", "1")
    ).strip().lower() not in {"0", "false", "no", "off"}
    if compatibility_enabled and str(host or "").strip().lower() == "mail.arkyntech.com":
        try:
            context_ssl.load_verify_locations(cadata=_smtp_letsencrypt_y_chain())

            # mail.arkyntech.com no entrega la cadena completa. Los certificados
            # oficiales de Let's Encrypt cargados y validados arriba se aceptan
            # como punto de confianza explícito para completar esa cadena, sin
            # desactivar la verificación del certificado ni del nombre del host.
            if hasattr(ssl, "VERIFY_X509_PARTIAL_CHAIN"):
                context_ssl.verify_flags |= ssl.VERIFY_X509_PARTIAL_CHAIN
            if hasattr(ssl, "VERIFY_X509_TRUSTED_FIRST"):
                context_ssl.verify_flags |= ssl.VERIFY_X509_TRUSTED_FIRST
        except Exception as exc:
            # Conserva el contexto seguro normal. Si el servidor continúa con
            # la cadena incompleta, Python bloqueará el envío antes del login.
            app.logger.warning(
                "No fue posible cargar la cadena complementaria SMTP de Let's Encrypt: %r",
                exc,
            )
    return context_ssl


def alert_send_email(subject, text_body, html_body=None, recipients=None):
    smtp = get_email_config()
    host = smtp.get("SMTP_HOST")
    port = int(smtp.get("SMTP_PORT") or 587)
    username = smtp.get("SMTP_USER")
    password = smtp.get("SMTP_PASS")
    sender = smtp.get("SMTP_FROM") or username
    if not host or not username or not password or not sender:
        raise RuntimeError("La configuración SMTP de Parámetros Generales está incompleta.")
    recipients = recipients or alert_parse_recipients(alert_get_config().recipients)[0]
    if not recipients:
        raise RuntimeError("No hay correos destinatarios configurados en Administración de Alertas.")
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message.set_content(text_body)
    if html_body:
        message.add_alternative(html_body, subtype="html")
    context_ssl = alert_smtp_ssl_context(host)
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=context_ssl, timeout=30) as smtp_client:
            smtp_client.login(username, password)
            smtp_client.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=30) as smtp_client:
            smtp_client.ehlo()
            smtp_client.starttls(context=context_ssl)
            smtp_client.ehlo()
            smtp_client.login(username, password)
            smtp_client.send_message(message)


def alert_event_email(event, recipients):
    cfg = alert_get_config()
    prefix = (cfg.subject_prefix or "[Arkyntech GRAC]").strip()
    subject = f"{prefix} {event.severity.upper()} - {event.title}"
    configured_base = (cfg.base_url or "").strip().rstrip("/")
    target = (event.reference_url or "").strip()
    link = f"{configured_base}{target}" if configured_base and target.startswith("/") else target
    text_body = (
        f"Arkyntech GRAC - Centro de Alertas\n\n"
        f"Severidad: {event.severity.title()}\nMódulo: {event.module}\n"
        f"Alerta: {event.title}\n{event.message}\n"
        f"Valor observado: {alert_format_number(event.value)}\n"
        f"Fecha: {event.last_seen_at.strftime('%Y-%m-%d %H:%M')}\n"
        + (f"Consultar: {link}\n" if link else "")
    )
    html_body = f"""
    <div style="font-family:Arial,sans-serif;background:#f3f7fc;padding:24px;color:#172033">
      <div style="max-width:680px;margin:auto;background:#fff;border-radius:16px;overflow:hidden;border:1px solid #dce7f5">
        <div style="padding:22px;background:linear-gradient(135deg,#063463,#0b63b6);color:#fff">
          <div style="font-size:12px;font-weight:700;opacity:.9">ARKYNTECH GRAC · CENTRO DE ALERTAS</div>
          <h2 style="margin:8px 0 0">{escape(event.title)}</h2>
        </div>
        <div style="padding:24px">
          <p><b>Severidad:</b> {escape(event.severity.title())}</p>
          <p><b>Módulo:</b> {escape(event.module)}</p>
          <p>{escape(event.message)}</p>
          <div style="padding:14px;border-radius:10px;background:#eef5ff"><b>Valor observado:</b> {alert_format_number(event.value)}</div>
          {f'<p style="margin-top:22px"><a href="{escape(link)}" style="background:#0b63b6;color:white;text-decoration:none;padding:11px 18px;border-radius:9px;font-weight:700">Consultar en GRAC</a></p>' if link else ''}
        </div>
      </div>
    </div>"""
    alert_send_email(subject, text_body, html_body, recipients)


def alert_evaluate_all(send_emails=True, force_email=False):
    alert_seed_defaults()
    cfg = alert_get_config()
    recipients, _ = alert_parse_recipients(cfg.recipients)
    now = datetime.utcnow()
    summary = {"evaluated": 0, "triggered": 0, "created": 0, "resolved": 0,
               "emails_sent": 0, "email_errors": 0}
    for rule in AlertRule.query.filter_by(enabled=True).order_by(AlertRule.id.asc()).all():
        summary["evaluated"] += 1
        try:
            value = alert_metric_value(rule.metric_key)
        except Exception as exc:
            db.session.rollback()
            app.logger.warning("No se pudo evaluar alerta %s: %r", rule.code, exc)
            continue
        fingerprint = f"{rule.code}:global"
        event = AlertEvent.query.filter_by(fingerprint=fingerprint).first()
        triggered = alert_compare(value, rule.operator, rule.threshold)
        if not triggered:
            if event and event.status not in {"resuelta", "descartada"}:
                event.status = "resuelta"
                event.resolved_at = now
                event.resolved_by = "Sistema"
                event.last_seen_at = now
                summary["resolved"] += 1
                db.session.commit()
            continue

        summary["triggered"] += 1
        message = alert_documents_message(rule.metric_key, value) or (
            f"Se detectó {alert_format_number(value)}. "
            f"La regla configurada es valor {rule.operator} {alert_format_number(rule.threshold)}."
        )
        if not event:
            event = AlertEvent(
                rule_id=rule.id, fingerprint=fingerprint, title=rule.name,
                message=message, module=rule.module, severity=rule.severity,
                status="nueva", value=value, threshold=rule.threshold,
                reference_url=ALERT_RULE_URLS.get(rule.code, ""),
                first_seen_at=now, last_seen_at=now,
            )
            db.session.add(event)
            db.session.commit()
            summary["created"] += 1
        else:
            if event.status in {"resuelta", "descartada"}:
                event.status = "nueva"
                event.first_seen_at = now
                event.resolved_at = None
                event.resolved_by = None
                event.acknowledged_at = None
                event.acknowledged_by = None
            event.rule_id = rule.id
            event.title = rule.name
            event.message = message
            event.module = rule.module
            event.severity = rule.severity
            event.value = value
            event.threshold = rule.threshold
            event.last_seen_at = now
            event.occurrence_count = int(event.occurrence_count or 0) + 1
            event.reference_url = ALERT_RULE_URLS.get(rule.code, event.reference_url or "")
            db.session.commit()

        repeat_after = datetime_module.timedelta(minutes=max(5, int(rule.repeat_minutes or 1440)))
        email_due = force_email or not event.last_email_at or (now - event.last_email_at >= repeat_after)
        if send_emails and cfg.email_enabled and rule.email_enabled and recipients and email_due:
            delivery = AlertDelivery(event_id=event.id, recipients=", ".join(recipients), status="pendiente")
            db.session.add(delivery)
            db.session.commit()
            try:
                alert_event_email(event, recipients)
                delivery.status = "enviado"
                delivery.sent_at = datetime.utcnow()
                event.last_email_at = delivery.sent_at
                event.last_email_status = "enviado"
                event.last_email_error = None
                summary["emails_sent"] += 1
            except Exception as exc:
                delivery.status = "fallido"
                delivery.error = str(exc)[:2000]
                event.last_email_status = "fallido"
                event.last_email_error = str(exc)[:2000]
                summary["email_errors"] += 1
                app.logger.warning("Falló correo de alerta %s: %r", rule.code, exc)
            db.session.commit()
    return summary


def alert_status_badge(status):
    return {
        "nueva": "danger", "leida": "primary", "reconocida": "warning text-dark",
        "en tratamiento": "info text-dark", "resuelta": "success", "descartada": "secondary",
    }.get(alert_plain(status), "secondary")


ALERT_MODULE_PERMISSIONS = {
    "Riesgos": "Gestión de Riesgos",
    "Vulnerabilidades": "Registro de Vulnerabilidades",
    "Incidentes": "Registro de Incidentes",
    "Planes de acción": "Planes de acción del SGSI",
    "Requisitos legales": "Requisitos Legales",
    "Proveedores": "Registro de Proveedores",
    "Documentación": "Listado Maestro de Documentos",
    "Madurez": "Métricas",
    "Cumplimiento continuo": "Cumplimiento Continuo",
    "Gobierno de Firewall": "Cumplimiento Continuo",
    "Continuidad": "Continuidad del Negocio (BCP/DRP)",
}


ALERT_PAGE_HEADER_STYLES = """
<style>
  .grac-alert-header-card {
    background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
    border-radius:18px;
    padding:16px 24px;
    min-height:94px;
    display:flex;
    align-items:center;
    box-shadow:0 12px 24px rgba(15,23,42,.25);
    position:relative;
    overflow:hidden;
    margin-bottom:14px;
  }

  .grac-alert-header-card::before {
    content:"";
    position:absolute;
    inset:0;
    background:
      radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
      repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
  }

  .grac-alert-header-overlay {
    width:100%;
    display:flex;
    align-items:center;
    gap:14px;
    position:relative;
    z-index:1;
    min-width:0;
  }

  .grac-alert-header-icon {
    width:54px;
    height:54px;
    min-width:54px;
    border-radius:14px;
    background:#fff;
    color:#0b4a8f;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:1.4rem;
    box-shadow:0 8px 18px rgba(0,0,0,.25);
  }

  .grac-alert-header-text {
    flex:1 1 auto;
    min-width:0;
  }

  .grac-alert-header-badge {
    display:inline-block;
    background:rgba(255,255,255,.18);
    border-radius:999px;
    padding:3px 10px;
    font-size:.65rem;
    font-weight:800;
    margin-bottom:4px;
    color:#fff;
  }

  .grac-alert-header-title {
    color:#fff !important;
    font-weight:950;
    font-size:1.32rem;
    line-height:1.1;
    margin:0 !important;
    text-shadow:0 4px 14px rgba(0,0,0,.45);
    overflow-wrap:break-word;
  }

  .grac-alert-header-subtitle {
    color:rgba(255,255,255,.95);
    font-size:.78rem;
    line-height:1.25;
    margin-top:3px;
    overflow-wrap:break-word;
  }

  .grac-alert-header-actions {
    flex:0 0 auto;
    margin-left:auto;
  }

  .grac-alert-header-button {
    border-radius:10px !important;
    border:1px solid rgba(255,255,255,.72) !important;
    background:#fff !important;
    color:#0f172a !important;
    font-weight:900 !important;
    box-shadow:0 4px 10px rgba(0,0,0,.12);
    white-space:nowrap;
  }

  .grac-alert-header-button:hover {
    background:#edf5ff !important;
    color:#0b65d8 !important;
  }

  @media (max-width:768px) {
    .grac-alert-header-card {
      padding:14px 16px;
    }

    .grac-alert-header-overlay {
      align-items:flex-start;
      flex-wrap:wrap;
    }

    .grac-alert-header-icon {
      width:48px;
      height:48px;
      min-width:48px;
    }

    .grac-alert-header-title {
      font-size:1.18rem;
    }

    .grac-alert-header-actions {
      width:100%;
      margin-left:62px;
    }
  }

  @media (max-width:480px) {
    .grac-alert-header-actions {
      margin-left:0;
    }

    .grac-alert-header-button {
      width:100%;
    }
  }
</style>
"""


def alert_user_can_view_module(user, module_name):
    if not user or user.role == "auditor":
        return False
    if user.role == "admin":
        return True
    permission = ALERT_MODULE_PERMISSIONS.get(module_name)
    if not permission:
        return False
    try:
        return bool(verificar_permiso(user, permission))
    except Exception:
        return False


@app.route("/admin/alertas", methods=["GET", "POST"])
@login_required
@admin_required
def admin_alertas():
    alert_seed_defaults()
    cfg = alert_get_config()
    rules = AlertRule.query.order_by(AlertRule.module.asc(), AlertRule.id.asc()).all()
    if request.method == "POST":
        action = (request.form.get("action") or "").strip()
        if action == "save_config":
            recipients, invalid = alert_parse_recipients(request.form.get("recipients"))
            if invalid:
                flash("Correos no válidos: " + ", ".join(invalid), "danger")
                return redirect(url_for("admin_alertas"))
            cfg.recipients = ", ".join(recipients)
            cfg.email_enabled = bool(request.form.get("email_enabled"))
            cfg.in_app_enabled = bool(request.form.get("in_app_enabled"))
            cfg.subject_prefix = re.sub(
                r"[\r\n]+", " ",
                (request.form.get("subject_prefix") or "[Arkyntech GRAC]").strip(),
            )[:120]
            try:
                cfg.evaluation_minutes = max(5, min(1440, int(request.form.get("evaluation_minutes") or 15)))
            except (TypeError, ValueError):
                cfg.evaluation_minutes = 15
            base_url = (request.form.get("base_url") or "").strip().rstrip("/")[:500]
            if base_url and not re.match(r"^https?://", base_url, flags=re.IGNORECASE):
                flash("La URL de GRAC debe comenzar por http:// o https://.", "danger")
                return redirect(url_for("admin_alertas"))
            cfg.base_url = base_url or None
            db.session.commit()
            flash("Configuración general de alertas guardada.", "success")
        elif action == "save_rules":
            for rule in rules:
                rule.enabled = bool(request.form.get(f"enabled_{rule.id}"))
                rule.email_enabled = bool(request.form.get(f"email_{rule.id}"))
                operator = (request.form.get(f"operator_{rule.id}") or rule.operator).strip()
                rule.operator = operator if operator in ALERT_OPERATORS else rule.operator
                try:
                    rule.threshold = float(request.form.get(f"threshold_{rule.id}") or 0)
                except ValueError:
                    pass
                severity = (request.form.get(f"severity_{rule.id}") or rule.severity).strip().lower()
                rule.severity = severity if severity in ALERT_SEVERITIES else rule.severity
                try:
                    rule.repeat_minutes = max(5, min(43200, int(request.form.get(f"repeat_{rule.id}") or 1440)))
                except ValueError:
                    pass
                if not rule.enabled:
                    for event in AlertEvent.query.filter_by(rule_id=rule.id).filter(
                            ~AlertEvent.status.in_(["resuelta", "descartada"])).all():
                        event.status = "resuelta"
                        event.resolved_at = datetime.utcnow()
                        event.resolved_by = "Sistema - regla desactivada"
            db.session.commit()
            flash("Reglas de alertamiento actualizadas.", "success")
        elif action == "evaluate":
            result = alert_evaluate_all(send_emails=True, force_email=False)
            flash(
                f"Evaluación completada: {result['triggered']} activas, "
                f"{result['created']} nuevas y {result['emails_sent']} correos enviados.",
                "success",
            )
        elif action == "test_email":
            recipients, invalid = alert_parse_recipients(cfg.recipients)
            if invalid or not recipients:
                flash("Configure al menos un correo destinatario válido antes de probar.", "danger")
            else:
                try:
                    alert_send_email(
                        f"{cfg.subject_prefix} Prueba de correo",
                        "La configuración SMTP y los destinatarios del Centro de Alertas funcionan correctamente.",
                        "<h2>Arkyntech GRAC</h2><p>La configuración SMTP y los destinatarios del Centro de Alertas funcionan correctamente.</p>",
                        recipients,
                    )
                    flash("Correo de prueba enviado correctamente.", "success")
                except Exception as exc:
                    flash(f"No fue posible enviar el correo de prueba: {exc}", "danger")
        return redirect(url_for("admin_alertas"))

    smtp_cfg = get_email_config()
    deliveries = AlertDelivery.query.order_by(AlertDelivery.id.desc()).limit(20).all()
    inner = render_template_string(ALERT_PAGE_HEADER_STYLES + """
    <div class="container-fluid py-3" style="max-width:1500px">
      <div class="grac-alert-header-card">
        <div class="grac-alert-header-overlay">
          <div class="grac-alert-header-icon"><i class="bi bi-bell-fill"></i></div>
          <div class="grac-alert-header-text">
            <div class="grac-alert-header-badge">SGSI · Administración</div>
            <h3 class="grac-alert-header-title">Administración de Alertas</h3>
            <div class="grac-alert-header-subtitle">Configura destinatarios, umbrales, severidad y frecuencia. La conexión se toma de Parámetros Generales → Configuración del Correo.</div>
          </div>
        </div>
      </div>

      <div class="alert {{ 'alert-success' if smtp_ready else 'alert-warning' }} shadow-sm">
        <b>SMTP:</b> {{ 'Configurado' if smtp_ready else 'Incompleto' }}
        {% if smtp_host %} · Servidor: {{ smtp_host }}{% endif %}
        <a href="{{ url_for('config_email') }}" class="btn btn-sm btn-outline-primary ms-2">Abrir configuración SMTP</a>
      </div>

      <div class="card border-0 shadow-sm rounded-4 mb-3"><div class="card-body p-4">
        <h5 class="fw-bold text-primary">Destinatarios y funcionamiento</h5>
        <form method="post" class="row g-3">
          <input type="hidden" name="action" value="save_config">
          <div class="col-lg-7"><label class="form-label fw-bold">Correo o correos destinatarios</label>
            <textarea class="form-control" name="recipients" rows="3" placeholder="seguridad@empresa.com; gerencia@empresa.com">{{ cfg.recipients or '' }}</textarea>
            <div class="form-text">Separe los correos con coma, punto y coma o salto de línea.</div>
          </div>
          <div class="col-lg-5"><label class="form-label fw-bold">URL pública o interna de GRAC</label>
            <input class="form-control" name="base_url" value="{{ cfg.base_url or '' }}" placeholder="https://grac.arkyntech.com">
            <label class="form-label fw-bold mt-3">Prefijo del asunto</label>
            <input class="form-control" name="subject_prefix" value="{{ cfg.subject_prefix or '[Arkyntech GRAC]' }}">
          </div>
          <div class="col-md-4"><label class="form-label fw-bold">Evaluar cada (minutos)</label>
            <input class="form-control" type="number" min="5" max="1440" name="evaluation_minutes" value="{{ cfg.evaluation_minutes or 15 }}">
          </div>
          <div class="col-md-4 d-flex align-items-end"><div class="form-check form-switch mb-2">
            <input class="form-check-input" type="checkbox" name="email_enabled" id="email_enabled" {% if cfg.email_enabled %}checked{% endif %}>
            <label class="form-check-label fw-bold" for="email_enabled">Enviar por correo</label></div></div>
          <div class="col-md-4 d-flex align-items-end"><div class="form-check form-switch mb-2">
            <input class="form-check-input" type="checkbox" name="in_app_enabled" id="in_app_enabled" {% if cfg.in_app_enabled %}checked{% endif %}>
            <label class="form-check-label fw-bold" for="in_app_enabled">Mostrar en GRAC</label></div></div>
          <div class="col-12"><button class="btn btn-primary"><i class="bi bi-save me-1"></i>Guardar configuración</button></div>
        </form>
      </div></div>

      <div class="card border-0 shadow-sm rounded-4 mb-3"><div class="card-body p-4">
        <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
          <h5 class="fw-bold text-primary m-0">Reglas de alertamiento</h5>
          <div class="d-flex gap-2">
            <form method="post"><input type="hidden" name="action" value="test_email"><button class="btn btn-outline-primary"><i class="bi bi-envelope-check"></i> Probar correo</button></form>
            <form method="post"><input type="hidden" name="action" value="evaluate"><button class="btn btn-success"><i class="bi bi-arrow-repeat"></i> Evaluar ahora</button></form>
            <a class="btn btn-dark" href="{{ url_for('alert_center') }}"><i class="bi bi-bell"></i> Ver alertas</a>
          </div>
        </div>
        <form method="post"><input type="hidden" name="action" value="save_rules">
          <div class="table-responsive"><table class="table align-middle table-hover">
            <thead class="table-primary"><tr><th>Activa</th><th>Regla / módulo</th><th>Condición</th><th>Severidad</th><th>Correo</th><th>Repetir (min)</th></tr></thead>
            <tbody>{% for rule in rules %}<tr>
              <td><input class="form-check-input" type="checkbox" name="enabled_{{ rule.id }}" {% if rule.enabled %}checked{% endif %}></td>
              <td><b>{{ rule.name }}</b><div class="small text-muted">{{ rule.module }} · {{ rule.description }}</div></td>
              <td><div class="input-group input-group-sm" style="min-width:150px"><select class="form-select" name="operator_{{ rule.id }}">{% for op in operators %}<option {% if rule.operator==op %}selected{% endif %}>{{ op }}</option>{% endfor %}</select><input class="form-control" type="number" step="0.01" name="threshold_{{ rule.id }}" value="{{ rule.threshold }}"></div></td>
              <td><select class="form-select form-select-sm" name="severity_{{ rule.id }}">{% for sev in severities %}<option value="{{ sev }}" {% if rule.severity==sev %}selected{% endif %}>{{ sev|title }}</option>{% endfor %}</select></td>
              <td class="text-center"><input class="form-check-input" type="checkbox" name="email_{{ rule.id }}" {% if rule.email_enabled %}checked{% endif %}></td>
              <td><input class="form-control form-control-sm" type="number" min="5" max="43200" name="repeat_{{ rule.id }}" value="{{ rule.repeat_minutes }}"></td>
            </tr>{% endfor %}</tbody>
          </table></div>
          <button class="btn btn-primary"><i class="bi bi-save me-1"></i>Guardar reglas</button>
        </form>
      </div></div>

      <div class="card border-0 shadow-sm rounded-4"><div class="card-body p-4">
        <h5 class="fw-bold text-primary">Últimos envíos</h5>
        <div class="table-responsive"><table class="table table-sm align-middle"><thead><tr><th>Fecha</th><th>Alerta</th><th>Destinatarios</th><th>Estado</th><th>Error</th></tr></thead><tbody>
        {% for d in deliveries %}<tr><td>{{ d.created_at.strftime('%Y-%m-%d %H:%M') }}</td><td>{{ d.event.title }}</td><td>{{ d.recipients }}</td><td><span class="badge bg-{{ 'success' if d.status=='enviado' else 'danger' if d.status=='fallido' else 'warning text-dark' }}">{{ d.status }}</span></td><td class="small text-danger">{{ d.error or '' }}</td></tr>{% else %}<tr><td colspan="5" class="text-muted">Todavía no hay envíos registrados.</td></tr>{% endfor %}
        </tbody></table></div>
      </div></div>
    </div>
    """, cfg=cfg, rules=rules, deliveries=deliveries,
       smtp_ready=bool(smtp_cfg.get("SMTP_HOST") and smtp_cfg.get("SMTP_USER") and smtp_cfg.get("SMTP_PASS")),
       smtp_host=smtp_cfg.get("SMTP_HOST"), operators=[">", ">=", "=", "<", "<="],
       severities=["informativa", "baja", "media", "alta", "crítica"])
    return render_template_string(BASE, content=Markup(inner))


@app.route("/alertas", methods=["GET", "POST"])
@login_required
def alert_center():
    # Control de acceso real del Centro de Alertas (también por URL directa).
    current_alert_user = User.query.get(session.get("user_id"))
    if (not current_alert_user or current_alert_user.role == "auditor"
            or not verificar_permiso(current_alert_user, "Centro de Alertas")):
        abort(403, description="No tiene permiso para acceder al Centro de Alertas.")

    alert_seed_defaults()
    cfg = alert_get_config()
    if request.method == "POST":
        action = (request.form.get("action") or "").strip()
        event_id = request.form.get("event_id", type=int)
        if action == "refresh":
            result = alert_evaluate_all(send_emails=False)
            flash(f"Alertas actualizadas: {result['triggered']} condiciones activas.", "success")
        elif event_id:
            event = AlertEvent.query.get_or_404(event_id)
            if not alert_user_can_view_module(current_alert_user, event.module):
                abort(403)
            username = session.get("username") or "Usuario"
            if action == "acknowledge":
                event.status = "reconocida"
                event.acknowledged_at = datetime.utcnow()
                event.acknowledged_by = username
                db.session.commit()
                flash("Alerta reconocida.", "success")
            elif action == "resolve":
                event.status = "resuelta"
                event.resolved_at = datetime.utcnow()
                event.resolved_by = username
                db.session.commit()
                flash("Alerta marcada como resuelta.", "success")
            elif action == "discard":
                event.status = "descartada"
                event.resolved_at = datetime.utcnow()
                event.resolved_by = username
                db.session.commit()
                flash("Alerta descartada.", "success")
        return redirect(url_for("alert_center", module=request.args.get("module", ""), status=request.args.get("status", "")))

    module_filter = (request.args.get("module") or "").strip()
    status_filter = (request.args.get("status") or "").strip()
    severity_filter = (request.args.get("severity") or "").strip()
    allowed_modules = [
        module_name for module_name in ALERT_MODULE_PERMISSIONS
        if alert_user_can_view_module(current_alert_user, module_name)
    ]
    if not cfg.in_app_enabled and current_alert_user and current_alert_user.role != "admin":
        allowed_modules = []
    query = AlertEvent.query.filter(AlertEvent.module.in_(allowed_modules))
    if module_filter:
        query = query.filter(AlertEvent.module == module_filter)
    if status_filter:
        query = query.filter(AlertEvent.status == status_filter)
    if severity_filter:
        query = query.filter(AlertEvent.severity == severity_filter)
    events = query.order_by(AlertEvent.last_seen_at.desc()).limit(500).all()
    modules = [row[0] for row in db.session.query(AlertEvent.module).filter(
        AlertEvent.module.in_(allowed_modules)
    ).distinct().order_by(AlertEvent.module).all()]
    visible_query = AlertEvent.query.filter(AlertEvent.module.in_(allowed_modules))
    counts = {
        "active": visible_query.filter(~AlertEvent.status.in_(["resuelta", "descartada"])).count(),
        "critical": visible_query.filter(AlertEvent.severity == "crítica", ~AlertEvent.status.in_(["resuelta", "descartada"])).count(),
        "new": visible_query.filter(AlertEvent.status == "nueva").count(),
        "resolved": visible_query.filter(AlertEvent.status == "resuelta").count(),
    }
    inner = render_template_string(ALERT_PAGE_HEADER_STYLES + """
    <div class="container-fluid py-3" style="max-width:1500px">
      <div class="grac-alert-header-card">
        <div class="grac-alert-header-overlay">
          <div class="grac-alert-header-icon"><i class="bi bi-bell-fill"></i></div>
          <div class="grac-alert-header-text">
            <div class="grac-alert-header-badge">SGSI · Monitoreo</div>
            <h3 class="grac-alert-header-title">Centro de Alertas</h3>
            <div class="grac-alert-header-subtitle">Seguimiento centralizado de condiciones que requieren atención.</div>
          </div>
          <form method="post" class="grac-alert-header-actions">
            <input type="hidden" name="action" value="refresh">
            <button class="btn grac-alert-header-button"><i class="bi bi-arrow-clockwise me-1"></i>Actualizar ahora</button>
          </form>
        </div>
      </div>
      <div class="row g-3 mb-3">{% for label,value,color in [('Activas',counts.active,'danger'),('Críticas',counts.critical,'dark'),('Nuevas',counts.new,'primary'),('Resueltas',counts.resolved,'success')] %}<div class="col-6 col-lg-3"><div class="card border-0 shadow-sm rounded-4 h-100"><div class="card-body"><div class="text-muted small fw-bold">{{ label }}</div><div class="display-6 fw-bold text-{{ color }}">{{ value }}</div></div></div></div>{% endfor %}</div>
      <div class="card border-0 shadow-sm rounded-4 mb-3"><div class="card-body"><form class="row g-2">
        <div class="col-md-4"><select class="form-select" name="module"><option value="">Todos los módulos</option>{% for item in modules %}<option {% if module_filter==item %}selected{% endif %}>{{ item }}</option>{% endfor %}</select></div>
        <div class="col-md-3"><select class="form-select" name="severity"><option value="">Todas las severidades</option>{% for item in ['informativa','baja','media','alta','crítica'] %}<option {% if severity_filter==item %}selected{% endif %}>{{ item }}</option>{% endfor %}</select></div>
        <div class="col-md-3"><select class="form-select" name="status"><option value="">Todos los estados</option>{% for item in ['nueva','reconocida','en tratamiento','resuelta','descartada'] %}<option {% if status_filter==item %}selected{% endif %}>{{ item }}</option>{% endfor %}</select></div>
        <div class="col-md-2"><button class="btn btn-primary w-100">Filtrar</button></div>
      </form></div></div>
      <div class="card border-0 shadow-sm rounded-4"><div class="card-body p-0"><div class="table-responsive"><table class="table table-hover align-middle mb-0">
        <thead class="table-primary"><tr><th class="ps-3">Severidad</th><th>Alerta</th><th>Valor</th><th>Estado</th><th>Última detección</th><th>Acciones</th></tr></thead><tbody>
        {% for event in events %}<tr><td class="ps-3"><span class="badge bg-{{ 'danger' if event.severity in ['alta','crítica'] else 'warning text-dark' if event.severity=='media' else 'info text-dark' }}">{{ event.severity|upper }}</span></td>
          <td><b>{{ event.title }}</b><div class="small text-muted">{{ event.module }} · {{ event.message }}</div>{% if event.reference_url %}<a class="small" href="{{ event.reference_url }}">Abrir registro relacionado</a>{% endif %}</td>
          <td class="fw-bold">{{ format_number(event.value) }}</td><td><span class="badge bg-{{ badge(event.status) }}">{{ event.status }}</span></td><td>{{ event.last_seen_at.strftime('%Y-%m-%d %H:%M') }}</td>
          <td><div class="grac-alert-action-group">{% if event.status not in ['resuelta','descartada'] %}<form method="post"><input type="hidden" name="event_id" value="{{ event.id }}"><input type="hidden" name="action" value="acknowledge"><button class="btn btn-sm btn-outline-warning" title="Reconocer" aria-label="Reconocer alerta"><i class="bi bi-eye" aria-hidden="true"></i><span>Reconocer</span></button></form><form method="post"><input type="hidden" name="event_id" value="{{ event.id }}"><input type="hidden" name="action" value="resolve"><button class="btn btn-sm btn-outline-success" title="Resolver" aria-label="Resolver alerta"><i class="bi bi-check2-circle" aria-hidden="true"></i><span>Resolver</span></button></form><form method="post"><input type="hidden" name="event_id" value="{{ event.id }}"><input type="hidden" name="action" value="discard"><button class="btn btn-sm btn-outline-secondary" title="Descartar" aria-label="Descartar alerta"><i class="bi bi-x-circle" aria-hidden="true"></i><span>Descartar</span></button></form>{% endif %}</div></td></tr>
        {% else %}<tr><td colspan="6" class="text-center text-muted py-5"><i class="bi bi-bell-slash fs-1 d-block mb-2"></i>No hay alertas para los filtros seleccionados.</td></tr>{% endfor %}
        </tbody></table></div></div></div>
      {% if is_admin %}<div class="text-end mt-3"><a class="btn btn-outline-primary" href="{{ url_for('admin_alertas') }}"><i class="bi bi-gear"></i> Administrar alertas</a></div>{% endif %}
    </div>
    """, events=events, modules=modules, counts=counts, module_filter=module_filter,
       status_filter=status_filter, severity_filter=severity_filter,
       format_number=alert_format_number, badge=alert_status_badge,
       is_admin=bool(current_alert_user and current_alert_user.role == "admin"))
    return render_template_string(BASE, content=Markup(inner))

# =========================
# Logo Empresa
# =========================

@app.route("/empresa/logo", methods=["GET", "POST"])
@login_required
def empresa_logo():
    # (opcional) restringir a admin
    # user = User.query.get(session.get("user_id"))
    # if user.role != "admin": ...

    if request.method == "POST":
        company = (request.form.get("company_name") or "").strip()
        f = request.files.get("logo")

        if not company:
            flash("Debe indicar el nombre de la empresa.", "danger")
            return redirect(url_for("empresa_logo"))

        if not f or not f.filename:
            flash("Debe seleccionar un archivo de logo.", "danger")
            return redirect(url_for("empresa_logo"))

        if not _allowed_logo(f.filename):
            flash("Formato inválido. Use PNG/JPG/JPEG.", "danger")
            return redirect(url_for("empresa_logo"))

        safe = secure_filename(f.filename)
        # nombre final: company_normalizado + ext
        ext = safe.rsplit(".", 1)[-1].lower()
        base = "".join(ch if ch.isalnum() else "_" for ch in company)[:60]
        final_name = f"logo_{base}.{ext}"

        save_path = os.path.join(LOGOS_DIR, final_name)
        f.save(save_path)

        cfg = EmpresaConfig.query.filter_by(company_name=company).first()
        if not cfg:
            cfg = EmpresaConfig(company_name=company)
            db.session.add(cfg)

        cfg.logo_filename = final_name
        db.session.commit()

        flash("Logo actualizado correctamente.", "success")
        return redirect(url_for("empresa_logo", company=company))

    company = (request.args.get("company") or "").strip()
    logo_path = get_company_logo_path(company) if company else None

    html = f"""
    <div class="logo-shell">

      <!-- CABECERA -->
      <div class="logo-header-card">
        <div class="logo-header-overlay">
          <div class="logo-header-text">
            <h3 class="logo-title m-0">Logo por empresa</h3>
            <div class="logo-subtitle">
              Permite registrar o actualizar el logotipo institucional que será utilizado
              en reportes, documentos y comunicaciones del SGSI.
            </div>
          </div>
        </div>
      </div>

      <!-- FORMULARIO -->
      <div class="logo-card p-4">

        <div class="logo-section-title">
          Configuración del logo corporativo
        </div>

        <form method="POST" enctype="multipart/form-data">
          <div class="row g-3">

            <div class="col-md-6">
              <label class="form-label">Empresa (company_name)</label>
              <input class="form-control"
                     name="company_name"
                     value="{company}">
            </div>

            <div class="col-md-6">
              <label class="form-label">Logo (PNG / JPG)</label>
              <input class="form-control"
                     type="file"
                     name="logo"
                     accept=".png,.jpg,.jpeg">
            </div>

          </div>

          <div class="mt-4 d-flex justify-content-center gap-2">
            <button class="btn btn-success rounded-pill px-4" type="submit">
              Guardar logo
            </button>
          </div>

        </form>

        <div class="logo-preview mt-4 text-center">
          {"<div class='text-muted'>Logo actual: " + logo_path + "</div>" if logo_path else "<div class='text-muted'>No hay logo cargado.</div>"}
        </div>

      </div>

    </div>

    <style>
      body {{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }}

      .logo-shell {{
        width:96%;
        max-width:1100px;
        margin:26px auto 24px auto;
        overflow:hidden;
      }}

      .logo-header-card {{
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
      }}

      .logo-header-card::before {{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }}

      .logo-header-overlay {{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
        min-width:0;
      }}

      .logo-header-overlay::before {{
        content:"🖼️";
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
      }}

      .logo-header-text {{
        max-width:1000px;
        min-width:0;
      }}

      .logo-header-text::before {{
        content:"SGSI · Configuración de Logo Institucional";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }}

      .logo-title {{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 4px 14px rgba(0,0,0,.45);
        overflow-wrap:break-word;
      }}

      .logo-subtitle {{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        line-height:1.25;
        margin-top:3px;
        overflow-wrap:break-word;
      }}

      .logo-header-actions {{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }}

      .btn {{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
        max-width:100%;
      }}

      .logo-btn-main {{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }}

      .logo-btn-main:hover {{
        background:#edf5ff;
        color:#0b65d8;
      }}

      .logo-card {{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
        width:100%;
        max-width:100%;
      }}

      .logo-card .card-body {{
        padding:22px;
        overflow:hidden;
      }}

      .logo-section-title {{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:18px;
        border-bottom:2px solid rgba(59,130,246,.18);
        padding-bottom:8px;
        overflow-wrap:break-word;
      }}

      .form-control,
      .form-select {{
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
        max-width:100%;
      }}

      .form-control:focus,
      .form-select:focus {{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#ffffff;
      }}

      .input-group-text {{
        border-radius:0 10px 10px 0;
        background:#eef5ff;
        border-color:#d9e3f0;
        color:#0b4a8f;
        font-weight:900;
      }}

      .logo-preview {{
        font-size:.85rem;
        color:#334155;
        font-weight:700;
        overflow:hidden;
        max-width:100%;
      }}

      .logo-preview img {{
        border-radius:14px;
        border:1px solid #e2ebf5;
        padding:8px;
        background:#ffffff;
        box-shadow:0 8px 18px rgba(15,23,42,.10);
        max-width:100%;
        height:auto;
      }}

      .logo-soft-box {{
        background:#f8fbff;
        border:1px solid #e2ebf5;
        border-radius:14px;
        padding:14px 16px;
        min-width:0;
        max-width:100%;
        overflow:hidden;
        overflow-wrap:break-word;
      }}

      h3 {{
        color:#ffffff;
        margin:0;
      }}

      @media (max-width:992px){{
        .logo-shell {{
          width:98%;
          margin:8px auto 22px auto;
        }}

        .logo-title {{
          font-size:1.20rem;
        }}

        .logo-subtitle {{
          font-size:.68rem;
        }}

        .logo-card .card-body {{
          padding:16px;
        }}
      }}

      @media (max-width:768px){{
        .logo-header-overlay {{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }}

        .logo-header-overlay::before {{
          margin:0;
        }}

        .logo-title,
        .logo-subtitle {{
          text-align:center;
        }}

        .logo-header-actions .btn {{
          width:100%;
        }}
      }}
    </style>
    """
    return render_template_string(BASE, content=html)


# ============================================================================================================================================
#                                                               Fin Módulo de Áreas de la Empresa
# ============================================================================================================================================

# ============================================================================================================================================
#                                                               Módulo de Ádministración Key
# ============================================================================================================================================

#==================================
# Helper
#==================================

#==================================
# Cifrado Key
#==================================

def _fernet_from_app() -> Fernet:
    """
    Usa APP_FERNET_KEY si existe; si no, deriva una key estable desde SECRET_KEY.
    Recomendado: definir APP_FERNET_KEY en entorno para máxima seguridad.
    """
    env_key = os.environ.get("APP_FERNET_KEY") or os.environ.get("FERNET_KEY")
    if env_key:
        return Fernet(env_key.encode("utf-8"))

    # Deriva desde SECRET_KEY (fallback). Mejor que nada, pero ideal usar APP_FERNET_KEY.
    secret = (app.config.get("SECRET_KEY") or getattr(app, "secret_key", None) or "dev-secret-change-me")
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)  # 32 bytes urlsafe base64
    return Fernet(key)


def set_system_secret(key_name: str, plaintext: str) -> None:
    if not key_name:
        raise ValueError("key_name vacío")
    if plaintext is None or not str(plaintext).strip():
        raise ValueError("valor vacío")

    f = _fernet_from_app()
    token = f.encrypt(str(plaintext).strip().encode("utf-8")).decode("utf-8")

    row = SystemSecret.query.filter_by(key_name=key_name).first()
    if not row:
        row = SystemSecret(key_name=key_name, value_enc=token)
        db.session.add(row)
    else:
        row.value_enc = token

    db.session.commit()


def get_system_secret(key_name: str) -> str | None:
    row = SystemSecret.query.filter_by(key_name=key_name).first()
    if not row:
        return None
    try:
        f = _fernet_from_app()
        return f.decrypt(row.value_enc.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        # Cambió APP_FERNET_KEY o SECRET_KEY; no se puede descifrar
        return None
    except Exception:
        return None


def delete_system_secret(key_name: str) -> None:
    row = SystemSecret.query.filter_by(key_name=key_name).first()
    if row:
        db.session.delete(row)
        db.session.commit()


def get_openrouter_api_key() -> str:
    """
    Fuente preferida: BD cifrada. Fallback: variable de entorno.
    """
    v = get_system_secret("OPENROUTER_API_KEY")
    if v:
        return v
    return (os.environ.get("OPENROUTER_API_KEY") or "").strip()

def get_ai_provider() -> str:
    """
    Proveedor activo de IA:
    - openrouter
    - ollama
    """
    v = get_system_secret("AI_PROVIDER")
    if v:
        return v.strip().lower()
    return "openrouter"


def get_ollama_base_url() -> str:
    """
    URL base de Ollama.
    """
    v = get_system_secret("OLLAMA_BASE_URL")
    if v:
        return v.strip()
    return (os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434").strip()


def get_ollama_model() -> str:
    """
    Modelo por defecto de Ollama.
    """
    v = get_system_secret("OLLAMA_MODEL")
    if v:
        return v.strip()
    return (os.environ.get("OLLAMA_MODEL") or "llama3.1").strip()

def get_ollama_models(base_url: str | None = None) -> list[str]:
    """
    Consulta los modelos disponibles en Ollama.
    Devuelve una lista de nombres de modelos.
    """
    import requests

    try:
        url_base = (base_url or get_ollama_base_url() or "http://localhost:11434").strip().rstrip("/")
        resp = requests.get(f"{url_base}/api/tags", timeout=8)
        resp.raise_for_status()

        data = resp.json() or {}
        models = data.get("models", []) or []

        nombres = []
        for m in models:
            nombre = (m.get("name") or "").strip()
            if nombre:
                nombres.append(nombre)

        return nombres
    except Exception as e:
        print("ERROR consultando modelos de Ollama:", str(e))
        return []

#==================================
# Fin del Cifrado Key
#==================================


@app.route("/admin/openrouter_key", methods=["GET", "POST"])
@login_required
def admin_openrouter_key():
    user = User.query.get(session.get("user_id"))
    if not user or user.role != "admin":
        flash("No tiene permiso para configurar los proveedores de IA.", "danger")
        return redirect(url_for("menu"))

    if request.method == "POST":
        action = (request.form.get("action") or "").strip()

        if action == "clear_openrouter":
            delete_system_secret("OPENROUTER_API_KEY")
            flash("✅ API Key de OpenRouter eliminada.", "success")
            return redirect(url_for("admin_openrouter_key"))

        if action == "clear_ollama":
            delete_system_secret("OLLAMA_BASE_URL")
            delete_system_secret("OLLAMA_MODEL")
            flash("✅ Configuración de Ollama eliminada.", "success")
            return redirect(url_for("admin_openrouter_key"))

        provider = (request.form.get("ai_provider") or "openrouter").strip().lower()
        if provider not in ("openrouter", "ollama"):
            provider = "openrouter"

        set_system_secret("AI_PROVIDER", provider)

        openrouter_api_key = (request.form.get("api_key") or "").strip()
        ollama_base_url = (request.form.get("ollama_base_url") or "").strip()
        ollama_model = (request.form.get("ollama_model") or "").strip()

        if provider == "openrouter":
            if openrouter_api_key:
                if not openrouter_api_key.startswith("sk-or-"):
                    flash("⚠️ La key no parece ser de OpenRouter (debe iniciar con sk-or-). Aun así se guardará.", "warning")
                set_system_secret("OPENROUTER_API_KEY", openrouter_api_key)

            if not get_system_secret("OPENROUTER_API_KEY"):
                flash("⚠️ Debes ingresar una API Key de OpenRouter.", "warning")
                return redirect(url_for("admin_openrouter_key"))

            flash("✅ Configuración de OpenRouter guardada correctamente.", "success")
            return redirect(url_for("admin_openrouter_key"))

        if provider == "ollama":
            if not ollama_base_url:
                ollama_base_url = "http://localhost:11434"

            if not ollama_model:
                ollama_model = get_ollama_model() or "llama3.1"

            set_system_secret("OLLAMA_BASE_URL", ollama_base_url)
            set_system_secret("OLLAMA_MODEL", ollama_model)

            flash("✅ Configuración de Ollama guardada correctamente.", "success")
            return redirect(url_for("admin_openrouter_key"))

    ai_provider = get_ai_provider()
    has_openrouter_key = bool(get_system_secret("OPENROUTER_API_KEY"))
    ollama_base_url = get_ollama_base_url()
    ollama_model = get_ollama_model()
    ollama_models = get_ollama_models(ollama_base_url)
    has_ollama = bool(ollama_base_url and ollama_model)

    options_ollama = "".join(
        f"<option value='{m}' {'selected' if ollama_model == m else ''}>{m}</option>"
        for m in ollama_models
    )

    content = f"""
    <div class="openrouter-shell">

      <!-- CABECERA -->
      <div class="openrouter-header-card">
        <div class="openrouter-header-overlay">
          <div class="openrouter-header-text">
            <h3 class="openrouter-title m-0">Configuración de Inteligencia Artificial</h3>
            <div class="openrouter-subtitle">
              Administra el proveedor de IA del SGSI y configura OpenRouter u Ollama
              sin afectar los módulos actuales del sistema.
            </div>
          </div>
        </div>
      </div>

      <!-- TARJETA -->
      <div class="openrouter-card p-4">

        <div class="openrouter-section-title">
          Configuración general del proveedor de IA
        </div>

        <form method="POST">

          <label class="form-label fw-semibold">Proveedor activo</label>
          <select name="ai_provider" id="ai_provider" class="form-select mb-3" onchange="toggleAiSections()">
            <option value="openrouter" {"selected" if ai_provider == "openrouter" else ""}>OpenRouter</option>
            <option value="ollama" {"selected" if ai_provider == "ollama" else ""}>Ollama</option>
          </select>

          <div class="d-flex justify-content-between align-items-center flex-wrap mb-3">
            <div class="fw-bold">Proveedor actual</div>
            <span class="badge bg-primary">{ai_provider.upper()}</span>
          </div>

          <!-- =========================
               OPENROUTER
          ========================= -->
          <div id="openrouter_section">
            <div class="openrouter-section-title mt-4">
              OpenRouter
            </div>

            <div class="d-flex justify-content-between align-items-center flex-wrap mb-3">
              <div class="fw-bold">Estado OpenRouter</div>
              {"<span class='badge bg-success'>Configurada</span>" if has_openrouter_key else "<span class='badge bg-secondary'>No configurada</span>"}
            </div>

            <label class="form-label fw-semibold">OpenRouter API Key</label>
            <input type="password"
                   name="api_key"
                   class="form-control"
                   placeholder="sk-or-..."
                   autocomplete="off">

            <div class="text-muted small mt-2">
              La clave se almacenará cifrada y no se mostrará nuevamente por seguridad.
            </div>

            <div class="d-flex justify-content-center flex-wrap gap-2 mt-4">
              <button class="btn btn-primary rounded-pill px-5" type="submit">
                Guardar configuración
              </button>

              <button class="btn btn-outline-danger rounded-pill px-4"
                      type="submit"
                      name="action"
                      value="clear_openrouter"
                      onclick="return confirm('¿Eliminar la API Key guardada de OpenRouter?');">
                Eliminar API Key
              </button>
            </div>
          </div>

          <!-- =========================
               OLLAMA
          ========================= -->
          <div id="ollama_section">
            <div class="openrouter-section-title mt-4">
              Ollama
            </div>

            <div class="d-flex justify-content-between align-items-center flex-wrap mb-3">
              <div class="fw-bold">Estado Ollama</div>
              {"<span class='badge bg-success'>Configurado</span>" if has_ollama else "<span class='badge bg-secondary'>No configurado</span>"}
            </div>

            <label class="form-label fw-semibold">URL base de Ollama</label>
            <input type="text"
                   name="ollama_base_url"
                   class="form-control"
                   placeholder="http://localhost:11434"
                   value="{ollama_base_url}">

            <div class="text-muted small mt-2">
              Dirección del servicio de Ollama.
            </div>

            <label class="form-label fw-semibold mt-3">Modelo de Ollama</label>
            <select name="ollama_model" class="form-select">
              <option value="">Seleccione un modelo...</option>
              {options_ollama}
            </select>

            <div class="text-muted small mt-2">
              {"Modelos detectados desde Ollama." if ollama_models else "No se pudieron cargar modelos desde Ollama. Verifique que Ollama esté activo y que la URL base sea correcta."}
            </div>

            <div class="d-flex justify-content-center flex-wrap gap-2 mt-4">
              <button class="btn btn-primary rounded-pill px-5" type="submit">
                Guardar configuración
              </button>

              <button class="btn btn-outline-danger rounded-pill px-4"
                      type="submit"
                      name="action"
                      value="clear_ollama"
                      onclick="return confirm('¿Eliminar la configuración guardada de Ollama?');">
                Eliminar configuración
              </button>
            </div>
          </div>

        </form>

        <div class="alert alert-info small mt-4 mb-0">
          Esta pantalla solo agrega la configuración de Ollama y del proveedor activo.
          Las funciones actuales que usan <b>get_openrouter_api_key()</b> seguirán funcionando sin cambios.
        </div>

      </div>

    </div>

    <style>
      body {{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }}

      .openrouter-shell {{
        width:96%;
        max-width:1100px;
        margin:26px auto 24px auto;
        overflow:hidden;
      }}

      .openrouter-header-card {{
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
      }}

      .openrouter-header-card::before {{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }}

      .openrouter-header-overlay {{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
        min-width:0;
      }}

      .openrouter-header-overlay::before {{
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
      }}

      .openrouter-header-text {{
        max-width:900px;
        min-width:0;
      }}

      .openrouter-header-text::before {{
        content:"SGSI · Configuración de OpenRouter AI";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }}

      .openrouter-title {{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 4px 14px rgba(0,0,0,.45);
        overflow-wrap:break-word;
      }}

      .openrouter-subtitle {{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        line-height:1.25;
        margin-top:3px;
        overflow-wrap:break-word;
      }}

      .openrouter-header-actions {{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }}

      .btn {{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
        max-width:100%;
      }}

      .openrouter-btn-main {{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }}

      .openrouter-btn-main:hover {{
        background:#edf5ff;
        color:#0b65d8;
      }}

      .openrouter-card {{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
        width:100%;
        max-width:100%;
      }}

      .openrouter-card.p-4 {{
        padding:1.5rem !important;
      }}

      .openrouter-section-title {{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:18px;
        border-bottom:2px solid rgba(59,130,246,.18);
        padding-bottom:8px;
        overflow-wrap:break-word;
      }}

      .form-control,
      .form-select {{
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
        max-width:100%;
      }}

      textarea.form-control {{
        min-height:90px;
        resize:vertical;
      }}

      .form-control:focus,
      .form-select:focus {{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#ffffff;
      }}

      .btn.rounded-pill {{
        border-radius:999px !important;
      }}

      .openrouter-card .btn-primary,
      .openrouter-card .btn-outline-secondary,
      .openrouter-card .btn-outline-danger {{
        box-shadow:0 4px 10px rgba(0,0,0,.08);
        font-weight:900;
      }}

      h3 {{
        color:#ffffff;
        margin:0;
      }}

      @media (max-width:992px){{
        .openrouter-shell {{
          width:98%;
          margin:8px auto 22px auto;
        }}

        .openrouter-title {{
          font-size:1.20rem;
          line-height:1.08;
        }}

        .openrouter-subtitle {{
          font-size:.68rem;
          line-height:1.12;
        }}

        .openrouter-card.p-4 {{
          padding:1rem !important;
        }}
      }}

      @media (max-width:768px){{
        .openrouter-header-overlay {{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }}

        .openrouter-header-overlay::before {{
          margin:0;
        }}

        .openrouter-title,
        .openrouter-subtitle {{
          text-align:center;
        }}

        .openrouter-header-actions .btn {{
          width:100%;
        }}
      }}
    </style>

    <script>
      function toggleAiSections() {{
        const provider = document.getElementById('ai_provider')?.value || 'openrouter';
        const openrouterSection = document.getElementById('openrouter_section');
        const ollamaSection = document.getElementById('ollama_section');

        if (provider === 'ollama') {{
          if (openrouterSection) openrouterSection.style.display = 'none';
          if (ollamaSection) ollamaSection.style.display = 'block';
        }} else {{
          if (openrouterSection) openrouterSection.style.display = 'block';
          if (ollamaSection) ollamaSection.style.display = 'none';
        }}
      }}

      document.addEventListener('DOMContentLoaded', function() {{
        toggleAiSections();
      }});
    </script>
    """
    return render_template_string(BASE, content=Markup(content))

# ============================================================================================================================================
#                                                               Fin Módulo de Ádministración Key
# ============================================================================================================================================

# ============================================================================================================================================
#                                                               Módulo Declaración de Aplicabilidad
# ============================================================================================================================================

@app.route('/soa', methods=['GET', 'POST'])
@login_required
def declaracion_aplicabilidad():
    user = User.query.get(session.get('user_id'))

    # Permisos
    if user.role not in ('admin', 'auditor') and not verificar_permiso(user, "Contexto Interno"):
        flash("No tiene permiso para acceder al módulo de contexto interno.", "danger")
        return redirect(url_for('menu'))

    read_only = (user.role == 'auditor')

    if request.method == 'POST' and read_only:
        flash("El rol Auditor no puede modificar o guardar información.", "danger")
        return redirect(url_for('declaracion_aplicabilidad'))

    if request.method == 'POST':
        for control in Control.query.all():
            a = request.form.get(f"applicable_{control.id}", "").strip() or None
            j = request.form.get(f"justification_{control.id}", "").strip()
            files = request.files.getlist(f"motivation_{control.id}")
            uploaded_files = control.motivation.split(',') if control.motivation else []

            for file in files:
                if file and allowed_evidence_file(file.filename):
                    filename = secure_filename(f"{control.id}_{file.filename}")
                    if filename not in uploaded_files:
                        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                        uploaded_files.append(filename)

            control.applicable = a
            control.justification = j
            control.motivation = ",".join(uploaded_files)
            control.implemented = request.form.get(f"implemented_{control.id}", "").strip() or None

        db.session.commit()
        flash("Cambios guardados correctamente.", "success")
        return redirect(url_for('declaracion_aplicabilidad'))

    filtro_aplicable = request.args.get("filtro_aplicable", "")
    filtro_implementado = request.args.get("filtro_implementado", "")

    query = Control.query
    if filtro_aplicable:
        query = query.filter(Control.applicable == filtro_aplicable)
    if filtro_implementado:
        query = query.filter(Control.implemented == filtro_implementado)

    controles = query.all()

    def ordenar_nr(control):
        nr = (control.nr or "").strip()
        partes = nr.split(".")
        clave = []
        for p in partes:
            p = p.strip()
            clave.append(int(p) if p.isdigit() else p.lower())
        return clave

    controles = sorted(controles, key=ordenar_nr)

    rows = []
    for c in controles:
        rows.append({
            "id": c.id,
            "nr": c.nr,
            "chapter": c.chapter,
            "topic": c.topic,
            "control_text": c.control_text,
            "applicable": c.applicable or "",
            "justification": c.justification or "",
            "motivation": c.motivation or "",
            "implemented": c.implemented or ""
        })

    content = render_template_string("""
    <div class="soa-shell">

      <!-- =========================
           HERO / TÍTULO DEL MÓDULO
      ========================== -->
      <div class="soa-hero-card">

        <div class="soa-hero-left">

          <div class="soa-hero-icon">
            📄
          </div>

          <div class="soa-hero-text">
            <div class="soa-hero-kicker">
              ISO 27001:2022 · SGSI
            </div>

            <h2 class="soa-hero-title">
              Declaración de Aplicabilidad
            </h2>

            <p class="soa-hero-subtitle">
              Controles del Anexo A — aplicabilidad, justificación, evidencia e implementación.
            </p>
          </div>

        </div>

        <div class="soa-hero-badge">
          SoA
        </div>

      </div>

      <!-- =========================
           BOTÓN GUARDAR
      ========================== -->
      {% if not read_only %}
      <div class="soa-save-wrapper">
        <button class="soa-save-btn" type="submit" form="soa-main-form">
          💾 Guardar
        </button>
      </div>
      {% endif %}

      <!-- =========================
           FILTROS
      ========================== -->
      <div class="soa-filter-panel">
        <form method="get" class="soa-filter-form">

          <div class="soa-filter-group">
            <div class="soa-filter-bubble">🔎</div>
            <div class="soa-filter-control">
              <label>Filtrar por “Aplicable”</label>
              <select class="form-select" name="filtro_aplicable">
                <option value="">-- Todos --</option>
                <option value="sí" {% if filtro_aplicable == 'sí' %}selected{% endif %}>Sí</option>
                <option value="no" {% if filtro_aplicable == 'no' %}selected{% endif %}>No</option>
              </select>
            </div>
          </div>

          <div class="soa-filter-group">
            <div class="soa-filter-bubble">🔎</div>
            <div class="soa-filter-control">
              <label>Filtrar por “Implementado”</label>
              <select class="form-select" name="filtro_implementado">
                <option value="">-- Todos --</option>
                <option value="sí" {% if filtro_implementado == 'sí' %}selected{% endif %}>Sí</option>
                <option value="no" {% if filtro_implementado == 'no' %}selected{% endif %}>No</option>
              </select>
            </div>
          </div>

          <div class="soa-filter-actions">
            <button type="submit" class="soa-primary-btn">
              Aplicar filtros
            </button>

            <a href="{{ url_for('declaracion_aplicabilidad') }}" class="soa-secondary-btn">
              Mostrar todo
            </a>
          </div>

        </form>
      </div>

      <!-- =========================
           TABLA
      ========================== -->
      <form id="soa-main-form" method="post" enctype="multipart/form-data">
        <div class="soa-table-panel">
          <div class="soa-table-scroll">

            <table class="table soa-table align-middle mb-0">
              <thead>
                <tr>
                  <th>Nr.</th>
                  <th>Capítulo</th>
                  <th>Tema</th>
                  <th>Control</th>
                  <th>Aplicable</th>
                  <th>Justificación</th>
                  <th>Evidencia</th>
                  <th>Implementado</th>
                </tr>
              </thead>

              <tbody>
              {% for r in rows %}
                <tr>
                  <td>
                    <span class="soa-nr-badge">{{ r.nr }}</span>
                  </td>

                  <td>{{ r.chapter }}</td>
                  <td>{{ r.topic }}</td>

                  <td>
                    <div class="soa-control-text">{{ r.control_text }}</div>
                  </td>

                  <td>
                    <select name="applicable_{{ r.id }}"
                            class="form-select form-select-sm"
                            {% if read_only %}disabled{% endif %}>
                      <option value="" {% if r.applicable=="" %}selected{% endif %}></option>
                      <option value="sí" {% if r.applicable=='sí' %}selected{% endif %}>sí</option>
                      <option value="no" {% if r.applicable=='no' %}selected{% endif %}>no</option>
                    </select>
                  </td>

                  <td>
                    <textarea name="justification_{{ r.id }}"
                              class="form-control form-control-sm"
                              rows="2"
                              {% if read_only %}disabled{% endif %}>{{ r.justification }}</textarea>
                  </td>

                  <td>
                    <div id="files_list_{{ r.id }}" class="soa-files-list">
                      {% if r.motivation %}
                        {% for file in r.motivation.split(',') if file %}
                          <div class="soa-file-item" id="file-{{ r.id }}-{{ loop.index }}">
                            <a href="{{ url_for('vista_evidencia', filename=file, next='declaracion_aplicabilidad') }}"
                               title="{{ file }}">
                              📎 {{ file }}
                            </a>

                            {% if not read_only %}
                            <button type="button" class="soa-evidence-delete grac-trash-button"
                                    title="Eliminar archivo" aria-label="Eliminar archivo"
                                    onclick="deleteEvidence({{ r.id }}, '{{ file }}', 'file-{{ r.id }}-{{ loop.index }}')">
                              <i class="bi bi-trash3-fill" aria-hidden="true"></i>
                            </button>
                            {% endif %}
                          </div>
                        {% endfor %}
                      {% endif %}
                    </div>

                    {% if not read_only %}
                    <button type="button"
                            class="soa-attach-btn"
                            onclick="document.getElementById('file_input_{{ r.id }}').click();">
                      📎 Adjuntar
                    </button>

                    <input type="file"
                           id="file_input_{{ r.id }}"
                           name="motivation_{{ r.id }}"
                           accept=".pdf,.doc,.docx,.xls,.xlsx"
                           multiple
                           style="display:none;"
                           onchange="mostrarArchivos(this, 'files_list_{{ r.id }}')">
                    {% endif %}
                  </td>

                  <td>
                    <select name="implemented_{{ r.id }}"
                            class="form-select form-select-sm"
                            {% if read_only %}disabled{% endif %}>
                      <option value="" {% if r.implemented=="" %}selected{% endif %}></option>
                      <option value="sí" {% if r.implemented=='sí' %}selected{% endif %}>sí</option>
                      <option value="no" {% if r.implemented=='no' %}selected{% endif %}>no</option>
                    </select>
                  </td>
                </tr>
              {% endfor %}
              </tbody>
            </table>

          </div>
        </div>

        <script>
          function mostrarArchivos(input, listaId) {
            const lista = document.getElementById(listaId);
            if (!lista) return;

            for (const file of input.files) {
              const div = document.createElement('div');
              div.className = "soa-file-item";

              const enlace = document.createElement('a');
              enlace.href = URL.createObjectURL(file);
              enlace.target = "_blank";
              enlace.title = file.name;
              enlace.textContent = "📎 " + file.name;

              const eliminarBtn = document.createElement('button');
              eliminarBtn.type = "button";
              eliminarBtn.className = "soa-evidence-delete grac-trash-button";
              eliminarBtn.setAttribute("title", "Quitar archivo");
              eliminarBtn.setAttribute("aria-label", "Quitar archivo");
              eliminarBtn.innerHTML = '<i class="bi bi-trash3-fill" aria-hidden="true"></i>';
              eliminarBtn.onclick = () => {
                div.remove();

                const dt = new DataTransfer();
                for (const f of input.files) {
                  if (f !== file) dt.items.add(f);
                }
                input.files = dt.files;
              };

              div.appendChild(enlace);
              div.appendChild(eliminarBtn);
              lista.appendChild(div);
            }
          }

          async function deleteEvidence(controlId, filename, elementId) {
            if (!confirm('¿Eliminar este archivo?')) return;

            try {
              const response = await fetch(`/delete_evidence/${controlId}/${filename}`, {
                method: 'POST'
              });

              if (response.ok) {
                const elem = document.getElementById(elementId);
                if (elem) elem.remove();
              } else {
                alert('Error al eliminar el archivo.');
              }
            } catch (err) {
              alert('Error de conexión al eliminar el archivo.');
            }
          }
        </script>
      </form>
    </div>

    <style>
      body {
        background-image: url('/static/img/ccsgsi.jpg');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        background-repeat: no-repeat;
      }

      .soa-shell {
        width: 96%;
        max-width: 1580px;
        margin: 10px auto 24px auto;
      }

      /* =========================
         HERO COMPACTO
      ========================== */
      .soa-hero-card {
        background:
          linear-gradient(135deg, rgba(11,58,110,.97), rgba(20,89,166,.95), rgba(44,123,229,.92));
        border-radius: 18px;
        padding: 16px 24px;
        min-height: 94px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 12px 24px rgba(15, 23, 42, .24);
        color: #ffffff;
        position: relative;
        overflow: hidden;
        margin-bottom: 10px;
      }

      .soa-hero-card::before {
        content: "";
        position: absolute;
        inset: 0;
        background:
          radial-gradient(circle at 92% 12%, rgba(255,255,255,.20), transparent 26%),
          repeating-linear-gradient(
            135deg,
            rgba(255,255,255,.05) 0px,
            rgba(255,255,255,.05) 1px,
            transparent 1px,
            transparent 15px
          );
        pointer-events: none;
      }

      .soa-hero-left {
        display: flex;
        align-items: center;
        gap: 14px;
        position: relative;
        z-index: 1;
      }

      .soa-hero-icon {
        width: 54px;
        height: 54px;
        min-width: 54px;
        border-radius: 14px;
        background: rgba(255,255,255,.96);
        color: #0b4a8f;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.55rem;
        box-shadow: 0 8px 18px rgba(0,0,0,.20);
      }

      .soa-hero-text {
        position: relative;
        z-index: 1;
      }

      .soa-hero-kicker {
        display: inline-block;
        background: rgba(255,255,255,.18);
        border: 1px solid rgba(255,255,255,.30);
        border-radius: 999px;
        padding: 3px 10px;
        font-size: .66rem;
        font-weight: 800;
        letter-spacing: .35px;
        margin-bottom: 4px;
      }

      .soa-hero-title {
        margin: 0;
        font-size: 1.36rem;
        font-weight: 950;
        line-height: 1.08;
        color: #ffffff;
        text-shadow: 0 3px 10px rgba(0,0,0,.32);
      }

      .soa-hero-subtitle {
        margin: 4px 0 0 0;
        font-size: .78rem;
        color: rgba(248,252,255,.96);
        max-width: 820px;
        line-height: 1.25;
      }

      .soa-hero-badge {
        position: relative;
        z-index: 1;
        width: 66px;
        height: 66px;
        border-radius: 18px;
        background: rgba(255,255,255,.95);
        color: #0b4a8f;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.25rem;
        font-weight: 950;
        box-shadow: 0 10px 20px rgba(0,0,0,.22);
        transform: rotate(-4deg);
      }

      /* =========================
         BOTÓN GUARDAR COMPACTO
      ========================== */
      .soa-save-wrapper {
        display: flex;
        justify-content: center;
        margin: 10px 0 12px 0;
      }

      .soa-save-btn {
        border: none;
        border-radius: 13px;
        background: linear-gradient(135deg, #12844b, #16a05d);
        color: #fff;
        padding: 9px 30px;
        font-weight: 900;
        font-size: .86rem;
        box-shadow: 0 8px 16px rgba(18,132,75,.26);
      }

      .soa-save-btn:hover {
        filter: brightness(.96);
        transform: translateY(-1px);
      }

      /* =========================
         FILTROS COMPACTOS
      ========================== */
      .soa-filter-panel {
        background: rgba(255,255,255,.96);
        border-radius: 16px;
        padding: 14px 18px;
        box-shadow: 0 10px 22px rgba(15,23,42,.15);
        backdrop-filter: blur(10px);
        margin-bottom: 14px;
      }

      .soa-filter-form {
        display: grid;
        grid-template-columns: 1fr 1fr 1.05fr;
        gap: 14px;
        align-items: end;
      }

      .soa-filter-group {
        display: grid;
        grid-template-columns: 44px 1fr;
        gap: 10px;
        align-items: end;
      }

      .soa-filter-bubble {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: #eef5ff;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #1d74e8;
        font-size: 1rem;
      }

      .soa-filter-control label {
        font-weight: 800;
        font-size: .78rem;
        color: #25324a;
        margin-bottom: 4px;
      }

      .soa-filter-control .form-select {
        height: 38px;
        border-radius: 9px;
        border: 1px solid #d9e3f0;
        box-shadow: none;
        font-size: .84rem;
        padding-top: 4px;
        padding-bottom: 4px;
      }

      .soa-filter-actions {
        display: flex;
        gap: 10px;
        justify-content: flex-end;
        align-items: center;
        border-left: 1px solid #e5edf7;
        padding-left: 16px;
      }

      .soa-primary-btn,
      .soa-secondary-btn {
        height: 38px;
        border-radius: 10px;
        padding: 0 20px;
        font-weight: 900;
        font-size: .82rem;
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 7px;
        white-space: nowrap;
      }

      .soa-primary-btn {
        border: none;
        background: linear-gradient(135deg, #086df0, #2487ff);
        color: #fff;
        box-shadow: 0 7px 14px rgba(8,109,240,.22);
      }

      .soa-secondary-btn {
        border: 1px solid #1e7cff;
        color: #1e7cff;
        background: #fff;
      }

      .soa-secondary-btn:hover {
        background: #edf5ff;
        color: #0b65d8;
      }

      /* =========================
         TABLA COMPACTA
      ========================== */
      .soa-table-panel {
        background: rgba(255,255,255,.96);
        border-radius: 18px;
        padding: 10px;
        box-shadow: 0 12px 24px rgba(15,23,42,.18);
        backdrop-filter: blur(8px);
      }

      .soa-table-scroll {
        border-radius: 14px;
        overflow-x: auto;
        overflow-y: visible;
        border: 1px solid #dbe6f4;
        background: #fff;
      }

      .soa-table {
        min-width: 1760px;
        table-layout: fixed;
        border-collapse: separate;
        border-spacing: 0;
      }

      .soa-table thead th {
        background: linear-gradient(135deg, #1d5fa9, #2f7fd1);
        color: #fff;
        font-weight: 900;
        text-align: center;
        vertical-align: middle;
        padding: 11px 9px;
        border-right: 1px solid rgba(255,255,255,.28);
        font-size: .78rem;
      }

      .soa-table thead th:first-child {
        border-top-left-radius: 12px;
      }

      .soa-table thead th:last-child {
        border-top-right-radius: 12px;
      }

      .soa-table tbody td {
        padding: 9px 8px;
        border-right: 1px solid #dce6f3;
        border-bottom: 1px solid #dce6f3;
        vertical-align: middle;
        background: rgba(255,255,255,.98);
        font-size: .78rem;
        color: #0b1220;
      }

      .soa-table tbody tr:nth-child(even) td {
        background: #f8fbff;
      }

      .soa-table tbody tr:hover td {
        background: #eef6ff;
      }

      .soa-nr-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 39px;
        height: 28px;
        border-radius: 11px;
        background: #eaf3ff;
        color: #1476ef;
        font-weight: 900;
        font-size: .78rem;
        box-shadow: inset 0 0 0 1px rgba(20,118,239,.10);
      }

      .soa-control-text {
        white-space: pre-wrap;
        word-break: break-word;
        line-height: 1.35;
        font-size: .78rem;
      }

      .soa-table textarea,
      .soa-table select {
        border-radius: 8px;
        border-color: #d9e3f0;
        font-size: .76rem;
      }

      .soa-table textarea {
        min-height: 56px;
      }

      .soa-files-list {
        display: flex;
        flex-direction: column;
        gap: 5px;
      }

      .soa-file-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 7px;
        background: #f1f7ff;
        border: 1px solid #d9eaff;
        border-radius: 9px;
        padding: 5px 7px;
      }

      .soa-file-item a {
        color: #255f9f;
        text-decoration: none;
        font-weight: 700;
        font-size: .74rem;
        max-width: 190px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .soa-file-item button {
        border: none;
        background: transparent;
        color: #dc3545;
        font-size: .86rem;
        padding: 0;
      }

      .soa-attach-btn {
        margin-top: 7px;
        width: 100%;
        border-radius: 9px;
        border: 1px solid #2f7fd1;
        background: #fff;
        color: #1e6fc4;
        font-weight: 800;
        font-size: .75rem;
        padding: 6px 8px;
      }

      .soa-attach-btn:hover {
        background: #eef6ff;
      }

      .soa-table th:nth-child(1), .soa-table td:nth-child(1) { width: 78px; text-align: center; }
      .soa-table th:nth-child(2), .soa-table td:nth-child(2) { width: 220px; }
      .soa-table th:nth-child(3), .soa-table td:nth-child(3) { width: 270px; }
      .soa-table th:nth-child(4), .soa-table td:nth-child(4) { width: 460px; }
      .soa-table th:nth-child(5), .soa-table td:nth-child(5) { width: 125px; }
      .soa-table th:nth-child(6), .soa-table td:nth-child(6) { width: 300px; }
      .soa-table th:nth-child(7), .soa-table td:nth-child(7) { width: 275px; }
      .soa-table th:nth-child(8), .soa-table td:nth-child(8) { width: 132px; }

      .soa-table-scroll::-webkit-scrollbar {
        height: 11px;
      }

      .soa-table-scroll::-webkit-scrollbar-track {
        background: #dbe4f0;
        border-radius: 12px;
      }

      .soa-table-scroll::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, #5aa3ea 0%, #3f86d6 100%);
        border-radius: 12px;
        border: 2px solid #dbe4f0;
      }

      .soa-table-scroll {
        scrollbar-width: thin;
        scrollbar-color: #3f86d6 #dbe4f0;
      }

      /* =========================
         RESPONSIVE
      ========================== */
      @media (max-width: 1200px) {
        .soa-hero-badge {
          display: none;
        }

        .soa-filter-form {
          grid-template-columns: 1fr;
        }

        .soa-filter-actions {
          border-left: none;
          padding-left: 0;
          justify-content: stretch;
        }

        .soa-primary-btn,
        .soa-secondary-btn {
          flex: 1;
        }
      }

      @media (max-width: 768px) {
        .soa-shell {
          width: 98%;
        }

        .soa-hero-card {
          padding: 18px;
        }

        .soa-hero-left {
          flex-direction: column;
          text-align: center;
        }

        .soa-hero-title {
          font-size: 1.22rem;
        }

        .soa-hero-subtitle {
          font-size: .74rem;
        }

        .soa-filter-group {
          grid-template-columns: 1fr;
        }

        .soa-filter-bubble {
          display: none;
        }

        .soa-filter-actions {
          flex-direction: column;
        }

        .soa-primary-btn,
        .soa-secondary-btn {
          width: 100%;
        }
      }
    </style>
    """,
    rows=rows,
    filtro_aplicable=filtro_aplicable,
    filtro_implementado=filtro_implementado,
    read_only=read_only)
    
    return render_template_string(BASE, content=content)

# =========================
# Ver evidencia
# =========================

@app.route('/ver_evidencia/<path:filename>')
@login_required
def ver_evidencia(filename):
    full_path = safe_join(app.config['UPLOAD_FOLDER'], filename)
    if not full_path or not os.path.isfile(full_path):
        abort(404)

    ext = os.path.splitext(filename)[1].lower()
    mimetypes = {
        '.pdf':  'application/pdf',
        '.doc':  'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xls':  'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    }
    mime = mimetypes.get(ext, 'application/octet-stream')

    # Importante: as_attachment=False => intenta mostrar inline
    return send_file(full_path, mimetype=mime, as_attachment=False, download_name=filename, conditional=True)

# =========================
# Ver evidencia convertido
# =========================

@app.route('/ver_evidencia_convertido/<path:filename>')
@login_required
def ver_evidencia_convertido(filename):
    full_path = safe_join(CONVERTED_FOLDER, filename)
    if not full_path or not os.path.isfile(full_path):
        abort(404)
    return send_file(full_path, mimetype='application/pdf', as_attachment=False, download_name=filename, conditional=True)



# =========================
# Vista de archivos
# =========================
# Carpeta donde guardas PDFs convertidos
CONVERTED_FOLDER = os.path.join(app.root_path, "static", "converted")
os.makedirs(CONVERTED_FOLDER, exist_ok=True)

def _find_soffice():
    """
    Encuentra el ejecutable de LibreOffice (soffice).
    - En Mac suele estar dentro de /Applications/LibreOffice.app/...
    - En Linux/Windows normalmente basta con 'soffice' en PATH.
    """
    # 1) Si está en PATH
    p = shutil.which("soffice")
    if p:
        return p

    # 2) Rutas típicas en macOS
    mac_candidates = [
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice.bin",
    ]
    for c in mac_candidates:
        if os.path.exists(c):
            return c

    return None

def ensure_pdf_from_office(filename: str) -> str | None:
    """
    Convierte .doc/.docx/.xls/.xlsx a PDF usando LibreOffice headless.
    Retorna el nombre del PDF (archivo en CONVERTED_FOLDER) o None si falla.
    """
    if not filename:
        return None

    # Seguridad: solo nombre base, no rutas
    filename = os.path.basename(filename)
    src_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    if not os.path.isfile(src_path):
        return None

    ext = os.path.splitext(filename)[1].lower()
    if ext not in {".doc", ".docx", ".xls", ".xlsx"}:
        return None

    # Nombre PDF destino
    base = os.path.splitext(filename)[0]
    out_pdf_name = secure_filename(base) + ".pdf"
    out_pdf_path = os.path.join(CONVERTED_FOLDER, out_pdf_name)

    # Cache: si ya existe y es más nuevo que el origen, no reconvertir
    try:
        if os.path.isfile(out_pdf_path):
            if os.path.getmtime(out_pdf_path) >= os.path.getmtime(src_path):
                return out_pdf_name
    except Exception:
        pass

    soffice = _find_soffice()
    if not soffice:
        # No hay LibreOffice disponible
        return None

    # Ejecuta conversión
    try:
        cmd = [
            soffice,
            "--headless",
            "--nologo",
            "--nolockcheck",
            "--nodefault",
            "--nofirststartwizard",
            "--convert-to", "pdf",
            "--outdir", CONVERTED_FOLDER,
            src_path,
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)

        # LibreOffice a veces escribe mensajes aunque convierta; validamos por existencia del PDF
        if os.path.isfile(out_pdf_path):
            return out_pdf_name

        # Si no creó el PDF, falló
        return None

    except Exception:
        return None


# =========================
# Borrado de archivos
# =========================

@app.route('/delete_evidence/<int:control_id>/<filename>', methods=['POST'])
@login_required
def delete_evidence(control_id, filename):
    user = User.query.filter_by(username=session['username']).first()
    if user.role == 'auditor':
        flash("No tiene permiso para eliminar archivos.", "danger")
        return redirect(url_for('declaracion_aplicabilidad'))
    
    control = Control.query.get_or_404(control_id)
    if not control.motivation:
        flash("No hay archivos asociados.", "warning")
        return redirect(url_for('declaracion_aplicabilidad'))

    archivos = control.motivation.split(',')
    if filename in archivos:
        archivos.remove(filename)
        control.motivation = ','.join(archivos)
        # Elimina físicamente el archivo
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        db.session.commit()
        flash(f"Archivo '{filename}' eliminado correctamente.", "success")
    else:
        flash("Archivo no encontrado.", "danger")

    return redirect(url_for('declaracion_aplicabilidad'))

# ============================================================================================================================================
#                                                               Fin Módulo Declaración de Aplicabilidad
# ============================================================================================================================================


# ============================================================================================================================================
#                                                               Módulo Gestión de Riesgos
# ============================================================================================================================================

# =========================
# Modelo
# =========================

class Riesgo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo_riesgo = db.Column(db.String(50))
    riesgo = db.Column(db.String(255))
    fecha_identificacion = db.Column(db.String(50))
    propietario_riesgo = db.Column(db.String(255))
    codigo_amenaza = db.Column(db.String(50))
    amenaza = db.Column(db.String(255))
    codigo_vulnerabilidad = db.Column(db.String(50))
    vulnerabilidad = db.Column(db.String(255))
    tipo_activo = db.Column(db.String(100))
    nombre_activo = db.Column(db.String(255))
    dimension_seguridad = db.Column(db.String(50))
    probabilidad = db.Column(db.Integer)
    impacto = db.Column(db.Integer)

    # Campos de control
    control_codigo = db.Column(db.String(50))
    codigo_anexo = db.Column(db.String(50))
    codigo_control_pci_dss = db.Column(db.String(50))
    codigo_control_nist_csf = db.Column(db.String(50))
    codigo_control_soc2 = db.Column(db.String(50))
    descripcion_control = db.Column(db.Text)
    plan_accion = db.Column(db.String(255))
    asignacion = db.Column(db.String(255))
    cargo = db.Column(db.String(255))
    tipo_control = db.Column(db.String(50))
    forma_control = db.Column(db.String(50))
    frecuencia = db.Column(db.String(50))
    funcionalidad = db.Column(db.String(50))
    estado_control = db.Column(db.String(50))
    referencia_documental = db.Column(db.String(255))
    evidencia_control = db.Column(db.String(255))
    soporte_evidencia = db.Column(db.String(255))
    activo = db.Column(db.String(255))
    diseno_control = db.Column(db.String(50))
    ejecucion_control = db.Column(db.String(50))
    valor = db.Column(db.Float)
    solidez_individual = db.Column(db.Float)
    solidez_grupal = db.Column(db.Float)
    prob_inh = db.Column(db.String(100))
    imp_inh = db.Column(db.String(100))
    riesgo_inherente = db.Column(db.String(100))
    cuadrante_prob = db.Column(db.String(50))
    cuadrante_imp = db.Column(db.String(50))
    prob_res = db.Column(db.String(100))
    riesgo_residual = db.Column(db.String(100))
    calificacion_asignacion = db.Column(db.Float)
    calificacion_tipo_control = db.Column(db.Float)
    calificacion_forma_control = db.Column(db.Float)
    calificacion_funcionalidad = db.Column(db.Float)
    calificacion_estado_control = db.Column(db.Float)
    calificacion_soporte_evidencia = db.Column(db.Float)
    valor_ejecucion_control = db.Column(db.Float)

    # Campos finales
    fecha_revision = db.Column(db.String(50))
    tratamiento_riesgo = db.Column(db.String(255))
    observaciones = db.Column(db.Text)
    planes_accion = db.Column(db.Text)
    responsable = db.Column(db.String(255))
    fecha_implementacion = db.Column(db.String(50))
    impacto_res = db.Column(db.Integer)        # nivel numérico 1–5
    impacto_res_label = db.Column(db.String(100))  # descripción ("Moderado", "Alto", etc.)
    archivado = db.Column(Boolean, nullable=False, default=False)
    archivado_en = db.Column(DateTime, nullable=True)
    archivado_por = db.Column(db.String(120), nullable=True)
    tipo_riesgo_id = db.Column(
        db.Integer,
        db.ForeignKey("tipos_riesgo.id"),
        nullable=True
    )
    tipo_riesgo_id = db.Column(db.Integer, db.ForeignKey("tipos_riesgo.id"), nullable=True)

    # ✅ Relación: permite acceder a r.tipo_riesgo_rel.nombre
    tipo_riesgo_rel = db.relationship("TipoRiesgo", lazy="joined")

    controles_detalle = db.relationship(
        "RiesgoControl",
        back_populates="riesgo_rel",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="RiesgoControl.orden",
        lazy="selectin",
    )

    # ✅ Propiedad para que tu tabla use key="tipo_riesgo"
    @property
    def tipo_riesgo(self):
        return self.tipo_riesgo_rel.nombre if self.tipo_riesgo_rel else ""


class RiesgoControl(db.Model):
    """Evaluación individual de cada control asociado a un riesgo."""
    __tablename__ = "riesgo_control"

    id = db.Column(db.Integer, primary_key=True)
    riesgo_id = db.Column(
        db.Integer,
        db.ForeignKey("riesgo.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    orden = db.Column(db.Integer, nullable=False, default=1)

    estandar = db.Column(db.String(30), nullable=False)
    codigo_control = db.Column(db.String(80), nullable=True)
    nombre_control = db.Column(db.String(500), nullable=False)
    descripcion_control = db.Column(db.Text, nullable=True)

    asignacion = db.Column(db.String(50), nullable=True)
    cargo = db.Column(db.String(255), nullable=True)
    tipo_control = db.Column(db.String(50), nullable=True)
    forma_control = db.Column(db.String(50), nullable=True)
    frecuencia = db.Column(db.String(100), nullable=True)
    funcionalidad = db.Column(db.String(50), nullable=True)
    estado_control = db.Column(db.String(80), nullable=True)
    evidencia_control = db.Column(db.String(50), nullable=True)
    referencia_documental = db.Column(db.String(500), nullable=True)
    soporte_evidencia = db.Column(db.String(500), nullable=True)
    ejecucion_control = db.Column(db.String(50), nullable=True)

    diseno_control = db.Column(db.Float, nullable=False, default=0.0)
    valor_ejecucion_control = db.Column(db.Float, nullable=False, default=0.0)
    solidez_individual = db.Column(db.Float, nullable=False, default=0.0)

    creado_en = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    actualizado_en = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    riesgo_rel = db.relationship("Riesgo", back_populates="controles_detalle")


def asegurar_columnas_marcos_controles_riesgo():
    """
    Agrega las columnas multimarco a instalaciones existentes.
    En bases nuevas, db.create_all() las crea directamente desde el modelo.
    """
    try:
        RiesgoControl.__table__.create(bind=db.engine, checkfirst=True)
        inspector = inspect(db.engine)
        if "riesgo" not in inspector.get_table_names():
            return

        columnas_actuales = {
            columna.get("name")
            for columna in inspector.get_columns("riesgo")
        }

        columnas_requeridas = {
            "codigo_control_pci_dss": "VARCHAR(50)",
            "codigo_control_nist_csf": "VARCHAR(50)",
            "codigo_control_soc2": "VARCHAR(50)",
        }

        cambios = 0
        for nombre_columna, tipo_sql in columnas_requeridas.items():
            if nombre_columna not in columnas_actuales:
                db.session.execute(
                    text(f"ALTER TABLE riesgo ADD COLUMN {nombre_columna} {tipo_sql}")
                )
                cambios += 1

        if cambios:
            db.session.commit()
            print(f"✅ Gestión de Riesgos: {cambios} columna(s) multimarco agregada(s).")

    except Exception as e:
        db.session.rollback()
        print("⚠️ No se pudieron asegurar las columnas multimarco de Riesgo:", repr(e))


class TipoRiesgo(db.Model):
    __tablename__ = "tipos_riesgo"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)

    owner_user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False,
        index=True
    )

    activo = db.Column(db.Boolean, default=True, nullable=False)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    creado_por = db.Column(db.String(120), nullable=True)

    __table_args__ = (
        db.UniqueConstraint("owner_user_id", "nombre",
                            name="uq_tipo_riesgo_usuario"),
    )

class ConfigProbResidual(db.Model):
    __tablename__ = 'config_prob_residual'  # Nombre de la tabla
    id = db.Column(db.Integer, primary_key=True)
    min = db.Column(db.Float, nullable=False)
    max = db.Column(db.Float, nullable=False)
    bajar = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"<ConfigProbResidual {self.min}-{self.max} => bajar {self.bajar}>"

class ConfigImpactoResidual(db.Model):
    __tablename__ = 'config_impacto_residual'
    id = db.Column(db.Integer, primary_key=True)
    min = db.Column(db.Float, nullable=False)
    max = db.Column(db.Float, nullable=False)
    bajar = db.Column(db.Integer, nullable=False)


class ConfigEvaluacionControl(db.Model):
    """Porcentajes configurables para la evaluación y eficacia de controles."""
    __tablename__ = "config_evaluacion_control"

    id = db.Column(db.Integer, primary_key=True)
    clave = db.Column(db.String(80), nullable=False, unique=True, index=True)
    grupo = db.Column(db.String(100), nullable=False)
    opcion = db.Column(db.String(150), nullable=False)
    porcentaje = db.Column(db.Float, nullable=False)
    orden = db.Column(db.Integer, nullable=False, default=0)
    actualizado_en = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


# ============================================================
# MOTOR ÚNICO DE CÁLCULO DE RIESGO RESIDUAL
# - La solidez se guarda internamente entre 0 y 1.
# - Las reglas configuradas pueden estar en 0..100 o en 0..1.
# - En límites compartidos se aplica el rango de mayor solidez.
# - La matriz 5x5 usa los mismos umbrales del Mapa de Calor.
# ============================================================
RISK_PROB_LABEL_TO_NUM = {
    "Rara vez o Muy baja": 1,
    "Eventualmente o baja": 2,
    "Puede ocurrir o Moderada": 3,
    "Probable o Alta": 4,
    "Muy frecuente o Muy Alta": 5,
}
RISK_PROB_NUM_TO_LABEL = {v: k for k, v in RISK_PROB_LABEL_TO_NUM.items()}

RISK_IMPACT_LABEL_TO_NUM = {
    "Insignificante o Inferior": 1,
    "Menor": 2,
    "Moderado o Importante": 3,
    "Mayor": 4,
    "Catastrófico o Crítico": 5,
}
RISK_IMPACT_NUM_TO_LABEL = {v: k for k, v in RISK_IMPACT_LABEL_TO_NUM.items()}

# Valores iniciales del instrumento. Se copian a la base de datos la primera vez
# y posteriormente pueden modificarse desde Gestión de Riesgos > Parámetros.
RISK_CONTROL_PARAMETER_DEFINITIONS = (
    {"clave": "asignacion_asignado", "grupo": "Asignación", "opcion": "Asignado", "porcentaje": 20.0, "orden": 10},
    {"clave": "asignacion_no_asignado", "grupo": "Asignación", "opcion": "No Asignado", "porcentaje": 0.0, "orden": 11},

    {"clave": "tipo_preventivo", "grupo": "Tipo de Control", "opcion": "Preventivo", "porcentaje": 15.0, "orden": 20},
    {"clave": "tipo_detectivo", "grupo": "Tipo de Control", "opcion": "Detectivo", "porcentaje": 10.0, "orden": 21},
    {"clave": "tipo_correctivo", "grupo": "Tipo de Control", "opcion": "Correctivo", "porcentaje": 7.0, "orden": 22},

    {"clave": "forma_automatico", "grupo": "Forma de Control", "opcion": "Automático", "porcentaje": 15.0, "orden": 30},
    {"clave": "forma_semiautomatico", "grupo": "Forma de Control", "opcion": "Semiautomático", "porcentaje": 7.0, "orden": 31},
    {"clave": "forma_manual", "grupo": "Forma de Control", "opcion": "Manual", "porcentaje": 5.0, "orden": 32},

    {"clave": "funcionalidad_adecuada", "grupo": "Funcionalidad", "opcion": "Adecuada", "porcentaje": 15.0, "orden": 40},
    {"clave": "funcionalidad_no_adecuada", "grupo": "Funcionalidad", "opcion": "No Adecuada", "porcentaje": 0.0, "orden": 41},

    {"clave": "estado_implementado_documentado", "grupo": "Estado del Control", "opcion": "Implementado y Documentado", "porcentaje": 20.0, "orden": 50},
    {"clave": "estado_implementado_no_documentado", "grupo": "Estado del Control", "opcion": "Implementado y No Documentado", "porcentaje": 7.0, "orden": 51},
    {"clave": "estado_no_documentado", "grupo": "Estado del Control", "opcion": "No Documentado", "porcentaje": 0.0, "orden": 52},

    {"clave": "evidencia_con_evidencia", "grupo": "Evidencia del Control", "opcion": "Con Evidencia", "porcentaje": 15.0, "orden": 60},
    {"clave": "evidencia_sin_evidencia", "grupo": "Evidencia del Control", "opcion": "Sin Evidencia", "porcentaje": 0.0, "orden": 61},

    {"clave": "ejecucion_siempre", "grupo": "Ejecución", "opcion": "Siempre", "porcentaje": 100.0, "orden": 70},
    {"clave": "ejecucion_casi_siempre", "grupo": "Ejecución", "opcion": "Casi Siempre", "porcentaje": 50.0, "orden": 71},
    {"clave": "ejecucion_nunca", "grupo": "Ejecución", "opcion": "Nunca", "porcentaje": 0.0, "orden": 72},

    {"clave": "formula_peso_diseno", "grupo": "Fórmula de Solidez Individual", "opcion": "Peso del Diseño", "porcentaje": 60.0, "orden": 80},
    {"clave": "formula_peso_ejecucion", "grupo": "Fórmula de Solidez Individual", "opcion": "Peso de la Ejecución", "porcentaje": 40.0, "orden": 81},
)

RISK_CONTROL_DESIGN_GROUP_KEYS = {
    "Asignación": ("asignacion_asignado", "asignacion_no_asignado"),
    "Tipo de Control": ("tipo_preventivo", "tipo_detectivo", "tipo_correctivo"),
    "Forma de Control": ("forma_automatico", "forma_semiautomatico", "forma_manual"),
    "Funcionalidad": ("funcionalidad_adecuada", "funcionalidad_no_adecuada"),
    "Estado del Control": (
        "estado_implementado_documentado",
        "estado_implementado_no_documentado",
        "estado_no_documentado",
    ),
    "Evidencia del Control": ("evidencia_con_evidencia", "evidencia_sin_evidencia"),
}


def riesgo_asegurar_config_evaluacion_control():
    """Crea la tabla y carga únicamente los parámetros que aún no existan."""
    try:
        ConfigEvaluacionControl.__table__.create(bind=db.engine, checkfirst=True)
        existentes = {
            fila.clave: fila
            for fila in ConfigEvaluacionControl.query.all()
        }
        cambios = False
        for definicion in RISK_CONTROL_PARAMETER_DEFINITIONS:
            fila = existentes.get(definicion["clave"])
            if fila is None:
                db.session.add(ConfigEvaluacionControl(**definicion))
                cambios = True
                continue

            # Mantiene nombre, agrupación y orden alineados con el formulario,
            # sin sobrescribir el porcentaje definido por el usuario.
            if (
                fila.grupo != definicion["grupo"]
                or fila.opcion != definicion["opcion"]
                or fila.orden != definicion["orden"]
            ):
                fila.grupo = definicion["grupo"]
                fila.opcion = definicion["opcion"]
                fila.orden = definicion["orden"]
                cambios = True

        if cambios:
            db.session.commit()
        return True
    except Exception as exc:
        db.session.rollback()
        print("[WARN] No se pudo inicializar la configuración de evaluación de controles:", repr(exc))
        return False


def riesgo_obtener_config_evaluacion_control():
    """Devuelve los porcentajes vigentes convertidos a fracciones entre 0 y 1."""
    riesgo_asegurar_config_evaluacion_control()
    valores = {
        item["clave"]: max(0.0, min(1.0, float(item["porcentaje"]) / 100.0))
        for item in RISK_CONTROL_PARAMETER_DEFINITIONS
    }
    try:
        for fila in ConfigEvaluacionControl.query.all():
            if fila.clave in valores:
                valores[fila.clave] = max(0.0, min(1.0, float(fila.porcentaje or 0.0) / 100.0))
    except Exception as exc:
        print("[WARN] Se usarán parámetros predeterminados de evaluación de controles:", repr(exc))

    peso_diseno = valores["formula_peso_diseno"]
    peso_ejecucion = valores["formula_peso_ejecucion"]
    total_pesos = peso_diseno + peso_ejecucion
    if total_pesos <= 0:
        peso_diseno, peso_ejecucion = 0.60, 0.40
    else:
        # Protección adicional para configuraciones antiguas o alteradas manualmente.
        peso_diseno /= total_pesos
        peso_ejecucion /= total_pesos

    return {
        "diseno": {
            "asignacion": {
                "asignado": valores["asignacion_asignado"],
                "no asignado": valores["asignacion_no_asignado"],
            },
            "tipo_control": {
                "preventivo": valores["tipo_preventivo"],
                "detectivo": valores["tipo_detectivo"],
                "correctivo": valores["tipo_correctivo"],
            },
            "forma_control": {
                "automatico": valores["forma_automatico"],
                "semiautomatico": valores["forma_semiautomatico"],
                "manual": valores["forma_manual"],
            },
            "funcionalidad": {
                "adecuada": valores["funcionalidad_adecuada"],
                "no adecuada": valores["funcionalidad_no_adecuada"],
            },
            "estado_control": {
                "implementado y documentado": valores["estado_implementado_documentado"],
                "implementado y no documentado": valores["estado_implementado_no_documentado"],
                "no documentado": valores["estado_no_documentado"],
            },
            "evidencia_control": {
                "con evidencia": valores["evidencia_con_evidencia"],
                "sin evidencia": valores["evidencia_sin_evidencia"],
            },
        },
        "ejecucion": {
            "siempre": valores["ejecucion_siempre"],
            "casi siempre": valores["ejecucion_casi_siempre"],
            "nunca": valores["ejecucion_nunca"],
        },
        "peso_diseno": peso_diseno,
        "peso_ejecucion": peso_ejecucion,
        "valores": valores,
    }


def riesgo_parametros_control_frontend(configuracion=None):
    """Convierte la configuración a las etiquetas exactas utilizadas en el formulario."""
    cfg = configuracion or riesgo_obtener_config_evaluacion_control()
    d = cfg["diseno"]
    e = cfg["ejecucion"]
    return {
        "asignacion": {
            "Asignado": d["asignacion"]["asignado"],
            "No Asignado": d["asignacion"]["no asignado"],
        },
        "tipo": {
            "Preventivo": d["tipo_control"]["preventivo"],
            "Detectivo": d["tipo_control"]["detectivo"],
            "Correctivo": d["tipo_control"]["correctivo"],
        },
        "forma": {
            "Automático": d["forma_control"]["automatico"],
            "Semiautomático": d["forma_control"]["semiautomatico"],
            "Manual": d["forma_control"]["manual"],
        },
        "funcionalidad": {
            "Adecuada": d["funcionalidad"]["adecuada"],
            "No Adecuada": d["funcionalidad"]["no adecuada"],
        },
        "estado": {
            "Implementado y Documentado": d["estado_control"]["implementado y documentado"],
            "Implementado y No Documentado": d["estado_control"]["implementado y no documentado"],
            "No Documentado": d["estado_control"]["no documentado"],
        },
        "evidencia": {
            "Con Evidencia": d["evidencia_control"]["con evidencia"],
            "Sin Evidencia": d["evidencia_control"]["sin evidencia"],
        },
        "ejecucion": {
            "Siempre": e["siempre"],
            "Casi Siempre": e["casi siempre"],
            "Nunca": e["nunca"],
        },
        "peso_diseno": cfg["peso_diseno"],
        "peso_ejecucion": cfg["peso_ejecucion"],
    }


def riesgo_normalizar_opcion(valor):
    texto = str(valor or "").strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto).strip()


def riesgo_float(valor, default=None):
    if valor is None:
        return default
    texto = str(valor).strip().replace("%", "").replace(",", ".")
    if not texto:
        return default
    try:
        return float(texto)
    except (TypeError, ValueError):
        return default


def riesgo_normalizar_fraccion(valor, default=0.0):
    """Convierte 80, '80%', 0.8 o '0.8' a 0.8 y limita a 0..1."""
    numero = riesgo_float(valor, None)
    if numero is None:
        return default
    if numero > 1.0:
        numero = numero / 100.0
    return max(0.0, min(1.0, float(numero)))


def riesgo_formatear_porcentaje(fraccion):
    porcentaje = riesgo_normalizar_fraccion(fraccion, 0.0) * 100.0
    return f"{porcentaje:.2f}".rstrip("0").rstrip(".") + "%"


def riesgo_nivel_numero(valor, tipo="probabilidad", default=1):
    mapa = RISK_PROB_LABEL_TO_NUM if tipo == "probabilidad" else RISK_IMPACT_LABEL_TO_NUM
    if valor in mapa:
        return mapa[valor]

    numero = riesgo_float(valor, None)
    if numero is not None:
        return max(1, min(5, int(round(numero))))

    texto = riesgo_normalizar_opcion(valor)
    if tipo == "probabilidad":
        if "muy frecuente" in texto or "muy alta" in texto:
            return 5
        if "probable" in texto or texto == "alta":
            return 4
        if "puede ocurrir" in texto or "moderada" in texto:
            return 3
        if "eventual" in texto or texto == "baja":
            return 2
        if "rara" in texto or "muy baja" in texto:
            return 1
    else:
        if "catastrofico" in texto or "critico" in texto:
            return 5
        if texto == "mayor":
            return 4
        if "moderado" in texto or "importante" in texto:
            return 3
        if texto == "menor":
            return 2
        if "insignificante" in texto or "inferior" in texto:
            return 1
    return max(1, min(5, int(default or 1)))


def riesgo_clasificar_puntaje(puntaje):
    """Umbrales oficiales usados por el mapa de calor del módulo."""
    valor = max(1, min(25, int(round(float(puntaje or 1)))))
    if valor <= 4:
        return "Bajo"
    if valor <= 8:
        return "Medio"
    if valor <= 12:
        return "Alto"
    if valor <= 20:
        return "Muy Alto"
    return "Extremo"


def riesgo_normalizar_reglas(reglas):
    normalizadas = []
    for posicion, regla in enumerate(reglas or []):
        try:
            if isinstance(regla, dict):
                minimo = riesgo_float(regla.get("min"), None)
                maximo = riesgo_float(regla.get("max"), None)
                bajar = int(regla.get("bajar") or 0)
            else:
                minimo = riesgo_float(getattr(regla, "min", None), None)
                maximo = riesgo_float(getattr(regla, "max", None), None)
                bajar = int(getattr(regla, "bajar", 0) or 0)
            if minimo is None or maximo is None:
                continue

            # Compatibilidad con configuraciones antiguas expresadas como 0..1.
            if max(abs(minimo), abs(maximo)) <= 1.0:
                minimo *= 100.0
                maximo *= 100.0

            rango_min = max(0.0, min(100.0, min(minimo, maximo)))
            rango_max = max(0.0, min(100.0, max(minimo, maximo)))
            normalizadas.append({
                "rmin": rango_min,
                "rmax": rango_max,
                "bajar": max(0, min(4, bajar)),
                "posicion": posicion,
            })
        except Exception as exc:
            print("[WARN] Regla residual inválida:", repr(exc))

    # En límites compartidos (ej. 60-80 y 80-100), prevalece el rango superior.
    return sorted(
        normalizadas,
        key=lambda item: (item["rmin"], -(item["rmax"] - item["rmin"]), -item["posicion"]),
        reverse=True,
    )


def riesgo_resolver_regla_solidez(solidez_individual, reglas):
    """
    Resuelve la banda configurada para una solidez entre 0 y 100.

    Prioridad:
    1. Coincidencia exacta dentro del intervalo.
    2. Si existen huecos entre bandas, usa la banda más cercana.
    3. Si el porcentaje supera el máximo configurado, usa la banda superior.
    4. Si queda por debajo del mínimo configurado, usa la banda inferior.

    De esta manera una solidez válida nunca queda sin regla por decimales,
    límites compartidos o pequeños huecos de configuración.
    """
    solidez_pct = riesgo_normalizar_fraccion(solidez_individual, 0.0) * 100.0
    reglas_norm = riesgo_normalizar_reglas(reglas)

    if not reglas_norm:
        return None, solidez_pct, "sin_reglas"

    # Coincidencia directa. La lista ya está ordenada para que en límites
    # compartidos prevalezca la banda de mayor solidez.
    for regla in reglas_norm:
        if regla["rmin"] <= solidez_pct <= regla["rmax"]:
            return regla, solidez_pct, "exacta"

    # Por encima o por debajo de todo el instrumento.
    banda_superior = max(reglas_norm, key=lambda item: (item["rmax"], item["rmin"]))
    banda_inferior = min(reglas_norm, key=lambda item: (item["rmin"], item["rmax"]))
    if solidez_pct > banda_superior["rmax"]:
        return banda_superior, solidez_pct, "superior"
    if solidez_pct < banda_inferior["rmin"]:
        return banda_inferior, solidez_pct, "inferior"

    # Hueco entre intervalos: selecciona la banda más cercana. En empate,
    # privilegia la banda superior porque representa mayor solidez.
    def distancia(item):
        if solidez_pct < item["rmin"]:
            return item["rmin"] - solidez_pct
        if solidez_pct > item["rmax"]:
            return solidez_pct - item["rmax"]
        return 0.0

    regla = min(
        reglas_norm,
        key=lambda item: (distancia(item), -item["rmin"], -item["rmax"]),
    )
    return regla, solidez_pct, "cercana"


def riesgo_reduccion_por_solidez(solidez_individual, reglas):
    regla, solidez_pct, modo = riesgo_resolver_regla_solidez(solidez_individual, reglas)
    if regla is None:
        return 0, None, solidez_pct
    regla_aplicada = dict(regla)
    regla_aplicada["modo"] = modo
    return regla_aplicada["bajar"], regla_aplicada, solidez_pct


def riesgo_calcular_solidez_control(
    asignacion=None,
    tipo_control=None,
    forma_control=None,
    funcionalidad=None,
    estado_control=None,
    evidencia_control=None,
    ejecucion_control=None,
    diseno_control=None,
    solidez_existente=None,
    configuracion_control=None,
):
    configuracion_control = configuracion_control or riesgo_obtener_config_evaluacion_control()
    mapas_diseno = configuracion_control["diseno"]
    mapa_ejecucion = configuracion_control["ejecucion"]

    valores = {
        "asignacion": asignacion,
        "tipo_control": tipo_control,
        "forma_control": forma_control,
        "funcionalidad": funcionalidad,
        "estado_control": estado_control,
        "evidencia_control": evidencia_control,
    }

    componentes = {}
    evaluacion_completa = True
    for campo, valor in valores.items():
        clave = riesgo_normalizar_opcion(valor)
        mapa = mapas_diseno[campo]
        if clave in mapa:
            componentes[campo] = mapa[clave]
        else:
            componentes[campo] = 0.0
            evaluacion_completa = False

    if evaluacion_completa:
        diseno = max(0.0, min(1.0, sum(componentes.values())))
    else:
        diseno = riesgo_normalizar_fraccion(diseno_control, None)

    clave_ejecucion = riesgo_normalizar_opcion(ejecucion_control)
    ejecucion = mapa_ejecucion.get(clave_ejecucion)

    if evaluacion_completa and diseno is not None and ejecucion is not None:
        solidez = max(
            0.0,
            min(
                1.0,
                (diseno * configuracion_control["peso_diseno"])
                + (ejecucion * configuracion_control["peso_ejecucion"]),
            ),
        )
        calculada = True
    else:
        solidez = riesgo_normalizar_fraccion(solidez_existente, 0.0)
        calculada = False

    return {
        "diseno": diseno,
        "ejecucion": ejecucion,
        "solidez": round(solidez, 6),
        "componentes": componentes,
        "calculada": calculada,
    }


# ============================================================
# CONTROLES MÚLTIPLES POR RIESGO
# ============================================================
RISK_CONTROL_STANDARD_LABELS = {
    "ISO_27001": "ISO 27001 / Anexo A (ISO 27002:2022)",
    "NIST_CSF": "NIST CSF 2.0",
    "PCI_DSS": "PCI DSS",
    "SOC_2": "SOC 2",
    "OTROS": "Otros",
}


def riesgo_normalizar_estandar_control(valor):
    clave = riesgo_normalizar_opcion(valor).replace("/", " ").replace("_", " ")
    if clave in {"iso 27001", "iso 27002", "iso iec 27001", "iso iec 27002", "iso 27001 anexo a"}:
        return "ISO_27001"
    if clave in {"nist", "nist csf", "nist csf 2.0", "nist csf 20"}:
        return "NIST_CSF"
    if clave in {"pci", "pci dss", "pcidss"}:
        return "PCI_DSS"
    if clave in {"soc", "soc 2", "soc2"}:
        return "SOC_2"
    if clave in {"otros", "otro", "other"}:
        return "OTROS"
    if str(valor or "").strip() in RISK_CONTROL_STANDARD_LABELS:
        return str(valor).strip()
    return ""


def riesgo_catalogo_fuente(estandar):
    return {
        "ISO_27001": ISO_27002_CONTROLES,
        "NIST_CSF": NIST_CSF_20_CONTROLES,
        "PCI_DSS": PCI_DSS_CONTROLES,
        "SOC_2": SOC2_CONTROLES,
    }.get(estandar, [])


def riesgo_texto_resumido(valor, limite=135):
    texto = re.sub(r"\s+", " ", str(valor or "")).strip()
    if len(texto) <= limite:
        return texto
    return texto[: limite - 1].rstrip() + "…"


def riesgo_catalogos_para_frontend():
    temas_iso = {
        str(item.get("nr") or "").strip(): str(item.get("topic") or "").strip()
        for item in (globals().get("FULL_SOA") or [])
        if isinstance(item, dict)
    }
    resultado = {}
    for estandar in ("ISO_27001", "NIST_CSF", "PCI_DSS", "SOC_2"):
        items = []
        for codigo, descripcion in riesgo_catalogo_fuente(estandar):
            codigo = str(codigo or "").strip()
            descripcion = str(descripcion or "").strip()
            nombre = temas_iso.get(codigo) if estandar == "ISO_27001" else ""
            if not nombre:
                nombre = riesgo_texto_resumido(descripcion)
            items.append({
                "codigo": codigo,
                "nombre": nombre,
                "descripcion": descripcion,
            })
        resultado[estandar] = items
    return resultado


def riesgo_buscar_control_catalogo(estandar, codigo):
    estandar = riesgo_normalizar_estandar_control(estandar)
    codigo = str(codigo or "").strip()
    if not estandar or not codigo or estandar == "OTROS":
        return None
    for item in riesgo_catalogos_para_frontend().get(estandar, []):
        if item["codigo"] == codigo:
            return item
    return None


def riesgo_lista_form(form, nombre):
    try:
        return form.getlist(nombre)
    except Exception:
        valor = form.get(nombre)
        return [valor] if valor is not None else []


def riesgo_extraer_controles_formulario(form):
    configuracion_control = riesgo_obtener_config_evaluacion_control()
    campos = {
        "estandar": riesgo_lista_form(form, "control_estandar[]"),
        "codigo": riesgo_lista_form(form, "control_catalogo_codigo[]"),
        "otro_nombre": riesgo_lista_form(form, "control_otro_nombre[]"),
        "otro_descripcion": riesgo_lista_form(form, "control_otro_descripcion[]"),
        "asignacion": riesgo_lista_form(form, "control_asignacion[]"),
        "cargo": riesgo_lista_form(form, "control_cargo[]"),
        "tipo_control": riesgo_lista_form(form, "control_tipo[]"),
        "forma_control": riesgo_lista_form(form, "control_forma[]"),
        "frecuencia": riesgo_lista_form(form, "control_frecuencia[]"),
        "funcionalidad": riesgo_lista_form(form, "control_funcionalidad[]"),
        "estado_control": riesgo_lista_form(form, "control_estado[]"),
        "evidencia_control": riesgo_lista_form(form, "control_evidencia[]"),
        "referencia_documental": riesgo_lista_form(form, "control_referencia[]"),
        "soporte_evidencia": riesgo_lista_form(form, "control_soporte[]"),
        "ejecucion_control": riesgo_lista_form(form, "control_ejecucion[]"),
        # Valores históricos usados como respaldo durante la migración de
        # riesgos anteriores y riesgos originados en Superficie de Ataque.
        "diseno_existente": riesgo_lista_form(form, "control_diseno_existente[]"),
        "solidez_existente": riesgo_lista_form(form, "control_solidez_existente[]"),
    }
    total = max((len(v) for v in campos.values()), default=0)

    def valor(campo, posicion):
        lista = campos.get(campo, [])
        return str(lista[posicion] if posicion < len(lista) else "").strip()

    controles = []
    for i in range(total):
        estandar = riesgo_normalizar_estandar_control(valor("estandar", i))
        if not estandar:
            continue

        codigo = valor("codigo", i)
        nombre = ""
        descripcion = ""
        if estandar == "OTROS":
            nombre = valor("otro_nombre", i)
            descripcion = valor("otro_descripcion", i)
            codigo = ""
            if not nombre:
                continue
        else:
            if not codigo:
                continue
            catalogo = riesgo_buscar_control_catalogo(estandar, codigo)
            if catalogo:
                nombre = catalogo["nombre"] or codigo
                descripcion = catalogo["descripcion"] or ""
            else:
                nombre = codigo

        evaluacion = {
            "asignacion": valor("asignacion", i),
            "cargo": valor("cargo", i),
            "tipo_control": valor("tipo_control", i),
            "forma_control": valor("forma_control", i),
            "frecuencia": valor("frecuencia", i),
            "funcionalidad": valor("funcionalidad", i),
            "estado_control": valor("estado_control", i),
            "evidencia_control": valor("evidencia_control", i),
            "referencia_documental": valor("referencia_documental", i),
            "soporte_evidencia": valor("soporte_evidencia", i),
            "ejecucion_control": valor("ejecucion_control", i),
        }
        calculo = riesgo_calcular_solidez_control(
            asignacion=evaluacion["asignacion"],
            tipo_control=evaluacion["tipo_control"],
            forma_control=evaluacion["forma_control"],
            funcionalidad=evaluacion["funcionalidad"],
            estado_control=evaluacion["estado_control"],
            evidencia_control=evaluacion["evidencia_control"],
            ejecucion_control=evaluacion["ejecucion_control"],
            # Si el registro proviene de una versión anterior o de
            # Superficie de Ataque, conserva la efectividad existente hasta
            # que la evaluación nueva esté completamente diligenciada.
            diseno_control=valor("diseno_existente", i),
            solidez_existente=valor("solidez_existente", i),
            configuracion_control=configuracion_control,
        )
        controles.append({
            "orden": len(controles) + 1,
            "estandar": estandar,
            "codigo_control": codigo,
            "nombre_control": nombre,
            "descripcion_control": descripcion,
            **evaluacion,
            "diseno_control": calculo["diseno"] or 0.0,
            "valor_ejecucion_control": calculo["ejecucion"] or 0.0,
            "solidez_individual": calculo["solidez"],
            "componentes": calculo["componentes"],
        })
    return controles


def riesgo_calcular_solidez_grupal(controles):
    valores = [
        riesgo_normalizar_fraccion(c.get("solidez_individual"), 0.0)
        for c in (controles or [])
    ]
    if not valores:
        return 0.0
    return round(sum(valores) / len(valores), 6)


def riesgo_reemplazar_controles(riesgo, controles):
    riesgo.controles_detalle.clear()
    for posicion, control in enumerate(controles or [], start=1):
        riesgo.controles_detalle.append(RiesgoControl(
            orden=posicion,
            estandar=control.get("estandar") or "OTROS",
            codigo_control=control.get("codigo_control") or None,
            nombre_control=control.get("nombre_control") or "Control sin nombre",
            descripcion_control=control.get("descripcion_control") or None,
            asignacion=control.get("asignacion") or None,
            cargo=control.get("cargo") or None,
            tipo_control=control.get("tipo_control") or None,
            forma_control=control.get("forma_control") or None,
            frecuencia=control.get("frecuencia") or None,
            funcionalidad=control.get("funcionalidad") or None,
            estado_control=control.get("estado_control") or None,
            evidencia_control=control.get("evidencia_control") or None,
            referencia_documental=control.get("referencia_documental") or None,
            soporte_evidencia=control.get("soporte_evidencia") or None,
            ejecucion_control=control.get("ejecucion_control") or None,
            diseno_control=riesgo_normalizar_fraccion(control.get("diseno_control"), 0.0),
            valor_ejecucion_control=riesgo_normalizar_fraccion(control.get("valor_ejecucion_control"), 0.0),
            solidez_individual=riesgo_normalizar_fraccion(control.get("solidez_individual"), 0.0),
        ))


def riesgo_sincronizar_campos_legacy(riesgo, controles):
    '''Mantiene reportes antiguos compatibles y guarda la solidez grupal efectiva.'''
    controles = list(controles or [])
    grupal = riesgo_calcular_solidez_grupal(controles)
    riesgo.solidez_grupal = grupal
    riesgo.valor = grupal

    if not controles:
        riesgo.control_codigo = None
        riesgo.codigo_anexo = None
        riesgo.codigo_control_pci_dss = None
        riesgo.codigo_control_nist_csf = None
        riesgo.codigo_control_soc2 = None
        riesgo.descripcion_control = None
        riesgo.solidez_individual = 0.0
        return grupal

    primero = controles[0]
    riesgo.solidez_individual = riesgo_normalizar_fraccion(primero.get("solidez_individual"), 0.0)
    riesgo.control_codigo = " | ".join(
        f"{RISK_CONTROL_STANDARD_LABELS.get(c.get('estandar'), c.get('estandar'))}: "
        f"{c.get('codigo_control') or c.get('nombre_control')}"
        for c in controles
    )
    riesgo.codigo_anexo = ", ".join(c.get("codigo_control") or "" for c in controles if c.get("estandar") == "ISO_27001")
    riesgo.codigo_control_nist_csf = ", ".join(c.get("codigo_control") or "" for c in controles if c.get("estandar") == "NIST_CSF")
    riesgo.codigo_control_pci_dss = ", ".join(c.get("codigo_control") or "" for c in controles if c.get("estandar") == "PCI_DSS")
    riesgo.codigo_control_soc2 = ", ".join(c.get("codigo_control") or "" for c in controles if c.get("estandar") == "SOC_2")
    riesgo.descripcion_control = "\n\n".join(
        f"{RISK_CONTROL_STANDARD_LABELS.get(c.get('estandar'), c.get('estandar'))} — "
        f"{c.get('codigo_control') or c.get('nombre_control')}\n"
        f"{c.get('nombre_control') or ''}\n{c.get('descripcion_control') or ''}".strip()
        for c in controles
    )

    riesgo.asignacion = primero.get("asignacion")
    riesgo.cargo = primero.get("cargo")
    riesgo.tipo_control = primero.get("tipo_control")
    riesgo.forma_control = primero.get("forma_control")
    riesgo.frecuencia = primero.get("frecuencia")
    riesgo.funcionalidad = primero.get("funcionalidad")
    riesgo.estado_control = primero.get("estado_control")
    riesgo.referencia_documental = primero.get("referencia_documental")
    riesgo.evidencia_control = primero.get("evidencia_control")
    riesgo.soporte_evidencia = primero.get("soporte_evidencia")
    riesgo.ejecucion_control = primero.get("ejecucion_control")
    riesgo.diseno_control = riesgo_formatear_porcentaje(primero.get("diseno_control"))
    riesgo.valor_ejecucion_control = riesgo_normalizar_fraccion(primero.get("valor_ejecucion_control"), 0.0)

    componentes = primero.get("componentes") or {}
    riesgo.calificacion_asignacion = componentes.get("asignacion", 0.0)
    riesgo.calificacion_tipo_control = componentes.get("tipo_control", 0.0)
    riesgo.calificacion_forma_control = componentes.get("forma_control", 0.0)
    riesgo.calificacion_funcionalidad = componentes.get("funcionalidad", 0.0)
    riesgo.calificacion_estado_control = componentes.get("estado_control", 0.0)
    riesgo.calificacion_soporte_evidencia = componentes.get("evidencia_control", 0.0)
    return grupal


def riesgo_control_para_dict(control):
    return {
        "estandar": control.estandar or "OTROS",
        "codigo_control": control.codigo_control or "",
        "nombre_control": control.nombre_control or "",
        "descripcion_control": control.descripcion_control or "",
        "asignacion": control.asignacion or "",
        "cargo": control.cargo or "",
        "tipo_control": control.tipo_control or "",
        "forma_control": control.forma_control or "",
        "frecuencia": control.frecuencia or "",
        "funcionalidad": control.funcionalidad or "",
        "estado_control": control.estado_control or "",
        "evidencia_control": control.evidencia_control or "",
        "referencia_documental": control.referencia_documental or "",
        "soporte_evidencia": control.soporte_evidencia or "",
        "ejecucion_control": control.ejecucion_control or "",
        "diseno_control": riesgo_normalizar_fraccion(control.diseno_control, 0.0),
        "solidez_individual": riesgo_normalizar_fraccion(control.solidez_individual, 0.0),
    }


def riesgo_controles_para_formulario(riesgo):
    filas = list(getattr(riesgo, "controles_detalle", []) or [])
    if filas:
        return [riesgo_control_para_dict(c) for c in filas]

    # Compatibilidad: convierte la evaluación única histórica en uno o varios controles virtuales.
    referencias = [
        ("ISO_27001", getattr(riesgo, "codigo_anexo", None)),
        ("NIST_CSF", getattr(riesgo, "codigo_control_nist_csf", None)),
        ("PCI_DSS", getattr(riesgo, "codigo_control_pci_dss", None)),
        ("SOC_2", getattr(riesgo, "codigo_control_soc2", None)),
    ]
    controles = []
    for estandar, codigo in referencias:
        codigo = str(codigo or "").strip()
        if not codigo:
            continue
        item = riesgo_buscar_control_catalogo(estandar, codigo) or {
            "codigo": codigo,
            "nombre": codigo,
            "descripcion": "",
        }
        controles.append({
            "estandar": estandar,
            "codigo_control": codigo,
            "nombre_control": item.get("nombre") or codigo,
            "descripcion_control": item.get("descripcion") or "",
        })

    if not controles and (getattr(riesgo, "control_codigo", None) or getattr(riesgo, "descripcion_control", None)):
        controles.append({
            "estandar": "OTROS",
            "codigo_control": "",
            "nombre_control": getattr(riesgo, "control_codigo", None) or "Control existente",
            "descripcion_control": getattr(riesgo, "descripcion_control", None) or "",
        })

    for control in controles:
        control.update({
            "asignacion": getattr(riesgo, "asignacion", None) or "",
            "cargo": getattr(riesgo, "cargo", None) or "",
            "tipo_control": getattr(riesgo, "tipo_control", None) or "",
            "forma_control": getattr(riesgo, "forma_control", None) or "",
            "frecuencia": getattr(riesgo, "frecuencia", None) or "",
            "funcionalidad": getattr(riesgo, "funcionalidad", None) or "",
            "estado_control": getattr(riesgo, "estado_control", None) or "",
            "evidencia_control": getattr(riesgo, "evidencia_control", None) or "",
            "referencia_documental": getattr(riesgo, "referencia_documental", None) or "",
            "soporte_evidencia": getattr(riesgo, "soporte_evidencia", None) or "",
            "ejecucion_control": getattr(riesgo, "ejecucion_control", None) or "",
            "diseno_control": riesgo_normalizar_fraccion(getattr(riesgo, "diseno_control", None), 0.0),
            "solidez_individual": riesgo_normalizar_fraccion(getattr(riesgo, "solidez_individual", None), 0.0),
        })
    return controles


def riesgo_json_seguro(valor):
    return json.dumps(valor, ensure_ascii=False).replace("</", "<\\/")


def riesgo_controles_widget_html(controles_iniciales=None, reglas_prob=None, reglas_imp=None, section_class="riskform-section-title"):
    catalogos_json = riesgo_json_seguro(riesgo_catalogos_para_frontend())
    iniciales_json = riesgo_json_seguro(controles_iniciales or [])
    reglas_prob_json = riesgo_json_seguro(reglas_prob or [])
    reglas_imp_json = riesgo_json_seguro(reglas_imp or [])
    parametros_control_json = riesgo_json_seguro(riesgo_parametros_control_frontend())
    plantilla = r'''
<div class="col-12">
  <div class="%SECTION_CLASS% risk-controls-section-header">
    <span>🧩 Controles Actuales - Evaluación del Control</span>
    <button type="button" class="btn btn-outline-primary btn-sm rounded-pill" onclick="riesgoAgregarControl()">
      ➕ Agregar control
    </button>
  </div>
  <div class="risk-controls-help">
    Seleccione el estándar y el control. Cada control tiene su propia evaluación, diseño y solidez individual. Los riesgos históricos conservan su efectividad hasta completar la nueva evaluación.
  </div>
</div>
<div class="col-12">
  <div id="risk-controls-container" class="risk-controls-container"></div>
</div>

<style>
  .risk-controls-section-header{display:flex!important;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
  .risk-controls-help{font-size:.78rem;color:#64748b;margin:-5px 0 10px 2px}
  .risk-controls-container{display:flex;flex-direction:column;gap:14px}
  .risk-control-card{border:1px solid #cfe0f5;border-radius:16px;background:linear-gradient(180deg,#f8fbff,#fff);box-shadow:0 8px 18px rgba(15,23,42,.08);padding:14px}
  .risk-control-card-header{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:12px;padding-bottom:9px;border-bottom:1px solid #dbe8f7}
  .risk-control-card-title{font-weight:950;color:#0b4a8f;font-size:.88rem}
  .risk-control-card-badge{font-size:.68rem;font-weight:900;color:#1d4f8f;background:#e7f1ff;border:1px solid #cfe0f5;border-radius:999px;padding:4px 9px}
  .risk-control-remove{border:none;background:#fff1f2;color:#b91c1c;border-radius:999px;font-weight:900;font-size:.72rem;padding:5px 10px}
  .risk-control-result{background:#eff6ff!important;color:#0b4a8f!important;font-weight:950!important}
  .risk-control-description{min-height:82px!important}
  .risk-control-hidden{display:none!important}
  @media(max-width:768px){.risk-controls-section-header .btn{width:100%}.risk-control-card{padding:10px}}
</style>

<script>
(function(){
  const CATALOGOS = %CATALOGOS%;
  const INICIALES = %INICIALES%;
  const REGLAS_PROB = %REGLAS_PROB%;
  const REGLAS_IMP = %REGLAS_IMP%;
  const PARAMETROS_CONTROL = %PARAMETROS_CONTROL%;
  const ETIQUETAS = {
    ISO_27001: 'ISO 27001 / Anexo A',
    NIST_CSF: 'NIST CSF 2.0',
    PCI_DSS: 'PCI DSS',
    SOC_2: 'SOC 2',
    OTROS: 'Otros'
  };

  function esc(v){
    return String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
  }
  function seleccionado(actual, valor){ return String(actual || '') === valor ? 'selected' : ''; }
  function opciones(lista, actual){
    return ['<option value="">Seleccione...</option>'].concat(
      lista.map(v => `<option value="${esc(v)}" ${seleccionado(actual,v)}>${esc(v)}</option>`)
    ).join('');
  }
  function opcionesEstandar(actual){
    return '<option value="">Seleccione un estándar...</option>' + Object.entries(ETIQUETAS)
      .map(([k,v]) => `<option value="${k}" ${seleccionado(actual,k)}>${esc(v)}</option>`).join('');
  }
  function buscarCatalogo(estandar, codigo){
    return (CATALOGOS[estandar] || []).find(x => String(x.codigo) === String(codigo)) || null;
  }
  function opcionesCatalogo(estandar, actual){
    return '<option value="">Seleccione un control...</option>' + (CATALOGOS[estandar] || []).map(item => {
      const label = `${item.codigo} - ${item.nombre}`;
      return `<option value="${esc(item.codigo)}" ${seleccionado(actual,item.codigo)}>${esc(label)}</option>`;
    }).join('');
  }
  function valorPct(raw){
    let n = parseFloat(String(raw || '0').replace('%','').replace(',','.'));
    if (isNaN(n)) return 0;
    if (!String(raw).includes('%') && n <= 1) n *= 100;
    return Math.max(0, Math.min(100, n));
  }

  function iniciar(){
    const container = document.getElementById('risk-controls-container');
    if (!container || container.dataset.ready === '1') return;
    container.dataset.ready = '1';

    function renumerar(){
      [...container.querySelectorAll('.risk-control-card')].forEach((card, i) => {
        const titulo = card.querySelector('.risk-control-card-title');
        const badge = card.querySelector('.risk-control-card-badge');
        if (titulo) titulo.textContent = `Control ${i + 1}`;
        if (badge) badge.textContent = `Evaluación individual ${i + 1}`;
      });
    }

    function actualizarGrupo(){
      const solidos = [...container.querySelectorAll('.risk-control-card')].filter(card => {
        const estandar = card.querySelector('[name="control_estandar[]"]')?.value || '';
        const codigo = card.querySelector('[name="control_catalogo_codigo[]"]')?.value || '';
        const otro = card.querySelector('[name="control_otro_nombre[]"]')?.value.trim() || '';
        return estandar && (estandar === 'OTROS' ? otro : codigo);
      }).map(card => valorPct(card.querySelector('[name="control_solidez_visual[]"]')?.value || '0'));

      const promedio = solidos.length ? solidos.reduce((a,b) => a + b, 0) / solidos.length : 0;
      const campoGrupo = document.getElementById('solidez_grupal');
      const campoValor = document.getElementById('valor');
      if (campoGrupo) {
        campoGrupo.value = promedio.toFixed(2) + '%';
        campoGrupo.dispatchEvent(new Event('input', {bubbles:true}));
      }
      if (campoValor) campoValor.value = promedio.toFixed(2) + '%';
      if (typeof window.riesgoActualizarResidualGrupal === 'function') window.riesgoActualizarResidualGrupal();
    }

    function calcularTarjeta(card){
      const get = nombre => card.querySelector(`[name="${nombre}"]`)?.value || '';
      const mapas = PARAMETROS_CONTROL;
      const valoresDiseno = [
        get('control_asignacion[]'),
        get('control_tipo[]'),
        get('control_forma[]'),
        get('control_funcionalidad[]'),
        get('control_estado[]'),
        get('control_evidencia[]')
      ];
      const evaluacionDisenoCompleta = valoresDiseno.every(v => String(v || '').trim() !== '');
      const ejecucionTexto = get('control_ejecucion[]');
      const ejecucion = mapas.ejecucion[ejecucionTexto];

      const disenoCalculado =
        (mapas.asignacion[get('control_asignacion[]')] || 0) +
        (mapas.tipo[get('control_tipo[]')] || 0) +
        (mapas.forma[get('control_forma[]')] || 0) +
        (mapas.funcionalidad[get('control_funcionalidad[]')] || 0) +
        (mapas.estado[get('control_estado[]')] || 0) +
        (mapas.evidencia[get('control_evidencia[]')] || 0);

      // Los riesgos generados desde Superficie de Ataque pueden traer una
      // efectividad histórica y valores de ejecución como Fuerte/Débil. Al
      // editar no se debe convertir esa solidez a 0 % antes de diligenciar
      // completamente la nueva evaluación por control.
      const disenoExistente = valorPct(card.querySelector('.risk-control-existing-design')?.value || '0') / 100;
      const solidezExistente = valorPct(card.querySelector('.risk-control-existing-solidity')?.value || '0') / 100;
      const puedeRecalcular = evaluacionDisenoCompleta && ejecucion !== undefined;
      const diseno = puedeRecalcular ? disenoCalculado : disenoExistente;
      const solidez = puedeRecalcular
        ? ((disenoCalculado * PARAMETROS_CONTROL.peso_diseno) + (ejecucion * PARAMETROS_CONTROL.peso_ejecucion))
        : solidezExistente;

      const campoDiseno = card.querySelector('[name="control_diseno_visual[]"]');
      const campoSolidez = card.querySelector('[name="control_solidez_visual[]"]');
      if (campoDiseno) campoDiseno.value = (diseno * 100).toFixed(2) + '%';
      if (campoSolidez) campoSolidez.value = (solidez * 100).toFixed(2) + '%';
      actualizarGrupo();
    }

    function crearTarjeta(data){
      data = data || {};
      const card = document.createElement('div');
      card.className = 'risk-control-card';
      card.innerHTML = `
        <div class="risk-control-card-header">
          <div><span class="risk-control-card-title">Control</span> <span class="risk-control-card-badge">Evaluación individual</span></div>
          <button type="button" class="risk-control-remove">🗑️ Eliminar control</button>
        </div>
        <div class="row g-3">
          <div class="col-md-4">
            <label class="form-label">Estándar</label>
            <select class="form-select risk-standard" name="control_estandar[]" required>${opcionesEstandar(data.estandar)}</select>
          </div>
          <div class="col-md-8 risk-catalog-group">
            <label class="form-label">Control del estándar</label>
            <select class="form-select risk-catalog" name="control_catalogo_codigo[]"></select>
          </div>
          <div class="col-md-4 risk-other-name-group risk-control-hidden">
            <label class="form-label">Nombre del control</label>
            <input class="form-control risk-other-name" name="control_otro_nombre[]" value="${esc(data.nombre_control || '')}" placeholder="Digite el nombre del control">
          </div>
          <div class="col-12">
            <label class="form-label">Descripción del control</label>
            <textarea class="form-control risk-control-description" name="control_otro_descripcion[]" rows="3">${esc(data.descripcion_control || '')}</textarea>
          </div>

          <div class="col-12"><div class="fw-bold text-primary small mt-1">🧩 Evaluación y Eficacia del Control</div></div>
          <div class="col-md-3"><label class="form-label">Asignación</label><select class="form-select risk-eval" name="control_asignacion[]" required>${opciones(['Asignado','No Asignado'],data.asignacion)}</select></div>
          <div class="col-md-3"><label class="form-label">Cargo</label><input class="form-control risk-eval" name="control_cargo[]" value="${esc(data.cargo || '')}"></div>
          <div class="col-md-3"><label class="form-label">Tipo de Control</label><select class="form-select risk-eval" name="control_tipo[]" required>${opciones(['Detectivo','Preventivo','Correctivo'],data.tipo_control)}</select></div>
          <div class="col-md-3"><label class="form-label">Forma de Control</label><select class="form-select risk-eval" name="control_forma[]" required>${opciones(['Automático','Semiautomático','Manual'],data.forma_control)}</select></div>
          <div class="col-md-3"><label class="form-label">Frecuencia</label><input class="form-control risk-eval" name="control_frecuencia[]" value="${esc(data.frecuencia || '')}"></div>
          <div class="col-md-3"><label class="form-label">Funcionalidad</label><select class="form-select risk-eval" name="control_funcionalidad[]" required>${opciones(['Adecuada','No Adecuada'],data.funcionalidad)}</select></div>
          <div class="col-md-3"><label class="form-label">Estado del Control</label><select class="form-select risk-eval" name="control_estado[]" required>${opciones(['Implementado y Documentado','Implementado y No Documentado','No Documentado'],data.estado_control)}</select></div>
          <div class="col-md-3"><label class="form-label">Evidencia que Compone el Control</label><select class="form-select risk-eval" name="control_evidencia[]" required>${opciones(['Con Evidencia','Sin Evidencia'],data.evidencia_control)}</select></div>
          <div class="col-md-3"><label class="form-label">Referencia Documental</label><input class="form-control risk-eval" name="control_referencia[]" value="${esc(data.referencia_documental || '')}"></div>
          <div class="col-md-3"><label class="form-label">Soporte de Evidencia</label><input class="form-control risk-eval" name="control_soporte[]" value="${esc(data.soporte_evidencia || '')}"></div>
          <div class="col-md-2"><label class="form-label">Diseño (Automático)</label><input class="form-control risk-control-result" name="control_diseno_visual[]" readonly></div>
          <div class="col-md-2"><label class="form-label">Ejecución</label><select class="form-select risk-eval" name="control_ejecucion[]" required>${opciones(['Siempre','Casi Siempre','Nunca'],data.ejecucion_control)}</select></div>
          <div class="col-md-2"><label class="form-label">Solidez Individual</label><input class="form-control risk-control-result" name="control_solidez_visual[]" readonly></div>
          <input type="hidden" class="risk-control-existing-design" name="control_diseno_existente[]" value="${esc(data.diseno_control ?? '')}">
          <input type="hidden" class="risk-control-existing-solidity" name="control_solidez_existente[]" value="${esc(data.solidez_individual ?? '')}">
        </div>`;

      container.appendChild(card);
      const estandar = card.querySelector('.risk-standard');
      const catalogo = card.querySelector('.risk-catalog');
      const catalogGroup = card.querySelector('.risk-catalog-group');
      const otherGroup = card.querySelector('.risk-other-name-group');
      const otherName = card.querySelector('.risk-other-name');
      const descripcion = card.querySelector('.risk-control-description');

      function configurarEstandar(codigoInicial){
        const valor = estandar.value;
        const esOtro = valor === 'OTROS';
        catalogGroup.classList.toggle('risk-control-hidden', esOtro);
        otherGroup.classList.toggle('risk-control-hidden', !esOtro);
        catalogo.required = !esOtro && !!valor;
        otherName.required = esOtro;
        descripcion.readOnly = !esOtro;
        if (esOtro) {
          catalogo.innerHTML = '<option value="">No aplica</option>';
        } else {
          catalogo.innerHTML = opcionesCatalogo(valor, codigoInicial || '');
          const item = buscarCatalogo(valor, catalogo.value);
          descripcion.value = item ? item.descripcion : '';
        }
        calcularTarjeta(card);
      }

      estandar.addEventListener('change', () => configurarEstandar(''));
      catalogo.addEventListener('change', () => {
        const item = buscarCatalogo(estandar.value, catalogo.value);
        descripcion.value = item ? item.descripcion : '';
        calcularTarjeta(card);
      });
      card.querySelectorAll('.risk-eval,.risk-other-name,.risk-control-description').forEach(campo => {
        campo.addEventListener('change', () => calcularTarjeta(card));
        campo.addEventListener('input', () => calcularTarjeta(card));
      });
      card.querySelector('.risk-control-remove').addEventListener('click', () => {
        card.remove();
        if (!container.querySelector('.risk-control-card')) crearTarjeta({});
        renumerar();
        actualizarGrupo();
      });

      configurarEstandar(data.codigo_control || '');
      renumerar();
      calcularTarjeta(card);
    }

    function normalizarReglas(reglas){
      return (reglas || []).map((r,index) => {
        let a = parseFloat(String(r.min ?? '').replace(',','.'));
        let b = parseFloat(String(r.max ?? '').replace(',','.'));
        if (isNaN(a) || isNaN(b)) return null;
        if (Math.max(Math.abs(a),Math.abs(b)) <= 1){ a*=100; b*=100; }
        return {
          min:Math.max(0,Math.min(100,Math.min(a,b))),
          max:Math.max(0,Math.min(100,Math.max(a,b))),
          bajar:Math.max(0,Math.min(4,parseInt(r.bajar,10)||0)),
          index
        };
      }).filter(Boolean).sort((a,b)=>(b.min-a.min)||((a.max-a.min)-(b.max-b.min))||(a.index-b.index));
    }

    function resolverRegla(reglas,pct){
      const lista=normalizarReglas(reglas);
      if(!lista.length) return {regla:null,modo:'sin_reglas'};

      const exacta=lista.find(x=>x.min<=pct&&pct<=x.max);
      if(exacta) return {regla:exacta,modo:'exacta'};

      const superior=[...lista].sort((a,b)=>(b.max-a.max)||(b.min-a.min))[0];
      const inferior=[...lista].sort((a,b)=>(a.min-b.min)||(a.max-b.max))[0];
      if(pct>superior.max) return {regla:superior,modo:'superior'};
      if(pct<inferior.min) return {regla:inferior,modo:'inferior'};

      const distancia=r=>pct<r.min?r.min-pct:(pct>r.max?pct-r.max:0);
      const cercana=[...lista].sort((a,b)=>
        (distancia(a)-distancia(b)) || (b.min-a.min) || (b.max-a.max)
      )[0];
      return {regla:cercana,modo:'cercana'};
    }

    function bajar(reglas,pct){
      const res=resolverRegla(reglas,pct);
      return res.regla?res.regla.bajar:0;
    }

    function textoRegla(reglas,pct,tipo){
      const res=resolverRegla(reglas,pct);
      if(!res.regla) return `${tipo}: no hay bandas configuradas`;
      const r=res.regla;
      const nota=res.modo==='exacta'?'':` · ajuste ${res.modo}`;
      return `${tipo}: ${r.min.toFixed(2)}%–${r.max.toFixed(2)}% · baja ${r.bajar} nivel(es)${nota}`;
    }
    function nivel(score){ if(score<=4)return'Bajo';if(score<=8)return'Medio';if(score<=12)return'Alto';if(score<=20)return'Muy Alto';return'Extremo'; }
    const MAPA_PROB={'Rara vez o Muy baja':1,'Eventualmente o baja':2,'Puede ocurrir o Moderada':3,'Probable o Alta':4,'Muy frecuente o Muy Alta':5};
    const MAPA_PROB_LABEL={1:'Rara vez o Muy baja',2:'Eventualmente o baja',3:'Puede ocurrir o Moderada',4:'Probable o Alta',5:'Muy frecuente o Muy Alta'};
    const MAPA_IMP={'Insignificante o Inferior':1,'Menor':2,'Moderado o Importante':3,'Mayor':4,'Catastrófico o Crítico':5};
    const MAPA_IMP_LABEL={1:'Insignificante o Inferior',2:'Menor',3:'Moderado o Importante',4:'Mayor',5:'Catastrófico o Crítico'};

    function actualizarInherente(){
      const p=MAPA_PROB[document.getElementById('prob_inh')?.value||'']||0;
      const i=MAPA_IMP[document.getElementById('imp_inh')?.value||'']||0;
      const campo=document.getElementById('riesgo_inherente');
      if(campo) campo.value=(p&&i)?`${p*i} (${nivel(p*i)})`:'';
    }
    function actualizarResidual(){
      actualizarInherente();
      const p=MAPA_PROB[document.getElementById('prob_inh')?.value||'']||1;
      const i=MAPA_IMP[document.getElementById('imp_inh')?.value||'']||1;
      const pct=valorPct(document.getElementById('solidez_grupal')?.value||'0');
      const bajaProb=bajar(REGLAS_PROB,pct);
      const bajaImp=bajar(REGLAS_IMP,pct);
      const pr=Math.max(1,p-bajaProb);
      const ir=Math.max(1,i-bajaImp);
      const cp=document.getElementById('cuadrante_prob');
      const ci=document.getElementById('cuadrante_imp');
      const rr=document.getElementById('riesgo_residual');
      const detalle=document.getElementById('detalle_regla_residual');
      if(cp) cp.value=MAPA_PROB_LABEL[pr];
      if(ci) ci.value=MAPA_IMP_LABEL[ir];
      if(rr) rr.value=`${pr*ir} (${nivel(pr*ir)})`;
      if(detalle){
        detalle.textContent=
          textoRegla(REGLAS_PROB,pct,'Probabilidad')+' | '+
          textoRegla(REGLAS_IMP,pct,'Impacto');
      }
    }
    window.riesgoActualizarResidualGrupal=actualizarResidual;
    window.actualizarRiesgoResidualDesdeParametros=actualizarResidual;
    window.calcularRiesgoInherente=actualizarInherente;
    window.calcularRiesgoResidual=actualizarResidual;
    window.riesgoAgregarControl=() => crearTarjeta({});

    (INICIALES.length ? INICIALES : [{}]).forEach(crearTarjeta);
    ['prob_inh','imp_inh'].forEach(id => document.getElementById(id)?.addEventListener('change',actualizarResidual));
    actualizarGrupo();
    actualizarResidual();
  }

  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', iniciar);
  else iniciar();
})();
</script>
'''
    return (plantilla
        .replace("%SECTION_CLASS%", section_class)
        .replace("%CATALOGOS%", catalogos_json)
        .replace("%INICIALES%", iniciales_json)
        .replace("%REGLAS_PROB%", reglas_prob_json)
        .replace("%REGLAS_IMP%", reglas_imp_json)
        .replace("%PARAMETROS_CONTROL%", parametros_control_json))


def riesgo_controles_detalle_html(riesgo):
    controles = riesgo_controles_para_formulario(riesgo)
    if not controles:
        return '<div class="col-12"><div class="alert alert-secondary mb-0">No hay controles registrados para este riesgo.</div></div>'
    bloques = []
    for i, c in enumerate(controles, start=1):
        codigo = c.get("codigo_control") or c.get("nombre_control") or "—"
        estandar = RISK_CONTROL_STANDARD_LABELS.get(c.get("estandar"), c.get("estandar") or "Otros")
        bloques.append(f'''
        <div class="col-12">
          <div class="border rounded-4 p-3 bg-light mb-2">
            <div class="d-flex justify-content-between gap-2 flex-wrap mb-2">
              <strong class="text-primary">Control {i}: {escape(estandar)} — {escape(codigo)}</strong>
              <span class="badge bg-primary">Solidez individual: {riesgo_formatear_porcentaje(c.get('solidez_individual'))}</span>
            </div>
            <div class="small mb-2"><b>Nombre:</b> {escape(c.get('nombre_control') or '—')}</div>
            <div class="small text-muted mb-3" style="white-space:pre-wrap">{escape(c.get('descripcion_control') or '—')}</div>
            <div class="row g-2 small">
              <div class="col-md-3"><b>Asignación:</b> {escape(c.get('asignacion') or '—')}</div>
              <div class="col-md-3"><b>Cargo:</b> {escape(c.get('cargo') or '—')}</div>
              <div class="col-md-3"><b>Tipo:</b> {escape(c.get('tipo_control') or '—')}</div>
              <div class="col-md-3"><b>Forma:</b> {escape(c.get('forma_control') or '—')}</div>
              <div class="col-md-3"><b>Frecuencia:</b> {escape(c.get('frecuencia') or '—')}</div>
              <div class="col-md-3"><b>Funcionalidad:</b> {escape(c.get('funcionalidad') or '—')}</div>
              <div class="col-md-3"><b>Estado:</b> {escape(c.get('estado_control') or '—')}</div>
              <div class="col-md-3"><b>Evidencia:</b> {escape(c.get('evidencia_control') or '—')}</div>
              <div class="col-md-4"><b>Referencia:</b> {escape(c.get('referencia_documental') or '—')}</div>
              <div class="col-md-4"><b>Soporte:</b> {escape(c.get('soporte_evidencia') or '—')}</div>
              <div class="col-md-2"><b>Diseño:</b> {riesgo_formatear_porcentaje(c.get('diseno_control'))}</div>
              <div class="col-md-2"><b>Ejecución:</b> {escape(c.get('ejecucion_control') or '—')}</div>
            </div>
          </div>
        </div>''')
    return "".join(bloques)


def riesgo_describir_regla(regla):
    if not regla:
        return "sin banda configurada"
    return (
        f"{float(regla.get('rmin', 0.0)):.2f}%-{float(regla.get('rmax', 0.0)):.2f}%"
        f" · {regla.get('modo', 'exacta')}"
    )


def riesgo_calcular_resultados(prob_inh, imp_inh, solidez_grupal, reglas_prob=None, reglas_imp=None):
    prob_inh_num = riesgo_nivel_numero(prob_inh, "probabilidad", 1)
    imp_inh_num = riesgo_nivel_numero(imp_inh, "impacto", 1)

    if reglas_prob is None:
        reglas_prob = ConfigProbResidual.query.all()
    if reglas_imp is None:
        reglas_imp = ConfigImpactoResidual.query.all()

    bajar_prob, regla_prob, solidez_pct = riesgo_reduccion_por_solidez(solidez_grupal, reglas_prob)
    bajar_imp, regla_imp, _ = riesgo_reduccion_por_solidez(solidez_grupal, reglas_imp)

    prob_res_num = max(1, min(5, prob_inh_num - int(bajar_prob)))
    imp_res_num = max(1, min(5, imp_inh_num - int(bajar_imp)))

    inherente_score = prob_inh_num * imp_inh_num
    residual_score = prob_res_num * imp_res_num

    return {
        "solidez_pct": round(solidez_pct, 2),
        "prob_inh_num": prob_inh_num,
        "imp_inh_num": imp_inh_num,
        "prob_res_num": prob_res_num,
        "imp_res_num": imp_res_num,
        "prob_res_label": RISK_PROB_NUM_TO_LABEL[prob_res_num],
        "imp_res_label": RISK_IMPACT_NUM_TO_LABEL[imp_res_num],
        "bajar_prob": bajar_prob,
        "bajar_imp": bajar_imp,
        "regla_prob": regla_prob,
        "regla_imp": regla_imp,
        "inherente_score": inherente_score,
        "inherente_nivel": riesgo_clasificar_puntaje(inherente_score),
        "residual_score": residual_score,
        "residual_nivel": riesgo_clasificar_puntaje(residual_score),
        "riesgo_inherente": f"{inherente_score} ({riesgo_clasificar_puntaje(inherente_score)})",
        "riesgo_residual": f"{residual_score} ({riesgo_clasificar_puntaje(residual_score)})",
    }


def riesgo_actualizar_calculo_objeto(riesgo, reglas_prob=None, reglas_imp=None, configuracion_control=None):
    """Recalcula controles individuales, promedio grupal y riesgo residual."""
    configuracion_control = configuracion_control or riesgo_obtener_config_evaluacion_control()
    campos_control = [
        "diseno_control", "calificacion_asignacion", "calificacion_tipo_control",
        "calificacion_forma_control", "calificacion_funcionalidad",
        "calificacion_estado_control", "calificacion_soporte_evidencia",
        "valor_ejecucion_control", "solidez_individual", "solidez_grupal",
        "prob_inh", "imp_inh", "riesgo_inherente", "cuadrante_prob", "prob_res",
        "cuadrante_imp", "impacto_res", "impacto_res_label", "riesgo_residual",
        "probabilidad", "impacto",
    ]
    antes = tuple(getattr(riesgo, campo, None) for campo in campos_control)

    filas = list(getattr(riesgo, "controles_detalle", []) or [])
    if filas:
        controles = []
        for fila in filas:
            calculo = riesgo_calcular_solidez_control(
                asignacion=fila.asignacion,
                tipo_control=fila.tipo_control,
                forma_control=fila.forma_control,
                funcionalidad=fila.funcionalidad,
                estado_control=fila.estado_control,
                evidencia_control=fila.evidencia_control,
                ejecucion_control=fila.ejecucion_control,
                diseno_control=fila.diseno_control,
                solidez_existente=fila.solidez_individual,
                configuracion_control=configuracion_control,
            )
            fila.diseno_control = calculo["diseno"] or 0.0
            fila.valor_ejecucion_control = calculo["ejecucion"] or 0.0
            fila.solidez_individual = calculo["solidez"]
            controles.append({
                **riesgo_control_para_dict(fila),
                "componentes": calculo["componentes"],
                "diseno_control": fila.diseno_control,
                "valor_ejecucion_control": fila.valor_ejecucion_control,
                "solidez_individual": fila.solidez_individual,
            })
        solidez_efectiva = riesgo_sincronizar_campos_legacy(riesgo, controles)
    else:
        evidencia = getattr(riesgo, "evidencia_control", None)
        if not evidencia and riesgo_normalizar_opcion(getattr(riesgo, "soporte_evidencia", None)) in configuracion_control["diseno"]["evidencia_control"]:
            evidencia = getattr(riesgo, "soporte_evidencia", None)
        control = riesgo_calcular_solidez_control(
            asignacion=getattr(riesgo, "asignacion", None),
            tipo_control=getattr(riesgo, "tipo_control", None),
            forma_control=getattr(riesgo, "forma_control", None),
            funcionalidad=getattr(riesgo, "funcionalidad", None),
            estado_control=getattr(riesgo, "estado_control", None),
            evidencia_control=evidencia,
            ejecucion_control=getattr(riesgo, "ejecucion_control", None),
            diseno_control=getattr(riesgo, "diseno_control", None),
            solidez_existente=getattr(riesgo, "solidez_individual", None),
            configuracion_control=configuracion_control,
        )
        componentes = control["componentes"]
        if control["diseno"] is not None and control["calculada"]:
            riesgo.diseno_control = riesgo_formatear_porcentaje(control["diseno"])
            riesgo.calificacion_asignacion = componentes["asignacion"]
            riesgo.calificacion_tipo_control = componentes["tipo_control"]
            riesgo.calificacion_forma_control = componentes["forma_control"]
            riesgo.calificacion_funcionalidad = componentes["funcionalidad"]
            riesgo.calificacion_estado_control = componentes["estado_control"]
            riesgo.calificacion_soporte_evidencia = componentes["evidencia_control"]
            riesgo.valor_ejecucion_control = control["ejecucion"]
        riesgo.solidez_individual = control["solidez"]
        riesgo.solidez_grupal = control["solidez"]
        riesgo.valor = control["solidez"]
        solidez_efectiva = riesgo.solidez_grupal

    prob_base = getattr(riesgo, "prob_inh", None) or getattr(riesgo, "probabilidad", None)
    imp_base = getattr(riesgo, "imp_inh", None) or getattr(riesgo, "impacto", None)
    if not prob_base or not imp_base:
        return False

    resultado = riesgo_calcular_resultados(
        prob_base,
        imp_base,
        solidez_efectiva,
        reglas_prob=reglas_prob,
        reglas_imp=reglas_imp,
    )
    riesgo.probabilidad = resultado["prob_inh_num"]
    riesgo.impacto = resultado["imp_inh_num"]
    riesgo.prob_inh = RISK_PROB_NUM_TO_LABEL[resultado["prob_inh_num"]]
    riesgo.imp_inh = RISK_IMPACT_NUM_TO_LABEL[resultado["imp_inh_num"]]
    riesgo.riesgo_inherente = resultado["riesgo_inherente"]
    riesgo.cuadrante_prob = resultado["prob_res_label"]
    riesgo.prob_res = resultado["prob_res_label"]
    riesgo.cuadrante_imp = resultado["imp_res_label"]
    riesgo.impacto_res = resultado["imp_res_num"]
    riesgo.impacto_res_label = resultado["imp_res_label"]
    riesgo.riesgo_residual = resultado["riesgo_residual"]

    despues = tuple(getattr(riesgo, campo, None) for campo in campos_control)
    return antes != despues


def riesgo_recalcular_matriz_existente(commit=True):
    reglas_prob = ConfigProbResidual.query.all()
    reglas_imp = ConfigImpactoResidual.query.all()
    configuracion_control = riesgo_obtener_config_evaluacion_control()
    actualizados = 0
    for riesgo in Riesgo.query.all():
        try:
            if riesgo_actualizar_calculo_objeto(
                riesgo,
                reglas_prob,
                reglas_imp,
                configuracion_control=configuracion_control,
            ):
                actualizados += 1
        except Exception as exc:
            print(f"[WARN] No se pudo recalcular el riesgo {getattr(riesgo, 'id', '?')}: {exc!r}")
    if commit and actualizados:
        db.session.commit()
    return actualizados


def riesgo_get(obj, key, default="—"):
    """
    Obtiene el valor de un riesgo con aliases para soportar distintos nombres
    de campos del modelo sin romper la vista.
    """
    aliases = {
        "codigo_riesgo": ["codigo_riesgo"],
        "riesgo": ["riesgo", "riesgo_texto"],
        "tipo_riesgo": ["tipo_riesgo", "clase_riesgo", "categoria_riesgo", "dimension_seguridad"],
        "prob_inh": ["prob_inh", "probabilidad_inherente", "probabilidad"],
        "imp_inh": ["imp_inh", "impacto_inherente", "impacto"],
        "riesgo_inherente": ["riesgo_inherente"],
        "prob_res": ["prob_res", "probabilidad_residual"],
        "imp_res": ["imp_res", "impacto_residual"],
        "riesgo_residual": ["riesgo_residual"],
        "estado": ["estado", "estatus_riesgo", "estado_riesgo"],
    }

    for attr in aliases.get(key, [key]):
        if hasattr(obj, attr):
            value = getattr(obj, attr)
            if value is not None and str(value).strip() != "":
                return value
    return default

# =========================
# ENTRADA DIRECTA A GESTIÓN DE RIESGOS
# =========================
@app.route('/riesgos_menu')
@login_required
def riesgos_menu():
    user = User.query.get(session.get('user_id'))

    if user.role not in ('admin', 'auditor') and not verificar_permiso(user, "Gestión de Riesgos"):
        flash("No tiene permiso para acceder al módulo de gestión de riesgos.", "danger")
        return redirect(url_for('menu'))

    return redirect(url_for('gestion_riesgos', ver='activos'))

# ===========================
# GESTIÓN DE RIESGOS
# ===========================
@app.route('/riesgos', methods=['GET', 'POST'])
@login_required
def gestion_riesgos():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        solo_lectura = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Gestión de Riesgos"):
            flash("No tiene permiso para ver la Gestión de Riesgos.", "danger")
            return redirect(url_for('menu'))
        solo_lectura = False

    # Mantiene la matriz sincronizada con la configuración residual vigente.
    if request.method == 'GET':
        try:
            riesgo_recalcular_matriz_existente(commit=True)
        except Exception as exc:
            db.session.rollback()
            print("[WARN] No se pudo sincronizar la matriz residual:", repr(exc))

    # =========================
    # POST
    # =========================
    if request.method == 'POST' and not solo_lectura:
        codigo_riesgo = request.form.get('codigo_riesgo')
        riesgo_texto = request.form.get('riesgo')
        activo = request.form.get('activo')
        codigo_amenaza = request.form.get('codigo_amenaza')
        amenaza = request.form.get('amenaza')
        codigo_vulnerabilidad = request.form.get('codigo_vulnerabilidad')
        vulnerabilidad = request.form.get('vulnerabilidad')
        dimension_seguridad = request.form.get('dimension_seguridad')

        prob_inh = request.form.get('prob_inh')
        imp_inh = request.form.get('imp_inh')
        valor_riesgo, nivel_riesgo = calcular_riesgo(prob_inh, imp_inh)
        riesgo_inherente = f"{valor_riesgo} ({nivel_riesgo})"

        probabilidad_residual = int(request.form.get('prob_r', 0))
        impacto_residual = int(request.form.get('imp_r', 0))
        riesgo_residual = probabilidad_residual * impacto_residual
        controles_existentes = request.form.get('controles_existentes')
        plan_accion = request.form.get('plan_accion')
        responsable = request.form.get('responsable')
        fecha_compromiso = request.form.get('fecha_compromiso')
        estado = request.form.get('estado')
        prob_inh = request.form['prob_inh']
        imp_inh = request.form['imp_inh']
        prob_res = request.form['prob_res']
        imp_res = request.form['imp_res']

        valor_inh, nivel_inh = calcular_riesgo(prob_inh, imp_inh)
        valor_res, nivel_res = calcular_riesgo(prob_res, imp_res)

        riesgo_inherente = nivel_inh
        riesgo_residual = nivel_res
        valor = valor_inh

        nuevo = Riesgo(
            codigo_riesgo=codigo_riesgo,
            riesgo=riesgo_texto,
            fecha_identificacion=fecha_identificacion,
            propietario_riesgo=propietario_riesgo,
            codigo_amenaza=codigo_amenaza,
            amenaza=amenaza,
            codigo_vulnerabilidad=codigo_vulnerabilidad,
            vulnerabilidad=vulnerabilidad,
            tipo_activo=tipo_activo,
            nombre_activo=nombre_activo,
            dimension_seguridad=dimension_seguridad,
            probabilidad=probabilidad,
            impacto=impacto,
            riesgo_inherente=riesgo_inherente,
            control_codigo=control_codigo,
            codigo_anexo=(request.form.get('codigo_anexo') or request.form.get('cod_anexo')),
            codigo_control_pci_dss=request.form.get('codigo_control_pci_dss'),
            codigo_control_nist_csf=request.form.get('codigo_control_nist_csf'),
            codigo_control_soc2=request.form.get('codigo_control_soc2'),
            descripcion_control=construir_descripcion_controles_multimarco(
                codigo_iso=(request.form.get('codigo_anexo') or request.form.get('cod_anexo')),
                codigo_pci=request.form.get('codigo_control_pci_dss'),
                codigo_nist=request.form.get('codigo_control_nist_csf'),
                codigo_soc2=request.form.get('codigo_control_soc2')
            ),
            plan_accion=plan_accion,
            asignacion=asignacion,
            cargo=cargo,
            tipo_control=tipo_control,
            forma_control=forma_control,
            frecuencia=frecuencia,
            funcionalidad=funcionalidad,
            estado_control=estado_control,
            referencia_documental=referencia_documental,
            evidencia_control=evidencia_control,
            soporte_evidencia=soporte_evidencia,
            diseno_control=diseno_control,
            ejecucion_control=ejecucion_control,
            valor=solidez_individual_calculada,
            solidez_individual=solidez_individual,
            solidez_grupal=solidez_grupal,
            cuadrante_prob=cuadrante_prob,
            cuadrante_imp=cuadrante_imp,
            riesgo_residual=riesgo_residual,
            fecha_revision=fecha_revision,
            tratamiento_riesgo=tratamiento_riesgo,
            observaciones=observaciones,
            planes_accion=planes_accion,
            responsable=responsable,
            fecha_implementacion=fecha_implementacion
        )
        db.session.add(nuevo)
        db.session.commit()
        flash("✅ Riesgo registrado correctamente", "success")
        return redirect(url_for('gestion_riesgos'))

    # =========================
    # FILTRO DE VISTA
    # =========================
    ver = request.args.get('ver', 'activos')  # activos | archivados | todos

    filtro_riesgo_inherente = (request.args.get('riesgo_inherente') or '').strip()
    filtro_riesgo_residual = (request.args.get('riesgo_residual') or '').strip()
    filtro_tipo_riesgo = (request.args.get('tipo_riesgo') or '').strip()

    query = Riesgo.query

    if ver == 'archivados':
        query = query.filter(Riesgo.archivado == True)
    elif ver == 'todos':
        query = query.order_by(Riesgo.archivado.asc(), Riesgo.id.desc())
    else:
        query = query.filter(Riesgo.archivado == False)

    if filtro_riesgo_inherente:
        query = query.filter(Riesgo.riesgo_inherente == filtro_riesgo_inherente)

    if filtro_riesgo_residual:
        query = query.filter(Riesgo.riesgo_residual == filtro_riesgo_residual)

    if filtro_tipo_riesgo:
        query = query.filter(Riesgo.dimension_seguridad == filtro_tipo_riesgo)

    if ver in ('activos', 'archivados'):
        query = query.order_by(Riesgo.id.desc())

    riesgos = query.all()

    # Relaciona cada riesgo visible con su plan independiente más reciente.
    # Reconoce tanto planes asignados manualmente como planes sincronizados.
    risk_plan_ids = {}
    visible_risk_ids = {riesgo.id for riesgo in riesgos}
    if visible_risk_ids:
        for plan in ContinuousActionPlan.query.order_by(
            ContinuousActionPlan.id.desc()
        ).all():
            risk_id_asociado = None
            source_ref = (plan.source_ref or "").strip()
            match = re.match(
                r"^(?:riesgo-manual|riesgo-existente):(\d+)(?::|$)",
                source_ref,
                flags=re.IGNORECASE,
            )
            if match:
                risk_id_asociado = int(match.group(1))

            if risk_id_asociado is None and plan.raw_json:
                try:
                    raw_data = json.loads(plan.raw_json)
                    if isinstance(raw_data, dict) and raw_data.get("riesgo_id"):
                        risk_id_asociado = int(raw_data["riesgo_id"])
                except (TypeError, ValueError, json.JSONDecodeError):
                    pass

            if (
                risk_id_asociado in visible_risk_ids
                and risk_id_asociado not in risk_plan_ids
            ):
                risk_plan_ids[risk_id_asociado] = plan.id

    total_activos = Riesgo.query.filter_by(archivado=False).count()
    total_archivados = Riesgo.query.filter_by(archivado=True).count()
    total_registros = Riesgo.query.count()
    total_filtrados = len(riesgos)

    opciones_riesgo_inherente = [
        x[0] for x in db.session.query(Riesgo.riesgo_inherente)
        .filter(Riesgo.riesgo_inherente.isnot(None))
        .filter(Riesgo.riesgo_inherente != '')
        .distinct()
        .order_by(Riesgo.riesgo_inherente.asc())
        .all()
    ]

    opciones_riesgo_residual = [
        x[0] for x in db.session.query(Riesgo.riesgo_residual)
        .filter(Riesgo.riesgo_residual.isnot(None))
        .filter(Riesgo.riesgo_residual != '')
        .distinct()
        .order_by(Riesgo.riesgo_residual.asc())
        .all()
    ]

    opciones_tipo_riesgo = [
        x[0] for x in db.session.query(Riesgo.dimension_seguridad)
        .filter(Riesgo.dimension_seguridad.isnot(None))
        .filter(Riesgo.dimension_seguridad != '')
        .distinct()
        .order_by(Riesgo.dimension_seguridad.asc())
        .all()
    ]

    def color_por_valor(valor):
        if valor is None or str(valor).strip() == "":
            return "nivel-none"

        s = str(valor).strip().lower()

        if "extremo" in s:
            return "nivel5"
        if "muy alto" in s or "muyalto" in s:
            return "nivel4"
        if "alto" in s:
            return "nivel3"
        if "medio" in s or "moderado" in s:
            return "nivel2"
        if "bajo" in s:
            return "nivel1"

        try:
            import re
            m = re.search(r"\d+(\.\d+)?", s)
            n = float(m.group(0)) if m else 0
        except Exception:
            n = 0

        if n <= 0:
            return "nivel-none"
        elif n <= 4:
            return "nivel1"
        elif n <= 8:
            return "nivel2"
        elif n <= 12:
            return "nivel3"
        elif n <= 20:
            return "nivel4"
        else:
            return "nivel5"

    riesgos_html = """
    <div class="risk-shell">

      <!-- =========================
           HERO / TÍTULO DEL MÓDULO
      ========================== -->
      <div class="risk-hero-card">

        <div class="risk-hero-left">

          <div class="risk-hero-icon">
            ⚠️
          </div>

          <div class="risk-hero-text">
            <div class="risk-hero-kicker">
              SGSI · Gestión de Riesgos
            </div>

            <h2 class="risk-hero-title">
              Gestión de Riesgos
            </h2>

            <p class="risk-hero-subtitle">
              Identificación, valoración, tratamiento y seguimiento de riesgos de seguridad de la información.
            </p>
          </div>

        </div>

        <div class="risk-hero-badge">
          Risk
        </div>

      </div>

      <!-- =========================
           MENÚ SUPERIOR
      ========================== -->
      <div class="risk-menu-panel">
        <div class="risk-top-menu">

          {% if not solo_lectura %}
            <a href="{{ url_for('agregar_riesgo', ver='activos') }}"
               class="risk-menu-btn"
               onclick="showLoader()">
              ➕ Agregar Riesgo
            </a>
          {% endif %}

          <div class="risk-dropdown">
            {% if solo_lectura %}
              <button type="button" class="risk-menu-btn risk-menu-btn-disabled" disabled>
                ⚙️ Parámetros ▾
              </button>
            {% else %}
              <button type="button" class="risk-menu-btn" onclick="toggleRiskConfigMenu(event)">
                ⚙️ Parámetros ▾
              </button>

              <div class="risk-dropdown-content" id="riskConfigDropdown">
                <a href="{{ url_for('configurar_probabilidad_residual') }}" onclick="showLoader()">
                  📈 Probabilidad Residual
                </a>
                <a href="{{ url_for('configurar_impacto_residual') }}" onclick="showLoader()">
                  📉 Impacto Residual
                </a>
                <a href="{{ url_for('configurar_evaluacion_control') }}" onclick="showLoader()">
                  🧩 Evaluación y Eficacia del Control
                </a>
                <a href="{{ url_for('configurar_tipos_riesgo') }}" onclick="showLoader()">
                  🏷️ Tipos de Riesgo
                </a>
              </div>
            {% endif %}
          </div>

          <a href="{{ url_for('mapa_calor') }}"
             class="risk-menu-btn"
             onclick="showLoader()">
            🌡️ Mapa de Calor
          </a>

        </div>
      </div>

      <!-- =========================
           RESUMEN
      ========================== -->
      <div class="risk-summary-grid">

        <div class="risk-summary-box">
          <div class="risk-summary-label">Total registros</div>
          <div class="risk-summary-value">{{ total_registros }}</div>
        </div>

        <div class="risk-summary-box success">
          <div class="risk-summary-label">Riesgos activos</div>
          <div class="risk-summary-value">{{ total_activos }}</div>
        </div>

        <div class="risk-summary-box muted">
          <div class="risk-summary-label">Archivados</div>
          <div class="risk-summary-value">{{ total_archivados }}</div>
        </div>

        <div class="risk-summary-box info">
          <div class="risk-summary-label">Filtrados</div>
          <div class="risk-summary-value">{{ total_filtrados }}</div>
        </div>

      </div>

      <!-- =========================
           FILTROS
      ========================== -->
      <div class="risk-filter-panel">
        <form method="get" action="{{ url_for('gestion_riesgos') }}" class="risk-filter-form">

          <div class="risk-filter-group">
            <div class="risk-filter-bubble">🔎</div>
            <div class="risk-filter-control">
              <label>Estatus del Riesgo</label>
              <select name="ver" class="form-select">
                <option value="activos" {% if ver == 'activos' %}selected{% endif %}>Activos</option>
                <option value="archivados" {% if ver == 'archivados' %}selected{% endif %}>Archivados</option>
                <option value="todos" {% if ver == 'todos' %}selected{% endif %}>Todos</option>
              </select>
            </div>
          </div>

          <div class="risk-filter-group">
            <div class="risk-filter-bubble">📊</div>
            <div class="risk-filter-control">
              <label>Riesgo Inherente</label>
              <select name="riesgo_inherente" class="form-select">
                <option value="">Todos</option>
                {% for op in opciones_riesgo_inherente %}
                  <option value="{{ op }}" {% if filtro_riesgo_inherente == op %}selected{% endif %}>
                    {{ op }}
                  </option>
                {% endfor %}
              </select>
            </div>
          </div>

          <div class="risk-filter-group">
            <div class="risk-filter-bubble">📉</div>
            <div class="risk-filter-control">
              <label>Riesgo Residual</label>
              <select name="riesgo_residual" class="form-select">
                <option value="">Todos</option>
                {% for op in opciones_riesgo_residual %}
                  <option value="{{ op }}" {% if filtro_riesgo_residual == op %}selected{% endif %}>
                    {{ op }}
                  </option>
                {% endfor %}
              </select>
            </div>
          </div>

          <div class="risk-filter-group">
            <div class="risk-filter-bubble">🏷️</div>
            <div class="risk-filter-control">
              <label>Tipo de Riesgo</label>
              <select name="tipo_riesgo" class="form-select">
                <option value="">Todos</option>
                {% for op in opciones_tipo_riesgo %}
                  <option value="{{ op }}" {% if filtro_tipo_riesgo == op %}selected{% endif %}>
                    {{ op }}
                  </option>
                {% endfor %}
              </select>
            </div>
          </div>

          <div class="risk-filter-actions">
            <button type="submit" class="risk-primary-btn">
              Filtrar
            </button>

            <a href="{{ url_for('gestion_riesgos') }}" class="risk-secondary-btn">
              Limpiar
            </a>
          </div>

        </form>
      </div>

      <!-- =========================
           TABLA
      ========================== -->
      <div class="risk-table-panel">
        <div class="risk-table-scroll">

          <table class="table risk-table align-middle mb-0">
            <thead>
              <tr>
                <th>Cod Riesgo</th>
                <th>Riesgo</th>
                <th>Tipo de Riesgo</th>
                <th>Prob. Inh.</th>
                <th>Impacto Inh.</th>
                <th>Riesgo Inherente</th>
                <th>Prob. Res.</th>
                <th>Impacto Res.</th>
                <th>Riesgo Residual</th>
                <th>Estatus</th>
                <th class="risk-actions-header">Acciones</th>
              </tr>
            </thead>

            <tbody>
              {% for r in riesgos %}
                <tr>
                  <td class="texto-corto">
                    <span class="risk-code-badge">{{ r.codigo_riesgo or '—' }}</span>
                  </td>

                  <td class="texto-largo">{{ r.riesgo or '—' }}</td>

                  <td class="texto-medio">
                    {% if r.tipo_riesgo_rel %}
                      {{ r.tipo_riesgo_rel.nombre }}
                    {% elif r.tipo_riesgo %}
                      {{ r.tipo_riesgo }}
                    {% elif r.dimension_seguridad %}
                      {{ r.dimension_seguridad }}
                    {% else %}
                      —
                    {% endif %}
                  </td>

                  <td class="texto-corto">{{ r.prob_inh or '—' }}</td>
                  <td class="texto-corto">{{ r.imp_inh or '—' }}</td>

                  <td class="texto-corto {{ color_por_valor(r.riesgo_inherente) }}">
                    {{ r.riesgo_inherente or '—' }}
                  </td>

                  <td class="texto-corto">{{ r.prob_res or r.cuadrante_prob or '—' }}</td>
                  <td class="texto-corto">{{ r.impacto_res_label or r.cuadrante_imp or '—' }}</td>

                  <td class="texto-corto {{ color_por_valor(r.riesgo_residual) }}">
                    {{ r.riesgo_residual or '—' }}
                  </td>

                  <td class="texto-corto">
                    {% if r.archivado %}
                      <span class="risk-status archived">Archivado</span>
                    {% else %}
                      <span class="risk-status active">Activo</span>
                    {% endif %}
                  </td>

                  <td class="risk-actions-cell">
                    <div class="risk-actions-wrap">

                      <a href="{{ url_for('riesgo_detalle', riesgo_id=r.id) }}"
                         class="risk-action-btn view">
                        Ver
                      </a>

                      {% set associated_plan_id = risk_plan_ids.get(r.id) %}

                      {% if not solo_lectura %}
                        {% if not r.archivado %}

                          <a href="/editar_riesgo/{{ r.id }}"
                             class="risk-action-btn edit">
                            Editar
                          </a>

                          {% if associated_plan_id %}
                            <a href="{{ url_for('planes_accion_dashboard', plan_id=associated_plan_id) }}"
                               class="risk-action-btn plan-action"
                               title="Abrir el plan de acción asignado"
                               aria-label="Ir al plan de acción del riesgo {{ r.codigo_riesgo or r.id }}">
                              <i class="bi bi-box-arrow-up-right" aria-hidden="true"></i>
                              <span>Ir al plan de acción</span>
                            </a>
                          {% else %}
                            <a href="{{ url_for('planes_accion_new', riesgo_id=r.id) }}"
                               class="risk-action-btn plan-action d-inline-flex align-items-center justify-content-center gap-2 text-nowrap"
                               title="Asignar un plan de acción a este riesgo"
                               aria-label="Asignar plan de acción al riesgo {{ r.codigo_riesgo or r.id }}">
                              <i class="bi bi-clipboard2-plus-fill flex-shrink-0" aria-hidden="true"></i>
                              <span>Asignar plan de acción</span>
                            </a>
                          {% endif %}

                          <form action="{{ url_for('archivar_riesgo', riesgo_id=r.id) }}"
                                method="post"
                                onsubmit="return confirm('¿Seguro deseas archivar este riesgo?');"
                                class="m-0 p-0">
                            <button type="submit" class="risk-action-btn archive">
                              Archivar
                            </button>
                          </form>

                          <a href="/eliminar_riesgo/{{ r.id }}"
                             class="risk-action-btn delete"
                             onclick="return confirm('¿Seguro desea eliminar este riesgo?');">
                            Eliminar
                          </a>

                        {% else %}

                          {% if associated_plan_id %}
                            <a href="{{ url_for('planes_accion_dashboard', plan_id=associated_plan_id) }}"
                               class="risk-action-btn plan-action"
                               title="Abrir el plan de acción asignado">
                              <i class="bi bi-box-arrow-up-right" aria-hidden="true"></i>
                              <span>Ir al plan de acción</span>
                            </a>
                          {% endif %}

                          <form action="{{ url_for('restaurar_riesgo', riesgo_id=r.id) }}"
                                method="post"
                                onsubmit="return confirm('¿Restaurar este riesgo a activos?');"
                                class="m-0 p-0">
                            <button type="submit" class="risk-action-btn restore">
                              Activar
                            </button>
                          </form>

                          <a href="/eliminar_riesgo/{{ r.id }}"
                             class="risk-action-btn delete"
                             onclick="return confirm('¿Seguro desea eliminar este riesgo?');">
                            Eliminar
                          </a>

                        {% endif %}
                      {% elif associated_plan_id %}
                        <a href="{{ url_for('planes_accion_dashboard', plan_id=associated_plan_id) }}"
                           class="risk-action-btn plan-action"
                           title="Consultar el plan de acción asignado"
                           aria-label="Ir al plan de acción del riesgo {{ r.codigo_riesgo or r.id }}">
                          <i class="bi bi-box-arrow-up-right" aria-hidden="true"></i>
                          <span>Ir al plan de acción</span>
                        </a>
                      {% endif %}

                    </div>
                  </td>
                </tr>
              {% endfor %}

              {% if riesgos|length == 0 %}
                <tr>
                  <td colspan="11" class="text-center text-muted py-4">
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
      body {
        background-image: url('/static/img/ccsgsi.jpg');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        background-repeat: no-repeat;
      }

      .risk-shell {
        width: 96%;
        max-width: 1650px;
        margin: 26px auto 24px auto;
        position: relative;
        overflow: visible !important;
        z-index: 1;
      }

      /* =========================
         HERO COMPACTO
      ========================== */
      .risk-hero-card {
        background:
          linear-gradient(135deg, rgba(11,58,110,.97), rgba(20,89,166,.95), rgba(44,123,229,.92));
        border-radius: 18px;
        padding: 16px 24px;
        min-height: 94px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 12px 24px rgba(15,23,42,.24);
        color: #ffffff;
        position: relative;
        overflow: hidden;
        margin-bottom: 10px;
        z-index: 1;
      }

      .risk-hero-card::before {
        content: "";
        position: absolute;
        inset: 0;
        background:
          radial-gradient(circle at 92% 12%, rgba(255,255,255,.20), transparent 26%),
          repeating-linear-gradient(
            135deg,
            rgba(255,255,255,.05) 0px,
            rgba(255,255,255,.05) 1px,
            transparent 1px,
            transparent 15px
          );
        pointer-events: none;
      }

      .risk-hero-left {
        display: flex;
        align-items: center;
        gap: 14px;
        position: relative;
        z-index: 1;
      }

      .risk-hero-icon {
        width: 54px;
        height: 54px;
        min-width: 54px;
        border-radius: 14px;
        background: rgba(255,255,255,.96);
        color: #0b4a8f;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.55rem;
        box-shadow: 0 8px 18px rgba(0,0,0,.20);
      }

      .risk-hero-text {
        position: relative;
        z-index: 1;
      }

      .risk-hero-kicker {
        display: inline-block;
        background: rgba(255,255,255,.18);
        border: 1px solid rgba(255,255,255,.30);
        border-radius: 999px;
        padding: 3px 10px;
        font-size: .66rem;
        font-weight: 800;
        letter-spacing: .35px;
        margin-bottom: 4px;
      }

      .risk-hero-title {
        margin: 0;
        font-size: 1.36rem;
        font-weight: 950;
        line-height: 1.08;
        color: #ffffff;
        text-shadow: 0 3px 10px rgba(0,0,0,.32);
      }

      .risk-hero-subtitle {
        margin: 4px 0 0 0;
        font-size: .78rem;
        color: rgba(248,252,255,.96);
        max-width: 820px;
        line-height: 1.25;
      }

      .risk-hero-badge {
        position: relative;
        z-index: 1;
        width: 66px;
        height: 66px;
        border-radius: 18px;
        background: rgba(255,255,255,.95);
        color: #0b4a8f;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.05rem;
        font-weight: 950;
        box-shadow: 0 10px 20px rgba(0,0,0,.22);
        transform: rotate(-4deg);
      }

      /* =========================
         MENÚ COMPACTO CORREGIDO
         NO SE SOBREPONE A NAVBAR
      ========================== */
      .risk-menu-panel {
        background: rgba(255,255,255,.96);
        border-radius: 16px;
        padding: 12px 16px;
        box-shadow: 0 10px 22px rgba(15,23,42,.15);
        backdrop-filter: none !important;
        margin-bottom: 12px;
        position: relative !important;
        z-index: 20 !important;
        overflow: visible !important;
      }

      .risk-top-menu {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 10px;
        flex-wrap: wrap;
        position: relative !important;
        z-index: 21 !important;
        overflow: visible !important;
      }

      .risk-menu-btn {
        min-width: 180px;
        height: 38px;
        border: none;
        border-radius: 10px;
        padding: 0 18px;
        background: linear-gradient(135deg, #086df0, #2487ff);
        color: #ffffff;
        font-weight: 900;
        font-size: .80rem;
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 7px 14px rgba(8,109,240,.22);
        cursor: pointer;
        white-space: nowrap;
      }

      .risk-menu-btn:hover {
        color: #ffffff;
        filter: brightness(.96);
        transform: translateY(-1px);
      }

      .risk-menu-btn-disabled {
        background: #d1d5db !important;
        color: #4b5563 !important;
        cursor: not-allowed;
        box-shadow: none;
      }

      .risk-dropdown {
        position: relative !important;
        z-index: 22 !important;
        overflow: visible !important;
      }

      .risk-dropdown-content {
        display: none;
        position: absolute !important;
        top: calc(100% + 8px);
        left: 50%;
        transform: translateX(-50%);
        min-width: 270px;
        background: rgba(255,255,255,.99);
        border-radius: 14px;
        box-shadow: 0 22px 55px rgba(0,0,0,.30);
        padding: 8px;
        border: 1px solid rgba(219,230,244,.95);
        z-index: 30 !important;
        overflow: visible !important;
      }

      .risk-dropdown-content.show {
        display: block !important;
      }

      .risk-dropdown-content a {
        display: block;
        text-decoration: none;
        color: #101827;
        font-weight: 800;
        font-size: .80rem;
        padding: 9px 12px;
        border-radius: 10px;
        white-space: nowrap;
      }

      .risk-dropdown-content a:hover {
        background: #eef4ff;
        color: #0b65d8;
      }

      /* =========================
         RESUMEN
      ========================== */
      .risk-summary-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
        margin-bottom: 12px;
        position: relative;
        z-index: 1 !important;
      }

      .risk-summary-box {
        background: rgba(255,255,255,.96);
        border-radius: 15px;
        padding: 13px 14px;
        text-align: center;
        box-shadow: 0 10px 22px rgba(15,23,42,.14);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(219,230,244,.9);
      }

      .risk-summary-label {
        font-size: .74rem;
        color: #475569;
        font-weight: 800;
        margin-bottom: 3px;
      }

      .risk-summary-value {
        font-size: 1.25rem;
        font-weight: 950;
        color: #1e3a8a;
        line-height: 1;
      }

      .risk-summary-box.success .risk-summary-value {
        color: #087c3d;
      }

      .risk-summary-box.muted .risk-summary-value {
        color: #475569;
      }

      .risk-summary-box.info .risk-summary-value {
        color: #2563eb;
      }

      /* =========================
         FILTROS
      ========================== */
      .risk-filter-panel {
        background: rgba(255,255,255,.96);
        border-radius: 16px;
        padding: 14px 18px;
        box-shadow: 0 10px 22px rgba(15,23,42,.15);
        backdrop-filter: blur(10px);
        margin-bottom: 14px;
        position: relative;
        z-index: 1 !important;
      }

      .risk-filter-form {
        display: grid;
        grid-template-columns: 1fr 1fr 1fr 1fr .95fr;
        gap: 12px;
        align-items: end;
      }

      .risk-filter-group {
        display: grid;
        grid-template-columns: 40px 1fr;
        gap: 9px;
        align-items: end;
      }

      .risk-filter-bubble {
        width: 38px;
        height: 38px;
        border-radius: 50%;
        background: #eef5ff;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #1d74e8;
        font-size: .95rem;
      }

      .risk-filter-control label {
        font-weight: 800;
        font-size: .74rem;
        color: #25324a;
        margin-bottom: 4px;
      }

      .risk-filter-control .form-select {
        height: 37px;
        border-radius: 9px;
        border: 1px solid #d9e3f0;
        box-shadow: none;
        font-size: .80rem;
        padding-top: 4px;
        padding-bottom: 4px;
      }

      .risk-filter-actions {
        display: flex;
        gap: 9px;
        justify-content: flex-end;
        align-items: center;
        border-left: 1px solid #e5edf7;
        padding-left: 14px;
      }

      .risk-primary-btn,
      .risk-secondary-btn {
        height: 37px;
        border-radius: 10px;
        padding: 0 18px;
        font-weight: 900;
        font-size: .78rem;
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        white-space: nowrap;
      }

      .risk-primary-btn {
        border: none;
        background: linear-gradient(135deg, #086df0, #2487ff);
        color: #ffffff;
        box-shadow: 0 7px 14px rgba(8,109,240,.22);
      }

      .risk-secondary-btn {
        border: 1px solid #1e7cff;
        color: #1e7cff;
        background: #ffffff;
      }

      .risk-secondary-btn:hover {
        background: #edf5ff;
        color: #0b65d8;
      }

      /* =========================
         TABLA
      ========================== */
      .risk-table-panel {
        background: rgba(255,255,255,.96);
        border-radius: 18px;
        padding: 10px;
        box-shadow: 0 12px 24px rgba(15,23,42,.18);
        backdrop-filter: blur(8px);
        position: relative;
        z-index: 1 !important;
      }

      .risk-table-scroll {
        max-height: 68vh;
        overflow-x: auto;
        overflow-y: auto;
        border-radius: 14px;
        border: 1px solid #dbe6f4;
        background: #ffffff;
        position: relative;
        z-index: 1 !important;
      }

      .risk-table {
        min-width: 1750px;
        table-layout: fixed;
        border-collapse: separate;
        border-spacing: 0;
      }

      .risk-table thead th {
        position: sticky;
        top: 0;
        z-index: 2 !important;
        background: linear-gradient(135deg, #1d5fa9, #2f7fd1);
        color: #ffffff;
        font-weight: 900;
        text-align: center;
        vertical-align: middle;
        padding: 11px 8px;
        border-right: 1px solid rgba(255,255,255,.28);
        font-size: .76rem;
      }

      .risk-table tbody td {
        padding: 9px 8px;
        border-right: 1px solid #dce6f3;
        border-bottom: 1px solid #dce6f3;
        vertical-align: middle;
        background: rgba(255,255,255,.98);
        font-size: .76rem;
        color: #0b1220;
        word-break: break-word;
      }

      .risk-table tbody tr:nth-child(even) td {
        background: #f8fbff;
      }

      .risk-table tbody tr:hover td {
        background: #eef6ff;
      }

      .risk-code-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 54px;
        min-height: 28px;
        border-radius: 11px;
        background: #eaf3ff;
        color: #1476ef;
        font-weight: 900;
        font-size: .74rem;
        padding: 3px 8px;
      }

      .texto-largo {
        width: 330px;
        max-width: 330px;
      }

      .texto-medio {
        width: 190px;
        max-width: 190px;
      }

      .texto-corto {
        width: 130px;
        max-width: 130px;
        text-align: center;
      }

      .risk-status {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: 999px;
        padding: 5px 11px;
        font-weight: 900;
        font-size: .72rem;
      }

      .risk-status.active {
        background: #dcfce7;
        color: #166534;
        border: 1px solid #bbf7d0;
      }

      .risk-status.archived {
        background: #f1f5f9;
        color: #475569;
        border: 1px solid #cbd5e1;
      }

      /* Columna compacta con botones organizados verticalmente */
      .risk-table th.risk-actions-header,
      .risk-table td.risk-actions-cell {
        width: 220px;
        min-width: 220px;
        max-width: 220px;
        text-align: center;
      }

      .risk-actions-wrap {
        display: flex;
        flex-direction: column;
        flex-wrap: nowrap;
        gap: 6px;
        align-items: center;
        justify-content: center;
        width: 100%;
      }

      .risk-actions-wrap form {
        display: flex;
        flex: 0 0 auto;
        width: 190px;
        margin: 0;
      }

      .risk-action-btn {
        width: 190px;
        min-width: 190px;
        max-width: 190px;
        height: 28px;
        border: none;
        border-radius: 999px;
        font-size: .70rem;
        font-weight: 900;
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 0 10px;
        color: #ffffff;
        flex: 0 0 auto;
        gap: 6px;
        white-space: nowrap;
        box-sizing: border-box;
      }

      .risk-actions-wrap form .risk-action-btn {
        width: 100%;
      }

      .risk-action-btn.view { background: #087ab8; }
      .risk-action-btn.edit { background: #c76b00; color: #0b1220; }
      .risk-action-btn.plan-action { background: #0f766e; color: #ffffff; }
      .risk-action-btn.archive { background: #2563eb; }
      .risk-action-btn.delete { background: #b91c1c; }
      .risk-action-btn.restore { background: #087c3d; }

      .risk-table-scroll::-webkit-scrollbar {
        height: 11px;
        width: 11px;
      }

      .risk-table-scroll::-webkit-scrollbar-track {
        background: #dbe4f0;
        border-radius: 12px;
      }

      .risk-table-scroll::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, #5aa3ea 0%, #3f86d6 100%);
        border-radius: 12px;
        border: 2px solid #dbe4f0;
      }

      .risk-table-scroll {
        scrollbar-width: thin;
        scrollbar-color: #3f86d6 #dbe4f0;
      }

      /* =========================
           COLORES RIESGOS
           IGUALES AL MAPA DE CALOR
        ========================== */

        .risk-table tbody td.nivel1,
        .risk-table tbody tr:nth-child(even) td.nivel1,
        .risk-table tbody tr:hover td.nivel1 {
          background: #2ecc71 !important;
          color: #ffffff !important;
          font-weight: 900 !important;
        }

        .risk-table tbody td.nivel2,
        .risk-table tbody tr:nth-child(even) td.nivel2,
        .risk-table tbody tr:hover td.nivel2 {
          background: #f1c40f !important;
          color: #111111 !important;
          font-weight: 900 !important;
        }

        .risk-table tbody td.nivel3,
        .risk-table tbody tr:nth-child(even) td.nivel3,
        .risk-table tbody tr:hover td.nivel3 {
          background: #ff69b4 !important;
          color: #111111 !important;
          font-weight: 900 !important;
        }

        .risk-table tbody td.nivel4,
        .risk-table tbody tr:nth-child(even) td.nivel4,
        .risk-table tbody tr:hover td.nivel4 {
          background: #e74c3c !important;
          color: #ffffff !important;
          font-weight: 900 !important;
        }

        .risk-table tbody td.nivel5,
        .risk-table tbody tr:nth-child(even) td.nivel5,
        .risk-table tbody tr:hover td.nivel5 {
          background: #8e44ad !important;
          color: #ffffff !important;
          font-weight: 900 !important;
        }

        .risk-table tbody td.nivel-none,
        .risk-table tbody tr:nth-child(even) td.nivel-none,
        .risk-table tbody tr:hover td.nivel-none {
          background: rgba(255,255,255,.98) !important;
          color: #475569 !important;
          font-weight: 800 !important;
        }

      @media (max-width: 1200px) {
        .risk-hero-badge {
          display: none;
        }

        .risk-summary-grid {
          grid-template-columns: repeat(2, 1fr);
        }

        .risk-filter-form {
          grid-template-columns: 1fr;
        }

        .risk-filter-actions {
          border-left: none;
          padding-left: 0;
          justify-content: stretch;
        }

        .risk-primary-btn,
        .risk-secondary-btn {
          flex: 1;
        }
      }

      @media (max-width: 768px) {
        .risk-shell {
          width: 98%;
        }

        .risk-hero-card {
          padding: 18px;
        }

        .risk-hero-left {
          flex-direction: column;
          text-align: center;
        }

        .risk-hero-title {
          font-size: 1.22rem;
        }

        .risk-hero-subtitle {
          font-size: .74rem;
        }

        .risk-summary-grid {
          grid-template-columns: 1fr;
        }

        .risk-filter-group {
          grid-template-columns: 1fr;
        }

        .risk-filter-bubble {
          display: none;
        }

        .risk-filter-actions {
          flex-direction: column;
        }

        .risk-primary-btn,
        .risk-secondary-btn,
        .risk-menu-btn {
          width: 100%;
        }

        .risk-dropdown {
          width: 100%;
        }

        .risk-dropdown-content {
          left: 0;
          right: 0;
          transform: none;
          min-width: 100%;
        }
      }
    </style>

    <script>
      function toggleRiskConfigMenu(event){
        event.stopPropagation();
        const menu = document.getElementById('riskConfigDropdown');
        if(menu){
          menu.classList.toggle('show');
        }
      }

      document.addEventListener('click', function(e){
        const menu = document.getElementById('riskConfigDropdown');
        if(menu && !e.target.closest('.risk-dropdown')){
          menu.classList.remove('show');
        }
      });
    </script>
    """

    return render_template_string(
        BASE,
        content=Markup(render_template_string(
            riesgos_html,
            riesgos=riesgos,
            risk_plan_ids=risk_plan_ids,
            solo_lectura=solo_lectura,
            ver=ver,
            color_por_valor=color_por_valor,
            total_registros=total_registros,
            total_activos=total_activos,
            total_archivados=total_archivados,
            total_filtrados=total_filtrados,
            opciones_riesgo_inherente=opciones_riesgo_inherente,
            opciones_riesgo_residual=opciones_riesgo_residual,
            opciones_tipo_riesgo=opciones_tipo_riesgo,
            filtro_riesgo_inherente=filtro_riesgo_inherente,
            filtro_riesgo_residual=filtro_riesgo_residual,
            filtro_tipo_riesgo=filtro_tipo_riesgo
        ))
    )

# ===========================
# AGREGAR RIESGO (Versión completa + prellenado desde proveedores)
# ===========================
