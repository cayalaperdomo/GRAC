@app.route('/agregar_riesgo', methods=['GET', 'POST'])
@login_required
def agregar_riesgo():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede agregar registros.", "danger")
        return redirect(url_for('riesgos_menu'))

    if user.role != 'admin' and not verificar_permiso(user, "Gestión de Riesgos"):
        flash("No tiene permiso para agregar riesgos.", "danger")
        return redirect(url_for('riesgos_menu'))

    # =========================================================
    # DATOS DE ORIGEN / PREFILL DESDE PROVEEDORES
    # =========================================================
    origen = (request.args.get('origen') or request.form.get('origen') or '').strip()
    proveedor_id = request.args.get('proveedor_id', type=int) or request.form.get('proveedor_id', type=int)
    proveedor_nombre_qs = (request.args.get('proveedor') or request.form.get('proveedor') or '').strip()
    activo_qs = (request.args.get('activo') or request.form.get('activo') or '').strip()
    descripcion_qs = (request.args.get('descripcion') or request.form.get('descripcion') or '').strip()
    observacion_qs = (request.args.get('observacion') or request.form.get('observacion') or '').strip()

    proveedor_obj = None
    if origen.lower() == 'proveedor' and proveedor_id:
        try:
            proveedor_obj = ProveedorEvaluacion.query.get(proveedor_id)
        except Exception:
            proveedor_obj = None

    fecha_hoy = datetime.now().strftime('%Y-%m-%d')

    propietario_prefill = ''
    riesgo_prefill = ''
    amenaza_prefill = ''
    vulnerabilidad_prefill = ''
    tipo_activo_prefill = ''
    nombre_activo_prefill = ''
    dimension_prefill = ''
    observaciones_prefill = ''
    planes_accion_prefill = ''
    responsable_prefill = ''

    if proveedor_obj:
        nombre_proveedor = (proveedor_obj.nombre_proveedor or '').strip()
        responsable_area = (proveedor_obj.responsable_area_nombre or proveedor_obj.responsable_area_cargo or '').strip()
        resultado_eval = (proveedor_obj.resultado_evaluacion or '').strip()
        criticidad_txt = (proveedor_obj.criticidad_texto or '').strip()
        criticidad_pct = proveedor_obj.criticidad_pct if proveedor_obj.criticidad_pct is not None else 0

        if proveedor_obj.procesa_info_sensible == 'Sí' or proveedor_obj.procesa_datos_personales == 'Sí':
            dimension_prefill = 'Confidencialidad'
        elif proveedor_obj.es_esencial == 'Sí':
            dimension_prefill = 'Disponibilidad'
        else:
            dimension_prefill = ''

        propietario_prefill = responsable_area
        responsable_prefill = responsable_area
        riesgo_prefill = f"Dependencia y exposición de seguridad asociada al proveedor {nombre_proveedor}"
        amenaza_prefill = "Incumplimiento, indisponibilidad o falla del proveedor"
        vulnerabilidad_prefill = (
            "Proveedor no aprobado por seguridad o con brechas en controles, continuidad, "
            "recuperación, nube, datos personales o SLA"
        )
        tipo_activo_prefill = "Proveedor"
        nombre_activo_prefill = nombre_proveedor

        observaciones_prefill = (
            "Riesgo generado automáticamente desde el módulo de proveedores.\n"
            f"Proveedor: {nombre_proveedor}\n"
            f"Resultado evaluación: {resultado_eval}\n"
            f"Criticidad: {criticidad_txt} ({criticidad_pct}%)\n"
            f"Descripción producto/servicio: {proveedor_obj.desc_producto_servicio or ''}\n"
            f"Transversal: {proveedor_obj.es_transversal or ''}\n"
            f"Esencial continuidad: {proveedor_obj.es_esencial or ''}\n"
            f"Plan de continuidad: {proveedor_obj.tiene_plan_cont or ''}\n"
            f"Plan de recuperación: {proveedor_obj.tiene_plan_rec or ''}\n"
            f"Alternativas en el mercado: {proveedor_obj.existen_alternativas or ''}\n"
            f"Plan de migración: {proveedor_obj.existe_plan_migracion or ''}\n"
            f"Procesa info. sensible: {proveedor_obj.procesa_info_sensible or ''}\n"
            f"Procesa datos personales: {proveedor_obj.procesa_datos_personales or ''}\n"
            f"Procesa información en la nube: {proveedor_obj.procesa_info_nube or ''}\n"
            f"Incluye SLA definidos: {proveedor_obj.incluye_sla or ''}\n"
        )

        planes_accion_prefill = (
            "1. Definir tratamiento del riesgo del proveedor.\n"
            "2. Validar controles de seguridad exigibles al tercero.\n"
            "3. Revisar continuidad, recuperación y SLA.\n"
            "4. Formalizar plan de seguimiento y remediación."
        )

    else:
        riesgo_prefill = (descripcion_qs or '').strip()
        amenaza_prefill = "Incumplimiento, indisponibilidad o falla del proveedor" if origen.lower() == 'proveedor' else ''
        vulnerabilidad_prefill = (
            "Proveedor no aprobado por seguridad o con brechas en controles, continuidad, recuperación, nube, datos personales o SLA"
            if origen.lower() == 'proveedor' else ''
        )
        tipo_activo_prefill = 'Proveedor' if origen.lower() == 'proveedor' else ''
        nombre_activo_prefill = (activo_qs or proveedor_nombre_qs or '').strip()
        observaciones_prefill = (observacion_qs or '').strip()

    # =========================================================
    # POST
    # =========================================================
    if request.method == 'POST':

        controles_formulario = riesgo_extraer_controles_formulario(request.form)
        solidez_individual_calculada = (
            controles_formulario[0]["solidez_individual"] if controles_formulario else 0.0
        )
        solidez_grupal_calculada = riesgo_calcular_solidez_grupal(controles_formulario)

        resultado_residual = riesgo_calcular_resultados(
            request.form.get('prob_inh'),
            request.form.get('imp_inh'),
            solidez_grupal_calculada,
        )
        prob_res_num = resultado_residual['prob_res_num']
        impacto_res_num = resultado_residual['imp_res_num']
        prob_res_label = resultado_residual['prob_res_label']
        impacto_res_label = resultado_residual['imp_res_label']
        cuadrante_prob = prob_res_label
        prob_res = prob_res_label
        cuadrante_imp = impacto_res_label
        riesgo_residual_calc = resultado_residual['riesgo_residual']
        riesgo_inherente_calc = resultado_residual['riesgo_inherente']

        tipo_riesgo_id = request.form.get("tipo_riesgo_id")

        obs_final = (request.form.get('observaciones') or '').strip()
        if origen.lower() == 'proveedor':
            traza = (
                f"\n\n[TRAZABILIDAD]\n"
                f"Origen: Proveedor\n"
                f"Proveedor ID: {proveedor_id or ''}\n"
                f"Proveedor: {proveedor_nombre_qs or nombre_activo_prefill or ''}"
            )
            if traza not in obs_final:
                obs_final = (obs_final + traza).strip()

        nuevo = Riesgo(
            codigo_riesgo=request.form.get('codigo_riesgo'),
            riesgo=request.form.get('riesgo'),
            fecha_identificacion=request.form.get('fecha_identificacion'),
            propietario_riesgo=request.form.get('propietario_riesgo'),
            codigo_amenaza=request.form.get('cod_amenaza'),
            amenaza=request.form.get('amenaza'),
            codigo_vulnerabilidad=request.form.get('cod_vulnerabilidad'),
            vulnerabilidad=request.form.get('vulnerabilidad'),
            tipo_activo=request.form.get('tipo_activo'),
            nombre_activo=request.form.get('nombre_activo'),
            dimension_seguridad=request.form.get('dimension_seguridad'),
            probabilidad=resultado_residual['prob_inh_num'],
            impacto=resultado_residual['imp_inh_num'],
            prob_inh=request.form.get('prob_inh'),
            imp_inh=request.form.get('imp_inh'),
            riesgo_inherente=riesgo_inherente_calc,
            control_codigo=None,
            codigo_anexo=None,
            codigo_control_pci_dss=None,
            codigo_control_nist_csf=None,
            codigo_control_soc2=None,
            descripcion_control=None,
            plan_accion=request.form.get('plan_accion'),
            asignacion=None,
            cargo=None,
            tipo_control=None,
            forma_control=None,
            frecuencia=None,
            funcionalidad=None,
            estado_control=None,
            referencia_documental=None,
            evidencia_control=None,
            soporte_evidencia=None,
            diseno_control=None,
            ejecucion_control=None,
            calificacion_asignacion=0.0,
            calificacion_tipo_control=0.0,
            calificacion_forma_control=0.0,
            calificacion_funcionalidad=0.0,
            calificacion_estado_control=0.0,
            calificacion_soporte_evidencia=0.0,
            valor_ejecucion_control=0.0,
            valor=solidez_grupal_calculada,
            solidez_individual=solidez_individual_calculada,
            solidez_grupal=solidez_grupal_calculada,
            cuadrante_prob=cuadrante_prob,
            prob_res=prob_res,
            cuadrante_imp=cuadrante_imp,
            impacto_res=impacto_res_num,
            impacto_res_label=impacto_res_label,
            riesgo_residual=riesgo_residual_calc,
            fecha_revision=request.form.get('fecha_revision'),
            tratamiento_riesgo=request.form.get('tratamiento_riesgo'),
            observaciones=obs_final,
            planes_accion=request.form.get('planes_accion'),
            responsable=request.form.get('responsable'),
            fecha_implementacion=request.form.get('fecha_implementacion'),
            tipo_riesgo_id=int(tipo_riesgo_id) if tipo_riesgo_id else None,
        )

        db.session.add(nuevo)
        db.session.flush()
        riesgo_reemplazar_controles(nuevo, controles_formulario)
        riesgo_sincronizar_campos_legacy(nuevo, controles_formulario)
        db.session.commit()
        flash(
            f"✅ Riesgo registrado con {len(controles_formulario)} control(es). "
            f"Solidez grupal: {solidez_grupal_calculada * 100:.2f}%.",
            "success",
        )
        return redirect(url_for('riesgos_menu'))

    reglas = sorted(ConfigProbResidual.query.all(), key=lambda r: max(float(r.min), float(r.max)), reverse=True)
    reglas_impacto = sorted(ConfigImpactoResidual.query.all(), key=lambda r: max(float(r.min), float(r.max)), reverse=True)
    reglas_json = json.dumps([{'min': r.min, 'max': r.max, 'bajar': r.bajar} for r in reglas])
    reglas_impacto_json = json.dumps([{'min': r.min, 'max': r.max, 'bajar': r.bajar} for r in reglas_impacto])

    tipos_riesgo = TipoRiesgo.query.filter_by(
        owner_user_id=user.id,
        activo=True
    ).order_by(TipoRiesgo.nombre.asc()).all()

    reglas_prob_data = [{'min': r.min, 'max': r.max, 'bajar': r.bajar} for r in reglas]
    reglas_imp_data = [{'min': r.min, 'max': r.max, 'bajar': r.bajar} for r in reglas_impacto]
    controles_widget = riesgo_controles_widget_html(
        controles_iniciales=[],
        reglas_prob=reglas_prob_data,
        reglas_imp=reglas_imp_data,
        section_class="riskform-section-title",
    )

    riesgos_html_formulario = """
    <div class="riskform-shell">

      <div class="riskform-header-card">
        <div class="riskform-header-overlay">
          <div class="riskform-header-text">
            <h3 class="riskform-title m-0">➕ Adición de Riesgos</h3>
            <div class="riskform-subtitle">
              Registro, análisis, valoración y tratamiento de riesgos del Sistema de Gestión de Seguridad de la Información
            </div>
          </div>
        </div>
      </div>

      <div class="riskform-top-actions">
        <a href="{{ url_for('riesgos_menu') }}"
           class="btn btn-light rounded-pill px-4 fw-semibold">
          ⬅ Volver a Gestión de Riesgos
        </a>
      </div>

      <form method="POST" class="riskform-card">
        <input type="hidden" name="origen" value="{{ origen }}">
        <input type="hidden" name="proveedor_id" value="{{ proveedor_id or '' }}">
        <input type="hidden" name="proveedor" value="{{ proveedor_nombre_qs or '' }}">
        <input type="hidden" name="activo" value="{{ nombre_activo_prefill or '' }}">
        <input type="hidden" name="descripcion" value="{{ riesgo_prefill or '' }}">
        <input type="hidden" name="observacion" value="{{ observaciones_prefill or '' }}">

        <div class="riskform-card-body">
          <div class="row g-3">

            {% if origen|lower == 'proveedor' %}
            <div class="col-12">
              <div class="alert alert-danger rounded-4 shadow-sm mb-2">
                <strong>Origen:</strong> este riesgo fue iniciado desde el módulo de proveedores.
                {% if proveedor_nombre_qs %}<br><strong>Proveedor:</strong> {{ proveedor_nombre_qs }}{% endif %}
              </div>
            </div>
            {% endif %}

            <div class="col-12">
              <div class="riskform-section-title">🧩 Identificación del Riesgo</div>
            </div>

            <div class="col-md-3">
              <label class="form-label">Código de Riesgo</label>
              <input class="form-control" name="codigo_riesgo" required>
            </div>
            <div class="col-md-5">
              <label class="form-label">Riesgo</label>
              <input class="form-control" name="riesgo" value="{{ riesgo_prefill or '' }}" required>
            </div>
            <div class="col-md-4">
              <label class="form-label">Tipo de Riesgo</label>
              <select class="form-control" name="tipo_riesgo_id" required>
                <option value="">Seleccione...</option>
                {% for t in tipos_riesgo %}
                  <option value="{{ t.id }}">{{ t.nombre }}</option>
                {% endfor %}
              </select>
            </div>

            <div class="col-md-3">
              <label class="form-label">Fecha de Identificación</label>
              <input type="date" class="form-control" name="fecha_identificacion" value="{{ fecha_hoy }}">
            </div>
            <div class="col-md-5">
              <label class="form-label">Propietario del Riesgo</label>
              <input class="form-control" name="propietario_riesgo" value="{{ propietario_prefill or '' }}">
            </div>
            <div class="col-md-4">
              <label class="form-label">Responsable</label>
              <input class="form-control" name="responsable" value="{{ responsable_prefill or '' }}">
            </div>

            <div class="col-12">
              <div class="riskform-section-title">🧩 Análisis</div>
            </div>

            <div class="col-md-3">
              <label class="form-label">Código Amenaza</label>
              <input class="form-control" name="cod_amenaza">
            </div>
            <div class="col-md-3">
              <label class="form-label">Amenaza</label>
              <input class="form-control" name="amenaza" value="{{ amenaza_prefill or '' }}">
            </div>
            <div class="col-md-3">
              <label class="form-label">Código Vulnerabilidad</label>
              <input class="form-control" name="cod_vulnerabilidad">
            </div>
            <div class="col-md-3">
              <label class="form-label">Vulnerabilidad</label>
              <input class="form-control" name="vulnerabilidad" value="{{ vulnerabilidad_prefill or '' }}">
            </div>

            <div class="col-md-3">
              <label class="form-label">Tipo de Activo</label>
              <input class="form-control" name="tipo_activo" value="{{ tipo_activo_prefill or '' }}">
            </div>
            <div class="col-md-5">
              <label class="form-label">Nombre del Activo</label>
              <input class="form-control" name="nombre_activo" value="{{ nombre_activo_prefill or '' }}">
            </div>
            <div class="col-md-4">
              <label class="form-label">Principio de Seguridad</label>
              <select class="form-control" name="dimension_seguridad">
                <option value="">Seleccione...</option>
                <option value="Confidencialidad" {% if dimension_prefill=='Confidencialidad' %}selected{% endif %}>Confidencialidad</option>
                <option value="Integridad" {% if dimension_prefill=='Integridad' %}selected{% endif %}>Integridad</option>
                <option value="Disponibilidad" {% if dimension_prefill=='Disponibilidad' %}selected{% endif %}>Disponibilidad</option>
              </select>
            </div>

            <div class="col-12">
              <div class="riskform-section-title">🧩 Valoración del Riesgo Inherente</div>
            </div>

            <div class="col-md-4">
              <label class="form-label">Probabilidad Riesgo Inherente</label>
              <select class="form-control" name="prob_inh" id="prob_inh" onchange="calcularRiesgoInherente();calcularRiesgoResidual();">
                <option value="">Seleccione...</option>
                <option>Rara vez o Muy baja</option>
                <option>Eventualmente o baja</option>
                <option>Puede ocurrir o Moderada</option>
                <option>Probable o Alta</option>
                <option>Muy frecuente o Muy Alta</option>
              </select>
            </div>
            <div class="col-md-4">
              <label class="form-label">Impacto Riesgo Inherente</label>
              <select class="form-control" name="imp_inh" id="imp_inh" onchange="calcularRiesgoInherente();calcularRiesgoResidual();">
                <option value="">Seleccione...</option>
                <option>Insignificante o Inferior</option>
                <option>Menor</option>
                <option>Moderado o Importante</option>
                <option>Mayor</option>
                <option>Catastrófico o Crítico</option>
              </select>
            </div>
            <div class="col-md-4">
              <label class="form-label">Riesgo Inherente</label>
              <input type="text" class="form-control" name="riesgo_inherente" id="riesgo_inherente" readonly>
            </div>

            {{ controles_widget|safe }}

            <div class="col-12">
              <div class="riskform-section-title">🧩 Tratamiento del Riesgo Inherente</div>
            </div>
            <div class="col-md-12">
              <label class="form-label">Plan de Acción</label>
              <textarea class="form-control" name="plan_accion"></textarea>
            </div>

            <div class="col-12">
              <div class="riskform-section-title">🧩 Evaluación del Riesgo Residual</div>
            </div>
            <div class="col-md-3">
              <label class="form-label">Solidez Grupal (Promedio)</label>
              <input class="form-control risk-control-result" id="solidez_grupal" name="solidez_grupal" readonly>
              <input type="hidden" id="valor" name="valor">
              <div class="form-text">Promedio de la solidez individual de todos los controles registrados.</div>
            </div>
            <div class="col-md-3">
              <label class="form-label">Probabilidad Residual</label>
              <input class="form-control" id="cuadrante_prob" name="cuadrante_prob" readonly>
            </div>
            <div class="col-md-3">
              <label class="form-label">Impacto Residual</label>
              <input class="form-control" id="cuadrante_imp" name="cuadrante_imp" readonly>
            </div>
            <div class="col-md-3">
              <label class="form-label">Riesgo Residual</label>
              <input class="form-control" id="riesgo_residual" name="riesgo_residual" readonly>
            </div>
            <div class="col-md-3">
              <label class="form-label">Fecha de Revisión</label>
              <input type="date" class="form-control" name="fecha_revision">
            </div>

            <div class="col-12">
              <div class="riskform-section-title">🧩 Tratamiento del Riesgo Residual</div>
            </div>

            <div class="col-md-3">
              <label class="form-label">Tratamiento del Riesgo</label>
              <select class="form-control" name="tratamiento_riesgo" required>
                <option value="">Seleccione...</option>
                <option value="Aceptación">Aceptación</option>
                <option value="Rechazo">Rechazo</option>
                <option value="Transferencia">Transferencia</option>
                <option value="Mitigación">Mitigación</option>
              </select>
            </div>

            <div class="col-md-12">
              <label class="form-label">Observaciones</label>
              <textarea class="form-control" name="observaciones" rows="8">{{ observaciones_prefill or '' }}</textarea>
            </div>
            <div class="col-md-12">
              <label class="form-label">Planes de Acción</label>
              <textarea class="form-control" name="planes_accion">{{ planes_accion_prefill or '' }}</textarea>
            </div>

          </div>

          <div class="riskform-bottom-actions">
            <button class="btn btn-success rounded-pill px-5 py-2 fw-bold" type="submit">
              Guardar Riesgo
            </button>
            <a href="{{ url_for('riesgos_menu') }}" class="btn rounded-pill px-5 py-2 fw-bold riskform-cancel-btn">
              Cancelar
            </a>
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

          .riskform-shell{
            width:96%;
            max-width:1600px;
            margin:10px auto 24px auto;
          }

          /* =========================
             HEADER / HERO COMPACTO
          ========================== */
          .riskform-header-card{
            background:
              linear-gradient(135deg, rgba(11,58,110,.97), rgba(20,89,166,.95), rgba(44,123,229,.92));
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

          .riskform-header-card::before{
            content:"";
            position:absolute;
            inset:0;
            background:
              radial-gradient(circle at 92% 12%, rgba(255,255,255,.20), transparent 26%),
              repeating-linear-gradient(
                135deg,
                rgba(255,255,255,.05) 0px,
                rgba(255,255,255,.05) 1px,
                transparent 1px,
                transparent 15px
              );
            pointer-events:none;
          }

          .riskform-header-overlay{
            width:100%;
            height:100%;
            display:flex;
            align-items:center;
            justify-content:flex-start;
            text-align:left;
            padding:0;
            background:transparent;
            position:relative;
            z-index:1;
          }

          .riskform-header-overlay::before{
            content:"⚠️";
            width:54px;
            height:54px;
            min-width:54px;
            border-radius:14px;
            background:rgba(255,255,255,.96);
            color:#0b4a8f;
            display:flex;
            align-items:center;
            justify-content:center;
            font-size:1.55rem;
            box-shadow:0 8px 18px rgba(0,0,0,.20);
            margin-right:14px;
          }

          .riskform-header-text{
            max-width:1100px;
            position:relative;
            z-index:1;
          }

          .riskform-header-text::before{
            content:"SGSI · Gestión de Riesgos";
            display:inline-block;
            background:rgba(255,255,255,.18);
            border:1px solid rgba(255,255,255,.30);
            border-radius:999px;
            padding:3px 10px;
            font-size:.66rem;
            font-weight:800;
            letter-spacing:.35px;
            margin-bottom:4px;
          }

          .riskform-title{
            color:#ffffff !important;
            font-weight:950;
            font-size:1.36rem;
            line-height:1.08;
            text-shadow:0 3px 10px rgba(0,0,0,.32);
            margin:0;
          }

          .riskform-subtitle{
            color:rgba(248,252,255,.96);
            font-size:.78rem;
            margin-top:4px;
            line-height:1.25;
            text-shadow:none;
          }

          /* =========================
             ACCIONES SUPERIORES
          ========================== */
          .riskform-top-actions{
            display:flex;
            justify-content:center;
            gap:10px;
            flex-wrap:wrap;
            margin:10px 0 12px 0;
          }

          .riskform-top-actions .btn{
            border-radius:10px !important;
            min-height:36px;
            padding:7px 20px !important;
            font-size:.80rem;
            font-weight:900;
            box-shadow:0 7px 14px rgba(15,23,42,.14);
          }

          /* =========================
             CARD PRINCIPAL
          ========================== */
          .riskform-card{
            background:rgba(255,255,255,.96);
            border-radius:18px;
            box-shadow:0 12px 24px rgba(15,23,42,.18);
            overflow:hidden;
            backdrop-filter:blur(8px);
            border:1px solid rgba(219,230,244,.9);
          }

          .riskform-card-body{
            padding:16px 18px;
          }

          /* =========================
             SECCIONES
          ========================== */
          .riskform-section-title{
            font-weight:950;
            font-size:.78rem;
            color:#0b4a8f;
            padding:9px 12px;
            border-radius:12px;
            background:#eef5ff;
            border:1px solid #d9eaff;
            margin:10px 0 12px 0;
          }

          .riskform-section-title:first-child{
            margin-top:0;
          }

          /* =========================
             FORMULARIOS COMPACTOS
          ========================== */
          .riskform-card .form-label{
            font-weight:800;
            color:#25324a;
            margin-bottom:4px;
            font-size:.78rem;
          }

          .riskform-card .form-control,
          .riskform-card .form-select{
            border-radius:9px;
            border:1px solid #d9e3f0;
            min-height:37px;
            font-size:.80rem;
            box-shadow:none;
            padding-top:5px;
            padding-bottom:5px;
          }

          .riskform-card textarea.form-control{
            min-height:68px;
            resize:vertical;
          }

          .riskform-card .form-control:focus,
          .riskform-card .form-select:focus{
            border-color:#3f86d6;
            box-shadow:0 0 0 .18rem rgba(63,134,214,.18);
          }

          .riskform-card .row{
            row-gap:10px;
          }

          .riskform-card .mb-3{
            margin-bottom:.70rem !important;
          }

          /* =========================
             ACCIONES INFERIORES
          ========================== */
          .riskform-bottom-actions{
            display:flex;
            justify-content:center;
            gap:10px;
            flex-wrap:wrap;
            margin-top:18px;
          }

          .riskform-bottom-actions .btn{
            border-radius:10px !important;
            min-height:32px;
            padding:8px 24px !important;
            font-size:.82rem;
            font-weight:900;
            box-shadow:0 8px 16px rgba(15,23,42,.14);
          }

          .riskform-bottom-actions .btn-primary,
          .riskform-top-actions .btn-primary{
            border:none;
            background:linear-gradient(135deg,#086df0,#2487ff);
            color:#fff;
          }

          .riskform-bottom-actions .btn-success,
          .riskform-top-actions .btn-success{
            border:none;
            background:linear-gradient(135deg,#12844b,#16a05d);
            color:#fff;
          }

          .riskform-cancel-btn{
            background:#ffffff;
            color:#0f172a;
            border:1px solid #cfd8e3;
            box-shadow:0 6px 14px rgba(0,0,0,.10);
          }

          .riskform-cancel-btn:hover{
            background:#edf5ff;
            color:#0b65d8;
            border-color:#9ec5fe;
          }

          /* =========================
             RESPONSIVE
          ========================== */
          @media (max-width:992px){
            .riskform-shell{
              width:98%;
              margin:8px auto 22px auto;
            }

            .riskform-header-card{
              min-height:88px;
              padding:15px 18px;
            }

            .riskform-title{
              font-size:1.22rem;
            }

            .riskform-subtitle{
              font-size:.74rem;
            }

            .riskform-card-body{
              padding:8px 7px;
            }

            .riskform-section-title{
              font-size:.82rem;
            }
          }

          @media (max-width:768px){
            .riskform-header-overlay{
              justify-content:center;
              text-align:center;
              flex-direction:column;
              gap:10px;
            }

            .riskform-header-overlay::before{
              margin-right:0;
            }

            .riskform-title{
              font-size:1.12rem;
            }

            .riskform-subtitle{
              font-size:.72rem;
            }

            .riskform-bottom-actions .btn,
            .riskform-top-actions .btn{
              width:100%;
            }
          }
        </style>
      </form>
    </div>
    """

    form_rendered = render_template_string(
        riesgos_html_formulario,
        tipos_riesgo=tipos_riesgo,
        reglas_json=reglas_json,
        reglas_impacto_json=reglas_impacto_json,
        fecha_hoy=fecha_hoy,
        origen=origen,
        proveedor_id=proveedor_id,
        proveedor_nombre_qs=proveedor_nombre_qs,
        riesgo_prefill=riesgo_prefill,
        propietario_prefill=propietario_prefill,
        amenaza_prefill=amenaza_prefill,
        vulnerabilidad_prefill=vulnerabilidad_prefill,
        tipo_activo_prefill=tipo_activo_prefill,
        nombre_activo_prefill=nombre_activo_prefill,
        dimension_prefill=dimension_prefill,
        observaciones_prefill=observaciones_prefill,
        planes_accion_prefill=planes_accion_prefill,
        responsable_prefill=responsable_prefill,
        controles_widget=Markup(controles_widget),
        pci_options=construir_opciones_control(PCI_DSS_CONTROLES),
        nist_options=construir_opciones_control(NIST_CSF_20_CONTROLES),
        soc2_options=construir_opciones_control(SOC2_CONTROLES)
    )

    return render_template_string(BASE, content=Markup(form_rendered))

