class ProveedorEvalConfig(db.Model):
    __tablename__ = "proveedor_eval_config"

    id = db.Column(db.Integer, primary_key=True)

    min_certificaciones_aprobado = db.Column(db.Integer, default=1)
    pct_aprob_min = db.Column(db.Integer, default=81)
    pct_revision_min = db.Column(db.Integer, default=61)

    crit_muy_baja_max = db.Column(db.Integer, default=25)
    crit_baja_max = db.Column(db.Integer, default=50)
    crit_media_max = db.Column(db.Integer, default=75)

    # NUEVOS PESOS CONFIGURABLES
    peso_transversal = db.Column(db.Integer, default=10)
    peso_esencial = db.Column(db.Integer, default=15)
    peso_plan_continuidad = db.Column(db.Integer, default=10)
    peso_plan_recuperacion = db.Column(db.Integer, default=10)
    peso_alternativas = db.Column(db.Integer, default=10)
    peso_impacto_falla = db.Column(db.Integer, default=10)
    peso_plan_migracion = db.Column(db.Integer, default=10)
    peso_info_sensible = db.Column(db.Integer, default=10)
    peso_datos_personales = db.Column(db.Integer, default=5)
    peso_nube = db.Column(db.Integer, default=5)
    peso_sla = db.Column(db.Integer, default=5)

    @staticmethod
    def get():
        obj = ProveedorEvalConfig.query.first()
        if not obj:
            obj = ProveedorEvalConfig()
            db.session.add(obj)
            db.session.commit()
        return obj

# =========================
# ENTRADA DIRECTA — Registro de Proveedores
# =========================
@app.route('/proveedores_menu')
@login_required
def proveedores_menu():
    user = User.query.get(session.get('user_id'))

    if user.role != 'admin' and user.role != 'auditor' and not verificar_permiso(user, "Registro de Proveedores"):
        flash("No tiene permiso para acceder al módulo de registro de proveedores.", "danger")
        return redirect(url_for('menu'))

    return redirect(url_for('proveedores_matriz'))


# =========================
# HELPERS
# =========================
def _proveedor_paises():
    try:
        paises = [c.name for c in pycountry.countries]
        paises.sort()
        return paises
    except Exception:
        return ["Colombia", "Argentina", "Brasil", "Chile", "México", "Perú", "España", "Estados Unidos"]

def _proveedor_fill_area_data(area_id):
    responsable_area_nombre = ''
    responsable_area_cargo = ''

    if area_id:
        a = AreaEmpresa.query.get(area_id)
        if a:
            responsable_area_nombre = (getattr(a, 'responsable_nombre', '') or '')
            responsable_area_cargo = (getattr(a, 'responsable_cargo', '') or '')

    return responsable_area_nombre, responsable_area_cargo

def _proveedor_apply_scores(obj, form, cfg):
    obj.es_transversal = form.get('es_transversal') or 'No'
    obj.es_esencial = form.get('es_esencial') or 'No'
    obj.tiene_plan_cont = form.get('tiene_plan_cont') or 'No'
    obj.tiene_plan_rec = form.get('tiene_plan_rec') or 'No'
    obj.existen_alternativas = form.get('existen_alternativas') or 'No'
    obj.impacto_falla = form.get('impacto_falla') or 'Bajo'
    obj.existe_plan_migracion = form.get('existe_plan_migracion') or 'No'
    obj.procesa_info_sensible = form.get('procesa_info_sensible') or 'No'
    obj.procesa_datos_personales = form.get('procesa_datos_personales') or 'No'
    obj.procesa_info_nube = form.get('procesa_info_nube') or 'No'
    obj.incluye_sla = form.get('incluye_sla') or 'No'

    obj.valor_alcance = int(cfg.peso_transversal or 0) if obj.es_transversal == 'Sí' else 0
    obj.valor_esencial = int(cfg.peso_esencial or 0) if obj.es_esencial == 'Sí' else 0
    obj.valor_plan_cont = 0 if obj.tiene_plan_cont == 'Sí' else int(cfg.peso_plan_continuidad or 0)
    obj.valor_plan_rec = 0 if obj.tiene_plan_rec == 'Sí' else int(cfg.peso_plan_recuperacion or 0)
    obj.valor_alternativas = 0 if obj.existen_alternativas == 'Sí' else int(cfg.peso_alternativas or 0)

    if obj.impacto_falla == 'Alto':
        obj.valor_impacto_falla = int(cfg.peso_impacto_falla or 0)
    elif obj.impacto_falla == 'Medio':
        obj.valor_impacto_falla = round(int(cfg.peso_impacto_falla or 0) * 0.5)
    else:
        obj.valor_impacto_falla = 0

    obj.valor_plan_migracion = 0 if obj.existe_plan_migracion == 'Sí' else int(cfg.peso_plan_migracion or 0)
    obj.valor_info_sensible = int(cfg.peso_info_sensible or 0) if obj.procesa_info_sensible == 'Sí' else 0
    obj.valor_datos_personales = int(cfg.peso_datos_personales or 0) if obj.procesa_datos_personales == 'Sí' else 0
    obj.valor_nube = int(cfg.peso_nube or 0) if obj.procesa_info_nube == 'Sí' else 0
    obj.valor_sla = 0 if obj.incluye_sla == 'Sí' else int(cfg.peso_sla or 0)

    obj.tiene_certificacion = form.get('tiene_certificacion') or 'No'
    obj.puntos_formulario = form.get('puntos_formulario', type=int) or 0
    obj.num_certificaciones = form.get('num_certificaciones', type=int) or 0
    obj.nombre_certificaciones = (form.get('nombre_certificaciones') or '').strip()

    obj.calcular_criticidad()
    obj.calcular_certificados()

    try:
        total_criticidad = int(getattr(obj, 'criticidad_pct', 0) or 0)
    except Exception:
        total_criticidad = 0

    if total_criticidad <= int(cfg.crit_baja_max or 50):
        obj.calificacion_total = 100
        obj.resultado_evaluacion = 'Aprobado Por Seguridad'
        obj.resultado_color = 'badge-aprobado'
        obj.requiere_formulario = 'No'
        obj.puntos_certificacion = 100
        obj.puntos_formulario = 0

def _proveedor_save_files(obj, files):
    for f in files:
        if not f or not f.filename:
            continue

        if not is_allowed_pdf(f.filename):
            flash(f"Archivo no permitido (solo PDF): {f.filename}", "danger")
            continue

        store_name = unique_store_name(f.filename)
        path = os.path.join(app.config['UPLOAD_PROVEEDORES_DIR'], store_name)
        f.save(path)

        ev = ProveedorEvidencia(
            proveedor=obj,
            filename=store_name,
            original_name=secure_filename(f.filename),
            mime='application/pdf',
            size=os.path.getsize(path)
        )
        db.session.add(ev)

