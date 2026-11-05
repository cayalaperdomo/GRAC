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
@app.route('/partes_interesadas/detalle/<int:id>')
@login_required
def parte_interesada_detalle(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Partes Interesadas"):
            flash("No tiene permiso para ver el detalle del registro.", "danger")
            return redirect(url_for('partes_interesadas_matriz'))
        read_only = False

    it = ParteInteresada.query.get_or_404(id)

    html = """
    <div class="pid-shell">

      <div class="pid-header-card">
        <div class="pid-header-overlay">
          <div class="pid-header-text">
            <h3 class="pid-title m-0">Detalle de Parte Interesada</h3>
            <div class="pid-subtitle">
              Consulta completa del registro en modo solo lectura
            </div>
          </div>
        </div>
      </div>

      <div class="pid-header-actions">
        <a href="{{ url_for('partes_interesadas_matriz') }}"
           class="btn rounded-pill px-4 fw-bold pid-back-btn"
           onclick="showLoader()">
          ⬅ Volver a la Matriz
        </a>

        {% if not read_only %}
          <a href="{{ url_for('parte_interesada_edit', id=it.id) }}"
             class="btn btn-warning rounded-pill px-4 fw-bold"
             onclick="showLoader()">
            Editar registro
          </a>
        {% endif %}
      </div>

      <div class="pid-card">
        <div class="pid-card-body">

          <div class="pid-section">
            <div class="pid-section-title">Información principal</div>
            <div class="row g-3">
              <div class="col-md-8">
                <div class="pid-field">
                  <div class="pid-label">Parte Interesada</div>
                  <div class="pid-value pid-value-lg">{{ it.parte_interesada or '—' }}</div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="pid-field">
                  <div class="pid-label">Fecha de Revisión</div>
                  <div class="pid-value">{{ format_fecha_partes(it.fecha_revision) }}</div>
                </div>
              </div>
            </div>
          </div>

          <div class="pid-section">
            <div class="pid-section-title">Análisis del registro</div>
            <div class="row g-3">
              <div class="col-md-12">
                <div class="pid-field">
                  <div class="pid-label">Necesidades / Expectativas</div>
                  <div class="pid-value">{{ it.necesidades_expectativas or '—' }}</div>
                </div>
              </div>

              <div class="col-md-12">
                <div class="pid-field">
                  <div class="pid-label">Requisitos Aplicables</div>
                  <div class="pid-value">{{ it.requisitos_aplicables or '—' }}</div>
                </div>
              </div>
            </div>
          </div>

          <div class="pid-section">
            <div class="pid-section-title">Evidencias</div>
            {% if it.evidencias %}
              <div class="pid-ev-grid">
                {% for ev in it.evidencias %}
                  <div class="pid-ev-card">
                    <div class="pid-ev-left">
                      <div class="pid-ev-icon">PDF</div>
                      <div class="pid-ev-meta">
                        <a href="{{ url_for('partes_evidencia_view', evi_id=ev.id, next='partes_interesadas_matriz') }}"
                           class="pid-ev-name">
                          {{ ev.original_name }}
                        </a>
                        <div class="pid-ev-size">
                          {{ ((ev.size or 0) / 1024)|round(1) }} KB
                        </div>
                      </div>
                    </div>
                    <div class="pid-ev-actions">
                      <a href="{{ url_for('partes_evidencia_view', evi_id=ev.id, next='partes_interesadas_matriz') }}"
                         class="btn btn-outline-primary btn-sm rounded-pill px-3">
                        Ver PDF
                      </a>
                    </div>
                  </div>
                {% endfor %}
              </div>
            {% else %}
              <div class="pid-empty-box">
                No hay evidencias cargadas para este registro.
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

      .pid-shell{
        width:96%;
        max-width:1250px;
        margin:10px auto 24px auto;
      }

      .pid-header-card{
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

      .pid-header-card::before{
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

      .pid-header-overlay{
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

      .pid-header-overlay::before{
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

      .pid-header-text{
        max-width:1100px;
        position:relative;
        z-index:1;
      }

      .pid-header-text::before{
        content:"SGSI · Detalle de Parte Interesada";
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

      .pid-title{
        color:#fff !important;
        font-weight:950;
        font-size:1.36rem;
        line-height:1.08;
        text-shadow:0 3px 10px rgba(0,0,0,.32);
        margin:0 !important;
      }

      .pid-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
        text-shadow:none;
      }

      .pid-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px 0;
      }

      .pid-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .pid-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .pid-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .pid-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        overflow:hidden;
        border:1px solid rgba(219,230,244,.9);
      }

      .pid-card-body{
        padding:16px 18px;
      }

      .pid-section{
        margin-bottom:14px;
        background:#ffffff;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:8px 7px;
        box-shadow:0 8px 18px rgba(15,23,42,.08);
      }

      .pid-section:last-child{
        margin-bottom:0;
      }

      .pid-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:0 0 12px 0;
      }

      .pid-field{
        background:linear-gradient(180deg,#f8fbff 0%,#ffffff 100%);
        border:1px solid #dbe6f4;
        border-radius:14px;
        padding:12px;
        min-height:100%;
      }

      .pid-label{
        font-size:.70rem;
        font-weight:900;
        text-transform:uppercase;
        letter-spacing:.35px;
        color:#0b4a8f;
        margin-bottom:6px;
      }

      .pid-value{
        color:#101827;
        font-size:.82rem;
        line-height:1.38;
        white-space:pre-wrap;
        word-break:break-word;
      }

      .pid-value-lg{
        font-size:.90rem;
        font-weight:900;
        color:#0f172a;
        line-height:1.35;
      }

      .pid-ev-grid{
        display:grid;
        gap:10px;
      }

      .pid-ev-card{
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

      .pid-ev-left{
        display:flex;
        align-items:center;
        gap:7px;
        min-width:0;
      }

      .pid-ev-icon{
        width:32px;
        height:32px;
        min-width:32px;
        border-radius:11px;
        background:linear-gradient(135deg,#b91c1c,#ef4444);
        color:#fff;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:.74rem;
        font-weight:900;
        box-shadow:0 6px 14px rgba(211,47,47,.20);
      }

      .pid-ev-meta{
        min-width:0;
      }

      .pid-ev-name{
        display:block;
        font-size:.78rem;
        font-weight:900;
        color:#1d4ed8;
        text-decoration:none;
        word-break:break-word;
      }

      .pid-ev-name:hover{
        text-decoration:underline;
      }

      .pid-ev-size{
        font-size:.70rem;
        color:#475569;
        margin-top:2px;
      }

      .pid-empty-box{
        background:rgba(255,255,255,.75);
        border:1px dashed #cfd8e3;
        border-radius:14px;
        padding:8px 7px;
        text-align:center;
        color:#475569;
        font-size:.80rem;
      }

      @media (max-width:992px){
        .pid-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .pid-header-card{
          min-height:88px;
          padding:15px 18px;
        }

        .pid-title{
          font-size:1.22rem;
        }

        .pid-subtitle{
          font-size:.74rem;
        }

        .pid-card-body{
          padding:8px 7px;
        }

        .pid-section{
          padding:12px;
        }
      }

      @media (max-width:768px){
        .pid-header-overlay{
          justify-content:center;
          text-align:center;
          flex-direction:column;
          gap:10px;
        }

        .pid-header-overlay::before{
          margin-right:0;
        }

        .pid-title{
          font-size:1.12rem;
        }

        .pid-subtitle{
          font-size:.72rem;
        }

        .pid-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(
        html,
        it=it,
        read_only=read_only,
        format_fecha_partes=format_fecha_partes
    )
    return render_template_string(BASE, content=Markup(inner))


# ==========================
# Editar
# ==========================
@app.route('/partes_interesadas/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def parte_interesada_edit(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede editar registros.", "danger")
        return redirect(url_for('partes_interesadas_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Partes Interesadas"):
        flash("No tiene permiso para editar registros.", "danger")
        return redirect(url_for('partes_interesadas_matriz'))

    it = ParteInteresada.query.get_or_404(id)

    if request.method == 'POST':
        parte_interesada = (request.form.get('parte_interesada') or '').strip()
        necesidades = (request.form.get('necesidades_expectativas') or '').strip()
        requisitos = (request.form.get('requisitos_aplicables') or '').strip()
        fecha_str = (request.form.get('fecha_revision') or '').strip()

        if not all([parte_interesada, necesidades, requisitos]):
            flash("Campos obligatorios: Parte interesada, Necesidades/Expectativas y Requisitos aplicables.", "danger")
            return redirect(url_for('parte_interesada_edit', id=id))

        fecha_revision = None
        if fecha_str:
            try:
                fecha_revision = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            except ValueError:
                flash("Fecha de revisión inválida.", "danger")
                return redirect(url_for('parte_interesada_edit', id=id))

        it.parte_interesada = parte_interesada
        it.necesidades_expectativas = necesidades
        it.requisitos_aplicables = requisitos
        it.fecha_revision = fecha_revision

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
        flash("Registro actualizado.", "success")
        return redirect(url_for('partes_interesadas_matriz'))

    fecha_value = ""
    if getattr(it, "fecha_revision", None):
        try:
            fecha_value = it.fecha_revision.strftime("%Y-%m-%d")
        except Exception:
            fecha_value = ""

    html = """
    <div class="partesedit-shell">

      <div class="partesedit-header-card">
        <div class="partesedit-header-overlay">
          <div class="partesedit-header-text">
            <h3 class="partesedit-title m-0">Editar Parte Interesada</h3>
            <div class="partesedit-subtitle">
              Actualización de la información, necesidades, requisitos aplicables y evidencias de la parte interesada
            </div>
          </div>
        </div>
      </div>

      <div class="partesedit-header-actions">
        <a href="{{ url_for('partes_interesadas_matriz') }}"
           class="btn rounded-pill px-4 fw-bold partesedit-back-btn">
          ⬅ Volver a la Matriz
        </a>
      </div>

      <div class="partesedit-card">
        <div class="partesedit-card-body">
          <form method="post" enctype="multipart/form-data">
            <div class="row g-3">

              <div class="col-md-6">
                <label class="form-label">Parte Interesada</label>
                <input name="parte_interesada" class="form-control" required value="{{ it.parte_interesada }}">
              </div>

              <div class="col-md-6">
                <label class="form-label">Fecha de Revisión</label>
                <input type="date" name="fecha_revision" class="form-control" value="{{ fecha_value }}">
              </div>

              <div class="col-md-12">
                <label class="form-label">Necesidades / Expectativas</label>
                <textarea name="necesidades_expectativas" class="form-control" rows="2" required>{{ it.necesidades_expectativas }}</textarea>
              </div>

              <div class="col-md-12">
                <label class="form-label">Requisitos Aplicables</label>
                <textarea name="requisitos_aplicables" class="form-control" rows="2" required>{{ it.requisitos_aplicables }}</textarea>
              </div>

              <div class="col-lg-6">
                <label class="form-label">Agregar nuevas evidencias PDF</label>

                <div class="partesedit-upload-box">
                  <div class="partesedit-upload-icon">📎</div>
                  <div class="partesedit-upload-title">Adjuntar nuevos archivos</div>
                  <div class="partesedit-upload-subtitle2">
                    Los PDFs actuales se conservan. Aquí solo agregarás evidencias nuevas.
                  </div>

                  <div class="mt-3">
                    <input
                      type="file"
                      id="evidencias"
                      name="evidencias"
                      accept=".pdf"
                      multiple
                      class="form-control partesedit-file-input"
                      onchange="acumularEvidencias(this)">
                  </div>

                  <div class="mt-3">
                    <div id="lista_evidencias_nuevas" class="partesedit-files-grid"></div>
                  </div>
                </div>
              </div>

              <div class="col-lg-6">
                <label class="form-label">Evidencias actuales</label>

                <div class="partesedit-current-box">
                  {% if it.evidencias %}
                    <div class="partesedit-files-grid">
                      {% for ev in it.evidencias %}
                        <div id="ev-row-{{ ev.id }}" class="partesedit-file-card-current">
                          <div class="partesedit-file-left">
                            <div class="partesedit-file-pdf">PDF</div>
                            <div class="partesedit-file-meta">
                              <div class="partesedit-file-name" title="{{ ev.original_name }}">
                                {{ ev.original_name }}
                              </div>
                              <div class="partesedit-file-status">
                                Archivo cargado · {{ ((ev.size or 0)/1024)|round(1) }} KB
                              </div>
                            </div>
                          </div>

                          <div class="partesedit-file-actions">
                            <a href="{{ url_for('partes_evidencia_view', evi_id=ev.id, next='partes_interesadas_matriz') }}"
                               class="btn btn-sm btn-outline-primary rounded-pill px-3">
                              Ver
                            </a>

                            <button type="button"
                                    class="btn btn-sm btn-outline-danger rounded-pill px-3"
                                    onclick="eliminarEvidenciaParte({{ ev.id }})">
                              Eliminar
                            </button>
                          </div>
                        </div>
                      {% endfor %}
                    </div>
                  {% else %}
                    <div class="text-muted small partesedit-empty-box">
                      No hay evidencias cargadas para este registro.
                    </div>
                  {% endif %}
                </div>
              </div>

            </div>

            <div class="partesedit-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar cambios
              </button>
              <a href="{{ url_for('partes_interesadas_matriz') }}"
                 class="btn rounded-pill px-4 fw-bold partesedit-cancel-btn">
                Cancelar
              </a>
            </div>
          </form>
        </div>
      </div>
    </div>

    <script>
      async function eliminarEvidenciaParte(eviId) {
        if (!confirm('¿Desea eliminar esta evidencia?')) return;

        try {
          const resp = await fetch(`/partes_evidencia/${eviId}/delete`, {
            method: 'POST',
            headers: {
              'X-Requested-With': 'XMLHttpRequest'
            }
          });

          if (resp.ok) {
            const row = document.getElementById(`ev-row-${eviId}`);
            if (row) row.remove();
          } else {
            alert('No se pudo eliminar la evidencia.');
          }
        } catch (err) {
          console.error(err);
          alert('Error de conexión al eliminar la evidencia.');
        }
      }

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
            <div class="text-muted small partesedit-empty-box">
              No hay archivos nuevos seleccionados
            </div>
          `;
          return;
        }

        for (let i = 0; i < evidenciasBufferDT.files.length; i++) {
          const f = evidenciasBufferDT.files[i];
          const card = document.createElement('div');
          card.className = 'partesedit-file-card-new';
          card.innerHTML = `
            <div class="partesedit-file-left">
              <div class="partesedit-file-pdf">PDF</div>
              <div class="partesedit-file-meta">
                <div class="partesedit-file-name" title="${f.name}">${f.name}</div>
                <div class="partesedit-file-status">Listo para cargar · ${formatFileSize(f.size)}</div>
              </div>
            </div>

            <button type="button"
                    class="btn btn-sm btn-outline-danger rounded-pill px-3"
                    onclick="removeEvidenciaFromBuffer(${i})">
              Quitar
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

    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .partesedit-shell{
        width:96%;
        max-width:1300px;
        margin:10px auto 24px auto;
      }

      /* =========================
         HERO SGSI UNIFICADO
      ========================== */
      .partesedit-header-card{
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

      .partesedit-header-card::before{
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

      .partesedit-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        padding:0;
        position:relative;
        z-index:1;
      }

      .partesedit-header-overlay::before{
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

      .partesedit-header-text::before{
        content:"SGSI · Edición Parte Interesada";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
      }

      .partesedit-title{
        color:#fff;
        font-weight:950;
        font-size:1.32rem;
        margin:0;
      }

      .partesedit-subtitle{
        font-size:.78rem;
        opacity:.9;
      }

      /* =========================
         ACCIONES
      ========================== */
      .partesedit-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px;
      }

      .partesedit-back-btn{
        background:#fff;
        border:1px solid #cfd8e3;
        border-radius:10px;
        padding:8px 18px;
        font-weight:800;
      }

      /* =========================
         CARD
      ========================== */
      .partesedit-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
      }

      .partesedit-card-body{
        padding:16px 18px;
      }

      /* =========================
         FORMULARIO
      ========================== */
      .partesedit-card .form-label{
        font-weight:800;
        font-size:.78rem;
        margin-bottom:4px;
      }

      .partesedit-card .form-control,
      .partesedit-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:36px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .partesedit-card textarea{
        min-height:70px;
      }

      /* =========================
         UPLOAD
      ========================== */
      .partesedit-upload-box,
      .partesedit-current-box{
        border-radius:16px;
        padding:8px 7px;
        border:1px solid #dbe6f4;
        background:#fff;
      }

      .partesedit-upload-box{
        border:2px dashed #7fb0e6;
        text-align:center;
      }

      .partesedit-upload-icon{
        width:52px;
        height:52px;
        margin:auto;
        border-radius:14px;
        background:linear-gradient(135deg,#062b55,#1d5fae);
        color:#fff;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:1.4rem;
      }

      .partesedit-files-grid{
        display:grid;
        gap:10px;
      }

      .partesedit-file-card-current,
      .partesedit-file-card-new{
        display:flex;
        justify-content:space-between;
        align-items:center;
        padding:10px;
        border-radius:12px;
        border:1px solid #dbe6f4;
        background:#fff;
      }

      .partesedit-file-pdf{
        width:36px;
        height:36px;
        border-radius:10px;
        background:#b91c1c;
        color:#fff;
        display:flex;
        align-items:center;
        justify-content:center;
        font-weight:900;
      }

      /* =========================
         BOTONES
      ========================== */
      .partesedit-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:18px;
        flex-wrap:wrap;
      }

      .partesedit-bottom-actions .btn{
        border-radius:10px;
        padding:8px 20px;
        font-size:.8rem;
        font-weight:900;
      }

      /* =========================
         RESPONSIVE
      ========================== */
      @media(max-width:992px){
        .partesedit-shell{ width:98%; }

        .partesedit-header-card{
          min-height:88px;
        }

        .partesedit-title{
          font-size:1.2rem;
        }

        .partesedit-card-body{
          padding:8px 7px;
        }
      }

      @media(max-width:768px){
        .partesedit-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .partesedit-header-overlay::before{
          margin:0;
        }

        .partesedit-bottom-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(html, it=it, fecha_value=fecha_value)
    return render_template_string(BASE, content=Markup(inner))


# ==========================
# Eliminar registro
# ==========================
@app.route('/partes_interesadas/<int:id>/delete', methods=['POST'])
@login_required
def parte_interesada_delete(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede eliminar registros.", "danger")
        return redirect(url_for('partes_interesadas_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Partes Interesadas"):
        flash("No tiene permiso para eliminar registros.", "danger")
        return redirect(url_for('menu'))

    it = ParteInteresada.query.get_or_404(id)

    evs = list(getattr(it, 'evidencias', []) or [])
    for ev in evs:
        try:
            path = os.path.join(app.config['UPLOAD_PARTES_INTERESADAS_DIR'], ev.filename)
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
        db.session.delete(ev)

    db.session.delete(it)
    db.session.commit()
    flash("Registro eliminado.", "success")
    return redirect(url_for('partes_interesadas_matriz'))


# ==========================
# Eliminar evidencia individual
# ==========================
@app.route('/partes_evidencia/<int:evi_id>/delete', methods=['POST'])
@login_required
def partes_evidencia_delete(evi_id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede eliminar evidencias.", "danger")
        return redirect(url_for('partes_interesadas_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Partes Interesadas"):
        flash("No tiene permiso para eliminar evidencias.", "danger")
        return redirect(url_for('menu'))

    ev = ParteInteresadaEvidencia.query.get_or_404(evi_id)
    registro_id = ev.registro_id

    try:
        path = os.path.join(app.config['UPLOAD_PARTES_INTERESADAS_DIR'], ev.filename)
        if os.path.exists(path):
            os.remove(path)
    except Exception as ex:
        print("Error eliminando archivo físico de partes interesadas:", ex)

    db.session.delete(ev)
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return ('', 204)

    flash("Evidencia eliminada correctamente.", "success")
    return redirect(url_for('parte_interesada_edit', id=registro_id))

# ==========================================================================================================================================
#                                                               Fin Módulo Partes Interesadas
# ==========================================================================================================================================


# =========================================================================================================================================
#                                                               Módulo de Contexto Interno
# =========================================================================================================================================

class ContextoInterno(db.Model):
    __tablename__ = 'contexto_interno'

    id = db.Column(db.Integer, primary_key=True)

    factor_interno   = db.Column(db.String(200), nullable=False)   # Factor Interno
    descripcion      = db.Column(db.Text, nullable=False)          # Descripción
    impacto_sgsi     = db.Column(db.Text, nullable=False)          # Impacto en el SGSI
    fortalezas       = db.Column(db.Text, nullable=True)           # Fortalezas
    debilidades      = db.Column(db.Text, nullable=True)           # Debilidades
    fecha_revision   = db.Column(db.Date, nullable=True)           # Fecha de Revisión

def format_fecha_contexto(valor):
    if not valor:
        return '—'
    try:
        return valor.strftime('%Y-%m-%d')
    except Exception:
        return str(valor)

def resumir_contexto_texto(valor, limite=140):
    if not valor:
        return '—'
    txt = str(valor).strip()
    if len(txt) <= limite:
        return txt
    return txt[:limite].rstrip() + '...'


# ==========================
# ENTRADA DIRECTA AL MÓDULO
# ==========================
@app.route('/contexto_interno_menu')
@login_required
def contexto_interno_menu():
    user = User.query.get(session.get('user_id'))

    if user.role not in ('admin', 'auditor') and not verificar_permiso(user, "Contexto Interno"):
        flash("No tiene permiso para acceder al módulo de contexto interno.", "danger")
        return redirect(url_for('menu'))

    return redirect(url_for('contexto_interno_matriz'))


# ==========================
# Agregar Contexto Interno
# ==========================
@app.route('/contexto_interno/new', methods=['GET', 'POST'])
@login_required
def contexto_interno_new():

    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede agregar registros.", "danger")
        return redirect(url_for('contexto_interno_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Contexto Interno"):
        flash("No tiene permiso para agregar resgitro de contexto interno.", "danger")
        return redirect(url_for('contexto_interno_matriz'))

    if request.method == 'POST':
        factor_interno = (request.form.get('factor_interno') or '').strip()
        descripcion    = (request.form.get('descripcion') or '').strip()
        impacto_sgsi   = (request.form.get('impacto_sgsi') or '').strip()
        fortalezas     = (request.form.get('fortalezas') or '').strip()
        debilidades    = (request.form.get('debilidades') or '').strip()
        fecha_str      = (request.form.get('fecha_revision') or '').strip()

        fecha_revision = None
        if fecha_str:
            try:
                fecha_revision = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            except ValueError:
                flash("Fecha de revisión inválida.", "danger")
                return redirect(url_for('contexto_interno_new'))

        if not (factor_interno and descripcion and impacto_sgsi):
            flash("Campos obligatorios: Factor Interno, Descripción e Impacto en el SGSI.", "danger")
            return redirect(url_for('contexto_interno_new'))

        it = ContextoInterno(
            factor_interno=factor_interno,
            descripcion=descripcion,
            impacto_sgsi=impacto_sgsi,
            fortalezas=fortalezas,
            debilidades=debilidades,
            fecha_revision=fecha_revision
        )
        db.session.add(it)
        db.session.commit()
        flash("Contexto interno registrado.", "success")
        return redirect(url_for('contexto_interno_matriz'))

    html = """
    <div class="ctxint-shell">

      <div class="ctxint-header-card">
        <div class="ctxint-header-overlay">
          <div class="ctxint-header-text">
            <h3 class="ctxint-title m-0">Agregar Contexto Interno</h3>
            <div class="ctxint-subtitle">
              Registro de factores internos que influyen en el Sistema de Gestión de Seguridad de la Información
            </div>
          </div>
        </div>
      </div>

      <div class="ctxint-header-actions">
        <a href="{{ url_for('contexto_interno_matriz') }}"
           class="btn rounded-pill px-4 fw-bold ctxint-back-btn">
          ⬅ Volver a la Matriz
        </a>

      </div>

      <div class="ctxint-card">
        <div class="ctxint-card-body">
          <form method="post">
            <div class="row g-3">

              <div class="col-md-4">
                <label class="form-label">Factor Interno</label>
                <input name="factor_interno" class="form-control" required>
              </div>

              <div class="col-md-8">
                <label class="form-label">Descripción</label>
                <textarea name="descripcion" class="form-control" rows="2" required></textarea>
              </div>

              <div class="col-md-12">
                <label class="form-label">Impacto en el SGSI</label>
                <textarea name="impacto_sgsi" class="form-control" rows="2" required></textarea>
              </div>

              <div class="col-md-6">
                <label class="form-label">Fortalezas</label>
                <textarea name="fortalezas" class="form-control" rows="2"></textarea>
              </div>

              <div class="col-md-6">
                <label class="form-label">Debilidades</label>
                <textarea name="debilidades" class="form-control" rows="2"></textarea>
              </div>

              <div class="col-md-3">
                <label class="form-label">Fecha de Revisión</label>
                <input type="date" name="fecha_revision" class="form-control">
              </div>

            </div>

            <div class="ctxint-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar
              </button>

              <a href="{{ url_for('contexto_interno_matriz') }}"
                 class="btn rounded-pill px-4 fw-bold ctxint-cancel-btn">
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

      .ctxint-shell{
        width:96%;
        max-width:1300px;
        margin:10px auto 24px auto;
      }

      .ctxint-header-card{
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

      .ctxint-header-card::before{
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

      .ctxint-header-overlay{
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

      .ctxint-header-overlay::before{
        content:"🏢";
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

      .ctxint-header-text{
        max-width:1100px;
        position:relative;
        z-index:1;
      }

      .ctxint-header-text::before{
        content:"SGSI · Contexto Interno";
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

      .ctxint-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.36rem;
        line-height:1.08;
        text-shadow:0 3px 10px rgba(0,0,0,.32);
        margin:0 !important;
      }

      .ctxint-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
        text-shadow:none;
      }

      .ctxint-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px 0;
      }

      .ctxint-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .ctxint-header-actions .btn-primary,
      .ctxint-header-actions .btn-success{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .ctxint-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .ctxint-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .ctxint-card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        overflow:hidden;
        border:1px solid rgba(219,230,244,.9);
      }

      .ctxint-card-body{
        padding:16px 18px;
      }

      .ctxint-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .ctxint-card .form-control,
      .ctxint-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:37px;
        font-size:.80rem;
        background:#f8fafc;
        box-shadow:none;
        padding-top:5px;
        padding-bottom:5px;
      }

      .ctxint-card textarea{
        min-height:70px;
        resize:vertical;
      }

      .ctxint-card .form-control:focus,
      .ctxint-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .18rem rgba(63,134,214,.18);
      }

      .ctxint-card .row{
        row-gap:10px;
      }

      .ctxint-card .mb-3{
        margin-bottom:.70rem !important;
      }

      .ctxint-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:18px;
        flex-wrap:wrap;
      }

      .ctxint-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 24px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .ctxint-bottom-actions .btn-primary,
      .ctxint-bottom-actions .btn-success{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .ctxint-bottom-actions .btn-danger{
        border:none;
        background:linear-gradient(135deg,#b91c1c,#ef4444);
        color:#fff;
      }

      .ctxint-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .ctxint-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      @media (max-width:992px){
        .ctxint-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .ctxint-header-card{
          min-height:88px;
          padding:15px 18px;
        }

        .ctxint-title{
          font-size:1.22rem;
        }

        .ctxint-subtitle{
          font-size:.74rem;
        }

        .ctxint-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .ctxint-header-overlay{
          justify-content:center;
          text-align:center;
          flex-direction:column;
          gap:10px;
        }

        .ctxint-header-overlay::before{
          margin-right:0;
        }

        .ctxint-title{
          font-size:1.12rem;
        }

        .ctxint-subtitle{
          font-size:.72rem;
        }

        .ctxint-bottom-actions .btn,
        .ctxint-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(html)
    return render_template_string(BASE, content=Markup(inner))


# ==========================
# Matriz Contexto Interno
# ==========================
CONTEXTO_INTERNO_MATRIZ_MIN_COLS = [
    "factor_interno",
    "descripcion",
    "impacto_sgsi",
    "fecha_revision",
]

@app.route('/contexto_interno_matriz', methods=['GET'])
@login_required
def contexto_interno_matriz():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Contexto Interno"):
            flash("No tiene permiso para ver los contextos internos.", "danger")
            return redirect(url_for('menu'))
        read_only = False

    items = ContextoInterno.query.order_by(ContextoInterno.id.desc()).all()

    html = """
    <div class="ctxintmat-shell">

      <div class="ctxintmat-header-card">
        <div class="ctxintmat-header-overlay">
          <div class="ctxintmat-header-text">
            <h3 class="ctxintmat-title m-0">Contexto Interno</h3>
            <div class="ctxintmat-subtitle">
              Visualización resumida de los factores internos que afectan el Sistema de Gestión de Seguridad de la Información
            </div>
          </div>
        </div>
      </div>

      <div class="ctxintmat-header-actions">
        {% if not read_only %}
          <a href="{{ url_for('contexto_interno_new') }}"
             class="btn btn-primary rounded-pill px-4 fw-bold">
            ⨁ Agregar Contexto Interno
          </a>
        {% endif %}

      </div>

      <div class="ctxintmat-card">
        <div class="ctxintmat-topbar">
          <div>
            <h5 class="ctxintmat-top-title mb-1">Resumen de registros</h5>
            <div class="ctxintmat-top-note">
              La matriz presenta únicamente los campos más importantes. Para revisar el registro completo usa el botón <strong>Ver detalle</strong>.
            </div>
          </div>
          <div class="ctxintmat-counter-badge">
            Total registros: {{ items|length }}
          </div>
        </div>

        <div class="ctxintmat-card-body">
          <div class="ctxintmat-table-wrap">
            <div class="table-responsive">
              <table class="table table-bordered table-hover align-middle ctxintmat-table mb-0">
                <colgroup>
                  <col style="width: 22%;">
                  <col style="width: 28%;">
                  <col style="width: 28%;">
                  <col style="width: 10%;">
                  <col style="width: 12%;">
                </colgroup>

                <thead>
                  <tr>
                    <th>Factor Interno</th>
                    <th>Descripción</th>
                    <th>Impacto en el SGSI</th>
                    <th>Fecha de Revisión</th>
                    <th>Acciones</th>
                  </tr>
                </thead>

                <tbody>
                  {% for it in items %}
                    <tr>
                      <td class="ctxintmat-cell-main">
                        <div class="ctxintmat-main-text">{{ it.factor_interno or '—' }}</div>
                      </td>

                      <td>{{ resumir_contexto_texto(it.descripcion, 150) }}</td>

                      <td>{{ resumir_contexto_texto(it.impacto_sgsi, 150) }}</td>

                      <td class="text-center">
                        {{ format_fecha_contexto(it.fecha_revision) }}
                      </td>

                      <td class="text-center">
                        <div class="ctxintmat-actions-wrap">
                          <a href="{{ url_for('contexto_interno_detalle', id=it.id) }}"
                             class="btn btn-info btn-sm rounded-pill px-3 fw-bold text-white">
                            Ver detalle
                          </a>

                          {% if not read_only %}
                            <a href="{{ url_for('contexto_interno_edit', id=it.id) }}"
                               class="btn btn-warning btn-sm rounded-pill px-3 fw-bold">
                              Editar
                            </a>

                            <a href="{{ url_for('contexto_interno_delete', id=it.id) }}"
                               class="btn btn-danger btn-sm rounded-pill px-3 fw-bold"
                               onclick="return confirm('¿Eliminar este registro?');">
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

      .ctxintmat-shell{
        width:96%;
        max-width:1650px;
        margin:10px auto 24px auto;
      }

      .ctxintmat-header-card{
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

      .ctxintmat-header-card::before{
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

      .ctxintmat-header-overlay{
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

      .ctxintmat-header-overlay::before{
        content:"🏢";
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

      .ctxintmat-header-text{
        max-width:1100px;
        position:relative;
        z-index:1;
      }

      .ctxintmat-header-text::before{
        content:"SGSI · Contexto Interno";
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

      .ctxintmat-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.36rem;
        line-height:1.08;
        text-shadow:0 3px 10px rgba(0,0,0,.32);
        margin:0 !important;
      }

      .ctxintmat-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
        text-shadow:none;
      }

      .ctxintmat-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px 0;
      }

      .ctxintmat-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .ctxintmat-header-actions .btn-primary,
      .ctxintmat-header-actions .btn-success{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .ctxintmat-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .ctxintmat-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .ctxintmat-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        overflow:hidden;
        border:1px solid rgba(219,230,244,.9);
      }

      .ctxintmat-topbar{
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:12px;
        padding:14px 16px 0 16px;
        flex-wrap:wrap;
      }

      .ctxintmat-top-title{
        color:#0f172a;
        font-weight:950;
        font-size:.94rem;
      }

      .ctxintmat-top-note{
        color:#475569;
        font-size:.78rem;
        margin-top:3px;
      }

      .ctxintmat-counter-badge{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        color:#fff;
        font-weight:900;
        border-radius:999px;
        padding:7px 14px;
        font-size:.78rem;
        box-shadow:0 8px 16px rgba(15,23,42,.16);
      }

      .ctxintmat-card-body{
        padding:12px 16px 16px 16px;
      }

      .ctxintmat-table-wrap{
        max-height:70vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:rgba(255,255,255,.99);
      }

      .ctxintmat-table{
        min-width:1200px;
        margin-bottom:0;
        table-layout:fixed;
        border-collapse:separate;
        border-spacing:0;
      }

      .ctxintmat-table th,
      .ctxintmat-table td{
        white-space:normal;
        word-break:break-word;
        vertical-align:top;
        font-size:.68rem;
        padding:9px 8px;
      }

      .ctxintmat-table thead th{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff;
        font-weight:900;
        text-align:center;
        vertical-align:middle;
        border-right:1px solid rgba(255,255,255,.28);
      }

      .ctxintmat-table td{
        color:#101827;
        border-right:1px solid #dce6f3;
        border-bottom:1px solid #dce6f3;
        background:#ffffff;
      }

      .ctxintmat-table tbody tr:nth-child(even) td{
        background:#f8fbff;
      }

      .ctxintmat-table tbody tr:hover td{
        background:#eef6ff;
      }

      .ctxintmat-cell-main .ctxintmat-main-text{
        font-weight:900;
        color:#0f172a;
        line-height:1.35;
      }

      .ctxintmat-actions-wrap{
        display:flex;
        flex-direction:column;
        gap:6px;
        align-items:center;
        justify-content:center;
      }

      .ctxintmat-actions-wrap .btn,
      .ctxintmat-table .btn{
        min-width:86px;
        min-height:28px;
        border-radius:999px !important;
        padding:4px 12px !important;
        font-size:.70rem;
        font-weight:900;
        display:inline-flex;
        align-items:center;
        justify-content:center;
      }

      .ctxintmat-table .btn-info{
        background:#087ab8;
        border:none;
        color:#fff;
      }

      .ctxintmat-table .btn-warning{
        background:#c76b00;
        border:none;
        color:#0b1220;
      }

      .ctxintmat-table .btn-danger{
        background:#b91c1c;
        border:none;
        color:#fff;
      }

      .ctxintmat-table .btn-success{
        background:#087c3d;
        border:none;
        color:#fff;
      }

      .ctxintmat-table-wrap::-webkit-scrollbar{
        height:11px;
        width:11px;
      }

      .ctxintmat-table-wrap::-webkit-scrollbar-track{
        background:#dbe4f0;
        border-radius:12px;
      }

      .ctxintmat-table-wrap::-webkit-scrollbar-thumb{
        background:linear-gradient(180deg,#5aa3ea,#3f86d6);
        border-radius:12px;
        border:2px solid #dbe4f0;
      }

      .ctxintmat-table-wrap{
        scrollbar-width:thin;
        scrollbar-color:#3f86d6 #dbe4f0;
      }

      @media (max-width:992px){
        .ctxintmat-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .ctxintmat-header-card{
          min-height:88px;
          padding:15px 18px;
        }

        .ctxintmat-card-body{
          padding:12px 14px 14px 14px;
        }

        .ctxintmat-topbar{
          padding:12px 14px 0 14px;
        }

        .ctxintmat-title{
          font-size:1.22rem;
        }

        .ctxintmat-subtitle{
          font-size:.74rem;
        }
      }

      @media (max-width:768px){
        .ctxintmat-header-overlay{
          justify-content:center;
          text-align:center;
          flex-direction:column;
          gap:10px;
        }

        .ctxintmat-header-overlay::before{
          margin-right:0;
        }

        .ctxintmat-title{
          font-size:1.12rem;
        }

        .ctxintmat-subtitle{
          font-size:.72rem;
        }

        .ctxintmat-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(
        html,
        items=items,
        read_only=read_only,
        resumir_contexto_texto=resumir_contexto_texto,
        format_fecha_contexto=format_fecha_contexto
    )
    return render_template_string(BASE, content=Markup(inner))


# ==========================
# Detalle Contexto Interno
# ==========================
@app.route('/contexto_interno/detalle/<int:id>')
@login_required
def contexto_interno_detalle(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Contexto Interno"):
            flash("No tiene permiso para ver el detalle del contexto interno.", "danger")
            return redirect(url_for('contexto_interno_matriz'))
        read_only = False

    it = ContextoInterno.query.get_or_404(id)

    html = """
    <div class="ctxintd-shell">

      <div class="ctxintd-header-card">
        <div class="ctxintd-header-overlay">
          <div class="ctxintd-header-text">
            <h3 class="ctxintd-title m-0">Detalle — Contexto Interno</h3>
            <div class="ctxintd-subtitle">
              Consulta completa del registro en modo solo lectura
            </div>
          </div>
        </div>
      </div>

      <div class="ctxintd-header-actions">
        <a href="{{ url_for('contexto_interno_matriz') }}"
           class="btn rounded-pill px-4 fw-bold ctxintd-back-btn">
          ⬅ Volver a la Matriz
        </a>


        {% if not read_only %}
          <a href="{{ url_for('contexto_interno_edit', id=it.id) }}"
             class="btn btn-warning rounded-pill px-4 fw-bold">
            Editar registro
          </a>
        {% endif %}
      </div>

      <div class="ctxintd-card">
        <div class="ctxintd-card-body">

          <div class="ctxintd-section">
            <div class="ctxintd-section-title">Información principal</div>
            <div class="row g-3">
              <div class="col-md-8">
                <div class="ctxintd-field">
                  <div class="ctxintd-label">Factor Interno</div>
                  <div class="ctxintd-value ctxintd-value-lg">{{ it.factor_interno or '—' }}</div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="ctxintd-field">
                  <div class="ctxintd-label">Fecha de Revisión</div>
                  <div class="ctxintd-value">{{ format_fecha_contexto(it.fecha_revision) }}</div>
                </div>
              </div>

              <div class="col-md-12">
                <div class="ctxintd-field">
                  <div class="ctxintd-label">Descripción</div>
                  <div class="ctxintd-value">{{ it.descripcion or '—' }}</div>
                </div>
              </div>

              <div class="col-md-12">
                <div class="ctxintd-field">
                  <div class="ctxintd-label">Impacto en el SGSI</div>
                  <div class="ctxintd-value">{{ it.impacto_sgsi or '—' }}</div>
                </div>
              </div>
            </div>
          </div>

          <div class="ctxintd-section">
            <div class="ctxintd-section-title">Análisis interno</div>
            <div class="row g-3">
              <div class="col-md-6">
                <div class="ctxintd-field">
                  <div class="ctxintd-label">Fortalezas</div>
                  <div class="ctxintd-value">{{ it.fortalezas or '—' }}</div>
                </div>
              </div>

              <div class="col-md-6">
                <div class="ctxintd-field">
                  <div class="ctxintd-label">Debilidades</div>
                  <div class="ctxintd-value">{{ it.debilidades or '—' }}</div>
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

      .ctxintd-shell{
        width:96%;
        max-width:1250px;
        margin:10px auto 24px auto;
      }

      /* =========================
         HERO SGSI UNIFICADO
      ========================== */
      .ctxintd-header-card{
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

      .ctxintd-header-card::before{
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

      .ctxintd-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        padding:0;
        position:relative;
        z-index:1;
      }

      .ctxintd-header-overlay::before{
        content:"🏢";
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

      .ctxintd-header-text::before{
        content:"SGSI · Contexto Interno (Detalle)";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
      }

      .ctxintd-title{
        color:#fff;
        font-weight:950;
        font-size:1.32rem;
        margin:0;
      }

      .ctxintd-subtitle{
        font-size:.78rem;
        opacity:.9;
      }

      /* =========================
         ACCIONES
      ========================== */
      .ctxintd-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px;
      }

      .ctxintd-back-btn{
        background:#fff;
        border:1px solid #cfd8e3;
        border-radius:10px;
        padding:8px 18px;
        font-weight:800;
      }

      /* =========================
         CARD
      ========================== */
      .ctxintd-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
      }

      .ctxintd-card-body{
        padding:16px 18px;
      }

      /* =========================
         SECCIONES
      ========================== */
      .ctxintd-section{
        margin-bottom:14px;
        background:#ffffff;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:8px 7px;
        box-shadow:0 8px 18px rgba(15,23,42,.08);
      }

      .ctxintd-section:last-child{
        margin-bottom:0;
      }

      .ctxintd-section-title{
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
         CAMPOS
      ========================== */
      .ctxintd-field{
        background:linear-gradient(180deg,#f8fbff 0%,#ffffff 100%);
        border:1px solid #dbe6f4;
        border-radius:14px;
        padding:12px;
        min-height:100%;
      }

      .ctxintd-label{
        font-size:.70rem;
        font-weight:900;
        text-transform:uppercase;
        letter-spacing:.35px;
        color:#0b4a8f;
        margin-bottom:6px;
      }

      .ctxintd-value{
        color:#101827;
        font-size:.82rem;
        line-height:1.38;
        white-space:pre-wrap;
        word-break:break-word;
      }

      .ctxintd-value-lg{
        font-size:.90rem;
        font-weight:900;
        color:#0f172a;
      }

      /* =========================
         RESPONSIVE
      ========================== */
      @media(max-width:992px){
        .ctxintd-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .ctxintd-header-card{
          min-height:88px;
        }

        .ctxintd-title{
          font-size:1.2rem;
        }

        .ctxintd-card-body{
          padding:8px 7px;
        }

        .ctxintd-section{
          padding:12px;
        }
      }

      @media(max-width:768px){
        .ctxintd-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .ctxintd-header-overlay::before{
          margin:0;
        }
      }
    </style>
    """

    inner = render_template_string(
        html,
        it=it,
        read_only=read_only,
        format_fecha_contexto=format_fecha_contexto
    )
    return render_template_string(BASE, content=Markup(inner))


# ==========================
# Edición
# ==========================
@app.route('/contexto_interno/edit/<int:id>', methods=['GET','POST'])
@login_required
def contexto_interno_edit(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor' or (
        user.role != 'admin' and not verificar_permiso(user, "Contexto Interno")
    ):
        flash("No tiene permiso para editar registros del contexto interno.", "danger")
        return redirect(url_for('contexto_interno_matriz'))
    
    item = ContextoInterno.query.get_or_404(id)

    if request.method == 'POST':
        item.factor_interno = (request.form.get('factor_interno') or '').strip()
        item.descripcion    = (request.form.get('descripcion') or '').strip()
        item.impacto_sgsi   = (request.form.get('impacto_sgsi') or '').strip()
        item.fortalezas     = (request.form.get('fortalezas') or '').strip()
        item.debilidades    = (request.form.get('debilidades') or '').strip()
        fecha_str           = (request.form.get('fecha_revision') or '').strip()

        if fecha_str:
            try:
                item.fecha_revision = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            except ValueError:
                flash("Fecha de revisión inválida.", "danger")
                return redirect(url_for('contexto_interno_edit', id=id))
        else:
            item.fecha_revision = None

        db.session.commit()
        flash("Registro actualizado.", "success")
        return redirect(url_for('contexto_interno_matriz'))

    html = """
    <div class="ctxinted-shell">

      <div class="ctxinted-header-card">
        <div class="ctxinted-header-overlay">
          <div class="ctxinted-header-text">
            <h3 class="ctxinted-title m-0">Editar Contexto Interno</h3>
            <div class="ctxinted-subtitle">
              Actualización de factores internos que afectan el Sistema de Gestión de Seguridad de la Información
            </div>
          </div>
        </div>
      </div>

      <div class="ctxinted-header-actions">
        <a href="{{ url_for('contexto_interno_matriz') }}"
           class="btn rounded-pill px-4 fw-bold ctxinted-back-btn">
          ⬅ Volver a la Matriz
        </a>

      </div>

      <div class="ctxinted-card">
        <div class="ctxinted-card-body">

          <form method="post">
            <div class="row g-3">

              <div class="col-md-4">
                <label class="form-label">Factor Interno</label>
                <input name="factor_interno"
                       class="form-control"
                       value="{{ item.factor_interno }}"
                       required>
              </div>

              <div class="col-md-8">
                <label class="form-label">Descripción</label>
                <textarea name="descripcion"
                          class="form-control"
                          rows="2"
                          required>{{ item.descripcion }}</textarea>
              </div>

              <div class="col-md-12">
                <label class="form-label">Impacto en el SGSI</label>
                <textarea name="impacto_sgsi"
                          class="form-control"
                          rows="2"
                          required>{{ item.impacto_sgsi }}</textarea>
              </div>

              <div class="col-md-6">
                <label class="form-label">Fortalezas</label>
                <textarea name="fortalezas"
                          class="form-control"
                          rows="2">{{ item.fortalezas }}</textarea>
              </div>

              <div class="col-md-6">
                <label class="form-label">Debilidades</label>
                <textarea name="debilidades"
                          class="form-control"
                          rows="2">{{ item.debilidades }}</textarea>
              </div>

              <div class="col-md-3">
                <label class="form-label">Fecha de Revisión</label>
                <input type="date"
                       name="fecha_revision"
                       class="form-control"
                       value="{{ item.fecha_revision.strftime('%Y-%m-%d') if item.fecha_revision else '' }}">
              </div>

            </div>

            <div class="ctxinted-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold"
                      type="submit">
                Guardar cambios
              </button>

              <a href="{{ url_for('contexto_interno_matriz') }}"
                 class="btn rounded-pill px-4 fw-bold ctxinted-cancel-btn">
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

      .ctxinted-shell{
        width:96%;
        max-width:1300px;
        margin:10px auto 24px auto;
      }

      .ctxinted-header-card{
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

      .ctxinted-header-card::before{
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

      .ctxinted-header-overlay{
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

      .ctxinted-header-overlay::before{
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
      }

      .ctxinted-header-text{
        max-width:1100px;
        position:relative;
        z-index:1;
      }

      .ctxinted-header-text::before{
        content:"SGSI · Edición Contexto Interno";
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

      .ctxinted-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.36rem;
        line-height:1.08;
        text-shadow:0 3px 10px rgba(0,0,0,.32);
        margin:0 !important;
      }

      .ctxinted-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
        text-shadow:none;
      }

      .ctxinted-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px 0;
      }

      .ctxinted-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .ctxinted-header-actions .btn-primary,
      .ctxinted-header-actions .btn-success{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .ctxinted-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .ctxinted-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .ctxinted-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        overflow:hidden;
        border:1px solid rgba(219,230,244,.9);
      }

      .ctxinted-card-body{
        padding:16px 18px;
      }

      .ctxinted-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .ctxinted-card .form-control,
      .ctxinted-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:37px;
        font-size:.80rem;
        background:#f8fafc;
        box-shadow:none;
        padding-top:5px;
        padding-bottom:5px;
      }

      .ctxinted-card textarea{
        min-height:70px;
        resize:vertical;
      }

      .ctxinted-card .form-control:focus,
      .ctxinted-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .18rem rgba(63,134,214,.18);
      }

      .ctxinted-card .row{
        row-gap:10px;
      }

      .ctxinted-card .mb-3{
        margin-bottom:.70rem !important;
      }

      .ctxinted-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:18px;
        flex-wrap:wrap;
      }

      .ctxinted-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 24px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .ctxinted-bottom-actions .btn-primary,
      .ctxinted-bottom-actions .btn-success{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .ctxinted-bottom-actions .btn-danger{
        border:none;
        background:linear-gradient(135deg,#b91c1c,#ef4444);
        color:#fff;
      }

      .ctxinted-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .ctxinted-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      @media (max-width:992px){
        .ctxinted-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .ctxinted-header-card{
          min-height:88px;
          padding:15px 18px;
        }

        .ctxinted-title{
          font-size:1.22rem;
        }

        .ctxinted-subtitle{
          font-size:.74rem;
        }

        .ctxinted-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .ctxinted-header-overlay{
          justify-content:center;
          text-align:center;
          flex-direction:column;
          gap:10px;
        }

        .ctxinted-header-overlay::before{
          margin-right:0;
        }

        .ctxinted-title{
          font-size:1.12rem;
        }

        .ctxinted-subtitle{
          font-size:.72rem;
        }

        .ctxinted-bottom-actions .btn,
        .ctxinted-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(html, item=item)
    return render_template_string(BASE, content=Markup(inner))


# ==========================
# Borrado
# ==========================
@app.route('/contexto_interno/delete/<int:id>')
@login_required
def contexto_interno_delete(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor' or (
        user.role != 'admin' and not verificar_permiso(user, "Contexto Interno")
    ):
        flash("No tiene permiso para eliminar registros del contexto interno.", "danger")
        return redirect(url_for('contexto_interno_matriz'))

    item = ContextoInterno.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash("Registro eliminado.", "success")
    return redirect(url_for('contexto_interno_matriz'))

# ==========================================================================================================================================
#                                                               Fin Módulo de Contexto Interno
# ==========================================================================================================================================


# ==========================================================================================================================================
#                                                               Módulo de Contexto Externo
# ==========================================================================================================================================

class ContextoExterno(db.Model):
    __tablename__ = 'contexto_externo'

    id = db.Column(db.Integer, primary_key=True)

    categoria            = db.Column(db.String(200), nullable=False)  # Categoría
    descripcion_factor   = db.Column(db.Text, nullable=False)         # Descripción del factor externo
    impacto_sgsi         = db.Column(db.Text, nullable=False)         # Impacto en el SGSI
    oportunidades = db.Column(db.Text, nullable=True)
    amenazas      = db.Column(db.Text, nullable=True)
    fecha_revision       = db.Column(db.Date, nullable=True)          # Fecha de Revisión

def format_fecha_contexto_externo(valor):
    if not valor:
        return '—'
    try:
        return valor.strftime('%Y-%m-%d')
    except Exception:
        return str(valor)

def resumir_contexto_externo_texto(valor, limite=140):
    if not valor:
        return '—'
    txt = str(valor).strip()
    if len(txt) <= limite:
        return txt
    return txt[:limite].rstrip() + '...'


# ==========================
# ENTRADA DIRECTA AL MÓDULO
# ==========================
@app.route('/contexto_externo_menu')
@login_required
def contexto_externo_menu():
    user = User.query.get(session.get('user_id'))

    if user.role not in ('admin', 'auditor') and not verificar_permiso(user, "Contexto Externo"):
        flash("No tiene permiso para acceder al módulo de contexto externo.", "danger")
        return redirect(url_for('menu'))

    return redirect(url_for('contexto_externo_matriz'))


# ==========================
# Agregar Contexto Externo
# ==========================
@app.route('/contexto_externo/new', methods=['GET', 'POST'])
@login_required
def contexto_externo_new():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        flash("El rol Auditor no puede agregar registros.", "danger")
        return redirect(url_for('contexto_externo_matriz'))

    if user.role != 'admin' and not verificar_permiso(user, "Contexto Externo"):
        flash("No tiene permiso para agregar registro de contexto externo.", "danger")
        return redirect(url_for('contexto_externo_matriz'))

    if request.method == 'POST':
        categoria          = (request.form.get('categoria') or '').strip()
        descripcion_factor = (request.form.get('descripcion_factor') or '').strip()
        impacto_sgsi       = (request.form.get('impacto_sgsi') or '').strip()
        oportunidades      = (request.form.get('oportunidades') or '').strip()
        amenazas           = (request.form.get('amenazas') or '').strip()
        fecha_str          = (request.form.get('fecha_revision') or '').strip()

        fecha_revision = None
        if fecha_str:
            try:
                fecha_revision = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            except ValueError:
                flash("Fecha de revisión inválida.", "danger")
                return redirect(url_for('contexto_externo_new'))

        if not (categoria and descripcion_factor and impacto_sgsi):
            flash("Campos obligatorios: Categoría, Descripción del factor externo e Impacto en el SGSI.", "danger")
            return redirect(url_for('contexto_externo_new'))

        it = ContextoExterno(
            categoria=categoria,
            descripcion_factor=descripcion_factor,
            impacto_sgsi=impacto_sgsi,
            oportunidades=oportunidades,
            amenazas=amenazas,
            fecha_revision=fecha_revision
        )
        db.session.add(it)
        db.session.commit()
        flash("Contexto externo registrado.", "success")
        return redirect(url_for('contexto_externo_matriz'))

    html = """
    <div class="ctxext-shell">

      <div class="ctxext-header-card">
        <div class="ctxext-header-overlay">
          <div class="ctxext-header-text">
            <h3 class="ctxext-title m-0">⨁ Agregar Contexto Externo</h3>
            <div class="ctxext-subtitle">
              Registro de factores externos que influyen en el Sistema de Gestión de Seguridad de la Información
            </div>
          </div>
        </div>
      </div>

      <div class="ctxext-header-actions">
        <a href="{{ url_for('contexto_externo_matriz') }}"
           class="btn rounded-pill px-4 fw-bold ctxext-back-btn">
          ⬅ Volver a la Matriz
        </a>

      </div>

      <div class="ctxext-card">
        <div class="ctxext-card-body">
          <form method="post">
            <div class="row g-3">

              <div class="col-md-4">
                <label class="form-label">Categoría</label>
                <input name="categoria" class="form-control" required>
              </div>

              <div class="col-md-8">
                <label class="form-label">Descripción del factor externo</label>
                <textarea name="descripcion_factor" class="form-control" rows="2" required></textarea>
              </div>

              <div class="col-md-12">
                <label class="form-label">Impacto en el SGSI</label>
                <textarea name="impacto_sgsi" class="form-control" rows="2" required></textarea>
              </div>

              <div class="col-md-6">
                <label class="form-label">Oportunidades</label>
                <textarea name="oportunidades" class="form-control" rows="2"></textarea>
              </div>

              <div class="col-md-6">
                <label class="form-label">Amenazas</label>
                <textarea name="amenazas" class="form-control" rows="2"></textarea>
              </div>

              <div class="col-md-3">
                <label class="form-label">Fecha de Revisión</label>
                <input type="date" name="fecha_revision" class="form-control">
              </div>

            </div>

            <div class="ctxext-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar
              </button>

              <a href="{{ url_for('contexto_externo_matriz') }}"
                 class="btn rounded-pill px-4 fw-bold ctxext-cancel-btn">
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

      .ctxext-shell{
        width:96%;
        max-width:1300px;
        margin:10px auto 24px auto;
      }

      /* =========================
         HERO SGSI UNIFICADO
      ========================== */
      .ctxext-header-card{
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

      .ctxext-header-card::before{
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

      .ctxext-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        padding:0;
        position:relative;
        z-index:1;
      }

      .ctxext-header-overlay::before{
        content:"🌍";
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

      .ctxext-header-text::before{
        content:"SGSI · Contexto Externo";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
      }

      .ctxext-title{
        color:#fff;
        font-weight:950;
        font-size:1.32rem;
        margin:0;
      }

      .ctxext-subtitle{
        font-size:.78rem;
        opacity:.9;
      }

      /* =========================
         ACCIONES
      ========================== */
      .ctxext-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px;
      }

      .ctxext-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .ctxext-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .ctxext-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         CARD FORMULARIO
      ========================== */
      .ctxext-card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
      }

      .ctxext-card-body{
        padding:16px 18px;
      }

      /* =========================
         FORMULARIOS COMPACTOS
      ========================== */
      .ctxext-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .ctxext-card .form-control,
      .ctxext-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:37px;
        font-size:.80rem;
        background:#f8fafc;
        box-shadow:none;
      }

      .ctxext-card textarea{
        min-height:70px;
        resize:vertical;
      }

      .ctxext-card .form-control:focus,
      .ctxext-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .18rem rgba(63,134,214,.18);
      }

      .ctxext-card .row{
        row-gap:10px;
      }

      .ctxext-card .mb-3{
        margin-bottom:.70rem !important;
      }

      /* =========================
         BOTONES
      ========================== */
      .ctxext-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:18px;
        flex-wrap:wrap;
      }

      .ctxext-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 24px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .ctxext-bottom-actions .btn-primary,
      .ctxext-bottom-actions .btn-success{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .ctxext-bottom-actions .btn-danger{
        border:none;
        background:linear-gradient(135deg,#b91c1c,#ef4444);
        color:#fff;
      }

      .ctxext-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .ctxext-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         RESPONSIVE
      ========================== */
      @media (max-width:992px){
        .ctxext-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .ctxext-header-card{
          min-height:88px;
        }

        .ctxext-title{
          font-size:1.2rem;
        }

        .ctxext-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .ctxext-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .ctxext-header-overlay::before{
          margin:0;
        }

        .ctxext-bottom-actions .btn,
        .ctxext-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(html)
    return render_template_string(BASE, content=Markup(inner))


# ==========================
# Matriz Contexto Externo
# ==========================
CONTEXTO_EXTERNO_MATRIZ_MIN_COLS = [
    "categoria",
    "descripcion_factor",
    "impacto_sgsi",
    "fecha_revision",
]

@app.route('/contexto_externo_matriz', methods=['GET'])
@login_required
def contexto_externo_matriz():
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Contexto Externo"):
            flash("No tiene permiso para ver los contextos externos.", "danger")
            return redirect(url_for('menu'))
        read_only = False

    items = ContextoExterno.query.order_by(ContextoExterno.id.desc()).all()

    html = """
    <div class="ctxextmat-shell">

      <div class="ctxextmat-header-card">
        <div class="ctxextmat-header-overlay">
          <div class="ctxextmat-header-text">
            <h3 class="ctxextmat-title m-0">Contexto Externo</h3>
            <div class="ctxextmat-subtitle">
              Visualización resumida de los factores externos que afectan el Sistema de Gestión de Seguridad de la Información
            </div>
          </div>
        </div>
      </div>

      <div class="ctxextmat-header-actions">
        {% if not read_only %}
          <a href="{{ url_for('contexto_externo_new') }}"
             class="btn btn-primary rounded-pill px-4 fw-bold">
            Agregar Contexto Externo
          </a>
        {% endif %}

      </div>

      <div class="ctxextmat-card">
        <div class="ctxextmat-topbar">
          <div>
            <h5 class="ctxextmat-top-title mb-1">Resumen de registros</h5>
            <div class="ctxextmat-top-note">
              La matriz presenta únicamente los campos más importantes. Para revisar el registro completo usa el botón <strong>Ver detalle</strong>.
            </div>
          </div>
          <div class="ctxextmat-counter-badge">
            Total registros: {{ items|length }}
          </div>
        </div>

        <div class="ctxextmat-card-body">
          <div class="ctxextmat-table-wrap">
            <div class="table-responsive">
              <table class="table table-bordered table-hover align-middle ctxextmat-table mb-0">
                <colgroup>
                  <col style="width: 20%;">
                  <col style="width: 30%;">
                  <col style="width: 28%;">
                  <col style="width: 10%;">
                  <col style="width: 12%;">
                </colgroup>

                <thead>
                  <tr>
                    <th>Categoría</th>
                    <th>Descripción del factor externo</th>
                    <th>Impacto en el SGSI</th>
                    <th>Fecha de Revisión</th>
                    <th>Acciones</th>
                  </tr>
                </thead>

                <tbody>
                  {% for it in items %}
                    <tr>
                      <td class="ctxextmat-cell-main">
                        <div class="ctxextmat-main-text">{{ it.categoria or '—' }}</div>
                      </td>

                      <td>{{ resumir_contexto_externo_texto(it.descripcion_factor, 150) }}</td>

                      <td>{{ resumir_contexto_externo_texto(it.impacto_sgsi, 150) }}</td>

                      <td class="text-center">
                        {{ format_fecha_contexto_externo(it.fecha_revision) }}
                      </td>

                      <td class="text-center">
                        <div class="ctxextmat-actions-wrap">
                          <a href="{{ url_for('contexto_externo_detalle', id=it.id) }}"
                             class="btn btn-info btn-sm rounded-pill px-3 fw-bold text-white">
                            Ver detalle
                          </a>

                          {% if not read_only %}
                            <a href="{{ url_for('contexto_externo_edit', id=it.id) }}"
                               class="btn btn-warning btn-sm rounded-pill px-3 fw-bold">
                              Editar
                            </a>

                            <a href="{{ url_for('contexto_externo_delete', id=it.id) }}"
                               class="btn btn-danger btn-sm rounded-pill px-3 fw-bold"
                               onclick="return confirm('¿Eliminar este registro?');">
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

      .ctxextmat-shell{
        width:96%;
        max-width:1650px;
        margin:10px auto 24px auto;
      }

      .ctxextmat-header-card{
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

      .ctxextmat-header-card::before{
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

      .ctxextmat-header-overlay{
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

      .ctxextmat-header-overlay::before{
        content:"🌍";
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

      .ctxextmat-header-text{
        max-width:1100px;
        position:relative;
        z-index:1;
      }

      .ctxextmat-header-text::before{
        content:"SGSI · Contexto Externo";
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

      .ctxextmat-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.36rem;
        line-height:1.08;
        text-shadow:0 3px 10px rgba(0,0,0,.32);
        margin:0 !important;
      }

      .ctxextmat-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
        text-shadow:none;
      }

      .ctxextmat-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px 0;
      }

      .ctxextmat-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .ctxextmat-header-actions .btn-primary,
      .ctxextmat-header-actions .btn-success{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .ctxextmat-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .ctxextmat-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .ctxextmat-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        overflow:hidden;
        border:1px solid rgba(219,230,244,.9);
      }

      .ctxextmat-topbar{
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:12px;
        padding:14px 16px 0 16px;
        flex-wrap:wrap;
      }

      .ctxextmat-top-title{
        color:#0f172a;
        font-weight:950;
        font-size:.94rem;
      }

      .ctxextmat-top-note{
        color:#475569;
        font-size:.78rem;
        margin-top:3px;
      }

      .ctxextmat-counter-badge{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        color:#fff;
        font-weight:900;
        border-radius:999px;
        padding:7px 14px;
        font-size:.78rem;
        box-shadow:0 8px 16px rgba(15,23,42,.16);
      }

      .ctxextmat-card-body{
        padding:12px 16px 16px 16px;
      }

      .ctxextmat-table-wrap{
        max-height:70vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:rgba(255,255,255,.99);
      }

      .ctxextmat-table{
        min-width:1200px;
        margin-bottom:0;
        table-layout:fixed;
        border-collapse:separate;
        border-spacing:0;
      }

      .ctxextmat-table th,
      .ctxextmat-table td{
        white-space:normal;
        word-break:break-word;
        vertical-align:top;
        font-size:.68rem;
        padding:9px 8px;
      }

      .ctxextmat-table thead th{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff;
        font-weight:900;
        text-align:center;
        vertical-align:middle;
        border-right:1px solid rgba(255,255,255,.28);
      }

      .ctxextmat-table td{
        color:#101827;
        border-right:1px solid #dce6f3;
        border-bottom:1px solid #dce6f3;
        background:#ffffff;
      }

      .ctxextmat-table tbody tr:nth-child(even) td{
        background:#f8fbff;
      }

      .ctxextmat-table tbody tr:hover td{
        background:#eef6ff;
      }

      .ctxextmat-cell-main .ctxextmat-main-text{
        font-weight:900;
        color:#0f172a;
        line-height:1.35;
      }

      .ctxextmat-actions-wrap{
        display:flex;
        flex-direction:column;
        gap:6px;
        align-items:center;
        justify-content:center;
      }

      .ctxextmat-actions-wrap .btn,
      .ctxextmat-table .btn{
        min-width:86px;
        min-height:28px;
        border-radius:999px !important;
        padding:4px 12px !important;
        font-size:.70rem;
        font-weight:900;
        display:inline-flex;
        align-items:center;
        justify-content:center;
      }

      .ctxextmat-table .btn-info{
        background:#087ab8;
        border:none;
        color:#fff;
      }

      .ctxextmat-table .btn-warning{
        background:#c76b00;
        border:none;
        color:#0b1220;
      }

      .ctxextmat-table .btn-danger{
        background:#b91c1c;
        border:none;
        color:#fff;
      }

      .ctxextmat-table .btn-success{
        background:#087c3d;
        border:none;
        color:#fff;
      }

      .ctxextmat-table-wrap::-webkit-scrollbar{
        height:11px;
        width:11px;
      }

      .ctxextmat-table-wrap::-webkit-scrollbar-track{
        background:#dbe4f0;
        border-radius:12px;
      }

      .ctxextmat-table-wrap::-webkit-scrollbar-thumb{
        background:linear-gradient(180deg,#5aa3ea,#3f86d6);
        border-radius:12px;
        border:2px solid #dbe4f0;
      }

      .ctxextmat-table-wrap{
        scrollbar-width:thin;
        scrollbar-color:#3f86d6 #dbe4f0;
      }

      @media (max-width:992px){
        .ctxextmat-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .ctxextmat-header-card{
          min-height:88px;
          padding:15px 18px;
        }

        .ctxextmat-card-body{
          padding:12px 14px 14px 14px;
        }

        .ctxextmat-topbar{
          padding:12px 14px 0 14px;
        }

        .ctxextmat-title{
          font-size:1.22rem;
        }

        .ctxextmat-subtitle{
          font-size:.74rem;
        }
      }

      @media (max-width:768px){
        .ctxextmat-header-overlay{
          justify-content:center;
          text-align:center;
          flex-direction:column;
          gap:10px;
        }

        .ctxextmat-header-overlay::before{
          margin-right:0;
        }

        .ctxextmat-title{
          font-size:1.12rem;
        }

        .ctxextmat-subtitle{
          font-size:.72rem;
        }

        .ctxextmat-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(
        html,
        items=items,
        read_only=read_only,
        resumir_contexto_externo_texto=resumir_contexto_externo_texto,
        format_fecha_contexto_externo=format_fecha_contexto_externo
    )
    return render_template_string(BASE, content=Markup(inner))


# ==========================
# Detalle Contexto Externo
# ==========================
@app.route('/contexto_externo/detalle/<int:id>')
@login_required
def contexto_externo_detalle(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor':
        read_only = True
    else:
        if user.role != 'admin' and not verificar_permiso(user, "Contexto Externo"):
            flash("No tiene permiso para ver el detalle del contexto externo.", "danger")
            return redirect(url_for('contexto_externo_matriz'))
        read_only = False

    it = ContextoExterno.query.get_or_404(id)

    html = """
    <div class="ctxextd-shell">

      <div class="ctxextd-header-card">
        <div class="ctxextd-header-overlay">
          <div class="ctxextd-header-text">
            <h3 class="ctxextd-title m-0">Detalle — Contexto Externo</h3>
            <div class="ctxextd-subtitle">
              Consulta completa del registro en modo solo lectura
            </div>
          </div>
        </div>
      </div>

      <div class="ctxextd-header-actions">
        <a href="{{ url_for('contexto_externo_matriz') }}"
           class="btn rounded-pill px-4 fw-bold ctxextd-back-btn">
          ⬅ Volver a la Matriz
        </a>


        {% if not read_only %}
          <a href="{{ url_for('contexto_externo_edit', id=it.id) }}"
             class="btn btn-warning rounded-pill px-4 fw-bold">
            Editar registro
          </a>
        {% endif %}
      </div>

      <div class="ctxextd-card">
        <div class="ctxextd-card-body">

          <div class="ctxextd-section">
            <div class="ctxextd-section-title">Información principal</div>
            <div class="row g-3">
              <div class="col-md-8">
                <div class="ctxextd-field">
                  <div class="ctxextd-label">Categoría</div>
                  <div class="ctxextd-value ctxextd-value-lg">{{ it.categoria or '—' }}</div>
                </div>
              </div>

              <div class="col-md-4">
                <div class="ctxextd-field">
                  <div class="ctxextd-label">Fecha de Revisión</div>
                  <div class="ctxextd-value">{{ format_fecha_contexto_externo(it.fecha_revision) }}</div>
                </div>
              </div>

              <div class="col-md-12">
                <div class="ctxextd-field">
                  <div class="ctxextd-label">Descripción del factor externo</div>
                  <div class="ctxextd-value">{{ it.descripcion_factor or '—' }}</div>
                </div>
              </div>

              <div class="col-md-12">
                <div class="ctxextd-field">
                  <div class="ctxextd-label">Impacto en el SGSI</div>
                  <div class="ctxextd-value">{{ it.impacto_sgsi or '—' }}</div>
                </div>
              </div>
            </div>
          </div>

          <div class="ctxextd-section">
            <div class="ctxextd-section-title">Análisis externo</div>
            <div class="row g-3">
              <div class="col-md-6">
                <div class="ctxextd-field">
                  <div class="ctxextd-label">Oportunidades</div>
                  <div class="ctxextd-value">{{ it.oportunidades or '—' }}</div>
                </div>
              </div>

              <div class="col-md-6">
                <div class="ctxextd-field">
                  <div class="ctxextd-label">Amenazas</div>
                  <div class="ctxextd-value">{{ it.amenazas or '—' }}</div>
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

      .ctxextd-shell{
        width:96%;
        max-width:1250px;
        margin:10px auto 24px auto;
      }

      .ctxextd-header-card{
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

      .ctxextd-header-card::before{
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

      .ctxextd-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        padding:0;
        position:relative;
        z-index:1;
      }

      .ctxextd-header-overlay::before{
        content:"🌍";
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

      .ctxextd-header-text::before{
        content:"SGSI · Contexto Externo (Detalle)";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
      }

      .ctxextd-title{
        color:#fff !important;
        font-weight:950;
        font-size:1.32rem;
        margin:0 !important;
      }

      .ctxextd-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
      }

      .ctxextd-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px;
      }

      .ctxextd-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .ctxextd-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .ctxextd-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      .ctxextd-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        overflow:hidden;
        border:1px solid rgba(219,230,244,.9);
      }

      .ctxextd-card-body{
        padding:16px 18px;
      }

      .ctxextd-section{
        margin-bottom:14px;
        background:#ffffff;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:8px 7px;
        box-shadow:0 8px 18px rgba(15,23,42,.08);
      }

      .ctxextd-section:last-child{
        margin-bottom:0;
      }

      .ctxextd-section-title{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:0 0 12px 0;
      }

      .ctxextd-field{
        background:linear-gradient(180deg,#f8fbff 0%,#ffffff 100%);
        border:1px solid #dbe6f4;
        border-radius:14px;
        padding:12px;
        min-height:100%;
      }

      .ctxextd-label{
        font-size:.70rem;
        font-weight:900;
        text-transform:uppercase;
        letter-spacing:.35px;
        color:#0b4a8f;
        margin-bottom:6px;
      }

      .ctxextd-value{
        color:#101827;
        font-size:.82rem;
        line-height:1.38;
        white-space:pre-wrap;
        word-break:break-word;
      }

      .ctxextd-value-lg{
        font-size:.90rem;
        font-weight:900;
        color:#0f172a;
      }

      @media (max-width:992px){
        .ctxextd-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .ctxextd-header-card{
          min-height:88px;
          padding:15px 18px;
        }

        .ctxextd-title{
          font-size:1.2rem;
        }

        .ctxextd-card-body{
          padding:8px 7px;
        }

        .ctxextd-section{
          padding:12px;
        }
      }

      @media (max-width:768px){
        .ctxextd-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .ctxextd-header-overlay::before{
          margin:0;
        }

        .ctxextd-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(
        html,
        it=it,
        read_only=read_only,
        format_fecha_contexto_externo=format_fecha_contexto_externo
    )
    return render_template_string(BASE, content=Markup(inner))


# ==========================
# Editar
# ==========================
@app.route('/contexto_externo/edit/<int:id>', methods=['GET','POST'])
@login_required
def contexto_externo_edit(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor' or (
        user.role != 'admin' and not verificar_permiso(user, "Contexto Externo")
    ):
        flash("No tiene permiso para editar registros del contexto externo.", "danger")
        return redirect(url_for('contexto_externo_matriz'))

    item = ContextoExterno.query.get_or_404(id)

    if request.method == 'POST':
        item.categoria          = (request.form.get('categoria') or '').strip()
        item.descripcion_factor = (request.form.get('descripcion_factor') or '').strip()
        item.impacto_sgsi       = (request.form.get('impacto_sgsi') or '').strip()
        item.oportunidades      = (request.form.get('oportunidades') or '').strip()
        item.amenazas           = (request.form.get('amenazas') or '').strip()
        fecha_str               = (request.form.get('fecha_revision') or '').strip()

        if fecha_str:
            try:
                item.fecha_revision = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            except ValueError:
                flash("Fecha de revisión inválida.", "danger")
                return redirect(url_for('contexto_externo_edit', id=id))
        else:
            item.fecha_revision = None

        db.session.commit()
        flash("Registro actualizado.", "success")
        return redirect(url_for('contexto_externo_matriz'))

    html = """
    <div class="ctxexed-shell">

      <div class="ctxexed-header-card">
        <div class="ctxexed-header-overlay">
          <div class="ctxexed-header-text">
            <h3 class="ctxexed-title m-0">Editar Contexto Externo</h3>
            <div class="ctxexed-subtitle">
              Actualización de factores externos que afectan el Sistema de Gestión de Seguridad de la Información
            </div>
          </div>
        </div>
      </div>

      <div class="ctxexed-header-actions">
        <a href="{{ url_for('contexto_externo_matriz') }}"
           class="btn rounded-pill px-4 fw-bold ctxexed-back-btn">
          ⬅ Volver a la Matriz
        </a>

      </div>

      <div class="ctxexed-card">
        <div class="ctxexed-card-body">

          <form method="post">
            <div class="row g-3">

              <div class="col-md-4">
                <label class="form-label">Categoría</label>
                <input name="categoria"
                       class="form-control"
                       value="{{ item.categoria }}"
                       required>
              </div>

              <div class="col-md-8">
                <label class="form-label">Descripción del factor externo</label>
                <textarea name="descripcion_factor"
                          class="form-control"
                          rows="2"
                          required>{{ item.descripcion_factor }}</textarea>
              </div>

              <div class="col-md-12">
                <label class="form-label">Impacto en el SGSI</label>
                <textarea name="impacto_sgsi"
                          class="form-control"
                          rows="2"
                          required>{{ item.impacto_sgsi }}</textarea>
              </div>

              <div class="col-md-6">
                <label class="form-label">Oportunidades</label>
                <textarea name="oportunidades"
                          class="form-control"
                          rows="2">{{ item.oportunidades or "" }}</textarea>
              </div>

              <div class="col-md-6">
                <label class="form-label">Amenazas</label>
                <textarea name="amenazas"
                          class="form-control"
                          rows="2">{{ item.amenazas or "" }}</textarea>
              </div>

              <div class="col-md-3">
                <label class="form-label">Fecha de Revisión</label>
                <input type="date"
                       name="fecha_revision"
                       class="form-control"
                       value="{{ item.fecha_revision.strftime('%Y-%m-%d') if item.fecha_revision else '' }}">
              </div>

            </div>

            <div class="ctxexed-bottom-actions">
              <button class="btn btn-success rounded-pill px-4 fw-bold" type="submit">
                Guardar cambios
              </button>

              <a href="{{ url_for('contexto_externo_matriz') }}"
                 class="btn rounded-pill px-4 fw-bold ctxexed-cancel-btn">
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

      .ctxexed-shell{
        width:96%;
        max-width:1300px;
        margin:10px auto 24px auto;
      }

      /* =========================
         HERO SGSI UNIFICADO
      ========================== */
      .ctxexed-header-card{
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

      .ctxexed-header-card::before{
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

      .ctxexed-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        padding:0;
        position:relative;
        z-index:1;
      }

      .ctxexed-header-overlay::before{
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

      .ctxexed-header-text::before{
        content:"SGSI · Edición Contexto Externo";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
      }

      .ctxexed-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        margin:0 !important;
      }

      .ctxexed-subtitle{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:4px;
      }

      /* =========================
         ACCIONES
      ========================== */
      .ctxexed-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 12px;
      }

      .ctxexed-header-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .ctxexed-back-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .ctxexed-back-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         CARD FORMULARIO
      ========================== */
      .ctxexed-card{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
      }

      .ctxexed-card-body{
        padding:16px 18px;
      }

      /* =========================
         FORMULARIO COMPACTO
      ========================== */
      .ctxexed-card .form-label{
        font-weight:800;
        color:#25324a;
        margin-bottom:4px;
        font-size:.78rem;
      }

      .ctxexed-card .form-control,
      .ctxexed-card .form-select{
        border-radius:9px;
        border:1px solid #d9e3f0;
        min-height:37px;
        font-size:.80rem;
        background:#f8fafc;
      }

      .ctxexed-card textarea{
        min-height:70px;
        resize:vertical;
      }

      .ctxexed-card .form-control:focus,
      .ctxexed-card .form-select:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .18rem rgba(63,134,214,.18);
      }

      .ctxexed-card .row{
        row-gap:10px;
      }

      .ctxexed-card .mb-3{
        margin-bottom:.70rem !important;
      }

      /* =========================
         BOTONES
      ========================== */
      .ctxexed-bottom-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        margin-top:18px;
        flex-wrap:wrap;
      }

      .ctxexed-bottom-actions .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 24px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.14);
      }

      .ctxexed-bottom-actions .btn-primary,
      .ctxexed-bottom-actions .btn-success{
        border:none;
        background:linear-gradient(135deg,#086df0,#2487ff);
        color:#fff;
      }

      .ctxexed-bottom-actions .btn-danger{
        border:none;
        background:linear-gradient(135deg,#b91c1c,#ef4444);
        color:#fff;
      }

      .ctxexed-cancel-btn{
        background:#ffffff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        box-shadow:0 6px 14px rgba(0,0,0,.10);
      }

      .ctxexed-cancel-btn:hover{
        background:#edf5ff;
        color:#0b65d8;
        border-color:#9ec5fe;
      }

      /* =========================
         RESPONSIVE
      ========================== */
      @media (max-width:992px){
        .ctxexed-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .ctxexed-header-card{
          min-height:88px;
        }

        .ctxexed-title{
          font-size:1.2rem;
        }

        .ctxexed-card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .ctxexed-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .ctxexed-header-overlay::before{
          margin:0;
        }

        .ctxexed-bottom-actions .btn,
        .ctxexed-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """
    inner = render_template_string(html, item=item)
    return render_template_string(BASE, content=Markup(inner))


# ==========================
# Eliminar
# ==========================
@app.route('/contexto_externo/delete/<int:id>')
@login_required
def contexto_externo_delete(id):
    user = User.query.get(session.get('user_id'))

    if user.role == 'auditor' or (
        user.role != 'admin' and not verificar_permiso(user, "Contexto Externo")
    ):
        flash("No tiene permiso para eliminar registros del contexto externo.", "danger")
        return redirect(url_for('contexto_externo_matriz'))

    item = ContextoExterno.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash("Registro eliminado.", "success")
    return redirect(url_for('contexto_externo_matriz'))

# ==========================================================================================================================================
#                                                       Fin Módulo de Contexto Externo
# ==========================================================================================================================================

# ==========================================================================================================================================
#                                                               Módulo DOFA
# ==========================================================================================================================================

# ==========================
# DOFA
# ==========================

class DofaAnalisis(db.Model):
    __tablename__ = 'dofa_analisis'

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False, default="DOFA")
    fecha = db.Column(db.Date, nullable=False, default=date.today)

    fortalezas = db.Column(db.Text, nullable=True)
    debilidades = db.Column(db.Text, nullable=True)
    oportunidades = db.Column(db.Text, nullable=True)
    amenazas = db.Column(db.Text, nullable=True)

    estrategias_fo = db.Column(db.Text, nullable=True)
    estrategias_fa = db.Column(db.Text, nullable=True)
    estrategias_do = db.Column(db.Text, nullable=True)
    estrategias_da = db.Column(db.Text, nullable=True)

    creado_por = db.Column(db.String(80), nullable=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


# =================================
#   Entrada directa a listado DOFA
# =================================

@app.route('/dofa_menu')
@login_required
def dofa_menu():
    user = User.query.get(session.get('user_id'))

    if user.role not in ('admin', 'auditor') and not verificar_permiso(user, "DOFA"):
        flash("No tiene permiso para acceder al módulo DOFA.", "danger")
        return redirect(url_for('menu'))

    return redirect(url_for('dofa_list'))


def _autollenar_dofa_desde_contexto():
    internos = ContextoInterno.query.all()
    externos = ContextoExterno.query.all()

    fortalezas = []
    debilidades = []
    for r in internos:
        if r.fortalezas and r.fortalezas.strip():
            fortalezas.append(f"- {r.fortalezas.strip()}")
        if r.debilidades and r.debilidades.strip():
            debilidades.append(f"- {r.debilidades.strip()}")

    oportunidades = []
    amenazas = []
    for e in externos:
        op = (e.oportunidades or "").strip()
        am = (e.amenazas or "").strip()

        if op:
            oportunidades.append(f"- {op}")
        if am:
            amenazas.append(f"- {am}")

    return (
        "\n".join(fortalezas).strip(),
        "\n".join(debilidades).strip(),
        "\n".join(oportunidades).strip(),
        "\n".join(amenazas).strip(),
    )


# ==========================================
# Generación de estrategias DOFA con IA
# ==========================================

def _dofa_ai_clean(value, limit=9000):
    text_value = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    return text_value[:limit]


def _dofa_ai_normalize_strategy(value):
    if isinstance(value, list):
        items = []
        for item in value:
            item_text = _dofa_ai_clean(item, 1800)
            if item_text:
                items.append(item_text if item_text.startswith(("-", "•")) else f"- {item_text}")
        return "\n".join(items).strip()

    if isinstance(value, dict):
        items = []
        for item in value.values():
            item_text = _dofa_ai_clean(item, 1800)
            if item_text:
                items.append(item_text if item_text.startswith(("-", "•")) else f"- {item_text}")
        return "\n".join(items).strip()

    text_value = _dofa_ai_clean(value, 5000)
    text_value = re.sub(r"^\s*(?:ESTRATEGIAS?\s*)?(?:FO|FA|DO|DA)\s*[:\-]\s*", "", text_value, flags=re.I)
    return text_value.strip()


def _dofa_ai_extract_result(raw_text):
    raw_text = _dofa_ai_clean(raw_text, 20000)
    if not raw_text:
        raise ValueError("La IA no devolvió contenido.")

    cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.I)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    data = None
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        try:
            data = json.loads(cleaned[start:end + 1])
        except Exception:
            data = None

    if not isinstance(data, dict):
        # Respaldo para modelos que respondan con secciones FO / FA / DO / DA.
        section_pattern = re.compile(
            r"(?ims)^\s*(?:#{1,6}\s*)?(FO|FA|DO|DA)\s*(?:\([^)]*\))?\s*[:\-]\s*(.*?)(?=^\s*(?:#{1,6}\s*)?(?:FO|FA|DO|DA)\s*(?:\([^)]*\))?\s*[:\-]|\Z)"
        )
        sections = {}
        for match in section_pattern.finditer(cleaned):
            sections[match.group(1).lower()] = match.group(2).strip()
        if len(sections) == 4:
            data = sections

    if not isinstance(data, dict):
        raise ValueError("La IA no devolvió las cuatro estrategias en un formato válido.")

    aliases = {
        "estrategias_fo": ("estrategias_fo", "estrategia_fo", "fo", "FO"),
        "estrategias_fa": ("estrategias_fa", "estrategia_fa", "fa", "FA"),
        "estrategias_do": ("estrategias_do", "estrategia_do", "do", "DO"),
        "estrategias_da": ("estrategias_da", "estrategia_da", "da", "DA"),
    }

    result = {}
    for target, possible_keys in aliases.items():
        value = None
        for key in possible_keys:
            if key in data:
                value = data.get(key)
                break
        normalized = _dofa_ai_normalize_strategy(value)
        if not normalized:
            raise ValueError(f"La IA no generó contenido para {target.replace('estrategias_', '').upper()}.")
        result[target] = normalized

    return result


def _dofa_generate_strategies_with_ai(fortalezas, oportunidades, debilidades, amenazas):
    quadrants = {
        "fortalezas": _dofa_ai_clean(fortalezas),
        "oportunidades": _dofa_ai_clean(oportunidades),
        "debilidades": _dofa_ai_clean(debilidades),
        "amenazas": _dofa_ai_clean(amenazas),
    }

    missing_labels = {
        "fortalezas": "Fortalezas",
        "oportunidades": "Oportunidades",
        "debilidades": "Debilidades",
        "amenazas": "Amenazas",
    }
    missing = [missing_labels[key] for key, value in quadrants.items() if not value]
    if missing:
        raise ValueError(
            "Complete los cuatro cuadrantes antes de generar estrategias con IA. "
            "Falta información en: " + ", ".join(missing) + "."
        )

    expected_format = {
        "estrategias_fo": "- Estrategia 1\n- Estrategia 2",
        "estrategias_fa": "- Estrategia 1\n- Estrategia 2",
        "estrategias_do": "- Estrategia 1\n- Estrategia 2",
        "estrategias_da": "- Estrategia 1\n- Estrategia 2",
    }

    prompt = f"""
Genere estrategias cruzadas para una matriz DOFA de una organización, utilizando únicamente
la información proporcionada. No invente capacidades, tecnologías, contratos, certificaciones,
presupuestos, incidentes ni condiciones que no estén presentes en los cuadrantes.

Criterios:
- FO: utilizar fortalezas para aprovechar oportunidades.
- FA: utilizar fortalezas para reducir o afrontar amenazas.
- DO: superar debilidades aprovechando oportunidades.
- DA: reducir debilidades y evitar o mitigar amenazas.
- Genere exactamente dos estrategias concretas y accionables por cada cuadrante.
- Cada estrategia debe indicar una acción organizacional clara.
- Responda en español.
- No agregue explicaciones, encabezados ni texto fuera del JSON.
- Devuelva exclusivamente un objeto JSON válido con estas cuatro claves:
{json.dumps(expected_format, ensure_ascii=False, indent=2)}

MATRIZ DOFA:
{json.dumps(quadrants, ensure_ascii=False, indent=2)}
""".strip()

    raw_result = ai_text_general(
        prompt=prompt,
        system_prompt=(
            "Eres un consultor senior en planeación estratégica, gestión de riesgos y seguridad "
            "de la información. Genera estrategias DOFA realistas y responde solo JSON válido."
        ),
        temperature=0.2,
        max_tokens=350,
    )
    return _dofa_ai_extract_result(raw_result)


@app.route('/dofa/generar_estrategias_ia', methods=['POST'])
@login_required
def dofa_generar_estrategias_ia():
    user = User.query.get(session.get('user_id'))

    if not user:
        return jsonify(ok=False, message="La sesión de usuario no es válida."), 401

    if user.role not in ('admin', 'auditor') and not verificar_permiso(user, "DOFA"):
        return jsonify(ok=False, message="No tiene permiso para utilizar la IA del módulo DOFA."), 403

    if user.role == 'auditor':
        return jsonify(ok=False, message="Perfil auditor: solo lectura."), 403

    data = request.get_json(silent=True) or request.form.to_dict()

    try:
        strategies = _dofa_generate_strategies_with_ai(
            fortalezas=data.get("fortalezas"),
            oportunidades=data.get("oportunidades"),
            debilidades=data.get("debilidades"),
            amenazas=data.get("amenazas"),
        )

        try:
            registrar_log(
                user.username,
                "Generó estrategias FO, FA, DO y DA con IA en el módulo DOFA."
            )
        except Exception:
            pass

        return jsonify(
            ok=True,
            message=(
                "Estrategias generadas. Revise y edite el contenido antes de guardar la matriz DOFA."
            ),
            estrategias=strategies,
        )
    except ValueError as exc:
        return jsonify(ok=False, message=str(exc)), 400
    except Exception as exc:
        print("Error generando estrategias DOFA con IA:", repr(exc))
        return jsonify(
            ok=False,
            message=(
                "No fue posible generar las estrategias con IA. Verifique la configuración "
                "de OpenRouter u Ollama e inténtelo nuevamente."
            ),
        ), 500


# =================================
# Agregar DOFA
# =================================