# ===========================================================
# CONFIGURAR PROBABILIDAD RESIDUAL
# ===========================================================
@app.route('/configurar_probabilidad_residual', methods=['GET', 'POST'])
@login_required
def configurar_probabilidad_residual():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede configurar parámetros.", "danger")
        return redirect(url_for('gestion_riesgos'))

    if user.role != 'admin' and not verificar_permiso(user, "Gestión de Riesgos"):
        flash("No tiene permiso para configurar parámetros.", "danger")
        return redirect(url_for('gestion_riesgos'))

    if request.method == 'POST':
        reglas = []
        for i in range(1, 5):
            min_val = request.form.get(f'min_{i}')
            max_val = request.form.get(f'max_{i}')
            bajar = request.form.get(f'bajar_{i}')

            if min_val not in (None, '') and max_val not in (None, '') and bajar not in (None, ''):
                minimo = float(str(min_val).replace(',', '.'))
                maximo = float(str(max_val).replace(',', '.'))
                reglas.append({
                    'min': min(minimo, maximo),
                    'max': max(minimo, maximo),
                    'bajar': max(0, min(4, int(bajar)))
                })

        db.session.query(ConfigProbResidual).delete()

        for r in reglas:
            nueva = ConfigProbResidual(
                min=r['min'],
                max=r['max'],
                bajar=r['bajar']
            )
            db.session.add(nueva)

        db.session.commit()
        actualizados = riesgo_recalcular_matriz_existente(commit=True)
        flash(
            f"✅ Configuración de probabilidad residual guardada. {actualizados} riesgo(s) recalculado(s).",
            "success",
        )
        return redirect(url_for('configurar_probabilidad_residual'))

    reglas = sorted(ConfigProbResidual.query.all(), key=lambda r: max(float(r.min), float(r.max)), reverse=True)

    html = render_template_string("""
    <div class="prob-shell">

      <div class="prob-header-card">
        <div class="prob-header-overlay">
          <div class="prob-header-text">
            <h2 class="prob-title m-0">Configuración de Probabilidad Residual</h2>
            <div class="prob-subtitle">
              Definición de rangos y niveles de reducción para el cálculo de probabilidad residual del riesgo
            </div>
          </div>
        </div>
      </div>

      {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
          <div class="prob-alert-card">
            {% for category, message in messages %}
              <div class="alert alert-{{ category if category in ['success','danger','warning','info','primary','secondary'] else 'info' }} mb-0">
                {{ message }}
              </div>
            {% endfor %}
          </div>
        {% endif %}
      {% endwith %}

      <form method="POST">
        <div class="prob-table-card">
          <div class="prob-table-card-body">

            <div class="prob-table-wrap">
              <div class="table-responsive">
                <table class="table table-bordered align-middle text-center prob-table mb-0">
                  <thead>
                    <tr>
                      <th>Rango mínimo (%)</th>
                      <th>Rango máximo (%)</th>
                      <th>Bajada de nivel</th>
                    </tr>
                  </thead>
                  <tbody>
                    {% for i in range(1, 5) %}
                    <tr>
                      <td>
                        <input type="number"
                               step="0.01"
                               class="form-control text-center"
                               name="min_{{i}}"
                               value="{{ reglas[i-1].min if reglas|length >= i else '' }}"
                               required>
                      </td>
                      <td>
                        <input type="number"
                               step="0.01"
                               class="form-control text-center"
                               name="max_{{i}}"
                               value="{{ reglas[i-1].max if reglas|length >= i else '' }}"
                               required>
                      </td>
                      <td>
                        <select class="form-select text-center" name="bajar_{{i}}">
                          <option value="0" {% if reglas|length >= i and reglas[i-1].bajar == 0 %}selected{% endif %}>0 niveles</option>
                          <option value="1" {% if reglas|length >= i and reglas[i-1].bajar == 1 %}selected{% endif %}>1 nivel</option>
                          <option value="2" {% if reglas|length >= i and reglas[i-1].bajar == 2 %}selected{% endif %}>2 niveles</option>
                          <option value="3" {% if reglas|length >= i and reglas[i-1].bajar == 3 %}selected{% endif %}>3 niveles</option>
                          <option value="4" {% if reglas|length >= i and reglas[i-1].bajar == 4 %}selected{% endif %}>4 niveles</option>
                        </select>
                      </td>
                    </tr>
                    {% endfor %}
                  </tbody>
                </table>
              </div>
            </div>

            <div class="prob-bottom-actions">
              <button type="submit" class="btn btn-success rounded-pill px-5 py-2 fw-bold">
                💾 Guardar configuración
              </button>

              <a href="{{ url_for('gestion_riesgos') }}"
                 class="btn rounded-pill px-5 py-2 fw-bold prob-back-btn">
                ⬅ Volver a Gestión de Riesgos
              </a>
            </div>

          </div>
        </div>
      </form>

    </div>

    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg') !important;
        background-size:cover !important;
        background-position:center !important;
        background-attachment:fixed !important;
        background-repeat:no-repeat !important;
        background-color:transparent !important;
      }

      .prob-shell{
        width:96%;
        max-width:1300px;
        margin:10px auto 24px auto;
      }

      /* =========================
         HEADER / HERO COMPACTO
      ========================== */
      .prob-header-card{
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

      .prob-header-card::before{
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
        pointer-events:none;
      }

      .prob-header-overlay{
        width:100%;
        height:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        padding:0;
        background:transparent;
        position:relative;
        z-index:1;
      }

      .prob-header-overlay::before{
        content:"📈";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:rgba(255,255,255,.96);
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.55rem;
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .prob-header-text{
        max-width:1000px;
        position:relative;
        z-index:1;
      }

      .prob-header-text::before{
        content:"SGSI · Parámetros de Riesgo";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border:1px solid rgba(255,255,255,.30);
        border-radius:999px;
        padding:3px 10px;
        font-size:.66rem;
        font-weight:800;
        letter-spacing:.35px;
        margin-bottom:4px;
      }

      .prob-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.36rem;
        line-height:1.08;
        text-shadow:0 3px 10px rgba(0,0,0,.32);
        margin:0;
      }

      .prob-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
        text-shadow:none;
      }

      /* =========================
         ALERTAS
      ========================== */
      .prob-alert-card{
        margin-bottom:12px;
      }

      .prob-alert-card .alert{
        border-radius:14px;
        font-size:.82rem;
        font-weight:700;
        box-shadow:0 8px 18px rgba(15,23,42,.12);
      }

      /* =========================
         CARD / TABLA
      ========================== */
      .prob-table-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        overflow:hidden;
        border:1px solid rgba(219,230,244,.9);
      }

      .prob-table-card-body{
        padding:8px 7px;
      }

      .prob-table-wrap{
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:rgba(255,255,255,.98);
        overflow:auto;
      }

      .prob-table{
        margin-bottom:0;
        font-size:.80rem;
      }

      .prob-table thead th{
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff;
        font-weight:900;
        text-align:center;
        vertical-align:middle;
        padding:11px 9px;
        font-size:.78rem;
        border-right:1px solid rgba(255,255,255,.28);
      }

      .prob-table thead th:first-child{
        border-top-left-radius:12px;
      }

      .prob-table thead th:last-child{
        border-top-right-radius:12px;
      }

      .prob-table td{
        vertical-align:middle;
        padding:9px 8px;
        font-size:.78rem;
        border-right:1px solid #dce6f3;
        border-bottom:1px solid #dce6f3;
        background:rgba(255,255,255,.98);
      }

      .prob-table tbody tr:nth-child(even) td{
        background:#f8fbff;
      }

      .prob-table tbody tr:hover td{
        background:#eef6ff;
      }

      .prob-table .form-control,
      .prob-table .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:36px;
        font-size:.78rem;
        box-shadow:none;
        padding-top:5px;
        padding-bottom:5px;
      }

      .prob-table .form-control:focus,
      .prob-table .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .18rem rgba(63,134,214,.18);
      }

      /* =========================
         BOTONES
      ========================== */
      .prob-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin-top:16px;
      }

      .prob-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 24px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .prob-bottom-actions .btn-primary,
      .prob-bottom-actions .btn-success{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .prob-bottom-actions .btn-danger{
        border:none;
        background:linear-gradient(135deg,#b91c1c,#ef4444);
        color:#fff;
      }

      .prob-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .prob-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         SCROLLBAR
      ========================== */
      .prob-table-wrap::-webkit-scrollbar{
        height:11px;
        width:11px;
      }

      .prob-table-wrap::-webkit-scrollbar-track{
        background:#dbe4f0;
        border-radius:12px;
      }

      .prob-table-wrap::-webkit-scrollbar-thumb{
        background:linear-gradient(180deg,#5aa3ea 0%,#3f86d6 100%);
        border-radius:12px;
        border:2px solid #dbe4f0;
      }

      .prob-table-wrap{
        scrollbar-width:thin;
        scrollbar-color:#3f86d6 #dbe4f0;
      }

      /* =========================
         RESPONSIVE
      ========================== */
      @media (max-width:992px){
        .prob-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .prob-header-card{
          min-height:88px;
          padding:15px 18px;
        }

        .prob-title{
          font-size:1.22rem;
        }

        .prob-subtitle{
          font-size:.74rem;
        }

        .prob-table-card-body{
          padding:12px;
        }

        .prob-table thead th,
        .prob-table td{
          padding:8px 7px;
          font-size:.74rem;
        }
      }

      @media (max-width:768px){
        .prob-header-overlay{
          justify-content:center;
          text-align:center;
          flex-direction:column;
          gap:10px;
        }

        .prob-header-overlay::before{
          margin-right:0;
        }

        .prob-title{
          font-size:1.12rem;
        }

        .prob-subtitle{
          font-size:.72rem;
        }

        .prob-bottom-actions .btn{
          width:100%;
        }
      }
    </style>
    """, reglas=reglas)

    return render_template_string(BASE, content=Markup(html))

# ===========================================================
# CONFIGURAR IMPACTO RESIDUAL
# ===========================================================
@app.route('/configurar_impacto_residual', methods=['GET', 'POST'])
@login_required
def configurar_impacto_residual():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede configurar parámetros.", "danger")
        return redirect(url_for('gestion_riesgos'))

    if user.role != 'admin' and not verificar_permiso(user, "Gestión de Riesgos"):
        flash("No tiene permiso para configurar parámetros.", "danger")
        return redirect(url_for('gestion_riesgos'))

    if request.method == 'POST':
        reglas = []
        for i in range(1, 5):
            min_val = request.form.get(f'min_{i}')
            max_val = request.form.get(f'max_{i}')
            bajar = request.form.get(f'bajar_{i}')

            if min_val not in (None, '') and max_val not in (None, '') and bajar not in (None, ''):
                minimo = float(str(min_val).replace(',', '.'))
                maximo = float(str(max_val).replace(',', '.'))
                reglas.append({
                    'min': min(minimo, maximo),
                    'max': max(minimo, maximo),
                    'bajar': max(0, min(4, int(bajar)))
                })

        db.session.query(ConfigImpactoResidual).delete()

        for r in reglas:
            nueva = ConfigImpactoResidual(
                min=r['min'],
                max=r['max'],
                bajar=r['bajar']
            )
            db.session.add(nueva)

        db.session.commit()
        actualizados = riesgo_recalcular_matriz_existente(commit=True)
        flash(
            f"✅ Configuración de impacto residual guardada. {actualizados} riesgo(s) recalculado(s).",
            "success",
        )
        return redirect(url_for('configurar_impacto_residual'))

    reglas = sorted(ConfigImpactoResidual.query.all(), key=lambda r: max(float(r.min), float(r.max)), reverse=True)

    html = render_template_string("""
    <div class="imp-shell">

      <div class="imp-header-card">
        <div class="imp-header-overlay">
          <div class="imp-header-text">
            <h2 class="imp-title m-0">Configuración de Impacto Residual</h2>
            <div class="imp-subtitle">
              Definición de rangos y niveles de reducción para el cálculo de impacto residual del riesgo
            </div>
          </div>
        </div>
      </div>

      {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
          <div class="imp-alert-card">
            {% for category, message in messages %}
              <div class="alert alert-{{ category if category in ['success','danger','warning','info','primary','secondary'] else 'info' }} mb-0">
                {{ message }}
              </div>
            {% endfor %}
          </div>
        {% endif %}
      {% endwith %}

      <form method="POST">
        <div class="imp-table-card">
          <div class="imp-table-card-body">

            <div class="imp-table-wrap">
              <div class="table-responsive">
                <table class="table table-bordered align-middle text-center imp-table mb-0">
                  <thead>
                    <tr>
                      <th>Rango mínimo (%)</th>
                      <th>Rango máximo (%)</th>
                      <th>Bajada de nivel</th>
                    </tr>
                  </thead>
                  <tbody>
                    {% for i in range(1, 5) %}
                    <tr>
                      <td>
                        <input type="number"
                               step="0.01"
                               class="form-control text-center"
                               name="min_{{i}}"
                               value="{{ reglas[i-1].min if reglas|length >= i else '' }}"
                               required>
                      </td>
                      <td>
                        <input type="number"
                               step="0.01"
                               class="form-control text-center"
                               name="max_{{i}}"
                               value="{{ reglas[i-1].max if reglas|length >= i else '' }}"
                               required>
                      </td>
                      <td>
                        <select class="form-select text-center" name="bajar_{{i}}">
                          <option value="0" {% if reglas|length >= i and reglas[i-1].bajar == 0 %}selected{% endif %}>0 niveles</option>
                          <option value="1" {% if reglas|length >= i and reglas[i-1].bajar == 1 %}selected{% endif %}>1 nivel</option>
                          <option value="2" {% if reglas|length >= i and reglas[i-1].bajar == 2 %}selected{% endif %}>2 niveles</option>
                          <option value="3" {% if reglas|length >= i and reglas[i-1].bajar == 3 %}selected{% endif %}>3 niveles</option>
                          <option value="4" {% if reglas|length >= i and reglas[i-1].bajar == 4 %}selected{% endif %}>4 niveles</option>
                        </select>
                      </td>
                    </tr>
                    {% endfor %}
                  </tbody>
                </table>
              </div>
            </div>

            <div class="imp-bottom-actions">
              <button type="submit" class="btn btn-success rounded-pill px-5 py-2 fw-bold">
                💾 Guardar configuración
              </button>

              <a href="{{ url_for('gestion_riesgos') }}"
                 class="btn rounded-pill px-5 py-2 fw-bold imp-back-btn">
                ⬅ Volver a Gestión de Riesgos
              </a>
            </div>

          </div>
        </div>
      </form>

    </div>

    <style>

      body{
        background-image:url('/static/img/ccsgsi.jpg') !important;
        background-size:cover !important;
        background-position:center !important;
        background-attachment:fixed !important;
        background-repeat:no-repeat !important;
        background-color:transparent !important;
      }

      .imp-shell{
        width:96%;
        max-width:1300px;
        margin:10px auto 24px auto;
      }

      /* =========================
         HERO SGSI COMPACTO
      ========================== */
      .imp-header-card{
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

      .imp-header-card::before{
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
        pointer-events:none;
      }

      .imp-header-overlay{
        width:100%;
        height:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        padding:0;
        background:transparent;
        position:relative;
        z-index:1;
      }

      .imp-header-overlay::before{
        content:"📉";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:rgba(255,255,255,.96);
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.55rem;
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .imp-header-text{
        max-width:1000px;
        position:relative;
        z-index:1;
      }

      .imp-header-text::before{
        content:"SGSI · Impacto Residual";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border:1px solid rgba(255,255,255,.30);
        border-radius:999px;
        padding:3px 10px;
        font-size:.66rem;
        font-weight:800;
        letter-spacing:.35px;
        margin-bottom:4px;
      }

      .imp-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.36rem;
        line-height:1.08;
        text-shadow:0 3px 10px rgba(0,0,0,.32);
        margin:0;
      }

      .imp-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      /* =========================
         ALERTAS
      ========================== */
      .imp-alert-card{
        margin-bottom:12px;
      }

      .imp-alert-card .alert{
        border-radius:14px;
        font-size:.82rem;
        font-weight:700;
        box-shadow:0 8px 18px rgba(15,23,42,.12);
      }

      /* =========================
         CARD TABLA
      ========================== */
      .imp-table-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        overflow:hidden;
        border:1px solid rgba(219,230,244,.9);
      }

      .imp-table-card-body{
        padding:8px 7px;
      }

      .imp-table-wrap{
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:rgba(255,255,255,.98);
        overflow:auto;
      }

      .imp-table{
        margin-bottom:0;
        font-size:.80rem;
      }

      .imp-table thead th{
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff;
        font-weight:900;
        text-align:center;
        vertical-align:middle;
        padding:11px 9px;
        font-size:.78rem;
        border-right:1px solid rgba(255,255,255,.28);
      }

      .imp-table td{
        vertical-align:middle;
        padding:9px 8px;
        font-size:.78rem;
        border-right:1px solid #dce6f3;
        border-bottom:1px solid #dce6f3;
        background:rgba(255,255,255,.98);
      }

      .imp-table tbody tr:nth-child(even) td{
        background:#f8fbff;
      }

      .imp-table tbody tr:hover td{
        background:#eef6ff;
      }

      .imp-table .form-control,
      .imp-table .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:36px;
        font-size:.78rem;
        box-shadow:none;
      }

      .imp-table .form-control:focus,
      .imp-table .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .18rem rgba(63,134,214,.18);
      }

      /* =========================
         BOTONES
      ========================== */
      .imp-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin-top:16px;
      }

      .imp-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 24px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .imp-bottom-actions .btn-primary{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .imp-bottom-actions .btn-success{
        border:none;
        background:linear-gradient(135deg,#12844b,#16a05d);
        color:#fff;
      }

      .imp-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .imp-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         SCROLL
      ========================== */
      .imp-table-wrap::-webkit-scrollbar{
        height:11px;
        width:11px;
      }

      .imp-table-wrap::-webkit-scrollbar-track{
        background:#dbe4f0;
        border-radius:12px;
      }

      .imp-table-wrap::-webkit-scrollbar-thumb{
        background:linear-gradient(180deg,#5aa3ea,#3f86d6);
        border-radius:12px;
      }

      /* =========================
         RESPONSIVE
      ========================== */
      @media(max-width:992px){
        .imp-shell{width:98%;}
        .imp-title{font-size:1.2rem;}
        .imp-subtitle{font-size:.74rem;}
        .imp-table-card-body{padding:12px;}
      }

      @media(max-width:768px){
        .imp-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .imp-header-overlay::before{
          margin-right:0;
        }

        .imp-bottom-actions .btn{
          width:100%;
        }
      }

    </style>
    """, reglas=reglas)

    return render_template_string(BASE, content=Markup(html))


# ===========================================================
# CONFIGURAR EVALUACIÓN Y EFICACIA DEL CONTROL
# ===========================================================
@app.route('/configurar_evaluacion_control', methods=['GET', 'POST'])
@login_required
def configurar_evaluacion_control():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede configurar parámetros.", "danger")
        return redirect(url_for('gestion_riesgos'))

    if user.role != 'admin' and not verificar_permiso(user, "Gestión de Riesgos"):
        flash("No tiene permiso para configurar parámetros.", "danger")
        return redirect(url_for('gestion_riesgos'))

    riesgo_asegurar_config_evaluacion_control()

    if request.method == 'POST':
        accion = (request.form.get('accion') or 'guardar').strip().lower()

        if accion == 'restablecer':
            db.session.query(ConfigEvaluacionControl).delete()
            db.session.commit()
            riesgo_asegurar_config_evaluacion_control()
            actualizados = riesgo_recalcular_matriz_existente(commit=True)
            flash(
                f"✅ Valores predeterminados restablecidos. {actualizados} riesgo(s) recalculado(s).",
                "success",
            )
            return redirect(url_for('configurar_evaluacion_control'))

        definiciones = {item['clave']: item for item in RISK_CONTROL_PARAMETER_DEFINITIONS}
        valores = {}
        errores = []
        for clave, definicion in definiciones.items():
            raw = request.form.get(f'pct_{clave}')
            numero = riesgo_float(raw, None)
            if numero is None:
                errores.append(f"Debe diligenciar el porcentaje de {definicion['grupo']} - {definicion['opcion']}.")
                continue
            if numero < 0 or numero > 100:
                errores.append(f"El porcentaje de {definicion['opcion']} debe estar entre 0 y 100.")
                continue
            valores[clave] = round(float(numero), 4)

        # El máximo alcanzable por el diseño debe representar exactamente 100 %.
        if not errores:
            maximo_diseno = sum(
                max(valores[clave] for clave in claves)
                for claves in RISK_CONTROL_DESIGN_GROUP_KEYS.values()
            )
            if abs(maximo_diseno - 100.0) > 0.01:
                errores.append(
                    f"La suma de los máximos de Diseño debe ser 100 %. Actualmente es {maximo_diseno:.2f} %."
                )

            total_formula = valores['formula_peso_diseno'] + valores['formula_peso_ejecucion']
            if abs(total_formula - 100.0) > 0.01:
                errores.append(
                    f"Los pesos de Diseño y Ejecución deben sumar 100 %. Actualmente suman {total_formula:.2f} %."
                )

        if errores:
            for error in errores:
                flash(error, 'danger')
        else:
            filas = {fila.clave: fila for fila in ConfigEvaluacionControl.query.all()}
            for clave, numero in valores.items():
                definicion = definiciones[clave]
                fila = filas.get(clave)
                if fila is None:
                    fila = ConfigEvaluacionControl(**definicion)
                    db.session.add(fila)
                fila.porcentaje = numero
                fila.grupo = definicion['grupo']
                fila.opcion = definicion['opcion']
                fila.orden = definicion['orden']

            db.session.commit()
            actualizados = riesgo_recalcular_matriz_existente(commit=True)
            flash(
                f"✅ Parámetros de Evaluación y Eficacia del Control guardados. "
                f"{actualizados} riesgo(s) recalculado(s).",
                'success',
            )
            return redirect(url_for('configurar_evaluacion_control'))

    filas_db = {fila.clave: fila for fila in ConfigEvaluacionControl.query.all()}
    grupos = []
    nombres_grupo = [
        'Asignación', 'Tipo de Control', 'Forma de Control', 'Funcionalidad',
        'Estado del Control', 'Evidencia del Control', 'Ejecución'
    ]
    for nombre in nombres_grupo:
        filas = []
        for definicion in RISK_CONTROL_PARAMETER_DEFINITIONS:
            if definicion['grupo'] != nombre:
                continue
            fila_db = filas_db.get(definicion['clave'])
            filas.append({
                **definicion,
                'porcentaje_actual': (
                    float(fila_db.porcentaje)
                    if fila_db is not None
                    else float(definicion['porcentaje'])
                ),
            })
        grupos.append({'nombre': nombre, 'filas': filas})

    formula = []
    for definicion in RISK_CONTROL_PARAMETER_DEFINITIONS:
        if definicion['grupo'] != 'Fórmula de Solidez Individual':
            continue
        fila_db = filas_db.get(definicion['clave'])
        formula.append({
            **definicion,
            'porcentaje_actual': (
                float(fila_db.porcentaje)
                if fila_db is not None
                else float(definicion['porcentaje'])
            ),
        })

    maximo_diseno_actual = sum(
        max(
            float(filas_db[clave].porcentaje) if clave in filas_db else next(
                float(item['porcentaje']) for item in RISK_CONTROL_PARAMETER_DEFINITIONS if item['clave'] == clave
            )
            for clave in claves
        )
        for claves in RISK_CONTROL_DESIGN_GROUP_KEYS.values()
    )

    html = render_template_string("""
    <div class="ctrlcfg-shell">
      <div class="ctrlcfg-header-card">
        <div class="ctrlcfg-header-overlay">
          <div class="ctrlcfg-header-icon">🧩</div>
          <div>
            <div class="ctrlcfg-kicker">SGSI · Parámetros de Riesgo</div>
            <h2 class="ctrlcfg-title">Evaluación y Eficacia del Control</h2>
            <div class="ctrlcfg-subtitle">
              Configure la puntuación de cada opción y los pesos utilizados para calcular la solidez individual y grupal.
            </div>
          </div>
        </div>
      </div>

      {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
          <div class="mb-3">
            {% for category, message in messages %}
              <div class="alert alert-{{ category if category in ['success','danger','warning','info'] else 'info' }} mb-2">{{ message }}</div>
            {% endfor %}
          </div>
        {% endif %}
      {% endwith %}

      <div class="ctrlcfg-info-card">
        <div><strong>Regla de validación:</strong> la suma de la mejor opción de cada componente de Diseño debe ser 100 %.</div>
        <div><strong>Diseño máximo actual:</strong> {{ '%.2f'|format(maximo_diseno_actual) }} %.</div>
        <div><strong>Campos informativos:</strong> Cargo, Frecuencia, Referencia Documental y Soporte de Evidencia no agregan puntuación.</div>
      </div>

      <form method="POST" id="controlParamsForm">
        <input type="hidden" name="accion" value="guardar">

        <div class="row g-3">
          {% for grupo in grupos %}
          <div class="col-lg-6">
            <div class="ctrlcfg-card h-100">
              <div class="ctrlcfg-card-title">{{ grupo.nombre }}</div>
              <div class="table-responsive">
                <table class="table align-middle mb-0 ctrlcfg-table">
                  <thead><tr><th>Opción</th><th class="text-center">Puntuación (%)</th></tr></thead>
                  <tbody>
                    {% for fila in grupo.filas %}
                    <tr>
                      <td class="fw-semibold">{{ fila.opcion }}</td>
                      <td style="width:180px">
                        <div class="input-group input-group-sm">
                          <input type="number" min="0" max="100" step="0.01"
                                 class="form-control text-end ctrlcfg-score"
                                 name="pct_{{ fila.clave }}"
                                 value="{{ '%.2f'|format(fila.porcentaje_actual) }}" required>
                          <span class="input-group-text">%</span>
                        </div>
                      </td>
                    </tr>
                    {% endfor %}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
          {% endfor %}
        </div>

        <div class="ctrlcfg-card mt-3">
          <div class="ctrlcfg-card-title">Fórmula de Solidez Individual</div>
          <div class="ctrlcfg-formula">
            {% for fila in formula %}
            <div class="ctrlcfg-formula-item">
              <label class="form-label fw-semibold">{{ fila.opcion }}</label>
              <div class="input-group">
                <input type="number" min="0" max="100" step="0.01"
                       class="form-control text-end ctrlcfg-formula-score"
                       name="pct_{{ fila.clave }}"
                       value="{{ '%.2f'|format(fila.porcentaje_actual) }}" required>
                <span class="input-group-text">%</span>
              </div>
            </div>
            {% endfor %}
          </div>
          <div class="ctrlcfg-formula-preview mt-3" id="formulaPreview">
            Solidez Individual = Diseño × 60 % + Ejecución × 40 %
          </div>
        </div>

        <div class="ctrlcfg-actions">
          <a href="{{ url_for('gestion_riesgos', ver='activos') }}" class="btn btn-outline-secondary rounded-pill px-4">⬅ Volver</a>
          <button type="button" class="btn btn-outline-danger rounded-pill px-4" onclick="restablecerParametrosControl()">↺ Restablecer valores</button>
          <button type="submit" class="btn btn-primary rounded-pill px-5 fw-bold">💾 Guardar y recalcular riesgos</button>
        </div>
      </form>

      <form method="POST" id="resetControlParamsForm" class="d-none">
        <input type="hidden" name="accion" value="restablecer">
      </form>
    </div>

    <style>
      body{background-image:url('/static/img/ccsgsi.jpg');background-size:cover;background-position:center;background-attachment:fixed}
      .ctrlcfg-shell{width:96%;max-width:1280px;margin:22px auto 30px}
      .ctrlcfg-header-card{background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);border-radius:20px;padding:18px 24px;color:#fff;box-shadow:0 14px 30px rgba(15,23,42,.25);margin-bottom:15px;position:relative;overflow:hidden}
      .ctrlcfg-header-card:before{content:"";position:absolute;inset:0;background:radial-gradient(circle at 90% 10%,rgba(255,255,255,.22),transparent 28%)}
      .ctrlcfg-header-overlay{position:relative;display:flex;align-items:center;gap:15px;z-index:1}
      .ctrlcfg-header-icon{width:56px;height:56px;min-width:56px;border-radius:16px;background:#fff;color:#0b4a8f;display:flex;align-items:center;justify-content:center;font-size:1.55rem;box-shadow:0 8px 20px rgba(0,0,0,.23)}
      .ctrlcfg-kicker{display:inline-block;background:rgba(255,255,255,.17);padding:4px 10px;border-radius:999px;font-size:.68rem;font-weight:900;margin-bottom:4px}
      .ctrlcfg-title{font-size:1.45rem;font-weight:950;margin:0;color:#fff!important}
      .ctrlcfg-subtitle{font-size:.82rem;opacity:.92;margin-top:3px}
      .ctrlcfg-info-card,.ctrlcfg-card{background:rgba(255,255,255,.97);border:1px solid #d7e5f5;border-radius:18px;box-shadow:0 10px 24px rgba(15,23,42,.12)}
      .ctrlcfg-info-card{padding:13px 18px;margin-bottom:15px;display:flex;flex-wrap:wrap;gap:10px 24px;font-size:.78rem;color:#475569}
      .ctrlcfg-card{padding:16px}
      .ctrlcfg-card-title{font-weight:950;color:#0b4a8f;border-bottom:1px solid #dce8f5;padding-bottom:9px;margin-bottom:8px}
      .ctrlcfg-table th{font-size:.70rem;color:#64748b;text-transform:uppercase;letter-spacing:.04em;background:#f4f8fd}
      .ctrlcfg-table td{font-size:.78rem;padding:.50rem .55rem}
      .ctrlcfg-formula{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px}
      .ctrlcfg-formula-preview{background:#eff6ff;border:1px solid #bfdbfe;border-radius:12px;padding:11px 15px;color:#1d4f8f;font-weight:900;text-align:center}
      .ctrlcfg-actions{display:flex;justify-content:center;flex-wrap:wrap;gap:10px;margin-top:18px}
      @media(max-width:768px){.ctrlcfg-formula{grid-template-columns:1fr}.ctrlcfg-actions .btn{width:100%}.ctrlcfg-header-overlay{align-items:flex-start}.ctrlcfg-title{font-size:1.20rem}}
    </style>

    <script>
      (function(){
        const designInput = document.querySelector('[name="pct_formula_peso_diseno"]');
        const executionInput = document.querySelector('[name="pct_formula_peso_ejecucion"]');
        const preview = document.getElementById('formulaPreview');
        function actualizarFormula(){
          const d = parseFloat(String(designInput?.value || 0).replace(',','.')) || 0;
          const e = parseFloat(String(executionInput?.value || 0).replace(',','.')) || 0;
          if(preview) preview.textContent = `Solidez Individual = Diseño × ${d.toFixed(2)} % + Ejecución × ${e.toFixed(2)} % · Total: ${(d+e).toFixed(2)} %`;
        }
        designInput?.addEventListener('input', actualizarFormula);
        executionInput?.addEventListener('input', actualizarFormula);
        actualizarFormula();
      })();

      function restablecerParametrosControl(){
        if(confirm('¿Desea restablecer todos los porcentajes predeterminados y recalcular los riesgos existentes?')){
          document.getElementById('resetControlParamsForm').submit();
        }
      }
    </script>
    """, grupos=grupos, formula=formula, maximo_diseno_actual=maximo_diseno_actual)

    return render_template_string(BASE, content=Markup(html))