def _render_proveedor_form(item=None, areas=None, paises=None, cfg=None, is_edit=False):
    if item is None:
        class Dummy:
            pass
        item = Dummy()
        item.id = None
        item.fecha_eval_seguridad = ''
        item.nombre_proveedor = ''
        item.estatus_proveedor = ''
        item.area_id = None
        item.responsable_area_nombre = ''
        item.responsable_area_cargo = ''
        item.nombre_cargo_evaluador = ''
        item.pais_origen = ''
        item.pais_servicio = ''
        item.desc_producto_servicio = ''
        item.estado_avance = 'Operando'
        item.estado_evaluacion = 'Proceso'
        item.es_transversal = 'No'
        item.es_esencial = 'No'
        item.tiene_plan_cont = 'No'
        item.tiene_plan_rec = 'No'
        item.existen_alternativas = 'No'
        item.impacto_falla = 'Bajo'
        item.existe_plan_migracion = 'No'
        item.procesa_info_sensible = 'No'
        item.procesa_datos_personales = 'No'
        item.procesa_info_nube = 'No'
        item.incluye_sla = 'No'
        item.criticidad_pct = 0
        item.criticidad_texto = 'Criticidad muy baja'
        item.tiene_certificacion = 'No'
        item.num_certificaciones = 0
        item.nombre_certificaciones = ''
        item.puntos_formulario = 0
        item.calificacion_total = 0
        item.resultado_evaluacion = 'No Aprobado por Seguridad'
        item.observaciones = ''
        item.evidencias = []

    html = """
    <div class="provform-shell">

      <div class="provform-header-card">
        <div class="provform-header-overlay">
          <div class="provform-header-text">
            <h3 class="provform-title m-0">
              {% if is_edit %}Editar Proveedor{% else %}Agregar — Proveedor{% endif %}
            </h3>
            <div class="provform-subtitle">
              Registro y evaluación de proveedores, incluyendo criticidad, certificaciones, continuidad, recuperación, SLA, nube, datos personales, evidencias y resultado de aprobación por seguridad
            </div>
          </div>
        </div>
      </div>

      <div class="provform-header-actions">
        <a href="{{ url_for('proveedores_matriz') }}"
           class="btn rounded-pill px-5 fw-bold provform-back-btn"
           onclick="showLoader()">
          ⬅ Volver a la Matriz de Proveedores
        </a>
      </div>

      <div class="provform-card">
        <div class="provform-card-body">
          <form method="post" enctype="multipart/form-data" oninput="recalc()">
            <div class="row g-3">

              <div class="col-12">
                <div class="provform-section-box">
                  <div class="provform-section-title">Información general del proveedor</div>
                  <div class="provform-section-subtitle">
                    Datos básicos del proveedor, área responsable, evaluador, ubicación, descripción del servicio y estado del registro.
                  </div>
                </div>
              </div>

              <div class="col-md-3">
                <label class="form-label">Fecha de registro por el área de seguridad</label>
                <input type="date" name="fecha_eval_seguridad" class="form-control" value="{{ item.fecha_eval_seguridad or '' }}" required>
              </div>

              <div class="col-md-3">
                <label class="form-label">Nombre del Proveedor</label>
                <input type="text" name="nombre_proveedor" class="form-control" value="{{ item.nombre_proveedor or '' }}" required>
              </div>

              <div class="col-md-3">
                <label class="form-label">Estatus del Proveedor</label>
                <input type="text" name="estatus_proveedor" class="form-control" value="{{ item.estatus_proveedor or '' }}">
              </div>

              <div class="col-md-3">
                <label class="form-label">Área responsable del proveedor</label>
                <select name="area_id" id="provArea" class="form-select" required onchange="fillResp()">
                  <option value="">-- Seleccione --</option>
                  {% for a in areas %}
                    <option value="{{ a.id }}" {% if item.area_id == a.id %}selected{% endif %}>{{ a.area }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-4">
                <label class="form-label">Nombre del responsable del área</label>
                <input type="text" name="responsable_area_nombre" id="provResp" class="form-control" value="{{ item.responsable_area_nombre or '' }}" readonly>
              </div>

              <div class="col-md-4">
                <label class="form-label">Cargo del responsable del área</label>
                <input type="text" name="responsable_area_cargo" id="provCargo" class="form-control" value="{{ item.responsable_area_cargo or '' }}" readonly>
              </div>

              <div class="col-md-4">
                <label class="form-label">Nombre y cargo del evaluador</label>
                <input type="text" name="nombre_cargo_evaluador" class="form-control" value="{{ item.nombre_cargo_evaluador or '' }}">
              </div>

              <div class="col-md-2">
                <label class="form-label">País de origen</label>
                <select name="pais_origen" class="form-select">
                  <option value="">-- Seleccione --</option>
                  {% for p in paises %}
                    <option value="{{ p }}" {% if item.pais_origen == p %}selected{% endif %}>{{ p }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-2">
                <label class="form-label">País de servicio</label>
                <select name="pais_servicio" class="form-select">
                  <option value="">-- Seleccione --</option>
                  {% for p in paises %}
                    <option value="{{ p }}" {% if item.pais_servicio == p %}selected{% endif %}>{{ p }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-12">
                <label class="form-label">Descripción del producto/servicio</label>
                <textarea name="desc_producto_servicio" class="form-control" rows="2">{{ item.desc_producto_servicio or '' }}</textarea>
              </div>

              <div class="col-md-3">
                <label class="form-label">Estado / avance</label>
                <select name="estado_avance" class="form-select">
                  {% for opt in ['Operando','Negociación','Instalaciones'] %}
                    <option {% if item.estado_avance == opt %}selected{% endif %}>{{ opt }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-3">
                <label class="form-label">Estado del registro</label>
                <select name="estado_evaluacion" class="form-select">
                  {% for opt in ['Finalizado','Proceso'] %}
                    <option {% if item.estado_evaluacion == opt %}selected{% endif %}>{{ opt }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-12">
                <div class="provform-section-box">
                  <div class="provform-section-title">Calificación del proveedor</div>
                  <div class="provform-section-subtitle">
                    Criterios de criticidad y evaluación del proveedor: transversalidad, continuidad, recuperación, alternativas, impacto, migración, información sensible, datos personales, nube y SLA.
                  </div>
                </div>
              </div>

              <div class="col-md-3">
                <label class="form-label">¿Es transversal a toda la Organización?</label>
                <select name="es_transversal" id="es_transversal" class="form-select">
                  <option {% if item.es_transversal == 'No' %}selected{% endif %}>No</option>
                  <option {% if item.es_transversal == 'Sí' %}selected{% endif %}>Sí</option>
                </select>
                <small>Valor alcance: <b id="val_alc">0</b>%</small>
              </div>

              <div class="col-md-3">
                <label class="form-label">¿Es esencial para la continuidad?</label>
                <select name="es_esencial" id="es_esencial" class="form-select">
                  <option {% if item.es_esencial == 'No' %}selected{% endif %}>No</option>
                  <option {% if item.es_esencial == 'Sí' %}selected{% endif %}>Sí</option>
                </select>
                <small>Valor esencial: <b id="val_esen">0</b>%</small>
              </div>

              <div class="col-md-3">
                <label class="form-label">¿Tiene plan de continuidad?</label>
                <select name="tiene_plan_cont" id="tiene_plan_cont" class="form-select">
                  <option {% if item.tiene_plan_cont == 'No' %}selected{% endif %}>No</option>
                  <option {% if item.tiene_plan_cont == 'Sí' %}selected{% endif %}>Sí</option>
                </select>
                <small>Valor plan cont.: <b id="val_plan">0</b>%</small>
              </div>

              <div class="col-md-3">
                <label class="form-label">¿Tiene plan de recuperación?</label>
                <select name="tiene_plan_rec" id="tiene_plan_rec" class="form-select">
                  <option {% if item.tiene_plan_rec == 'No' %}selected{% endif %}>No</option>
                  <option {% if item.tiene_plan_rec == 'Sí' %}selected{% endif %}>Sí</option>
                </select>
                <small>Valor plan rec.: <b id="val_plan_rec">0</b>%</small>
              </div>

              <div class="col-md-3">
                <label class="form-label">¿Existen alternativas en el mercado?</label>
                <select name="existen_alternativas" id="existen_alternativas" class="form-select">
                  <option {% if item.existen_alternativas == 'No' %}selected{% endif %}>No</option>
                  <option {% if item.existen_alternativas == 'Sí' %}selected{% endif %}>Sí</option>
                </select>
                <small>Valor alternativas: <b id="val_alt">0</b>%</small>
              </div>

              <div class="col-md-3">
                <label class="form-label">Impacto en caso de falla</label>
                <select name="impacto_falla" id="impacto_falla" class="form-select">
                  <option {% if item.impacto_falla == 'Bajo' %}selected{% endif %}>Bajo</option>
                  <option {% if item.impacto_falla == 'Medio' %}selected{% endif %}>Medio</option>
                  <option {% if item.impacto_falla == 'Alto' %}selected{% endif %}>Alto</option>
                </select>
                <small>Valor impacto: <b id="val_impacto">0</b>%</small>
              </div>

              <div class="col-md-3">
                <label class="form-label">¿Existe plan de migración?</label>
                <select name="existe_plan_migracion" id="existe_plan_migracion" class="form-select">
                  <option {% if item.existe_plan_migracion == 'No' %}selected{% endif %}>No</option>
                  <option {% if item.existe_plan_migracion == 'Sí' %}selected{% endif %}>Sí</option>
                </select>
                <small>Valor migración: <b id="val_mig">0</b>%</small>
              </div>

              <div class="col-md-3">
                <label class="form-label">¿Procesa/almacena info. sensible?</label>
                <select name="procesa_info_sensible" id="procesa_info_sensible" class="form-select">
                  <option {% if item.procesa_info_sensible == 'No' %}selected{% endif %}>No</option>
                  <option {% if item.procesa_info_sensible == 'Sí' %}selected{% endif %}>Sí</option>
                </select>
                <small>Valor info sensible: <b id="val_inf">0</b>%</small>
              </div>

              <div class="col-md-3">
                <label class="form-label">¿Procesa/almacena datos personales?</label>
                <select name="procesa_datos_personales" id="procesa_datos_personales" class="form-select">
                  <option {% if item.procesa_datos_personales == 'No' %}selected{% endif %}>No</option>
                  <option {% if item.procesa_datos_personales == 'Sí' %}selected{% endif %}>Sí</option>
                </select>
                <small>Valor datos personales: <b id="val_datos">0</b>%</small>
              </div>

              <div class="col-md-3">
                <label class="form-label">¿Procesa/almacena información en la nube?</label>
                <select name="procesa_info_nube" id="procesa_info_nube" class="form-select">
                  <option {% if item.procesa_info_nube == 'No' %}selected{% endif %}>No</option>
                  <option {% if item.procesa_info_nube == 'Sí' %}selected{% endif %}>Sí</option>
                </select>
                <small>Valor nube: <b id="val_nube">0</b>%</small>
              </div>

              <div class="col-md-3">
                <label class="form-label">¿Incluye SLA definidos?</label>
                <select name="incluye_sla" id="incluye_sla" class="form-select">
                  <option {% if item.incluye_sla == 'No' %}selected{% endif %}>No</option>
                  <option {% if item.incluye_sla == 'Sí' %}selected{% endif %}>Sí</option>
                </select>
                <small>Valor SLA: <b id="val_sla">0</b>%</small>
              </div>

              <div class="col-md-6">
                <label class="form-label">Criticidad % (auto)</label>
                <input type="text" class="form-control provform-readonly" id="criticidad_pct" value="{{ item.criticidad_pct or 0 }}" readonly>
                <small id="criticidad_texto" class="badge badge-verde-claro mt-1">{{ item.criticidad_texto or 'Criticidad muy baja' }}</small>
              </div>

              <div class="col-12">
                <div class="provform-section-box">
                  <div class="provform-section-title">Registro del proveedor</div>
                  <div class="provform-section-subtitle">
                    Registro de certificaciones, cantidad, nombres, puntos del formulario, cálculo automático de la calificación total y resultado de evaluación.
                  </div>
                </div>
              </div>

              <div class="col-md-3">
                <label class="form-label">¿Tiene certificación (ISO 27001, SOC2, etc.)?</label>
                <select name="tiene_certificacion" id="tiene_certificacion" class="form-select">
                  <option {% if item.tiene_certificacion == 'No' %}selected{% endif %}>No</option>
                  <option {% if item.tiene_certificacion == 'Sí' %}selected{% endif %}>Sí</option>
                </select>
                <small>Requiere formulario: <b id="req_form">Sí</b></small><br>
                <small>Puntos por certificación: <b id="pt_cert">0</b>%</small>
              </div>

              <div class="col-md-3">
                <label class="form-label">Número de certificaciones</label>
                <input type="number" min="0" name="num_certificaciones" id="num_certificaciones" class="form-control" value="{{ item.num_certificaciones or 0 }}">
              </div>

              <div class="col-md-3">
                <label class="form-label">Nombre de las certificaciones</label>
                <textarea name="nombre_certificaciones" id="nombre_certificaciones" class="form-control" rows="2">{{ item.nombre_certificaciones or '' }}</textarea>
              </div>

              <div class="col-md-3">
                <label class="form-label">Puntos obtenidos en el formulario</label>
                <input type="number" max="100" min="0" name="puntos_formulario" id="puntos_formulario" class="form-control" value="{{ item.puntos_formulario or 0 }}">
                <small>Solo editable si no hay certificación.</small>
              </div>

              <div class="col-md-3">
                <label class="form-label">Calificación total (auto)</label>
                <input type="text" class="form-control provform-readonly" id="cal_total" value="{{ item.calificacion_total or 0 }}" readonly>
              </div>

              <div class="col-md-3">
                <label class="form-label">Resultado (auto)</label><br>
                <span id="resultado_badge" class="badge badge-noaprob px-3 py-2">{{ item.resultado_evaluacion or 'No Aprobado por Seguridad' }}</span>
              </div>

              <div class="col-12">
                <div class="provform-section-box">
                  <div class="provform-section-title">Evidencias y observaciones</div>
                  <div class="provform-section-subtitle">
                    Adjunta soportes en PDF y registra observaciones complementarias sobre el proveedor, el análisis efectuado y los hallazgos identificados.
                  </div>
                </div>
              </div>

              {% if is_edit %}
              <div class="col-12">
                <label class="form-label">Evidencias existentes</label>
                {% if item.evidencias %}
                  <div class="row g-3">
                    {% for ev in item.evidencias %}
                    <div class="col-md-6">
                      <div class="provdet-file-card d-flex justify-content-between align-items-center">
                        <div class="provdet-file-meta">
                          <div class="provdet-file-label">Archivo</div>
                          <a class="provdet-file-name" href="{{ url_for('proveedores_evidencia_view', evi_id=ev.id, next='proveedores_edit', reg_id=item.id) }}">{{ ev.original_name or ev.filename }}</a>
                          <div class="provdet-file-size">{{ (ev.size / 1024)|round(1) if ev.size else 0 }} KB</div>
                        </div>

                        <button type="submit"
                                class="btn btn-sm btn-danger rounded-pill"
                                formaction="{{ url_for('proveedores_evidencia_delete', evi_id=ev.id) }}"
                                formmethod="post"
                                formenctype="application/x-www-form-urlencoded"
                                onclick="return confirm('¿Eliminar esta evidencia?');">
                          Eliminar
                        </button>
                      </div>
                    </div>
                    {% endfor %}
                  </div>
                {% else %}
                  <div class="provdet-empty-box">No hay evidencias cargadas.</div>
                {% endif %}
              </div>
              {% endif %}

              <div class="col-12">
                <label class="form-label">{% if is_edit %}Agregar nuevas evidencias (PDF){% else %}Evidencias (PDF, puedes adjuntar varios){% endif %}</label>
                <input type="file" id="evidencias" name="evidencias" accept=".pdf" multiple class="form-control" onchange="acumularEvidenciasPDF(this)">
                <small class="text-muted">Puedes seleccionar varios a la vez o ir agregando en varias rondas.</small>
                <div id="lista_evidencias_nuevas" class="mt-2"></div>
              </div>

              <div class="col-12">
                <label class="form-label">Observaciones</label>
                <textarea name="observaciones" class="form-control" rows="2">{{ item.observaciones or '' }}</textarea>
              </div>

            </div>

            <div class="provform-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                {% if is_edit %}Guardar cambios{% else %}Guardar{% endif %}
              </button>

              <a href="{{ url_for('proveedores_matriz') }}"
                 class="btn rounded-pill px-4 fw-bold provform-cancel-btn"
                 onclick="showLoader()">
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

      .provform-shell{
        width:96%;
        max-width:1500px;
        margin:26px auto 24px auto;
      }

      .provform-header-card{
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

      .provform-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .provform-header-overlay{
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

      .provform-header-overlay::before{
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

      .provform-header-text{
        max-width:1200px;
        width:100%;
        display:block !important;
        transform:none !important;
      }

      .provform-header-text::before{
        content:"SGSI · Gestión de Proveedores";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .provform-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .provform-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .provform-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .provform-header-actions .btn,
      .provform-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .provform-back-btn,
      .provform-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .provform-back-btn:hover,
      .provform-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .provform-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .provform-card-body{
        padding:18px;
      }

      .provform-section-box{
        background:#eef5ff;
        border:1px solid #d9eaff;
        border-left:6px solid #0b4a8f;
        border-radius:14px;
        padding:12px 14px;
        margin:10px 0 12px;
        box-shadow:0 6px 14px rgba(15,23,42,.06);
      }

      .provform-section-title{
        font-size:.90rem;
        font-weight:950;
        color:#0b4a8f;
        line-height:1.1;
        margin-bottom:4px;
      }

      .provform-section-subtitle{
        font-size:.78rem;
        color:#475569;
        line-height:1.35;
      }

      .provform-card .form-label{
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

      textarea.form-control{
        min-height:72px;
        resize:vertical;
      }

      .form-control:focus,
      .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
        background:#ffffff;
      }

      .provform-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:22px;
        flex-wrap:wrap;
        width:100%;
      }

      .badge,
      .badge-verde-claro,
      .badge-verde-oscuro,
      .badge-amarillo,
      .badge-rojo,
      .badge-aprobado,
      .badge-revision,
      .badge-noaprob{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }

      .badge-verde-claro{ background:#d1fae5; color:#065f46; }
      .badge-verde-oscuro{ background:#10b981; color:#ffffff; }
      .badge-amarillo{ background:#fef3c7; color:#92400e; }
      .badge-rojo{ background:#fee2e2; color:#991b1b; }
      .badge-aprobado{ background:#dcfce7; color:#166534; }
      .badge-revision{ background:#fef3c7; color:#92400e; }
      .badge-noaprob{ background:#fee2e2; color:#991b1b; }

      .btn.rounded-pill{
        border-radius:10px !important;
      }

      @media (max-width:992px){
        .provform-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .provform-header-card{
          min-height:88px;
        }

        .provform-title{
          font-size:1.20rem;
        }

        .provform-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .provform-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .provform-header-overlay::before{
          margin:0;
        }

        .provform-header-text::before{
          margin-left:auto;
          margin-right:auto;
        }

        .provform-header-actions .btn,
        .provform-bottom-actions .btn{
          width:100%;
        }
      }
    </style>

    <script>
      const AREAS_RESP = {
        {% for a in areas %}
        "{{ a.id }}": {nombre: {{ (a.responsable_nombre or '')|tojson }}, cargo: {{ (a.responsable_cargo or '')|tojson }}},
        {% endfor %}
      };

      const CRIT_MUY_BAJA_MAX = {{ cfg.crit_muy_baja_max or 25 }};
      const CRIT_BAJA_MAX     = {{ cfg.crit_baja_max or 50 }};
      const CRIT_MEDIA_MAX    = {{ cfg.crit_media_max or 75 }};
      const PCT_APROB_MIN     = {{ cfg.pct_aprob_min or 81 }};
      const PCT_REV_MIN       = {{ cfg.pct_revision_min or 61 }};
      const MIN_CERTS_100     = {{ cfg.min_certificaciones_aprobado or 1 }};

      const PESO_TRANSVERSAL       = {{ cfg.peso_transversal or 0 }};
      const PESO_ESENCIAL          = {{ cfg.peso_esencial or 0 }};
      const PESO_PLAN_CONTINUIDAD  = {{ cfg.peso_plan_continuidad or 0 }};
      const PESO_PLAN_RECUPERACION = {{ cfg.peso_plan_recuperacion or 0 }};
      const PESO_ALTERNATIVAS      = {{ cfg.peso_alternativas or 0 }};
      const PESO_IMPACTO_FALLA     = {{ cfg.peso_impacto_falla or 0 }};
      const PESO_PLAN_MIGRACION    = {{ cfg.peso_plan_migracion or 0 }};
      const PESO_INFO_SENSIBLE     = {{ cfg.peso_info_sensible or 0 }};
      const PESO_DATOS_PERSONALES  = {{ cfg.peso_datos_personales or 0 }};
      const PESO_NUBE              = {{ cfg.peso_nube or 0 }};
      const PESO_SLA               = {{ cfg.peso_sla or 0 }};

      function fillResp(){
        const areaId = document.getElementById('provArea').value;
        const data = AREAS_RESP[areaId] || {nombre:'', cargo:''};
        document.getElementById('provResp').value = data.nombre || '';
        document.getElementById('provCargo').value = data.cargo || '';
      }

      function setCertFieldsEnabled(enabled){
        document.getElementById('num_certificaciones').disabled = !enabled;
        document.getElementById('nombre_certificaciones').disabled = !enabled;
      }

      function recalc(){
        const yn = id => (document.getElementById(id)?.value || 'No');
        const impacto = document.getElementById('impacto_falla')?.value || 'Bajo';

        const val_alc = yn('es_transversal') === 'Sí' ? PESO_TRANSVERSAL : 0;
        const val_esen = yn('es_esencial') === 'Sí' ? PESO_ESENCIAL : 0;
        const val_plan = yn('tiene_plan_cont') === 'Sí' ? 0 : PESO_PLAN_CONTINUIDAD;
        const val_plan_rec = yn('tiene_plan_rec') === 'Sí' ? 0 : PESO_PLAN_RECUPERACION;
        const val_alt = yn('existen_alternativas') === 'Sí' ? 0 : PESO_ALTERNATIVAS;
        const val_mig = yn('existe_plan_migracion') === 'Sí' ? 0 : PESO_PLAN_MIGRACION;
        const val_inf = yn('procesa_info_sensible') === 'Sí' ? PESO_INFO_SENSIBLE : 0;
        const val_datos = yn('procesa_datos_personales') === 'Sí' ? PESO_DATOS_PERSONALES : 0;
        const val_nube = yn('procesa_info_nube') === 'Sí' ? PESO_NUBE : 0;
        const val_sla = yn('incluye_sla') === 'Sí' ? 0 : PESO_SLA;

        let val_impacto = 0;
        if (impacto === 'Alto') val_impacto = PESO_IMPACTO_FALLA;
        else if (impacto === 'Medio') val_impacto = Math.round(PESO_IMPACTO_FALLA * 0.5);

        document.getElementById('val_alc').innerText = val_alc;
        document.getElementById('val_esen').innerText = val_esen;
        document.getElementById('val_plan').innerText = val_plan;
        document.getElementById('val_plan_rec').innerText = val_plan_rec;
        document.getElementById('val_alt').innerText = val_alt;
        document.getElementById('val_impacto').innerText = val_impacto;
        document.getElementById('val_mig').innerText = val_mig;
        document.getElementById('val_inf').innerText = val_inf;
        document.getElementById('val_datos').innerText = val_datos;
        document.getElementById('val_nube').innerText = val_nube;
        document.getElementById('val_sla').innerText = val_sla;

        const total = val_alc + val_esen + val_plan + val_plan_rec + val_alt + val_impacto + val_mig + val_inf + val_datos + val_nube + val_sla;
        document.getElementById('criticidad_pct').value = total;

        const ct = document.getElementById('criticidad_texto');
        if (total <= CRIT_MUY_BAJA_MAX){
          ct.className='badge badge-verde-claro mt-1';
          ct.innerText='Criticidad muy baja';
        } else if (total <= CRIT_BAJA_MAX){
          ct.className='badge badge-verde-oscuro mt-1';
          ct.innerText='Criticidad baja';
        } else if (total <= CRIT_MEDIA_MAX){
          ct.className='badge badge-amarillo mt-1';
          ct.innerText='Criticidad media';
        } else {
          ct.className='badge badge-rojo mt-1';
          ct.innerText='Criticidad alta';
        }

        const cert = document.getElementById('tiene_certificacion').value;
        const pf = document.getElementById('puntos_formulario');

        setCertFieldsEnabled(cert === 'Sí');

        let numCerts = parseInt(document.getElementById('num_certificaciones').value || '0');

        let pt_cert = 0;
        if (cert === 'Sí' && numCerts >= MIN_CERTS_100){
          pt_cert = 100;
        }
        document.getElementById('pt_cert').innerText = pt_cert;

        const req_form = (pt_cert === 100 ? 'No' : 'Sí');
        document.getElementById('req_form').innerText = req_form;

        pf.disabled = (cert === 'Sí' && pt_cert === 100);

        let total_cal = pt_cert + (parseInt(pf.value || '0'));

        if (total <= CRIT_BAJA_MAX){
          total_cal = 100;
        }

        document.getElementById('cal_total').value = total_cal;

        const rb = document.getElementById('resultado_badge');
        rb.className = 'badge px-3 py-2';

        if (total <= CRIT_BAJA_MAX){
          rb.classList.add('badge-aprobado');
          rb.innerText='Aprobado Por Seguridad';
        }
        else if (total_cal >= PCT_APROB_MIN){
          rb.classList.add('badge-aprobado');
          rb.innerText='Aprobado por Seguridad';
        }
        else if (total_cal >= PCT_REV_MIN){
          rb.classList.add('badge-revision');
          rb.innerText='En revisión';
        }
        else{
          rb.classList.add('badge-noaprob');
          rb.innerText='No Aprobado por Seguridad';
        }
      }

      let evidenciasBufferDT = new DataTransfer();

      function renderListaEvidenciasPDF() {
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
          row.innerHTML = `<span class="text-truncate small" style="max-width:260px;">📎 ${f.name}</span><button type="button" class="btn btn-link text-danger p-0 small" onclick="removeEvidenciaPDF(${i})">🗑️</button>`;
          cont.appendChild(row);
        }
      }

      function acumularEvidenciasPDF(inputEl) {
        for (const f of inputEl.files) {
          evidenciasBufferDT.items.add(f);
        }
        inputEl.files = evidenciasBufferDT.files;
        renderListaEvidenciasPDF();
      }

      function removeEvidenciaPDF(index) {
        const tmp = new DataTransfer();
        for (let i = 0; i < evidenciasBufferDT.files.length; i++) {
          if (i !== index) tmp.items.add(evidenciasBufferDT.files[i]);
        }
        evidenciasBufferDT = tmp;
        const inputEl = document.getElementById('evidencias');
        if (inputEl) inputEl.files = evidenciasBufferDT.files;
        renderListaEvidenciasPDF();
      }

      window.addEventListener('DOMContentLoaded', ()=>{
        fillResp();
        recalc();
        renderListaEvidenciasPDF();
      });
    </script>
    """
    return render_template_string(
        html,
        item=item,
        areas=areas,
        paises=paises,
        cfg=cfg,
        is_edit=is_edit
    )


# =========================
# AGREGAR — Registro de Proveedores
# =========================
@app.route('/proveedores/new', methods=['GET', 'POST'])
@login_required
def proveedores_new():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede agregar registros.", "danger")
        return redirect(url_for('proveedores_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Registro de Proveedores"):
        flash("No tiene permiso para agregar registro de proveedores.", "danger")
        return redirect(url_for('proveedores_matriz'))

    areas = AreaEmpresa.query.order_by(AreaEmpresa.area.asc()).all()
    cfg = ProveedorEvalConfig.get()
    paises = _proveedor_paises()

    if request.method == 'POST':
        it = ProveedorEvaluacion()

        it.fecha_eval_seguridad = request.form.get('fecha_eval_seguridad')
        it.nombre_proveedor = (request.form.get('nombre_proveedor') or '').strip()
        it.estatus_proveedor = (request.form.get('estatus_proveedor') or '').strip()

        it.area_id = request.form.get('area_id', type=int)
        it.responsable_area_nombre, it.responsable_area_cargo = _proveedor_fill_area_data(it.area_id)

        it.nombre_cargo_evaluador = (request.form.get('nombre_cargo_evaluador') or '').strip()
        it.pais_origen = (request.form.get('pais_origen') or '').strip()
        it.pais_servicio = (request.form.get('pais_servicio') or '').strip()
        it.desc_producto_servicio = (request.form.get('desc_producto_servicio') or '').strip()
        it.estado_avance = request.form.get('estado_avance') or 'Operando'
        it.estado_evaluacion = request.form.get('estado_evaluacion') or 'Proceso'
        it.observaciones = (request.form.get('observaciones') or '').strip()

        _proveedor_apply_scores(it, request.form, cfg)

        db.session.add(it)
        db.session.flush()

        _proveedor_save_files(it, request.files.getlist('evidencias'))

        db.session.commit()
        flash("Proveedor registrado.", "success")
        return redirect(url_for('proveedores_matriz'))

    html = _render_proveedor_form(
        item=None,
        areas=areas,
        paises=paises,
        cfg=cfg,
        is_edit=False
    )
    return render_template_string(BASE, content=Markup(html))


# =========================
# EVIDENCIA — Descargar
# =========================
@app.route('/proveedores/evidencia/<int:evi_id>')
@login_required
def proveedores_evidencia_download(evi_id):
    evi = ProveedorEvidencia.query.get_or_404(evi_id)
    directory = app.config['UPLOAD_PROVEEDORES_DIR']
    return send_from_directory(
        directory=directory,
        path=evi.filename,
        as_attachment=True,
        download_name=evi.original_name,
        mimetype=evi.mime
    )


# =========================
# EVIDENCIA — RAW / VISOR
# =========================
@app.route('/proveedores/evidencia/<int:evi_id>/raw')
@login_required
def proveedores_evidencia_raw(evi_id):
    evi = ProveedorEvidencia.query.get_or_404(evi_id)
    fullpath = os.path.join(app.config['UPLOAD_PROVEEDORES_DIR'], evi.filename)

    resp = send_file(
        fullpath,
        mimetype='application/pdf',
        download_name=evi.original_name,
        as_attachment=False
    )
    resp.headers['Content-Disposition'] = f'inline; filename="{evi.original_name}"'
    return resp


@app.route('/proveedores/evidencia/<int:evi_id>/ver')
@login_required
def proveedores_evidencia_view(evi_id):
    evi = ProveedorEvidencia.query.get_or_404(evi_id)

    path = os.path.join(app.config['UPLOAD_PROVEEDORES_DIR'], evi.filename)
    if not os.path.isfile(path):
        abort(404)

    ext = os.path.splitext(evi.filename or '')[1].lower()
    is_pdf = ext == '.pdf'
    is_office = ext in {'.doc', '.docx', '.xls', '.xlsx'}
    is_image = ext in {'.png', '.jpg', '.jpeg', '.webp', '.gif'}

    next_ep = request.args.get('next')
    reg_id = request.args.get('reg_id', type=int)

    if next_ep == 'proveedores_detalle' and reg_id:
        back_url = url_for('proveedores_detalle', id=reg_id)
        back_label = '⬅ Volver al Detalle'
    elif next_ep == 'proveedores_edit' and reg_id:
        back_url = url_for('proveedores_edit', id=reg_id)
        back_label = '⬅ Volver a Edición'
    else:
        back_url = url_for('proveedores_matriz')
        back_label = '⬅ Volver a la Matriz'

    pdf_converted_name = None
    if is_office:
        try:
            converted_dir = app.config.get(
                'UPLOAD_PROVEEDORES_CONVERTED_DIR',
                os.path.join(app.root_path, 'static', 'converted_proveedores_evidencias')
            )
            os.makedirs(converted_dir, exist_ok=True)

            pdf_converted_path = ensure_pdf_from_office(path, output_dir=converted_dir)
            if pdf_converted_path and os.path.isfile(pdf_converted_path):
                pdf_converted_name = os.path.basename(pdf_converted_path)
        except Exception:
            pdf_converted_name = None

    inner_html = """
    <div class="provevi-shell">
      <div class="provevi-header-actions">
        <a href="{{ back_url }}" class="btn rounded-pill px-4 py-2 fw-bold provevi-back-btn">
          {{ back_label }}
        </a>
        <div class="provevi-file-pill" title="{{ original_name }}">📎 {{ original_name }}</div>
      </div>

      <div class="provevi-card">
        <div class="provevi-card-body">
          {% if is_pdf %}
            <iframe src="{{ url_for('proveedores_evidencia_raw', evi_id=evi_id) }}" class="provevi-frame"></iframe>
          {% elif pdf_converted_name %}
            <iframe src="{{ url_for('static', filename='converted_proveedores_evidencias/' ~ pdf_converted_name) }}" class="provevi-frame"></iframe>
          {% elif is_image %}
            <div class="text-center">
              <img src="{{ url_for('proveedores_evidencia_raw', evi_id=evi_id) }}" class="img-fluid rounded shadow-sm">
            </div>
          {% else %}
            <div class="alert alert-warning mb-0">
              No se pudo mostrar vista previa.
              <a href="{{ url_for('proveedores_evidencia_download', evi_id=evi_id) }}" target="_blank">Abrir archivo</a>
            </div>
          {% endif %}
        </div>
      </div>
    </div>

    <style>
      body{background-image:url('/static/img/ccsgsi.jpg');background-size:cover;background-position:center;background-attachment:fixed;background-repeat:no-repeat;}
      .provevi-shell{width:96%;max-width:1650px;margin:10px auto 30px auto;}
      .provevi-header-actions{display:flex;justify-content:center;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:16px;}
      .provevi-back-btn{background:#ffffff;color:#000000;border:2px solid #ffffff;box-shadow:0 4px 10px rgba(0,0,0,.10);}
      .provevi-back-btn:hover{background:#f3f4f6;color:#000000;border-color:#f3f4f6;}
      .provevi-file-pill{background:#3f86d6;color:#fff;border-radius:999px;padding:10px 16px;font-weight:700;max-width:520px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;box-shadow:0 4px 10px rgba(0,0,0,.10);}
      .provevi-card{background:rgba(248,252,255,.96)!important;border-radius:18px;backdrop-filter:blur(6px);box-shadow:0 10px 24px rgba(0,0,0,.18);overflow:hidden;}
      .provevi-card-body{padding:16px;}
      .provevi-frame{width:100%;height:78vh;border:none;border-radius:12px;background:#fff;}
    </style>
    """

    return render_template_string(
        BASE,
        content=Markup(render_template_string(
            inner_html,
            back_url=back_url,
            back_label=back_label,
            evi_id=evi_id,
            original_name=evi.original_name or evi.filename,
            is_pdf=is_pdf,
            is_image=is_image,
            pdf_converted_name=pdf_converted_name
        ))
    )


# =========================
# EVIDENCIA — Eliminar
# =========================
@app.route('/proveedores/evidencia/<int:evi_id>/delete', methods=['POST'])
@login_required
def proveedores_evidencia_delete(evi_id):
    evi = ProveedorEvidencia.query.get_or_404(evi_id)
    p = os.path.join(app.config['UPLOAD_PROVEEDORES_DIR'], evi.filename)
    try:
        if os.path.exists(p):
            os.remove(p)
    except Exception:
        pass

    proveedor_id = evi.proveedor_id
    db.session.delete(evi)
    db.session.commit()
    flash("Evidencia eliminada.", "success")
    return redirect(url_for('proveedores_edit', id=proveedor_id))


# =========================
# MATRIZ — Registro de Proveedores
# =========================
@app.route('/proveedores', methods=['GET'])
@login_required
def proveedores_matriz():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Registro de Proveedores"):
            flash("No tiene permiso para ver los registros de proveedores.", "danger")
            return redirect(url_for('menu'))
        read_only = False

    filtro_proveedor = (request.args.get('proveedor') or '').strip()
    filtro_avance = (request.args.get('avance') or '').strip()
    filtro_area_responsable = (request.args.get('area_responsable') or '').strip()
    filtro_criticidad = (request.args.get('criticidad') or '').strip()
    filtro_resultado = (request.args.get('resultado') or '').strip()

    query = (
        ProveedorEvaluacion.query
        .options(
            selectinload(ProveedorEvaluacion.area),
            selectinload(ProveedorEvaluacion.evidencias)
        )
    )

    if filtro_proveedor:
        query = query.filter(ProveedorEvaluacion.nombre_proveedor == filtro_proveedor)

    if filtro_avance:
        query = query.filter(ProveedorEvaluacion.estado_avance == filtro_avance)

    if filtro_area_responsable:
        query = query.filter(ProveedorEvaluacion.area.has(area=filtro_area_responsable))

    if filtro_criticidad:
        query = query.filter(ProveedorEvaluacion.criticidad_texto == filtro_criticidad)

    if filtro_resultado:
        query = query.filter(ProveedorEvaluacion.resultado_evaluacion == filtro_resultado)

    items = query.order_by(ProveedorEvaluacion.id.desc()).all()

    opciones_proveedor = [
        x[0] for x in db.session.query(ProveedorEvaluacion.nombre_proveedor)
        .filter(ProveedorEvaluacion.nombre_proveedor.isnot(None))
        .filter(ProveedorEvaluacion.nombre_proveedor != '')
        .distinct()
        .order_by(ProveedorEvaluacion.nombre_proveedor.asc())
        .all()
    ]

    opciones_avance = [
        x[0] for x in db.session.query(ProveedorEvaluacion.estado_avance)
        .filter(ProveedorEvaluacion.estado_avance.isnot(None))
        .filter(ProveedorEvaluacion.estado_avance != '')
        .distinct()
        .order_by(ProveedorEvaluacion.estado_avance.asc())
        .all()
    ]

    opciones_area_responsable = [
        x[0] for x in db.session.query(AreaEmpresa.area)
        .join(ProveedorEvaluacion, ProveedorEvaluacion.area_id == AreaEmpresa.id)
        .filter(AreaEmpresa.area.isnot(None))
        .filter(AreaEmpresa.area != '')
        .distinct()
        .order_by(AreaEmpresa.area.asc())
        .all()
    ]

    opciones_criticidad = [
        x[0] for x in db.session.query(ProveedorEvaluacion.criticidad_texto)
        .filter(ProveedorEvaluacion.criticidad_texto.isnot(None))
        .filter(ProveedorEvaluacion.criticidad_texto != '')
        .distinct()
        .order_by(ProveedorEvaluacion.criticidad_texto.asc())
        .all()
    ]

    opciones_resultado = [
        x[0] for x in db.session.query(ProveedorEvaluacion.resultado_evaluacion)
        .filter(ProveedorEvaluacion.resultado_evaluacion.isnot(None))
        .filter(ProveedorEvaluacion.resultado_evaluacion != '')
        .distinct()
        .order_by(ProveedorEvaluacion.resultado_evaluacion.asc())
        .all()
    ]

    total_general = ProveedorEvaluacion.query.count()
    total_filtrados = len(items)

    html = """
    <div class="provmat-shell">

      <div class="provmat-header-card">
        <div class="provmat-header-overlay">
          <div class="provmat-header-text">
            <h3 class="provmat-title m-0">Registro de Proveedores</h3>
            <div class="provmat-subtitle">
              Visualización resumida del registro de proveedores, criticidad, resultado de evaluación y responsables del proceso
            </div>
          </div>
        </div>
      </div>

      <div class="provmat-header-actions">

        {% if not read_only %}
        <a href="{{ url_for('proveedores_param') }}"
           class="btn btn-secondary rounded-pill px-4 fw-bold"
           onclick="showLoader()">
          ⚙️ Parametrización
        </a>

        <a href="{{ url_for('proveedores_new') }}"
           class="btn btn-primary rounded-pill px-4 fw-bold"
           onclick="showLoader()">
          ➕ Agregar Registro
        </a>
        {% endif %}
      </div>

      <div class="provmat-topbar-card">
        <div class="provmat-topbar-title">Resumen de proveedores</div>
        <div class="provmat-topbar-subtitle">
          Total registros: <strong>{{ total_general }}</strong>
          &nbsp; | &nbsp;
          Mostrando: <strong>{{ total_filtrados }}</strong>
        </div>
      </div>

      <div class="provmat-filter-card">
        <div class="provmat-filter-head">Filtros de búsqueda</div>
        <div class="provmat-filter-body">
          <form method="get">
            <div class="row g-2 align-items-end">

              <div class="col-md-3">
                <label class="form-label provmat-label">Proveedor</label>
                <select name="proveedor" class="form-select form-select-sm provmat-input-sm">
                  <option value="">-- Todos --</option>
                  {% for op in opciones_proveedor %}
                    <option value="{{ op }}" {% if filtro_proveedor == op %}selected{% endif %}>{{ op }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-2">
                <label class="form-label provmat-label">Avance</label>
                <select name="avance" class="form-select form-select-sm provmat-input-sm">
                  <option value="">-- Todos --</option>
                  {% for op in opciones_avance %}
                    <option value="{{ op }}" {% if filtro_avance == op %}selected{% endif %}>{{ op }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-2">
                <label class="form-label provmat-label">Área responsable</label>
                <select name="area_responsable" class="form-select form-select-sm provmat-input-sm">
                  <option value="">-- Todas --</option>
                  {% for op in opciones_area_responsable %}
                    <option value="{{ op }}" {% if filtro_area_responsable == op %}selected{% endif %}>{{ op }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-2">
                <label class="form-label provmat-label">Criticidad</label>
                <select name="criticidad" class="form-select form-select-sm provmat-input-sm">
                  <option value="">-- Todas --</option>
                  {% for op in opciones_criticidad %}
                    <option value="{{ op }}" {% if filtro_criticidad == op %}selected{% endif %}>{{ op }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-2">
                <label class="form-label provmat-label">Resultado</label>
                <select name="resultado" class="form-select form-select-sm provmat-input-sm">
                  <option value="">-- Todos --</option>
                  {% for op in opciones_resultado %}
                    <option value="{{ op }}" {% if filtro_resultado == op %}selected{% endif %}>{{ op }}</option>
                  {% endfor %}
                </select>
              </div>

              <div class="col-md-1">
                <div class="d-flex gap-2 provmat-filter-actions flex-column">
                  <button type="submit" class="btn btn-primary btn-sm rounded-pill px-3 w-100 fw-bold">
                    Filtrar
                  </button>

                  <a href="{{ url_for('proveedores_matriz') }}"
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

      <div class="provmat-card">
        <div class="provmat-card-body">
          <div class="table-responsive provmat-table-wrap">
            <table class="table table-hover align-middle provmat-table mb-0">
              <thead>
                <tr>
                  <th>Proveedor</th>
                  <th>Estatus</th>
                  <th>Avance</th>
                  <th>Área</th>
                  <th>Criticidad</th>
                  <th>Resultado</th>
                  <th>Responsable</th>
                  <th>Fecha</th>
                  <th class="provmat-col-acciones">Acciones</th>
                </tr>
              </thead>

              <tbody>
                {% for it in items %}
                <tr>
                  <td>{{ it.nombre_proveedor or '—' }}</td>
                  <td>{{ it.estatus_proveedor or '—' }}</td>
                  <td>{{ it.estado_avance or '—' }}</td>
                  <td>{{ it.area.area if it.area else '—' }}</td>

                  <td class="text-center">
                    <span class="badge {{ it.criticidad_color or 'bg-secondary' }}">
                      {{ it.criticidad_texto or '—' }}
                    </span>
                  </td>

                  <td class="text-center">
                    <span class="badge {{ it.resultado_color or 'bg-secondary' }}">
                      {{ it.resultado_evaluacion or '—' }}
                    </span>
                  </td>

                  <td>{{ it.responsable_area_nombre or '—' }}</td>
                  <td>{{ it.fecha_eval_seguridad or '—' }}</td>

                  <td class="provmat-col-acciones">
                    <div class="provmat-actions-wrap">
                      <a href="{{ url_for('proveedores_detalle', id=it.id) }}"
                         class="btn btn-info btn-sm rounded-pill provmat-btn-action text-white fw-bold"
                         onclick="showLoader()">
                        Ver detalle
                      </a>

                      {% if not read_only %}
                        <a href="{{ url_for('proveedores_edit', id=it.id) }}"
                           class="btn btn-warning btn-sm rounded-pill provmat-btn-action fw-bold"
                           onclick="showLoader()">
                          Editar
                        </a>

                        {% set resultado_norm = (it.resultado_evaluacion or '')|trim|lower %}
                        {% set es_aprobado = resultado_norm in ['aprobado', 'aprobado por seguridad'] %}
                        {% if not es_aprobado %}
                          <a href="{{ url_for('agregar_riesgo',
                                               origen='Proveedor',
                                               proveedor_id=it.id,
                                               proveedor=it.nombre_proveedor or '',
                                               activo=it.nombre_proveedor or '',
                                               descripcion=('Riesgo asociado al proveedor: ' ~ (it.nombre_proveedor or '')),
                                               observacion=('Proveedor con resultado de evaluación: ' ~ (it.resultado_evaluacion or 'No Aprobado'))) }}"
                             class="btn btn-danger btn-sm rounded-pill provmat-btn-action fw-bold"
                             onclick="showLoader()">
                            Registrar riesgo
                          </a>
                        {% endif %}

                        <a href="{{ url_for('proveedores_delete', id=it.id) }}"
                           class="btn btn-danger btn-sm rounded-pill provmat-btn-action fw-bold"
                           onclick="return confirm('¿Eliminar este proveedor?');">
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
                  <td colspan="9" class="text-center text-muted py-4">
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

    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .provmat-shell{
        width:96%;
        max-width:1600px;
        margin:26px auto 24px auto;
      }

      /* =========================
         HEADER SGSI UNIFICADO
      ========================= */
      .provmat-header-card{
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

      .provmat-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .provmat-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
      }

      .provmat-header-overlay::before{
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

      .provmat-header-text{
        max-width:1200px;
      }

      .provmat-header-text::before{
        content:"SGSI · Gestión de Proveedores";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }

      .provmat-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .provmat-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
      }

      /* =========================
         BOTONES
      ========================= */
      .provmat-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .provmat-header-actions .btn{
        border-radius:10px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 6px 14px rgba(0,0,0,.12);
      }

      .provmat-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .provmat-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
      }

      /* =========================
         TOPBAR
      ========================= */
      .provmat-topbar-card{
        background:rgba(255,255,255,.96);
        border-radius:16px;
        box-shadow:0 8px 18px rgba(15,23,42,.14);
        padding:12px 16px;
        margin-bottom:12px;
      }

      .provmat-topbar-title{
        font-weight:900;
        font-size:.95rem;
        color:#101827;
      }

      .provmat-topbar-subtitle{
        font-size:.82rem;
        color:#475569;
      }

      /* =========================
         FILTROS
      ========================= */
      .provmat-filter-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        box-shadow:0 10px 24px rgba(15,23,42,.16);
        margin-bottom:14px;
        overflow:hidden;
      }

      .provmat-filter-head{
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1);
        color:#fff;
        font-weight:800;
        font-size:.82rem;
        padding:10px 14px;
      }

      .provmat-filter-body{
        padding:8px 7px;
      }

      .provmat-label{
        font-size:.70rem;
        font-weight:900;
        color:#0b4a8f;
        text-transform:uppercase;
        margin-bottom:4px;
      }

      .provmat-input-sm{
        min-height:30px !important;
        font-size:.72rem !important;
        border-radius:10px !important;
        border:1px solid #d9e3f0 !important;
        background:#f8fafc !important;
      }

      .provmat-input-sm:focus{
        border-color:#3f86d6 !important;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
        background:#fff !important;
      }

      /* =========================
         CARD PRINCIPAL
      ========================= */
      .provmat-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
      }

      .provmat-card-body{
        padding:16px;
      }

      /* =========================
         TABLA SGSI
      ========================= */
      .provmat-table thead th{
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff !important;
        font-weight:900;
        font-size:.78rem;
        border:none;
        padding:9px 8px;
        text-align:center;
      }

      .provmat-table td{
        font-size:.82rem;
        padding:9px 8px;
        vertical-align:middle;
        border-bottom:1px solid #e5edf7;
      }

      .provmat-table tbody tr:nth-child(even){
        background:#f8fbff;
      }

      .provmat-table tbody tr:hover{
        background:#eef6ff;
      }

      /* =========================
         ACCIONES
      ========================= */
      .provmat-col-acciones{
        width:160px;
        text-align:center;
      }

      .provmat-actions-wrap{
        display:flex;
        flex-direction:column;
        gap:6px;
        align-items:center;
      }

      .provmat-btn-action{
        font-size:.72rem;
        padding:4px 10px;
        min-width:110px;
        border-radius:999px;
        font-weight:800;
      }

      /* =========================
         BADGES
      ========================= */
      .badge{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }

      .badge-verde-claro{ background:#d1fae5; color:#065f46; }
      .badge-verde-oscuro{ background:#10b981; color:#fff; }
      .badge-amarillo{ background:#fef3c7; color:#92400e; }
      .badge-rojo{ background:#fee2e2; color:#991b1b; }
      .badge-aprobado{ background:#dcfce7; color:#166534; }
      .badge-revision{ background:#fef3c7; color:#92400e; }
      .badge-noaprob{ background:#fee2e2; color:#991b1b; }

      /* =========================
         RESPONSIVE
      ========================= */
      @media (max-width:992px){
        .provmat-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .provmat-title{
          font-size:1.18rem;
        }

        .provmat-subtitle{
          font-size:.75rem;
        }

        .provmat-card-body{
          padding:12px;
        }
      }

      @media (max-width:768px){
        .provmat-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .provmat-header-overlay::before{
          margin:0;
        }

        .provmat-header-text::before{
          margin-left:auto;
          margin-right:auto;
        }
      }
    </style>
    """

    inner = render_template_string(
        html,
        items=items,
        read_only=read_only,
        opciones_proveedor=opciones_proveedor,
        opciones_avance=opciones_avance,
        opciones_area_responsable=opciones_area_responsable,
        opciones_criticidad=opciones_criticidad,
        opciones_resultado=opciones_resultado,
        filtro_proveedor=filtro_proveedor,
        filtro_avance=filtro_avance,
        filtro_area_responsable=filtro_area_responsable,
        filtro_criticidad=filtro_criticidad,
        filtro_resultado=filtro_resultado,
        total_filtrados=total_filtrados,
        total_general=total_general
    )
    return render_template_string(BASE, content=Markup(inner))


# =========================
# DETALLE — Proveedor
# =========================
@app.route('/proveedores/detalle/<int:id>')
@login_required
def proveedores_detalle(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Registro de Proveedores"):
            flash("No tiene permiso para ver el detalle del proveedor.", "danger")
            return redirect(url_for('proveedores_matriz'))
        read_only = False

    it = (
        ProveedorEvaluacion.query
        .options(
            selectinload(ProveedorEvaluacion.area),
            selectinload(ProveedorEvaluacion.evidencias)
        )
        .get_or_404(id)
    )

    def fmt_fecha(v):
        if not v:
            return '—'
        try:
            return v.strftime('%Y-%m-%d')
        except Exception:
            return str(v)

    def yn_badge(v):
        val = (v or '').strip().lower()
        if val in ('sí', 'si'):
            return Markup('<span class="badge badge-aprobado px-3 py-2">Sí</span>')
        if val == 'no':
            return Markup('<span class="badge badge-noaprob px-3 py-2">No</span>')
        return Markup('<span class="badge bg-secondary px-3 py-2">—</span>')

    html = """
    <div class="provdet-shell">

      <div class="provdet-header-card">
        <div class="provdet-header-overlay">
          <div class="provdet-header-text">
            <h3 class="provdet-title m-0">Detalle del Proveedor</h3>
            <div class="provdet-subtitle">
              Consulta completa del registro en modo solo lectura
            </div>
          </div>
        </div>
      </div>

      <div class="provdet-header-actions">
        <a href="{{ url_for('proveedores_matriz') }}"
           class="btn rounded-pill px-4 fw-bold provdet-back-btn">
          ⬅ Volver a la Matriz
        </a>

        {% if not read_only %}
          <a href="{{ url_for('proveedores_edit', id=it.id) }}"
             class="btn btn-warning rounded-pill px-4 fw-bold">
            Editar registro
          </a>
        {% endif %}
      </div>

      <div class="provdet-card">
        <div class="provdet-card-body">

          <!-- =========================
               INFORMACIÓN GENERAL
          ========================== -->
          <div class="provdet-section">
            <div class="provdet-section-title">Información general del proveedor</div>
            <div class="row g-3">

              <div class="col-md-3">
                <div class="provdet-field">
                  <div class="provdet-label">Fecha de registro por el área de seguridad</div>
                  <div class="provdet-value">{{ fmt_fecha(it.fecha_eval_seguridad) }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="provdet-field">
                  <div class="provdet-label">Nombre del proveedor</div>
                  <div class="provdet-value provdet-value-lg">{{ it.nombre_proveedor or '—' }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="provdet-field">
                  <div class="provdet-label">Estatus del proveedor</div>
                  <div class="provdet-value">{{ it.estatus_proveedor or '—' }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="provdet-field">
                  <div class="provdet-label">Área responsable</div>
                  <div class="provdet-value">{{ it.area.area if it.area else '—' }}</div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="provdet-field">
                  <div class="provdet-label">Nombre del responsable del área</div>
                  <div class="provdet-value">{{ it.responsable_area_nombre or '—' }}</div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="provdet-field">
                  <div class="provdet-label">Cargo del responsable del área</div>
                  <div class="provdet-value">{{ it.responsable_area_cargo or '—' }}</div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="provdet-field">
                  <div class="provdet-label">Nombre y cargo del evaluador</div>
                  <div class="provdet-value">{{ it.nombre_cargo_evaluador or '—' }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="provdet-field">
                  <div class="provdet-label">País de origen</div>
                  <div class="provdet-value">{{ it.pais_origen or '—' }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="provdet-field">
                  <div class="provdet-label">País de servicio</div>
                  <div class="provdet-value">{{ it.pais_servicio or '—' }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="provdet-field">
                  <div class="provdet-label">Estado / avance</div>
                  <div class="provdet-value">{{ it.estado_avance or '—' }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="provdet-field">
                  <div class="provdet-label">Estado del registro</div>
                  <div class="provdet-value">{{ it.estado_evaluacion or '—' }}</div>
                </div>
              </div>

              <div class="col-12">
                <div class="provdet-field">
                  <div class="provdet-label">Descripción del producto / servicio</div>
                  <div class="provdet-value provdet-value-lg">{{ it.desc_producto_servicio or '—' }}</div>
                </div>
              </div>

            </div>
          </div>

          <!-- =========================
               CALIFICACIÓN DEL PROVEEDOR
          ========================== -->
          <div class="provdet-section">
            <div class="provdet-section-title">Calificación del proveedor</div>
            <div class="row g-3">

              <div class="col-md-4">
                <div class="provdet-field">
                  <div class="provdet-label">¿Es transversal a toda la organización?</div>
                  <div class="provdet-value d-flex justify-content-between align-items-center gap-2">
                    <span>{{ yn_badge(it.es_transversal) }}</span>
                    <span class="provdet-score">Valor: {{ it.valor_alcance or 0 }}%</span>
                  </div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="provdet-field">
                  <div class="provdet-label">¿Es esencial para la continuidad?</div>
                  <div class="provdet-value d-flex justify-content-between align-items-center gap-2">
                    <span>{{ yn_badge(it.es_esencial) }}</span>
                    <span class="provdet-score">Valor: {{ it.valor_esencial or 0 }}%</span>
                  </div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="provdet-field">
                  <div class="provdet-label">¿Tiene plan de continuidad?</div>
                  <div class="provdet-value d-flex justify-content-between align-items-center gap-2">
                    <span>{{ yn_badge(it.tiene_plan_cont) }}</span>
                    <span class="provdet-score">Valor: {{ it.valor_plan_cont or 0 }}%</span>
                  </div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="provdet-field">
                  <div class="provdet-label">¿Tiene plan de recuperación?</div>
                  <div class="provdet-value d-flex justify-content-between align-items-center gap-2">
                    <span>{{ yn_badge(it.tiene_plan_rec) }}</span>
                    <span class="provdet-score">Valor: {{ it.valor_plan_rec or 0 }}%</span>
                  </div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="provdet-field">
                  <div class="provdet-label">¿Existen alternativas en el mercado?</div>
                  <div class="provdet-value d-flex justify-content-between align-items-center gap-2">
                    <span>{{ yn_badge(it.existen_alternativas) }}</span>
                    <span class="provdet-score">Valor: {{ it.valor_alternativas or 0 }}%</span>
                  </div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="provdet-field">
                  <div class="provdet-label">Impacto en caso de falla</div>
                  <div class="provdet-value d-flex justify-content-between align-items-center gap-2">
                    <span class="badge bg-secondary px-3 py-2">{{ it.impacto_falla or '—' }}</span>
                    <span class="provdet-score">Valor: {{ it.valor_impacto_falla or 0 }}%</span>
                  </div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="provdet-field">
                  <div class="provdet-label">¿Existe plan de migración?</div>
                  <div class="provdet-value d-flex justify-content-between align-items-center gap-2">
                    <span>{{ yn_badge(it.existe_plan_migracion) }}</span>
                    <span class="provdet-score">Valor: {{ it.valor_plan_migracion or 0 }}%</span>
                  </div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="provdet-field">
                  <div class="provdet-label">¿Procesa / almacena información sensible?</div>
                  <div class="provdet-value d-flex justify-content-between align-items-center gap-2">
                    <span>{{ yn_badge(it.procesa_info_sensible) }}</span>
                    <span class="provdet-score">Valor: {{ it.valor_info_sensible or 0 }}%</span>
                  </div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="provdet-field">
                  <div class="provdet-label">¿Procesa / almacena datos personales?</div>
                  <div class="provdet-value d-flex justify-content-between align-items-center gap-2">
                    <span>{{ yn_badge(it.procesa_datos_personales) }}</span>
                    <span class="provdet-score">Valor: {{ it.valor_datos_personales or 0 }}%</span>
                  </div>
                </div>
              </div>

              <div class="col-md-6">
                <div class="provdet-field">
                  <div class="provdet-label">¿Procesa / almacena información en la nube?</div>
                  <div class="provdet-value d-flex justify-content-between align-items-center gap-2">
                    <span>{{ yn_badge(it.procesa_info_nube) }}</span>
                    <span class="provdet-score">Valor: {{ it.valor_nube or 0 }}%</span>
                  </div>
                </div>
              </div>

              <div class="col-md-6">
                <div class="provdet-field">
                  <div class="provdet-label">¿Incluye SLA definidos?</div>
                  <div class="provdet-value d-flex justify-content-between align-items-center gap-2">
                    <span>{{ yn_badge(it.incluye_sla) }}</span>
                    <span class="provdet-score">Valor: {{ it.valor_sla or 0 }}%</span>
                  </div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="provdet-field text-center">
                  <div class="provdet-label">Criticidad total</div>
                  <div class="provdet-big-number">{{ it.criticidad_pct or 0 }}%</div>
                  <div class="mt-2">
                    <span class="badge {{ it.criticidad_color or 'bg-secondary' }} px-3 py-2">
                      {{ it.criticidad_texto or '—' }}
                    </span>
                  </div>
                </div>
              </div>


              <div class="col-md-4">
                <div class="provdet-field">
                  <div class="provdet-label">¿Requiere formulario?</div>
                  <div class="provdet-value d-flex justify-content-between align-items-center gap-2">
                    <span>{{ yn_badge(it.requiere_formulario) }}</span>
                    <span class="provdet-score">Puntos cert.: {{ it.puntos_certificacion or 0 }}%</span>
                  </div>
                </div>
              </div>

            </div>
          </div>

          <!-- =========================
               REGISTRO DEL PROVEEDOR
          ========================== -->
          <div class="provdet-section">
            <div class="provdet-section-title">Registro del proveedor</div>
            <div class="row g-3">

              <div class="col-md-3">
                <div class="provdet-field">
                  <div class="provdet-label">¿Tiene certificación?</div>
                  <div class="provdet-value">{{ yn_badge(it.tiene_certificacion) }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="provdet-field">
                  <div class="provdet-label">Número de certificaciones</div>
                  <div class="provdet-value">{{ it.num_certificaciones or 0 }}</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="provdet-field">
                  <div class="provdet-label">Puntos obtenidos en el formulario</div>
                  <div class="provdet-value">{{ it.puntos_formulario or 0 }}%</div>
                </div>
              </div>

              <div class="col-md-3">
                <div class="provdet-field">
                  <div class="provdet-label">Puntos por certificación</div>
                  <div class="provdet-value">{{ it.puntos_certificacion or 0 }}%</div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="provdet-field text-center">
                  <div class="provdet-label">Calificación total</div>
                  <div class="provdet-big-number">{{ it.calificacion_total or 0 }}%</div>
                  <div class="mt-2">
                    <span class="badge {{ it.resultado_color or 'bg-secondary' }} px-3 py-2">
                      {{ it.resultado_evaluacion or '—' }}
                    </span>
                  </div>
                </div>
              </div>

              <div class="col-12">
                <div class="provdet-field">
                  <div class="provdet-label">Nombre de las certificaciones</div>
                  <div class="provdet-value provdet-value-lg">{{ it.nombre_certificaciones or '—' }}</div>
                </div>
              </div>

            </div>
          </div>

          <!-- =========================
               EVIDENCIAS
          ========================== -->
          <div class="provdet-section">
            <div class="provdet-section-title">Evidencias</div>

            {% if it.evidencias %}
              <div class="provdet-ev-grid">
                {% for ev in it.evidencias %}
                  <div class="provdet-file-card">
                    <div class="provdet-file-left">
                      <div class="provdet-file-icon">PDF</div>
                      <div class="provdet-file-meta">
                        <div class="provdet-file-label">Archivo</div>
                        <a class="provdet-file-name"
                           href="{{ url_for('proveedores_evidencia_view', evi_id=ev.id, next='proveedores_detalle', reg_id=it.id) }}">
                          {{ ev.original_name or ev.filename }}
                        </a>
                        <div class="provdet-file-size">
                          {{ (ev.size / 1024)|round(1) if ev.size else 0 }} KB
                        </div>
                      </div>
                    </div>

                    <a href="{{ url_for('proveedores_evidencia_download', evi_id=ev.id) }}"
                       class="btn btn-outline-primary rounded-pill px-3 fw-bold">
                      Descargar
                    </a>
                  </div>
                {% endfor %}
              </div>
            {% else %}
              <div class="provdet-empty-box">No hay evidencias cargadas.</div>
            {% endif %}
          </div>

          <!-- =========================
               OBSERVACIONES
          ========================== -->
          <div class="provdet-section">
            <div class="provdet-section-title">Observaciones</div>
            <div class="provdet-field">
              <div class="provdet-value provdet-value-lg">{{ it.observaciones or '—' }}</div>
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

      .provdet-shell{
        width:96%;
        max-width:1500px;
        margin:26px auto 24px auto;
      }

      .provdet-header-card{
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

      .provdet-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .provdet-header-overlay{
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

      .provdet-header-overlay::before{
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

      .provdet-header-text{
        max-width:1200px;
        width:100%;
        display:block !important;
        transform:none !important;
      }

      .provdet-header-text::before{
        content:"SGSI · Detalle de Proveedor";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .provdet-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .provdet-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .provdet-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .provdet-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .provdet-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .provdet-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .provdet-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .provdet-card-body{
        padding:18px;
      }

      .provdet-section{
        margin-bottom:14px;
        background:#ffffff;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:8px 7px;
        box-shadow:0 8px 18px rgba(15,23,42,.08);
      }

      .provdet-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:0 0 12px 0;
      }

      .provdet-field{
        background:linear-gradient(180deg,#f8fbff 0%,#ffffff 100%);
        border:1px solid #dbe6f4;
        border-radius:14px;
        padding:12px;
        min-height:78px;
        height:100%;
      }

      .provdet-label{
        font-size:.70rem;
        font-weight:900;
        text-transform:uppercase;
        letter-spacing:.35px;
        color:#0b4a8f;
        margin-bottom:6px;
      }

      .provdet-value{
        color:#101827;
        font-size:.86rem;
        line-height:1.38;
        white-space:pre-wrap;
        word-break:break-word;
        overflow-wrap:anywhere;
      }

      .provdet-value-lg{
        min-height:72px;
      }

      .provdet-big-number{
        font-size:1.75rem;
        font-weight:950;
        color:#0b4a8f;
        line-height:1.1;
      }

      .provdet-score{
        font-size:.68rem;
        font-weight:900;
        color:#475569;
        white-space:nowrap;
      }

      .provdet-ev-grid{
        display:grid;
        grid-template-columns:repeat(auto-fit, minmax(320px, 1fr));
        gap:14px;
      }

      .provdet-file-card{
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

      .provdet-file-card:hover{
        transform:translateY(-3px);
        box-shadow:0 10px 20px rgba(15,23,42,.13);
      }

      .provdet-file-left{
        display:flex;
        align-items:center;
        gap:12px;
        min-width:0;
      }

      .provdet-file-icon{
        width:52px;
        height:52px;
        min-width:52px;
        border-radius:12px;
        background:linear-gradient(135deg,#b91c1c,#b91c1c);
        color:#ffffff;
        display:flex;
        align-items:center;
        justify-content:center;
        font-weight:950;
        font-size:.82rem;
        flex:0 0 auto;
      }

      .provdet-file-meta{
        min-width:0;
      }

      .provdet-file-label{
        font-size:.70rem;
        color:#475569;
        font-weight:900;
        text-transform:uppercase;
        letter-spacing:.35px;
      }

      .provdet-file-name{
        display:block;
        font-weight:900;
        color:#1d4ed8;
        text-decoration:none;
        word-break:break-word;
        font-size:.82rem;
        margin-top:2px;
      }

      .provdet-file-name:hover{
        text-decoration:underline;
      }

      .provdet-file-size{
        font-size:.70rem;
        color:#475569;
        margin-top:3px;
        font-weight:700;
      }

      .provdet-empty-box{
        background:#f8fbff;
        border:1px dashed #b8cce8;
        border-radius:14px;
        padding:16px;
        text-align:center;
        color:#475569;
        font-size:.82rem;
        font-weight:800;
      }

      .badge,
      .badge-verde-claro,
      .badge-verde-oscuro,
      .badge-amarillo,
      .badge-rojo,
      .badge-aprobado,
      .badge-revision,
      .badge-noaprob{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }

      .badge-verde-claro{ background:#d1fae5; color:#065f46; }
      .badge-verde-oscuro{ background:#10b981; color:#ffffff; }
      .badge-amarillo{ background:#fef3c7; color:#92400e; }
      .badge-rojo{ background:#fee2e2; color:#991b1b; }
      .badge-aprobado{ background:#dcfce7; color:#166534; }
      .badge-revision{ background:#fef3c7; color:#92400e; }
      .badge-noaprob{ background:#fee2e2; color:#991b1b; }

      .btn.rounded-pill{
        border-radius:10px !important;
      }

      @media (max-width:992px){
        .provdet-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .provdet-header-card{
          min-height:88px;
        }

        .provdet-title{
          font-size:1.20rem;
        }

        .provdet-card-body{
          padding:8px 7px;
        }

        .provdet-file-card{
          flex-direction:column;
          align-items:flex-start;
        }
      }

      @media (max-width:768px){
        .provdet-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .provdet-header-overlay::before{
          margin:0;
        }

        .provdet-header-text::before{
          margin-left:auto;
          margin-right:auto;
        }

        .provdet-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(
        html,
        it=it,
        read_only=read_only,
        fmt_fecha=fmt_fecha,
        yn_badge=yn_badge
    )
    return render_template_string(BASE, content=Markup(inner))


# =========================
# EDITAR — Proveedor
# =========================
@app.route('/proveedores/edit/<int:id>', methods=['GET','POST'])
@login_required
def proveedores_edit(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor' or (
        user.role != 'admin' and not verificar_permiso(user, "Registro de Proveedores")
    ):
        flash("No tiene permiso para editar registros del módulo de proveedores.", "danger")
        return redirect(url_for('proveedores_matriz'))

    item = (
        ProveedorEvaluacion.query
        .options(
            selectinload(ProveedorEvaluacion.area),
            selectinload(ProveedorEvaluacion.evidencias)
        )
        .get_or_404(id)
    )

    areas = AreaEmpresa.query.order_by(AreaEmpresa.area.asc()).all()
    cfg = ProveedorEvalConfig.get()
    paises = _proveedor_paises()

    if request.method == 'POST':
        item.fecha_eval_seguridad = request.form.get('fecha_eval_seguridad')
        item.nombre_proveedor = (request.form.get('nombre_proveedor') or '').strip()
        item.estatus_proveedor = (request.form.get('estatus_proveedor') or '').strip()

        item.area_id = request.form.get('area_id', type=int)
        item.responsable_area_nombre, item.responsable_area_cargo = _proveedor_fill_area_data(item.area_id)

        item.nombre_cargo_evaluador = (request.form.get('nombre_cargo_evaluador') or '').strip()
        item.pais_origen = (request.form.get('pais_origen') or '').strip()
        item.pais_servicio = (request.form.get('pais_servicio') or '').strip()
        item.desc_producto_servicio = (request.form.get('desc_producto_servicio') or '').strip()
        item.estado_avance = request.form.get('estado_avance') or item.estado_avance
        item.estado_evaluacion = request.form.get('estado_evaluacion') or item.estado_evaluacion
        item.observaciones = (request.form.get('observaciones') or '').strip()

        _proveedor_apply_scores(item, request.form, cfg)
        _proveedor_save_files(item, request.files.getlist('evidencias'))

        db.session.commit()
        flash("Proveedor actualizado.", "success")
        return redirect(url_for('proveedores_matriz'))

    html = _render_proveedor_form(
        item=item,
        areas=areas,
        paises=paises,
        cfg=cfg,
        is_edit=True
    )
    return render_template_string(BASE, content=Markup(html))


# =========================
# ELIMINAR — Proveedor
# =========================
@app.route('/proveedores/delete')
@login_required
def proveedores_delete():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor' or (
        user.role != 'admin' and not verificar_permiso(user, "Registro de Proveedores")
    ):
        flash("No tiene permiso para eliminar registros de proveedores.", "danger")
        return redirect(url_for('proveedores_matriz'))

    rid = request.args.get('id', type=int)
    it = ProveedorEvaluacion.query.get(rid)
    if it:
        db.session.delete(it)
        db.session.commit()
        flash("Eliminado correctamente.", "success")
    else:
        flash("Registro no encontrado.", "danger")

    return redirect(url_for('proveedores_matriz'))


# =========================
# PARAMETRIZACIÓN — Proveedores
# =========================
@app.route('/proveedores/param', methods=['GET','POST'])
@login_required
def proveedores_param():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede agregar parametrizaciones de proveedores.", "danger")
        return redirect(url_for('proveedores_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Registro de Proveedores"):
        flash("No tiene permiso para agregar parametrizaciones de proveedores.", "danger")
        return redirect(url_for('proveedores_matriz'))

    cfg = ProveedorEvalConfig.get()

    if request.method == 'POST':
        cfg.min_certificaciones_aprobado = request.form.get('min_certificaciones_aprobado', type=int) or 1
        cfg.pct_aprob_min = request.form.get('pct_aprob_min', type=int) or 81
        cfg.pct_revision_min = request.form.get('pct_revision_min', type=int) or 61

        cfg.crit_muy_baja_max = request.form.get('crit_muy_baja_max', type=int) or 25
        cfg.crit_baja_max = request.form.get('crit_baja_max', type=int) or 50
        cfg.crit_media_max = request.form.get('crit_media_max', type=int) or 75

        cfg.peso_transversal = request.form.get('peso_transversal', type=int) or 0
        cfg.peso_esencial = request.form.get('peso_esencial', type=int) or 0
        cfg.peso_plan_continuidad = request.form.get('peso_plan_continuidad', type=int) or 0
        cfg.peso_plan_recuperacion = request.form.get('peso_plan_recuperacion', type=int) or 0
        cfg.peso_alternativas = request.form.get('peso_alternativas', type=int) or 0
        cfg.peso_impacto_falla = request.form.get('peso_impacto_falla', type=int) or 0
        cfg.peso_plan_migracion = request.form.get('peso_plan_migracion', type=int) or 0
        cfg.peso_info_sensible = request.form.get('peso_info_sensible', type=int) or 0
        cfg.peso_datos_personales = request.form.get('peso_datos_personales', type=int) or 0
        cfg.peso_nube = request.form.get('peso_nube', type=int) or 0
        cfg.peso_sla = request.form.get('peso_sla', type=int) or 0

        db.session.commit()
        flash("Parametrización guardada correctamente.", "success")
        return redirect(url_for('proveedores_matriz'))

    html = """
    <div class="provparam-shell">

      <div class="provparam-header-card">
        <div class="provparam-header-overlay">
          <div class="provparam-header-text">
            <h3 class="provparam-title m-0">Parametrización — Proveedores</h3>
            <div class="provparam-subtitle">
              Configuración de criterios de criticidad, puntuación y umbrales de aprobación
            </div>
          </div>
        </div>
      </div>

      <div class="provparam-header-actions">
        <a href="{{ url_for('proveedores_matriz') }}"
           class="btn rounded-pill px-4 fw-bold provparam-back-btn"
           onclick="showLoader()">
          ⬅ Volver a la Matriz
        </a>
      </div>

      <div class="provparam-card">
        <div class="provparam-card-body">
          <form method="post">
            <div class="row g-3">

              <div class="col-12"><div class="provparam-section-title">Umbrales de resultado</div></div>

              <div class="col-md-4">
                <label class="form-label">Mínimo certificaciones para 100%</label>
                <input type="number" name="min_certificaciones_aprobado" class="form-control" value="{{ cfg.min_certificaciones_aprobado or 1 }}">
              </div>

              <div class="col-md-4">
                <label class="form-label">% mínimo aprobado</label>
                <input type="number" name="pct_aprob_min" class="form-control" value="{{ cfg.pct_aprob_min or 81 }}">
              </div>

              <div class="col-md-4">
                <label class="form-label">% mínimo en revisión</label>
                <input type="number" name="pct_revision_min" class="form-control" value="{{ cfg.pct_revision_min or 61 }}">
              </div>

              <div class="col-12"><div class="provparam-section-title">Umbrales de criticidad</div></div>

              <div class="col-md-4">
                <label class="form-label">Criticidad muy baja hasta</label>
                <input type="number" name="crit_muy_baja_max" class="form-control" value="{{ cfg.crit_muy_baja_max or 25 }}">
              </div>

              <div class="col-md-4">
                <label class="form-label">Criticidad baja hasta</label>
                <input type="number" name="crit_baja_max" class="form-control" value="{{ cfg.crit_baja_max or 50 }}">
              </div>

              <div class="col-md-4">
                <label class="form-label">Criticidad media hasta</label>
                <input type="number" name="crit_media_max" class="form-control" value="{{ cfg.crit_media_max or 75 }}">
              </div>

              <div class="col-12"><div class="provparam-section-title">Pesos de criticidad</div></div>

              <div class="col-md-3"><label class="form-label">Peso transversal</label><input type="number" name="peso_transversal" class="form-control" value="{{ cfg.peso_transversal or 0 }}"></div>
              <div class="col-md-3"><label class="form-label">Peso esencial</label><input type="number" name="peso_esencial" class="form-control" value="{{ cfg.peso_esencial or 0 }}"></div>
              <div class="col-md-3"><label class="form-label">Peso plan continuidad</label><input type="number" name="peso_plan_continuidad" class="form-control" value="{{ cfg.peso_plan_continuidad or 0 }}"></div>
              <div class="col-md-3"><label class="form-label">Peso plan recuperación</label><input type="number" name="peso_plan_recuperacion" class="form-control" value="{{ cfg.peso_plan_recuperacion or 0 }}"></div>

              <div class="col-md-3"><label class="form-label">Peso alternativas</label><input type="number" name="peso_alternativas" class="form-control" value="{{ cfg.peso_alternativas or 0 }}"></div>
              <div class="col-md-3"><label class="form-label">Peso impacto falla</label><input type="number" name="peso_impacto_falla" class="form-control" value="{{ cfg.peso_impacto_falla or 0 }}"></div>
              <div class="col-md-3"><label class="form-label">Peso plan migración</label><input type="number" name="peso_plan_migracion" class="form-control" value="{{ cfg.peso_plan_migracion or 0 }}"></div>
              <div class="col-md-3"><label class="form-label">Peso info sensible</label><input type="number" name="peso_info_sensible" class="form-control" value="{{ cfg.peso_info_sensible or 0 }}"></div>

              <div class="col-md-4"><label class="form-label">Peso datos personales</label><input type="number" name="peso_datos_personales" class="form-control" value="{{ cfg.peso_datos_personales or 0 }}"></div>
              <div class="col-md-4"><label class="form-label">Peso nube</label><input type="number" name="peso_nube" class="form-control" value="{{ cfg.peso_nube or 0 }}"></div>
              <div class="col-md-4"><label class="form-label">Peso SLA</label><input type="number" name="peso_sla" class="form-control" value="{{ cfg.peso_sla or 0 }}"></div>

            </div>

            <div class="provparam-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">Guardar parametrización</button>
              <a href="{{ url_for('proveedores_matriz') }}" class="btn rounded-pill px-4 fw-bold provparam-cancel-btn" onclick="showLoader()">Cancelar</a>
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

      .provparam-shell{
        width:96%;
        max-width:1600px;
        margin:26px auto 24px auto;
      }

      .provparam-header-card{
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

      .provparam-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .provparam-header-overlay{
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

      .provparam-header-overlay::before{
        content:"⚙️";
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

      .provparam-header-text{
        max-width:1200px;
        width:100%;
        display:block !important;
        transform:none !important;
      }

      .provparam-header-text::before{
        content:"SGSI · Parámetros de Proveedores";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .provparam-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .provparam-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .provparam-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .provparam-header-actions .btn,
      .provparam-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .provparam-back-btn,
      .provparam-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
      }

      .provparam-back-btn:hover,
      .provparam-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .provparam-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .provparam-card-body{
        padding:18px;
      }

      .provparam-card .form-label{
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

      .provparam-card .form-control,
      .provparam-card .form-select{
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
        box-shadow:none !important;
      }

      .provparam-card .form-control:focus,
      .provparam-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
        background:#ffffff;
      }

      .provparam-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:10px 0 12px;
      }

      .provparam-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:22px;
        flex-wrap:wrap;
        width:100%;
      }

      .btn.rounded-pill{
        border-radius:10px !important;
      }

      @media (max-width:992px){
        .provparam-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .provparam-header-card{
          min-height:88px;
        }

        .provparam-title{
          font-size:1.20rem;
        }

        .provparam-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .provparam-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .provparam-header-overlay::before{
          margin:0;
        }

        .provparam-header-text::before{
          margin-left:auto;
          margin-right:auto;
        }

        .provparam-header-actions .btn,
        .provparam-bottom-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(html, cfg=cfg)
    return render_template_string(BASE, content=Markup(inner))

# ==========================================================================================================================================
#                                                            Fin Módulo Gestión de Proveedores
# ==========================================================================================================================================


# ==========================================================================================================================================
#                                                       Módulo de Métricas
# ==========================================================================================================================================

import os
import sqlite3
from datetime import datetime
from flask import request, redirect, url_for, flash, render_template_string
from markupsafe import Markup

# ==========================
# DB INCIDENTES SQLITE (instance/incidentes.db)
# ==========================
os.makedirs(app.instance_path, exist_ok=True)
INCIDENTES_DB_PATH = os.path.join(app.instance_path, "incidentes.db")

def get_incidentes_db_connection():
    conn = sqlite3.connect(INCIDENTES_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_incidentes_db():
    os.makedirs(app.instance_path, exist_ok=True)

    conn = sqlite3.connect(INCIDENTES_DB_PATH)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS registro_incidentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_alerta TEXT,
            nombre_alerta TEXT,
            descripcion_alerta TEXT,
            id_incidente TEXT,
            clasificacion_incidente TEXT,
            cargo_responsable TEXT,
            atacante TEXT,
            ubicacion_atacante TEXT,
            tipo_recurso_afectado TEXT,
            nombre_recurso_id TEXT,
            estado TEXT,
            fecha_cierre TEXT,
            descripcion_cierre TEXT,
            principio TEXT,
            prioridad TEXT,
            se_requiere_contencion TEXT,
            fecha_hora_contencion TEXT,
            descripcion_contencion TEXT,
            se_requiere_recuperacion TEXT,
            fecha_hora_recuperacion TEXT,
            descripcion_recuperacion TEXT
        )
    """)

    conn.commit()
    conn.close()

# Crear la base y tabla si no existen
init_incidentes_db()



#========================
# Modelos
#========================


class MetricConfigIncidentes(db.Model):
    __tablename__ = "metric_config_incidentes"

    id = db.Column(db.Integer, primary_key=True)
    eta_objetivo = db.Column(db.Float, nullable=True)   # porcentaje (0-100)
    fecha_ultima_actualizacion = db.Column(db.DateTime, default=datetime.utcnow)

    clasificaciones = db.relationship(
        "MetricConfigIncidentesClasificacion",
        backref="config",
        cascade="all, delete-orphan"
    )


class MetricConfigIncidentesClasificacion(db.Model):
    __tablename__ = "metric_config_incidentes_clasificacion"

    id = db.Column(db.Integer, primary_key=True)
    config_id = db.Column(
        db.Integer,
        db.ForeignKey("metric_config_incidentes.id"),
        nullable=False
    )

    clasificacion = db.Column(db.String(100), nullable=False)  # Ej: Crítico, Alto, Medio
    tmr = db.Column(db.Float, nullable=True)   # Tiempo máx. respuesta
    mtcd = db.Column(db.Float, nullable=True)  # Tiempo MTCD
    mtir = db.Column(db.Float, nullable=True)  # Tiempo MTIR

class MetricasVulnerabilidadesConfig(db.Model):
    # Si NO tienes __tablename__, el nombre de tabla será:
    # "metricas_vulnerabilidades_config"
    # __tablename__ = 'metricas_vulnerabilidades_config'  # opcional

    id = db.Column(db.Integer, primary_key=True)
    meta_anual_activas = db.Column(db.Float, nullable=True)
    creado_por_id = db.Column(db.Integer, nullable=True)

    clasificaciones = db.relationship(
        "MetricasVulnerabilidadesClasificacion",
        back_populates="config",
        cascade="all, delete-orphan"
    )

class MetricasVulnerabilidadesClasificacion(db.Model):
    __tablename__ = 'metricas_vuln_clasificacion'

    id = db.Column(db.Integer, primary_key=True)

    # 🔴 AQUÍ ESTÁ EL PROBLEMA: el string NO coincide con el nombre real de la tabla padre
    # config_id = db.Column(db.Integer, db.ForeignKey('metricas_vuln_config.id'))

    # ✅ AJUSTA EL NOMBRE DEL FOREIGN KEY
    config_id = db.Column(
        db.Integer,
        db.ForeignKey('metricas_vulnerabilidades_config.id'),  # <-- usa el nombre REAL de la tabla padre
        nullable=False
    )

    clasificacion = db.Column(db.String(50), nullable=False)
    cantidad_aceptada = db.Column(db.Integer, nullable=True)
    porcentaje_cumplimiento = db.Column(db.Float, nullable=True)
    tiempo_max_cierre_dias = db.Column(db.Integer, nullable=True)

    config = db.relationship("MetricasVulnerabilidadesConfig", back_populates="clasificaciones")
    

class MetricasVulnerabilidadesNivel(db.Model):
    __tablename__ = "metricas_vulnerabilidades_nivel"

    id = db.Column(db.Integer, primary_key=True)

    config_id = db.Column(
        db.Integer,
        db.ForeignKey("metricas_vulnerabilidades_config.id"),
        nullable=False
    )

    # Clasificación definida por el usuario (Crítico, Alto, Medio, Bajo, etc.)
    clasificacion = db.Column(db.String(100), nullable=False)

    # Cantidad aceptada de vulnerabilidades activas (mensual/anual) según su clasificación
    cantidad_aceptada = db.Column(db.Integer, nullable=True)

    # Distribución del % de cumplimiento de vulnerabilidades según su clasificación
    porcentaje_cumplimiento = db.Column(db.Float, nullable=True)


class MetricasCulturaConfig(db.Model):
    __tablename__ = "metricas_cultura_config"

    id = db.Column(db.Integer, primary_key=True)

    # META U OBJETIVO GENERAL (%)
    meta_general = db.Column(db.Float, nullable=True)

    # INDICADOR META INDIVIDUAL DE EFECTIVIDAD EN LA FORMACION INICIAL (FI) (%)
    meta_fi = db.Column(db.Float, nullable=True)

    # INDICADOR META INDIVIDUAL EJECUCION DE LA PLANEACION (EP) (%)
    meta_ep = db.Column(db.Float, nullable=True)

    fecha_actualizacion = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

class MetricasCultura(db.Model):
    __tablename__ = "metricas_cultura"

    id = db.Column(db.Integer, primary_key=True)

    anio = db.Column(db.Integer, nullable=False)
    mes  = db.Column(db.Integer, nullable=False)  # 1–12

    # Datos base
    personas_contratadas = db.Column(db.Integer, nullable=False)
    formacion_inicial_aprobada = db.Column(db.Integer, nullable=False)
    personas_reinduccion = db.Column(db.Integer, nullable=False)
    reinduccion_aprobada = db.Column(db.Integer, nullable=False)

    # Metas calculadas (porcentaje 0–100)
    meta_formacion = db.Column(db.Float)             # META ALCANZADA DE FORMACIÓN
    actividades_planeadas = db.Column(db.Integer, nullable=False)
    actividades_ejecutadas = db.Column(db.Integer, nullable=False)
    meta_actividades = db.Column(db.Float)           # META ALCANZADA DE ACTIVIDADES
    resultado_meta_general = db.Column(db.Float)     # RESULTADO DE LA META U OBJETIVO GENERAL

    # Análisis textual (AI + edición manual)
    analisis_mensual = db.Column(db.Text)

    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("anio", "mes", name="uq_metricas_cultura_anio_mes"),
    )

class MetricaIncidente(db.Model):
    __tablename__ = "metricas_incidentes"

    id = db.Column(db.Integer, primary_key=True)

    # Referencia al incidente original (tabla registro_incidentes)
    incidente_id = db.Column(db.Integer, nullable=False)

    # Datos básicos
    fecha_registro = db.Column(db.DateTime, nullable=False)  # Fecha y hora de la alerta
    descripcion_incidente = db.Column(db.Text, nullable=False)
    cargo_responsable = db.Column(db.String(255), nullable=True)
    clasificacion = db.Column(db.String(120), nullable=True)

    # Bloque CONTENCIÓN (MTDC)
    requiere_contencion = db.Column(db.Boolean, default=False)
    descripcion_mtcd = db.Column(db.Text, nullable=True)
    fecha_fin_mtcd = db.Column(db.DateTime, nullable=True)
    tiempo_mtcd_horas = db.Column(db.Float, nullable=True)
    cumplimiento_mtcd = db.Column(db.Float, nullable=True)  # %

    # Bloque RECUPERACIÓN (MTIR)
    requiere_recuperacion = db.Column(db.Boolean, default=False)
    descripcion_mtir = db.Column(db.Text, nullable=True)
    fecha_mtir = db.Column(db.DateTime, nullable=True)
    tiempo_mtir_horas = db.Column(db.Float, nullable=True)
    cumplimiento_mtir = db.Column(db.Float, nullable=True)  # %

    # Cumplimiento global
    cumplimiento_global = db.Column(db.Float, nullable=True)  # %

    # Análisis IA / manual por incidente
    analisis = db.Column(db.Text, nullable=True)

    creado_en = db.Column(db.DateTime, default=datetime.utcnow)


#========================
# Helper
#========================

# =============================
# Constantes globales INCIDENCIAS
# =============================

INCIDENTE_CLASIFICACIONES = ['Crítico', 'Alto', 'Medio', 'Bajo']

# ===========================
# Helpers de configuración de incidentes
# ===========================


def normalizar_texto(s):
    return s.strip().lower() if s else None

def get_config_incidentes_map():
    """
    Devuelve:
      clasif_nombres = ['Crítico', 'Alto', ...]
      tiempos_por_clas = {
        'crítico':  {'tmr': 4, 'mtcd': 1, 'mtir': 3},
        'alto':     {...},
        ...
      }
    """
    config = MetricConfigIncidentes.query.first()
    clasif_nombres = []
    tiempos_por_clas = {}

    # Si no hay configuración aún, devolvemos listas/diccionarios vacíos
    if not config:
        return clasif_nombres, tiempos_por_clas

    for fila in config.clasificaciones:
        nombre = (fila.clasificacion or "").strip()
        if not nombre:
            continue

        # Lista "bonita" para los combos/selects
        clasif_nombres.append(nombre)

        # Mapa normalizado para cálculos (keys en minúsculas)
        key = normalizar_texto(nombre)
        tiempos_por_clas[key] = {
            "tmr":  fila.tmr,
            "mtcd": fila.mtcd,
            "mtir": fila.mtir,
        }

    return clasif_nombres, tiempos_por_clas

# ===========================
# Vista métrica construida desde registro_incidentes
# ===========================

class IncidenteMetricaView:
    """
    Objeto ligero para que la plantilla de la matriz de métricas funcione
    igual que antes, pero tomando datos desde registro_incidentes.
    """
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def parse_dt_maybe(value: str):
    """
    Intenta parsear 'YYYY-MM-DD HH:MM' o 'YYYY-MM-DDTHH:MM'.
    Devuelve datetime o None si no se puede.
    """
    if not value:
        return None

    from datetime import datetime
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def construir_metrica_desde_incidente_row(row, tiempos_por_clas: dict) -> IncidenteMetricaView:
    """
    Recibe una fila de sqlite3.Row de la tabla registro_incidentes
    y la convierte en un IncidenteMetricaView con campos compatibles
    con la plantilla de la Matriz de Métricas.
    """

    # Campos básicos
    id_reg        = row["id"]
    fecha_alerta  = row["fecha_alerta"]
    desc_alerta   = row["descripcion_alerta"]
    clasif        = row["clasificacion_incidente"] or "Sin clasificación"

    se_req_cont   = (row["se_requiere_contencion"] or "No") == "Si"
    se_req_rec    = (row["se_requiere_recuperacion"] or "No") == "Si"

    fh_cont_raw   = row["fecha_hora_contencion"]
    fh_rec_raw    = row["fecha_hora_recuperacion"]

    dt_reg        = parse_dt_maybe(fecha_alerta)
    dt_cont       = parse_dt_maybe(fh_cont_raw)
    dt_rec        = parse_dt_maybe(fh_rec_raw)

    # ==========================
    # Cálculo de tiempos en horas
    # ==========================
    tiempo_mtcd_horas = None
    if se_req_cont and dt_reg and dt_cont:
        delta = dt_cont - dt_reg
        tiempo_mtcd_horas = max(0.0, delta.total_seconds() / 3600.0)

    # MTIR: depende de si hubo contención previa o no
    tiempo_mtir_horas = None
    if se_req_rec and dt_rec:
        if se_req_cont and dt_cont:
            base = dt_cont
        else:
            base = dt_reg
        if base:
            delta = dt_rec - base
            tiempo_mtir_horas = max(0.0, delta.total_seconds() / 3600.0)

    # ==========================
    # Buscar objetivos en la config (TMR, MTCD, MTIR)
    # ==========================
    key = normalizar_texto(clasif)
    cfg = tiempos_por_clas.get(key, {})
    tmr_obj  = cfg.get("tmr")   # Tiempo máximo total (TMR)
    mtcd_obj = cfg.get("mtcd")  # Tiempo respuesta MTCD
    mtir_obj = cfg.get("mtir")  # Tiempo máximo MTIR cuando hay MTCD

    # ==========================
    # Cumplimiento MTCD
    # ==========================
    cumplimiento_mtcd = None
    if se_req_cont and tiempo_mtcd_horas is not None and mtcd_obj is not None:
        if tiempo_mtcd_horas <= mtcd_obj:
            cumplimiento_mtcd = 100.0
        else:
            exceso = tiempo_mtcd_horas - mtcd_obj
            # % de cumplimiento aproximado (100% menos el porcentaje de exceso)
            cumplimiento_mtcd = max(0.0, 100.0 - (exceso / mtcd_obj) * 100.0)

    # ==========================
    # Cumplimiento MTIR
    # Lógica:
    #  - Si hubo MTCD: se compara contra MTIR
    #  - Si NO hubo MTCD: se compara contra TMR
    # ==========================
    cumplimiento_mtir = None
    if se_req_rec and tiempo_mtir_horas is not None:
        if se_req_cont and mtir_obj is not None:
            objetivo = mtir_obj
        else:
            objetivo = tmr_obj

        if objetivo is not None:
            if tiempo_mtir_horas <= objetivo:
                cumplimiento_mtir = 100.0
            else:
                exceso = tiempo_mtir_horas - objetivo
                cumplimiento_mtir = max(0.0, 100.0 - (exceso / objetivo) * 100.0)

    # ==========================
    # Cumplimiento global (promedio de los que existan)
    # ==========================
    valores = []
    if cumplimiento_mtcd is not None:
        valores.append(cumplimiento_mtcd)
    if cumplimiento_mtir is not None:
        valores.append(cumplimiento_mtir)

    cumplimiento_global = None
    if valores:
        cumplimiento_global = sum(valores) / len(valores)

    # De momento no generamos análisis automático (puedes luego
    # llamar a analizar_metrica_incidente_ia si quieres)
    analisis = None

    return IncidenteMetricaView(
        id=id_reg,                          # ✅ id BD (registro_incidentes.id) -> entero
        id_incidente=row["id_incidente"],   # ✅ id de negocio (INC-2025-001)
        fecha_registro=dt_reg,              # ✅ datetime desde fecha_alerta
        descripcion_incidente=desc_alerta or "",  # ✅ NUNCA None
        cargo_responsable=row["cargo_responsable"],

        clasificacion_incidente=clasif,     # si tu UI lo usa
        clasificacion=clasif,               # ✅ para guardar en MetricaIncidente

        requiere_contencion=se_req_cont,
        tiempo_mtcd_horas=tiempo_mtcd_horas,
        cumplimiento_mtcd=cumplimiento_mtcd,

        requiere_recuperacion=se_req_rec,
        tiempo_mtir_horas=tiempo_mtir_horas,
        cumplimiento_mtir=cumplimiento_mtir,

        cumplimiento_global=cumplimiento_global,
        analisis=None,
    )

    config = MetricConfigIncidentes.query.first()
    clasif_nombres = []
    tiempos_por_clas = {}

    if not config:
        return clasif_nombres, tiempos_por_clas

    for fila in config.clasificaciones:
        nombre = (fila.clasificacion or "").strip()
        if not nombre:
            continue
        clasif_nombres.append(nombre)

        key = normalizar_texto(nombre)
        tiempos_por_clas[key] = {
            "tmr": fila.tmr,
            "mtcd": fila.mtcd,
            "mtir": fila.mtir,
        }

    return clasif_nombres, tiempos_por_clas

def calcular_icv_vulnerabilidades(config, detalles, fecha_inicio, fecha_fin):
    """
    Calcula el Índice de Cumplimiento en Vulnerabilidades (ICV) para el periodo.
    Devuelve: (icv_global, filas_detalle)
    filas_detalle = [
      {
        "clasificacion": ...,
        "aceptada": ...,
        "real": ...,
        "cumplimiento": ...,
        "peso": ...,
        "aporte": ...
      },
      ...
    ]
    """
    if not config or not detalles:
        return None, []

    icv_global = 0.0
    filas = []

    for det in detalles:
        aceptada = det.cantidad_aceptada or 0
        peso = det.peso_pct or 0.0

        # Conteo de vulnerabilidades ACTIVAS en el periodo, por clasificación
        real = (
            Vulnerabilidad.query
            .filter(
                Vulnerabilidad.clasificacion == det.clasificacion,
                Vulnerabilidad.estado == "Activa",
                Vulnerabilidad.fecha_registro >= fecha_inicio,
                Vulnerabilidad.fecha_registro < fecha_fin,
            )
            .count()
        )

        # Cálculo de cumplimiento por clasificación
        if real == 0:
            cumplimiento = 100.0
        elif aceptada <= 0:
            # No se aceptan vulnerabilidades de esta clase
            cumplimiento = 0.0 if real > 0 else 100.0
        elif real <= aceptada:
            cumplimiento = 100.0
        else:
            cumplimiento = (aceptada / real) * 100.0

        cumplimiento = round(cumplimiento, 2)

        # Aporte ponderado al índice global
        aporte = round(cumplimiento * (peso / 100.0), 2)
        icv_global += aporte

        filas.append({
            "clasificacion": det.clasificacion,
            "aceptada": aceptada,
            "real": real,
            "cumplimiento": cumplimiento,
            "peso": peso,
            "aporte": aporte,
        })

    icv_global = round(icv_global, 2)
    return icv_global, filas

def normalizar_clasificacion(texto):
    if not texto:
        return None
    return texto.strip().lower()

def analizar_metricas_vuln_ia(datos_metricas: dict) -> str:
    prompt = f"""
Eres un analista experto en gestión de vulnerabilidades y SLAs.

Con base en estos datos (JSON), redacta un análisis ejecutivo en español.
- No inventes cifras.
- Incluye hallazgos, riesgos, y 5 acciones concretas priorizadas.
- Si no hay datos suficientes, dilo claramente.

DATOS (JSON):
{json.dumps(datos_metricas, ensure_ascii=False, indent=2)}
"""
    return chat_ai(prompt, model="openai/gpt-4o-mini").strip()


def analizar_vulnerabilidad_por_codigo_ia(vuln, sla_dias, dias_abierta):
    prompt = f"""
Eres un analista senior de ciberseguridad.
Debes redactar un análisis ejecutivo y accionable de una vulnerabilidad ABIERTA fuera de SLA.

Datos:
- Código: {vuln.codigo}
- Clasificación: {vuln.clasificacion or 'Sin clasificar'}
- Responsable: {vuln.responsable or 'Sin responsable'}
- Fecha identificación: {vuln.fecha_identificacion}
- Días abierta: {dias_abierta}
- SLA (días): {sla_dias}

Instrucciones:
- Escribe en español.
- Máximo 10-12 líneas.
- Incluye: impacto probable, riesgo de negocio, urgencia, y 3 acciones concretas verificables.
- NO inventes datos técnicos si no están.
- Si faltan datos, dilo y sugiere qué evidencia pedir.
"""

    return (chat_ai(prompt, model="openai/gpt-4o-mini") or "").strip()


def analizar_vulnerabilidad_cerrada_fuera_sla_ia(vuln, sla_dias, dias_cierre, cierre_eff):
    prompt = f"""
Eres un analista senior de ciberseguridad.
Debes redactar un análisis post-mortem de una vulnerabilidad CERRADA fuera de SLA.

Datos:
- Código: {vuln.codigo}
- Clasificación: {vuln.clasificacion or 'Sin clasificar'}
- Responsable: {vuln.responsable or 'Sin responsable'}
- Fecha identificación: {vuln.fecha_identificacion}
- Fecha cierre: {cierre_eff}
- Días cierre: {dias_cierre}
- SLA (días): {sla_dias}

Instrucciones:
- Escribe en español.
- Máximo 10-12 líneas.
- Explica el incumplimiento de SLA en términos de proceso (sin inventar causas).
- Propón 3 mejoras concretas del proceso (ej.: triage, dueños, ventanas, seguimiento).
- NO inventes datos.
"""

    return (chat_ai(prompt, model="openai/gpt-4o-mini") or "").strip()


def analizar_vulnerabilidad_cerrada_fuera_sla_ia(vuln, sla_dias, dias_cierre, cierre_eff) -> str:
    prompt = f"""
Eres un auditor de seguridad.

Analiza una vulnerabilidad CERRADA fuera de SLA y redacta:
1) Resumen del incumplimiento
2) Posibles causas (solo si se infieren razonablemente)
3) Lecciones aprendidas
4) Acciones preventivas para evitar repetición (mínimo 5)
5) Indicadores/controles recomendados