# ==============================
# CONFIGURACIÓN TIPOS DE RIESGO
# ==============================
@app.route('/configurar_tipos_riesgo', methods=['GET','POST'])
@login_required
def configurar_tipos_riesgo():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede configurar parámetros.", "danger")
        return redirect(url_for('riesgos_menu'))

    if user.role != 'admin' and not verificar_permiso(user, "Gestión de Riesgos"):
        flash("No tiene permiso para configurar parámetros.", "danger")
        return redirect(url_for('riesgos_menu'))

    if request.method == 'POST':
        nombre = (request.form.get("nombre") or "").strip()
        if not nombre:
            flash("Debe ingresar un nombre para el Tipo de Riesgo.", "warning")
        else:
            existe = TipoRiesgo.query.filter(
                TipoRiesgo.owner_user_id == user.id,
                db.func.lower(TipoRiesgo.nombre) == nombre.lower()
            ).first()

            if existe:
                flash("Ese tipo de riesgo ya existe.", "warning")
            else:
                tr = TipoRiesgo(
                    nombre=nombre,
                    activo=True,
                    creado_por=session.get("username", "sistema"),
                    owner_user_id=user.id
                )
                db.session.add(tr)
                db.session.commit()
                flash("✅ Tipo de riesgo creado.", "success")
        return redirect(url_for("configurar_tipos_riesgo"))

    tipos = TipoRiesgo.query.filter_by(owner_user_id=user.id)\
        .order_by(TipoRiesgo.activo.desc(), TipoRiesgo.nombre.asc())\
        .all()

    html = """
    <div class="tipo-shell">

      <div class="tipo-header-card">
        <div class="tipo-header-overlay">
          <div class="tipo-header-text">
            <h2 class="tipo-title m-0">Configuración de Tipos de Riesgo</h2>
            <div class="tipo-subtitle">
              Administración de categorías de riesgo utilizadas en la gestión del SGSI
            </div>
          </div>
        </div>
      </div>

      <div class="tipo-form-card">
        <div class="tipo-form-card-body">

          <form method="POST" class="row g-3 align-items-end">
            <div class="col-md-9">
              <label class="form-label fw-semibold">Nuevo tipo de riesgo</label>
              <input class="form-control"
                     name="nombre"
                     placeholder="Ej: Operacional, Tecnológico, Legal, Estratégico">
            </div>

            <div class="col-md-3">
              <button class="btn btn-success w-100 rounded-pill fw-bold">
                ➕ Guardar tipo
              </button>
            </div>
          </form>

        </div>
      </div>

      <div class="tipo-table-card">
        <div class="tipo-table-card-body">

          <h5 class="mb-3 fw-bold">Listado de Tipos de Riesgo</h5>

          <div class="tipo-table-wrap">
            <div class="table-responsive">
              <table class="table table-bordered table-sm align-middle tipo-table mb-0">
                <thead>
                  <tr>
                    <th>Nombre</th>
                    <th style="width:160px;">Estado</th>
                    <th style="width:260px;">Acciones</th>
                  </tr>
                </thead>
                <tbody>

                  {% for t in tipos %}
                  <tr>
                    <td>{{ t.nombre }}</td>

                    <td class="text-center">
                      {% if t.activo %}
                        <span class="badge bg-success rounded-pill px-3 py-2">Activo</span>
                      {% else %}
                        <span class="badge bg-secondary rounded-pill px-3 py-2">Inactivo</span>
                      {% endif %}
                    </td>

                    <td class="text-center">
                      <a class="btn btn-warning btn-sm rounded-pill px-3"
                         href="/editar_tipo_riesgo/{{ t.id }}">
                         ✏️ Editar
                      </a>

                      {% if t.activo %}
                        <form method="POST"
                              action="/desactivar_tipo_riesgo/{{ t.id }}"
                              class="d-inline"
                              onsubmit="return confirm('¿Desactivar este tipo?');">
                          <button class="btn btn-secondary btn-sm rounded-pill px-3">
                            Desactivar
                          </button>
                        </form>
                      {% else %}
                        <form method="POST"
                              action="/activar_tipo_riesgo/{{ t.id }}"
                              class="d-inline"
                              onsubmit="return confirm('¿Activar este tipo?');">
                          <button class="btn btn-success btn-sm rounded-pill px-3">
                            Activar
                          </button>
                        </form>
                      {% endif %}
                    </td>
                  </tr>
                  {% endfor %}

                  {% if tipos|length == 0 %}
                  <tr>
                    <td colspan="3" class="text-center text-muted">
                      Aún no hay tipos de riesgo configurados.
                    </td>
                  </tr>
                  {% endif %}

                </tbody>
              </table>
            </div>
          </div>

        </div>
      </div>

      <div class="tipo-bottom-actions">
        <a href="/riesgos"
           class="btn rounded-pill px-5 py-2 fw-bold tipo-back-btn">
           ⬅ Volver a Gestión de Riesgos
        </a>
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

      .tipo-shell{
        width:96%;
        max-width:1300px;
        margin:10px auto 24px auto;
      }

      /* =========================
         HERO SGSI COMPACTO
      ========================== */
      .tipo-header-card{
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

      .tipo-header-card::before{
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
        pointer-events:none;
      }

      .tipo-header-overlay{
        width:100%;
        height:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        padding:0;
        background:transparent;
        position:relative;
        z-index:1;
      }

      .tipo-header-overlay::before{
        content:"🏷️️";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:rgba(255,255,255,.96);
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.55rem;
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .tipo-header-text{
        max-width:1000px;
        position:relative;
        z-index:1;
      }

      .tipo-header-text::before{
        content:"SGSI · Tipos de Riesgo";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border:1px solid rgba(255,255,255,.30);
        border-radius:999px;
        padding:3px 10px;
        font-size:.66rem;
        font-weight:800;
        letter-spacing:.35px;
        margin-bottom:4px;
      }

      .tipo-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.36rem;
        line-height:1.08;
        text-shadow:0 3px 10px rgba(0,0,0,.32);
        margin:0;
      }

      .tipo-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
        text-shadow:none;
      }

      /* =========================
         FORMULARIO / TABLA
      ========================== */
      .tipo-form-card,
      .tipo-table-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        margin-bottom:14px;
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .tipo-form-card-body,
      .tipo-table-card-body{
        padding:8px 7px;
      }

      .tipo-form-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .tipo-form-card .form-control{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:37px;
        font-size:.80rem;
        box-shadow:none;
        padding-top:5px;
        padding-bottom:5px;
      }

      .tipo-form-card .form-control:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .18rem rgba(63,134,214,.18);
      }

      .tipo-form-card .btn{
        border-radius:10px !important;
        min-height:37px;
        padding:7px 20px !important;
        font-size:.80rem;
        font-weight:900;
        box-shadow:0 7px 14px rgba(15,23,42,.14);
      }

      .tipo-form-card .btn-primary,
      .tipo-form-card .btn-success{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .tipo-table-wrap{
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:rgba(255,255,255,.98);
        overflow:auto;
      }

      .tipo-table{
        margin-bottom:0;
        font-size:.80rem;
      }

      .tipo-table thead th{
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff;
        font-weight:900;
        text-align:center;
        vertical-align:middle;
        padding:11px 9px;
        font-size:.78rem;
        border-right:1px solid rgba(255,255,255,.28);
      }

      .tipo-table td{
        vertical-align:middle;
        padding:9px 8px;
        font-size:.78rem;
        border-right:1px solid #dce6f3;
        border-bottom:1px solid #dce6f3;
        background:rgba(255,255,255,.98);
      }

      .tipo-table tbody tr:nth-child(even) td{
        background:#f8fbff;
      }

      .tipo-table tbody tr:hover td{
        background:#eef6ff;
      }

      .tipo-table .btn{
        border-radius:999px !important;
        min-height:28px;
        padding:4px 12px !important;
        font-size:.70rem;
        font-weight:900;
      }

      /* =========================
         BOTÓN VOLVER
      ========================== */
      .tipo-bottom-actions{
        text-align:center;
        margin-top:16px;
      }

      .tipo-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 24px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .tipo-back-btn{
        background:#ffffff;
        border:1px solid #cfd8e3;
        color:#0f172a;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .tipo-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         SCROLL
      ========================== */
      .tipo-table-wrap::-webkit-scrollbar{
        height:11px;
        width:11px;
      }

      .tipo-table-wrap::-webkit-scrollbar-track{
        background:#dbe4f0;
        border-radius:12px;
      }

      .tipo-table-wrap::-webkit-scrollbar-thumb{
        background:linear-gradient(180deg,#5aa3ea,#3f86d6);
        border-radius:12px;
        border:2px solid #dbe4f0;
      }

      .tipo-table-wrap{
        scrollbar-width:thin;
        scrollbar-color:#3f86d6 #dbe4f0;
      }

      /* =========================
         RESPONSIVE
      ========================== */
      @media(max-width:992px){
        .tipo-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .tipo-header-card{
          min-height:88px;
          padding:15px 18px;
        }

        .tipo-title{
          font-size:1.22rem;
        }

        .tipo-subtitle{
          font-size:.74rem;
        }

        .tipo-form-card-body,
        .tipo-table-card-body{
          padding:12px;
        }
      }

      @media(max-width:768px){
        .tipo-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .tipo-header-overlay::before{
          margin-right:0;
        }

        .tipo-title{
          font-size:1.12rem;
        }

        .tipo-subtitle{
          font-size:.72rem;
        }

        .tipo-bottom-actions .btn,
        .tipo-form-card .btn{
          width:100%;
        }
      }
    </style>
    """
    return render_template_string(BASE, content=Markup(render_template_string(html, tipos=tipos)))

@app.route("/tipos_riesgo/agregar", methods=["POST"])
@login_required
def tipos_riesgo_agregar():
    user_id = session.get("user_id")
    if not user_id:
        flash("Sesión inválida: falta user_id. Inicia sesión de nuevo.", "danger")
        return redirect(url_for("login"))

    nombre = (request.form.get("nombre") or "").strip()
    if not nombre:
        flash("Debe ingresar el nombre del tipo de riesgo.", "warning")
        return redirect(url_for("gestion_riesgos"))

    t = TipoRiesgo(
        nombre=nombre,
        creado_por=session.get("username"),
        owner_user_id=user_id,   # ✅ ESTA ES LA LÍNEA CLAVE
        activo=True
    )
    db.session.add(t)
    db.session.commit()
    flash("✅ Tipo de riesgo creado.", "success")
    return redirect(url_for("gestion_riesgos"))