NO inventes fechas ni información.

Datos:
- Código: {vuln.codigo}
- Estado: {vuln.estado}
- Clasificación: {vuln.clasificacion}
- Responsable: {vuln.responsable}
- Fecha identificación: {vuln.fecha_identificacion}
- Fecha cierre efectiva: {cierre_eff}
- Días de cierre: {dias_cierre}
- SLA días: {sla_dias}
"""
    return chat_ai(prompt, model="openai/gpt-4o-mini").strip()


def cargar_incidente_por_id(incidente_id: int):
    init_incidentes_db()
    conn = get_incidentes_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM registro_incidentes WHERE id = ?", (incidente_id,))
    row = c.fetchone()
    conn.close()
    return row

def listar_incidentes_metricas():
    init_incidentes_db()
    conn = get_incidentes_db_connection()
    c = conn.cursor()
    c.execute("""
        SELECT *
        FROM registro_incidentes
        ORDER BY id DESC
    """)
    rows = c.fetchall()
    conn.close()
    return rows

def listar_incidentes_metricas_filtrados(
    nombre_alerta: str = "",
    clasificacion_incidente: str = "",
    prioridad: str = "",
    estado: str = ""
):
    init_incidentes_db()
    conn = get_incidentes_db_connection()
    c = conn.cursor()

    query = """
        SELECT *
        FROM registro_incidentes
        WHERE 1=1
    """
    params = []

    if (nombre_alerta or "").strip():
        query += " AND nombre_alerta LIKE ?"
        params.append(f"%{nombre_alerta.strip()}%")

    if (clasificacion_incidente or "").strip():
        query += " AND clasificacion_incidente = ?"
        params.append(clasificacion_incidente.strip())

    if (prioridad or "").strip():
        query += " AND prioridad = ?"
        params.append(prioridad.strip())

    if (estado or "").strip():
        query += " AND estado = ?"
        params.append(estado.strip())

    query += " ORDER BY id DESC"

    c.execute(query, tuple(params))
    rows = c.fetchall()
    conn.close()
    return rows




def analizar_metrica_incidente_ia(metrica: "MetricaIncidente", eta_objetivo: float | None = None) -> str:
    """
    Genera un análisis breve del resultado de la métrica de un incidente específico,
    comparando, cuando exista, contra el ETA u objetivo global configurado.
    """
    clasif = metrica.clasificacion or "Sin clasificación"
    req_cont = "Sí" if metrica.requiere_contencion else "No"
    req_rec = "Sí" if metrica.requiere_recuperacion else "No"

    objetivo_txt = f"{eta_objetivo:.2f} %" if eta_objetivo is not None else "no definido"

    prompt = f"""
Eres un analista de respuesta a incidentes de seguridad de la información.

Analiza la siguiente métrica de un incidente individual:

- ID del incidente: {metrica.incidente_id}
- Clasificación del incidente: {clasif}
- Fecha y hora de registro del incidente: {metrica.fecha_registro}
- Se requirió contención (MTDC): {req_cont}
- Tiempo ejecutado en la eficacia de la MTDC (horas): {metrica.tiempo_mtcd_horas}
- Cumplimiento meta final de la CONTENCIÓN (%): {metrica.cumplimiento_mtcd}
- Se requirió recuperación (MTIR): {req_rec}
- Tiempo ejecutado en la eficacia de la MTIR (horas): {metrica.tiempo_mtir_horas}
- Cumplimiento meta final de la RECUPERACIÓN (%): {metrica.cumplimiento_mtir}
- Cumplimiento global de la métrica (%): {metrica.cumplimiento_global}
- Objetivo global ETA u objetivo mensual de respuesta y solución de incidentes (%): {objetivo_txt}

Instrucciones:
1. Compara explícitamente el cumplimiento global de la métrica frente al objetivo ETA cuando esté definido.
2. Describe si el incidente se gestionó por encima, dentro o por debajo de lo esperado.
3. Comenta brevemente el rol de la contención y la recuperación en el resultado global.
4. Incluye 1–2 recomendaciones concretas para mejorar incidentes similares en el futuro.