@app.route('/editar_tipo_riesgo/<int:id>', methods=['GET','POST'])
@login_required
def editar_tipo_riesgo(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("No permitido.", "danger")
        return redirect(url_for('riesgos_menu'))

    if user.role != 'admin' and not verificar_permiso(user, "Gestión de Riesgos"):
        flash("No tiene permiso.", "danger")
        return redirect(url_for('riesgos_menu'))

    t = TipoRiesgo.query.get_or_404(id)

    if request.method == 'POST':
        nombre = (request.form.get("nombre") or "").strip()
        if not nombre:
            flash("Nombre requerido.", "warning")
        else:
            existe = TipoRiesgo.query.filter(
                db.func.lower(TipoRiesgo.nombre) == nombre.lower(),
                TipoRiesgo.id != t.id
            ).first()

            if existe:
                flash("Ya existe otro tipo con ese nombre.", "warning")
            else:
                t.nombre = nombre
                db.session.commit()
                flash("✅ Actualizado.", "success")
                return redirect(url_for("configurar_tipos_riesgo"))

    html = """
    <div class="tipoedit-shell">

      <!-- =========================
           CABECERA
      ========================== -->
      <div class="tipoedit-header-card">
        <div class="tipoedit-header-overlay">
          <div class="tipoedit-header-text">
            <h2 class="tipoedit-title m-0">✏️ Editar Tipo de Riesgo</h2>
            <div class="tipoedit-subtitle">
              Actualización de la categoría de riesgo utilizada en la gestión del SGSI
            </div>
          </div>
        </div>
      </div>

      <!-- =========================
           FORMULARIO
      ========================== -->
      <div class="tipoedit-form-card">
        <div class="tipoedit-form-card-body">

          <form method="POST">
            <div class="row g-3">
              <div class="col-12">
                <label class="form-label fw-semibold">Nombre</label>
                <input class="form-control"
                       name="nombre"
                       value="{{ t.nombre }}"
                       placeholder="Ej: Operacional, Tecnológico, Legal, Estratégico"
                       required>
              </div>
            </div>

            <div class="tipoedit-bottom-actions">
              <button class="btn btn-primary rounded-pill px-5 py-2 fw-bold">
                Guardar
              </button>

              <a href="{{ url_for('configurar_tipos_riesgo') }}"
                 class="btn rounded-pill px-5 py-2 fw-bold tipoedit-back-btn">
                Cancelar
              </a>
            </div>
          </form>

        </div>
      </div>

    </div>

    <style>
      body{
        background-image: url('/static/img/ccsgsi.jpg');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        background-repeat: no-repeat;
      }

      .tipoedit-shell{
        width: 96%;
        max-width: 1000px;
        margin: 8px auto 30px auto;
      }

      .tipoedit-header-card{
        background: linear-gradient(135deg, #2f6fb6 0%, #3f86d6 55%, #5aa3ea 100%);
        height: 88px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 18px;
        box-shadow: 0 12px 30px rgba(0,0,0,.30);
        position: relative;
        overflow: hidden;
        margin-bottom: 14px;
      }

      .tipoedit-header-overlay{
        width: 100%;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 8px 24px;
        background: rgba(0,0,0,.08);
      }

      .tipoedit-header-text{
        max-width: 900px;
      }

      .tipoedit-title{
        color: #ffffff !important;
        font-weight: 900;
        font-size: 1.38rem;
        line-height: 1.15;
        text-shadow: 0 4px 14px rgba(0,0,0,.45);
        margin: 0;
      }

      .tipoedit-subtitle{
        color: rgba(255,255,255,.96);
        font-size: .82rem;
        margin-top: 4px;
        text-shadow: 0 2px 8px rgba(0,0,0,.35);
      }

      .tipoedit-form-card{
        background: rgba(248,252,255,.96);
        border-radius: 18px;
        backdrop-filter: blur(6px);
        box-shadow: 0 10px 24px rgba(0,0,0,.18);
        overflow: hidden;
      }

      .tipoedit-form-card-body{
        padding: 22px;
      }

      .tipoedit-form-card .form-label{
        color: #101827;
        margin-bottom: 6px;
      }

      .tipoedit-form-card .form-control{
        border-radius: 10px;
        border: 1px solid #cfd8e3;
        min-height: 44px;
      }

      .tipoedit-form-card .form-control:focus{
        border-color: #3f86d6;
        box-shadow: 0 0 0 0.2rem rgba(63,134,214,.18);
      }

      .tipoedit-bottom-actions{
        display: flex;
        justify-content: center;
        gap: 12px;
        flex-wrap: wrap;
        margin-top: 22px;
      }

      .tipoedit-back-btn{
        background: #ffffff;
        color: #000000;
        border: 2px solid #ffffff;
        box-shadow: 0 4px 10px rgba(0,0,0,.10);
      }

      .tipoedit-back-btn:hover{
        background: #f3f4f6;
        color: #000000;
        border-color: #f3f4f6;
      }

      @media (max-width: 992px){
        .tipoedit-shell{
          width: 98%;
          margin: 6px auto 24px auto;
        }

        .tipoedit-header-card{
          height: 84px;
        }

        .tipoedit-title{
          font-size: 1.20rem;
        }

        .tipoedit-subtitle{
          font-size: .76rem;
        }

        .tipoedit-form-card-body{
          padding: 14px;
        }
      }
    </style>
    """
    return render_template_string(BASE, content=Markup(render_template_string(html, t=t)))

@app.post('/desactivar_tipo_riesgo/<int:id>')
@login_required
def desactivar_tipo_riesgo(id):
    t = TipoRiesgo.query.get_or_404(id)
    t.activo = False
    db.session.commit()
    flash("Tipo desactivado.", "success")
    return redirect(url_for("configurar_tipos_riesgo"))

@app.post('/activar_tipo_riesgo/<int:id>')
@login_required
def activar_tipo_riesgo(id):
    t = TipoRiesgo.query.get_or_404(id)
    t.activo = True
    db.session.commit()
    flash("Tipo activado.", "success")
    return redirect(url_for("configurar_tipos_riesgo"))

# ===========================
# MAPA CALOR
# ===========================
@app.route('/mapa_calor')
@login_required
def mapa_calor():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        solo_lectura = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Gestión de Riesgos"):
            flash("No tiene permiso para ver la Gestión de Riesgos.", "danger")
            return redirect(url_for('riesgos_menu'))
        solo_lectura = False

    try:
        riesgos_db = Riesgo.query.filter_by(archivado=False).all()
    except Exception:
        riesgos_db = Riesgo.query.all()

    niveles = [
        "Rara vez o Muy baja",
        "Eventualmente o Baja",
        "Puede ocurrir o Moderada",
        "Probable o Alta",
        "Muy frecuente o Muy Alta"
    ]

    impacto_niveles = [
        "Insignificante o Inferior",
        "Menor",
        "Moderado o Importante",
        "Mayor",
        "Catastrófico o Crítico"
    ]

    colorPorValor = [
        {"min": 1,  "max": 4,  "class": "nivel1", "color": "#2ecc71"},
        {"min": 5,  "max": 8,  "class": "nivel2", "color": "#f1c40f"},
        {"min": 9,  "max": 12, "class": "nivel3", "color": "#ff69b4"},
        {"min": 13, "max": 20, "class": "nivel4", "color": "#e74c3c"},
        {"min": 21, "max": 25, "class": "nivel5", "color": "#8e44ad"},
    ]

    color_ranges = [
        {
            "min": c["min"],
            "max": c["max"],
            "class": c["class"],
            "color": c["color"]
        }
        for c in colorPorValor
    ]

    def normalizar(etiqueta, tipo="prob"):
        if not etiqueta:
            return niveles[0] if tipo == "prob" else impacto_niveles[0]

        e = str(etiqueta).strip().lower()

        if tipo == "prob":
            if "rara" in e or "muy baja" in e or e == "1":
                return "Rara vez o Muy baja"
            if "eventual" in e or "baja" in e or e == "2":
                return "Eventualmente o Baja"
            if "moderada" in e or "puede ocurrir" in e or e == "3":
                return "Puede ocurrir o Moderada"
            if "alta" in e or "probable" in e or e == "4":
                return "Probable o Alta"
            if "muy frecuente" in e or "muy alta" in e or e == "5":
                return "Muy frecuente o Muy Alta"

        if tipo == "imp":
            if "insignificante" in e or "inferior" in e or e == "1":
                return "Insignificante o Inferior"
            if "menor" in e or e == "2":
                return "Menor"
            if "moderado" in e or "importante" in e or e == "3":
                return "Moderado o Importante"
            if "mayor" in e or e == "4":
                return "Mayor"
            if "catastrófico" in e or "catastrofico" in e or "crítico" in e or "critico" in e or e == "5":
                return "Catastrófico o Crítico"

        return niveles[0] if tipo == "prob" else impacto_niveles[0]

    matriz = {p: {i: [] for i in impacto_niveles} for p in niveles}
    riesgos_json = []

    for r in riesgos_db:
        prob_text = normalizar(
            getattr(r, "prob_res", "") or getattr(r, "cuadrante_prob", ""),
            "prob"
        )

        impacto_text = normalizar(
            getattr(r, "impacto_res_label", "") or getattr(r, "cuadrante_imp", ""),
            "imp"
        )

        detalle_url = url_for("riesgo_detalle", riesgo_id=r.id)

        item = {
            "id": r.id,
            "codigo_riesgo": r.codigo_riesgo or "",
            "riesgo": r.riesgo or "",
            "nombre_activo": getattr(r, "nombre_activo", "") or "",
            "riesgo_residual": getattr(r, "riesgo_residual", "") or "",
            "propietario": getattr(r, "propietario_riesgo", "") or "",
            "detalle_url": detalle_url
        }

        if prob_text in niveles and impacto_text in impacto_niveles:
            matriz[prob_text][impacto_text].append(item)

        riesgos_json.append({
            "id": r.id,
            "codigo_riesgo": r.codigo_riesgo or "",
            "riesgo": r.riesgo or "",
            "nombre_activo": getattr(r, "nombre_activo", "") or "",
            "prob_res": prob_text,
            "impacto_res": impacto_text,
            "riesgo_residual": getattr(r, "riesgo_residual", "") or "",
            "propietario": getattr(r, "propietario_riesgo", "") or "",
            "detalle_url": detalle_url
        })

    html = render_template_string("""
    <div class="heat-shell">

      <div class="heat-header-card">
        <div class="heat-header-overlay">
          <div class="heat-header-text">
            <h2 class="heat-title m-0">🌡️ Mapa de Calor</h2>
            <div class="heat-subtitle">
              Visualización de la distribución de riesgos residuales por probabilidad e impacto
            </div>
          </div>
        </div>
      </div>

      <div class="heat-header-actions">
        <a class="heat-back-btn" href="{{ url_for('gestion_riesgos') }}">
          ⬅ Volver a Gestión de Riesgos
        </a>
      </div>

      <div class="heat-card">
        <div class="heat-card-body">
          <div class="heat-table-wrap">

            <table id="heatmap" class="heatmap-table">

              <colgroup>
                <col class="col-axis">
                <col class="col-prob">
                {% for imp in impacto_niveles %}
                  <col class="col-impact">
                {% endfor %}
              </colgroup>

              <thead>
                <tr>
                  <th class="heat-corner-fill" colspan="2" rowspan="2"></th>
                  <th class="heat-axis-impacto" colspan="{{ impacto_niveles|length }}">
                    IMPACTO
                  </th>
                </tr>

                <tr>
                  {% for imp in impacto_niveles %}
                    <th class="heat-impact-header">{{ imp }}</th>
                  {% endfor %}
                </tr>
              </thead>

              <tbody>
                {% for prob in niveles %}
                <tr>
                  {% if loop.first %}
                    <th class="heat-axis-probabilidad" rowspan="{{ niveles|length }}">
                      <span>PROBABILIDAD</span>
                    </th>
                  {% endif %}

                  <th class="heat-prob-header">{{ prob }}</th>

                  {% for imp in impacto_niveles %}
                    <td class="cell"
                        data-prob="{{ prob }}"
                        data-imp="{{ imp }}"
                        id="cell-{{ prob }}-{{ imp }}">
                    </td>
                  {% endfor %}
                </tr>
                {% endfor %}
              </tbody>

            </table>

          </div>
        </div>
      </div>

      <div class="heat-legend-card">
        <div class="heat-legend-body">
          <div class="heat-legend-title">Leyenda de niveles</div>

          <div class="legend">
            <span class="nivel1">Bajo (1-4)</span>
            <span class="nivel2">Medio (5-8)</span>
            <span class="nivel3">Alto (9-12)</span>
            <span class="nivel4">Muy Alto (13-20)</span>
            <span class="nivel5">Extremo (21-25)</span>
          </div>
        </div>
      </div>

    </div>

    <div id="modal" class="modal">
      <div class="box">
        <button type="button" class="close" onclick="cerrarModal()" aria-label="Cerrar">✕</button>
        <h3 id="modalTitle">Riesgos</h3>
        <ul id="modalList" class="rlist"></ul>
      </div>
    </div>

    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg') !important;
        background-size:cover !important;
        background-position:center !important;
        background-attachment:fixed !important;
        background-repeat:no-repeat !important;
      }

      .heat-shell{
        width:96%;
        max-width:1450px;
        margin:10px auto 24px auto;
      }

      .heat-header-card{
        background:linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
        border-radius:18px;
        padding:16px 24px;
        min-height:94px;
        display:flex;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 24px rgba(15,23,42,.24);
        position:relative;
        overflow:hidden;
        margin-bottom:10px;
        color:#fff;
      }

      .heat-header-card::before{
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

      .heat-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        gap:14px;
        position:relative;
        z-index:1;
      }

      .heat-header-overlay::before{
        content:"🌡️";
        width:54px;
        height:54px;
        border-radius:14px;
        background:#fff;
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.5rem;
        box-shadow:0 8px 18px rgba(0,0,0,.2);
      }

      .heat-header-text::before{
        content:"SGSI · Análisis de Riesgo";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
      }

      .heat-title{
        font-size:1.32rem;
        font-weight:950;
        margin:0;
      }

      .heat-subtitle{
        font-size:.78rem;
        opacity:.9;
      }

      .heat-header-actions{
        display:flex;
        justify-content:center;
        margin-bottom:12px;
      }

      .heat-back-btn{
        border-radius:10px;
        padding:8px 20px;
        font-size:.8rem;
        font-weight:900;
        background:#fff;
        border:1px solid #cfd8e3;
        text-decoration:none;
        color:#101827;
      }

      .heat-back-btn:hover{
        background:#eef4ff;
        color:#0b65d8;
      }

      .heat-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        margin-bottom:14px;
      }

      .heat-card-body{
        padding:8px 7px;
      }

      .heat-table-wrap{
        background:#fff;
        border-radius:14px;
        border:1px solid #dbe6f4;
        padding:12px;
        overflow:auto;
      }

      table.heatmap-table{
        margin:auto;
        border-collapse:separate;
        border-spacing:4px;
        table-layout:fixed;
      }

      .heatmap-table col.col-axis{
        width:64px;
      }

      .heatmap-table col.col-prob{
        width:140px;
      }

      .heatmap-table col.col-impact{
        width:140px;
      }

      .heatmap-table th,
      .heatmap-table td{
        height:95px;
        border-radius:10px;
        text-align:center;
        font-size:.78rem;
      }

      .heatmap-table th{
        background:#eaf3ff;
        font-weight:900;
        color:#101827;
      }

      .heat-corner-fill{
        background:linear-gradient(135deg,#2f6fb6 0%,#3f86d6 55%,#5aa3ea 100%) !important;
        color:#fff !important;
        border-radius:12px !important;
        box-shadow:0 8px 18px rgba(47,111,182,.24);
        border:none !important;
        height:95px !important;
      }

      .heat-axis-impacto{
        height:42px !important;
        background:linear-gradient(135deg,#2f6fb6,#3f86d6,#5aa3ea) !important;
        color:#fff !important;
        font-size:.98rem !important;
        letter-spacing:.08em;
        text-transform:uppercase;
        border-radius:12px !important;
        box-shadow:0 8px 18px rgba(47,111,182,.24);
      }

      .heat-axis-probabilidad{
        width:64px !important;
        min-width:64px !important;
        max-width:64px !important;
        background:linear-gradient(180deg,#2f6fb6,#3f86d6,#5aa3ea) !important;
        color:#fff !important;
        border-radius:14px !important;
        box-shadow:0 8px 18px rgba(47,111,182,.24);
      }

      .heat-axis-probabilidad span{
        writing-mode:vertical-rl;
        transform:rotate(180deg);
        display:inline-block;
        letter-spacing:.08em;
        text-transform:uppercase;
        font-size:.82rem;
      }

      .heat-impact-header{
        background:#eaf3ff !important;
        color:#101827 !important;
        font-weight:950 !important;
        line-height:1.25;
      }

      .heat-prob-header{
        background:#eaf3ff !important;
        color:#101827 !important;
        font-weight:950 !important;
        line-height:1.25;
      }

      .heatmap-table td.cell{
        cursor:pointer;
        font-weight:800;
        transition:.2s;
        background:#fff;
      }

      .heatmap-table td.cell:hover{
        transform:scale(1.05);
        box-shadow:0 6px 14px rgba(0,0,0,.2);
      }

      .nivel1{background:#2ecc71 !important;color:#fff;}
      .nivel2{background:#f1c40f !important;color:#111;}
      .nivel3{background:#ff69b4 !important;color:#111;}
      .nivel4{background:#e74c3c !important;color:#fff;}
      .nivel5{background:#8e44ad !important;color:#fff;}

      .heat-legend-card{
        background:#fff;
        border-radius:18px;
        box-shadow:0 12px 24px rgba(15,23,42,.18);
      }

      .heat-legend-body{
        padding:8px 7px;
        text-align:center;
      }

      .heat-legend-title{
        font-size:.82rem;
        font-weight:950;
        color:#101827;
        margin-bottom:8px;
      }

      .legend{
        display:flex;
        justify-content:center;
        flex-wrap:wrap;
        gap:6px;
      }

      .legend span{
        padding:6px 10px;
        border-radius:999px;
        font-size:.78rem;
        font-weight:800;
      }

      .modal{
        display:none;
        position:fixed;
        inset:0;
        background:rgba(0,0,0,.55);
        z-index:99999;
        padding:20px;
        align-items:center;
        justify-content:center;
      }

      .modal .box{
        position:relative;
        background:#fff;
        width:min(760px,92vw);
        padding:18px;
        border-radius:16px;
        box-shadow:0 20px 50px rgba(0,0,0,.3);
        max-height:78vh;
        overflow:auto;
        margin:0 auto;
      }

      .modal h3{
        font-size:1rem;
        font-weight:900;
        margin-bottom:12px;
        color:#101827;
      }

      .close{
        position:absolute;
        top:10px;
        right:10px;
        border:none;
        background:#eef2f7;
        border-radius:50%;
        width:30px;
        height:30px;
        cursor:pointer;
        font-weight:900;
      }

      .close:hover{
        background:#dbe6f4;
      }

      ul.rlist{
        list-style:none;
        padding:0;
        margin:0;
      }

      ul.rlist li{
        background:#f8fafc;
        padding:10px;
        border-radius:12px;
        margin-bottom:8px;
        font-size:.8rem;
        border:1px solid #dbe6f4;
        cursor:pointer;
        transition:.18s ease;
      }

      ul.rlist li:hover{
        background:#eef6ff;
        transform:translateY(-2px);
        box-shadow:0 8px 18px rgba(15,23,42,.12);
      }

      .risk-detail-link{
        color:#1476ef;
        font-weight:950;
        display:inline-block;
        margin-top:6px;
      }

      @media(max-width:992px){
        .heat-shell{
          width:98%;
        }

        .heat-title{
          font-size:1.2rem;
        }

        .heatmap-table col.col-axis{
          width:56px;
        }

        .heatmap-table col.col-prob,
        .heatmap-table col.col-impact{
          width:110px;
        }

        .heatmap-table th,
        .heatmap-table td{
          height:85px;
        }

        .heat-axis-probabilidad{
          width:56px !important;
          min-width:56px !important;
          max-width:56px !important;
        }
      }
    </style>

    <script>
      const riesgos = {{ riesgos_json|tojson }};
      const matrizServidor = {{ matriz|tojson }};
      const colorRanges = {{ color_ranges|tojson }};

      function escapeHtml(text){
        return String(text || "")
          .replaceAll("&", "&amp;")
          .replaceAll("<", "&lt;")
          .replaceAll(">", "&gt;")
          .replaceAll('"', "&quot;")
          .replaceAll("'", "&#039;");
      }

      function clasePorValor(valor) {
        for (let i = 0; i < colorRanges.length; i++) {
          const r = colorRanges[i];
          if (valor >= r.min && valor <= r.max) {
            return r.class;
          }
        }
        return "nivel5";
      }

      function pintarMapa(){
        for (const prob of Object.keys(matrizServidor)) {
          for (const imp of Object.keys(matrizServidor[prob])) {
            const cell = document.getElementById(`cell-${prob}-${imp}`);
            const lista = matrizServidor[prob][imp] || [];

            if (!cell) continue;

            if (lista.length === 0) {
              cell.innerHTML = "<small style='color:#777'>-</small>";
              continue;
            }

            const map = {
              "Rara vez o Muy baja": 1,
              "Eventualmente o Baja": 2,
              "Puede ocurrir o Moderada": 3,
              "Probable o Alta": 4,
              "Muy frecuente o Muy Alta": 5,
              "Insignificante o Inferior": 1,
              "Menor": 2,
              "Moderado o Importante": 3,
              "Mayor": 4,
              "Catastrófico o Crítico": 5
            };

            const valor = Number(map[prob] || 1) * Number(map[imp] || 1);
            const clase = clasePorValor(valor);

            cell.classList.add(clase);

            cell.innerHTML = `
              <div>${lista.length} riesgo(s)</div>
              <div style="font-size:12px;margin-top:6px">
                ${escapeHtml(lista[0].riesgo || lista[0].nombre_activo || '')}
              </div>
            `;

            cell.addEventListener('click', () => abrirModal(prob, imp, lista));
          }
        }
      }

      function abrirModal(prob, imp, lista){
        const modal = document.getElementById('modal');
        const title = document.getElementById('modalTitle');
        const list = document.getElementById('modalList');

        title.innerText = `Riesgos — ${prob} / ${imp} (${lista.length})`;
        list.innerHTML = '';

        lista.forEach(it => {
          const li = document.createElement('li');

          li.onclick = function(){
            window.location.href = it.detalle_url;
          };

          li.innerHTML = `
            <b>${escapeHtml(it.codigo_riesgo || 'Sin código')}</b>
            —
            ${escapeHtml(it.riesgo || it.nombre_activo || 'Sin título')}
            <br>
            <small>
              Activo: ${escapeHtml(it.nombre_activo || '—')}
              |
              Residual: ${escapeHtml(it.riesgo_residual || '—')}
              |
              Prop.: ${escapeHtml(it.propietario || '—')}
            </small>
            <br>
            <span class="risk-detail-link">🔎 Ver detalle del riesgo →</span>
          `;

          list.appendChild(li);
        });

        modal.style.display = 'flex';
      }

      function cerrarModal(){
        document.getElementById('modal').style.display = 'none';
      }

      window.onclick = (e) => {
        if (e.target.id === 'modal') {
          cerrarModal();
        }
      };

      document.addEventListener("DOMContentLoaded", pintarMapa);
    </script>
    """,
    niveles=niveles,
    impacto_niveles=impacto_niveles,
    matriz=matriz,
    riesgos_json=riesgos_json,
    color_ranges=color_ranges
    )

    return render_template_string(BASE, content=Markup(html))

# ======================================
# DETALLE DE RIESGO (MISMO ESTILO AGREGAR)
# ======================================
@app.route('/riesgos/detalle/<int:riesgo_id>')
@login_required
def riesgo_detalle(riesgo_id):
    user = User.query.get(session.get('user_id'))

    if user.role != 'auditor':
        if user.role != 'admin' and not verificar_permiso(user, "Gestión de Riesgos"):
            flash("No tiene permiso para ver el detalle del riesgo.", "danger")
            return redirect(url_for('riesgos_menu'))

    riesgo = Riesgo.query.get_or_404(riesgo_id)

    tipo_riesgo_nombre = ""
    try:
        if hasattr(riesgo, "tipo_riesgo_rel") and riesgo.tipo_riesgo_rel:
            tipo_riesgo_nombre = riesgo.tipo_riesgo_rel.nombre
        elif hasattr(riesgo, "tipo_riesgo") and riesgo.tipo_riesgo:
            tipo_riesgo_nombre = riesgo.tipo_riesgo
        else:
            tipo_riesgo_nombre = ""
    except Exception:
        tipo_riesgo_nombre = ""

    def color_por_valor(valor):
        if valor is None or str(valor).strip() == "":
            return ""
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
        return ""

    detalle_html = """
    <div class="riskform-shell">

      <div class="riskform-header-card">
        <div class="riskform-header-overlay">
          <div class="riskform-header-text">
            <h3 class="riskform-title m-0">📄 Detalle del Riesgo - Gestión de Riesgos</h3>
            <div class="riskform-subtitle">
              Consulta detallada del riesgo, análisis, valoración, controles y tratamiento del riesgo registrado
            </div>
          </div>
        </div>
      </div>

      <form class="riskform-card">
        <div class="riskform-card-body">
          <div class="row g-3">

            <div class="col-12">
              <div class="riskform-section-title">🧩 Identificación del Riesgo</div>
            </div>

            <div class="col-md-3">
              <label class="form-label">Código de Riesgo</label>
              <input class="form-control" value="{{ riesgo.codigo_riesgo or '' }}" readonly>
            </div>
            <div class="col-md-3">
              <label class="form-label">Riesgo</label>
              <input class="form-control" value="{{ riesgo.riesgo or '' }}" readonly>
            </div>
            <div class="col-md-3">
              <label class="form-label">Tipo de Riesgo</label>
              <input class="form-control" value="{{ tipo_riesgo_nombre }}" readonly>
            </div>
            <div class="col-md-3">
              <label class="form-label">Fecha de Identificación</label>
              <input class="form-control" value="{{ riesgo.fecha_identificacion or '' }}" readonly>
            </div>
            <div class="col-md-3">
              <label class="form-label">Propietario del Riesgo</label>
              <input class="form-control" value="{{ riesgo.propietario_riesgo or '' }}" readonly>
            </div>

            <div class="col-12">
              <div class="riskform-section-title">🧩 Análisis</div>
            </div>

            <div class="col-md-3">
              <label class="form-label">Código Amenaza</label>
              <input class="form-control" value="{{ riesgo.codigo_amenaza or '' }}" readonly>
            </div>
            <div class="col-md-3">
              <label class="form-label">Amenaza</label>
              <input class="form-control" value="{{ riesgo.amenaza or '' }}" readonly>
            </div>
            <div class="col-md-3">
              <label class="form-label">Código Vulnerabilidad</label>
              <input class="form-control" value="{{ riesgo.codigo_vulnerabilidad or '' }}" readonly>
            </div>
            <div class="col-md-3">
              <label class="form-label">Vulnerabilidad</label>
              <input class="form-control" value="{{ riesgo.vulnerabilidad or '' }}" readonly>
            </div>

            <div class="col-md-3">
              <label class="form-label">Tipo de Activo</label>
              <input class="form-control" value="{{ riesgo.tipo_activo or '' }}" readonly>
            </div>
            <div class="col-md-3">
              <label class="form-label">Nombre del Activo</label>
              <input class="form-control" value="{{ riesgo.nombre_activo or '' }}" readonly>
            </div>
            <div class="col-md-3">
              <label class="form-label">Principio de Seguridad</label>
              <input class="form-control" value="{{ riesgo.dimension_seguridad or '' }}" readonly>
            </div>
            <div class="col-md-3">
              <label class="form-label">Estado</label>
              <input class="form-control" value="{{ riesgo.estado or '' }}" readonly>
            </div>

            <div class="col-12">
              <div class="riskform-section-title">🧩 Valoración del Riesgo Inherente</div>
            </div>

            <div class="col-md-3">
              <label class="form-label">Probabilidad Riesgo Inherente</label>
              <input class="form-control" value="{{ riesgo.prob_inh or '' }}" readonly>
            </div>
            <div class="col-md-3">
              <label class="form-label">Impacto Riesgo Inherente</label>
              <input class="form-control" value="{{ riesgo.imp_inh or '' }}" readonly>
            </div>
            <div class="col-md-3">
              <label class="form-label">Riesgo Inherente</label>
              <input class="form-control {{ color_por_valor(riesgo.riesgo_inherente) }}" value="{{ riesgo.riesgo_inherente or '' }}" readonly>
            </div>

            <div class="col-12">
              <div class="riskform-section-title">🧩 Controles Actuales - Evaluación Individual</div>
            </div>
            {{ controles_detalle_html|safe }}

            <div class="col-12">
              <div class="riskform-section-title">🧩 Evaluación del Riesgo Residual</div>
            </div>
            <div class="col-md-3">
              <label class="form-label">Solidez Grupal (Promedio)</label>
              <input class="form-control" value="{{ riesgo_formatear_porcentaje(riesgo.solidez_grupal or 0) }}" readonly>
            </div>
            <div class="col-md-3">
              <label class="form-label">Probabilidad Residual</label>
              <input class="form-control" value="{{ riesgo.cuadrante_prob or riesgo.prob_res or '' }}" readonly>
            </div>
            <div class="col-md-3">
              <label class="form-label">Impacto Residual</label>
              <input class="form-control" value="{{ riesgo.cuadrante_imp or riesgo.impacto_res_label or '' }}" readonly>
            </div>
            <div class="col-md-3">
              <label class="form-label">Riesgo Residual</label>
              <input class="form-control" value="{{ riesgo.riesgo_residual or '' }}" readonly>
            </div>
            <div class="col-md-3">
              <label class="form-label">Fecha de Revisión</label>
              <input class="form-control" value="{{ riesgo.fecha_revision or '' }}" readonly>
            </div>

            <div class="col-12">
              <div class="riskform-section-title">🧩 Tratamiento del Riesgo Residual</div>
            </div>

            <div class="col-md-12">
              <label class="form-label">Observaciones</label>
              <textarea class="form-control" readonly>{{ riesgo.observaciones or '' }}</textarea>
            </div>
            <div class="col-md-12">
              <label class="form-label">Planes de Acción</label>
              <textarea class="form-control" readonly>{{ riesgo.planes_accion or '' }}</textarea>
            </div>
            <div class="col-md-6">
              <label class="form-label">Responsable</label>
              <input class="form-control" value="{{ riesgo.responsable or '' }}" readonly>
            </div>
            <div class="col-md-6">
              <label class="form-label">Fecha de Implementación</label>
              <input class="form-control" value="{{ riesgo.fecha_implementacion or '' }}" readonly>
            </div>

          </div>

          <div class="riskform-bottom-actions">
            <a href="{{ url_for('gestion_riesgos') }}" class="btn btn-primary rounded-pill px-5 py-2 fw-bold">
              Volver a la Matriz
            </a>
            {% if not riesgo.archivado %}
              <a href="/editar_riesgo/{{ riesgo.id }}" class="btn btn-warning rounded-pill px-5 py-2 fw-bold">
                Editar Riesgo
              </a>
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

          .riskform-shell{
            width:96%;
            max-width:1600px;
            margin:10px auto 24px auto;
          }

          /* =========================
             HERO SGSI (MISMO DISEÑO)
          ========================== */
          .riskform-header-card{
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

          .riskform-header-card::before{
            content:"";
            position:absolute;
            inset:0;
            background:
              radial-gradient(circle at 92% 12%, rgba(255,255,255,.20), transparent 26%),
              repeating-linear-gradient(
                135deg,
                rgba(255,255,255,.05) 0px,
                rgba(255,255,255,.05) 1px,
                transparent 1px,
                transparent 15px
              );
            pointer-events:none;
          }

          .riskform-header-overlay{
            width:100%;
            height:100%;
            display:flex;
            align-items:center;
            justify-content:flex-start;
            text-align:left;
            padding:0;
            background:transparent;
            position:relative;
            z-index:1;
          }

          .riskform-header-overlay::before{
            content:"⚠️";
            width:54px;
            height:54px;
            min-width:54px;
            border-radius:14px;
            background:rgba(255,255,255,.96);
            color:#0b4a8f;
            display:flex;
            align-items:center;
            justify-content:center;
            font-size:1.55rem;
            box-shadow:0 8px 18px rgba(0,0,0,.20);
            margin-right:14px;
          }

          .riskform-header-text{
            max-width:1100px;
            position:relative;
            z-index:1;
          }

          .riskform-header-text::before{
            content:"SGSI · Gestión de Riesgos";
            display:inline-block;
            background:rgba(255,255,255,.18);
            border:1px solid rgba(255,255,255,.30);
            border-radius:999px;
            padding:3px 10px;
            font-size:.66rem;
            font-weight:800;
            letter-spacing:.35px;
            margin-bottom:4px;
          }

          .riskform-title{
            color:#ffffff !important;
            font-weight:950;
            font-size:1.36rem;
            line-height:1.08;
            text-shadow:0 3px 10px rgba(0,0,0,.32);
            margin:0;
          }

          .riskform-subtitle{
            color:rgba(248,252,255,.96);
            font-size:.78rem;
            margin-top:4px;
            line-height:1.25;
          }

          /* =========================
             CARD PRINCIPAL
          ========================== */
          .riskform-card{
            background:rgba(255,255,255,.96) !important;
            border-radius:18px;
            backdrop-filter:blur(8px);
            box-shadow:0 12px 24px rgba(15,23,42,.18);
            overflow:hidden;
            border:1px solid rgba(219,230,244,.9);
          }

          .riskform-card-body{
            padding:16px 18px;
          }

          /* =========================
             SECCIONES
          ========================== */
          .riskform-section-title{
            font-weight:950;
            font-size:.78rem;
            color:#0b4a8f;
            padding:9px 12px;
            border-radius:12px;
            background:#eef5ff;
            border:1px solid #d9eaff;
            margin:10px 0 12px 0;
          }

          /* =========================
             FORMULARIOS COMPACTOS
          ========================== */
          .riskform-card .form-label{
            font-weight:800;
            color:#25324a;
            margin-bottom:4px;
            font-size:.78rem;
          }

          .riskform-card .form-control,
          .riskform-card .form-select{
            border-radius:9px;
            border:1px solid #d9e3f0;
            min-height:37px;
            font-size:.80rem;
            background:#f8fafc;
            box-shadow:none;
            padding-top:5px;
            padding-bottom:5px;
          }

          .riskform-card textarea.form-control{
            min-height:70px;
            resize:vertical;
          }

          .riskform-card .form-control:focus,
          .riskform-card .form-select:focus{
            border-color:#3f86d6;
            box-shadow:0 0 0 .18rem rgba(63,134,214,.18);
          }

          .riskform-card .row{
            row-gap:10px;
          }

          .riskform-card .mb-3{
            margin-bottom:.70rem !important;
          }

          /* =========================
             BOTONES
          ========================== */
          .riskform-bottom-actions{
            display:flex;
            justify-content:center;
            gap:10px;
            flex-wrap:wrap;
            margin-top:18px;
          }

          .riskform-bottom-actions .btn{
            border-radius:10px !important;
            min-height:32px;
            padding:8px 24px !important;
            font-size:.82rem;
            font-weight:900;
            box-shadow:0 8px 16px rgba(15,23,42,.14);
          }

          .riskform-bottom-actions .btn-primary,
          .riskform-bottom-actions .btn-success{
            border:none;
            background:linear-gradient(135deg,#086df0,#2487ff);
            color:#fff;
          }

          .riskform-bottom-actions .btn-danger{
            border:none;
            background:linear-gradient(135deg,#b91c1c,#ef4444);
            color:#fff;
          }

          .riskform-cancel-btn{
            background:#ffffff;
            color:#0f172a;
            border:1px solid #cfd8e3;
            box-shadow:0 6px 14px rgba(0,0,0,.10);
          }

          .riskform-cancel-btn:hover{
            background:#edf5ff;
            color:#0b65d8;
            border-color:#9ec5fe;
          }

          /* =========================
             COLORES DE NIVEL
          ========================== */
          .nivel1 { background:#2ecc71 !important; color:#fff !important; font-weight:800; }
          .nivel2 { background:#f1c40f !important; color:#111 !important; font-weight:800; }
          .nivel3 { background:#ff69b4 !important; color:#111 !important; font-weight:800; }
          .nivel4 { background:#e74c3c !important; color:#fff !important; font-weight:800; }
          .nivel5 { background:#8e44ad !important; color:#fff !important; font-weight:800; }

          /* =========================
             RESPONSIVE
          ========================== */
          @media (max-width:992px){
            .riskform-shell{
              width:98%;
              margin:8px auto 22px auto;
            }

            .riskform-header-card{
              min-height:88px;
              padding:15px 18px;
            }

            .riskform-title{
              font-size:1.22rem;
            }

            .riskform-subtitle{
              font-size:.74rem;
            }

            .riskform-card-body{
              padding:8px 7px;
            }
          }

          @media (max-width:768px){
            .riskform-header-overlay{
              justify-content:center;
              text-align:center;
              flex-direction:column;
              gap:10px;
            }

            .riskform-header-overlay::before{
              margin-right:0;
            }

            .riskform-title{
              font-size:1.12rem;
            }

            .riskform-subtitle{
              font-size:.72rem;
            }

            .riskform-bottom-actions .btn{
              width:100%;
            }
          }
        </style>
      </form>
    </div>
    """

    return render_template_string(
        BASE,
        content=Markup(render_template_string(
            detalle_html,
            riesgo=riesgo,
            tipo_riesgo_nombre=tipo_riesgo_nombre,
            color_por_valor=color_por_valor,
            controles_detalle_html=Markup(riesgo_controles_detalle_html(riesgo)),
            riesgo_formatear_porcentaje=riesgo_formatear_porcentaje
        ))
    )

# ===========================
# EDITAR RIESGO COMPLETO
# ===========================
@app.route('/editar_riesgo/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_riesgo(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor' or (
        user.role != 'admin' and not verificar_permiso(user, "Gestión de Riesgos")
    ):
        flash("No tiene permiso para editar registros de gestión de riesgos.", "danger")
        return redirect(url_for('riesgos_menu'))
    
    riesgo = Riesgo.query.get_or_404(id)
    user_role = session.get('role', 'admin')
    solo_lectura = (user_role == 'auditor')

    # Al abrir la edición se recalcula inmediatamente con las bandas vigentes.
    # Esto evita mostrar valores residuales históricos o calculados con una
    # configuración anterior.
    if request.method == 'GET':
        try:
            if riesgo_actualizar_calculo_objeto(
                riesgo,
                reglas_prob=ConfigProbResidual.query.all(),
                reglas_imp=ConfigImpactoResidual.query.all(),
            ):
                db.session.commit()
        except Exception as exc:
            db.session.rollback()
            print(f"[WARN] No se pudo refrescar el residual del riesgo {id}: {exc!r}")

    if request.method == 'POST' and not solo_lectura:
        # Identificación y análisis
        riesgo.codigo_riesgo = request.form.get('codigo_riesgo')
        riesgo.riesgo = request.form.get('riesgo')
        riesgo.fecha_identificacion = request.form.get('fecha_identificacion')
        riesgo.propietario_riesgo = request.form.get('propietario_riesgo')
        riesgo.codigo_amenaza = request.form.get('codigo_amenaza')
        riesgo.amenaza = request.form.get('amenaza')
        riesgo.codigo_vulnerabilidad = request.form.get('codigo_vulnerabilidad')
        riesgo.vulnerabilidad = request.form.get('vulnerabilidad')
        riesgo.tipo_activo = request.form.get('tipo_activo')
        riesgo.nombre_activo = request.form.get('nombre_activo')
        riesgo.dimension_seguridad = request.form.get('dimension_seguridad')
        riesgo.prob_inh = request.form.get('prob_inh')
        riesgo.imp_inh = request.form.get('imp_inh')

        tipo_riesgo_id = request.form.get('tipo_riesgo_id')
        riesgo.tipo_riesgo_id = int(tipo_riesgo_id) if tipo_riesgo_id else None

        # Controles múltiples y evaluación individual
        controles_formulario = riesgo_extraer_controles_formulario(request.form)
        riesgo.plan_accion = request.form.get('plan_accion')

        # Tratamiento y seguimiento
        riesgo.fecha_revision = request.form.get('fecha_revision')
        riesgo.tratamiento_riesgo = request.form.get('tratamiento_riesgo')
        riesgo.observaciones = request.form.get('observaciones')
        riesgo.planes_accion = request.form.get('planes_accion')
        riesgo.responsable = request.form.get('responsable')
        riesgo.fecha_implementacion = request.form.get('fecha_implementacion')

        riesgo_reemplazar_controles(riesgo, controles_formulario)
        solidez_grupal = riesgo_sincronizar_campos_legacy(riesgo, controles_formulario)

        reglas_prob_actuales = ConfigProbResidual.query.all()
        reglas_imp_actuales = ConfigImpactoResidual.query.all()
        resultado = riesgo_calcular_resultados(
            riesgo.prob_inh,
            riesgo.imp_inh,
            solidez_grupal,
            reglas_prob=reglas_prob_actuales,
            reglas_imp=reglas_imp_actuales,
        )
        riesgo.probabilidad = resultado['prob_inh_num']
        riesgo.impacto = resultado['imp_inh_num']
        riesgo.riesgo_inherente = resultado['riesgo_inherente']
        riesgo.cuadrante_prob = resultado['prob_res_label']
        riesgo.prob_res = resultado['prob_res_label']
        riesgo.cuadrante_imp = resultado['imp_res_label']
        riesgo.impacto_res = resultado['imp_res_num']
        riesgo.impacto_res_label = resultado['imp_res_label']
        riesgo.riesgo_residual = resultado['riesgo_residual']

        db.session.commit()
        flash(
            f"✅ Riesgo actualizado con {len(controles_formulario)} control(es). Solidez grupal: {resultado['solidez_pct']:.2f}%. "
            f"Reducción probabilidad: {resultado['bajar_prob']} nivel(es) "
            f"({riesgo_describir_regla(resultado['regla_prob'])}); "
            f"reducción impacto: {resultado['bajar_imp']} nivel(es) "
            f"({riesgo_describir_regla(resultado['regla_imp'])}).",
            "success",
        )
        return redirect(url_for('gestion_riesgos'))

    FULL_SOA = [
            {"nr":"5.1","chapter":"Controles organizacionales","topic":"Políticas de seguridad de la información",
             "control_text":"La política de seguridad de la información y las políticas específicas deberán definirse, aprobarse por la dirección, publicarse, comunicarse y reconocerse por el personal y las partes interesadas, y revisarse a intervalos planificados o cuando se produzcan cambios significativos."},
            {"nr":"5.2","chapter":"Controles organizacionales","topic":"Roles y responsabilidades de seguridad de la información",
             "control_text":"Los roles y responsabilidades de seguridad de la información deberán definirse y asignarse según las necesidades de la organización."},
            {"nr":"5.3","chapter":"Controles organizacionales","topic":"Separación de funciones",
             "control_text":"Las funciones conflictivas y las áreas de responsabilidad en conflicto deberán separarse."},
            {"nr":"5.4","chapter":"Controles organizacionales","topic":"Responsabilidades de la dirección",
             "control_text":"La dirección deberá exigir que todo el personal aplique la seguridad de la información de acuerdo con la política y los procedimientos específicos aplicables."},
            {"nr":"5.5","chapter":"Controles organizacionales","topic":"Contacto con autoridades",
             "control_text":"La organización deberá establecer y mantener contacto con las autoridades relevantes."},
            {"nr":"5.6","chapter":"Controles organizacionales","topic":"Contacto con grupos de interés especial",
             "control_text":"La organización deberá establecer y mantener contacto con grupos de especial interés, foros especializados y asociaciones profesionales."},
            {"nr":"5.7","chapter":"Controles organizacionales","topic":"Inteligencia de amenazas",
             "control_text":"Se deberá recopilar y analizar información relacionada con las amenazas para producir inteligencia sobre amenazas."},
            {"nr":"5.8","chapter":"Controles organizacionales","topic":"Seguridad de la información en la gestión de proyectos",
             "control_text":"La seguridad de la información deberá integrarse en la gestión de proyectos."},
            {"nr":"5.9","chapter":"Controles organizacionales","topic":"Inventario de información y activos asociados",
             "control_text":"Se deberá desarrollar y mantener un inventario de la información y otros activos asociados, incluidos los propietarios."},
            {"nr":"5.10","chapter":"Controles organizacionales","topic":"Uso aceptable de la información y activos asociados",
             "control_text":"Se deberán identificar, documentar e implantar reglas y procedimientos para el uso aceptable y el manejo de la información y otros activos asociados."},
            {"nr":"5.11","chapter":"Controles organizacionales","topic":"Devolución de activos",
             "control_text":"El personal y otras partes interesadas deberán devolver los activos de la organización en su posesión al cambiar o terminar su relación contractual o laboral."},
            {"nr":"5.12","chapter":"Controles organizacionales","topic":"Clasificación de la información",
             "control_text":"La información deberá clasificarse según las necesidades de seguridad de la organización (confidencialidad, integridad, disponibilidad) y requisitos de las partes interesadas."},
            {"nr":"5.13","chapter":"Controles organizacionales","topic":"Etiquetado de la información",
             "control_text":"Se deberán desarrollar e implantar procedimientos apropiados para etiquetar la información según el esquema de clasificación adoptado."},
            {"nr":"5.14","chapter":"Controles organizacionales","topic":"Transferencia de información",
             "control_text":"Deben existir reglas, procedimientos o acuerdos para todo tipo de transferencia dentro de la organización y con terceros."},
            {"nr":"5.15","chapter":"Controles organizacionales","topic":"Control de accesos",
             "control_text":"Se deberán establecer e implementar reglas para controlar el acceso físico y lógico a la información y activos asociados según requisitos de negocio y seguridad."},
            {"nr":"5.16","chapter":"Controles organizacionales","topic":"Gestión de identidades",
             "control_text":"Deberá gestionarse el ciclo de vida completo de las identidades."},
            {"nr":"5.17","chapter":"Controles organizacionales","topic":"Información de autenticación",
             "control_text":"La asignación y gestión de la información de autenticación deberá controlarse mediante procesos de gestión y orientación al personal."},
            {"nr":"5.18","chapter":"Controles organizacionales","topic":"Derechos de acceso",
             "control_text":"Los derechos de acceso deberán ser provisionados, revisados, modificados y eliminados conforme a políticas y reglas de control de acceso."},
            {"nr":"5.19","chapter":"Controles organizacionales","topic":"Seguridad de la información en relaciones con proveedores",
             "control_text":"Se deberán definir e implantar procesos para gestionar los riesgos de seguridad asociados al uso de productos o servicios de proveedores."},
            {"nr":"5.20","chapter":"Controles organizacionales","topic":"Seguridad en acuerdos con proveedores",
             "control_text":"Se establecerán y acordarán requisitos de seguridad de la información con cada proveedor según el tipo de relación."},
            {"nr":"5.21","chapter":"Controles organizacionales","topic":"Gestión de la seguridad en la cadena de suministro TIC",
             "control_text":"Se deberán definir e implantar procesos para gestionar los riesgos asociados con productos y servicios TIC de la cadena de suministro."},
            {"nr":"5.22","chapter":"Controles organizacionales","topic":"Monitoreo y gestión del cambio de servicios de proveedor",
             "control_text":"La organización deberá supervisar, revisar y gestionar cambios en prácticas de seguridad y entrega de servicios de proveedores."},
            {"nr":"5.23","chapter":"Controles organizacionales","topic":"Seguridad para uso de servicios en la nube",
             "control_text":"Se deberán establecer procesos para adquisición, uso, gestión y salida de servicios en la nube según requisitos de seguridad organizacionales."},
            {"nr":"5.24","chapter":"Controles organizacionales","topic":"Planificación y preparación para la gestión de incidentes",
             "control_text":"La organización deberá planear y prepararse para gestionar incidentes de seguridad definiendo procesos, roles y responsabilidades."},
            {"nr":"5.25","chapter":"Controles organizacionales","topic":"Evaluación y decisión sobre eventos de seguridad",
             "control_text":"La organización deberá evaluar los eventos de seguridad y decidir si deben categorizarse como incidentes."},
            {"nr":"5.26","chapter":"Controles organizacionales","topic":"Respuesta a incidentes de seguridad",
             "control_text":"Los incidentes de seguridad deben responderse de acuerdo con procedimientos documentados."},
            {"nr":"5.27","chapter":"Controles organizacionales","topic":"Aprendizaje de incidentes de seguridad",
             "control_text":"El conocimiento obtenido de incidentes debe usarse para fortalecer y mejorar los controles de seguridad."},
            {"nr":"5.28","chapter":"Controles organizacionales","topic":"Recopilación de evidencias",
             "control_text":"Se deberán establecer procedimientos para la identificación, recolección y preservación de evidencias relacionadas con eventos de seguridad."},
            {"nr":"5.29","chapter":"Controles organizacionales","topic":"Seguridad durante la interrupción",
             "control_text":"La organización deberá planear cómo mantener la seguridad de la información en un nivel apropiado durante una interrupción."},
            {"nr":"5.30","chapter":"Controles organizacionales","topic":"Preparación TIC para continuidad del negocio",
             "control_text":"La preparación TIC para continuidad debe planearse, implementarse, mantenerse y probarse según objetivos de continuidad."},
            {"nr":"5.31","chapter":"Controles organizacionales","topic":"Requisitos legales, reglamentarios y contractuales",
             "control_text":"Se deberán identificar, documentar y mantener actualizados los requisitos legales y contractuales relevantes para la seguridad de la información."},
            {"nr":"5.32","chapter":"Controles organizacionales","topic":"Derechos de propiedad intelectual",
             "control_text":"La organización deberá implantar procedimientos apropiados para proteger la propiedad intelectual."},
            {"nr":"5.33","chapter":"Controles organizacionales","topic":"Protección de registros",
             "control_text":"Los registros deberán protegerse contra pérdida, destrucción, falsificación, acceso no autorizado y divulgación no autorizada."},
            {"nr":"5.34","chapter":"Controles organizacionales","topic":"Privacidad y protección de datos personales (PII)",
             "control_text":"La organización deberá identificar y cumplir los requisitos de preservación de la privacidad y protección de PII conforme a leyes y contratos aplicables."},
            {"nr":"5.35","chapter":"Controles organizacionales","topic":"Revisión independiente de seguridad de la información",
             "control_text":"El enfoque de la organización para gestionar la seguridad deberá revisarse de forma independiente a intervalos planificados o tras cambios significativos."},
            {"nr":"5.36","chapter":"Controles organizacionales","topic":"Cumplimiento con políticas, reglas y estándares",
             "control_text":"El cumplimiento con la política de seguridad, políticas específicas, reglas y estándares deberá revisarse regularmente."},
            {"nr":"5.37","chapter":"Controles organizacionales","topic":"Procedimientos operativos documentados",
             "control_text":"Se deberán documentar los procedimientos operativos para las instalaciones de procesamiento de información y ponerlos a disposición del personal que los necesite."},

            {"nr":"6.1","chapter":"Controles de personas","topic":"Verificación de antecedentes (screening)",
             "control_text":"Se deberán efectuar verificaciones previas de antecedentes para candidatos al personal y de forma continua según leyes, regulaciones y riesgos."},
            {"nr":"6.2","chapter":"Controles de personas","topic":"Términos y condiciones de empleo",
             "control_text":"Los contratos de empleo deberán expresar las responsabilidades del personal y de la organización respecto a la seguridad de la información."},
            {"nr":"6.3","chapter":"Controles de personas","topic":"Concienciación, educación y formación en seguridad",
             "control_text":"El personal y partes interesadas relevantes deberán recibir formación y actualizaciones sobre políticas y procedimientos de seguridad."},
            {"nr":"6.4","chapter":"Controles de personas","topic":"Proceso disciplinario",
             "control_text":"Se deberá formalizar y comunicar un proceso disciplinario para acciones contra incumplimientos de la política de seguridad."},
            {"nr":"6.5","chapter":"Controles de personas","topic":"Responsabilidades tras terminación o cambio de empleo",
             "control_text":"Se deberán definir y comunicar responsabilidades de seguridad que se mantienen tras la terminación o cambio de empleo."},
            {"nr":"6.6","chapter":"Controles de personas","topic":"Acuerdos de confidencialidad (NDA)",
             "control_text":"Se deberán identificar, documentar, revisar y firmar acuerdos de confidencialidad según las necesidades de la organización."},
            {"nr":"6.7","chapter":"Controles de personas","topic":"Trabajo remoto",
             "control_text":"Se deberán implantar medidas de seguridad cuando el personal trabaje de forma remota para proteger la información fuera de las instalaciones."},
            {"nr":"6.8","chapter":"Controles de personas","topic":"Reportes de eventos de seguridad",
             "control_text":"La organización deberá proporcionar mecanismos para que el personal reporte incidentes observados o sospechados de forma oportuna."},

            {"nr":"7.1","chapter":"Controles físicos","topic":"Perímetros de seguridad física",
             "control_text":"Se deberán definir perímetros de seguridad para proteger áreas que contengan información y activos asociados."},
            {"nr":"7.2","chapter":"Controles físicos","topic":"Entrada física",
             "control_text":"Las áreas seguras deberán protegerse mediante controles de acceso y puntos de entrada apropiados."},
            {"nr":"7.3","chapter":"Controles físicos","topic":"Aseguramiento de oficinas, salas e instalaciones",
             "control_text":"La seguridad física de oficinas, salas e instalaciones deberá diseñarse e implementarse."},
            {"nr":"7.4","chapter":"Controles físicos","topic":"Monitorización de seguridad física",
             "control_text":"Las instalaciones deberán ser monitorizadas para detectar accesos físicos no autorizados."},
            {"nr":"7.5","chapter":"Controles físicos","topic":"Protección contra amenazas físicas y ambientales",
             "control_text":"Se deberán diseñar e implementar medidas contra amenazas físicas y ambientales (desastres naturales, etc.)."},
            {"nr":"7.6","chapter":"Controles físicos","topic":"Trabajo en áreas seguras",
             "control_text":"Se deberán implantar medidas de seguridad para el trabajo en áreas seguras."},
            {"nr":"7.7","chapter":"Controles físicos","topic":"Escritorio y pantalla limpios",
             "control_text":"Se deberán definir y aplicar reglas de escritorio y pantalla limpia para proteger la información."},
            {"nr":"7.8","chapter":"Controles físicos","topic":"Ubicación y protección del equipo",
             "control_text":"El equipo deberá ubicarse y protegerse físicamente."},
            {"nr":"7.9","chapter":"Controles físicos","topic":"Seguridad de activos fuera de las instalaciones",
             "control_text":"Los activos fuera de las instalaciones deberán protegerse adecuadamente."},
            {"nr":"7.10","chapter":"Controles físicos","topic":"Medios de almacenamiento",
             "control_text":"Los medios de almacenamiento deberán gestionarse durante todo su ciclo (adquisición, uso, transporte, eliminación) conforme al esquema de clasificación."},
            {"nr":"7.11","chapter":"Controles físicos","topic":"Servicios de apoyo",
             "control_text":"Las instalaciones de procesamiento de información deberán protegerse de fallos de servicios públicos y otras interrupciones."},
            {"nr":"7.12","chapter":"Controles físicos","topic":"Seguridad del cableado",
             "control_text":"Los cables que transporten energía o datos deberán protegerse contra intercepción, interferencia o daño."},
            {"nr":"7.13","chapter":"Controles físicos","topic":"Mantenimiento de equipos",
             "control_text":"El equipo deberá mantenerse para asegurar disponibilidad, integridad y confidencialidad."},
            {"nr":"7.14","chapter":"Controles físicos","topic":"Disposición segura o reutilización de equipos",
             "control_text":"Los equipos con medios de almacenamiento deberán verificarse para asegurar que los datos sensibles se han eliminado o sobrescrito antes de su eliminación o reutilización."},

            {"nr":"8.1","chapter":"Controles tecnológicos","topic":"Dispositivos endpoint de usuario",
             "control_text":"La información almacenada, procesada o accesible mediante dispositivos endpoint deberá protegerse."},
            {"nr":"8.2","chapter":"Controles tecnológicos","topic":"Derechos privilegiados de acceso",
             "control_text":"La asignación y uso de derechos privilegiados deberá restringirse y gestionarse."},
            {"nr":"8.3","chapter":"Controles tecnológicos","topic":"Restricción de acceso a la información",
             "control_text":"El acceso a la información y activos asociados deberá restringirse conforme a la política de control de acceso."},
            {"nr":"8.4","chapter":"Controles tecnológicos","topic":"Acceso al código fuente",
             "control_text":"El acceso de lectura/escritura al código fuente, herramientas de desarrollo y bibliotecas deberá gestionarse adecuadamente."},
            {"nr":"8.5","chapter":"Controles tecnológicos","topic":"Autenticación segura",
             "control_text":"Deben implementarse tecnologías y procedimientos de autenticación segura basados en la política de control de acceso."},
            {"nr":"8.6","chapter":"Controles tecnológicos","topic":"Gestión de capacidad",
             "control_text":"Se deberán monitorizar y ajustar los recursos conforme a los requisitos actuales y esperados."},
            {"nr":"8.7","chapter":"Controles tecnológicos","topic":"Protección contra malware",
             "control_text":"Deben implementarse medidas de protección contra malware y concienciación del usuario."},
            {"nr":"8.8","chapter":"Controles tecnológicos","topic":"Gestión de vulnerabilidades técnicas",
             "control_text":"Se deberá obtener información sobre vulnerabilidades técnicas y evaluar la exposición de la organización, tomando medidas apropiadas."},
            {"nr":"8.9","chapter":"Controles tecnológicos","topic":"Gestión de configuración",
             "control_text":"Se deberán establecer, documentar, implementar y revisar configuraciones, incluidas las de seguridad."},
            {"nr":"8.10","chapter":"Controles tecnológicos","topic":"Eliminación de información",
             "control_text":"La información almacenada en sistemas o medios deberá eliminarse cuando ya no sea necesaria."},
            {"nr":"8.11","chapter":"Controles tecnológicos","topic":"Enmascaramiento de datos",
             "control_text":"Se deberá aplicar enmascaramiento de datos conforme a políticas y requisitos legales y de negocio."},
            {"nr":"8.12","chapter":"Controles tecnológicos","topic":"Prevención de pérdida de datos",
             "control_text":"Se deberán aplicar medidas de prevención de fuga de datos a sistemas, redes y dispositivos que procesen información sensible."},
            {"nr":"8.13","chapter":"Controles tecnológicos","topic":"Copia de seguridad de la información",
             "control_text":"Se deberán mantener y probar regularmente copias de seguridad de información, software y sistemas conforme a la política de backups."},
            {"nr":"8.14","chapter":"Controles tecnológicos","topic":"Redundancia de instalaciones de procesamiento",
             "control_text":"Las instalaciones de procesamiento deberán contar con redundancia suficiente para cumplir requisitos de disponibilidad."},
            {"nr":"8.15","chapter":"Controles tecnológicos","topic":"Registro y trazabilidad (logging)",
             "control_text":"Deben generarse, almacenar, proteger y analizar registros que reflejen actividades, excepciones y fallos relevantes."},
            {"nr":"8.16","chapter":"Controles tecnológicos","topic":"Actividades de monitorización",
             "control_text":"Redes, sistemas y aplicaciones deberán monitorizarse para detectar comportamientos anómalos y evaluar posibles incidentes."},
            {"nr":"8.17","chapter":"Controles tecnológicos","topic":"Sincronización de relojes",
             "control_text":"Los relojes de los sistemas deberán sincronizarse con fuentes de tiempo aprobadas."},
            {"nr":"8.18","chapter":"Controles tecnológicos","topic":"Uso de utilidades privilegiadas",
             "control_text":"El uso de programas utilitarios capaces de anular controles del sistema deberá restringirse y controlarse estrictamente."},
            {"nr":"8.19","chapter":"Controles tecnológicos","topic":"Instalación de software en sistemas operativos",
             "control_text":"Deben implementarse procedimientos para gestionar la instalación de software en sistemas operativos de manera segura."},
            {"nr":"8.20","chapter":"Controles tecnológicos","topic":"Seguridad de redes",
             "control_text":"Redes y dispositivos de red deberán protegerse, gestionarse y controlarse para salvaguardar la información."},
            {"nr":"8.21","chapter":"Controles tecnológicos","topic":"Seguridad de servicios de red",
             "control_text":"Se deberán identificar, implementar y monitorizar mecanismos y niveles de servicio de los servicios de red."},
            {"nr":"8.22","chapter":"Controles tecnológicos","topic":"Segregación en redes",
             "control_text":"Se deberán segregar grupos de servicios, usuarios y sistemas en las redes de la organización."},
            {"nr":"8.23","chapter":"Controles tecnológicos","topic":"Filtrado web",
             "control_text":"El acceso a sitios externos deberá gestionarse para reducir exposición a contenido malicioso."},
            {"nr":"8.24","chapter":"Controles tecnológicos","topic":"Uso de criptografía",
             "control_text":"Deben definirse e implantar reglas para el uso efectivo de criptografía y gestión de claves."},
            {"nr":"8.25","chapter":"Controles tecnológicos","topic":"Ciclo de vida de desarrollo seguro",
             "control_text":"Deben establecerse y aplicarse reglas para el desarrollo seguro de software y sistemas."},
            {"nr":"8.26","chapter":"Controles tecnológicos","topic":"Requisitos de seguridad de aplicaciones",
             "control_text":"Se deberán identificar, especificar y aprobar requisitos de seguridad al desarrollar o adquirir aplicaciones."},
            {"nr":"8.27","chapter":"Controles tecnológicos","topic":"Arquitectura y principios de ingeniería seguros",
             "control_text":"Deben establecerse principios documentados para ingeniería de sistemas seguros en actividades de desarrollo."},
            {"nr":"8.28","chapter":"Controles tecnológicos","topic":"Codificación segura",
             "control_text":"Deben aplicarse principios de codificación segura durante el desarrollo de software."},
            {"nr":"8.29","chapter":"Controles tecnológicos","topic":"Pruebas de seguridad en desarrollo y aceptación",
             "control_text":"Deben definirse e implantar procesos de pruebas de seguridad dentro del ciclo de desarrollo."},
            {"nr":"8.30","chapter":"Controles tecnológicos","topic":"Desarrollo externalizado",
             "control_text":"La organización deberá dirigir, supervisar y revisar actividades relacionadas con el desarrollo externalizado."},
            {"nr":"8.31","chapter":"Controles tecnológicos","topic":"Separación de entornos (desarrollo, prueba, producción)",
             "control_text":"Los entornos de desarrollo, prueba y producción deberán separarse y asegurarse."},
            {"nr":"8.32","chapter":"Controles tecnológicos","topic":"Gestión de cambios",
             "control_text":"Los cambios en instalaciones y sistemas deberán sujetarse a procedimientos de gestión de cambios."},
            {"nr":"8.33","chapter":"Controles tecnológicos","topic":"Información de prueba",
             "control_text":"La información de prueba deberá seleccionarse, protegerse y gestionarse apropiadamente."},
            {"nr":"8.34","chapter":"Controles tecnológicos","topic":"Protección de sistemas durante pruebas de auditoría",
             "control_text":"Las pruebas de auditoría y actividades de aseguramiento en sistemas operativos deberán planificarse y acordarse con la dirección apropiada."}
    ]

    full_soa_json = json.dumps(FULL_SOA, ensure_ascii=False)

    tipos_riesgo = TipoRiesgo.query.filter_by(activo=True).order_by(TipoRiesgo.nombre.asc()).all()

    pci_options_html = construir_opciones_control(
        PCI_DSS_CONTROLES,
        riesgo.codigo_control_pci_dss
    )
    nist_options_html = construir_opciones_control(
        NIST_CSF_20_CONTROLES,
        riesgo.codigo_control_nist_csf
    )
    soc2_options_html = construir_opciones_control(
        SOC2_CONTROLES,
        riesgo.codigo_control_soc2
    )

    reglas_prob_edit = ConfigProbResidual.query.all()
    reglas_imp_edit = ConfigImpactoResidual.query.all()
    controles_widget = riesgo_controles_widget_html(
        controles_iniciales=riesgo_controles_para_formulario(riesgo),
        reglas_prob=[{'min': r.min, 'max': r.max, 'bajar': r.bajar} for r in reglas_prob_edit],
        reglas_imp=[{'min': r.min, 'max': r.max, 'bajar': r.bajar} for r in reglas_imp_edit],
        section_class="riskedit-section-title",
    )

    html_editar = f"""
    <div class="riskedit-shell">

      <!-- =========================
           CABECERA
      ========================== -->
      <div class="riskedit-header-card">
        <div class="riskedit-header-overlay">
          <div class="riskedit-header-text">
            <h3 class="riskedit-title m-0">✏️ Editar Riesgo #{riesgo.id}</h3>
            <div class="riskedit-subtitle">
              Actualización de la información, valoración y tratamiento del riesgo en la gestión del SGSI
            </div>
          </div>
        </div>
      </div>

      <form method='POST' class='riskedit-card'>
        <div class="riskedit-card-body">
          <div class='row g-3'>

            <div class="col-12">
              <div class="riskedit-section-title">🧩 Identificación del Riesgo</div>
            </div>

            <div class="col-md-3">
              <label class="form-label">Código de Riesgo</label>
              <input class="form-control" name="codigo_riesgo" value='{riesgo.codigo_riesgo or ""}' required>
            </div>
            <div class="col-md-3">
              <label class="form-label">Riesgo</label>
              <input class="form-control" name="riesgo" value='{riesgo.riesgo or ""}' required>
            </div>
            <div class="col-md-3">
              <label class="form-label">Tipo de Riesgo</label>
              <select class="form-control" name="tipo_riesgo_id" required>
                <option value="">Seleccione...</option>
                {{% for t in tipos_riesgo %}}
                  <option value="{{{{ t.id }}}}" {{% if riesgo.tipo_riesgo_id == t.id %}}selected{{% endif %}}>
                    {{{{ t.nombre }}}}
                  </option>
                {{% endfor %}}
              </select>
            </div>
            <div class="col-md-3">
              <label class="form-label">Fecha de Identificación</label>
              <input type="date" class="form-control" name="fecha_identificacion" value='{riesgo.fecha_identificacion or ""}'>
            </div>
            <div class="col-md-3">
              <label class="form-label">Propietario del Riesgo</label>
              <input class="form-control" name="propietario_riesgo" value='{riesgo.propietario_riesgo or ""}'>
            </div>

            <div class="col-12">
              <div class="riskedit-section-title">🧩 Análisis</div>
            </div>

            <div class="col-md-3">
              <label class="form-label">Código Amenaza</label>
              <input class="form-control" name="codigo_amenaza" value='{riesgo.codigo_amenaza or ""}'>
            </div>
            <div class="col-md-3">
              <label class="form-label">Amenaza</label>
              <input class="form-control" name="amenaza" value='{riesgo.amenaza or ""}'>
            </div>
            <div class="col-md-3">
              <label class="form-label">Código Vulnerabilidad</label>
              <input class="form-control" name="codigo_vulnerabilidad" value='{riesgo.codigo_vulnerabilidad or ""}'>
            </div>
            <div class="col-md-3">
              <label class="form-label">Vulnerabilidad</label>
              <input class="form-control" name="vulnerabilidad" value='{riesgo.vulnerabilidad or ""}'>
            </div>

            <div class="col-md-3">
              <label class="form-label">Tipo de Activo</label>
              <input class="form-control" name="tipo_activo" value='{riesgo.tipo_activo or ""}'>
            </div>
            <div class="col-md-3">
              <label class="form-label">Nombre del Activo</label>
              <input class="form-control" name="nombre_activo" value='{riesgo.nombre_activo or ""}'>
            </div>
            <div class="col-md-3">
              <label class="form-label">Principio de Seguridad</label>
              <select class="form-control" name="dimension_seguridad">
                  <option value="">Seleccione...</option>
                  <option value="Confidencialidad" {"selected" if riesgo.dimension_seguridad == "Confidencialidad" else ""}>Confidencialidad</option>
                  <option value="Integridad" {"selected" if riesgo.dimension_seguridad == "Integridad" else ""}>Integridad</option>
                  <option value="Disponibilidad" {"selected" if riesgo.dimension_seguridad == "Disponibilidad" else ""}>Disponibilidad</option>
              </select>
            </div>

            <div class="col-12">
              <div class="riskedit-section-title">🧮 Riesgo Inherente</div>
            </div>

            <div class='col-md-3'>
              <label class='form-label'>Probabilidad Inherente</label>
              <select id="prob_inh" class="form-control" name="prob_inh" required>
                  <option value="">Seleccione...</option>
                  <option value="Rara vez o Muy baja" {"selected" if riesgo.prob_inh=="Rara vez o Muy baja" else ""}>Rara vez o Muy baja</option>
                  <option value="Eventualmente o baja" {"selected" if riesgo.prob_inh=="Eventualmente o baja" else ""}>Eventualmente o baja</option>
                  <option value="Puede ocurrir o Moderada" {"selected" if riesgo.prob_inh=="Puede ocurrir o Moderada" else ""}>Puede ocurrir o Moderada</option>
                  <option value="Probable o Alta" {"selected" if riesgo.prob_inh=="Probable o Alta" else ""}>Probable o Alta</option>
                  <option value="Muy frecuente o Muy Alta" {"selected" if riesgo.prob_inh=="Muy frecuente o Muy Alta" else ""}>Muy frecuente o Muy Alta</option>
              </select>
            </div>
            <div class='col-md-3'>
              <label class='form-label'>Impacto Inherente</label>
              <select id="imp_inh" class="form-control" name="imp_inh" required>
                  <option value="">Seleccione...</option>
                  <option value="Insignificante o Inferior" {"selected" if riesgo.imp_inh=="Insignificante o Inferior" else ""}>Insignificante o Inferior</option>
                  <option value="Menor" {"selected" if riesgo.imp_inh=="Menor" else ""}>Menor</option>
                  <option value="Moderado o Importante" {"selected" if riesgo.imp_inh=="Moderado o Importante" else ""}>Moderado o Importante</option>
                  <option value="Mayor" {"selected" if riesgo.imp_inh=="Mayor" else ""}>Mayor</option>
                  <option value="Catastrófico o Crítico" {"selected" if riesgo.imp_inh=="Catastrófico o Crítico" else ""}>Catastrófico o Crítico</option>
              </select>
            </div>
            <div class="col-md-3">
              <label class="form-label">Riesgo Inherente</label>
              <input type="text" class="form-control" name="riesgo_inherente" id="riesgo_inherente" value="{riesgo.riesgo_inherente or ''}" readonly>
            </div>

            {controles_widget}

            <div class="col-12">
              <div class="riskedit-section-title">🧩 Tratamiento del Riesgo Inherente</div>
            </div>
            <div class="col-md-12">
              <label class="form-label">Plan de Acción</label>
              <textarea class="form-control" name="plan_accion">{riesgo.plan_accion or ""}</textarea>
            </div>

            <div class="col-12">
              <div class="riskedit-section-title">🧩 Riesgo Residual</div>
            </div>
            <div class="col-md-3">
              <label class="form-label">Solidez Grupal (Promedio)</label>
              <input class="form-control risk-control-result" id="solidez_grupal" name="solidez_grupal" value="{riesgo_formatear_porcentaje(riesgo.solidez_grupal or 0)}" readonly>
              <input type="hidden" id="valor" name="valor" value="{riesgo_formatear_porcentaje(riesgo.solidez_grupal or 0)}">
            </div>
            <div class="col-md-3">
              <label class="form-label">Probabilidad Residual</label>
              <input class="form-control" id="cuadrante_prob" value="{riesgo.cuadrante_prob or riesgo.prob_res or ''}" readonly>
            </div>
            <div class="col-md-3">
              <label class="form-label">Impacto Residual</label>
              <input class="form-control" id="cuadrante_imp" value="{riesgo.cuadrante_imp or riesgo.impacto_res_label or ''}" readonly>
            </div>
            <div class="col-md-3">
              <label class="form-label">Riesgo Residual</label>
              <input class="form-control" id="riesgo_residual" value="{riesgo.riesgo_residual or ''}" readonly>
            </div>
            <div class="col-12">
              <div id="detalle_regla_residual" class="alert alert-info py-2 px-3 mb-0 small">
                Validando las bandas configuradas de probabilidad e impacto...
              </div>
            </div>
            <div class="col-md-3">
              <label class="form-label">Fecha de Revisión</label>
              <input type="date" class="form-control" name="fecha_revision" value='{riesgo.fecha_revision or ""}'>
            </div>

            <div class="col-12">
              <div class="riskedit-section-title">🧩 Tratamiento del Riesgo Residual</div>
            </div>

            <div class="col-md-3">
              <label class="form-label">Tratamiento del Riesgo</label>
              <select class="form-control" name="tratamiento_riesgo" required>
                  <option value="">Seleccione...</option>
                  <option value="Aceptación" {"selected" if riesgo.tratamiento_riesgo=="Aceptación" else ""}>Aceptación</option>
                  <option value="Rechazo" {"selected" if riesgo.tratamiento_riesgo=="Rechazo" else ""}>Rechazo</option>
                  <option value="Transferencia" {"selected" if riesgo.tratamiento_riesgo=="Transferencia" else ""}>Transferencia</option>
                  <option value="Mitigación" {"selected" if riesgo.tratamiento_riesgo=="Mitigación" else ""}>Mitigación</option>
              </select>
            </div>

            <div class="col-md-12">
              <label class="form-label">Observaciones</label>
              <textarea class="form-control" name="observaciones">{riesgo.observaciones or ""}</textarea>
            </div>
            <div class="col-md-12">
              <label class="form-label">Planes de Acción</label>
              <textarea class="form-control" name="planes_accion">{riesgo.planes_accion or ""}</textarea>
            </div>
            <div class="col-md-6">
              <label class="form-label">Responsable</label>
              <input class="form-control" name="responsable" value='{riesgo.responsable or ""}'>
            </div>
            <div class="col-md-6">
              <label class="form-label">Fecha de Implementación</label>
              <input type="date" class="form-control" name="fecha_implementacion" value='{riesgo.fecha_implementacion or ""}'>
            </div>

          </div>

          <div class='riskedit-bottom-actions'>
            <button class='btn btn-primary rounded-pill px-4 py-2 fw-bold' type="submit">Guardar cambios</button>
            <a href='/riesgos' class='btn rounded-pill px-4 py-2 fw-bold riskedit-cancel-btn'>Cancelar</a>
          </div>
        </div>

      </form>
    </div>

    <style>
      body{{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }}

      .riskedit-shell{{
        width:96%;
        max-width:1600px;
        margin:10px auto 24px auto;
      }}

      /* =========================
         HERO SGSI
      ========================== */
      .riskedit-header-card{{
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
      }}

      .riskedit-header-card::before{{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%, rgba(255,255,255,.20), transparent 26%),
          repeating-linear-gradient(
            135deg,
            rgba(255,255,255,.05) 0px,
            rgba(255,255,255,.05) 1px,
            transparent 1px,
            transparent 15px
          );
        pointer-events:none;
      }}

      .riskedit-header-overlay{{
        width:100%;
        height:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        padding:0;
        background:transparent;
        position:relative;
        z-index:1;
      }}

      .riskedit-header-overlay::before{{
        content:"✏️";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:rgba(255,255,255,.96);
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.55rem;
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }}

      .riskedit-header-text{{
        max-width:1100px;
        position:relative;
        z-index:1;
      }}

      .riskedit-header-text::before{{
        content:"SGSI · Edición de Riesgo";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border:1px solid rgba(255,255,255,.30);
        border-radius:999px;
        padding:3px 10px;
        font-size:.66rem;
        font-weight:800;
        letter-spacing:.35px;
        margin-bottom:4px;
      }}

      .riskedit-title{{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.36rem;
        line-height:1.08;
        text-shadow:0 3px 10px rgba(0,0,0,.32);
        margin:0;
      }}

      .riskedit-subtitle{{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }}

      /* =========================
         CARD
      ========================== */
      .riskedit-card{{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        overflow:hidden;
        border:1px solid rgba(219,230,244,.9);
      }}

      .riskedit-card-body{{
        padding:16px 18px;
      }}

      /* =========================
         SECCIONES
      ========================== */
      .riskedit-section-title{{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:10px 0 12px 0;
      }}

      /* =========================
         FORMULARIOS
      ========================== */
      .riskedit-card .form-label{{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }}

      .riskedit-card .form-control,
      .riskedit-card .form-select{{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:37px;
        font-size:.80rem;
        background:#f8fafc;
        box-shadow:none;
      }}

      .riskedit-card textarea.form-control{{
        min-height:70px;
        resize:vertical;
      }}

      .riskedit-card .form-control:focus,
      .riskedit-card .form-select:focus{{
        border-color:#3f86d6;
        box-shadow:0 0 0 .18rem rgba(63,134,214,.18);
      }}

      /* =========================
         BOTONES
      ========================== */
      .riskedit-bottom-actions{{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin-top:18px;
      }}

      .riskedit-bottom-actions .btn{{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 24px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }}

      .riskedit-bottom-actions .btn-primary,
      .riskedit-bottom-actions .btn-success{{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }}

      .riskedit-bottom-actions .btn-danger{{
        border:none;
        background:linear-gradient(135deg,#b91c1c,#ef4444);
        color:#fff;
      }}

      .riskedit-cancel-btn{{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }}

      .riskedit-cancel-btn:hover{{
        background:#edf5ff;
        color:#0b65d8;
      }}

      /* =========================
         RESPONSIVE
      ========================== */
      @media (max-width:992px){{
        .riskedit-shell{{ width:98%; }}

        .riskedit-header-card{{ min-height:88px; }}

        .riskedit-title{{ font-size:1.22rem; }}

        .riskedit-subtitle{{ font-size:.74rem; }}

        .riskedit-card-body{{ padding:8px 7px; }}
      }}

      @media (max-width:768px){{
        .riskedit-header-overlay{{
          justify-content:center;
          text-align:center;
          flex-direction:column;
          gap:10px;
        }}

        .riskedit-header-overlay::before{{ margin-right:0; }}

        .riskedit-bottom-actions .btn{{ width:100%; }}
      }}
    </style>
    """
   
    return render_template_string(
        BASE,
        content=Markup(render_template_string(html_editar, riesgo=riesgo, tipos_riesgo=tipos_riesgo))
    )

# ===========================
# CALCULAR PROBABILIDAD RESIDUAL
# ===========================
def calcular_probabilidad_residual(prob_inherente, solidez):
    resultado = riesgo_calcular_resultados(
        prob_inherente,
        1,
        solidez,
        reglas_prob=ConfigProbResidual.query.all(),
        reglas_imp=[],
    )
    return resultado["prob_res_num"]


# ===========================================================
# CALCULAR IMPACTO RESIDUAL
# ===========================================================
def calcular_impacto_residual(impacto_inherente, solidez):
    resultado = riesgo_calcular_resultados(
        1,
        impacto_inherente,
        solidez,
        reglas_prob=[],
        reglas_imp=ConfigImpactoResidual.query.all(),
    )
    return resultado["imp_res_num"], resultado["imp_res_label"]


# ===========================
# FUNCIÓN DE CÁLCULO DE RIESGO
# ===========================
def calcular_riesgo(prob_texto, imp_texto):
    prob = riesgo_nivel_numero(prob_texto, "probabilidad", 1)
    imp = riesgo_nivel_numero(imp_texto, "impacto", 1)
    puntaje = prob * imp
    return puntaje, riesgo_clasificar_puntaje(puntaje)


@app.post("/tipos_riesgo/delete/<int:tipo_id>")
@login_required
def delete_tipo_riesgo(tipo_id):
    user = User.query.get(session.get("user_id"))
    t = TipoRiesgo.query.get_or_404(tipo_id)
    if t.owner_user_id != user.id and user.role != "admin":
        flash("No autorizado.", "danger")
        return redirect(url_for("configurar_tipos_riesgo"))
    db.session.delete(t)
    db.session.commit()
    flash("🗑️ Tipo eliminado.", "success")
    return redirect(url_for("configurar_tipos_riesgo"))


# ===========================
# Archivar Riesgo
# ===========================

@app.post('/archivar_riesgo/<int:riesgo_id>')
@login_required
def archivar_riesgo(riesgo_id):
    user_role = session.get('role', 'admin')
    if user_role == 'auditor':
        flash("No tienes permisos para archivar.", "warning")
        return redirect(url_for('gestion_riesgos'))

    r = Riesgo.query.get_or_404(riesgo_id)
    if r.archivado:
        flash("El riesgo ya estaba archivado.", "info")
    else:
        r.archivado = True
        r.archivado_en = datetime.utcnow()
        r.archivado_por = session.get('username', 'sistema')
        db.session.commit()
        flash("📦 Riesgo archivado.", "success")
    return redirect(url_for('gestion_riesgos'))

# ===========================
# Restaurar Riesgo
# ===========================

@app.post('/restaurar_riesgo/<int:riesgo_id>')
@login_required
def restaurar_riesgo(riesgo_id):
    user_role = session.get('role', 'admin')
    if user_role == 'auditor':
        flash("No tienes permisos para restaurar.", "warning")
        return redirect(url_for('gestion_riesgos', ver='archivados'))

    r = Riesgo.query.get_or_404(riesgo_id)
    if not r.archivado:
        flash("El riesgo no está archivado.", "info")
    else:
        r.archivado = False
        r.archivado_en = None
        r.archivado_por = None
        db.session.commit()
        flash("♻️ Riesgo restaurado.", "success")
    return redirect(url_for('gestion_riesgos', ver='archivados'))


# ===========================
# ELIMINAR RIESGO
# ===========================
@app.route('/eliminar_riesgo/<int:id>')
@login_required
def eliminar_riesgo(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor' or (user.role != 'admin' and not verificar_permiso(user, "Gestión de Riesgos")
    ):
        flash("No tiene permiso para eliminar registros del contexto externo.", "danger")
        return redirect(url_for('riesgos_menu'))

    riesgo = Riesgo.query.get_or_404(id)
    db.session.delete(riesgo)
    db.session.commit()
    flash("🗑️ Riesgo eliminado correctamente", "info")
    return redirect(url_for('gestion_riesgos'))

# ============================================================================================================================================
#                                                               Fin del Módulo Gestión de Riesgos
# ============================================================================================================================================


# ============================================================================================================================================
#                                                       Módulo Objetivo del Sistema de Gestión de Seguridad
# ============================================================================================================================================

class ObjetivoSGSI(db.Model):
    __tablename__ = 'objetivos_sgsi'

    id = db.Column(db.Integer, primary_key=True)

    # Campos de la matriz
    objetivo               = db.Column(db.Text)        # Objetivo
    indicador              = db.Column(db.Text)        # Indicador
    actividades            = db.Column(db.Text)        # Actividades para lograr el cumplimiento
    recursos               = db.Column(db.Text)        # Recursos
    forma_calculo          = db.Column(db.Text)        # Forma de cálculo del indicador
    meta_pct               = db.Column(db.Integer)     # Meta (porcentaje)
    frecuencia_calculo     = db.Column(db.String(50))  # Anual, Bimensual, ...
    frecuencia_detalle     = db.Column(db.Text)        # Solo si es "Por Demanda"
    fecha_meta             = db.Column(db.String(10))  # o Date, según manejes fechas
    responsable_calcular   = db.Column(db.Text)        # Responsable de calcular el indicador
    responsable_info       = db.Column(db.Text)        # Responsable de suministrar información


def obtener_responsable_objetivo(it):
    return (
        getattr(it, 'responsable_del_indicador', None)
        or getattr(it, 'responsable_indicador', None)
        or getattr(it, 'responsable', None)
        or getattr(it, 'responsable_calculo', None)
        or '—'
    )

def format_fecha_corta(valor):
    if not valor:
        return '—'
    try:
        return valor.strftime('%Y-%m-%d')
    except Exception:
        return str(valor)


# =========================
# ENTRADA DIRECTA AL MÓDULO
# =========================
@app.route('/objetivos_menu')
@login_required
def objetivos_menu():
    user = User.query.get(session.get('user_id'))

    if user.role not in ('admin', 'auditor') and not verificar_permiso(
        user, "Objetivos del Sistema de Gestión"
    ):
        flash("No tiene permiso para acceder al módulo de objetivos.", "danger")
        return redirect(url_for('menu'))

    return redirect(url_for('objetivos_matriz'))


# =========================
# AGREGAR — Objetivo SGSI
# =========================
@app.route('/objetivos/new', methods=['GET', 'POST'])
@login_required
def objetivos_new():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede agregar objetivos.", "danger")
        return redirect(url_for('objetivos_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Objetivos del Sistema de Gestión"):
        flash("No tiene permiso para agregar objetivos del SGSI.", "danger")
        return redirect(url_for('objetivos_matriz'))

    if request.method == 'POST':
        objetivo  = (request.form.get('objetivo') or '').strip()
        indicador = (request.form.get('indicador') or '').strip()
        actividades = (request.form.get('actividades') or '').strip()
        recursos    = (request.form.get('recursos') or '').strip()
        forma_calc  = (request.form.get('forma_calculo') or '').strip()
        meta_pct    = request.form.get('meta_pct', type=int) or 0
        frecuencia  = (request.form.get('frecuencia_calculo') or '').strip()
        frec_det    = (request.form.get('frecuencia_detalle') or '').strip()
        fecha_meta  = request.form.get('fecha_meta') or ''
        resp_calc   = (request.form.get('responsable_calcular') or '').strip()
        resp_info   = (request.form.get('responsable_info') or '').strip()

        it = ObjetivoSGSI(
            objetivo=objetivo,
            indicador=indicador,
            actividades=actividades,
            recursos=recursos,
            forma_calculo=forma_calc,
            meta_pct=meta_pct,
            frecuencia_calculo=frecuencia,
            frecuencia_detalle=frec_det if frecuencia == 'Por Demanda' else '',
            fecha_meta=fecha_meta,
            responsable_calcular=resp_calc,
            responsable_info=resp_info,
        )

        db.session.add(it)
        db.session.commit()
        flash("Objetivo registrado.", "success")
        return redirect(url_for('objetivos_matriz'))

    html = """
    <div class="objform-shell">

      <div class="objform-header-card">
        <div class="objform-header-overlay">
          <div class="objform-header-text">
            <h3 class="objform-title m-0">Agregar Objetivos del SGSI</h3>
            <div class="objform-subtitle">
              Registro de objetivos del Sistema de Gestión de Seguridad de la Información
            </div>
          </div>
        </div>
      </div>

      <div class="objform-header-actions">
        <a href="{{ url_for('objetivos_matriz') }}"
           class="btn rounded-pill px-4 fw-bold objform-back-btn">
          ⬅ Volver a la Matriz
        </a>

      </div>

      <div class="objform-card">
        <div class="objform-card-body">
          <form method="post">
            <div class="row g-3">

              <div class="col-md-12">
                <label class="form-label">Objetivo</label>
                <textarea name="objetivo" class="form-control" rows="2" required></textarea>
              </div>

              <div class="col-md-12">
                <label class="form-label">Indicador</label>
                <textarea name="indicador" class="form-control" rows="2"></textarea>
              </div>

              <div class="col-md-12">
                <label class="form-label">Actividades para lograr el cumplimiento</label>
                <textarea name="actividades" class="form-control" rows="2"></textarea>
              </div>

              <div class="col-md-12">
                <label class="form-label">Recursos</label>
                <textarea name="recursos" class="form-control" rows="2"></textarea>
              </div>

              <div class="col-md-12">
                <label class="form-label">Forma de cálculo del indicador</label>
                <textarea name="forma_calculo" class="form-control" rows="2"></textarea>
              </div>

              <div class="col-md-4">
                <label class="form-label">Meta (%)</label>
                <input type="number" name="meta_pct" class="form-control" min="0" max="100" value="0">
              </div>

              <div class="col-md-4">
                <label class="form-label">Frecuencia de cálculo</label>
                <select name="frecuencia_calculo" id="frecuencia_calculo" class="form-select" onchange="toggleFrecuenciaDetalle()">
                  <option value="">-- Seleccione --</option>
                  <option>Anual</option>
                  <option>Bimensual</option>
                  <option>Trimestral</option>
                  <option>Cuatrimestral</option>
                  <option>Mensual</option>
                  <option>Por Demanda</option>
                </select>
              </div>

              <div class="col-md-4" id="frecuencia_detalle_box" style="display:none;">
                <label class="form-label">Detalle (si es "Por Demanda")</label>
                <input type="text" name="frecuencia_detalle" id="frecuencia_detalle" class="form-control">
              </div>

              <div class="col-md-4">
                <label class="form-label">Fecha de la Meta</label>
                <input type="date" name="fecha_meta" class="form-control">
              </div>

              <div class="col-md-4">
                <label class="form-label">Responsable de calcular el indicador</label>
                <input type="text" name="responsable_calcular" class="form-control">
              </div>

              <div class="col-md-4">
                <label class="form-label">Responsable de suministrar información</label>
                <input type="text" name="responsable_info" class="form-control">
              </div>

            </div>

            <div class="objform-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar
              </button>
              <a href="{{ url_for('objetivos_matriz') }}"
                 class="btn rounded-pill px-4 fw-bold objform-cancel-btn">
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

      .objform-shell{
        width:96%;
        max-width:1300px;
        margin:10px auto 24px auto;
      }

      /* =========================
         HERO SGSI COMPACTO
      ========================== */
      .objform-header-card{
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

      .objform-header-card::before{
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
        pointer-events:none;
      }

      .objform-header-overlay{
        width:100%;
        height:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        padding:0;
        background:transparent;
        position:relative;
        z-index:1;
      }

      .objform-header-overlay::before{
        content:"🎯";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:rgba(255,255,255,.96);
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.55rem;
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .objform-header-text{
        max-width:1100px;
        position:relative;
        z-index:1;
      }

      .objform-header-text::before{
        content:"SGSI · Gestión de Objetivos";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border:1px solid rgba(255,255,255,.30);
        border-radius:999px;
        padding:3px 10px;
        font-size:.66rem;
        font-weight:800;
        letter-spacing:.35px;
        margin-bottom:4px;
      }

      .objform-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.36rem;
        line-height:1.08;
        text-shadow:0 3px 10px rgba(0,0,0,.32);
        margin:0 !important;
      }

      .objform-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
        text-shadow:none;
      }

      /* =========================
         ACCIONES SUPERIORES
      ========================== */
      .objform-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px 0;
      }

      .objform-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .objform-header-actions .btn-primary,
      .objform-header-actions .btn-success{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .objform-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .objform-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         CARD FORMULARIO
      ========================== */
      .objform-card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        overflow:hidden;
        border:1px solid rgba(219,230,244,.9);
      }

      .objform-card-body{
        padding:16px 18px;
      }

      .objform-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .objform-card .form-control,
      .objform-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:37px;
        font-size:.80rem;
        box-shadow:none;
        padding-top:5px;
        padding-bottom:5px;
      }

      .objform-card textarea.form-control{
        min-height:68px;
        resize:vertical;
      }

      .objform-card .form-control:focus,
      .objform-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .18rem rgba(63,134,214,.18);
      }

      .objform-card .row{
        row-gap:10px;
      }

      .objform-card .mb-3{
        margin-bottom:.70rem !important;
      }

      /* =========================
         ACCIONES INFERIORES
      ========================== */
      .objform-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin-top:18px;
      }

      .objform-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 24px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .objform-bottom-actions .btn-primary,
      .objform-bottom-actions .btn-success{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .objform-bottom-actions .btn-danger{
        border:none;
        background:linear-gradient(135deg,#b91c1c,#ef4444);
        color:#fff;
      }

      .objform-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .objform-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         RESPONSIVE
      ========================== */
      @media (max-width:992px){
        .objform-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .objform-header-card{
          min-height:88px;
          padding:15px 18px;
        }

        .objform-title{
          font-size:1.22rem;
        }

        .objform-subtitle{
          font-size:.74rem;
        }

        .objform-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .objform-header-overlay{
          justify-content:center;
          text-align:center;
          flex-direction:column;
          gap:10px;
        }

        .objform-header-overlay::before{
          margin-right:0;
        }

        .objform-title{
          font-size:1.12rem;
        }

        .objform-subtitle{
          font-size:.72rem;
        }

        .objform-header-actions .btn,
        .objform-bottom-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(html)
    return render_template_string(BASE, content=Markup(inner))


# =========================
# MATRIZ — Objetivos SGSI
# =========================
@app.route('/objetivos/matriz')
@login_required
def objetivos_matriz():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Objetivos del Sistema de Gestión"):
            flash("No tiene permiso para ver la Matriz de Objetivos.", "danger")
            return redirect(url_for('menu'))
        read_only = False

    items = ObjetivoSGSI.query.order_by(ObjetivoSGSI.id.desc()).all()

    html = """
    <div class="obj-shell">

      <div class="obj-header-card">
        <div class="obj-header-overlay">
          <div class="obj-header-text">
            <h3 class="obj-title m-0">Objetivos del Sistema de Gestión de Seguridad de la Información</h3>
            <div class="obj-subtitle">
              Consulta rápida de los objetivos del Sistema de Gestión de Seguridad de la Información
            </div>
          </div>
        </div>
      </div>

      <div class="obj-header-actions">
        {% if not read_only %}
          <a href="{{ url_for('objetivos_new') }}"
             class="btn btn-primary rounded-pill px-4 fw-bold">
            ➕ Agregar Objetivos del Sistema
          </a>
        {% endif %}

      </div>

      <div class="obj-table-card">
        <div class="obj-table-topbar">
          <div>
            <h5 class="obj-table-title mb-1">Resumen de Objetivos</h5>
            <div class="obj-table-note">
              La matriz muestra únicamente los campos más importantes. Para consultar el registro completo usa el botón <strong>Ver detalle</strong>.
            </div>
          </div>
          <div class="obj-counter-badge">
            Total registros: {{ items|length }}
          </div>
        </div>

        <div class="obj-table-card-body">
          <div class="table-wrap">
            <div class="table-responsive">
              <table class="table table-bordered table-hover align-middle obj-matriz mb-0">
                <colgroup>
                  <col style="width: 28%;">
                  <col style="width: 20%;">
                  <col style="width: 10%;">
                  <col style="width: 15%;">
                  <col style="width: 13%;">
                  <col style="width: 10%;">
                  <col style="width: 14%;">
                </colgroup>

                <thead>
                  <tr>
                    <th>Objetivo</th>
                    <th>Indicador</th>
                    <th>Meta (%)</th>
                    <th>Responsable</th>
                    <th>Frecuencia</th>
                    <th>Fecha meta</th>
                    <th>Acciones</th>
                  </tr>
                </thead>

                <tbody>
                  {% for it in items %}
                    <tr>
                      <td class="obj-cell-main">
                        <div class="obj-main-text">{{ it.objetivo or '—' }}</div>
                      </td>

                      <td>{{ it.indicador or '—' }}</td>

                      <td class="text-center fw-bold">
                        {{ (it.meta_pct ~ '%') if it.meta_pct is not none else '—' }}
                      </td>

                      <td>{{ obtener_responsable_objetivo(it) }}</td>

                      <td>
                        {{ it.frecuencia_calculo or '—' }}
                        {% if it.frecuencia_calculo == 'Por Demanda' and it.frecuencia_detalle %}
                          <div class="obj-mini-note">Detalle: {{ it.frecuencia_detalle }}</div>
                        {% endif %}
                      </td>

                      <td class="text-center">
                        {{ format_fecha_corta(it.fecha_meta) }}
                      </td>

                      <td class="text-center">
                        <div class="acciones-wrap">
                          <a href="{{ url_for('objetivos_detalle', id=it.id) }}"
                             class="btn btn-info btn-sm rounded-pill px-3 fw-bold text-white">
                            Ver detalle
                          </a>

                          {% if not read_only %}
                            <a href="{{ url_for('objetivos_edit', id=it.id) }}"
                               class="btn btn-warning btn-sm rounded-pill px-3 fw-bold">
                              Editar
                            </a>

                            <a href="{{ url_for('objetivos_delete', id=it.id) }}"
                               class="btn btn-danger btn-sm rounded-pill px-3 fw-bold"
                               onclick="return confirm('¿Eliminar este objetivo?');">
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
                      <td colspan="7" class="text-center text-muted py-5">
                        No hay registros de objetivos para mostrar.
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

      .obj-shell{
        width:96%;
        max-width:1650px;
        margin:10px auto 24px auto;
      }

      /* =========================
         HERO SGSI COMPACTO
      ========================== */
      .obj-header-card{
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

      .obj-header-card::before{
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
        pointer-events:none;
      }

      .obj-header-overlay{
        width:100%;
        height:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        padding:0;
        background:transparent;
        position:relative;
        z-index:1;
      }

      .obj-header-overlay::before{
        content:"🎯";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:rgba(255,255,255,.96);
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.55rem;
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .obj-header-text{
        max-width:1100px;
        position:relative;
        z-index:1;
      }

      .obj-header-text::before{
        content:"SGSI · Objetivos";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border:1px solid rgba(255,255,255,.30);
        border-radius:999px;
        padding:3px 10px;
        font-size:.66rem;
        font-weight:800;
        letter-spacing:.35px;
        margin-bottom:4px;
      }

      .obj-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.36rem;
        line-height:1.08;
        text-shadow:0 3px 10px rgba(0,0,0,.32);
        margin:0 !important;
      }

      .obj-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
        text-shadow:none;
      }

      /* =========================
         ACCIONES SUPERIORES
      ========================== */
      .obj-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px 0;
      }

      .obj-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .obj-header-actions .btn-primary,
      .obj-header-actions .btn-success{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .obj-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .obj-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         CARD TABLA
      ========================== */
      .obj-table-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        overflow:hidden;
        border:1px solid rgba(219,230,244,.9);
      }

      .obj-table-topbar{
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:12px;
        padding:14px 16px 0 16px;
        flex-wrap:wrap;
      }

      .obj-table-title{
        color:#0f172a;
        font-weight:950;
        font-size:.94rem;
        margin:0;
      }

      .obj-table-note{
        color:#475569;
        font-size:.78rem;
        margin-top:3px;
      }

      .obj-counter-badge{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        color:#fff;
        font-weight:900;
        border-radius:999px;
        padding:7px 14px;
        font-size:.78rem;
        box-shadow:0 8px 16px rgba(15,23,42,.16);
      }

      .obj-table-card-body{
        padding:12px 16px 16px 16px;
      }

      .table-wrap{
        max-height:70vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:rgba(255,255,255,.99);
      }

      .obj-matriz{
        min-width:1200px;
        margin-bottom:0;
        table-layout:fixed;
        border-collapse:separate;
        border-spacing:0;
      }

      .obj-matriz thead th{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff;
        font-weight:900;
        text-align:center;
        vertical-align:middle;
        padding:11px 9px;
        font-size:.68rem;
        border-right:1px solid rgba(255,255,255,.28);
      }

      .obj-matriz thead th:first-child{
        border-top-left-radius:12px;
      }

      .obj-matriz thead th:last-child{
        border-top-right-radius:12px;
      }

      .obj-matriz td{
        vertical-align:top;
        font-size:.68rem;
        padding:9px 8px;
        color:#101827;
        border-right:1px solid #dce6f3;
        border-bottom:1px solid #dce6f3;
        background:rgba(255,255,255,.98);
        word-break:break-word;
      }

      .obj-matriz tbody tr:nth-child(even) td{
        background:#f8fbff;
      }

      .obj-matriz tbody tr:hover td{
        background:#eef6ff;
      }

      .obj-cell-main .obj-main-text{
        font-weight:900;
        color:#0f172a;
        line-height:1.35;
      }

      .obj-mini-note{
        margin-top:5px;
        font-size:.70rem;
        color:#475569;
        line-height:1.25;
      }

      .acciones-wrap{
        display:flex;
        flex-direction:column;
        gap:6px;
        align-items:center;
        justify-content:center;
      }

      .acciones-wrap .btn,
      .obj-matriz .btn{
        min-width:86px;
        min-height:28px;
        border-radius:999px !important;
        padding:4px 12px !important;
        font-size:.70rem;
        font-weight:900;
        text-decoration:none;
        display:inline-flex;
        align-items:center;
        justify-content:center;
      }

      .obj-matriz .btn-info{
        background:#087ab8;
        border:none;
        color:#fff;
      }

      .obj-matriz .btn-warning{
        background:#c76b00;
        border:none;
        color:#0b1220;
      }

      .obj-matriz .btn-danger{
        background:#b91c1c;
        border:none;
        color:#fff;
      }

      .obj-matriz .btn-success{
        background:#087c3d;
        border:none;
        color:#fff;
      }

      /* =========================
         SCROLLBAR
      ========================== */
      .table-wrap::-webkit-scrollbar{
        height:11px;
        width:11px;
      }

      .table-wrap::-webkit-scrollbar-track{
        background:#dbe4f0;
        border-radius:12px;
      }

      .table-wrap::-webkit-scrollbar-thumb{
        background:linear-gradient(180deg,#5aa3ea,#3f86d6);
        border-radius:12px;
        border:2px solid #dbe4f0;
      }

      .table-wrap{
        scrollbar-width:thin;
        scrollbar-color:#3f86d6 #dbe4f0;
      }

      /* =========================
         RESPONSIVE
      ========================== */
      @media (max-width:992px){
        .obj-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .obj-header-card{
          min-height:88px;
          padding:15px 18px;
        }

        .obj-title{
          font-size:1.22rem;
        }

        .obj-subtitle{
          font-size:.74rem;
        }

        .obj-table-topbar{
          padding:12px 14px 0 14px;
        }

        .obj-table-card-body{
          padding:12px 14px 14px 14px;
        }
      }

      @media (max-width:768px){
        .obj-header-overlay{
          justify-content:center;
          text-align:center;
          flex-direction:column;
          gap:10px;
        }

        .obj-header-overlay::before{
          margin-right:0;
        }

        .obj-title{
          font-size:1.12rem;
        }

        .obj-subtitle{
          font-size:.72rem;
        }

        .obj-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(
        html,
        items=items,
        read_only=read_only,
        obtener_responsable_objetivo=obtener_responsable_objetivo,
        format_fecha_corta=format_fecha_corta
    )
    return render_template_string(BASE, content=Markup(inner))


# =========================
# DETALLE — Objetivo SGSI
# =========================
@app.route('/objetivos/detalle/<int:id>')
@login_required
def objetivos_detalle(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Objetivos del Sistema de Gestión"):
            flash("No tiene permiso para ver el detalle del objetivo.", "danger")
            return redirect(url_for('objetivos_matriz'))
        read_only = False

    it = ObjetivoSGSI.query.get_or_404(id)

    def ffecha(v):
        if not v:
            return '—'
        try:
            return v.strftime('%Y-%m-%d')
        except Exception:
            return str(v)

    html = """
    <div class="objd-shell">

      <div class="objd-header-card">
        <div class="objd-header-overlay">
          <div class="objd-header-text">
            <h3 class="objd-title m-0">Detalle del Objetivo SGSI</h3>
            <div class="objd-subtitle">
              Consulta completa del registro en modo solo lectura
            </div>
          </div>
        </div>
      </div>

      <div class="objd-header-actions">
        <a href="{{ url_for('objetivos_matriz') }}"
           class="btn rounded-pill px-4 fw-bold objd-back-btn">
          ⬅ Volver a la Matriz
        </a>

        {% if not read_only %}
          <a href="{{ url_for('objetivos_edit', id=it.id) }}"
             class="btn btn-warning rounded-pill px-4 fw-bold">
            Editar registro
          </a>
        {% endif %}
      </div>

      <div class="objd-card">
        <div class="objd-card-body">

          <div class="objd-section">
            <div class="objd-section-title">Información principal</div>
            <div class="row g-3">
              <div class="col-md-12">
                <div class="objd-field">
                  <div class="objd-label">Objetivo</div>
                  <div class="objd-value objd-value-lg">{{ it.objetivo or '—' }}</div>
                </div>
              </div>

              <div class="col-md-6">
                <div class="objd-field">
                  <div class="objd-label">Indicador</div>
                  <div class="objd-value">{{ it.indicador or '—' }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="objd-field">
                  <div class="objd-label">Meta (%)</div>
                  <div class="objd-value">{{ (it.meta_pct ~ '%') if it.meta_pct is not none else '—' }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="objd-field">
                  <div class="objd-label">Fecha meta</div>
                  <div class="objd-value">{{ ffecha(it.fecha_meta) }}</div>
                </div>
              </div>
            </div>
          </div>

          <div class="objd-section">
            <div class="objd-section-title">Responsables y seguimiento</div>
            <div class="row g-3">
              <div class="col-md-6">
                <div class="objd-field">
                  <div class="objd-label">Responsable de calcular el indicador</div>
                  <div class="objd-value">{{ it.responsable_calcular or '—' }}</div>
                </div>
              </div>

              <div class="col-md-6">
                <div class="objd-field">
                  <div class="objd-label">Responsable de suministrar información</div>
                  <div class="objd-value">{{ it.responsable_info or '—' }}</div>
                </div>
              </div>

              <div class="col-md-6">
                <div class="objd-field">
                  <div class="objd-label">Frecuencia de cálculo</div>
                  <div class="objd-value">
                    {{ it.frecuencia_calculo or '—' }}
                    {% if it.frecuencia_calculo == 'Por Demanda' and it.frecuencia_detalle %}
                      <div class="objd-subvalue">Detalle: {{ it.frecuencia_detalle }}</div>
                    {% endif %}
                  </div>
                </div>
              </div>

              <div class="col-md-6">
                <div class="objd-field">
                  <div class="objd-label">Forma de cálculo del indicador</div>
                  <div class="objd-value">{{ it.forma_calculo or '—' }}</div>
                </div>
              </div>
            </div>
          </div>

          <div class="objd-section">
            <div class="objd-section-title">Planeación y ejecución</div>
            <div class="row g-3">
              <div class="col-md-6">
                <div class="objd-field">
                  <div class="objd-label">Actividades</div>
                  <div class="objd-value">{{ it.actividades or '—' }}</div>
                </div>
              </div>

              <div class="col-md-6">
                <div class="objd-field">
                  <div class="objd-label">Recursos</div>
                  <div class="objd-value">{{ it.recursos or '—' }}</div>
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

      .objd-shell{
        width:96%;
        max-width:1250px;
        margin:10px auto 24px auto;
      }

      /* =========================
         HERO SGSI COMPACTO
      ========================== */
      .objd-header-card{
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

      .objd-header-card::before{
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
        pointer-events:none;
      }

      .objd-header-overlay{
        width:100%;
        height:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        padding:0;
        background:transparent;
        position:relative;
        z-index:1;
      }

      .objd-header-overlay::before{
        content:"🎯";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:rgba(255,255,255,.96);
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.55rem;
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .objd-header-text{
        max-width:1100px;
        position:relative;
        z-index:1;
      }

      .objd-header-text::before{
        content:"SGSI · Detalle del Objetivo";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border:1px solid rgba(255,255,255,.30);
        border-radius:999px;
        padding:3px 10px;
        font-size:.66rem;
        font-weight:800;
        letter-spacing:.35px;
        margin-bottom:4px;
      }

      .objd-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.36rem;
        line-height:1.08;
        text-shadow:0 3px 10px rgba(0,0,0,.32);
        margin:0 !important;
      }

      .objd-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
        text-shadow:none;
      }

      /* =========================
         ACCIONES
      ========================== */
      .objd-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px 0;
      }

      .objd-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .objd-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .objd-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         CARD PRINCIPAL
      ========================== */
      .objd-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        overflow:hidden;
        border:1px solid rgba(219,230,244,.9);
      }

      .objd-card-body{
        padding:16px 18px;
      }

      /* =========================
         SECCIONES
      ========================== */
      .objd-section{
        margin-bottom:14px;
        background:#ffffff;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:8px 7px;
        box-shadow:0 8px 18px rgba(15,23,42,.08);
      }

      .objd-section:last-child{
        margin-bottom:0;
      }

      .objd-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:0 0 12px 0;
      }

      /* =========================
         CAMPOS DETALLE
      ========================== */
      .objd-field{
        background:linear-gradient(180deg,#f8fbff 0%,#ffffff 100%);
        border:1px solid #dbe6f4;
        border-radius:14px;
        padding:12px;
        min-height:100%;
        box-shadow:inset 0 0 0 1px rgba(255,255,255,.45);
      }

      .objd-label{
        font-size:.70rem;
        font-weight:900;
        text-transform:uppercase;
        letter-spacing:.35px;
        color:#0b4a8f;
        margin-bottom:6px;
      }

      .objd-value{
        color:#101827;
        font-size:.82rem;
        line-height:1.38;
        white-space:pre-wrap;
        word-break:break-word;
      }

      .objd-value-lg{
        font-size:.90rem;
        font-weight:900;
        color:#0f172a;
        line-height:1.35;
      }

      .objd-subvalue{
        margin-top:7px;
        font-size:.74rem;
        color:#475569;
        line-height:1.3;
      }

      /* =========================
         RESPONSIVE
      ========================== */
      @media (max-width:992px){
        .objd-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .objd-header-card{
          min-height:88px;
          padding:15px 18px;
        }

        .objd-title{
          font-size:1.22rem;
        }

        .objd-subtitle{
          font-size:.74rem;
        }

        .objd-card-body{
          padding:8px 7px;
        }

        .objd-section{
          padding:12px;
        }
      }

      @media (max-width:768px){
        .objd-header-overlay{
          justify-content:center;
          text-align:center;
          flex-direction:column;
          gap:10px;
        }

        .objd-header-overlay::before{
          margin-right:0;
        }

        .objd-title{
          font-size:1.12rem;
        }

        .objd-subtitle{
          font-size:.72rem;
        }

        .objd-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(
        html,
        it=it,
        read_only=read_only,
        ffecha=ffecha
    )
    return render_template_string(BASE, content=Markup(inner))


# =========================
# EDITAR — Objetivo SGSI
# =========================
@app.route('/objetivos/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def objetivos_edit(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor' or (
        user.role != 'admin'
        and not verificar_permiso(user, "Objetivos del Sistema de Gestión")
    ):
        flash("No tiene permiso para editar objetivos.", "danger")
        return redirect(url_for('objetivos_matriz'))

    item = ObjetivoSGSI.query.get_or_404(id)
    FRECUENCIAS = ['Anual', 'Bimensual', 'Trimestral', 'Cuatrimestral', 'Mensual', 'Por Demanda']

    if request.method == 'POST':
        item.objetivo             = request.form.get('objetivo') or ''
        item.indicador            = request.form.get('indicador') or ''
        item.actividades          = request.form.get('actividades') or ''
        item.recursos             = request.form.get('recursos') or ''
        item.forma_calculo        = request.form.get('forma_calculo') or ''
        item.meta_pct             = request.form.get('meta_pct', type=int) or 0
        item.frecuencia_calculo   = request.form.get('frecuencia_calculo') or ''
        item.frecuencia_detalle   = request.form.get('frecuencia_detalle') or ''
        item.fecha_meta           = request.form.get('fecha_meta') or ''
        item.responsable_calcular = request.form.get('responsable_calcular') or ''
        item.responsable_info     = request.form.get('responsable_info') or ''

        db.session.commit()
        flash("Objetivo actualizado.", "success")
        return redirect(url_for('objetivos_matriz'))

    html = """
    <div class="objform-shell">

      <div class="objform-header-card">
        <div class="objform-header-overlay">
          <div class="objform-header-text">
            <h3 class="objform-title m-0">Editar Objetivo del SGSI</h3>
            <div class="objform-subtitle">
              Actualización de la información del objetivo del Sistema de Gestión de Seguridad de la Información
            </div>
          </div>
        </div>
      </div>

      <div class="objform-header-actions">
        <a href="{{ url_for('objetivos_matriz') }}"
           class="btn rounded-pill px-4 fw-bold objform-back-btn">
          ⬅ Volver a la Matriz
        </a>

      </div>

      <div class="objform-card">
        <div class="objform-card-body">
          <form method="post">
            <div class="row g-3">

              <div class="col-md-6">
                <label class="form-label">Objetivo</label>
                <input class="form-control" name="objetivo" value="{{ item.objetivo }}">
              </div>

              <div class="col-md-6">
                <label class="form-label">Indicador</label>
                <input class="form-control" name="indicador" value="{{ item.indicador }}">
              </div>

              <div class="col-md-12">
                <label class="form-label">Actividades para lograr el cumplimiento</label>
                <textarea class="form-control" name="actividades" rows="2">{{ item.actividades }}</textarea>
              </div>

              <div class="col-md-12">
                <label class="form-label">Recursos</label>
                <textarea class="form-control" name="recursos" rows="2">{{ item.recursos }}</textarea>
              </div>

              <div class="col-md-6">
                <label class="form-label">Forma de cálculo del indicador</label>
                <textarea class="form-control" name="forma_calculo" rows="2">{{ item.forma_calculo }}</textarea>
              </div>

              <div class="col-md-2">
                <label class="form-label">Meta (%)</label>
                <input type="number"
                       class="form-control"
                       name="meta_pct"
                       min="0" max="100"
                       value="{{ item.meta_pct or 0 }}">
              </div>

              <div class="col-md-4">
                <label class="form-label">Frecuencia de cálculo</label>
                <select name="frecuencia_calculo"
                        class="form-select"
                        onchange="showDetalle(this.value)">
                  <option value="">-- Seleccione --</option>
                  {% for f in FRECUENCIAS %}
                    <option value="{{ f }}" {% if item.frecuencia_calculo == f %}selected{% endif %}>
                      {{ f }}
                    </option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-12"
                   id="div_detalle"
                   style="display:{% if item.frecuencia_calculo == 'Por Demanda' %}block{% else %}none{% endif %};">
                <label class="form-label">Detalle de frecuencia (cuando es "Por Demanda")</label>
                <textarea class="form-control" name="frecuencia_detalle" rows="2">{{ item.frecuencia_detalle }}</textarea>
              </div>

              <div class="col-md-3">
                <label class="form-label">Fecha de la Meta</label>
                <input type="date" class="form-control" name="fecha_meta" value="{{ item.fecha_meta or '' }}">
              </div>

              <div class="col-md-4">
                <label class="form-label">Responsable de calcular el indicador</label>
                <input class="form-control" name="responsable_calcular" value="{{ item.responsable_calcular }}">
              </div>

              <div class="col-md-5">
                <label class="form-label">Responsable de suministrar información</label>
                <input class="form-control" name="responsable_info" value="{{ item.responsable_info }}">
              </div>

            </div>

            <div class="objform-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar cambios
              </button>
              <a href="{{ url_for('objetivos_matriz') }}"
                 class="btn rounded-pill px-4 fw-bold objform-cancel-btn">
                Cancelar
              </a>
            </div>
          </form>
        </div>
      </div>

    </div>

    <script>
      function showDetalle(v){
        document.getElementById('div_detalle').style.display =
          (v === "Por Demanda") ? "block" : "none";
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

      .objform-shell{
        width:96%;
        max-width:1300px;
        margin:10px auto 24px auto;
      }

      /* =========================
         HERO SGSI (UNIFICADO)
      ========================== */
      .objform-header-card{
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

      .objform-header-card::before{
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
        pointer-events:none;
      }

      .objform-header-overlay{
        width:100%;
        height:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        padding:0;
        background:transparent;
        position:relative;
        z-index:1;
      }

      .objform-header-overlay::before{
        content:"🎯";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:rgba(255,255,255,.96);
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.55rem;
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .objform-header-text{
        max-width:1100px;
        position:relative;
        z-index:1;
      }

      .objform-header-text::before{
        content:"SGSI · Gestión de Objetivos";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border:1px solid rgba(255,255,255,.30);
        border-radius:999px;
        padding:3px 10px;
        font-size:.66rem;
        font-weight:800;
        letter-spacing:.35px;
        margin-bottom:4px;
      }

      .objform-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.36rem;
        line-height:1.08;
        text-shadow:0 3px 10px rgba(0,0,0,.32);
        margin:0 !important;
      }

      .objform-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
        text-shadow:none;
      }

      /* =========================
         ACCIONES
      ========================== */
      .objform-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px 0;
      }

      .objform-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .objform-header-actions .btn-primary,
      .objform-header-actions .btn-success{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .objform-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .objform-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         CARD FORMULARIO
      ========================== */
      .objform-card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        overflow:hidden;
        border:1px solid rgba(219,230,244,.9);
      }

      .objform-card-body{
        padding:16px 18px;
      }

      /* =========================
         FORMULARIOS COMPACTOS
      ========================== */
      .objform-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .objform-card .form-control,
      .objform-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:37px;
        font-size:.80rem;
        background:#f8fafc;
        box-shadow:none;
      }

      .objform-card textarea.form-control{
        min-height:70px;
        resize:vertical;
      }

      .objform-card .form-control:focus,
      .objform-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .18rem rgba(63,134,214,.18);
      }

      .objform-card .row{
        row-gap:10px;
      }

      .objform-card .mb-3{
        margin-bottom:.70rem !important;
      }

      /* =========================
         BOTONES
      ========================== */
      .objform-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin-top:18px;
      }

      .objform-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 24px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .objform-bottom-actions .btn-primary,
      .objform-bottom-actions .btn-success{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .objform-bottom-actions .btn-danger{
        border:none;
        background:linear-gradient(135deg,#b91c1c,#ef4444);
        color:#fff;
      }

      .objform-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .objform-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         RESPONSIVE
      ========================== */
      @media (max-width:992px){
        .objform-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .objform-header-card{
          min-height:88px;
          padding:15px 18px;
        }

        .objform-title{
          font-size:1.22rem;
        }

        .objform-subtitle{
          font-size:.74rem;
        }

        .objform-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .objform-header-overlay{
          justify-content:center;
          text-align:center;
          flex-direction:column;
          gap:10px;
        }

        .objform-header-overlay::before{
          margin-right:0;
        }

        .objform-title{
          font-size:1.12rem;
        }

        .objform-subtitle{
          font-size:.72rem;
        }

        .objform-bottom-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(html, item=item, FRECUENCIAS=FRECUENCIAS)
    return render_template_string(BASE, content=Markup(inner))


# =========================
# ELIMINAR — Objetivo SGSI
# =========================
@app.route('/objetivos/delete/<int:id>')
@login_required
def objetivos_delete(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor' or (
        user.role != 'admin'
        and not verificar_permiso(user, "Objetivos del Sistema de Gestión")
    ):
        flash("No tiene permiso para eliminar objetivos.", "danger")
        return redirect(url_for('objetivos_matriz'))

    obj = ObjetivoSGSI.query.get_or_404(id)
    db.session.delete(obj)
    db.session.commit()
    flash("Objetivo eliminado.", "success")
    return redirect(url_for('objetivos_matriz'))


# ============================================================================================================================================
#                                    Fin del Módulo Objetivo del Sistema de Gestión de Seguridad
# ============================================================================================================================================

# ==========================================================================================================================================
#                                                               Módulo Partes Interesadas
# ==========================================================================================================================================

class ParteInteresada(db.Model):
    __tablename__ = 'partes_interesadas'

    id = db.Column(db.Integer, primary_key=True)

    parte_interesada = db.Column(db.String(200), nullable=False)
    necesidades_expectativas = db.Column(db.Text, nullable=False)
    requisitos_aplicables = db.Column(db.Text, nullable=False)
    fecha_revision = db.Column(db.Date, nullable=True)

    evidencias = db.relationship(
        "ParteInteresadaEvidencia",
        backref="registro",
        cascade="all, delete-orphan",
        lazy=True
    )


class ParteInteresadaEvidencia(db.Model):
    __tablename__ = 'parte_interesada_evidencia'

    id = db.Column(db.Integer, primary_key=True)

    registro_id = db.Column(
        db.Integer,
        db.ForeignKey('partes_interesadas.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    filename = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    mime = db.Column(db.String(120), default='application/pdf')
    size = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# =======
# Helpers
# =======

def is_allowed_pdf(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'

def unique_store_name(filename: str) -> str:
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'pdf'
    return f"{uuid.uuid4().hex}.{ext}"

def format_fecha_partes(valor):
    if not valor:
        return '—'
    try:
        return valor.strftime('%Y-%m-%d')
    except Exception:
        return str(valor)

def resumir_texto(valor, limite=120):
    if not valor:
        return '—'
    txt = str(valor).strip()
    if len(txt) <= limite:
        return txt
    return txt[:limite].rstrip() + '...'


# =========================
# ENTRADA DIRECTA AL MÓDULO
# =========================
@app.route('/partes_menu')
@login_required
def partes_menu():
    user = User.query.get(session.get('user_id'))

    if user.role not in ('admin', 'auditor') and not verificar_permiso(user, "Partes Interesadas"):
        flash("No tiene permiso para acceder al módulo de partes interesadas.", "danger")
        return redirect(url_for('menu'))

    return redirect(url_for('partes_interesadas_matriz'))


# =========================
# Agregar Partes Interesadas
# =========================
@app.route('/partes_interesadas/new', methods=['GET', 'POST'])
@login_required
def parte_interesada_new():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede agregar registros.", "danger")
        return redirect(url_for('partes_interesadas_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Partes Interesadas"):
        flash("No tiene permiso para agregar registro de partes interesadas.", "danger")
        return redirect(url_for('partes_interesadas_matriz'))

    if request.method == 'POST':
        parte_interesada = (request.form.get('parte_interesada') or '').strip()
        necesidades = (request.form.get('necesidades_expectativas') or '').strip()
        requisitos = (request.form.get('requisitos_aplicables') or '').strip()
        fecha_str = (request.form.get('fecha_revision') or '').strip()

        fecha_revision = None
        if fecha_str:
            try:
                fecha_revision = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            except ValueError:
                flash("Fecha de revisión inválida.", "danger")
                return redirect(url_for('parte_interesada_new'))

        if not all([parte_interesada, necesidades, requisitos]):
            flash("Campos obligatorios: Parte interesada, Necesidades/Expectativas y Requisitos aplicables.", "danger")
            return redirect(url_for('parte_interesada_new'))

        it = ParteInteresada(
            parte_interesada=parte_interesada,
            necesidades_expectativas=necesidades,
            requisitos_aplicables=requisitos,
            fecha_revision=fecha_revision
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
            path = os.path.join(app.config['UPLOAD_PARTES_INTERESADAS_DIR'], store_name)
            f.save(path)

            ev = ParteInteresadaEvidencia(
                registro=it,
                filename=store_name,
                original_name=secure_filename(f.filename),
                mime='application/pdf',
                size=os.path.getsize(path)
            )
            db.session.add(ev)

        db.session.commit()
        flash("Parte interesada registrada.", "success")
        return redirect(url_for('partes_interesadas_matriz'))

    html = """
    <div class="partesnew-shell">

      <div class="partesnew-header-card">
        <div class="partesnew-header-overlay">
          <div class="partesnew-header-text">
            <h3 class="partesnew-title m-0">Agregar Parte Interesada</h3>
            <div class="partesnew-subtitle">
              Registro de partes interesadas, necesidades, requisitos aplicables y evidencias del SGSI
            </div>
          </div>
        </div>
      </div>

      <div class="partesnew-header-actions">
        <a href="{{ url_for('partes_interesadas_matriz') }}"
           class="btn rounded-pill px-4 fw-bold partesnew-back-btn">
          ⬅ Volver a la Matriz
        </a>

      </div>

      <div class="partesnew-card">
        <div class="partesnew-card-body">
          <form method="post" enctype="multipart/form-data">
            <div class="row g-3">

              <div class="col-md-6">
                <label class="form-label">Parte Interesada</label>
                <input name="parte_interesada" class="form-control" required>
              </div>

              <div class="col-md-6">
                <label class="form-label">Fecha de Revisión</label>
                <input type="date" name="fecha_revision" class="form-control">
              </div>

              <div class="col-md-12">
                <label class="form-label">Necesidades / Expectativas</label>
                <textarea name="necesidades_expectativas" class="form-control" rows="2" required></textarea>
              </div>

              <div class="col-md-12">
                <label class="form-label">Requisitos Aplicables</label>
                <textarea name="requisitos_aplicables" class="form-control" rows="2" required></textarea>
              </div>

              <div class="col-md-12">
                <label class="form-label">Evidencias PDF</label>

                <div class="partesnew-upload-box">
                  <div class="partesnew-upload-icon">📄</div>
                  <div class="partesnew-upload-title">Adjuntar evidencias del registro</div>
                  <div class="partesnew-upload-subtitle2">
                    Puede cargar varios archivos PDF al mismo tiempo o en varias rondas.
                  </div>

                  <div class="mt-3">
                    <input
                      type="file"
                      id="evidencias"
                      name="evidencias"
                      accept=".pdf"
                      multiple
                      class="form-control partesnew-file-input"
                      onchange="acumularEvidencias(this)"
                    >
                  </div>

                  <div class="partesnew-upload-note mt-2">
                    Solo se permiten archivos en formato PDF.
                  </div>
                </div>
              </div>

              <div class="col-md-12">
                <label class="form-label mt-2">Archivos seleccionados</label>
                <div id="lista_evidencias_nuevas" class="partesnew-files-grid mt-2"></div>
              </div>

            </div>

            <div class="partesnew-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar
              </button>
              <a href="{{ url_for('partes_interesadas_matriz') }}"
                 class="btn rounded-pill px-4 fw-bold partesnew-cancel-btn">
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

      .partesnew-shell{
        width:96%;
        max-width:1300px;
        margin:10px auto 24px auto;
      }

      /* =========================
         HERO SGSI UNIFICADO
      ========================== */
      .partesnew-header-card{
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

      .partesnew-header-card::before{
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
        pointer-events:none;
      }

      .partesnew-header-overlay{
        width:100%;
        height:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        padding:0;
        background:transparent;
        position:relative;
        z-index:1;
      }

      .partesnew-header-overlay::before{
        content:"📄";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:rgba(255,255,255,.96);
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.55rem;
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .partesnew-header-text{
        max-width:1100px;
        position:relative;
        z-index:1;
      }

      .partesnew-header-text::before{
        content:"SGSI · Partes Interesadas";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border:1px solid rgba(255,255,255,.30);
        border-radius:999px;
        padding:3px 10px;
        font-size:.66rem;
        font-weight:800;
        letter-spacing:.35px;
        margin-bottom:4px;
      }

      .partesnew-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.36rem;
        line-height:1.08;
        text-shadow:0 3px 10px rgba(0,0,0,.32);
        margin:0 !important;
      }

      .partesnew-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
        text-shadow:none;
      }

      /* =========================
         ACCIONES
      ========================== */
      .partesnew-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px 0;
      }

      .partesnew-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .partesnew-header-actions .btn-primary,
      .partesnew-header-actions .btn-success{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .partesnew-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .partesnew-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         CARD FORMULARIO
      ========================== */
      .partesnew-card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        overflow:hidden;
        border:1px solid rgba(219,230,244,.9);
      }

      .partesnew-card-body{
        padding:16px 18px;
      }

      .partesnew-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .partesnew-card .form-control,
      .partesnew-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:37px;
        font-size:.80rem;
        background:#f8fafc;
        box-shadow:none;
        padding-top:5px;
        padding-bottom:5px;
      }

      .partesnew-card textarea.form-control{
        min-height:70px;
        resize:vertical;
      }

      .partesnew-card .form-control:focus,
      .partesnew-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .18rem rgba(63,134,214,.18);
      }

      .partesnew-card .row{
        row-gap:10px;
      }

      .partesnew-card .mb-3{
        margin-bottom:.70rem !important;
      }

      /* =========================
         UPLOAD BOX
      ========================== */
      .partesnew-upload-box{
        background:linear-gradient(180deg,#f8fbff 0%,#ffffff 100%);
        border:1.5px dashed #7fb0e6;
        border-radius:16px;
        padding:18px;
        text-align:center;
        box-shadow:inset 0 1px 0 rgba(255,255,255,.75),0 8px 18px rgba(15,23,42,.08);
      }

      .partesnew-upload-icon{
        width:54px;
        height:54px;
        margin:0 auto 8px auto;
        border-radius:14px;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.55rem;
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        color:#fff;
        box-shadow:0 8px 18px rgba(47,111,182,.24);
      }

      .partesnew-upload-title{
        font-size:.94rem;
        font-weight:950;
        color:#0f172a;
      }

      .partesnew-upload-subtitle2{
        font-size:.78rem;
        color:#475569;
        margin-top:4px;
      }

      .partesnew-upload-note{
        font-size:.74rem;
        color:#475569;
      }

      .partesnew-file-input{
        max-width:620px;
        margin:0 auto;
      }

      .partesnew-files-grid{
        display:grid;
        grid-template-columns:repeat(auto-fill,minmax(240px,1fr));
        gap:10px;
        min-height:60px;
      }

      .partesnew-file-card{
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:7px;
        background:linear-gradient(180deg,#ffffff 0%,#f8fbff 100%);
        border:1px solid #dbe6f4;
        border-radius:14px;
        padding:10px 12px;
        box-shadow:0 6px 14px rgba(15,23,42,.08);
      }

      .partesnew-file-left{
        display:flex;
        align-items:center;
        gap:7px;
        min-width:0;
      }

      .partesnew-file-pdf{
        width:32px;
        height:32px;
        min-width:32px;
        border-radius:11px;
        background:linear-gradient(135deg,#b91c1c,#ef4444);
        color:#fff;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1rem;
        box-shadow:0 6px 14px rgba(211,47,47,.20);
      }

      .partesnew-file-meta{
        min-width:0;
      }

      .partesnew-file-name{
        font-size:.78rem;
        font-weight:900;
        color:#0b1220;
        white-space:nowrap;
        overflow:hidden;
        text-overflow:ellipsis;
        max-width:160px;
      }

      .partesnew-file-status{
        font-size:.70rem;
        color:#475569;
        margin-top:2px;
      }

      .partesnew-file-remove{
        border:none;
        background:rgba(220,38,38,.10);
        color:#b91c1c;
        width:30px;
        height:30px;
        border-radius:50%;
        font-size:.85rem;
        transition:all .2s ease;
      }

      .partesnew-file-remove:hover{
        background:rgba(220,38,38,.18);
        transform:scale(1.06);
      }

      /* =========================
         BOTONES INFERIORES
      ========================== */
      .partesnew-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin-top:18px;
      }

      .partesnew-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 24px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .partesnew-bottom-actions .btn-primary,
      .partesnew-bottom-actions .btn-success{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .partesnew-bottom-actions .btn-danger{
        border:none;
        background:linear-gradient(135deg,#b91c1c,#ef4444);
        color:#fff;
      }

      .partesnew-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .partesnew-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         RESPONSIVE
      ========================== */
      @media (max-width:992px){
        .partesnew-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .partesnew-header-card{
          min-height:88px;
          padding:15px 18px;
        }

        .partesnew-title{
          font-size:1.22rem;
        }

        .partesnew-subtitle{
          font-size:.74rem;
        }

        .partesnew-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .partesnew-header-overlay{
          justify-content:center;
          text-align:center;
          flex-direction:column;
          gap:10px;
        }

        .partesnew-header-overlay::before{
          margin-right:0;
        }

        .partesnew-title{
          font-size:1.12rem;
        }

        .partesnew-subtitle{
          font-size:.72rem;
        }

        .partesnew-bottom-actions .btn,
        .partesnew-header-actions .btn{
          width:100%;
        }
      }
    </style>

    <script>
      let evidenciasBufferDT = new DataTransfer();

      function formatFileSize(bytes) {
        if (!bytes || bytes <= 0) return '0 KB';
        const kb = bytes / 1024;
        if (kb < 1024) return `${kb.toFixed(1)} KB`;
        return `${(kb / 1024).toFixed(2)} MB`;
      }

      function renderListaEvidencias() {
        const cont = document.getElementById('lista_evidencias_nuevas');
        if (!cont) return;
        cont.innerHTML = '';

        if (evidenciasBufferDT.files.length === 0) {
          cont.innerHTML = `
            <div class="text-muted small" style="
              background: rgba(255,255,255,.75);
              border:1px dashed #cfd8e3;
              border-radius:14px;
              padding:18px;
              text-align:center;">
              No hay archivos seleccionados
            </div>
          `;
          return;
        }

        for (let i = 0; i < evidenciasBufferDT.files.length; i++) {
          const f = evidenciasBufferDT.files[i];
          const card = document.createElement('div');
          card.className = 'partesnew-file-card';
          card.innerHTML = `
            <div class="partesnew-file-left">
              <div class="partesnew-file-pdf">PDF</div>
              <div class="partesnew-file-meta">
                <div class="partesnew-file-name" title="${f.name}">${f.name}</div>
                <div class="partesnew-file-status">Listo para cargar · ${formatFileSize(f.size)}</div>
              </div>
            </div>

            <button type="button"
                    class="partesnew-file-remove"
                    title="Quitar archivo"
                    onclick="removeEvidenciaFromBuffer(${i})">
              ✕
            </button>
          `;
          cont.appendChild(card);
        }
      }

      function acumularEvidencias(inputEl) {
        for (const f of inputEl.files) {
          const yaExiste = Array.from(evidenciasBufferDT.files).some(
            x => x.name === f.name && x.size === f.size && x.lastModified === f.lastModified
          );
          if (!yaExiste) evidenciasBufferDT.items.add(f);
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

      window.addEventListener('DOMContentLoaded', renderListaEvidencias);
    </script>
    """
    inner = render_template_string(html)
    return render_template_string(BASE, content=Markup(inner))


# ==========================
# Evidencias — Partes Interesadas
# ==========================
@app.route('/partes_evidencia/file/<int:evi_id>')
@login_required
def partes_evidencia_file(evi_id):
    ev = ParteInteresadaEvidencia.query.get_or_404(evi_id)
    path = os.path.join(app.config['UPLOAD_PARTES_INTERESADAS_DIR'], ev.filename)

    if not os.path.isfile(path):
        abort(404)

    ext = os.path.splitext(ev.filename)[1].lower()
    mimetypes = {
        '.pdf':  'application/pdf',
        '.doc':  'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xls':  'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.png':  'image/png',
        '.jpg':  'image/jpeg',
        '.jpeg': 'image/jpeg',
    }
    mime = mimetypes.get(ext, ev.mime or 'application/octet-stream')

    return send_file(
        path,
        mimetype=mime,
        as_attachment=False,
        download_name=ev.original_name or ev.filename,
        conditional=True
    )


@app.route('/partes_evidencia/<int:evi_id>')
@login_required
def partes_evidencia_legacy_redirect(evi_id):
    return redirect(url_for('partes_evidencia_view', evi_id=evi_id))


# ==========================
# Ver Evidencias
# ==========================
@app.route('/partes_evidencia/<int:evi_id>/view')
@login_required
def partes_evidencia_view(evi_id):
    ev = ParteInteresadaEvidencia.query.get_or_404(evi_id)

    path = os.path.join(app.config['UPLOAD_PARTES_INTERESADAS_DIR'], ev.filename)
    if not os.path.isfile(path):
        abort(404)

    ext = os.path.splitext(ev.filename)[1].lower()
    is_pdf = ext == '.pdf'
    is_office = ext in {'.doc', '.docx', '.xls', '.xlsx'}
    is_image = ext in {'.png', '.jpg', '.jpeg', '.webp', '.gif'}

    next_ep = request.args.get('next')

    back_label_map = {
        'partes_interesadas_matriz': '⬅ Volver a Partes Interesadas',
        'menu': '⬅ Volver al menú principal',
    }

    allowed_back = set(back_label_map.keys())

    if next_ep in allowed_back:
        back_url = url_for(next_ep)
        back_label = back_label_map[next_ep]
    else:
        back_url = request.referrer or url_for('menu')
        back_label = '⬅ Volver'

    pdf_converted_name = None
    if is_office:
        try:
            converted_dir = app.config.get(
                'UPLOAD_PARTES_INTERESADAS_CONVERTED_DIR',
                os.path.join(app.root_path, 'static', 'converted_partes_interesadas')
            )
            os.makedirs(converted_dir, exist_ok=True)

            pdf_converted_path = ensure_pdf_from_office(path, output_dir=converted_dir)

            if pdf_converted_path and os.path.isfile(pdf_converted_path):
                pdf_converted_name = os.path.basename(pdf_converted_path)
        except Exception:
            pdf_converted_name = None

    inner_html = """
    <div class="container my-3">
      <div class="d-flex justify-content-between align-items-center mb-2 flex-wrap gap-2">
        <a href="{{ back_url }}" class="btn btn-secondary rounded-pill px-4 py-2">
          {{ back_label }}
        </a>
        <div class="small text-muted text-truncate">
          Archivo: {{ original_name }}
        </div>
      </div>

      <div class="card shadow-sm border-0 rounded-4 overflow-hidden">
        <div class="card-body p-2">

          {% if is_pdf %}
            <div class="pdf-container">
              <iframe id="pdfFrame"
                      src="{{ url_for('partes_evidencia_file', evi_id=evi_id) }}#zoom=page-width"
                      title="Visor PDF"></iframe>
            </div>

          {% elif pdf_converted_name %}
            <div class="pdf-container">
              <iframe id="pdfFrame"
                      src="{{ url_for('partes_evidencia_convertido', filename=pdf_converted_name) }}#zoom=page-width"
                      title="Visor PDF convertido"></iframe>
            </div>
            <div class="mt-3 text-center">
              <a class="btn btn-outline-primary rounded-pill px-4"
                 href="{{ url_for('partes_evidencia_file', evi_id=evi_id) }}"
                 target="_blank" rel="noopener">
                Abrir archivo original
              </a>
            </div>

          {% elif is_image %}
            <div class="text-center p-3">
              <img src="{{ url_for('partes_evidencia_file', evi_id=evi_id) }}"
                   alt="{{ original_name }}"
                   class="img-fluid rounded-4 shadow-sm"
                   style="max-height: 78vh; object-fit: contain;">
            </div>

          {% elif is_office %}
            <div class="alert alert-warning m-2 rounded-4">
              No fue posible generar una vista previa interna del archivo Office.
              Verifica que LibreOffice esté instalado en el servidor.
            </div>
            <div class="text-center mb-2">
              <a class="btn btn-outline-primary rounded-pill px-4"
                 href="{{ url_for('partes_evidencia_file', evi_id=evi_id) }}"
                 target="_blank" rel="noopener">
                Abrir/descargar archivo original
              </a>
            </div>

          {% else %}
            <div class="alert alert-info m-2 rounded-4">
              Este tipo de archivo (<b>{{ ext }}</b>) no se puede previsualizar.
              Puedes abrirlo o descargarlo.
            </div>
            <div class="text-center mb-2">
              <a class="btn btn-outline-primary rounded-pill px-4"
                 href="{{ url_for('partes_evidencia_file', evi_id=evi_id) }}"
                 target="_blank" rel="noopener">
                Abrir archivo
              </a>
            </div>
          {% endif %}

        </div>
      </div>
    </div>

    <style>
      .pdf-container {
        height: min(82vh, 1000px);
        min-height: 600px;
        width: 100%;
      }

      .pdf-container iframe {
        width: 100%;
        height: 100%;
        border: 1px solid #dee2e6;
        border-radius: 16px;
        background: #fff;
      }

      body {
        background-image: url('/static/img/ccsgsi.jpg');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        background-repeat: no-repeat;
      }

      .card {
        background: rgba(255, 255, 255, 0.88) !important;
        backdrop-filter: blur(4px);
      }
    </style>
    """

    return render_template_string(
        BASE,
        content=Markup(render_template_string(
            inner_html,
            evi_id=evi_id,
            original_name=ev.original_name or ev.filename,
            ext=ext,
            is_pdf=is_pdf,
            is_office=is_office,
            is_image=is_image,
            pdf_converted_name=pdf_converted_name,
            back_url=back_url,
            back_label=back_label
        ))
    )


# ==========================
# Matriz Partes Interesadas
# ==========================
PARTES_INTERESADAS_MATRIZ_MIN_COLS = [
    "parte_interesada",
    "necesidades_expectativas",
    "fecha_revision",
    "evidencias",
]

@app.route('/partes_interesadas_matriz', methods=['GET'])
@login_required
def partes_interesadas_matriz():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Partes Interesadas"):
            flash("No tiene permiso para ver los registros de partes interesadas.", "danger")
            return redirect(url_for('menu'))
        read_only = False

    items = ParteInteresada.query.order_by(ParteInteresada.parte_interesada.asc()).all()

    html = """
    <div class="pi-shell">

      <div class="pi-header-card">
        <div class="pi-header-overlay">
          <div class="pi-header-text">
            <h3 class="pi-title m-0">Partes Interesadas</h3>
            <div class="pi-subtitle">
              Visualización resumida de las partes interesadas del Sistema de Gestión de Seguridad de la Información
            </div>
          </div>
        </div>
      </div>

      <div class="pi-header-actions">
        {% if not read_only %}
          <a href="{{ url_for('parte_interesada_new') }}"
             class="btn btn-primary rounded-pill px-4 fw-bold"
             onclick="showLoader()">
            ⨁ Agregar Partes Interesadas
          </a>
        {% endif %}

      </div>

      <div class="pi-table-card">
        <div class="pi-table-topbar">
          <div>
            <h5 class="pi-table-title mb-1">Resumen de registros</h5>
            <div class="pi-table-note">
              La matriz presenta únicamente los datos más relevantes. Para consultar el registro completo use el botón <strong>Ver detalle</strong>.
            </div>
          </div>
          <div class="pi-counter-badge">
            Total registros: {{ items|length }}
          </div>
        </div>

        <div class="pi-table-card-body">
          <div class="pi-table-wrap">
            <div class="table-responsive">
              <table class="table table-bordered table-hover align-middle pi-matriz mb-0">
                <colgroup>
                  <col style="width: 24%;">
                  <col style="width: 34%;">
                  <col style="width: 12%;">
                  <col style="width: 12%;">
                  <col style="width: 18%;">
                </colgroup>

                <thead>
                  <tr>
                    <th>Parte Interesada</th>
                    <th>Necesidades / Expectativas</th>
                    <th>Fecha de Revisión</th>
                    <th>Evidencias</th>
                    <th>Acciones</th>
                  </tr>
                </thead>

                <tbody>
                  {% for it in items %}
                    <tr>
                      <td class="pi-cell-main">
                        <div class="pi-main-text">{{ it.parte_interesada or '—' }}</div>
                      </td>

                      <td>{{ resumir_texto(it.necesidades_expectativas, 150) }}</td>

                      <td class="text-center">
                        {{ format_fecha_partes(it.fecha_revision) }}
                      </td>

                      <td class="text-center">
                        {% set total_ev = it.evidencias|length %}
                        {% if total_ev > 0 %}
                          <span class="pi-badge-ev">{{ total_ev }} PDF{{ 's' if total_ev != 1 else '' }}</span>
                        {% else %}
                          <span class="text-muted">—</span>
                        {% endif %}
                      </td>

                      <td class="text-center">
                        <div class="pi-actions-wrap">
                          <a href="{{ url_for('parte_interesada_detalle', id=it.id) }}"
                             class="btn btn-info btn-sm rounded-pill px-3 fw-bold text-white"
                             onclick="showLoader()">
                            Ver detalle
                          </a>

                          {% if not read_only %}
                            <a href="{{ url_for('parte_interesada_edit', id=it.id) }}"
                               class="btn btn-warning btn-sm rounded-pill px-3 fw-bold"
                               onclick="showLoader()">
                              Editar
                            </a>

                            <form method="post"
                                  action="{{ url_for('parte_interesada_delete', id=it.id) }}"
                                  style="display:inline;"
                                  onsubmit="return confirm('¿Seguro que desea eliminar este registro? Esta acción no se puede deshacer.');">
                              <button type="submit" class="btn btn-danger btn-sm rounded-pill px-3 fw-bold">
                                Eliminar
                              </button>
                            </form>
                          {% else %}
                            <span class="badge bg-secondary">Solo lectura</span>
                          {% endif %}
                        </div>
                      </td>
                    </tr>
                  {% endfor %}

                  {% if items|length == 0 %}
                    <tr>
                      <td colspan="5" class="text-center text-muted py-5">
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

      .pi-shell{
        width:96%;
        max-width:1650px;
        margin:10px auto 24px auto;
      }

      /* =========================
         HERO SGSI UNIFICADO
      ========================== */
      .pi-header-card{
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

      .pi-header-card::before{
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
        pointer-events:none;
      }

      .pi-header-overlay{
        width:100%;
        height:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        padding:0;
        background:transparent;
        position:relative;
        z-index:1;
      }

      .pi-header-overlay::before{
        content:"👥";
        width:54px;
        height:54px;
        min-width:54px;
        border-radius:14px;
        background:rgba(255,255,255,.96);
        color:#0b4a8f;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.55rem;
        box-shadow:0 8px 18px rgba(0,0,0,.20);
        margin-right:14px;
      }

      .pi-header-text{
        max-width:1100px;
        position:relative;
        z-index:1;
      }

      .pi-header-text::before{
        content:"SGSI · Partes Interesadas";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border:1px solid rgba(255,255,255,.30);
        border-radius:999px;
        padding:3px 10px;
        font-size:.66rem;
        font-weight:800;
        letter-spacing:.35px;
        margin-bottom:4px;
      }

      .pi-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.36rem;
        line-height:1.08;
        text-shadow:0 3px 10px rgba(0,0,0,.32);
        margin:0 !important;
      }

      .pi-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      /* =========================
         ACCIONES
      ========================== */
      .pi-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px 0;
      }

      .pi-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .pi-header-actions .btn-primary,
      .pi-header-actions .btn-success{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .pi-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .pi-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         CARD TABLA
      ========================== */
      .pi-table-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        overflow:hidden;
        border:1px solid rgba(219,230,244,.9);
      }

      .pi-table-topbar{
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:12px;
        padding:14px 16px 0 16px;
        flex-wrap:wrap;
      }

      .pi-table-title{
        color:#0f172a;
        font-weight:950;
        font-size:.94rem;
      }

      .pi-table-note{
        color:#475569;
        font-size:.78rem;
        margin-top:3px;
      }

      .pi-counter-badge{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        color:#fff;
        font-weight:900;
        border-radius:999px;
        padding:7px 14px;
        font-size:.78rem;
        box-shadow:0 8px 16px rgba(15,23,42,.16);
      }

      .pi-table-card-body{
        padding:12px 16px 16px 16px;
      }

      .pi-table-wrap{
        max-height:70vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:rgba(255,255,255,.99);
      }

      .pi-matriz{
        min-width:1150px;
        margin-bottom:0;
        table-layout:fixed;
        border-collapse:separate;
        border-spacing:0;
      }

      .pi-matriz thead th{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff;
        font-weight:900;
        text-align:center;
        vertical-align:middle;
        padding:11px 9px;
        font-size:.68rem;
        border-right:1px solid rgba(255,255,255,.28);
      }

      .pi-matriz td{
        vertical-align:top;
        font-size:.68rem;
        padding:9px 8px;
        color:#101827;
        border-right:1px solid #dce6f3;
        border-bottom:1px solid #dce6f3;
        background:#ffffff;
        word-break:break-word;
      }

      .pi-matriz tbody tr:nth-child(even) td{
        background:#f8fbff;
      }

      .pi-matriz tbody tr:hover td{
        background:#eef6ff;
      }

      .pi-cell-main .pi-main-text{
        font-weight:900;
        color:#0f172a;
      }

      .pi-badge-ev{
        display:inline-block;
        background:linear-gradient(135deg,#eef5ff,#dbeafe);
        color:#1d4ed8;
        border:1px solid #bfdbfe;
        border-radius:999px;
        padding:5px 10px;
        font-size:.72rem;
        font-weight:900;
      }

      .pi-actions-wrap{
        display:flex;
        flex-direction:column;
        gap:6px;
        align-items:center;
        justify-content:center;
      }

      /* =========================
         RESPONSIVE
      ========================== */
      @media (max-width:992px){
        .pi-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .pi-header-card{
          min-height:88px;
          padding:15px 18px;
        }

        .pi-title{
          font-size:1.22rem;
        }

        .pi-subtitle{
          font-size:.74rem;
        }

        .pi-table-card-body{
          padding:12px 14px 14px 14px;
        }
      }

      @media (max-width:768px){
        .pi-header-overlay{
          justify-content:center;
          text-align:center;
          flex-direction:column;
          gap:10px;
        }

        .pi-header-overlay::before{
          margin-right:0;
        }

        .pi-title{
          font-size:1.12rem;
        }

        .pi-subtitle{
          font-size:.72rem;
        }

        .pi-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(
        html,
        items=items,
        read_only=read_only,
        resumir_texto=resumir_texto,
        format_fecha_partes=format_fecha_partes
    )
    return render_template_string(BASE, content=Markup(inner))


# ==========================
# Detalle Partes Interesadas
# ==========================