Responde en ESPAÑOL, en un máximo de 8 líneas, en texto corrido, sin viñetas ni títulos.
    """.strip()

    try:
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )

        # 👇 AQUÍ ESTÁ EL PUNTO CLAVE:
        # NADA de ["content"], solo .message.content
        texto = resp.choices[0].message.content if resp.choices else ""
        if not texto:
            texto = "No se pudo generar automáticamente el análisis de la métrica. Por favor, complétalo manualmente."
        return texto.strip()

    except Exception as e:
        print("Error IA en analizar_metrica_incidente_ia:", e)
        return "No se pudo generar automáticamente el análisis de la métrica. Por favor, complétalo manualmente."

def analizar_vulnerabilidad_por_codigo_ia(vuln, sla_dias: int | None, dias_abierta: int) -> str:
    """
    Genera análisis por código de vulnerabilidad (vencida).
    vuln: objeto VulnerabilidadRegistro
    """
    cls = vuln.clasificacion or "Sin clasificar"
    resp = vuln.responsable or "No asignado"
    fecha_id = vuln.fecha_identificacion.strftime("%Y-%m-%d") if vuln.fecha_identificacion else "No definida"
    sla_txt = f"{sla_dias} días" if sla_dias is not None else "No definido"

    prompt = f"""
Eres un analista de gestión de vulnerabilidades.

Genera un análisis ejecutivo para una vulnerabilidad vencida (fuera de SLA):

Código: {vuln.codigo}
Clasificación: {cls}
Responsable: {resp}
Fecha identificación: {fecha_id}
Días abierta: {dias_abierta}
SLA configurado: {sla_txt}

Instrucciones:
1) Explica por qué está fuera de SLA y el riesgo operativo.
2) Indica 2–3 acciones concretas (plan de acción) para remediarla o mitigarla.
3) Tono profesional. Máximo 8–10 líneas. Sin viñetas ni títulos.
""".strip()

    resp_ai = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    texto = resp_ai.choices[0].message.content or ""
    return texto.strip()


#=================================
# Configuración de Riesgos
#=================================

@app.route('/metricas/configuracion/riesgos', methods=["GET", "POST"])
@login_required
def config_param_riesgos():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede configurar parámetros.", "danger")
        return redirect(url_for('menu'))

    if user.role != 'admin' and not verificar_permiso(user, "Métricas"):
        flash("No tiene permiso para configurar parámetros.", "danger")
        return redirect(url_for('menu'))

    # Cargar registro único (1 fila)
    cfg = MetricConfigRiesgos.query.first()
    if not cfg:
        cfg = MetricConfigRiesgos(
            apetito_residual_definido="",
            tendencia_tiempo="mensual"
        )
        db.session.add(cfg)
        db.session.commit()

    opciones = [
        ("mensual", "Mensual"),
        ("trimestral", "Trimestral"),
        ("cuatrimestral", "Cuatrimestral"),
        ("semestral", "Semestral"),
        ("anual", "Anual"),
    ]

    if request.method == "POST":
        apetito = (request.form.get("apetito_residual_definido") or "").strip()
        if not apetito or len(apetito) > 255:
            flash("El apetito de riesgo residual debe ser alfanumérico y máximo 255 caracteres.", "danger")
            return redirect(url_for("config_param_riesgos"))

        cfg.apetito_residual_definido = apetito
        tendencia = (request.form.get("tendencia_tiempo") or "mensual").strip().lower()

        permitidos = {k for k, _ in opciones}
        if tendencia not in permitidos:
            tendencia = "mensual"

        cfg.apetito_residual_definido = apetito
        cfg.tendencia_tiempo = tendencia
        db.session.commit()

        flash("Parámetros de riesgos guardados correctamente.", "success")
        return redirect(url_for("config_param_riesgos"))

    content = render_template_string("""
    <div class="riskcfg-shell">

      <!-- CABECERA -->
      <div class="riskcfg-header-card">
        <div class="riskcfg-header-overlay">
          <div class="riskcfg-header-text">
            <h3 class="riskcfg-title m-0">Parámetros de Riesgos</h3>
            <div class="riskcfg-subtitle">
              Configura el apetito de riesgo residual definido por la organización
              y la periodicidad de análisis de la tendencia en el tiempo.
            </div>
          </div>
        </div>
      </div>

      <!-- BOTÓN VOLVER -->
      <div class="riskcfg-header-actions">

      </div>

      <!-- TARJETA -->
      <div class="riskcfg-card p-4">

        <div class="riskcfg-section-title">
          Configuración de parámetros
        </div>

        <form method="POST">

          <div class="mb-3">
            <label class="form-label fw-semibold">
              Apetito de riesgo residual (Definido)
            </label>

            <input
              type="text"
              name="apetito_residual_definido"
              class="form-control"
              maxlength="255"
              value="{{ cfg.apetito_residual_definido }}"
              placeholder="Ej: Bajo | Moderado | Alto | Nivel 3 | Residual <= 6"
              required
            >

            <div class="form-text">
              Valor alfanumérico definido por la organización para aceptación del riesgo residual.
            </div>
          </div>

          <div class="mb-3">
            <label class="form-label fw-semibold">
              Tendencia en el tiempo
            </label>

            <select name="tendencia_tiempo" class="form-select">
              {% for val, label in opciones %}
                <option value="{{ val }}" {% if (cfg.tendencia_tiempo or 'mensual') == val %}selected{% endif %}>
                  {{ label }}
                </option>
              {% endfor %}
            </select>

            <div class="form-text">
              Define la periodicidad con la que se mostrará y analizará la tendencia del riesgo.
            </div>
          </div>

          <div class="text-center mt-4">
            <button type="submit" class="btn btn-primary rounded-pill px-4 fw-semibold">
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

      .riskcfg-shell {
        width: 96%;
        max-width: 1200px;
        margin: 26px auto 24px auto;
        overflow: hidden;
      }

      .riskcfg-header-card {
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

      .riskcfg-header-card::before {
        content: "";
        position: absolute;
        inset: 0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .riskcfg-header-overlay {
        width: 100%;
        display: flex;
        align-items: center;
        justify-content: flex-start;
        text-align: left;
        position: relative;
        z-index: 1;
        min-width: 0;
      }

      .riskcfg-header-overlay::before {
        content: "📉";
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

      .riskcfg-header-text {
        max-width: 1000px;
        min-width: 0;
      }

      .riskcfg-header-text::before {
        content: "SGSI · Configuración de Riesgos";
        display: inline-block;
        background: rgba(255,255,255,.18);
        border-radius: 999px;
        padding: 3px 10px;
        font-size: .65rem;
        font-weight: 800;
        margin-bottom: 4px;
        color: #ffffff;
      }

      .riskcfg-title {
        color: #ffffff !important;
        font-weight: 950;
        font-size: 1.32rem;
        line-height: 1.1;
        margin: 0 !important;
        text-shadow: 0 4px 14px rgba(0,0,0,.45);
        overflow-wrap: break-word;
      }

      .riskcfg-subtitle {
        color: rgba(255,255,255,.95);
        font-size: .78rem;
        line-height: 1.25;
        margin-top: 3px;
        overflow-wrap: break-word;
      }

      .riskcfg-header-actions {
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

      .riskcfg-btn-main {
        background: #ffffff;
        color: #0f172a;
        border: 1px solid #cfd8e3;
      }

      .riskcfg-btn-main:hover {
        background: #edf5ff;
        color: #0b65d8;
      }

      .riskcfg-card {
        background: rgba(255,255,255,.96) !important;
        border-radius: 18px;
        backdrop-filter: blur(8px);
        box-shadow: 0 12px 24px rgba(15,23,42,.18);
        border: 1px solid rgba(219,230,244,.9);
        overflow: hidden;
        width: 100%;
        max-width: 100%;
      }

      .riskcfg-card-body,
      .riskcfg-card .card-body {
        padding: 22px;
      }

      .riskcfg-section-title {
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

      h3 {
        color: #ffffff;
        margin: 0;
      }

      @media (max-width: 992px) {
        .riskcfg-shell {
          width: 98%;
          margin: 8px auto 22px auto;
        }

        .riskcfg-title {
          font-size: 1.20rem;
        }

        .riskcfg-subtitle {
          font-size: .76rem;
        }

        .riskcfg-card-body,
        .riskcfg-card .card-body {
          padding: 16px;
        }
      }

      @media (max-width: 768px) {
        .riskcfg-header-overlay {
          flex-direction: column;
          text-align: center;
          gap: 10px;
        }

        .riskcfg-header-overlay::before {
          margin: 0;
        }

        .riskcfg-title,
        .riskcfg-subtitle {
          text-align: center;
        }

        .riskcfg-header-actions .btn {
          width: 100%;
        }
      }
    </style>
    """, cfg=cfg, opciones=opciones)

    return render_template_string(BASE, content=content)

#=================================
# Configuración de Incidentes
#=================================

@app.route('/metricas/configuracion/incidentes', methods=['GET', 'POST'])
@login_required
def config_param_incidentes():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede agregar registros.", "danger")
        return redirect(url_for('menu'))

    if user.role != 'admin' and not verificar_permiso(user, "Métricas"):
        flash("No tiene permiso para configurar incidentes.", "danger")
        return redirect(url_for('menu'))
    # 🔹 Siempre trabajaremos con UNA sola configuración global
    config = MetricConfigIncidentes.query.first()

    if request.method == 'POST':
        eta_objetivo = request.form.get('eta_objetivo')
        clasificaciones = request.form.getlist('clasificacion[]')
        tmr_list = request.form.getlist('tmr[]')
        mtcd_list = request.form.getlist('mtcd[]')
        mtir_list = request.form.getlist('mtir[]')

        # Si no existe config, la creamos
        if not config:
            config = MetricConfigIncidentes()
            db.session.add(config)

        # Guardar ETA objetivo
        try:
            config.eta_objetivo = float(eta_objetivo) if eta_objetivo else None
        except ValueError:
            config.eta_objetivo = None

        config.fecha_ultima_actualizacion = datetime.utcnow()

        # 🔹 Limpiamos clasificaciones anteriores y guardamos las nuevas
        config.clasificaciones.clear()

        for clasif, tmr, mtcd, mtir in zip(clasificaciones, tmr_list, mtcd_list, mtir_list):
            # Ignorar filas totalmente vacías
            if not (clasif or tmr or mtcd or mtir):
                continue

            fila = MetricConfigIncidentesClasificacion(
                config=config,
                clasificacion=(clasif or "").strip() or "Sin nombre",
            )

            # Convertimos a float si viene algo
            fila.tmr = float(tmr) if (tmr or "").strip() else None
            fila.mtcd = float(mtcd) if (mtcd or "").strip() else None
            fila.mtir = float(mtir) if (mtir or "").strip() else None

            db.session.add(fila)

        db.session.commit()
        flash("Parámetros de incidentes guardados correctamente.", "success")
        return redirect(url_for('config_param_incidentes'))

    # 🔹 GET → cargar valores guardados (si existen)
    eta_valor = config.eta_objetivo if config else None
    clasificaciones_guardadas = config.clasificaciones if config else []

    content = render_template_string("""
    <div class="incparam-shell">

      <!-- CABECERA -->
      <div class="incparam-header-card">
        <div class="incparam-header-overlay">
          <div class="incparam-header-text">
            <h3 class="incparam-title m-0">Parámetros de Incidentes</h3>
            <div class="incparam-subtitle">
              Configura el objetivo mensual (ETA) y los tiempos máximos de respuesta
              y recuperación de incidentes según su clasificación.
            </div>
          </div>
        </div>
      </div>

      <!-- BOTÓN VOLVER -->
      <div class="incparam-header-actions">
        
      </div>

      <!-- TARJETA PRINCIPAL -->
      <div class="incparam-card p-4">

        <div class="incparam-section-title">
          Configuración de tiempos y objetivos
        </div>

        <form method="POST">

          <!-- ETA -->
          <div class="mb-3">
            <label for="eta_objetivo" class="form-label fw-semibold">
              ETA u objetivo mensual de respuesta y solución de incidentes (%)
            </label>

            <div class="input-group">
              <input type="number"
                     step="0.01"
                     min="0"
                     max="100"
                     class="form-control"
                     id="eta_objetivo"
                     name="eta_objetivo"
                     value="{{ eta_valor if eta_valor is not none else '' }}"
                     placeholder="Ej: 95">
              <span class="input-group-text">%</span>
            </div>

            <div class="form-text">
              Porcentaje de incidentes que se espera responder y solucionar dentro de los tiempos definidos.
            </div>
          </div>

          <hr>

          <!-- TABLA -->
          <h5 class="mb-3 fw-bold">
            Tiempo máximo de recuperación de incidentes en horas según clasificación
          </h5>

          <div class="table-responsive incparam-table-wrap">

            <table class="table table-sm align-middle mb-0" id="tabla-clasificaciones">

              <thead class="incparam-table-head">
                <tr>
                  <th style="min-width:140px;">Clasificación</th>
                  <th style="min-width:160px;">Tiempo máximo de respuesta (TMR)</th>
                  <th style="min-width:200px;">Tiempo MTCD dentro del TMR</th>
                  <th style="min-width:220px;">
                    Tiempo máximo de recuperación (MTIR)
                    <br>
                    <small class="text-muted">
                    Si no es requerido MTCD el tiempo será el definido en el TMR.
                    </small>
                  </th>
                  <th class="text-center" style="width:80px;">Acciones</th>
                </tr>
              </thead>

              <tbody id="body-clasificaciones">

              {% if clasificaciones_guardadas %}

                {% for fila in clasificaciones_guardadas %}
                <tr>

                  <td>
                    <select name="clasificacion[]" class="form-select">
                      <option value="">-- Seleccione --</option>
                      {% for op in clasif_choices %}
                        <option value="{{ op }}"
                          {% if fila.clasificacion == op %}selected{% endif %}>
                          {{ op }}
                        </option>
                      {% endfor %}
                    </select>
                  </td>

                  <td>
                    <input type="number"
                           step="0.01"
                           min="0"
                           name="tmr[]"
                           class="form-control"
                           value="{{ fila.tmr if fila.tmr is not none else '' }}">
                  </td>

                  <td>
                    <input type="number"
                           step="0.01"
                           min="0"
                           name="mtcd[]"
                           class="form-control"
                           value="{{ fila.mtcd if fila.mtcd is not none else '' }}">
                  </td>

                  <td>
                    <input type="number"
                           step="0.01"
                           min="0"
                           name="mtir[]"
                           class="form-control"
                           value="{{ fila.mtir if fila.mtir is not none else '' }}">
                  </td>

                  <td class="text-center">
                    <button type="button"
                            class="btn btn-outline-danger btn-sm grac-trash-button"
                            title="Eliminar clasificación" aria-label="Eliminar clasificación"
                            onclick="eliminarFila(this)">
                      <i class="bi bi-trash3-fill grac-action-icon-white" aria-hidden="true"></i><span class="visually-hidden">Eliminar</span>
                    </button>
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
                        <option value="{{ opcion }}"
                          {% if opcion == op %}selected{% endif %}>
                          {{ opcion }}
                        </option>
                      {% endfor %}
                    </select>
                  </td>

                  <td>
                    <input type="number" step="0.01" min="0"
                           name="tmr[]" class="form-control"
                           placeholder="Horas">
                  </td>

                  <td>
                    <input type="number" step="0.01" min="0"
                           name="mtcd[]" class="form-control"
                           placeholder="Horas">
                  </td>

                  <td>
                    <input type="number" step="0.01" min="0"
                           name="mtir[]" class="form-control"
                           placeholder="Horas">
                  </td>

                  <td class="text-center">
                    <button type="button"
                            class="btn btn-outline-danger btn-sm grac-trash-button"
                            title="Eliminar clasificación" aria-label="Eliminar clasificación"
                            onclick="eliminarFila(this)">
                      <i class="bi bi-trash3-fill grac-action-icon-white" aria-hidden="true"></i><span class="visually-hidden">Eliminar</span>
                    </button>
                  </td>

                </tr>
                {% endfor %}

              {% endif %}

              </tbody>

            </table>
          </div>

          <button type="button"
                  class="btn btn-outline-primary btn-sm mt-3"
                  onclick="agregarFila()">
            ➕ Agregar clasificación
          </button>

          <div class="d-flex justify-content-end mt-4">
            <button type="submit"
                    class="btn btn-success rounded-pill px-4">
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

      .incparam-shell {
        width: 96%;
        max-width: 1200px;
        margin: 26px auto 24px auto;
        overflow: hidden;
      }

      .incparam-header-card {
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

      .incparam-header-card::before {
        content: "";
        position: absolute;
        inset: 0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .incparam-header-overlay {
        width: 100%;
        display: flex;
        align-items: center;
        justify-content: flex-start;
        text-align: left;
        position: relative;
        z-index: 1;
        min-width: 0;
      }

      .incparam-header-overlay::before {
        content: "🚨";
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

      .incparam-header-text {
        max-width: 1000px;
        min-width: 0;
      }

      .incparam-header-text::before {
        content: "SGSI · Parámetros de Incidentes";
        display: inline-block;
        background: rgba(255,255,255,.18);
        border-radius: 999px;
        padding: 3px 10px;
        font-size: .65rem;
        font-weight: 800;
        margin-bottom: 4px;
        color: #ffffff;
      }

      .incparam-title {
        color: #ffffff !important;
        font-weight: 950;
        font-size: 1.32rem;
        line-height: 1.1;
        margin: 0 !important;
        text-shadow: 0 4px 14px rgba(0,0,0,.45);
        overflow-wrap: break-word;
      }

      .incparam-subtitle {
        color: rgba(255,255,255,.95);
        font-size: .78rem;
        line-height: 1.25;
        margin-top: 3px;
        overflow-wrap: break-word;
      }

      .incparam-header-actions {
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

      .incparam-btn-main {
        background: #ffffff;
        color: #0f172a;
        border: 1px solid #cfd8e3;
      }

      .incparam-btn-main:hover {
        background: #edf5ff;
        color: #0b65d8;
      }

      .incparam-card {
        background: rgba(255,255,255,.96) !important;
        border-radius: 18px;
        backdrop-filter: blur(8px);
        box-shadow: 0 12px 24px rgba(15,23,42,.18);
        border: 1px solid rgba(219,230,244,.9);
        overflow: hidden;
        width: 100%;
        max-width: 100%;
      }

      .incparam-card .card-body,
      .incparam-card-body {
        padding: 22px;
      }

      .incparam-section-title {
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

      .incparam-table-wrap {
        border: 1px solid #e2ebf5;
        border-radius: 14px;
        background: #ffffff;
        overflow-x: auto;
        overflow-y: hidden;
        box-shadow: inset 0 1px 0 rgba(255,255,255,.35);
        width: 100%;
        max-width: 100%;
      }

      .incparam-table-wrap .table {
        margin-bottom: 0;
        min-width: 780px;
      }

      .incparam-table-head th,
      .incparam-table-wrap thead th {
        background: #eef5ff !important;
        font-weight: 900;
        color: #0b4a8f;
        border-bottom: 1px solid #d7dee7 !important;
        vertical-align: middle;
        white-space: nowrap;
        font-size: .82rem;
      }

      .incparam-table-wrap tbody td {
        vertical-align: middle;
        font-size: .85rem;
        color: #334155;
      }

      .incparam-table-wrap tbody tr:last-child td {
        border-bottom: none;
      }

      .incparam-table-wrap tbody tr:hover {
        background: #f8fbff;
      }

      .incparam-btn-add {
        border-radius: 10px;
        font-weight: 900;
        box-shadow: 0 4px 10px rgba(0,0,0,.08);
      }

      .incparam-btn-del {
        border-radius: 10px;
        font-weight: 900;
      }

      h3 {
        color: #ffffff;
        margin: 0;
      }

      @media (max-width: 992px) {
        .incparam-shell {
          width: 98%;
          margin: 8px auto 22px auto;
        }

        .incparam-title {
          font-size: 1.20rem;
        }

        .incparam-subtitle {
          font-size: .76rem;
        }

        .incparam-card .card-body,
        .incparam-card-body {
          padding: 16px;
        }
      }

      @media (max-width: 768px) {
        .incparam-header-overlay {
          flex-direction: column;
          text-align: center;
          gap: 10px;
        }

        .incparam-header-overlay::before {
          margin: 0;
        }

        .incparam-title,
        .incparam-subtitle {
          text-align: center;
        }

        .incparam-header-actions .btn {
          width: 100%;
        }
      }
    </style>
    """,
    eta_valor=eta_valor,
    clasificaciones_guardadas=clasificaciones_guardadas,
    clasif_choices=INCIDENTE_CLASIFICACIONES)

    return render_template_string(BASE, content=content)

#==================================
# Configuración de Vulnerabilidades
#==================================

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
                                class="btn btn-outline-danger btn-sm rounded-pill px-3 grac-trash-button"
                                title="Eliminar clasificación" aria-label="Eliminar clasificación"
                                onclick="eliminarFilaVuln(this)"><i class="bi bi-trash3-fill grac-action-icon-white" aria-hidden="true"></i><span class="visually-hidden">Eliminar</span></button>
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
                                class="btn btn-outline-danger btn-sm rounded-pill px-3 grac-trash-button"
                                title="Eliminar clasificación" aria-label="Eliminar clasificación"
                                onclick="eliminarFilaVuln(this)"><i class="bi bi-trash3-fill grac-action-icon-white" aria-hidden="true"></i><span class="visually-hidden">Eliminar</span></button>
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

