iso22301_madurez_bp = Blueprint("madurez_iso22301", __name__, url_prefix="/madurez_iso22301")

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage,
    PageBreak
)

# ============================================================
# BASE DE DATOS INDEPENDIENTE — ISO 22301
# ============================================================
ISO22301_DB_PATH = os.path.join(app.instance_path, "iso22301_madurez.db")
os.makedirs(app.instance_path, exist_ok=True)

app.config.setdefault("SQLALCHEMY_BINDS", {})
app.config["SQLALCHEMY_BINDS"]["iso22301_madurez"] = "sqlite:///" + ISO22301_DB_PATH

ISO22301_PERMISSION_NAME = "Nivel de Madurez ISO 22301"
ISO22301_INSTRUMENTO_TEMPLATE_XLSX = os.path.join(BASE_DIR, "static", "templates", "Arkyntech_Matriz_Madurez_ISO_22301_ES.xlsx")

ISO22301_STATUS_SCORE = {
    "SI": 100,
    "PARCIAL": 50,
    "NO": 0,
    "NA": 0,  # Valor visible 0; se excluye explícitamente del denominador.
}

ISO22301_BLOCK_ORDER = ["4", "5", "6", "7", "8", "9", "10"]

ISO22301_BLOCK_TITLES = {
    "4": "Contexto de la organización",
    "5": "Liderazgo",
    "6": "Planificación",
    "7": "Apoyo",
    "8": "Operación",
    "9": "Evaluación del desempeño",
    "10": "Mejora",
}

# Catálogo original de Arkyntech. Permite inicializar la base independiente
# incluso cuando el Excel todavía no se ha copiado a static/templates.
ISO22301_EMBEDDED_CATALOG = [{'item_id': 'BCP-001',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '4',
  'clause': '4.1',
  'domain_es': 'Contexto interno y externo',
  'assessment_question_es': 'La organización identifica las condiciones internas que pueden afectar su capacidad para mantener productos y '
                            'servicios prioritarios.',
  'suggested_evidence_es': 'Análisis de contexto, mapa de procesos, diagnóstico organizacional, actas de revisión.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-002',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '4',
  'clause': '4.1',
  'domain_es': 'Contexto interno y externo',
  'assessment_question_es': 'La organización identifica factores externos que pueden originar interrupciones o modificar sus necesidades '
                            'de continuidad.',
  'suggested_evidence_es': 'Análisis PESTEL, escenarios de amenaza, informes sectoriales y regulatorios.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-003',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '4',
  'clause': '4.1',
  'domain_es': 'Contexto interno y externo',
  'assessment_question_es': 'Los temas de continuidad se relacionan explícitamente con la estrategia, los objetivos y el apetito de riesgo '
                            'de la organización.',
  'suggested_evidence_es': 'Plan estratégico, declaración de apetito de riesgo, mapa de objetivos.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-004',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '4',
  'clause': '4.1',
  'domain_es': 'Contexto interno y externo',
  'assessment_question_es': 'Se revisan periódicamente los cambios del contexto y sus efectos sobre el sistema de continuidad.',
  'suggested_evidence_es': 'Calendario de revisión, actas, registro de cambios y decisiones.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-005',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '4',
  'clause': '4.1',
  'domain_es': 'Cambio climático — Enmienda 2024',
  'assessment_question_es': 'Se ha evaluado y documentado si el cambio climático es un asunto pertinente para la continuidad del negocio.',
  'suggested_evidence_es': 'Evaluación de pertinencia climática, escenarios físicos y de transición, conclusión aprobada.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-006',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '4',
  'clause': '4.2',
  'domain_es': 'Partes interesadas',
  'assessment_question_es': 'Se mantienen identificadas las partes interesadas relevantes para la continuidad del negocio.',
  'suggested_evidence_es': 'Matriz de partes interesadas y responsables de relación.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-007',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '4',
  'clause': '4.2',
  'domain_es': 'Necesidades y expectativas',
  'assessment_question_es': 'Se conocen y actualizan las necesidades de continuidad de clientes, autoridades, empleados, proveedores y '
                            'socios críticos.',
  'suggested_evidence_es': 'Matriz de requisitos, contratos, SLA, comunicaciones y encuestas.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-008',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '4',
  'clause': '4.2.2',
  'domain_es': 'Requisitos legales y regulatorios',
  'assessment_question_es': 'Existe un inventario vigente de obligaciones legales, regulatorias y contractuales relacionadas con '
                            'continuidad.',
  'suggested_evidence_es': 'Matriz legal, circulares regulatorias, contratos, concepto jurídico.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-009',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '4',
  'clause': '4.2.2',
  'domain_es': 'Cumplimiento',
  'assessment_question_es': 'Se asignan responsables y mecanismos para evaluar el cumplimiento de las obligaciones de continuidad.',
  'suggested_evidence_es': 'Evaluaciones de cumplimiento, responsables, hallazgos y planes de cierre.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-010',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '4',
  'clause': '4.2',
  'domain_es': 'Cambio climático — Enmienda 2024',
  'assessment_question_es': 'Se consideran requisitos o expectativas de partes interesadas relacionados con cambio climático cuando '
                            'resultan pertinentes.',
  'suggested_evidence_es': 'Matriz de interesados, compromisos ESG, contratos, exigencias de autoridades o clientes.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-011',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '4',
  'clause': '4.3',
  'domain_es': 'Alcance del SGCN',
  'assessment_question_es': 'El alcance define límites organizacionales, ubicaciones, procesos, productos, servicios y dependencias '
                            'incluidos.',
  'suggested_evidence_es': 'Declaración de alcance aprobada y mapa de cobertura.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-012',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '4',
  'clause': '4.3',
  'domain_es': 'Alcance del SGCN',
  'assessment_question_es': 'La definición del alcance utiliza el contexto, las obligaciones y las necesidades de las partes interesadas.',
  'suggested_evidence_es': 'Trazabilidad del alcance con análisis de contexto y matriz de requisitos.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-013',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '4',
  'clause': '4.3',
  'domain_es': 'Alcance del SGCN',
  'assessment_question_es': 'Las interfaces con procesos, sedes, terceros y servicios fuera del alcance están identificadas y gestionadas.',
  'suggested_evidence_es': 'Mapa de interfaces, contratos, RACI y dependencias.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-014',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '4',
  'clause': '4.3',
  'domain_es': 'Alcance del SGCN',
  'assessment_question_es': 'La declaración de alcance está documentada, aprobada, disponible y sujeta a control de cambios.',
  'suggested_evidence_es': 'Documento vigente, aprobación, historial de versiones y publicación interna.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-015',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '4',
  'clause': '4.4',
  'domain_es': 'Sistema de gestión',
  'assessment_question_es': 'Los procesos necesarios del sistema de continuidad y sus interacciones están definidos.',
  'suggested_evidence_es': 'Mapa de procesos del SGCN, fichas de proceso y entradas/salidas.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-016',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '4',
  'clause': '4.4',
  'domain_es': 'Sistema de gestión',
  'assessment_question_es': 'Se asignan criterios, métodos, responsables y recursos para operar y controlar el sistema de continuidad.',
  'suggested_evidence_es': 'Procedimientos, indicadores, RACI, presupuesto y cronograma.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-017',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '4',
  'clause': '4.4',
  'domain_es': 'Sistema de gestión',
  'assessment_question_es': 'El sistema se mantiene y mejora con base en resultados, cambios, incidentes y lecciones aprendidas.',
  'suggested_evidence_es': 'Plan de mejora, revisiones, informes de incidentes y seguimiento.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-018',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '5',
  'clause': '5.1',
  'domain_es': 'Liderazgo y compromiso',
  'assessment_question_es': 'La alta dirección asume responsabilidad por la eficacia del sistema de continuidad.',
  'suggested_evidence_es': 'Actas de comité, decisiones, asignación de responsables y seguimiento ejecutivo.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-019',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '5',
  'clause': '5.1',
  'domain_es': 'Integración',
  'assessment_question_es': 'Los requisitos de continuidad están integrados en procesos de negocio, proyectos, cambios y decisiones '
                            'relevantes.',
  'suggested_evidence_es': 'Metodologías corporativas, controles de proyecto y criterios de aprobación.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-020',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '5',
  'clause': '5.1',
  'domain_es': 'Recursos y apoyo',
  'assessment_question_es': 'La alta dirección asegura recursos suficientes para establecer, operar, probar y mejorar la continuidad.',
  'suggested_evidence_es': 'Presupuesto, capacidad de personal, herramientas, contratos y aprobaciones.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-021',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '5',
  'clause': '5.1',
  'domain_es': 'Comunicación directiva',
  'assessment_question_es': 'Los líderes comunican la importancia de una continuidad eficaz y del cumplimiento de los compromisos '
                            'definidos.',
  'suggested_evidence_es': 'Comunicaciones, sesiones ejecutivas, campañas y registros de asistencia.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-022',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '5',
  'clause': '5.1',
  'domain_es': 'Resultados',
  'assessment_question_es': 'La dirección promueve el logro de resultados, la colaboración entre áreas y la mejora continua.',
  'suggested_evidence_es': 'Indicadores, compromisos de áreas, actas y reconocimientos o acciones correctivas.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-023',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '5',
  'clause': '5.2',
  'domain_es': 'Política de continuidad',
  'assessment_question_es': 'Existe una política adecuada al propósito, contexto y dirección estratégica de la organización.',
  'suggested_evidence_es': 'Política vigente, aprobación y relación con estrategia y alcance.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-024',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '5',
  'clause': '5.2',
  'domain_es': 'Política de continuidad',
  'assessment_question_es': 'La política incluye compromisos de cumplimiento de requisitos y mejora continua.',
  'suggested_evidence_es': 'Texto de la política y evidencias de aprobación.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-025',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '5',
  'clause': '5.2',
  'domain_es': 'Política de continuidad',
  'assessment_question_es': 'La política proporciona un marco para definir y revisar objetivos de continuidad.',
  'suggested_evidence_es': 'Trazabilidad entre política, objetivos, indicadores y planes.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-026',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '5',
  'clause': '5.2.2',
  'domain_es': 'Comunicación de la política',
  'assessment_question_es': 'La política está disponible, se comunica dentro de la organización y se comparte externamente cuando '
                            'corresponde.',
  'suggested_evidence_es': 'Intranet, inducción, comunicaciones a terceros y evidencia de acceso.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-027',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '5',
  'clause': '5.3',
  'domain_es': 'Roles y autoridades',
  'assessment_question_es': 'Se asignan y comunican responsabilidades y autoridades para los roles del sistema de continuidad.',
  'suggested_evidence_es': 'RACI, perfiles de cargo, nombramientos y comunicaciones.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-028',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '5',
  'clause': '5.3',
  'domain_es': 'Gobierno del SGCN',
  'assessment_question_es': 'Existe una instancia de gobierno con autoridad para decidir, escalar y supervisar el desempeño del sistema.',
  'suggested_evidence_es': 'Términos de referencia del comité, calendario, actas y decisiones.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-029',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '5',
  'clause': '5.3',
  'domain_es': 'Reporte a la dirección',
  'assessment_question_es': 'Está definida la responsabilidad de informar a la alta dirección sobre desempeño, brechas y oportunidades de '
                            'mejora.',
  'suggested_evidence_es': 'Informes ejecutivos, tablero, frecuencia y destinatarios.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-030',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '6',
  'clause': '6.1',
  'domain_es': 'Riesgos y oportunidades del SGCN',
  'assessment_question_es': 'Se determinan riesgos que podrían impedir que el sistema logre los resultados previstos.',
  'suggested_evidence_es': 'Registro de riesgos del SGCN, causas, consecuencias y controles.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-031',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '6',
  'clause': '6.1',
  'domain_es': 'Riesgos y oportunidades del SGCN',
  'assessment_question_es': 'Se identifican oportunidades para fortalecer la resiliencia y mejorar el sistema.',
  'suggested_evidence_es': 'Registro de oportunidades, iniciativas, responsables y beneficios esperados.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-032',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '6',
  'clause': '6.1',
  'domain_es': 'Tratamiento',
  'assessment_question_es': 'Las acciones para tratar riesgos y oportunidades están integradas en procesos y planes de trabajo.',
  'suggested_evidence_es': 'Planes de tratamiento, portafolio de iniciativas y seguimiento.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-033',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '6',
  'clause': '6.1',
  'domain_es': 'Evaluación de eficacia',
  'assessment_question_es': 'Se evalúa si las acciones tomadas frente a riesgos y oportunidades fueron eficaces.',
  'suggested_evidence_es': 'Indicadores, revisiones, resultados de pruebas y cierre de acciones.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-034',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '6',
  'clause': '6.2',
  'domain_es': 'Objetivos de continuidad',
  'assessment_question_es': 'Se establecen objetivos coherentes con la política y pertinentes para las funciones y niveles aplicables.',
  'suggested_evidence_es': 'Matriz de objetivos, aprobación y despliegue por áreas.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-035',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '6',
  'clause': '6.2',
  'domain_es': 'Objetivos de continuidad',
  'assessment_question_es': 'Los objetivos son medibles cuando es posible, se monitorean y se actualizan según necesidad.',
  'suggested_evidence_es': 'Indicadores, metas, periodicidad, resultados y revisiones.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-036',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '6',
  'clause': '6.2',
  'domain_es': 'Planificación de objetivos',
  'assessment_question_es': 'Cada objetivo define actividades, recursos, responsable, plazo y método para evaluar resultados.',
  'suggested_evidence_es': 'Ficha de objetivo, plan de trabajo, presupuesto y criterio de éxito.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-037',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '6',
  'clause': '6.2',
  'domain_es': 'Comunicación de objetivos',
  'assessment_question_es': 'Los objetivos se comunican a las personas y partes relevantes para su cumplimiento.',
  'suggested_evidence_es': 'Comunicaciones, tableros, reuniones y compromisos.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-038',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '6',
  'clause': '6.3',
  'domain_es': 'Cambios del SGCN',
  'assessment_question_es': 'Los cambios del sistema se planifican considerando propósito, consecuencias, integridad, recursos y '
                            'responsabilidades.',
  'suggested_evidence_es': 'Procedimiento de cambios, análisis de impacto y aprobaciones.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-039',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '7',
  'clause': '7.1',
  'domain_es': 'Recursos',
  'assessment_question_es': 'Se identifican y proveen recursos humanos, tecnológicos, físicos, financieros y de información para el SGCN.',
  'suggested_evidence_es': 'Plan de recursos, presupuesto, inventarios y contratos.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-040',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '7',
  'clause': '7.1',
  'domain_es': 'Disponibilidad de recursos',
  'assessment_question_es': 'Los recursos críticos de respuesta y recuperación están disponibles dentro de los tiempos requeridos.',
  'suggested_evidence_es': 'Pruebas de disponibilidad, inventarios, acuerdos y tiempos de activación.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-041',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '7',
  'clause': '7.2',
  'domain_es': 'Competencia',
  'assessment_question_es': 'Se han definido las competencias requeridas para roles que afectan el desempeño de continuidad.',
  'suggested_evidence_es': 'Perfiles, matriz de competencias y roles de crisis.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-042',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '7',
  'clause': '7.2',
  'domain_es': 'Competencia',
  'assessment_question_es': 'Las personas asignadas demuestran competencia mediante formación, experiencia o evaluación.',
  'suggested_evidence_es': 'Certificados, experiencia, evaluaciones y observación en ejercicios.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-043',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '7',
  'clause': '7.2',
  'domain_es': 'Desarrollo de capacidades',
  'assessment_question_es': 'Se ejecutan acciones para cerrar brechas de competencia y se evalúa su eficacia.',
  'suggested_evidence_es': 'Plan de formación, resultados, evaluaciones y mejoras.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-044',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '7',
  'clause': '7.3',
  'domain_es': 'Conciencia',
  'assessment_question_es': 'El personal conoce la política, su contribución a la continuidad y las consecuencias de no cumplir los '
                            'procedimientos.',
  'suggested_evidence_es': 'Inducciones, campañas, encuestas y pruebas de conocimiento.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-045',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '7',
  'clause': '7.3',
  'domain_es': 'Conciencia',
  'assessment_question_es': 'Las personas conocen su papel antes, durante y después de una interrupción.',
  'suggested_evidence_es': 'Tarjetas de rol, guías rápidas, simulacros y confirmaciones.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-046',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '7',
  'clause': '7.4',
  'domain_es': 'Comunicación',
  'assessment_question_es': 'Existe un plan que define qué, cuándo, con quién, cómo y quién comunica asuntos de continuidad.',
  'suggested_evidence_es': 'Plan de comunicación, matriz de contactos y vocerías.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-047',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '7',
  'clause': '7.4',
  'domain_es': 'Comunicación',
  'assessment_question_es': 'Los canales de comunicación de crisis cuentan con alternativas y mecanismos de escalamiento.',
  'suggested_evidence_es': 'Árbol de llamadas, canales alternos, pruebas y protocolos.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-048',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '7',
  'clause': '7.4',
  'domain_es': 'Comunicación',
  'assessment_question_es': 'La comunicación con autoridades, medios, clientes, proveedores y otras partes relevantes está prevista.',
  'suggested_evidence_es': 'Plantillas, directorio, criterios de notificación y voceros.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-049',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '7',
  'clause': '7.5',
  'domain_es': 'Información documentada',
  'assessment_question_es': 'Se determinan los documentos y registros necesarios para operar y demostrar la eficacia del sistema.',
  'suggested_evidence_es': 'Listado maestro, arquitectura documental y matriz de registros.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-050',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '7',
  'clause': '7.5',
  'domain_es': 'Control documental',
  'assessment_question_es': 'Los documentos se identifican, revisan, aprueban, actualizan y distribuyen de forma controlada.',
  'suggested_evidence_es': 'Procedimiento documental, versiones, aprobaciones y permisos.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-051',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '7',
  'clause': '7.5',
  'domain_es': 'Protección documental',
  'assessment_question_es': 'La información de continuidad se protege, conserva, recupera y elimina de acuerdo con reglas definidas.',
  'suggested_evidence_es': 'Controles de acceso, respaldos, retención y eliminación segura.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-052',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.1',
  'domain_es': 'Planificación y control operacional',
  'assessment_question_es': 'Se planifican y controlan los procesos necesarios para cumplir requisitos y ejecutar las acciones del SGCN.',
  'suggested_evidence_es': 'Planes operativos, criterios de aceptación, controles y registros.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-053',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.1',
  'domain_es': 'Cambios operacionales',
  'assessment_question_es': 'Los cambios planificados se controlan y los cambios no previstos se revisan para reducir efectos adversos.',
  'suggested_evidence_es': 'Registros de cambio, evaluación de impacto y acciones de mitigación.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-054',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.1',
  'domain_es': 'Procesos tercerizados',
  'assessment_question_es': 'Los procesos y servicios externos relevantes para continuidad están sujetos a controles definidos.',
  'suggested_evidence_es': 'Contratos, SLA, evaluaciones de proveedor, planes y pruebas conjuntas.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-055',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.2.1',
  'domain_es': 'BIA y evaluación de riesgos',
  'assessment_question_es': 'Existe un proceso formal, vigente y consistente para el análisis de impacto y la evaluación de riesgos de '
                            'interrupción.',
  'suggested_evidence_es': 'Metodología aprobada, calendario, responsables y resultados.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-056',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.2.2',
  'domain_es': 'Análisis de impacto al negocio',
  'assessment_question_es': 'El BIA identifica actividades que soportan productos y servicios priorizados dentro del alcance.',
  'suggested_evidence_es': 'Inventario de productos, servicios, procesos y actividades priorizadas.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-057',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.2.2',
  'domain_es': 'Impactos',
  'assessment_question_es': 'El BIA evalúa tipos de impacto y cómo aumentan con el tiempo después de una interrupción.',
  'suggested_evidence_es': 'Escalas de impacto, curvas temporales, criterios financieros, legales, operativos y reputacionales.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-058',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.2.2',
  'domain_es': 'Tiempos objetivo',
  'assessment_question_es': 'Se establecen y justifican los tiempos máximos tolerables, objetivos de recuperación y puntos objetivo de '
                            'recuperación cuando aplican.',
  'suggested_evidence_es': 'MTPD/MAO, RTO, RPO, criterios, aprobaciones y trazabilidad.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-059',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.2.2',
  'domain_es': 'Capacidad mínima',
  'assessment_question_es': 'Se define la capacidad mínima aceptable y el momento en que debe recuperarse cada actividad priorizada.',
  'suggested_evidence_es': 'Niveles mínimos de servicio, capacidad, volumen y cronograma de recuperación.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-060',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.2.2',
  'domain_es': 'Recursos y dependencias',
  'assessment_question_es': 'El BIA identifica personas, tecnología, datos, instalaciones, proveedores y otras dependencias necesarias.',
  'suggested_evidence_es': 'Mapa de dependencias, recursos mínimos y puntos únicos de falla.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-061',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.2.2',
  'domain_es': 'Interdependencias',
  'assessment_question_es': 'Se analizan dependencias entre procesos y se define una secuencia viable de recuperación.',
  'suggested_evidence_es': 'Mapa de interdependencias, cadena de recuperación y validación de áreas.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-062',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.2.2',
  'domain_es': 'Aprobación y actualización del BIA',
  'assessment_question_es': 'Los resultados del BIA son validados por dueños de negocio, aprobados y revisados ante cambios '
                            'significativos.',
  'suggested_evidence_es': 'Firmas, actas, versión vigente, disparadores y calendario de revisión.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-063',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.2.3',
  'domain_es': 'Riesgos de interrupción',
  'assessment_question_es': 'Se identifican amenazas, vulnerabilidades y escenarios que pueden interrumpir actividades priorizadas.',
  'suggested_evidence_es': 'Registro de escenarios, talleres, inteligencia de amenazas y análisis de vulnerabilidad.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-064',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.2.3',
  'domain_es': 'Análisis y evaluación',
  'assessment_question_es': 'Los riesgos de interrupción se analizan y evalúan con criterios consistentes y aprobados.',
  'suggested_evidence_es': 'Metodología, escalas, resultados, aceptación y priorización.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-065',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.2.3',
  'domain_es': 'Tratamiento y riesgo residual',
  'assessment_question_es': 'Se determinan controles, responsables, plazos y aceptación del riesgo residual.',
  'suggested_evidence_es': 'Plan de tratamiento, controles, aprobaciones y seguimiento.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-066',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.3.1',
  'domain_es': 'Estrategias y soluciones',
  'assessment_question_es': 'Las estrategias de continuidad se basan en los resultados del BIA y de la evaluación de riesgos.',
  'suggested_evidence_es': 'Trazabilidad BIA-riesgos-estrategias y criterios de decisión.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-067',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.3.2',
  'domain_es': 'Opciones de estrategia',
  'assessment_question_es': 'Se identifican opciones para antes, durante y después de una interrupción, incluyendo prevención, respuesta y '
                            'recuperación.',
  'suggested_evidence_es': 'Catálogo de opciones, escenarios, ventajas, limitaciones y costos.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-068',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.3.3',
  'domain_es': 'Selección de soluciones',
  'assessment_question_es': 'Las soluciones se seleccionan considerando tiempos objetivo, capacidad, riesgos, costos, beneficios y '
                            'obligaciones.',
  'suggested_evidence_es': 'Análisis multicriterio, caso de negocio y aprobación.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-069',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.3.3',
  'domain_es': 'Adecuación de soluciones',
  'assessment_question_es': 'Las soluciones seleccionadas son viables frente a escenarios severos pero plausibles.',
  'suggested_evidence_es': 'Pruebas de capacidad, análisis de estrés y supuestos documentados.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-070',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.3.4',
  'domain_es': 'Requisitos de recursos',
  'assessment_question_es': 'Se determinan los recursos necesarios para implementar las soluciones de continuidad.',
  'suggested_evidence_es': 'Requisitos de personal, instalaciones, TIC, datos, transporte, finanzas y proveedores.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-071',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.3.4',
  'domain_es': 'Proveedores y cadena de suministro',
  'assessment_question_es': 'Se establecen requisitos de continuidad para proveedores críticos y se verifica su capacidad.',
  'suggested_evidence_es': 'Cláusulas, cuestionarios, certificaciones, planes y resultados de pruebas.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-072',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.3.5',
  'domain_es': 'Implementación de soluciones',
  'assessment_question_es': 'Las soluciones aprobadas se implementan, mantienen y controlan con responsables y recursos definidos.',
  'suggested_evidence_es': 'Plan de implementación, entregables, responsables y evidencia operativa.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-073',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.3.5',
  'domain_es': 'Capacidad técnica',
  'assessment_question_es': 'La infraestructura y los mecanismos de recuperación cumplen los objetivos establecidos.',
  'suggested_evidence_es': 'Pruebas técnicas, capacidad, replicación, respaldos y tiempos reales.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-074',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.4.1',
  'domain_es': 'Planes y procedimientos',
  'assessment_question_es': 'Los planes permiten gestionar una interrupción y continuar o recuperar actividades priorizadas.',
  'suggested_evidence_es': 'Planes vigentes, procedimientos, listas de verificación y anexos.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-075',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.4.1',
  'domain_es': 'Características de los planes',
  'assessment_question_es': 'Los planes son específicos, flexibles, accesibles, comprensibles y utilizables bajo presión.',
  'suggested_evidence_es': 'Revisión de calidad, copias alternas, accesibilidad y pruebas de uso.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-076',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.4.2',
  'domain_es': 'Estructura de respuesta',
  'assessment_question_es': 'Existe una estructura de respuesta con niveles de autoridad, roles, suplencias y criterios de escalamiento.',
  'suggested_evidence_es': 'Organigrama de crisis, RACI, delegaciones y tarjetas de rol.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-077',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.4.2',
  'domain_es': 'Activación y desactivación',
  'assessment_question_es': 'Se definen criterios y responsables para activar, escalar, mantener y desactivar la respuesta.',
  'suggested_evidence_es': 'Matriz de activación, umbrales, autoridad y registro de decisiones.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-078',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.4.2',
  'domain_es': 'Gestión estratégica, táctica y operativa',
  'assessment_question_es': 'La estructura coordina decisiones estratégicas, tácticas y operativas durante una interrupción.',
  'suggested_evidence_es': 'Protocolos de coordinación, salas de crisis y cadencia de reuniones.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-079',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.4.3',
  'domain_es': 'Alerta y comunicación',
  'assessment_question_es': 'Se dispone de procedimientos para detectar, alertar, notificar y movilizar a los equipos relevantes.',
  'suggested_evidence_es': 'Monitoreo, alarmas, árbol de llamadas, pruebas y registros.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-080',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.4.3',
  'domain_es': 'Comunicación de crisis',
  'assessment_question_es': 'Los mensajes se preparan, autorizan, emiten y registran con control de consistencia y oportunidad.',
  'suggested_evidence_es': 'Plantillas, aprobaciones, registro de comunicaciones y monitoreo de medios.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-081',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.4.3',
  'domain_es': 'Interoperabilidad',
  'assessment_question_es': 'Los mecanismos de comunicación son compatibles con los de autoridades, respondedores y socios cuando aplica.',
  'suggested_evidence_es': 'Protocolos conjuntos, directorios, pruebas y acuerdos.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-082',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.4.4',
  'domain_es': 'Contenido del plan',
  'assessment_question_es': 'Cada plan define propósito, alcance, objetivos, criterios de activación, roles, acciones y recursos.',
  'suggested_evidence_es': 'Plan aprobado y lista de contenidos mínimos.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-083',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.4.4',
  'domain_es': 'Procedimientos de continuidad',
  'assessment_question_es': 'Los procedimientos detallan cómo operar a capacidad aceptable y cómo priorizar recursos durante la '
                            'interrupción.',
  'suggested_evidence_es': 'Procedimientos alternos, capacidad mínima y secuencia de actividades.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-084',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.4.4',
  'domain_es': 'Dependencias y terceros',
  'assessment_question_es': 'Los planes incorporan dependencias internas y externas, contactos y compromisos de terceros críticos.',
  'suggested_evidence_es': 'Anexos de dependencias, contactos, SLA y acuerdos de apoyo.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-085',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.4.4',
  'domain_es': 'Información vital',
  'assessment_question_es': 'La información esencial para ejecutar los planes está disponible, protegida y actualizada.',
  'suggested_evidence_es': 'Repositorios alternos, copias offline, control de acceso y versiones.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-086',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.4.5',
  'domain_es': 'Recuperación y retorno',
  'assessment_question_es': 'Se planifica la transición desde la respuesta hasta la recuperación y el retorno controlado a la operación '
                            'normal.',
  'suggested_evidence_es': 'Plan de retorno, criterios de estabilidad, validaciones y aceptación del negocio.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-087',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.4.5',
  'domain_es': 'Restauración priorizada',
  'assessment_question_es': 'La recuperación respeta los tiempos, la secuencia y la capacidad definidos por el BIA.',
  'suggested_evidence_es': 'Cronograma de recuperación, resultados de pruebas y trazabilidad con RTO/RPO.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-088',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.5',
  'domain_es': 'Programa de ejercicios',
  'assessment_question_es': 'Existe un programa de ejercicios alineado con alcance, riesgos, capacidades y objetivos de continuidad.',
  'suggested_evidence_es': 'Programa anual/plurianual, cobertura y aprobación.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-089',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.5',
  'domain_es': 'Tipos y escenarios',
  'assessment_question_es': 'Los ejercicios incluyen diferentes métodos y escenarios relevantes, progresivos y suficientemente exigentes.',
  'suggested_evidence_es': 'Ejercicios de escritorio, simulaciones, pruebas técnicas e integrales.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-090',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.5',
  'domain_es': 'Participación',
  'assessment_question_es': 'Participan las áreas, directivos, sedes y terceros necesarios para validar la capacidad de extremo a extremo.',
  'suggested_evidence_es': 'Listas de participantes, alcance, invitaciones y resultados.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-091',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.5',
  'domain_es': 'Criterios y seguridad',
  'assessment_question_es': 'Cada ejercicio define objetivos, criterios de éxito, controles de riesgo y reglas para evitar impactos no '
                            'deseados.',
  'suggested_evidence_es': 'Guion, plan de prueba, criterios, autorizaciones y plan de reversa.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-092',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.5',
  'domain_es': 'Resultados y mejoras',
  'assessment_question_es': 'Los ejercicios generan resultados documentados, lecciones, acciones, responsables y fechas de cierre.',
  'suggested_evidence_es': 'Informe de ejercicio, evidencias, plan de acción y seguimiento.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-093',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.5',
  'domain_es': 'Validación de capacidades',
  'assessment_question_es': 'Los resultados demuestran si las soluciones y planes alcanzan los tiempos y capacidades requeridos.',
  'suggested_evidence_es': 'Tiempos reales, volumen recuperado, desviaciones y aceptación del negocio.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-094',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.6',
  'domain_es': 'Evaluación documental y de capacidades',
  'assessment_question_es': 'Los planes, procedimientos y capacidades se revisan con una frecuencia definida y después de cambios o '
                            'incidentes.',
  'suggested_evidence_es': 'Calendario de revisión, disparadores, actas y versiones.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-095',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.6',
  'domain_es': 'Conformidad y vigencia',
  'assessment_question_es': 'La evaluación confirma que los elementos de continuidad siguen siendo adecuados, suficientes y eficaces.',
  'suggested_evidence_es': 'Revisiones cruzadas, listas de verificación y aprobaciones.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-096',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '8',
  'clause': '8.6',
  'domain_es': 'Lecciones aprendidas',
  'assessment_question_es': 'Los resultados de incidentes, ejercicios y evaluaciones se incorporan a planes, estrategias y formación.',
  'suggested_evidence_es': 'Registro de lecciones, cambios implementados y validación posterior.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-097',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '9',
  'clause': '9.1',
  'domain_es': 'Seguimiento y medición',
  'assessment_question_es': 'Se define qué medir, cómo medir, cuándo analizar y quién evalúa el desempeño del SGCN.',
  'suggested_evidence_es': 'Ficha de indicadores, fuentes, responsables y periodicidad.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-098',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '9',
  'clause': '9.1',
  'domain_es': 'Indicadores',
  'assessment_question_es': 'Los indicadores cubren preparación, capacidad, ejercicios, incidentes, acciones y cumplimiento de objetivos.',
  'suggested_evidence_es': 'Tablero de indicadores, metas, tendencias y umbrales.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-099',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '9',
  'clause': '9.1',
  'domain_es': 'Análisis y evaluación',
  'assessment_question_es': 'Los resultados se analizan para determinar eficacia, tendencias, desviaciones y necesidad de acciones.',
  'suggested_evidence_es': 'Informes de desempeño, análisis de causa y decisiones.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-100',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '9',
  'clause': '9.1',
  'domain_es': 'Evidencia de resultados',
  'assessment_question_es': 'Se conserva información documentada suficiente para demostrar los resultados del seguimiento y la evaluación.',
  'suggested_evidence_es': 'Registros, reportes, trazabilidad de datos y retención.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-101',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '9',
  'clause': '9.2.1',
  'domain_es': 'Auditoría interna',
  'assessment_question_es': 'Se realizan auditorías internas planificadas para evaluar conformidad y eficacia del sistema.',
  'suggested_evidence_es': 'Programa, planes, listas de verificación, informes y evidencias.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-102',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '9',
  'clause': '9.2.2',
  'domain_es': 'Programa de auditoría',
  'assessment_question_es': 'El programa considera importancia de procesos, cambios, riesgos y resultados de auditorías anteriores.',
  'suggested_evidence_es': 'Criterios de priorización, cobertura, frecuencia y cronograma.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-103',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '9',
  'clause': '9.2.2',
  'domain_es': 'Independencia y competencia',
  'assessment_question_es': 'Los auditores son competentes y mantienen objetividad e imparcialidad frente al trabajo auditado.',
  'suggested_evidence_es': 'Competencias, asignaciones, declaración de independencia y revisión.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-104',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '9',
  'clause': '9.2.2',
  'domain_es': 'Resultados de auditoría',
  'assessment_question_es': 'Los resultados se comunican a responsables pertinentes y se da seguimiento oportuno a las acciones.',
  'suggested_evidence_es': 'Informe, distribución, plan de acción y verificación de cierre.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-105',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '9',
  'clause': '9.3',
  'domain_es': 'Revisión por la dirección',
  'assessment_question_es': 'La alta dirección revisa el SGCN a intervalos planificados.',
  'suggested_evidence_es': 'Calendario, convocatoria, actas y participantes.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-106',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '9',
  'clause': '9.3.2',
  'domain_es': 'Entradas de revisión',
  'assessment_question_es': 'La revisión considera cambios, desempeño, auditorías, incidentes, ejercicios, riesgos, recursos y acciones '
                            'previas.',
  'suggested_evidence_es': 'Agenda, paquete de información y presentación ejecutiva.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-107',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '9',
  'clause': '9.3.2',
  'domain_es': 'Necesidades y oportunidades',
  'assessment_question_es': 'La revisión analiza oportunidades de mejora y necesidades de cambio, recursos o actualización del sistema.',
  'suggested_evidence_es': 'Análisis de brechas, propuestas, decisiones y priorización.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-108',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '9',
  'clause': '9.3.3',
  'domain_es': 'Salidas de revisión',
  'assessment_question_es': 'Las decisiones y acciones de la revisión quedan documentadas con responsables y plazos.',
  'suggested_evidence_es': 'Acta, decisiones, plan de acción y seguimiento.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-109',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '10',
  'clause': '10.1',
  'domain_es': 'No conformidad',
  'assessment_question_es': 'Las no conformidades e incidentes originan acciones para controlar, corregir y atender sus consecuencias.',
  'suggested_evidence_es': 'Registro de no conformidad, contención, corrección y evidencias.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-110',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '10',
  'clause': '10.1',
  'domain_es': 'Causa y recurrencia',
  'assessment_question_es': 'Se analizan causas y se determina si pueden existir problemas similares en otros procesos o ubicaciones.',
  'suggested_evidence_es': 'Análisis de causa raíz, revisión transversal y acciones sistémicas.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-111',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '10',
  'clause': '10.1',
  'domain_es': 'Acción correctiva',
  'assessment_question_es': 'Las acciones correctivas son proporcionales al efecto de la no conformidad y se implementan oportunamente.',
  'suggested_evidence_es': 'Plan de acción, priorización, responsables y plazos.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-112',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '10',
  'clause': '10.1',
  'domain_es': 'Eficacia y actualización',
  'assessment_question_es': 'Se revisa la eficacia de las acciones y se actualizan riesgos, controles o el sistema cuando corresponde.',
  'suggested_evidence_es': 'Verificación de eficacia, cambios, cierre y aprobación.',
  'default_weight': 1,
  'active': True},
 {'item_id': 'BCP-113',
  'standard_code': 'ISO 22301',
  'standard_version': '2019+Amd1:2024',
  'chapter': '10',
  'clause': '10.2',
  'domain_es': 'Mejora continua',
  'assessment_question_es': 'La organización mejora continuamente la adecuación, suficiencia y eficacia del sistema de continuidad.',
  'suggested_evidence_es': 'Portafolio de mejoras, indicadores, lecciones y beneficios realizados.',
  'default_weight': 1,
  'active': True}]

ISO22301_MADUREZ_LEVELS = [
    {
        "nivel": "Nivel 1: Inicial",
        "descripcion": "No existe implementación formal o es mínima; las prácticas son ad hoc.",
        "score": 1,
        "rango_pct": "0% – 20%",
        "logica": "Prácticas no formalizadas"
    },
    {
        "nivel": "Nivel 2: Repetible",
        "descripcion": "Existen prácticas parciales y repetibles, pero con documentación o control limitado.",
        "score": 2,
        "rango_pct": "21% – 40%",
        "logica": "Prácticas parciales"
    },
    {
        "nivel": "Nivel 3: Definido",
        "descripcion": "El proceso está definido, documentado y comunicado para su ejecución consistente.",
        "score": 3,
        "rango_pct": "41% – 60%",
        "logica": "Proceso documentado"
    },
    {
        "nivel": "Nivel 4: Gestionado",
        "descripcion": "El proceso se mide, gestiona, controla y tiene seguimiento periódico.",
        "score": 4,
        "rango_pct": "61% – 80%",
        "logica": "Proceso medido y gestionado"
    },
    {
        "nivel": "Nivel 5: Optimizado",
        "descripcion": "El proceso es eficaz, sostenido y mejorado continuamente con evidencia trazable.",
        "score": 5,
        "rango_pct": "81% – 100%",
        "logica": "Mejora continua"
    },
]


# ============================================================
# MODELOS DB — ISO 22301
# ============================================================
class Iso22301MadurezParametro(db.Model):
    __bind_key__ = "iso22301_madurez"
    __tablename__ = "iso22301_madurez_parametros"

    id = db.Column(db.Integer, primary_key=True)
    nivel = db.Column(db.String(80), nullable=False)
    rango_desde = db.Column(db.Float, nullable=False)
    rango_hasta = db.Column(db.Float, nullable=False)
    color = db.Column(db.String(20), nullable=True)
    descripcion = db.Column(db.Text, nullable=True)
    orden = db.Column(db.Integer, default=0)


class Iso22301MadurezPregunta(db.Model):
    __bind_key__ = "iso22301_madurez"
    __tablename__ = "iso22301_madurez_preguntas"

    id = db.Column(db.Integer, primary_key=True)
    bloque_codigo = db.Column(db.String(50), index=True, nullable=True)
    bloque_nombre = db.Column(db.String(255), nullable=True)
    seccion_codigo = db.Column(db.String(50), index=True, nullable=True)
    seccion_nombre = db.Column(db.Text, nullable=True)
    pregunta_codigo = db.Column(db.String(50), index=True, nullable=True)
    pregunta = db.Column(db.Text, nullable=False)
    evidencia_sugerida = db.Column(db.Text, nullable=True)
    tipo = db.Column(db.String(5), nullable=False, default="q")  # h / q
    orden = db.Column(db.Integer, default=0)
    activo = db.Column(db.Boolean, default=True)


class Iso22301MadurezRun(db.Model):
    __bind_key__ = "iso22301_madurez"
    __tablename__ = "iso22301_madurez_runs"

    id = db.Column(db.Integer, primary_key=True)
    consecutivo = db.Column(db.String(255), nullable=False, index=True)
    company_name = db.Column(db.String(255), nullable=True)
    user_id = db.Column(db.Integer, nullable=True)  # DB independiente: no FK cruzada
    estado = db.Column(db.String(20), nullable=False, default="BORRADOR", index=True)
    progreso_pct = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    resumen_json = db.Column(db.Text, nullable=False, default="{}")
    pct_general = db.Column(db.Float, nullable=False, default=0.0)
    radar_overall_b64 = db.Column(db.Text, nullable=True)

    informe_ejecutivo_ai = db.Column(db.Text, nullable=True)
    informe_ejecutivo_editado = db.Column(db.Text, nullable=True)
    plan_trabajo_ai = db.Column(db.Text, nullable=True)
    plan_trabajo_editado = db.Column(db.Text, nullable=True)


class Iso22301MadurezRespuesta(db.Model):
    __bind_key__ = "iso22301_madurez"
    __tablename__ = "iso22301_madurez_respuestas"

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey("iso22301_madurez_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    pregunta_id = db.Column(db.Integer, db.ForeignKey("iso22301_madurez_preguntas.id", ondelete="CASCADE"), nullable=False, index=True)
    estado = db.Column(db.String(20), nullable=False)  # SI / PARCIAL / NO / NA
    comentario = db.Column(db.Text, nullable=True)


class Iso22301MadurezCriterioAnalisis(db.Model):
    __bind_key__ = "iso22301_madurez"
    __tablename__ = "iso22301_madurez_criterio_analisis"

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey("iso22301_madurez_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    bloque_codigo = db.Column(db.String(50), nullable=False, index=True)
    bloque_nombre = db.Column(db.String(255), nullable=True)
    estado_actual = db.Column(db.Text, nullable=True)
    estado_requerido = db.Column(db.Text, nullable=True)
    plan_accion_ai = db.Column(db.Text, nullable=True)
    plan_accion_editado = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("run_id", "bloque_codigo", name="uq_iso22301_run_bloque"),
    )


# ============================================================
# INICIALIZACIÓN DB INDEPENDIENTE
# ============================================================
def _iso22301_ensure_schema():
    """Aplica migraciones idempotentes únicamente sobre la base ISO 22301."""
    os.makedirs(app.instance_path, exist_ok=True)
    conn = sqlite3.connect(ISO22301_DB_PATH)
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(iso22301_madurez_preguntas)").fetchall()}
        if cols and "evidencia_sugerida" not in cols:
            conn.execute("ALTER TABLE iso22301_madurez_preguntas ADD COLUMN evidencia_sugerida TEXT")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.commit()
    finally:
        conn.close()


def init_iso22301_madurez_db():
    try:
        os.makedirs(app.instance_path, exist_ok=True)
        app.config.setdefault("SQLALCHEMY_BINDS", {})
        app.config["SQLALCHEMY_BINDS"]["iso22301_madurez"] = "sqlite:///" + ISO22301_DB_PATH
        with app.app_context():
            db.create_all(bind_key="iso22301_madurez")
            _iso22301_ensure_schema()
            seed_iso22301_parametros()
            if Iso22301MadurezPregunta.query.filter_by(tipo="q").count() == 0:
                iso22301_seed_catalog(ISO22301_EMBEDDED_CATALOG, replace=False)
        print(f"✅ Base de datos ISO 22301 inicializada correctamente: {ISO22301_DB_PATH}")
    except Exception as e:
        print(f"❌ Error inicializando base de datos ISO 22301: {repr(e)}")
        raise


# ============================================================
# HELPERS GENERALES
# ============================================================
def iso22301_block_title(code: str) -> str:
    return ISO22301_BLOCK_TITLES.get((code or "").strip().upper(), code or "")


def iso22301_safe_str(x):
    if x is None:
        return ""
    try:
        if pd.isna(x):
            return ""
    except Exception:
        pass
    return str(x).strip()


def _iso22301_norm(s: str) -> str:
    s = iso22301_safe_str(s)
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = s.upper()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def iso22301_normalizar_texto_excel(texto: str) -> str:
    t = iso22301_safe_str(texto)
    if not t:
        return ""
    t = t.replace("\ufeff", " ").replace("\xa0", " ")
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"[ \t]+", " ", t).strip()
    return t


def iso22301_detectar_bloque(texto: str):
    n = _iso22301_norm(texto)
    match = re.search(r"(?:CAPITULO|CAPÍTULO|CLAUSULA|CLÁUSULA)?\s*(10|[4-9])(?:\.0)?$", n)
    if match:
        code = match.group(1)
        return code, ISO22301_BLOCK_TITLES.get(code, code)
    return None, None


def seed_iso22301_parametros():
    if Iso22301MadurezParametro.query.first():
        return
    params = [
        {"nivel": "Nivel 1: Inicial", "rango_desde": 0, "rango_hasta": 20.99, "color": "#dc3545", "descripcion": "No existe implementación formal o es mínima.", "orden": 1},
        {"nivel": "Nivel 2: Repetible", "rango_desde": 21, "rango_hasta": 40.99, "color": "#fd7e14", "descripcion": "Existen prácticas parciales y repetibles.", "orden": 2},
        {"nivel": "Nivel 3: Definido", "rango_desde": 41, "rango_hasta": 60.99, "color": "#ffc107", "descripcion": "El proceso está definido y documentado.", "orden": 3},
        {"nivel": "Nivel 4: Gestionado", "rango_desde": 61, "rango_hasta": 80.99, "color": "#0d6efd", "descripcion": "El proceso se mide, gestiona y controla.", "orden": 4},
        {"nivel": "Nivel 5: Optimizado", "rango_desde": 81, "rango_hasta": 100, "color": "#198754", "descripcion": "Proceso eficaz, sostenido y mejorado continuamente.", "orden": 5},
    ]
    for p in params:
        db.session.add(Iso22301MadurezParametro(**p))
    db.session.commit()


def iso22301_resolver_nivel(pct: float):
    try:
        pct = float(pct or 0)
    except Exception:
        pct = 0.0
    pct = max(0.0, min(100.0, pct))
    rows = Iso22301MadurezParametro.query.order_by(Iso22301MadurezParametro.orden.asc()).all()
    for r in rows:
        if float(r.rango_desde) <= pct <= float(r.rango_hasta):
            return {"nivel": r.nivel, "score": r.orden, "color": r.color or "#6c757d", "descripcion": r.descripcion or ""}
    return {"nivel": "Nivel no definido", "score": 0, "color": "#6c757d", "descripcion": ""}


def iso22301_resumen_instrumento():
    total_q = Iso22301MadurezPregunta.query.filter_by(tipo="q").count()
    total_h = Iso22301MadurezPregunta.query.filter_by(tipo="h").count()
    por_bloque = (
        db.session.query(Iso22301MadurezPregunta.bloque_codigo, func.count(Iso22301MadurezPregunta.id))
        .filter(Iso22301MadurezPregunta.tipo == "q")
        .group_by(Iso22301MadurezPregunta.bloque_codigo)
        .all()
    )
    return {"total_preguntas": total_q, "total_headers": total_h, "por_bloque": {k: v for k, v in por_bloque}}


def cargar_respuestas_iso22301(run_id):
    out = {}
    if not run_id:
        return out
    rows = Iso22301MadurezRespuesta.query.filter_by(run_id=run_id).all()
    for r in rows:
        out[r.pregunta_id] = {"estado": (r.estado or "").strip().upper(), "comentario": (r.comentario or "").strip()}
    return out


def calcular_progreso_iso22301(preguntas, form_data=None, respuestas_db=None):
    total = len(preguntas)
    respondidas = 0
    for q in preguntas:
        estado = ""
        if form_data is not None:
            estado = (form_data.get(f"st_{q.id}") or "").strip().upper()
        elif respuestas_db is not None:
            estado = (respuestas_db.get(q.id, {}).get("estado") or "").strip().upper()
        if estado in ("SI", "PARCIAL", "NO", "NA"):
            respondidas += 1
    pct = int(round((respondidas / total) * 100)) if total > 0 else 0
    return respondidas, total, pct


def obtener_borrador_iso22301(user_id):
    if not user_id:
        return None
    return (
        Iso22301MadurezRun.query
        .filter(Iso22301MadurezRun.user_id == user_id, Iso22301MadurezRun.estado == "BORRADOR")
        .order_by(Iso22301MadurezRun.updated_at.desc(), Iso22301MadurezRun.id.desc())
        .first()
    )


def _contar_respuestas_run_iso22301(run_id: int) -> int:
    if not run_id:
        return 0
    return Iso22301MadurezRespuesta.query.filter_by(run_id=run_id).count()


def _eliminar_runs_vacios_iso22301(user_id: int | None = None):
    q = Iso22301MadurezRun.query
    if user_id:
        q = q.filter(Iso22301MadurezRun.user_id == user_id)
    eliminados = 0
    for run in q.all():
        if Iso22301MadurezRespuesta.query.filter_by(run_id=run.id).count() == 0:
            Iso22301MadurezCriterioAnalisis.query.filter_by(run_id=run.id).delete(synchronize_session=False)
            db.session.delete(run)
            eliminados += 1
    if eliminados:
        db.session.commit()
    return eliminados


def iso22301_pct_from_estados(estados: list[str]) -> float:
    vals = []
    for e in estados:
        estado = (e or "").strip().upper()

        # N/A tiene valor 0, pero no es una pregunta aplicable y por eso
        # no suma ni aumenta el denominador del promedio.
        if estado == "NA":
            continue

        v = ISO22301_STATUS_SCORE.get(estado)
        if v is not None:
            vals.append(v)

    return round(sum(vals) / len(vals), 2) if vals else 0.0


def _parse_rango_pct_iso22301(rango: str):
    if not rango:
        return None, None
    s = rango.replace("%", "").strip().replace("–", "-")
    parts = [p.strip() for p in s.split("-")]
    if len(parts) != 2:
        return None, None
    try:
        return float(parts[0]), float(parts[1])
    except Exception:
        return None, None


def iso22301_nivel_visual_por_pct(pct: float):
    return iso22301_resolver_nivel(pct)


def _iso22301_group_questions():
    preguntas = (
        Iso22301MadurezPregunta.query
        .filter_by(activo=True, tipo="q")
        .order_by(Iso22301MadurezPregunta.bloque_codigo.asc(), Iso22301MadurezPregunta.orden.asc(), Iso22301MadurezPregunta.id.asc())
        .all()
    )
    grouped = {}
    for q in preguntas:
        bloque = (q.bloque_codigo or "SIN_BLOQUE").strip().upper()
        if bloque not in grouped:
            grouped[bloque] = {
                "titulo": q.bloque_nombre or iso22301_block_title(bloque) or bloque,
                "items": []
            }
        grouped[bloque]["items"].append(q)
    ordered = {}
    for code in ISO22301_BLOCK_ORDER:
        if code in grouped:
            ordered[code] = grouped[code]
    for code, val in grouped.items():
        if code not in ordered:
            ordered[code] = val
    return ordered


def _iso22301_build_resumen(run_id: int) -> dict:
    q = (
        db.session.query(Iso22301MadurezRespuesta, Iso22301MadurezPregunta)
        .join(Iso22301MadurezPregunta, Iso22301MadurezPregunta.id == Iso22301MadurezRespuesta.pregunta_id)
        .filter(Iso22301MadurezRespuesta.run_id == run_id)
        .filter(Iso22301MadurezPregunta.tipo == "q")
        .order_by(Iso22301MadurezPregunta.bloque_codigo.asc(), Iso22301MadurezPregunta.orden.asc())
    )
    por_bloque = {}
    for r, p in q.all():
        b = (p.bloque_codigo or "SIN_BLOQUE").strip().upper()
        por_bloque.setdefault(b, {
            "bloque": b,
            "nombre": p.bloque_nombre or iso22301_block_title(b) or b,
            "total": 0,
            "validas": 0,
            "SI": 0,
            "PARCIAL": 0,
            "NO": 0,
            "NA": 0,
            "items": [],
        })
        estado = (r.estado or "").strip().upper()
        por_bloque[b]["total"] += 1
        if estado in ("SI", "PARCIAL", "NO", "NA"):
            por_bloque[b][estado] += 1
        # Solo Sí, Parcial y No forman el denominador. N/A queda registrado
        # en el detalle, pero no participa en el nivel de madurez.
        if estado in ("SI", "PARCIAL", "NO"):
            por_bloque[b]["validas"] += 1
        por_bloque[b]["items"].append({
            "pregunta_id": p.id,
            "pregunta_codigo": p.pregunta_codigo,
            "pregunta": p.pregunta,
            "evidencia_sugerida": p.evidencia_sugerida or "",
            "estado": estado,
            "comentario": r.comentario or "",
        })

    resumen = {}
    for b, d in por_bloque.items():
        estados = [it["estado"] for it in d["items"]]
        pct = iso22301_pct_from_estados(estados)
        nivel = (
            iso22301_resolver_nivel(pct)
            if int(d.get("validas", 0) or 0) > 0
            else {
                "nivel": "No aplica",
                "score": 0,
                "color": "#6c757d",
                "descripcion": "Todas las preguntas del capítulo fueron marcadas N/A.",
            }
        )
        d["pct"] = pct
        d["madurez"] = nivel["nivel"]
        d["score"] = nivel.get("score", 0)
        d["color"] = nivel["color"]
        d["descripcion"] = nivel.get("descripcion", "")
        d["brecha_pct"] = round(100.0 - pct, 2) if d["validas"] > 0 else 0.0
        resumen[b] = d
    return resumen


def iso22301_pct_general_from_resumen(resumen: dict) -> float:
    """Calcula el resultado global solo con preguntas distintas de N/A."""
    estados = [
        item.get("estado", "")
        for bloque in (resumen or {}).values()
        for item in (bloque.get("items", []) or [])
    ]
    return iso22301_pct_from_estados(estados)


def iso22301_pct_por_criterio(resumen: dict, order: list[str] = None):
    order = order or ISO22301_BLOCK_ORDER
    labels, values = [], []
    for b in order:
        if b in (resumen or {}):
            d = (resumen or {}).get(b, {}) or {}
            if int(d.get("validas", 0) or 0) <= 0:
                continue
            labels.append(iso22301_block_title(b) or b)
            values.append(float(d.get("pct", 0) or 0))
    for b, d in (resumen or {}).items():
        if b not in order:
            if int(d.get("validas", 0) or 0) <= 0:
                continue
            labels.append(d.get("nombre") or b)
            values.append(float(d.get("pct", 0) or 0))
    return labels, values


def iso22301_radar_b64(labels: list[str], values: list[float], title: str = "Radar ISO 22301"):
    if not labels:
        return ""
    vals = [max(0.0, min(100.0, float(v))) for v in values]
    N = len(labels)
    angles = [n / float(N) * 2 * math.pi for n in range(N)]
    angles += angles[:1]
    plot_vals = vals + vals[:1]

    fig = plt.figure(figsize=(3.55, 3.55), dpi=170)
    ax = plt.subplot(111, polar=True)
    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=7.3)
    ax.tick_params(axis="x", pad=10)
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=7)
    ax.tick_params(axis="y", pad=4)
    ax.plot(angles, plot_vals, linewidth=2.0)
    ax.fill(angles, plot_vals, alpha=0.16)
    ax.set_title(title, fontsize=9.5, pad=14)
    fig.subplots_adjust(top=0.83, bottom=0.10, left=0.10, right=0.90)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", transparent=True, bbox_inches="tight", pad_inches=0.22)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def generar_iso22301_velocimetro_png_bytes(titulo, valor, nivel="", color="#6c757d"):
    try:
        valor = max(0, min(100, float(valor or 0)))
        fig = plt.figure(figsize=(7.2, 4.2), dpi=220)
        ax = plt.axes([0.04, 0.08, 0.92, 0.84])
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_xlim(-1.18, 1.18)
        ax.set_ylim(-0.28, 1.18)
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")
        rangos = [(180, 144, "#d9534f"), (144, 108, "#f0ad4e"), (108, 72, "#f7d154"), (72, 36, "#5bc0de"), (36, 0, "#5cb85c")]
        for theta1, theta2, c in rangos:
            ax.add_patch(Wedge((0, 0), 1.00, theta2, theta1, width=0.18, facecolor=c, edgecolor="white", linewidth=2))
        for pct in range(0, 101, 10):
            ang = math.radians(180 - (pct / 100.0) * 180.0)
            ax.plot([math.cos(ang) * 0.78, math.cos(ang) * 0.88], [math.sin(ang) * 0.78, math.sin(ang) * 0.88], linewidth=1.2, color="#4b5563")
        for pct in [0, 25, 50, 75, 100]:
            ang = math.radians(180 - (pct / 100.0) * 180.0)
            ax.text(math.cos(ang) * 0.63, math.sin(ang) * 0.63, f"{pct}", ha="center", va="center", fontsize=10, fontweight="bold", color="#374151")
        ang = math.radians(180 - (valor / 100.0) * 180.0)
        ax.add_patch(FancyArrowPatch((0, 0), (math.cos(ang) * 0.72, math.sin(ang) * 0.72), arrowstyle="-|>", mutation_scale=18, linewidth=2.4, color="#0b1220", zorder=5))
        ax.add_patch(Circle((0, 0), radius=0.065, facecolor="#0b1220", edgecolor="white", linewidth=1.0, zorder=6))
        titulo_corto = (titulo or "").strip()
        if len(titulo_corto) > 42:
            titulo_corto = titulo_corto[:39] + "..."
        ax.text(0, 1.06, titulo_corto, ha="center", va="center", fontsize=13, fontweight="bold", color="#0f3d68")
        ax.text(0, 0.30, f"{valor:.1f}%", ha="center", va="center", fontsize=24, fontweight="bold", color=color)
        if nivel:
            ax.text(0, 0.12, str(nivel)[:30], ha="center", va="center", fontsize=11, fontweight="bold", color="#374151")
        buf = io.BytesIO()
        canvas = FigureCanvas(fig)
        canvas.print_png(buf)
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()
    except Exception:
        plt.close("all")
        return None


def generar_iso22301_velocimetro_base64(label: str, pct: float, nivel: str, color: str):
    b = generar_iso22301_velocimetro_png_bytes(label, pct, nivel, color)
    if not b:
        return None
    return base64.b64encode(b).decode("utf-8")


def iso22301_normalizar_texto_rico_guardado(texto: str) -> str:
    txt = (texto or "").strip()

    if not txt:
        return ""

    txt = txt.replace("\r\n", "\n").replace("\r", "\n")
    txt = html.unescape(txt)
    txt = txt.replace("```json", "").replace("```", "").strip()

    # Extrae JSON aunque venga como:
    # { "informe_ejecutivo": "texto..." }
    # { "plan_trabajo": "texto..." }
    # { "texto": "texto..." }
    obj = None

    try:
        obj = json.loads(txt)
    except Exception:
        try:
            start = txt.find("{")
            end = txt.rfind("}")
            if start != -1 and end != -1 and end > start:
                obj = json.loads(txt[start:end + 1])
        except Exception:
            obj = None

    if isinstance(obj, dict):
        val = (
            obj.get("informe_ejecutivo")
            or obj.get("informe")
            or obj.get("resumen_ejecutivo")
            or obj.get("plan_trabajo")
            or obj.get("plan_accion")
            or obj.get("texto")
            or ""
        )

        if isinstance(val, list):
            val = _build_plan_accion_iso22301_texto(val)

        if isinstance(val, dict):
            val = json.dumps(val, ensure_ascii=False, indent=2)

        if isinstance(val, str) and val.strip():
            txt = val.strip()

    txt = html.unescape(txt)

    # Si aún quedaron llaves al inicio y contiene informe_ejecutivo,
    # intenta extraer por regex como último recurso.
    m = re.search(
        r'"informe_ejecutivo"\s*:\s*"(?P<txt>.*)"\s*\}?\s*$',
        txt,
        flags=re.IGNORECASE | re.DOTALL
    )

    if m:
        extraido = m.group("txt")

        try:
            # Solo interpreta secuencias JSON reales (\n, \u00f3, etc.)
            extraido = json.loads(f'"{extraido}"')
        except Exception:
            pass

        txt = extraido.strip()

    txt = re.sub(r"<\s*br\s*/?\s*>", "\n", txt, flags=re.IGNORECASE)
    txt = re.sub(r"<[^>]+>", "", txt)

    patrones = [
        r"^\s*\{\s*",
        r"^\s*\"informe_ejecutivo\"\s*:\s*\"?",
        r"^\s*\"resumen_ejecutivo\"\s*:\s*\"?",
        r"^\s*\*{0,3}\s*INFORME\s+EJECUTIVO\s*(DE\s+MADUREZ\s+ISO\s*22301)?\s*\*{0,3}\s*[:\-–—]?\s*",
        r"^\s*#{1,6}\s*INFORME\s+EJECUTIVO\s*(DE\s+MADUREZ\s+ISO\s*22301)?\s*[:\-–—]?\s*",
        r"^\s*RESUMEN\s+EJECUTIVO\s*[:\-–—]?\s*",
        r"^\s*PLAN\s+DE\s+TRABAJO\s*[:\-–—]?\s*",
    ]

    for p in patrones:
        txt = re.sub(p, "", txt, flags=re.IGNORECASE).strip()

    txt = re.sub(r'"\s*\}\s*$', "", txt).strip()
    txt = txt.replace("\\n", "\n")
    txt = txt.replace('\\"', '"')
    txt = txt.replace("**", "").replace("__", "")

    txt = re.sub(r"[ \t]+\n", "\n", txt)
    txt = re.sub(r"\n[ \t]+", "\n", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt)

    return txt.strip()


def _extraer_json_objeto_iso22301(raw: str) -> dict:
    raw = (raw or "").strip().replace("```json", "").replace("```", "").strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        pass
    try:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(raw[start:end + 1])
    except Exception:
        pass
    return {}


def _iso22301_texto_informe_desde_valor(valor) -> str:
    """Obtiene texto útil desde respuestas de IA con estructuras variables."""
    if valor is None:
        return ""

    if isinstance(valor, str):
        return iso22301_normalizar_texto_rico_guardado(valor)

    if isinstance(valor, list):
        partes = []
        for item in valor:
            texto_item = _iso22301_texto_informe_desde_valor(item)
            if texto_item:
                partes.append(texto_item)
        return "\n\n".join(partes).strip()

    if not isinstance(valor, dict):
        return ""

    aliases = (
        "informe_ejecutivo",
        "informe_ejecutivo_iso_22301",
        "informe",
        "resumen_ejecutivo",
        "executive_summary",
        "executive_report",
        "report",
        "summary",
        "texto",
        "contenido",
        "content",
        "respuesta",
        "response",
        "resultado",
        "result",
        "output",
        "answer",
    )

    claves_normalizadas = {}
    for clave in valor.keys():
        clave_txt = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(clave))
        clave_norm = re.sub(r"[^a-z0-9]+", "_", clave_txt.lower()).strip("_")
        claves_normalizadas[clave_norm] = clave

    # Primero busca los nombres de campo conocidos, incluidos formatos
    # alternativos frecuentes de OpenRouter y Ollama.
    for alias in aliases:
        clave_real = claves_normalizadas.get(alias)
        if clave_real is None:
            continue
        texto = _iso22301_texto_informe_desde_valor(valor.get(clave_real))
        if texto:
            return texto

    # Si el proveedor anidó el contenido bajo otra clave, conserva el texto
    # más completo en lugar de descartar toda la respuesta.
    candidatos = []
    for contenido in valor.values():
        texto = _iso22301_texto_informe_desde_valor(contenido)
        if texto:
            candidatos.append(texto)

    return max(candidatos, key=len) if candidatos else ""


def _iso22301_extraer_informe_ai(raw) -> str:
    """Acepta JSON, JSON anidado, bloques Markdown o texto plano de la IA."""
    if raw is None:
        return ""

    if isinstance(raw, (dict, list)):
        return _iso22301_texto_informe_desde_valor(raw)

    raw_txt = str(raw).strip()
    if not raw_txt:
        return ""

    limpio = raw_txt.replace("```json", "").replace("```", "").strip()
    obj = None
    try:
        obj = json.loads(limpio)
    except Exception:
        try:
            inicio = limpio.find("{")
            fin = limpio.rfind("}")
            if inicio != -1 and fin != -1 and fin > inicio:
                obj = json.loads(limpio[inicio:fin + 1])
        except Exception:
            obj = None

    # Si el JSON sí fue válido, una estructura vacía o sin contenido debe
    # provocar el reintento; no debe guardarse como si fuera un informe.
    if obj is not None:
        return _iso22301_texto_informe_desde_valor(obj)

    # Fallback para texto plano o JSON incompleto por límite de tokens.
    texto = iso22301_normalizar_texto_rico_guardado(raw_txt)
    if texto.strip() in ("", "{}", "[]"):
        return ""
    return texto.strip()


def _build_plan_accion_iso22301_texto(plan_list) -> str:
    if not isinstance(plan_list, list):
        return ""
    lines = []
    for i, it in enumerate(plan_list, start=1):
        accion = (it.get("accion") or it.get("actividad") or "").strip()
        prioridad = (it.get("prioridad") or "").strip()
        responsable = (it.get("responsable_sugerido") or "").strip()
        plazo = (it.get("plazo") or "").strip()
        evidencia = (it.get("evidencia_esperada") or it.get("entregable") or "").strip()
        lines.append(
            f"{i}. Acción: {accion or 'Sin definir'}\n"
            f"   Prioridad: {prioridad or 'Sin definir'}\n"
            f"   Responsable sugerido: {responsable or 'Sin definir'}\n"
            f"   Plazo: {plazo or 'Sin definir'}\n"
            f"   Evidencia esperada: {evidencia or 'Sin definir'}"
        )
    return "\n\n".join(lines).strip()


def _normalizar_plan_accion_iso22301_texto(texto_raw: str) -> str:
    txt = (texto_raw or "").strip().replace("```json", "").replace("```", "").strip()
    if not txt:
        return ""
    obj = _extraer_json_objeto_iso22301(txt)
    if isinstance(obj, dict):
        for key in ("plan_accion", "plan_trabajo", "plan", "acciones"):
            if isinstance(obj.get(key), list):
                return _build_plan_accion_iso22301_texto(obj.get(key))
    return iso22301_normalizar_texto_rico_guardado(txt)

# ============================================================
# ISO 22301 — PROMPT PLAN DE TRABAJO IA
# ============================================================

def _iso22301_prompt_plan_trabajo(run: "Iso22301MadurezRun", resumen: dict) -> str:
    """
    Prompt para generar plan de trabajo ISO 22301.
    Lo usa plan_trabajo_generar().
    """

    lineas = []

    for code in ISO22301_BLOCK_ORDER:
        d = (resumen or {}).get(code)
        if not d or int(d.get("validas", 0) or 0) <= 0:
            continue

        lineas.append(
            f"- {d.get('nombre') or iso22301_block_title(code) or code}: "
            f"{float(d.get('pct', 0) or 0):.2f}% | "
            f"Nivel: {d.get('madurez') or ''} | "
            f"Brecha: {float(d.get('brecha_pct', 0) or 0):.2f}% | "
            f"NO: {d.get('NO', 0)} | "
            f"Parcial: {d.get('PARCIAL', 0)}"
        )

    criterios_txt = "\n".join(lineas) if lineas else "Sin resultados consolidados."

    return f"""
Eres un consultor senior experto en ISO 22301 y preparación para auditoría.

Genera un plan de trabajo priorizado para cerrar brechas ISO 22301.

DATOS
Consecutivo: {run.consecutivo}
Cumplimiento general: {float(run.pct_general or 0):.2f}%

RESULTADOS POR CRITERIO
{criterios_txt}

RESPONDE ÚNICAMENTE JSON VÁLIDO.
No uses markdown.
No agregues texto antes ni después del JSON.

Formato exacto:
{{
  "plan_trabajo": [
    {{
      "accion": "texto",
      "prioridad": "Alta|Media|Baja",
      "responsable_sugerido": "texto",
      "plazo": "texto",
      "evidencia_esperada": "texto"
    }}
  ]
}}

REGLAS:
- Genera entre 8 y 12 acciones.
- Prioriza criterios con menor cumplimiento.
- Las acciones deben ser auditables y verificables.
- La evidencia esperada debe ser concreta.
- No inventes herramientas específicas.
""".strip()

# ============================================================
# IA — ISO 22301
# ============================================================
def _iso22301_ai_text(prompt: str, max_tokens: int = 900) -> str:
    """
    IA exclusiva para ISO 22301.
    Corrige timeout de Ollama:
    - Reduce num_predict
    - Aumenta timeout
    - No usa stream
    - Mantiene OpenRouter si está configurado como proveedor
    """

    provider = (get_ai_provider() or "openrouter").strip().lower()

    # =========================
    # OLLAMA
    # =========================
    if provider == "ollama":
        base_url = (get_ollama_base_url() or "http://localhost:11434").strip().rstrip("/")
        model = (get_ollama_model() or "llama3.1").strip()

        if not base_url:
            raise RuntimeError("No hay OLLAMA_BASE_URL configurada.")
        if not model:
            raise RuntimeError("No hay OLLAMA_MODEL configurado.")

        try:
            resp = requests.post(
                f"{base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.15,
                        "num_predict": int(max_tokens or 700),
                        "top_p": 0.9
                    }
                },
                timeout=600
            )

            resp.raise_for_status()
            data = resp.json() or {}
            texto = (data.get("response") or "").strip()

            if not texto:
                raise RuntimeError("Ollama respondió sin contenido.")

            return texto

        except requests.exceptions.ReadTimeout:
            raise RuntimeError(
                "Ollama tardó demasiado en responder. "
                "Se recomienda reducir el número de preguntas enviadas o usar OpenRouter para este análisis."
            )

        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                "No fue posible conectar con Ollama. "
                "Verifica que Ollama esté activo en http://localhost:11434."
            )

    # =========================
    # OPENROUTER
    # =========================
    if "_ai_text" in globals():
        return _ai_text(prompt, max_tokens=max_tokens)

    raise RuntimeError("No se encontró helper global _ai_text para OpenRouter/Ollama.")


def _iso22301_ai_prompt_criterio(
    run: "Iso22301MadurezRun",
    bloque_codigo: str,
    bloque_nombre: str,
    pct: float,
    items: list[dict]
):
    """
    Prompt ISO 22301 mejorado:
    - Evita respuestas demasiado cortas.
    - Mantiene límite para no generar timeout en Ollama.
    - Obliga estado actual y requerido con análisis real.
    """

    bullets = []

    applicable_items = [
        it for it in (items or [])
        if (it.get("estado") or "").strip().upper() != "NA"
    ]

    for it in applicable_items[:30]:
        pregunta = (it.get("pregunta") or "")[:260].replace("\n", " ")
        comentario = (it.get("comentario") or "")[:260].replace("\n", " ")
        estado = (it.get("estado") or "").strip().upper()

        linea = f"- [{estado}] {pregunta}"
        if comentario:
            linea += f" | Evidencia/Comentario: {comentario}"

        bullets.append(linea)

    joined = "\n".join(bullets) if bullets else "- Sin evidencias registradas."

    return f"""
Eres un consultor senior experto en ISO 22301, Trust Services Criteria, auditoría de controles, seguridad de la información y gobierno de riesgos.

Debes generar un análisis ejecutivo, claro y accionable para el criterio evaluado.

CONTEXTO DE LA EVALUACIÓN
Consecutivo: {run.consecutivo}
Criterio ISO 22301: {bloque_codigo} - {bloque_nombre}
Cumplimiento actual: {pct:.2f}%

EVIDENCIAS Y RESPUESTAS DEL CRITERIO
{joined}

INSTRUCCIONES OBLIGATORIAS
Responde únicamente JSON válido.
No uses markdown.
No agregues texto antes ni después del JSON.

Debes devolver exactamente estas llaves:
{{
  "estado_actual": "texto",
  "estado_requerido": "texto",
  "plan_accion": [
    {{
      "accion": "texto",
      "prioridad": "Alta|Media|Baja",
      "responsable_sugerido": "texto",
      "plazo": "texto",
      "evidencia_esperada": "texto"
    }}
  ]
}}

REGLAS PARA estado_actual:
- No respondas solo con el porcentaje.
- Redacta entre 2 y 4 párrafos.
- Explica qué tan maduro está el criterio actualmente.
- Menciona fortalezas visibles según respuestas SI.
- Menciona brechas según respuestas NO y PARCIAL.
- Usa los comentarios/evidencias cuando existan.
- Si hay pocas evidencias, dilo claramente.
- No inventes herramientas ni controles que no estén soportados por las respuestas.

REGLAS PARA estado_requerido:
- No respondas solo con "100% de cumplimiento".
- Redacta entre 2 y 4 párrafos.
- Describe el estado objetivo esperado para ISO 22301.
- Explica qué controles, evidencias, formalización, monitoreo y mejora deberían existir.
- Relaciona el estado requerido con auditoría, trazabilidad, evidencia y operación sostenida.
- No inventes marcas ni herramientas específicas.

REGLAS PARA plan_accion:
- Genera entre 5 y 8 acciones.
- Prioriza primero respuestas NO y PARCIAL.
- Cada acción debe ser concreta, auditable y verificable.
- La evidencia esperada debe ser un entregable real: política, procedimiento, matriz, registro, acta, reporte, evidencia de monitoreo, prueba de control, etc.
- Usa prioridades Alta, Media o Baja.

TONO
Profesional, ejecutivo y consultivo.
Enfocado en madurez ISO 22301 y preparación para auditoría.
""".strip()


# ============================================================
# CARGA DEL CATÁLOGO E IMPORTACIÓN DEL INSTRUMENTO ISO 22301
# ============================================================
def _iso22301_bool(value, default=True):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    txt = _iso22301_norm(value)
    return txt not in ("0", "FALSE", "FALSO", "NO", "INACTIVO")


def _iso22301_catalog_from_excel(xlsx_path):
    df = pd.read_excel(xlsx_path, sheet_name="Catálogo Arkyntech", header=0)
    normalized = {_iso22301_norm(c): c for c in df.columns}
    required = {
        "ITEM_ID", "CHAPTER", "CLAUSE", "DOMAIN_ES",
        "ASSESSMENT_QUESTION_ES", "SUGGESTED_EVIDENCE_ES"
    }
    missing = sorted(required - set(normalized))
    if missing:
        raise ValueError("Faltan columnas en 'Catálogo Arkyntech': " + ", ".join(missing))

    rows = []
    for _, row in df.iterrows():
        item_id = iso22301_safe_str(row.get(normalized["ITEM_ID"]))
        question = iso22301_normalizar_texto_excel(row.get(normalized["ASSESSMENT_QUESTION_ES"]))
        if not item_id or not question:
            continue
        rows.append({
            "item_id": item_id,
            "standard_code": iso22301_safe_str(row.get(normalized.get("STANDARD_CODE"))) or "ISO 22301",
            "standard_version": iso22301_safe_str(row.get(normalized.get("STANDARD_VERSION"))) or "2019+Amd1:2024",
            "chapter": iso22301_safe_str(row.get(normalized["CHAPTER"])).replace(".0", ""),
            "clause": iso22301_safe_str(row.get(normalized["CLAUSE"])),
            "domain_es": iso22301_safe_str(row.get(normalized["DOMAIN_ES"])),
            "assessment_question_es": question,
            "suggested_evidence_es": iso22301_normalizar_texto_excel(row.get(normalized["SUGGESTED_EVIDENCE_ES"])),
            "default_weight": 1,
            "active": _iso22301_bool(row.get(normalized.get("ACTIVE")), True),
        })
    return rows


def iso22301_seed_catalog(catalog_rows, replace=False):
    if replace:
        Iso22301MadurezCriterioAnalisis.query.delete(synchronize_session=False)
        Iso22301MadurezRespuesta.query.delete(synchronize_session=False)
        Iso22301MadurezRun.query.delete(synchronize_session=False)
        Iso22301MadurezPregunta.query.delete(synchronize_session=False)
        db.session.flush()
    elif Iso22301MadurezPregunta.query.filter_by(tipo="q").first():
        return {"headers": 0, "questions": 0, "ignored": 0}

    headers_created = set()
    creadas_q = 0
    creadas_h = 0
    ignoradas = 0
    orden = 1

    for item in catalog_rows or []:
        chapter = str(item.get("chapter") or "").strip().replace(".0", "")
        clause = str(item.get("clause") or "").strip()
        domain = str(item.get("domain_es") or "").strip()
        item_id = str(item.get("item_id") or "").strip()
        question = iso22301_normalizar_texto_excel(item.get("assessment_question_es"))
        evidence = iso22301_normalizar_texto_excel(item.get("suggested_evidence_es"))
        if chapter not in ISO22301_BLOCK_TITLES or not item_id or not question:
            ignoradas += 1
            continue

        if chapter not in headers_created:
            title = ISO22301_BLOCK_TITLES[chapter]
            db.session.add(Iso22301MadurezPregunta(
                bloque_codigo=chapter,
                bloque_nombre=title,
                seccion_codigo=chapter,
                seccion_nombre=title,
                pregunta_codigo=f"CAP-{chapter}",
                pregunta=title,
                evidencia_sugerida=None,
                tipo="h",
                orden=orden,
                activo=True,
            ))
            orden += 1
            creadas_h += 1
            headers_created.add(chapter)

        db.session.add(Iso22301MadurezPregunta(
            bloque_codigo=chapter,
            bloque_nombre=ISO22301_BLOCK_TITLES[chapter],
            seccion_codigo=clause,
            seccion_nombre=domain,
            pregunta_codigo=item_id,
            pregunta=question,
            evidencia_sugerida=evidence,
            tipo="q",
            orden=orden,
            activo=_iso22301_bool(item.get("active"), True),
        ))
        orden += 1
        creadas_q += 1

    db.session.commit()
    return {"headers": creadas_h, "questions": creadas_q, "ignored": ignoradas}


@iso22301_madurez_bp.route("/admin/importar_instrumento", methods=["POST"])
@login_required
def importar_instrumento_iso22301():
    user = User.query.get(session.get("user_id"))
    if user.role == "auditor":
        flash("El rol Auditor no puede importar instrumentos.", "danger")
        return redirect(url_for("madurez_iso22301.parametros"))
    if user.role != "admin" and not verificar_permiso(user, ISO22301_PERMISSION_NAME):
        flash("No tiene permiso para importar el instrumento ISO 22301.", "danger")
        return redirect(url_for("menu"))

    force = (request.args.get("force") == "1") or (request.form.get("force") == "1")
    try:
        if Iso22301MadurezPregunta.query.filter_by(tipo="q").first() and not force:
            flash("El instrumento ISO 22301 ya está cargado en la base de datos.", "warning")
            return redirect(url_for("madurez_iso22301.parametros"))

        alternativas = [
            ISO22301_INSTRUMENTO_TEMPLATE_XLSX,
            os.path.join(BASE_DIR, "static", "templates", "Arkyntech_Matriz_Madurez_ISO_22301_ES(1).xlsx"),
            os.path.join(BASE_DIR, "static", "templates", "ISO 22301.xlsx"),
        ]
        xlsx_path = next((p for p in alternativas if os.path.exists(p)), None)
        catalog_rows = _iso22301_catalog_from_excel(xlsx_path) if xlsx_path else ISO22301_EMBEDDED_CATALOG
        stats = iso22301_seed_catalog(catalog_rows, replace=force)
        source_name = os.path.basename(xlsx_path) if xlsx_path else "catálogo integrado en Arkyntech"
        flash(
            f"✅ Instrumento ISO 22301 importado desde {source_name}. "
            f"Capítulos: {stats['headers']} | Preguntas: {stats['questions']} | Ignoradas: {stats['ignored']}",
            "success",
        )
        return redirect(url_for("madurez_iso22301.parametros"))
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        flash(f"❌ Error importando instrumento ISO 22301: {e}", "danger")
        return redirect(url_for("madurez_iso22301.parametros"))


# ============================================================
# CONSOLIDAR ANÁLISIS
# ============================================================
def run_analysis_from_iso22301_run(iso22301_run_id: int):
    run = Iso22301MadurezRun.query.get_or_404(iso22301_run_id)
    resumen = _iso22301_build_resumen(run.id)
    # Cálculo general ponderado por pregunta aplicable. N/A se conserva
    # en el historial, pero no suma ni forma parte del denominador.
    pct_general = iso22301_pct_general_from_resumen(resumen)
    labels, values = iso22301_pct_por_criterio(resumen, ISO22301_BLOCK_ORDER)
    run.resumen_json = json.dumps(resumen, ensure_ascii=False)
    run.pct_general = pct_general
    run.radar_overall_b64 = iso22301_radar_b64(labels, values, title="Radar por Capítulo - ISO 22301")
    run.company_name = run.consecutivo
    run.updated_at = datetime.utcnow()
    db.session.commit()
    return run.id

# ============================================================
# PERMISOS ISO 22301 — ADMIN / USUARIO CON PERMISO / AUDITOR
# ============================================================

def iso22301_user_can_access(user):
    """
    Puede VER el módulo:
    - admin
    - auditor
    - usuario con permiso Nivel de madurez ISO 22301
    """
    return bool(
        user and (
            user.role in ("admin", "auditor")
            or verificar_permiso(user, ISO22301_PERMISSION_NAME)
        )
    )


def iso22301_user_can_execute(user):
    """
    Puede EJECUTAR / MODIFICAR:
    - admin
    - usuario con permiso Nivel de madurez ISO 22301

    Auditor NO puede:
    - editar
    - eliminar
    - generar IA
    - exportar PDF
    - importar instrumento
    - guardar / analizar
    """
    return bool(
        user
        and user.role != "auditor"
        and (
            user.role == "admin"
            or verificar_permiso(user, ISO22301_PERMISSION_NAME)
        )
    )


def iso22301_check_access_or_redirect(user, msg="No tiene permiso para acceder al módulo ISO 22301."):
    if not iso22301_user_can_access(user):
        flash(msg, "danger")
        return redirect(url_for("menu"))
    return None


def iso22301_check_execute_or_redirect(user, msg="No tiene permiso para ejecutar esta acción en ISO 22301."):
    if not iso22301_user_can_execute(user):
        flash(msg, "danger")
        return redirect(url_for("madurez_iso22301.inicio_iso22301"))
    return None


# Alias para compatibilidad con bloques anteriores
def iso22301_deny_access(msg="No tiene permiso para acceder al módulo ISO 22301."):
    flash(msg, "danger")
    return redirect(url_for("menu"))


def iso22301_deny_execute(msg="No tiene permiso para ejecutar esta acción en ISO 22301."):
    flash(msg, "danger")
    return redirect(url_for("madurez_iso22301.inicio_iso22301"))


# ============================================================
# PANTALLA PRINCIPAL — MISMO DISEÑO NIST
# ============================================================

@iso22301_madurez_bp.route("/", methods=["GET"], endpoint="inicio_iso22301")
@login_required
def inicio_iso22301():
    user = User.query.get(session.get("user_id"))

    if not iso22301_user_can_access(user):
        return iso22301_deny_access("No tiene permiso para acceder al módulo de nivel de madurez ISO 22301.")

    read_only = user.role == "auditor"

    ingreso_btn = """
      <button class="btn btn-secondary rounded-pill px-4 fw-bold" disabled title="El rol Auditor no puede ingresar información">
        <i class="bi bi-pencil-square me-2"></i>Ingresar la información
      </button>
    """ if read_only else f"""
      <a href="{url_for('madurez_iso22301.ingreso')}" class="btn nistmad-btn-primary rounded-pill px-4 fw-bold grac-nav-blue-btn">
        <i class="bi bi-pencil-square me-2"></i>Ingresar la información
      </a>
    """

    parametros_btn = """
      <button class="btn btn-outline-secondary rounded-pill px-3" disabled title="El rol Auditor no puede modificar parámetros">
        <i class="bi bi-gear me-2"></i>Parámetros
      </button>
    """ if read_only else f"""
      <a href="{url_for('madurez_iso22301.parametros')}" class="btn btn-outline-secondary rounded-pill px-3">
        <i class="bi bi-gear me-2"></i>Parámetros
      </a>
    """

    total = Iso22301MadurezPregunta.query.filter_by(tipo="q").count()
    badge = '<span class="badge bg-success ms-2">Instrumento cargado</span>' if total else '<span class="badge bg-danger ms-2">Instrumento NO cargado</span>'
    hint = "Puedes ingresar la información, analizar la evaluación o consultar el historial." if total else "Primero entra a Parámetros e importa el instrumento ISO 22301."

    content = f"""
<div class="nistmad-shell">

  <div class="nistmad-header-card">
    <div class="nistmad-header-overlay">
      <div class="nistmad-header-text">
        <h3 class="nistmad-title m-0">Nivel de Madurez — ISO 22301</h3>
        <div class="nistmad-subtitle">
          Evaluación por capítulos 4 a 10: Contexto, Liderazgo, Planificación, Apoyo,
          Operación, Evaluación del desempeño y Mejora.
        </div>
      </div>
    </div>
  </div>

  <div class="nistmad-header-actions">
    {ingreso_btn}
    <a href="{url_for('madurez_iso22301.historial')}" class="btn nistmad-btn-soft rounded-pill px-4 historial-pill">
      <span class="d-inline-flex align-items-center gap-2">
        <span class="hist-dot"></span>
        <i class="bi bi-clock-history"></i>
        <span class="fw-semibold">Historial de Revisiones</span>
      </span>
    </a>
  </div>

  <div class="row g-3 mt-2">
    <div class="col-12 col-lg-8">
      <div class="nistmad-card p-4 h-100">
        <div class="nistmad-section-title">Estado del instrumento</div>
        <div class="d-flex justify-content-between align-items-start flex-wrap gap-3">
          <div>
            <div class="fw-bold">Estado del instrumento {badge}</div>
            <div class="text-muted small mt-1">Preguntas cargadas: <b>{total}</b></div>
            <div class="mt-2 small">{hint}</div>
          </div>
          <div class="text-end">
            <div class="text-muted small">Acceso rápido</div>
            <div class="d-flex gap-2 flex-wrap justify-content-end mt-2">
              {parametros_btn}
            </div>
          </div>
        </div>
        <div class="alert alert-info mt-3 mb-0 small">
          <b>Sugerencia:</b> Usa <b>Parámetros</b> para ver la definición de niveles 1–5
          y gestionar la importación del instrumento ISO 22301.
        </div>
      </div>
    </div>

    <div class="col-12 col-lg-4">
      <div class="nistmad-card p-4 h-100">
        <div class="nistmad-section-title">¿Qué puedes hacer aquí?</div>
        <ul class="small mb-0 text-black ps-3">
          <li><b>Ingresar la información:</b> diligenciar respuestas con evidencia.</li>
          <li><b>Historial:</b> revisar evaluaciones previas y resultados.</li>
          <li><b>Parámetros:</b> gestionar niveles e instrumento, excepto auditor.</li>
        </ul>
      </div>
    </div>
  </div>
</div>
{iso22301_nist_css('nistmad', '🛡️')}
"""
    return render_template_string(BASE, title="Madurez ISO 22301", content=content)

# ============================================================
# PARÁMETROS — USUARIO CON PERMISO PUEDE MODIFICAR / AUDITOR NO
# ============================================================

@iso22301_madurez_bp.route("/parametros", methods=["GET", "POST"])
@login_required
def parametros():
    user = User.query.get(session.get("user_id"))

    if not iso22301_user_can_execute(user):
        return iso22301_deny_execute("No tiene permiso para administrar parámetros ISO 22301.")

    seed_iso22301_parametros()

    if request.method == "POST":
        try:
            for r in Iso22301MadurezParametro.query.all():
                r.nivel = (request.form.get(f"nivel_{r.id}") or r.nivel).strip()
                r.rango_desde = float(request.form.get(f"desde_{r.id}") or r.rango_desde)
                r.rango_hasta = float(request.form.get(f"hasta_{r.id}") or r.rango_hasta)
                r.color = (request.form.get(f"color_{r.id}") or r.color).strip()
                r.descripcion = (request.form.get(f"descripcion_{r.id}") or "").strip()
            db.session.commit()
            flash("✅ Parámetros ISO 22301 guardados correctamente.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error guardando parámetros ISO 22301: {e}", "danger")
        return redirect(url_for("madurez_iso22301.parametros"))

    rows = []
    for r in Iso22301MadurezParametro.query.order_by(Iso22301MadurezParametro.orden.asc()).all():
        rows.append(f"""
        <tr>
          <td><input class="form-control" name="nivel_{r.id}" value="{escape(r.nivel or '')}"></td>
          <td class="text-center"><input class="form-control text-center" name="desde_{r.id}" value="{r.rango_desde}"></td>
          <td class="text-center"><input class="form-control text-center" name="hasta_{r.id}" value="{r.rango_hasta}"></td>
          <td class="text-center"><input type="color" class="form-control form-control-color mx-auto" name="color_{r.id}" value="{escape(r.color or '#6c757d')}"></td>
          <td><textarea class="form-control" name="descripcion_{r.id}" rows="2">{escape(r.descripcion or '')}</textarea></td>
        </tr>
        """)

    resumen = iso22301_resumen_instrumento()

    content = f"""
<div class="nistpar-shell">
  <div class="nistpar-header-card">
    <div class="nistpar-header-overlay">
      <div class="nistpar-header-text">
        <h3 class="nistpar-title m-0">Parámetros de Madurez — ISO 22301</h3>
        <div class="nistpar-subtitle">Configuración de niveles, rangos de madurez e importación del instrumento.</div>
      </div>
    </div>
  </div>

  <div class="nistpar-header-actions">
    <a href="{url_for('madurez_iso22301.inicio_iso22301')}" class="btn nistpar-btn-main rounded-pill px-4 fw-bold">
      <i class="bi bi-arrow-left me-2"></i>Volver
    </a>
    <form method="POST" action="{url_for('madurez_iso22301.importar_instrumento_iso22301')}" class="m-0">
      <button class="btn btn-success rounded-pill px-4 fw-bold">
        <i class="bi bi-upload me-2"></i>Importar instrumento
      </button>
    </form>
    <form method="POST" action="{url_for('madurez_iso22301.importar_instrumento_iso22301')}?force=1" class="m-0" onsubmit="return confirm('¿Borrar e importar de nuevo el instrumento ISO 22301?')">
      <button class="btn btn-danger rounded-pill px-4 fw-bold">
        <i class="bi bi-arrow-repeat me-2"></i>Reimportar
      </button>
    </form>
  </div>

  <div class="nistpar-card p-4 mb-3">
    <div class="nistpar-section-title">Resumen instrumento</div>
    <div class="small text-black">
      Preguntas: <b>{resumen['total_preguntas']}</b> · Cabeceras: <b>{resumen['total_headers']}</b> · Por capítulo: <b>{escape(str(resumen['por_bloque']))}</b>
    </div>
  </div>

  <form method="POST" class="nistpar-card p-4">
    <div class="nistpar-section-title">Niveles de madurez</div>
    <div class="table-responsive">
      <table class="table table-hover align-middle nistpar-table">
        <thead class="nistpar-table-head">
          <tr>
            <th style="width:28%;">Nivel de Madurez</th>
            <th class="text-center" style="width:110px;">Desde %</th>
            <th class="text-center" style="width:110px;">Hasta %</th>
            <th class="text-center" style="width:90px;">Color</th>
            <th>Descripción del Nivel</th>
          </tr>
        </thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </div>
    <div class="text-end mt-3">
      <button class="btn btn-primary rounded-pill px-4 fw-bold">
        <i class="bi bi-save me-2"></i>Guardar parámetros
      </button>
    </div>
  </form>
</div>
{iso22301_nist_css('nistpar', '⚙️')}
"""
    return render_template_string(BASE, title="Parámetros ISO 22301", content=content)


# ============================================================
# INGRESO DE INFORMACIÓN ISO 22301 — SIN LOADER GLOBAL EN VALIDACIÓN
# ============================================================

@iso22301_madurez_bp.route("/ingreso", methods=["GET"])
@login_required
def ingreso():
    user = User.query.get(session.get("user_id"))

    if not iso22301_user_can_execute(user):
        return iso22301_deny_execute("No tiene permiso para ingresar información ISO 22301.")

    if Iso22301MadurezPregunta.query.filter_by(tipo="q").count() == 0:
        flash("⚠️ Primero debes importar el instrumento ISO 22301.", "warning")
        return redirect(url_for("madurez_iso22301.parametros"))

    preguntas = (
        Iso22301MadurezPregunta.query
        .filter_by(activo=True, tipo="q")
        .order_by(
            Iso22301MadurezPregunta.bloque_codigo.asc(),
            Iso22301MadurezPregunta.seccion_codigo.asc(),
            Iso22301MadurezPregunta.orden.asc(),
            Iso22301MadurezPregunta.id.asc()
        )
        .all()
    )

    draft = obtener_borrador_iso22301(user.id if user else None)
    respuestas_guardadas = cargar_respuestas_iso22301(draft.id) if draft else {}
    consecutivo_val = (draft.consecutivo if draft else "") or ""

    _, _, progreso_inicial = calcular_progreso_iso22301(
        preguntas,
        respuestas_db=respuestas_guardadas
    )

    grouped = _iso22301_group_questions()
    acc_html = []
    acc_id = 0

    def esc(x):
        return escape(str(x or ""))

    for bloque_codigo, payload in grouped.items():
        acc_id += 1
        func_key = f"iso22301func{acc_id}"
        titulo_bloque = payload.get("titulo") or iso22301_block_title(bloque_codigo) or bloque_codigo
        rows = []

        for q in payload.get("items", []):
            saved = respuestas_guardadas.get(q.id, {})
            saved_estado = (saved.get("estado") or "").strip().upper()
            saved_com = esc(saved.get("comentario") or "")
            qtext = q.pregunta or ""
            evidence_hint = q.evidencia_sugerida or ""
            clause_code = q.seccion_codigo or ""
            domain_name = q.seccion_nombre or ""
            cat_code = q.pregunta_codigo or clause_code or bloque_codigo

            rows.append(f"""
            <div class="col-12 col-xl-6">
              <div class="nistform-qcard h-100">
                <div class="nistform-qhead">
                  <div class="d-flex align-items-center gap-2 flex-wrap">
                    <span class="badge rounded-pill text-bg-light border fw-semibold">{esc(cat_code)}</span>
                    <span class="badge rounded-pill text-bg-primary">Orden {q.orden or 0}</span>
                  </div>
                </div>

                <div class="small text-primary fw-bold mb-2">Cláusula {esc(clause_code)} · {esc(domain_name)}</div>
                <div class="nistform-qtext">{esc(qtext)}</div>
                {f'<div class="alert alert-light border small mt-3 mb-0"><b>Evidencia sugerida:</b> {esc(evidence_hint)}</div>' if evidence_hint else ''}

                <div class="nistform-radio-row">
                  <label class="nistform-radio-card">
                    <input class="form-check-input" type="radio" name="st_{q.id}" value="NA" {"checked" if saved_estado == "NA" else ""}>
                    <span>N/A</span>
                  </label>

                  <label class="nistform-radio-card">
                    <input class="form-check-input" type="radio" name="st_{q.id}" value="SI" {"checked" if saved_estado == "SI" else ""}>
                    <span>Sí</span>
                  </label>

                  <label class="nistform-radio-card">
                    <input class="form-check-input" type="radio" name="st_{q.id}" value="PARCIAL" {"checked" if saved_estado == "PARCIAL" else ""}>
                    <span>Parcial</span>
                  </label>

                  <label class="nistform-radio-card">
                    <input class="form-check-input" type="radio" name="st_{q.id}" value="NO" {"checked" if saved_estado == "NO" else ""}>
                    <span>No</span>
                  </label>
                </div>

                <div class="mt-3">
                  <label class="form-label small fw-bold text-black mb-1">Comentarios / evidencia</label>
                  <textarea class="form-control form-control-sm"
                            name="cm_{q.id}"
                            rows="3"
                            placeholder="Comentarios / evidencia">{saved_com}</textarea>
                </div>
              </div>
            </div>
            """)

        acc_html.append(f"""
        <div class="accordion-item nistform-acc-item">
          <h2 class="accordion-header" id="h{func_key}">
            <button class="accordion-button {'collapsed' if acc_id != 1 else ''}"
                    type="button"
                    data-bs-toggle="collapse"
                    data-bs-target="#c{func_key}">
              <div class="nistform-acc-inner">
                <div>
                  <div class="nistform-func-title">{esc(titulo_bloque)}</div>
                  <div class="nistform-func-subtitle">Capítulo ISO 22301 · {esc(bloque_codigo)}</div>
                </div>
                <span class="badge rounded-pill text-bg-primary">{len(payload.get('items', []))} preguntas</span>
              </div>
            </button>
          </h2>

          <div id="c{func_key}" class="accordion-collapse collapse {'show' if acc_id == 1 else ''}">
            <div class="accordion-body nistform-acc-body">
              <div class="nistform-cat-block">
                <div class="nistform-cat-title">
                  <span>{esc(bloque_codigo)}</span>
                  <small>{esc(titulo_bloque)}</small>
                </div>
                <div class="row g-3">{''.join(rows)}</div>
              </div>
            </div>
          </div>
        </div>
        """)

    alerta_borrador = ""
    if draft:
        alerta_borrador = f"""
        <div class="alert alert-info rounded-4 border-0 shadow-sm">
          <i class="bi bi-info-circle-fill me-2"></i>
          Tienes un borrador ISO 22301 cargado automáticamente.
          <strong>Progreso actual:</strong> {progreso_inicial}%.
        </div>
        """

    disabled_analizar = "" if progreso_inicial == 100 else "disabled"

    content = f"""
    <div class="nistform-shell iso22301-no-global-loader">

      <style>
        #SGSI_PROGRESS_GLOBAL,
        #globalLoader,
        #loader,
        #progressOverlay,
        .modal-backdrop,
        .progress-overlay,
        .loader-overlay,
        .sgsi-loader,
        .sgsi-progress {{
          display: none !important;
          visibility: hidden !important;
          opacity: 0 !important;
          pointer-events: none !important;
        }}
      </style>

      <div class="nistform-header-card">
        <div class="nistform-header-overlay">
          <div class="nistform-header-text">
            <h3 class="nistform-title m-0">Nivel de Madurez — ISO 22301</h3>
            <div class="nistform-subtitle">Ingreso de información del instrumento ISO 22301</div>
          </div>
        </div>
      </div>

      <div class="nistform-header-actions">
        <a href="{url_for('madurez_iso22301.inicio_iso22301')}" class="btn btn-light rounded-pill px-4 fw-bold">
          <i class="bi bi-arrow-left me-2"></i>Volver
        </a>

        <a href="{url_for('madurez_iso22301.historial')}" class="btn btn-outline-primary rounded-pill px-4 fw-bold">
          <i class="bi bi-clock-history me-2"></i>Historial
        </a>
      </div>

      <div class="nistform-card p-4">
        {alerta_borrador}

        <form id="iso22301IngresoForm"
              method="POST"
              action="{url_for('madurez_iso22301.ingreso_guardar')}"
              novalidate>

          <input type="hidden" name="draft_id" value="{draft.id if draft else ''}">
          <input type="hidden" name="accion" id="iso22301Accion" value="guardar">

          <div class="nistform-section-title">Información de la revisión</div>

          <div class="mb-4">
            <label class="text-black form-label fw-semibold">
              Consecutivo de la Revisión <span class="text-danger">*</span>
            </label>

            <input type="text"
                   class="form-control form-control-lg rounded-pill"
                   name="consecutivo"
                   id="iso22301Consecutivo"
                   value="{esc(consecutivo_val)}"
                   autocomplete="off">

            <div id="iso22301ConsecutivoError"
                 class="invalid-feedback d-none fw-bold mt-2">
              Debes ingresar el consecutivo de la Revisión.
            </div>
          </div>

          <div class="nistform-section-title">
            📊 Progreso del instrumento
          </div>

          <div class="mb-4">
            <div class="progress nistform-progress">
              <div id="iso22301ProgressBar"
                   class="progress-bar progress-bar-striped progress-bar-animated"
                   role="progressbar"
                   style="width:{progreso_inicial}%"
                   aria-valuemin="0"
                   aria-valuemax="100"
                   aria-valuenow="{progreso_inicial}">
                {progreso_inicial}%
              </div>
            </div>

            <div class="text-center small text-muted mt-2">
              <span id="iso22301ProgressText">{progreso_inicial}%</span> del instrumento completado
            </div>
          </div>

          <div class="nistform-section-title">Instrumento de evaluación</div>

          <div class="accordion nistform-accordion" id="accIso22301">
            {''.join(acc_html)}
          </div>

          <div class="d-flex justify-content-center gap-3 flex-wrap mt-4">
            <button class="btn btn-outline-primary btn-lg rounded-pill px-5 shadow fw-semibold"
                    type="button"
                    id="btnGuardarIso22301">
              <i class="bi bi-save2 me-2"></i>Guardar
            </button>

            <button id="btnAnalizarIso22301"
                    class="btn btn-primary btn-lg rounded-pill px-5 shadow fw-semibold"
                    type="button"
                    {disabled_analizar}>
              <i class="bi bi-bar-chart-line-fill me-2"></i>Analizar
            </button>
          </div>
        </form>
      </div>
    </div>

    <script>
    (function () {{

      const total = {len(preguntas)};

      function hideLoader() {{
        const ids = ["SGSI_PROGRESS_GLOBAL", "globalLoader", "loader", "progressOverlay"];
        ids.forEach(function(id) {{
          const el = document.getElementById(id);
          if (el) {{
            el.style.display = "none";
            el.style.visibility = "hidden";
            el.style.opacity = "0";
            el.style.pointerEvents = "none";
            el.classList.add("d-none");
          }}
        }});

        document.querySelectorAll(".modal-backdrop, .progress-overlay, .loader-overlay, .sgsi-loader, .sgsi-progress").forEach(function(el) {{
          el.style.display = "none";
          el.style.visibility = "hidden";
          el.style.opacity = "0";
          el.style.pointerEvents = "none";
          el.classList.add("d-none");
        }});
      }}

      function marcadas() {{
        const names = new Set();
        document.querySelectorAll('input[type="radio"][name^="st_"]:checked').forEach(function(r) {{
          names.add(r.name);
        }});
        return names.size;
      }}

      function actualizarProgresoIso22301() {{
        const respondidas = marcadas();
        const porcentaje = total > 0 ? Math.round((respondidas / total) * 100) : 0;
        const bar = document.getElementById("iso22301ProgressBar");
        const text = document.getElementById("iso22301ProgressText");
        const btnAnalizar = document.getElementById("btnAnalizarIso22301");

        if (bar) {{
          bar.style.width = porcentaje + "%";
          bar.innerText = porcentaje + "%";
          bar.setAttribute("aria-valuenow", porcentaje);
        }}

        if (text) {{
          text.innerText = porcentaje + "%";
        }}

        if (btnAnalizar) {{
          btnAnalizar.disabled = porcentaje < 100;
          btnAnalizar.classList.toggle("disabled", porcentaje < 100);
        }}
      }}

      function validarConsecutivo() {{
        const consecutivo = document.getElementById("iso22301Consecutivo");
        const msg = document.getElementById("iso22301ConsecutivoError");

        if (!consecutivo || !consecutivo.value.trim()) {{
          hideLoader();

          if (consecutivo) {{
            consecutivo.classList.add("is-invalid");
            consecutivo.focus();
          }}

          if (msg) {{
            msg.classList.remove("d-none");
            msg.style.display = "block";
          }}

          return false;
        }}

        consecutivo.classList.remove("is-invalid");

        if (msg) {{
          msg.classList.add("d-none");
          msg.style.display = "none";
        }}

        return true;
      }}

      function enviarIso22301(accion) {{
        hideLoader();

        if (!validarConsecutivo()) {{
          hideLoader();
          return false;
        }}

        if (accion === "analizar" && marcadas() < total) {{
          hideLoader();
          alert("Para analizar debes completar el 100% del instrumento.");
          return false;
        }}

        const form = document.getElementById("iso22301IngresoForm");
        const accionInput = document.getElementById("iso22301Accion");

        if (!form) {{
          return false;
        }}

        if (accionInput) {{
          accionInput.value = accion;
        }}

        hideLoader();

        HTMLFormElement.prototype.submit.call(form);
        return false;
      }}

      window.iso22301GuardarSinLoader = function(e) {{
        if (e) {{
          e.preventDefault();
          e.stopPropagation();
          e.stopImmediatePropagation();
        }}
        return enviarIso22301("guardar");
      }};

      window.iso22301AnalizarSinLoader = function(e) {{
        if (e) {{
          e.preventDefault();
          e.stopPropagation();
          e.stopImmediatePropagation();
        }}
        return enviarIso22301("analizar");
      }};

      document.addEventListener("DOMContentLoaded", function () {{
        hideLoader();

        const btnGuardar = document.getElementById("btnGuardarIso22301");
        const btnAnalizar = document.getElementById("btnAnalizarIso22301");
        const consecutivo = document.getElementById("iso22301Consecutivo");
        const form = document.getElementById("iso22301IngresoForm");

        if (btnGuardar) {{
          btnGuardar.onclick = iso22301GuardarSinLoader;
        }}

        if (btnAnalizar) {{
          btnAnalizar.onclick = iso22301AnalizarSinLoader;
        }}

        if (consecutivo) {{
          consecutivo.addEventListener("input", function() {{
            validarConsecutivo();
            hideLoader();
          }});
        }}

        if (form) {{
          form.addEventListener("submit", function(e) {{
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            hideLoader();
            return false;
          }}, true);
        }}

        document.querySelectorAll('input[type="radio"][name^="st_"]').forEach(function(radio) {{
          radio.addEventListener("change", actualizarProgresoIso22301);
        }});

        actualizarProgresoIso22301();
        hideLoader();
        setInterval(hideLoader, 250);
      }});
    }})();
    </script>

    {iso22301_nistform_css()}
    """

    return render_template_string(BASE, title="Ingreso ISO 22301", content=content)


# ============================================================
# GUARDAR / ANALIZAR — ISO 22301
# ============================================================

@iso22301_madurez_bp.route("/ingreso/guardar", methods=["POST"])
@login_required
def ingreso_guardar():
    user = User.query.get(session.get("user_id"))

    if not iso22301_user_can_execute(user):
        return iso22301_deny_execute("No tiene permiso para guardar ni analizar información ISO 22301.")

    consecutivo = (request.form.get("consecutivo") or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    accion = (request.form.get("accion") or "guardar").strip().lower()
    draft_id = (request.form.get("draft_id") or "").strip()

    if not consecutivo:
        flash("Debes ingresar el consecutivo de la Revisión.", "warning")
        return redirect(url_for("madurez_iso22301.ingreso"))

    preguntas = (
        Iso22301MadurezPregunta.query
        .filter_by(activo=True, tipo="q")
        .order_by(
            Iso22301MadurezPregunta.bloque_codigo.asc(),
            Iso22301MadurezPregunta.orden.asc(),
            Iso22301MadurezPregunta.id.asc()
        )
        .all()
    )

    if not preguntas:
        flash("⚠️ No hay preguntas activas cargadas en el instrumento ISO 22301.", "warning")
        return redirect(url_for("madurez_iso22301.inicio_iso22301"))

    respondidas, total, progreso_pct = calcular_progreso_iso22301(preguntas, form_data=request.form)

    try:
        run = None

        if draft_id and draft_id.isdigit():
            run = Iso22301MadurezRun.query.filter_by(id=int(draft_id)).first()

        if not run:
            run = obtener_borrador_iso22301(user.id if user else None)

        if respondidas == 0:
            if run and _contar_respuestas_run_iso22301(run.id) == 0:
                Iso22301MadurezRespuesta.query.filter_by(run_id=run.id).delete(synchronize_session=False)
                Iso22301MadurezCriterioAnalisis.query.filter_by(run_id=run.id).delete(synchronize_session=False)
                db.session.delete(run)
                db.session.commit()

            flash("⚠️ Debes responder al menos una pregunta antes de guardar o analizar.", "warning")
            return redirect(url_for("madurez_iso22301.ingreso"))

        if not run:
            run = Iso22301MadurezRun(
                consecutivo=consecutivo,
                company_name=consecutivo,
                user_id=user.id if user else None,
                estado="BORRADOR",
                progreso_pct=0,
                resumen_json="{}",
                pct_general=0.0,
                radar_overall_b64=None
            )
            db.session.add(run)
            db.session.flush()

        run.consecutivo = consecutivo
        run.company_name = consecutivo
        run.user_id = user.id if user else run.user_id
        run.progreso_pct = progreso_pct
        run.updated_at = datetime.utcnow()

        Iso22301MadurezRespuesta.query.filter_by(run_id=run.id).delete(synchronize_session=False)

        respuestas_insertadas = 0

        for q in preguntas:
            st = (request.form.get(f"st_{q.id}") or "").strip().upper()
            cm = (request.form.get(f"cm_{q.id}") or "").replace("\r\n", "\n").replace("\r", "\n").strip()

            if st in ("SI", "PARCIAL", "NO", "NA"):
                db.session.add(Iso22301MadurezRespuesta(
                    run_id=run.id,
                    pregunta_id=q.id,
                    estado=st,
                    comentario=cm
                ))
                respuestas_insertadas += 1

        if accion == "analizar":
            if progreso_pct < 100:
                db.session.commit()
                flash("⚠️ Para analizar debes completar el 100% del instrumento.", "warning")
                return redirect(url_for("madurez_iso22301.ingreso"))

            run.estado = "FINALIZADO"
            run.progreso_pct = 100
            db.session.commit()

            run_id = run_analysis_from_iso22301_run(run.id)

            flash(f"✅ Revisión ISO 22301 analizada correctamente. Se consolidaron {respuestas_insertadas} respuestas.", "success")
            return redirect(url_for("madurez_iso22301.detalle", run_id=run_id))

        db.session.commit()
        flash("✅ Información ISO 22301 guardada correctamente.", "success")
        return redirect(url_for("madurez_iso22301.ingreso"))

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        flash(f"❌ Error guardando la revisión ISO 22301: {e}", "danger")
        return redirect(url_for("madurez_iso22301.ingreso"))

# ============================================================
# HISTORIAL ISO 22301 — COMPACTO SIN LOADER
# ============================================================

@iso22301_madurez_bp.route("/historial", methods=["GET"])
@login_required
def historial():

    user = User.query.get(session.get("user_id"))

    denied = iso22301_check_access_or_redirect(
        user,
        "No tiene permiso para ver historial ISO 22301."
    )

    if denied:
        return denied

    runs = (
        Iso22301MadurezRun.query
        .filter(Iso22301MadurezRun.estado == "FINALIZADO")
        .order_by(
            Iso22301MadurezRun.created_at.desc(),
            Iso22301MadurezRun.id.desc()
        )
        .all()
    )

    # Actualiza evaluaciones históricas creadas con la fórmula anterior,
    # sin incluir N/A en el denominador. Se reconstruye el resumen para
    # corregir también capítulos que tienen únicamente respuestas N/A.
    historial_actualizado = False
    for run in runs:
        resumen_corregido = _iso22301_build_resumen(run.id)
        resumen_json_corregido = json.dumps(resumen_corregido, ensure_ascii=False)
        pct_corregido = iso22301_pct_general_from_resumen(resumen_corregido)

        if (run.resumen_json or "{}") != resumen_json_corregido:
            run.resumen_json = resumen_json_corregido
            historial_actualizado = True

        if abs(float(run.pct_general or 0) - pct_corregido) > 0.005:
            run.pct_general = pct_corregido
            historial_actualizado = True
    if historial_actualizado:
        db.session.commit()

    # =========================================================
    # BOTÓN NUEVA REVISIÓN
    # =========================================================
    nueva_revision_btn = ""

    if iso22301_user_can_execute(user):

        nueva_revision_btn = f"""
        <a href="{url_for('madurez_iso22301.ingreso')}"
           class="btn btn-primary btn-sm rounded-pill px-3 fw-bold shadow-sm iso22301-no-loader grac-nav-blue-btn">

          <i class="bi bi-plus-circle me-1"></i>
          Nueva revisión

        </a>
        """

    # =========================================================
    # FILAS
    # =========================================================
    rows = []

    for run in runs:

        nivel = iso22301_resolver_nivel(run.pct_general or 0)

        badge = f"""
        <span class="iso22301hist-badge"
              style="background:{nivel.get('color','#6c757d')};">

          {escape(nivel.get('nivel','Sin nivel'))}

        </span>
        """

        eliminar_btn = ""

        if iso22301_user_can_execute(user):

            eliminar_btn = f"""
            <form method="POST"
                  action="{url_for('madurez_iso22301.eliminar_run', run_id=run.id)}"
                  class="d-inline iso22301-no-loader"
                  onsubmit="return confirm('¿Seguro que deseas eliminar esta revisión ISO 22301?');">

              <button type="submit"
                      class="btn btn-danger btn-xs iso22301hist-btn">

                <i class="bi bi-trash"></i>
                Eliminar

              </button>

            </form>
            """

        rows.append(f"""
        <tr>

          <td class="fw-semibold iso22301hist-text-main">
            {escape(run.consecutivo or '')}
          </td>

          <td class="text-center iso22301hist-text">
            {run.created_at.strftime('%Y-%m-%d %H:%M') if run.created_at else ''}
          </td>

          <td class="text-center">
            <span class="iso22301hist-pct">
              {float(run.pct_general or 0):.2f}%
            </span>
          </td>

          <td class="text-center">
            {badge}
          </td>

          <td class="text-center">

            <div class="d-flex justify-content-center gap-1 flex-wrap">

              <a href="{url_for('madurez_iso22301.detalle', run_id=run.id)}"
                 class="btn btn-primary btn-xs iso22301hist-btn iso22301-no-loader">

                <i class="bi bi-eye"></i>
                Ver

              </a>

              {eliminar_btn}

            </div>

          </td>

        </tr>
        """)

    # =========================================================
    # VACÍO
    # =========================================================
    if not rows:

        rows.append("""
        <tr>
          <td colspan="5"
              class="text-center text-muted py-4">

            No existen revisiones ISO 22301 finalizadas.

          </td>
        </tr>
        """)

    # =========================================================
    # HTML
    # =========================================================
    content = f"""

    <div class="iso22301hist-shell">

      <!-- HEADER -->
      <div class="iso22301hist-header-card">

        <div class="iso22301hist-header-overlay">

          <div class="iso22301hist-header-text">

            <h3 class="iso22301hist-title m-0">
              Historial de Revisiones — ISO 22301
            </h3>

            <div class="iso22301hist-subtitle">
              Consulta de evaluaciones históricas y resultados consolidados.
            </div>

          </div>

        </div>

      </div>

      <!-- BOTONES -->
      <div class="iso22301hist-header-actions">

        <a href="{url_for('madurez_iso22301.inicio_iso22301')}"
           class="btn btn-light btn-sm rounded-pill px-3 fw-bold shadow-sm iso22301-no-loader">

          <i class="bi bi-arrow-left me-1"></i>
          Volver

        </a>

        {nueva_revision_btn}

      </div>

      <!-- TABLA -->
      <div class="iso22301hist-card">

        <div class="iso22301hist-section-title">
          Revisiones finalizadas
        </div>

        <div class="table-responsive">

          <table class="table table-hover align-middle iso22301hist-table">

            <thead>
              <tr>
                <th>Consecutivo</th>
                <th class="text-center">Fecha</th>
                <th class="text-center">% Cumplimiento</th>
                <th class="text-center">Nivel</th>
                <th class="text-center">Acciones</th>
              </tr>
            </thead>

            <tbody>
              {''.join(rows)}
            </tbody>

          </table>

        </div>

      </div>

    </div>

    <!-- =================================================== -->
    <!-- CSS -->
    <!-- =================================================== -->

    <style>

      body {{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }}

      .iso22301hist-shell {{
        width:94%;
        max-width:1180px;
        margin:8px auto 24px auto;
      }}

      .iso22301hist-header-card {{
        background:linear-gradient(
          135deg,
          #2f6fb6 0%,
          #3f86d6 55%,
          #5aa3ea 100%
        );

        height:72px;

        display:flex;
        align-items:center;
        justify-content:center;

        border-radius:16px;

        box-shadow:0 10px 24px rgba(0,0,0,.24);

        margin-bottom:10px;
        overflow:hidden;
      }}

      .iso22301hist-header-overlay {{
        width:100%;
        height:100%;

        display:flex;
        align-items:center;
        justify-content:center;

        text-align:center;

        background:rgba(0,0,0,.08);

        padding:6px 18px;
      }}

      .iso22301hist-title {{
        color:#fff;
        font-size:1.28rem;
        font-weight:800;
        line-height:1.1;
        text-shadow:0 2px 8px rgba(0,0,0,.28);
      }}

      .iso22301hist-subtitle {{
        color:rgba(248,252,255,.96);
        font-size:.78rem;
        margin-top:3px;
        font-weight:500;
      }}

      .iso22301hist-header-actions {{
        display:flex;
        justify-content:center;
        align-items:center;
        gap:6px;
        flex-wrap:wrap;
        margin:8px 0 10px 0;
      }}

      .iso22301hist-card {{
        background:rgba(255,255,255,.95);
        border:1px solid rgba(255,255,255,.60);
        border-radius:16px;
        box-shadow:0 10px 24px rgba(0,0,0,.20);
        padding:12px;
        overflow:hidden;
      }}

      .iso22301hist-section-title {{
        color:#0f3d68;
        font-size:.92rem;
        font-weight:800;
        margin-bottom:8px;
        padding-bottom:6px;
        border-bottom:1px solid rgba(15,61,104,.12);
      }}

      .iso22301hist-table {{
        margin-bottom:0;
        font-size:.80rem;
      }}

      .iso22301hist-table thead th {{
        background:#0f3d68;
        color:#fff;
        font-size:.74rem;
        font-weight:800;
        padding:7px 8px;
        vertical-align:middle;
        white-space:nowrap;
      }}

      .iso22301hist-table tbody td {{
        padding:6px 8px;
        vertical-align:middle;
        background:rgba(255,255,255,.96);
        border-bottom:1px solid rgba(15,61,104,.08);
      }}

      .iso22301hist-table tbody tr:hover td {{
        background:#eef6ff;
      }}

      .iso22301hist-text-main {{
        color:#0b1220;
        font-size:.80rem;
      }}

      .iso22301hist-text {{
        color:#374151;
        font-size:.68rem;
      }}

      .iso22301hist-pct {{
        color:#0d6efd;
        font-weight:800;
        font-size:.80rem;
      }}

      .iso22301hist-badge {{
        display:inline-block;
        color:#fff;
        font-size:.68rem;
        font-weight:800;
        padding:4px 8px;
        border-radius:999px;
        line-height:1;
        white-space:nowrap;
      }}

      .iso22301hist-btn {{
        border-radius:999px !important;
        padding:3px 8px !important;
        font-size:.64rem !important;
        font-weight:700 !important;
        line-height:1.2 !important;
      }}

      .btn-xs {{
        --bs-btn-padding-y:.16rem;
        --bs-btn-padding-x:.40rem;
        --bs-btn-font-size:.70rem;
      }}

    </style>

    <!-- =================================================== -->
    <!-- DESACTIVAR LOADER -->
    <!-- =================================================== -->

    <script>

      document.addEventListener("DOMContentLoaded", function() {{

        // ==========================================
        // QUITAR OVERLAY GLOBAL
        // ==========================================
        const overlays = [
          "SGSI_PROGRESS_GLOBAL",
          "globalLoader",
          "loader",
          "progressOverlay"
        ];

        overlays.forEach(function(id) {{

          const el = document.getElementById(id);

          if (el) {{
            el.style.display = "none";
            el.style.visibility = "hidden";
            el.classList.add("d-none");
          }}

        }});

        // ==========================================
        // DESACTIVAR SHOWLOADER
        // ==========================================
        document.querySelectorAll(".iso22301-no-loader").forEach(function(el) {{

          el.removeAttribute("onclick");
          el.onclick = null;

        }});

      }});

    </script>
    """

    return render_template_string(
        BASE,
        title="Historial ISO 22301",
        content=content
    )


# ============================================================
# ISO 22301 — DETALLE POR CRITERIO
# ============================================================

@iso22301_madurez_bp.route("/detalle/<int:run_id>/criterio/<bloque_codigo>", methods=["GET"])
@login_required
def detalle_criterio(run_id: int, bloque_codigo: str):
    user = User.query.get(session.get("user_id"))

    if not iso22301_user_can_access(user):
        return iso22301_deny_access("No tiene permiso para ver el detalle del capítulo ISO 22301.")

    run = Iso22301MadurezRun.query.get_or_404(run_id)
    bloque_codigo = (bloque_codigo or "").strip().upper()

    try:
        resumen = json.loads(run.resumen_json or "{}")
    except Exception:
        resumen = {}

    d = resumen.get(bloque_codigo)
    if not d:
        flash("No se encontró información para este capítulo ISO 22301.", "warning")
        return redirect(url_for("madurez_iso22301.detalle", run_id=run.id))

    items = d.get("items", []) or []
    nombre = d.get("nombre") or iso22301_block_title(bloque_codigo) or bloque_codigo
    pct = float(d.get("pct", 0) or 0)
    aplicables = int(d.get("validas", 0) or 0)
    nivel = (
        iso22301_nivel_visual_por_pct(pct)
        if aplicables > 0
        else {"nivel": "No aplica", "score": 0, "color": "#6c757d"}
    )

    rows = []
    for it in items:
        estado = (it.get("estado") or "").upper()
        color = {
            "SI": "success",
            "PARCIAL": "warning text-dark",
            "NO": "danger",
            "NA": "secondary"
        }.get(estado, "secondary")

        rows.append(f"""
        <tr>
          <td style="width:120px;">
            <span class="badge bg-light text-primary border">
              {escape(it.get("pregunta_codigo") or "")}
            </span>
          </td>
          <td>
            <div class="fw-bold text-dark">{escape(it.get("pregunta") or "")}</div>
            <div class="small text-muted mt-1">{escape(it.get("comentario") or "")}</div>
          </td>
          <td class="text-center" style="width:110px;">
            <span class="badge bg-{color}">{escape(estado)}</span>
          </td>
        </tr>
        """)

    content = f"""
    <div class="nistdet-shell">

      <div class="nistdet-header-card">
        <div class="nistdet-header-overlay">
          <div class="nistdet-header-text">
            <h3 class="nistdet-title m-0">Preguntas ISO 22301 — {escape(nombre)}</h3>
            <div class="nistdet-subtitle">
              Consecutivo: <b>{escape(run.consecutivo or '')}</b>
              · Cumplimiento: <b>{pct:.2f}%</b>
              · Nivel: <b>{escape(nivel.get("nivel",""))}</b>
            </div>
          </div>
        </div>
      </div>

      <div class="nistdet-header-actions">
        <a href="{url_for('madurez_iso22301.detalle', run_id=run.id)}"
           class="btn nistdet-btn-main rounded-pill px-4 fw-bold">
          <i class="bi bi-arrow-left me-2"></i>Volver al detalle
        </a>
      </div>

      <div class="nistdet-card p-4">
        <div class="nistdet-section-title mb-3">{escape(nombre)}</div>

        <div class="table-responsive">
          <table class="table table-sm table-hover align-middle mb-0">
            <thead class="table-light">
              <tr>
                <th>Código</th>
                <th>Pregunta / Evidencia</th>
                <th class="text-center">Estado</th>
              </tr>
            </thead>
            <tbody>
              {''.join(rows)}
            </tbody>
          </table>
        </div>
      </div>
    </div>

    {iso22301_nist_css('nistdet', '📊')}
    """

    return render_template_string(BASE, title="Detalle capítulo ISO 22301", content=content)


# ============================================================
# ISO 22301 — ANÁLISIS POR CRITERIO
# ============================================================

@iso22301_madurez_bp.route("/detalle/<int:run_id>/criterio/<bloque_codigo>/analisis", methods=["GET", "POST"])
@login_required
def analisis_criterio(run_id: int, bloque_codigo: str):
    user = User.query.get(session.get("user_id"))

    if not iso22301_user_can_access(user):
        return iso22301_deny_access("No tiene permiso para ver el análisis ISO 22301.")

    run = Iso22301MadurezRun.query.get_or_404(run_id)
    bloque_codigo = (bloque_codigo or "").strip().upper()

    try:
        resumen = json.loads(run.resumen_json or "{}")
    except Exception:
        resumen = {}

    d = resumen.get(bloque_codigo)
    if not d:
        flash("No se encontró información para este capítulo ISO 22301.", "warning")
        return redirect(url_for("madurez_iso22301.detalle", run_id=run.id))

    nombre = d.get("nombre") or iso22301_block_title(bloque_codigo) or bloque_codigo
    pct = float(d.get("pct", 0) or 0)
    items = d.get("items", []) or []
    aplicables = int(d.get("validas", 0) or 0)

    analisis = Iso22301MadurezCriterioAnalisis.query.filter_by(
        run_id=run.id,
        bloque_codigo=bloque_codigo
    ).first()

    if request.method == "POST":
        if not iso22301_user_can_execute(user):
            return iso22301_deny_execute("El rol Auditor no puede generar análisis con IA.")

        if aplicables <= 0:
            flash("Este capítulo no tiene preguntas aplicables; todas fueron marcadas N/A.", "warning")
            return redirect(url_for("madurez_iso22301.analisis_criterio", run_id=run.id, bloque_codigo=bloque_codigo))

        prompt = _iso22301_ai_prompt_criterio(run, bloque_codigo, nombre, pct, items)

        try:
            raw = _iso22301_ai_text(prompt, max_tokens=1200)
            obj = _extraer_json_objeto_iso22301(raw)

            estado_actual = (obj.get("estado_actual") or "").strip() if isinstance(obj, dict) else ""
            estado_requerido = (obj.get("estado_requerido") or "").strip() if isinstance(obj, dict) else ""
            plan_raw = json.dumps(obj.get("plan_accion", []), ensure_ascii=False) if isinstance(obj, dict) else raw
            plan_txt = _build_plan_accion_iso22301_texto(obj.get("plan_accion", [])) if isinstance(obj, dict) else raw

            if not analisis:
                analisis = Iso22301MadurezCriterioAnalisis(
                    run_id=run.id,
                    bloque_codigo=bloque_codigo,
                    bloque_nombre=nombre
                )
                db.session.add(analisis)

            analisis.estado_actual = estado_actual
            analisis.estado_requerido = estado_requerido
            analisis.plan_accion_ai = plan_txt or plan_raw
            analisis.plan_accion_editado = plan_txt or plan_raw
            db.session.commit()

            flash("✅ Análisis ISO 22301 generado con IA.", "success")

        except Exception as e:
            db.session.rollback()
            traceback.print_exc()
            flash(f"❌ Error generando análisis ISO 22301: {e}", "danger")

        return redirect(url_for("madurez_iso22301.analisis_criterio", run_id=run.id, bloque_codigo=bloque_codigo))

    estado_actual = analisis.estado_actual if analisis else ""
    estado_requerido = analisis.estado_requerido if analisis else ""
    plan_accion = _normalizar_plan_accion_iso22301_texto(
        (analisis.plan_accion_editado or analisis.plan_accion_ai) if analisis else ""
    )

    boton_generar = ""
    if iso22301_user_can_execute(user):
        boton_generar = """
        <form method="POST" class="m-0">
          <button type="submit" class="btn nistdet-btn-success rounded-pill px-4 fw-bold">
            <i class="bi bi-magic me-2"></i>Generar análisis IA
          </button>
        </form>
        """
    else:
        boton_generar = """
        <button class="btn btn-secondary rounded-pill px-4 fw-bold" disabled>
          <i class="bi bi-lock me-2"></i>Solo lectura
        </button>
        """

    content = f"""
    <div class="nistdet-shell">

      <div class="nistdet-header-card">
        <div class="nistdet-header-overlay">
          <div class="nistdet-header-text">
            <h3 class="nistdet-title m-0">Análisis ISO 22301 — {escape(nombre)}</h3>
            <div class="nistdet-subtitle">
              Consecutivo: <b>{escape(run.consecutivo or '')}</b>
              · Cumplimiento: <b>{pct:.2f}%</b>
            </div>
          </div>
        </div>
      </div>

      <div class="nistdet-header-actions">
        <a href="{url_for('madurez_iso22301.detalle', run_id=run.id)}"
           class="btn nistdet-btn-main rounded-pill px-4 fw-bold">
          <i class="bi bi-arrow-left me-2"></i>Volver al detalle
        </a>
        {boton_generar}
      </div>

      <div class="row g-3">
        <div class="col-12 col-xl-6">
          <div class="nistdet-card p-4 h-100">
            <div class="nistdet-section-title">Estado actual</div>
            <div class="nistdet-exec-box mt-3">
              {escape(estado_actual) if estado_actual else "No se ha generado análisis."}
            </div>
          </div>
        </div>

        <div class="col-12 col-xl-6">
          <div class="nistdet-card p-4 h-100">
            <div class="nistdet-section-title">Estado requerido</div>
            <div class="nistdet-exec-box mt-3">
              {escape(estado_requerido) if estado_requerido else "No se ha generado análisis."}
            </div>
          </div>
        </div>

        <div class="col-12">
          <div class="nistdet-card p-4">
            <div class="nistdet-section-title">Plan de acción</div>
            <div class="nistdet-exec-box mt-3">
              <pre class="mb-0" style="white-space:pre-wrap;font-family:inherit;">{escape(plan_accion) if plan_accion else "No se ha generado plan de acción."}</pre>
            </div>
          </div>
        </div>
      </div>

    </div>

    {iso22301_nist_css('nistdet', '📊')}
    """

    return render_template_string(BASE, title="Análisis capítulo ISO 22301", content=content)

# ============================================================
# DETALLE ISO 22301 — MISMO DISEÑO NIST
# ============================================================

@iso22301_madurez_bp.route("/detalle/<int:run_id>", methods=["GET"])
@login_required
def detalle(run_id: int):
    user = User.query.get(session.get("user_id"))

    if not iso22301_user_can_access(user):
        return iso22301_deny_access("No tiene permiso para ver el detalle ISO 22301.")

    # Recalcula también las evaluaciones anteriores con la fórmula vigente.
    run_analysis_from_iso22301_run(run_id)
    run = Iso22301MadurezRun.query.get_or_404(run_id)
    try:
        resumen = json.loads(run.resumen_json or "{}")
    except Exception:
        resumen = {}

    def _nl2br_iso22301(s: str) -> str:
        txt = iso22301_normalizar_texto_rico_guardado(s or "")
        return txt.replace("\n", "<br>")

    radar_labels, radar_values = iso22301_pct_por_criterio(resumen, ISO22301_BLOCK_ORDER)
    radar_b64 = run.radar_overall_b64 or iso22301_radar_b64(
        radar_labels,
        radar_values,
        title="Radar por Capítulo"
    )

    informe_ai = iso22301_normalizar_texto_rico_guardado(run.informe_ejecutivo_ai or "")
    informe_editado = iso22301_normalizar_texto_rico_guardado(run.informe_ejecutivo_editado or "")
    informe_mostrar = informe_editado if informe_editado else informe_ai

    nivel_general = iso22301_nivel_visual_por_pct(run.pct_general)
    nivel_general_texto = (nivel_general.get("nivel") or "").strip()
    nivel_general_nombre = nivel_general_texto.split(":", 1)[1].strip() if ":" in nivel_general_texto else nivel_general_texto

    botones_ia = ""
    if iso22301_user_can_execute(user):
        botones_ia = f"""
          <form method="POST"
                  action="{url_for('madurez_iso22301.informe_ejecutivo_generar', run_id=run.id)}"
                  class="m-0">
              <button type="submit" class="btn nistdet-btn-success rounded-pill px-4 fw-bold">
                <i class="bi bi-magic me-2"></i>Generar con IA
              </button>
            </form>

            <a href="{url_for('madurez_iso22301.informe_ejecutivo_editar', run_id=run.id)}"
               class="btn btn-primary rounded-pill px-4 fw-bold">
              <i class="bi bi-pencil-square me-2"></i>Editar
            </a>
        """
    else:
        botones_ia = """
          <button class="btn btn-secondary rounded-pill px-4 fw-bold" disabled>
            <i class="bi bi-lock me-2"></i>Solo lectura
          </button>
        """

    pdf_btn = ""
    if iso22301_user_can_access(user):
        pdf_btn = f"""
        <a href="{url_for('madurez_iso22301.exportar_pdf', run_id=run.id)}"
           class="btn btn-danger rounded-pill px-4 fw-bold">
          <i class="bi bi-file-earmark-pdf me-2"></i>Exportar PDF
        </a>
        """

    top_html = f"""
    <div class="row g-3 mb-4">

      <div class="col-12 col-xl-5">
        <div class="nistdet-card p-4 h-100">
          <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-2">
            <div>
              <div class="nistdet-card-title">📊 Radar por Capítulo General</div>
              <div class="text-muted small">
                Resultado consolidado por criterios ISO 22301.
              </div>
            </div>

            <div class="text-end">
              <div class="badge rounded-pill px-3 py-2"
                   style="background:{nivel_general.get('color','#6c757d')}; color:#fff; font-size:.82rem;">
                Nivel {nivel_general.get('score', 0)}
              </div>
              <div class="small text-muted mt-1">{escape(nivel_general_nombre)}</div>
            </div>
          </div>

          <div class="text-center mt-3">
            {f'<img class="img-fluid nistdet-radar-img-small" src="data:image/png;base64,{radar_b64}">' if radar_b64 else '<div class="alert alert-warning mb-0">No fue posible generar el radar.</div>'}
          </div>
        </div>
      </div>

      <div class="col-12 col-xl-7">
        <div class="nistdet-card p-4 h-100">
          <div class="d-flex justify-content-between align-items-center flex-wrap gap-2">
            <div>
              <div class="nistdet-card-title">🧾 Informe ejecutivo</div>
              <div class="text-muted small">
                Síntesis ejecutiva generada con IA a partir de los resultados por capítulo ISO 22301.
              </div>
            </div>

            <div class="d-flex gap-2 flex-wrap">
              {botones_ia}
            </div>
          </div>

          <div class="nistdet-exec-box mt-3">
            {f'<div class="nistdet-exec-text">{_nl2br_iso22301(escape(informe_mostrar))}</div>' if informe_mostrar else '''
              <div class="text-center py-4">
                <div class="mb-2" style="font-size:2rem;">&#129302;</div>
                <div class="fw-bold text-black">Aún no hay informe ejecutivo</div>
                <div class="text-muted small mt-1">
                  No se ha generado informe ejecutivo para esta revisión.
                </div>
              </div>
            '''}
          </div>
        </div>
      </div>

    </div>
    """

    def gauge_svg_categoria(pct, color="#2f6fb6"):
        try:
            pct = max(0, min(100, float(pct or 0)))
        except Exception:
            pct = 0.0

        radius = 44
        circumference = math.pi * radius
        progress = circumference * (pct / 100.0)

        return f"""
        <svg width="150" height="96" viewBox="0 0 120 78" aria-hidden="true">
          <path d="M16 62 A44 44 0 0 1 104 62"
                fill="none" stroke="#e9ecef" stroke-width="10" stroke-linecap="round"/>
          <path d="M16 62 A44 44 0 0 1 104 62"
                fill="none" stroke="{color}" stroke-width="10" stroke-linecap="round"
                stroke-dasharray="{progress:.2f} {circumference:.2f}"/>
          <text x="60" y="46" text-anchor="middle"
                style="font-size:15px;font-weight:800;fill:#111;">{pct:.0f}%</text>
          <text x="17" y="74" text-anchor="middle"
                style="font-size:10px;fill:#6c757d;">0</text>
          <text x="103" y="74" text-anchor="middle"
                style="font-size:10px;fill:#6c757d;">100</text>
        </svg>
        """

    criterio_cards = []

    for code in ISO22301_BLOCK_ORDER:
        if code not in resumen:
            continue

        d = resumen.get(code, {}) or {}

        pct = float(d.get("pct", 0) or 0)
        total = int(d.get("total", 0) or 0)
        aplicables = int(d.get("validas", 0) or 0)
        no_aplica = int(d.get("NA", 0) or 0)
        nombre_criterio = (d.get("nombre") or iso22301_block_title(code) or code).strip()

        nivel_data = (
            iso22301_nivel_visual_por_pct(pct)
            if aplicables > 0
            else {"nivel": "No aplica", "score": 0, "color": "#6c757d"}
        )
        nivel_score = nivel_data.get("score", "")
        nivel_texto = (nivel_data.get("nivel") or "").strip()
        nivel_nombre = nivel_texto.split(":", 1)[1].strip() if ":" in nivel_texto else nivel_texto

        gauge_html = gauge_svg_categoria(pct, nivel_data.get("color", "#2f6fb6"))

        criterio_cards.append(f"""
        <div class="col-12 col-md-6 col-xl-4">
          <div class="nistdet-subcard h-100">

            <div class="nistdet-subcard-top">
              <div class="text-center">
                {gauge_html}
              </div>
            </div>

            <div class="nistdet-subcard-body">
              <div class="nistdet-row">
                <div class="nistdet-label">Criterio</div>
                <div class="nistdet-value fw-bold">{escape(code)}</div>
              </div>

              <div class="nistdet-row">
                <div class="nistdet-label">Nombre</div>
                <div class="nistdet-value nistdet-value-wrap">{escape(nombre_criterio)}</div>
              </div>

              <div class="nistdet-row">
                <div class="nistdet-label">% Cumplimiento</div>
                <div class="nistdet-value fw-bold">{pct:.2f}%</div>
              </div>

              <div class="nistdet-row">
                <div class="nistdet-label">Nivel de Madurez</div>
                <div class="nistdet-value">
                  <div class="d-flex align-items-center gap-2 flex-wrap mb-1">
                    <span class="nivel-dot"
                          style="background-color:{nivel_data.get('color','#6c757d')} !important;"></span>
                    <span class="fw-bold">Nivel {nivel_score}</span>
                  </div>
                  <div class="text-muted small nistdet-value-wrap">
                    {escape(nivel_nombre)}
                  </div>
                </div>
              </div>

              <div class="nistdet-row">
                <div class="nistdet-label">Ítems aplicables</div>
                <div class="nistdet-value fw-bold">{aplicables}</div>
              </div>

              <div class="nistdet-row">
                <div class="nistdet-label">N/A excluidos</div>
                <div class="nistdet-value fw-bold">{no_aplica} de {total}</div>
              </div>

              <div class="nistdet-row nistdet-row-actions">
                <div class="nistdet-label">Acciones</div>
                <div class="nistdet-value">
                  <div class="d-flex flex-wrap gap-2">
                    <a class="btn btn-sm btn-outline-primary rounded-pill"
                       href="{url_for('madurez_iso22301.detalle_criterio', run_id=run.id, bloque_codigo=code)}">
                      <i class="bi bi-list-check me-1"></i>Ver preguntas
                    </a>

                    <a class="btn btn-sm btn-outline-dark rounded-pill"
                       href="{url_for('madurez_iso22301.analisis_criterio', run_id=run.id, bloque_codigo=code)}">
                      <i class="bi bi-cpu me-1"></i>Análisis
                    </a>
                  </div>
                </div>
              </div>
            </div>

          </div>
        </div>
        """)

    capitulo_cards = f"""
    <div class="nistdet-card p-4 mb-4">
      <div class="d-flex justify-content-between align-items-start flex-wrap gap-3 mb-3">
        <div>
          <div class="nistdet-section-title">ISO 22301 — Trust Services Criteria</div>
          <div class="text-muted small">
            Resultado detallado por criterios ISO 22301.
          </div>
        </div>

        <div class="nistdet-capitulo-resumen">
          <div class="d-flex align-items-center gap-2 flex-wrap justify-content-end">
            <span class="badge rounded-pill px-3 py-2"
                  style="background:{nivel_general.get('color','#6c757d')}; color:#fff;">
              Nivel {nivel_general.get('score', 0)}
            </span>
            <span class="fw-bold text-dark">{run.pct_general:.2f}%</span>
          </div>
          <div class="small text-muted text-end mt-1">
            {escape(nivel_general_nombre)}
          </div>
        </div>
      </div>

      <div class="row g-3">
        {''.join(criterio_cards)}
      </div>
    </div>
    """

    content = f"""
    <div class="nistdet-shell">

      <div class="nistdet-header-card">
        <div class="nistdet-header-overlay">
          <div class="nistdet-header-text">
            <h3 class="nistdet-title m-0">Resultado de Madurez — ISO 22301</h3>
            <div class="nistdet-subtitle">
              Consecutivo: <b>{escape(run.consecutivo or '')}</b>
              · Cumplimiento general: <b>{run.pct_general:.2f}%</b>
              · Nivel general: <b>{escape(nivel_general_nombre)}</b>
            </div>
          </div>
        </div>
      </div>

      <div class="nistdet-header-actions">
        <a href="{url_for('madurez_iso22301.historial')}"
           class="btn nistdet-btn-main rounded-pill px-4 fw-bold">
          <i class="bi bi-arrow-left me-2"></i>Volver al historial
        </a>

        <a href="{url_for('madurez_iso22301.inicio_iso22301')}"
           class="btn nistdet-btn-soft rounded-pill px-4 fw-bold">
          <i class="bi bi-house-door-fill me-2"></i>Volver al módulo
        </a>

        {pdf_btn}
      </div>

      {top_html}

      {capitulo_cards}

    </div>

    {iso22301_nist_css('nistdet', '📊')}
    """
    return render_template_string(BASE, title="Detalle ISO 22301", content=content)


# Alias por compatibilidad si tu menú anterior apuntaba a resultado
@iso22301_madurez_bp.route("/resultado/<int:run_id>", methods=["GET"])
@login_required
def resultado(run_id: int):
    return detalle(run_id)

# ============================================================
# ISO 22301 — PROMPT INFORME EJECUTIVO IA
# ============================================================

def _iso22301_prompt_informe_ejecutivo(run: "Iso22301MadurezRun", resumen: dict) -> str:
    """
    Prompt para generar informe ejecutivo ISO 22301.
    Lo usa informe_ejecutivo_generar().
    """

    lineas = []

    for code in ISO22301_BLOCK_ORDER:
        d = (resumen or {}).get(code)
        if not d:
            continue

        lineas.append(
            f"- {d.get('nombre') or iso22301_block_title(code) or code}: "
            f"{float(d.get('pct', 0) or 0):.2f}% | "
            f"Nivel: {d.get('madurez') or ''} | "
            f"SI: {d.get('SI', 0)} | "
            f"Parcial: {d.get('PARCIAL', 0)} | "
            f"NO: {d.get('NO', 0)} | "
            f"N/A: {d.get('NA', 0)} | "
            f"Total: {d.get('total', 0)}"
        )

    criterios_txt = "\n".join(lineas) if lineas else "Sin resultados consolidados."

    return f"""
Eres un consultor senior experto en ISO 22301, auditoría de controles, gobierno de seguridad de la información y Trust Services Criteria.

Genera un informe ejecutivo profesional para alta dirección.

DATOS DE LA EVALUACIÓN
Consecutivo: {run.consecutivo}
Cumplimiento general: {float(run.pct_general or 0):.2f}%

RESULTADOS POR CRITERIO
{criterios_txt}

RESPONDE ÚNICAMENTE JSON VÁLIDO.
No uses markdown.
No agregues texto antes ni después del JSON.

Formato exacto:
{{
  "informe_ejecutivo": "texto"
}}

REGLAS:
- El informe debe tener entre 5 y 8 párrafos.
- No repitas el título "Informe Ejecutivo".
- Explica el estado general de madurez ISO 22301.
- Menciona fortalezas principales.
- Menciona brechas o criterios con menor cumplimiento.
- Explica riesgos ejecutivos asociados.
- Incluye recomendaciones estratégicas.
- No inventes datos que no estén en los resultados.
- Redacción clara, ejecutiva y consultiva.
""".strip()

# ============================================================
# IA — INFORME / PLAN
# ============================================================

@iso22301_madurez_bp.route("/detalle/<int:run_id>/informe-ejecutivo/generar", methods=["POST"])
@login_required
def informe_ejecutivo_generar(run_id: int):
    user = User.query.get(session.get("user_id"))

    if not iso22301_user_can_execute(user):
        return iso22301_deny_execute("El perfil Auditor no puede generar el informe ejecutivo con IA.")

    run_analysis_from_iso22301_run(run_id)
    run = Iso22301MadurezRun.query.get_or_404(run_id)

    try:
        resumen = json.loads(run.resumen_json or "{}")
    except Exception:
        resumen = {}

    if not resumen:
        flash("⚠️ No hay resultados consolidados para generar el informe ejecutivo.", "warning")
        return redirect(url_for("madurez_iso22301.detalle", run_id=run.id))

    try:
        prompt_informe = _iso22301_prompt_informe_ejecutivo(run, resumen)
        raw = _iso22301_ai_text(prompt_informe, max_tokens=1800)
        informe_ai = _iso22301_extraer_informe_ai(raw)

        # Un segundo intento solo se realiza cuando la respuesta existe pero
        # no contiene texto utilizable. Evita que una variación de formato
        # obligue al usuario a iniciar nuevamente la generación.
        if not informe_ai:
            prompt_reintento = f"""
{prompt_informe}

CORRECCIÓN DE FORMATO OBLIGATORIA:
La respuesta anterior no contenía texto utilizable. Devuelve un único objeto
JSON con la clave exacta \"informe_ejecutivo\" y un valor de texto no vacío.
""".strip()
            raw = _iso22301_ai_text(prompt_reintento, max_tokens=1800)
            informe_ai = _iso22301_extraer_informe_ai(raw)

        if not informe_ai:
            raise RuntimeError(
                "La IA respondió sin contenido utilizable después de dos intentos. "
                "Verifique el modelo configurado e intente nuevamente."
            )

        run.informe_ejecutivo_ai = informe_ai
        run.informe_ejecutivo_editado = informe_ai
        run.updated_at = datetime.utcnow()

        db.session.add(run)
        db.session.commit()

        flash("✅ Informe ejecutivo ISO 22301 generado con IA.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error llamando IA para el informe ejecutivo: {e}", "danger")

    return redirect(url_for("madurez_iso22301.detalle", run_id=run.id))


@iso22301_madurez_bp.route("/detalle/<int:run_id>/informe-ejecutivo/editar", methods=["GET", "POST"])
@login_required
def informe_ejecutivo_editar(run_id: int):
    user = User.query.get(session.get("user_id"))

    if not iso22301_user_can_execute(user):
        return iso22301_deny_execute("El perfil Auditor no puede editar el informe ejecutivo.")

    run = Iso22301MadurezRun.query.get_or_404(run_id)

    if request.method == "POST":
        texto_form = request.form.get("informe") or ""
        texto_limpio = iso22301_normalizar_texto_rico_guardado(texto_form)

        run.informe_ejecutivo_editado = texto_limpio
        run.updated_at = datetime.utcnow()

        db.session.add(run)
        db.session.commit()

        flash("✅ Informe ejecutivo ISO 22301 actualizado.", "success")
        return redirect(url_for("madurez_iso22301.detalle", run_id=run.id))

    texto = run.informe_ejecutivo_editado or run.informe_ejecutivo_ai or ""
    texto = iso22301_normalizar_texto_rico_guardado(texto)

    # Limpia en base de datos si venía guardado como JSON literal
    if texto and texto != (run.informe_ejecutivo_editado or run.informe_ejecutivo_ai or ""):
        run.informe_ejecutivo_editado = texto
        db.session.add(run)
        db.session.commit()

    content = f"""
<div class="nistdet-shell">
  <div class="nistdet-header-card">
    <div class="nistdet-header-overlay">
      <div class="nistdet-header-text">
        <h3 class="nistdet-title m-0">Editar Informe Ejecutivo — ISO 22301</h3>
      </div>
    </div>
  </div>

  <form method="POST" class="nistdet-card p-4">
    <textarea name="informe" rows="18" class="form-control">{escape(texto)}</textarea>

    <div class="text-end mt-3">
      <a href="{url_for('madurez_iso22301.detalle', run_id=run.id)}"
         class="btn btn-secondary rounded-pill px-4">
        Cancelar
      </a>

      <button class="btn btn-primary rounded-pill px-4 fw-bold">
        Guardar
      </button>
    </div>
  </form>
</div>
{iso22301_nist_css('nistdet', '✍️')}
"""
    return render_template_string(BASE, title="Editar Informe Ejecutivo ISO 22301", content=content)


@iso22301_madurez_bp.route("/detalle/<int:run_id>/plan-trabajo/generar", methods=["POST"])
@login_required
def plan_trabajo_generar(run_id: int):
    user = User.query.get(session.get("user_id"))

    if not iso22301_user_can_execute(user):
        return iso22301_deny_execute("El perfil Auditor no puede generar el plan de trabajo con IA.")

    run = Iso22301MadurezRun.query.get_or_404(run_id)
    resumen = json.loads(run.resumen_json or "{}")

    try:
        raw = _iso22301_ai_text(_iso22301_prompt_plan_trabajo(run, resumen), max_tokens=1600)
        obj = _extraer_json_objeto_iso22301(raw)
        plan = obj.get("plan_trabajo") if isinstance(obj, dict) else None
        plan_txt = _build_plan_accion_iso22301_texto(plan) if isinstance(plan, list) else raw
        plan_txt = iso22301_normalizar_texto_rico_guardado(plan_txt)

        if not plan_txt:
            raise RuntimeError("La IA no devolvió un plan válido.")

        run.plan_trabajo_ai = plan_txt
        run.plan_trabajo_editado = plan_txt
        db.session.commit()

        flash("✅ Plan de trabajo ISO 22301 generado con IA.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error generando plan de trabajo: {e}", "danger")

    return redirect(url_for("madurez_iso22301.detalle", run_id=run.id))


@iso22301_madurez_bp.route("/detalle/<int:run_id>/plan-trabajo/editar", methods=["GET", "POST"])
@login_required
def plan_trabajo_editar(run_id: int):
    user = User.query.get(session.get("user_id"))

    if not iso22301_user_can_execute(user):
        return iso22301_deny_execute("El perfil Auditor no puede editar el plan de trabajo.")

    run = Iso22301MadurezRun.query.get_or_404(run_id)

    if request.method == "POST":
        run.plan_trabajo_editado = (request.form.get("plan") or "").strip()
        db.session.commit()
        flash("✅ Plan de trabajo ISO 22301 actualizado.", "success")
        return redirect(url_for("madurez_iso22301.detalle", run_id=run.id))

    texto = run.plan_trabajo_editado or run.plan_trabajo_ai or ""

    content = f"""
<div class="nistdet-shell">
  <div class="nistdet-header-card">
    <div class="nistdet-header-overlay">
      <div class="nistdet-header-text">
        <h3 class="nistdet-title m-0">Editar Plan de Trabajo — ISO 22301</h3>
      </div>
    </div>
  </div>

  <form method="POST" class="nistdet-card p-4">
    <textarea name="plan" rows="18" class="form-control">{escape(texto)}</textarea>
    <div class="text-end mt-3">
      <a href="{url_for('madurez_iso22301.detalle', run_id=run.id)}" class="btn btn-secondary rounded-pill px-4">Cancelar</a>
      <button class="btn btn-success rounded-pill px-4 fw-bold">Guardar</button>
    </div>
  </form>
</div>
{iso22301_nist_css('nistdet', '✍️')}
"""
    return render_template_string(BASE, title="Editar Plan ISO 22301", content=content)

# ============================================================
# PDF EJECUTIVO ISO 22301
# ============================================================

def _iso22301_build_pdf_run(run: "Iso22301MadurezRun") -> io.BytesIO:
    try:
        resumen = json.loads(run.resumen_json or "{}")
    except Exception:
        resumen = {}

    labels, values = iso22301_pct_por_criterio(resumen, ISO22301_BLOCK_ORDER)
    radar_b64 = run.radar_overall_b64 or iso22301_radar_b64(
        labels,
        values,
        title="Radar por Capítulo - ISO 22301"
    )

    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=1.2 * cm,
        rightMargin=1.2 * cm,
        topMargin=1.0 * cm,
        bottomMargin=1.0 * cm,
        title="ISO 22301 - Informe Ejecutivo"
    )

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="ISO22301_Title",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        textColor=colors.white,
        alignment=TA_CENTER,
        spaceAfter=8
    ))

    styles.add(ParagraphStyle(
        name="ISO22301_Section",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=colors.HexColor("#1d4f8f"),
        spaceBefore=10,
        spaceAfter=8
    ))

    styles.add(ParagraphStyle(
        name="ISO22301_Normal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#101827"),
        spaceAfter=5
    ))

    styles.add(ParagraphStyle(
        name="ISO22301_Small",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9,
        textColor=colors.HexColor("#374151"),
        spaceAfter=4
    ))

    def pdf_escape(v):
        return html.escape(str(v or ""))

    story = []

    title_tbl = Table(
        [[Paragraph("ISO 22301 - Informe de Madurez", styles["ISO22301_Title"])]],
        colWidths=[26.8 * cm]
    )
    title_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#3f86d6")),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#1d4f8f")),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(title_tbl)
    story.append(Spacer(1, 8))

    nivel_general = iso22301_resolver_nivel(run.pct_general)

    resumen_tbl = Table([
        ["Consecutivo", pdf_escape(run.consecutivo)],
        ["Fecha", run.created_at.strftime("%Y-%m-%d %H:%M") if run.created_at else ""],
        ["Cumplimiento general", f"{float(run.pct_general or 0):.2f}% - {pdf_escape(nivel_general.get('nivel',''))}"],
    ], colWidths=[5.2 * cm, 21.6 * cm])

    resumen_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8f1fb")),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#1d4f8f")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cfd8e3")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(resumen_tbl)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Informe Ejecutivo", styles["ISO22301_Section"]))

    informe = iso22301_normalizar_texto_rico_guardado(
        run.informe_ejecutivo_editado or run.informe_ejecutivo_ai or ""
    )

    if informe:
        for parrafo in re.split(r"\n\s*\n", informe):
            if parrafo.strip():
                story.append(Paragraph(pdf_escape(parrafo.strip()), styles["ISO22301_Normal"]))
    else:
        story.append(Paragraph("No hay informe ejecutivo registrado.", styles["ISO22301_Normal"]))

    story.append(Spacer(1, 8))
    story.append(Paragraph("Radar por Capítulo ISO 22301", styles["ISO22301_Section"]))

    if radar_b64:
        try:
            img = RLImage(
                io.BytesIO(base64.b64decode(radar_b64)),
                width=11.5 * cm,
                height=11.0 * cm
            )
            story.append(img)
        except Exception:
            story.append(Paragraph("No fue posible insertar el radar.", styles["ISO22301_Normal"]))

    story.append(Paragraph("Detalle por Criterio", styles["ISO22301_Section"]))

    data = [[
        "Criterio",
        "% Cumplimiento",
        "Nivel",
        "SI",
        "Parcial",
        "NO",
        "N/A",
        "Ítems aplicables"
    ]]

    for code in ISO22301_BLOCK_ORDER:
        d = resumen.get(code)
        if not d:
            continue

        data.append([
            Paragraph(pdf_escape(d.get("nombre") or code), styles["ISO22301_Small"]),
            Paragraph(f"{float(d.get('pct', 0) or 0):.2f}%", styles["ISO22301_Small"]),
            Paragraph(pdf_escape(d.get("madurez") or ""), styles["ISO22301_Small"]),
            str(d.get("SI", 0)),
            str(d.get("PARCIAL", 0)),
            str(d.get("NO", 0)),
            str(d.get("NA", 0)),
            str(d.get("validas", 0)),
        ])

    tbl = Table(
        data,
        colWidths=[
            7.2 * cm,
            3.0 * cm,
            5.0 * cm,
            1.5 * cm,
            2.0 * cm,
            1.5 * cm,
            1.5 * cm,
            2.0 * cm
        ],
        repeatRows=1
    )

    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3f86d6")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cfd8e3")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    story.append(tbl)

    plan = _normalizar_plan_accion_iso22301_texto(
        run.plan_trabajo_editado or run.plan_trabajo_ai or ""
    )

    if plan:
        story.append(PageBreak())
        story.append(Paragraph("Plan de Trabajo", styles["ISO22301_Section"]))

        for parrafo in re.split(r"\n\s*\n", plan):
            if parrafo.strip():
                story.append(Paragraph(pdf_escape(parrafo.strip()), styles["ISO22301_Normal"]))

    doc.build(story)
    buf.seek(0)
    return buf

# ============================================================
# EXPORTAR PDF — ADMIN / USUARIO CON PERMISO / AUDITOR
# ============================================================

@iso22301_madurez_bp.route("/detalle/<int:run_id>/pdf", methods=["GET"])
@login_required
def exportar_pdf(run_id: int):
    user = User.query.get(session.get("user_id"))

    # ✅ Auditor también puede exportar/imprimir PDF
    denied = iso22301_check_access_or_redirect(
        user,
        "No tiene permiso para exportar PDF ISO 22301."
    )
    if denied:
        return denied

    # Garantiza que el PDF use la fórmula vigente incluso si la revisión
    # fue creada antes de excluir N/A del denominador.
    run_analysis_from_iso22301_run(run_id)
    run = Iso22301MadurezRun.query.get_or_404(run_id)

    pdf = _iso22301_build_pdf_run(run)

    filename = f"ISO22301_Madurez_{re.sub(r'[^A-Za-z0-9_-]+', '_', run.consecutivo or str(run.id))}.pdf"

    return send_file(
        pdf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename
    )


# ============================================================
# ELIMINAR — AUDITOR NO PUEDE
# ============================================================

@iso22301_madurez_bp.route("/detalle/<int:run_id>/eliminar", methods=["POST"])
@login_required
def eliminar_run(run_id: int):
    user = User.query.get(session.get("user_id"))

    if not iso22301_user_can_execute(user):
        return iso22301_deny_execute("El perfil Auditor no puede eliminar revisiones ISO 22301.")

    run = Iso22301MadurezRun.query.get_or_404(run_id)

    try:
        Iso22301MadurezCriterioAnalisis.query.filter_by(run_id=run.id).delete(synchronize_session=False)
        Iso22301MadurezRespuesta.query.filter_by(run_id=run.id).delete(synchronize_session=False)
        db.session.delete(run)
        db.session.commit()
        flash("✅ Revisión ISO 22301 eliminada correctamente.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error eliminando revisión ISO 22301: {e}", "danger")

    return redirect(url_for("madurez_iso22301.historial"))


# ============================================================
# CSS — COPIA DE PATRÓN NIST
# ============================================================
def iso22301_nist_css(prefix, icon, subtitle_label="ISO 22301"):
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
    max-width:1600px;
    margin:26px auto 24px auto;
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
    margin-bottom:14px;
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
    background:transparent !important;
    padding:0 !important;
    position:relative;
    z-index:1;
  }}

  .{prefix}-header-overlay::before{{
    content:"{icon}";
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

  .{prefix}-header-text{{
    max-width:1100px;
    width:100%;
    display:block !important;
    transform:none !important;
  }}

  .{prefix}-header-text::before{{
    content:"SGSI · {subtitle_label}";
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
    font-weight:800;
  }}

  .{prefix}-header-actions{{
    display:flex;
    justify-content:center;
    align-items:center;
    flex-wrap:wrap;
    gap:10px;
    margin:10px 0 14px;
  }}

  .{prefix}-header-actions .btn,
  .{prefix}-btn-main,
  .{prefix}-btn-primary,
  .{prefix}-btn-soft,
  .btn{{
    border-radius:10px !important;
    min-height:32px;
    padding:8px 22px !important;
    font-size:.82rem;
    font-weight:900;
    box-shadow:0 8px 16px rgba(15,23,42,.15);
  }}

  .{prefix}-btn-main,
  .{prefix}-btn-primary{{
    background:#0b4a8f !important;
    border:1px solid #0b4a8f !important;
    color:#ffffff !important;
  }}

  .{prefix}-btn-main:hover,
  .{prefix}-btn-primary:hover{{
    background:#0f4f94 !important;
    color:#ffffff !important;
  }}

  .{prefix}-btn-soft{{
    background:#ffffff !important;
    border:1px solid #cfd8e3 !important;
    color:#0f172a !important;
  }}

  .{prefix}-btn-soft:hover{{
    background:#edf5ff !important;
    color:#0b65d8 !important;
  }}

  .{prefix}-card,
  .card{{
    background:rgba(255,255,255,.96) !important;
    border-radius:18px !important;
    backdrop-filter:blur(8px);
    box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
    border:1px solid rgba(219,230,244,.9) !important;
    overflow:hidden;
  }}

  .{prefix}-section-title,
  .card h5,
  .card h6{{
    font-weight:950;
    font-size:.95rem;
    color:#0b4a8f;
    margin:8px 0 14px 0;
    padding-bottom:8px;
    border-bottom:2px solid rgba(59,130,246,.18);
  }}

  .form-control,
  .form-select{{
    border-radius:10px;
    border:1px solid #d9e3f0;
    min-height:40px;
    font-size:.86rem;
    background:#f8fafc;
    box-shadow:none !important;
  }}

  .form-control:focus,
  .form-select:focus{{
    border-color:#3f86d6;
    box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
    background:#ffffff;
  }}

  .badge{{
    border-radius:999px;
    font-size:.70rem;
    padding:.35rem .65rem;
    font-weight:900;
  }}

  @media(max-width:991.98px){{
    .{prefix}-shell{{
      width:98%;
      margin:8px auto 22px auto;
    }}

    .{prefix}-header-card{{
      min-height:88px;
    }}

    .{prefix}-title{{
      font-size:1.20rem;
    }}

    .{prefix}-subtitle{{
      font-size:.68rem;
    }}
  }}

  @media(max-width:768px){{
    .{prefix}-header-overlay{{
      flex-direction:column;
      text-align:center;
      gap:10px;
    }}

    .{prefix}-header-overlay::before{{
      margin:0;
    }}

    .{prefix}-header-text::before{{
      margin-left:auto;
      margin-right:auto;
    }}

    .{prefix}-title,
    .{prefix}-subtitle{{
      text-align:center;
    }}

    .{prefix}-header-actions .btn{{
      width:100%;
    }}
  }}
</style>
"""


def iso22301_nistform_css():
    return """
    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .nistform-shell{
        width:96%;
        max-width:1600px;
        margin:26px auto 24px auto;
      }

      .nistform-header-card{
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

      .nistform-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .nistform-header-overlay{
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

      .nistform-header-overlay::before{
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
        font-size:1.45rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }

      .nistform-header-text{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
      }

      .nistform-header-text::before{
        content:"SGSI · Evaluación ISO 22301";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .nistform-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .nistform-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
        font-weight:800;
      }

      .nistform-header-actions{
        display:flex;
        justify-content:center;
        align-items:center;
        flex-wrap:wrap;
        gap:10px;
        margin:10px 0 14px;
      }

      .nistform-header-actions .btn,
      .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .nistform-card,
      .card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }

      .nistform-section-title,
      .card h5,
      .card h6{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin:8px 0 14px 0;
        padding-bottom:8px;
        border-bottom:2px solid rgba(59,130,246,.18);
      }

      .nistform-progress{
        height:24px;
        border-radius:999px;
        background:#dbe6f4;
        overflow:hidden;
        box-shadow:inset 0 2px 6px rgba(0,0,0,.12);
      }

      .nistform-progress .progress-bar{
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1);
        font-weight:900;
      }

      .nistform-accordion{
        display:flex;
        flex-direction:column;
        gap:12px;
      }

      .nistform-acc-item{
        border:1px solid #dbe6f4;
        border-radius:18px!important;
        overflow:hidden;
        box-shadow:0 8px 18px rgba(15,23,42,.08);
      }

      .nistform-acc-item .accordion-button{
        background:linear-gradient(135deg,#eef6ff,#ffffff);
        color:#101827;
        font-weight:900;
        box-shadow:none;
        padding:16px 18px;
      }

      .nistform-acc-item .accordion-button:not(.collapsed){
        background:linear-gradient(135deg,#dceeff,#ffffff);
        color:#0b4a8f;
      }

      .nistform-acc-inner{
        width:100%;
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:14px;
      }

      .nistform-func-title{
        font-size:1.02rem;
        font-weight:950;
        color:#0b4a8f;
      }

      .nistform-func-subtitle{
        font-size:.78rem;
        color:#607086;
        font-weight:700;
        margin-top:2px;
      }

      .nistform-acc-body{
        background:#f8fbff;
        padding:16px;
      }

      .nistform-cat-block{
        background:rgba(255,255,255,.88);
        border:1px solid rgba(15,23,42,.08);
        border-radius:18px;
        padding:8px 7px;
        margin-bottom:14px;
      }

      .nistform-cat-title{
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:12px;
        margin-bottom:14px;
        color:#0b4a8f;
        font-weight:950;
      }

      .nistform-cat-title small{
        color:#607086;
        font-weight:700;
      }

      .nistform-qcard{
        background:#ffffff;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:16px;
        box-shadow:0 8px 18px rgba(15,23,42,.06);
      }

      .nistform-qhead{
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:10px;
        margin-bottom:10px;
      }

      .nistform-qtext{
        color:#0b1220;
        font-weight:800;
        line-height:1.35;
        min-height:76px;
      }

      .nistform-radio-row{
        display:grid;
        grid-template-columns:repeat(4,1fr);
        gap:6px;
        margin-top:14px;
      }

      .nistform-radio-card{
        display:flex;
        align-items:center;
        justify-content:center;
        gap:7px;
        border:1px solid #d7e0ec;
        background:#ffffff;
        color:#101827;
        border-radius:999px;
        padding:8px 10px;
        font-weight:900;
        font-size:.78rem;
        cursor:pointer;
        transition:all .18s ease;
        min-height:40px;
        user-select:none;
      }

      .nistform-radio-card input{
        accent-color:#0b4a8f;
      }

      .nistform-radio-card:hover{
        transform:translateY(-1px);
        box-shadow:0 8px 16px rgba(15,23,42,.10);
      }

      .nistform-radio-card:has(input[value="NA"]:checked){
        background:#e2e3e5;
        border-color:#6c757d;
        color:#41464b;
      }

      .nistform-radio-card:has(input[value="SI"]:checked){
        background:#d1e7dd;
        border-color:#198754;
        color:#0f5132;
      }

      .nistform-radio-card:has(input[value="PARCIAL"]:checked){
        background:#fff3cd;
        border-color:#ffc107;
        color:#664d03;
      }

      .nistform-radio-card:has(input[value="NO"]:checked){
        background:#f8d7da;
        border-color:#dc3545;
        color:#842029;
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

      .badge{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }

      @media(max-width:991.98px){
        .nistform-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .nistform-header-card{
          min-height:88px;
        }

        .nistform-title{
          font-size:1.20rem;
        }

        .nistform-subtitle{
          font-size:.68rem;
        }

        .nistform-card{
          padding:14px!important;
        }
      }

      @media(max-width:768px){
        .nistform-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .nistform-header-overlay::before{
          margin:0;
        }

        .nistform-header-text::before{
          margin-left:auto;
          margin-right:auto;
        }

        .nistform-title,
        .nistform-subtitle{
          text-align:center;
        }

        .nistform-header-actions .btn{
          width:100%;
        }

        .nistform-acc-inner,
        .nistform-cat-title{
          flex-direction:column;
          align-items:flex-start;
        }

        .nistform-radio-row{
          grid-template-columns:1fr;
        }
      }
    </style>
    """

# ==========================================================================================================================================
#                                                   Fin Módulo de Madurez ISO 22301 — Diseño NIST
# ============================================================================================================================================

# ============================================================================================================================================
#                       MÓDULO NIVEL DE MADUREZ — GESTIÓN DE INTELIGENCIA ARTIFICIAL ISO 42001
# ============================================================================================================================================

ai_madurez_bp = Blueprint("madurez_ai", __name__, url_prefix="/madurez-ai")

AI_MADUREZ_PERMISO = "Nivel de Madurez Gestión de Inteligencia Artificial"
AI_MADUREZ_DB_PATH = os.path.join(app.instance_path, "ai_madurez_42001.db")
AI_INSTRUMENTO_DEFAULT = os.path.join(app.root_path, "static", "templates", "Instrumento ISO 42001 ES.xlsx")

AI_STATUS_SCORE = {
    "SI": 1.0,
    "PARCIAL": 0.5,
    "NO": 0.0,
    "NA": None,
}

AI_MADUREZ_LEVELS = [
    {
        "nivel": "Nivel 1: Ejecutado (Performed)",
        "descripcion": "La organización ejecuta prácticas de gestión de IA de forma básica, reactiva o ad hoc.",
        "score": 1,
        "rango_pct": "0% – 20%",
        "logica": "Prácticas ad hoc",
    },
    {
        "nivel": "Nivel 2: Documentado (Documented)",
        "descripcion": "La organización cuenta con prácticas documentadas para gestionar riesgos, responsabilidades y controles de IA.",
        "score": 2,
        "rango_pct": "21% – 40%",
        "logica": "Existe documentación",
    },
    {
        "nivel": "Nivel 3: Gestionado (Managed)",
        "descripcion": "La organización gestiona formalmente el sistema de gestión de IA, asigna responsables y revisa cumplimiento.",
        "score": 3,
        "rango_pct": "41% – 60%",
        "logica": "Se gestiona cumplimiento",
    },
    {
        "nivel": "Nivel 4: Gestionado Cuantitativamente (Quantitatively Managed)",
        "descripcion": "La organización mide la efectividad, monitorea resultados y reporta periódicamente el desempeño del sistema de IA.",
        "score": 4,
        "rango_pct": "61% – 80%",
        "logica": "Se mide efectividad",
    },
    {
        "nivel": "Nivel 5: Optimizado (Optimizing)",
        "descripcion": "La organización mejora continuamente el sistema de gestión de IA y optimiza sus procesos de gobierno, riesgo y control.",
        "score": 5,
        "rango_pct": "81% – 100%",
        "logica": "Mejora continua institucionalizada",
    },
]

AI_CAP_ORDER_DEFAULT = [
    "Contexto de la Organización",
    "Liderazgo",
    "Planificación",
    "Soporte",
    "Operación",
    "Evaluación del Desempeño",
    "Mejora",
    "Anexo A",
    "Gobierno",
    "Riesgo",
    "Datos",
    "Transparencia",
    "Seguridad",
]

# ============================================================
# CATÁLOGO DE EVALUACIÓN DE RIESGOS DE IA — NIST AI RMF
# Fuente operativa: checklist suministrado por el usuario.
# La clasificación NIST usa las funciones GOVERN, MAP,
# MEASURE y MANAGE del AI RMF.
# ============================================================

AI_RISK_PHASES = [
    {
        "codigo": "F1",
        "nombre": "Fase 1: Concepción y Definición",
        "descripcion": "Definición del propósito, contexto, clasificación e impactos potenciales del sistema de IA.",
        "foco_nist": "MAP / GOVERN",
    },
    {
        "codigo": "F2",
        "nombre": "Fase 2: Gobernanza de Datos",
        "descripcion": "Licitud, calidad, representatividad, minimización y trazabilidad de los datos.",
        "foco_nist": "GOVERN / MAP / MEASURE",
    },
    {
        "codigo": "F3",
        "nombre": "Fase 3: Desarrollo y Entrenamiento",
        "descripcion": "Diseño seguro, documentación, explicabilidad, robustez y dependencias técnicas.",
        "foco_nist": "MAP / MEASURE",
    },
    {
        "codigo": "F4",
        "nombre": "Fase 4: Validación y Pruebas",
        "descripcion": "Medición independiente del rendimiento, la robustez, la equidad y la supervisión humana.",
        "foco_nist": "MEASURE / GOVERN",
    },
    {
        "codigo": "F5",
        "nombre": "Fase 5: Despliegue y Operación",
        "descripcion": "Monitoreo continuo, deriva, incidentes, contingencia y tratamiento del riesgo.",
        "foco_nist": "MEASURE / MANAGE",
    },
]

AI_RISK_FUNCTIONS = {
    "GOVERN": {
        "nombre": "GOVERN — Gobernar",
        "descripcion": "Políticas, responsabilidades, cultura y supervisión para gestionar los riesgos de IA.",
        "color": "#6f42c1",
    },
    "MAP": {
        "nombre": "MAP — Mapear",
        "descripcion": "Contexto, propósito, partes interesadas, impactos y riesgos del sistema de IA.",
        "color": "#0d6efd",
    },
    "MEASURE": {
        "nombre": "MEASURE — Medir",
        "descripcion": "Métodos, métricas, pruebas y seguimiento de riesgos y características de confianza.",
        "color": "#fd7e14",
    },
    "MANAGE": {
        "nombre": "MANAGE — Gestionar",
        "descripcion": "Priorización, respuesta, tratamiento, seguimiento y comunicación del riesgo.",
        "color": "#198754",
    },
}

# codigo, fase_codigo, fase, funcion NIST, categoría NIST,
# título, pregunta, evidencia sugerida, orden
AI_RISK_QUESTION_CATALOG = [
    (
        "AIR-001", "F1", "Fase 1: Concepción y Definición", "MAP", "MAP-1",
        "Definición del propósito previsto",
        "¿Se ha documentado el uso específico y el propósito previsto del sistema de IA conforme a los requisitos aplicables, incluido el AI Act cuando corresponda?",
        "Ficha del caso de uso, declaración de propósito, alcance, usuarios previstos y usos excluidos.", 1
    ),
    (
        "AIR-002", "F1", "Fase 1: Concepción y Definición", "MAP", "MAP-1",
        "Clasificación de riesgo",
        "¿Se ha determinado y documentado si el sistema se clasifica como riesgo prohibido, alto, limitado o mínimo?",
        "Matriz de clasificación regulatoria, concepto jurídico y aprobación del comité de IA.", 2
    ),
    (
        "AIR-003", "F1", "Fase 1: Concepción y Definición", "GOVERN", "GOVERN-1",
        "Evaluación de impacto",
        "¿Se ha realizado una evaluación de impacto sobre protección de datos (DPIA) conforme al RGPD o a la regulación de privacidad aplicable?",
        "DPIA, evaluación de impacto algorítmico, concepto de privacidad y plan de tratamiento.", 3
    ),
    (
        "AIR-004", "F1", "Fase 1: Concepción y Definición", "MAP", "MAP-3",
        "Análisis de partes interesadas",
        "¿Se han identificado los grupos y partes interesadas potencialmente afectados por las decisiones del sistema?",
        "Mapa de partes interesadas, perfiles afectados y registro de consultas.", 4
    ),
    (
        "AIR-005", "F1", "Fase 1: Concepción y Definición", "MAP", "MAP-5",
        "Viabilidad ética",
        "¿Se han evaluado los posibles impactos negativos en la equidad, los derechos fundamentales y la no discriminación?",
        "Evaluación ética, análisis de impacto en derechos fundamentales y criterios de aceptación.", 5
    ),
    (
        "AIR-006", "F2", "Fase 2: Gobernanza de Datos", "GOVERN", "GOVERN-1",
        "Licitud y procedencia",
        "¿Se ha verificado la base legal y la procedencia autorizada de los datos utilizados para entrenamiento, validación y operación?",
        "Inventario de fuentes, bases legales, licencias, consentimientos y contratos de datos.", 6
    ),
    (
        "AIR-007", "F2", "Fase 2: Gobernanza de Datos", "MEASURE", "MEASURE-2",
        "Representatividad",
        "¿Se han realizado pruebas para asegurar que los datos no introducen sesgos estadísticos significativos?",
        "Informe de representatividad, métricas de sesgo y resultados por subgrupos.", 7
    ),
    (
        "AIR-008", "F2", "Fase 2: Gobernanza de Datos", "MAP", "MAP-2",
        "Minimización",
        "¿Se han aplicado técnicas de anonimización, seudonimización o minimización para limitar los datos personales al mínimo necesario?",
        "Diseño de minimización, evidencia de anonimización y diccionario de datos.", 8
    ),
    (
        "AIR-009", "F2", "Fase 2: Gobernanza de Datos", "GOVERN", "GOVERN-1",
        "Linaje de datos",
        "¿Existe un registro completo del origen y de las transformaciones aplicadas a los conjuntos de datos?",
        "Registro de linaje, versionado de datasets, procesos ETL y responsables de custodia.", 9
    ),
    (
        "AIR-010", "F2", "Fase 2: Gobernanza de Datos", "MEASURE", "MEASURE-2",
        "Calidad técnica",
        "¿Se han auditado los datos para detectar valores atípicos (outliers), datos incompletos, inconsistentes o corruptos?",
        "Informe de calidad, reglas de validación, métricas y registros de corrección.", 10
    ),
    (
        "AIR-011", "F3", "Fase 3: Desarrollo y Entrenamiento", "MAP", "MAP-2",
        "Selección de algoritmos",
        "¿Se ha justificado la elección del modelo considerando su interpretabilidad, robustez y adecuación al propósito previsto?",
        "Decisión de arquitectura, comparación de modelos y criterios técnicos de selección.", 11
    ),
    (
        "AIR-012", "F3", "Fase 3: Desarrollo y Entrenamiento", "GOVERN", "GOVERN-1",
        "Documentación técnica",
        "¿Se ha generado una ficha técnica (Model Card) que detalle las limitaciones, los datos, las métricas y el uso previsto del modelo?",
        "Model Card, Data Card, documentación de arquitectura y registro de limitaciones.", 12
    ),
    (
        "AIR-013", "F3", "Fase 3: Desarrollo y Entrenamiento", "MEASURE", "MEASURE-2",
        "Seguridad del entorno",
        "¿Se han implementado y probado controles para prevenir el envenenamiento de datos, la extracción del modelo y otros ataques contra la IA?",
        "Modelo de amenazas, pruebas de seguridad, controles de acceso y resultados de red teaming.", 13
    ),
    (
        "AIR-014", "F3", "Fase 3: Desarrollo y Entrenamiento", "MEASURE", "MEASURE-2",
        "Explicabilidad",
        "¿Se han integrado mecanismos y herramientas para interpretar y auditar las decisiones o resultados del modelo?",
        "Pruebas de explicabilidad, documentación de métodos XAI y ejemplos de explicaciones.", 14
    ),
    (
        "AIR-015", "F3", "Fase 3: Desarrollo y Entrenamiento", "MAP", "MAP-4",
        "Gestión de dependencias",
        "¿Se han auditado las librerías, modelos y componentes de terceros para reducir vulnerabilidades de cadena de suministro?",
        "SBOM/ML-BOM, inventario de dependencias, análisis de vulnerabilidades y licencias.", 15
    ),
    (
        "AIR-016", "F4", "Fase 4: Validación y Pruebas", "MEASURE", "MEASURE-1",
        "Métricas de rendimiento",
        "¿Se ha validado el modelo con conjuntos de datos independientes y métricas apropiadas para el contexto de uso?",
        "Plan de validación, test set independiente, métricas y umbrales de aceptación.", 16
    ),
    (
        "AIR-017", "F4", "Fase 4: Validación y Pruebas", "MEASURE", "MEASURE-2",
        "Pruebas de robustez",
        "¿Se ha sometido el modelo a ataques adversarios simulados y pruebas de robustez?",
        "Informe de pruebas adversariales, escenarios, resultados y remediaciones.", 17
    ),
    (
        "AIR-018", "F4", "Fase 4: Validación y Pruebas", "GOVERN", "GOVERN-3",
        "Supervisión humana",
        "¿Se han definido y probado mecanismos de intervención humana (human-in-the-loop) para casos críticos?",
        "Matriz de decisiones, procedimiento de escalamiento, roles y pruebas de intervención.", 18
    ),
    (
        "AIR-019", "F4", "Fase 4: Validación y Pruebas", "MEASURE", "MEASURE-2",
        "Validación de equidad",
        "¿Se ha analizado el impacto del modelo en diferentes subgrupos demográficos o poblaciones afectadas?",
        "Métricas de equidad, análisis por subgrupos y plan de mitigación de sesgos.", 19
    ),
    (
        "AIR-020", "F4", "Fase 4: Validación y Pruebas", "MEASURE", "MEASURE-2",
        "Pruebas de estrés",
        "¿Se ha evaluado y documentado el comportamiento del sistema ante entradas inesperadas, datos fuera de distribución o ruido?",
        "Casos de prueba, resultados de estrés, límites operativos y criterios de degradación segura.", 20
    ),
    (
        "AIR-021", "F5", "Fase 5: Despliegue y Operación", "GOVERN", "GOVERN-1",
        "Control de versiones",
        "¿Se garantiza la trazabilidad y reproducibilidad de los modelos, datos, parámetros y configuraciones desplegados?",
        "Registro de versiones, repositorios, artefactos de despliegue y procedimiento de reproducción.", 21
    ),
    (
        "AIR-022", "F5", "Fase 5: Despliegue y Operación", "MEASURE", "MEASURE-3",
        "Monitorización de deriva",
        "¿Existen métricas y alertas ante cambios en la distribución de los datos o el desempeño del modelo (data/model drift)?",
        "Tablero de monitoreo, umbrales, alertas y registros de deriva.", 22
    ),
    (
        "AIR-023", "F5", "Fase 5: Despliegue y Operación", "MEASURE", "MEASURE-4",
        "Vigilancia post-comercialización",
        "¿Se ha establecido un proceso para recopilar y analizar el rendimiento y los impactos del sistema en el entorno real?",
        "Plan de monitoreo, reportes periódicos, retroalimentación y métricas posproducción.", 23
    ),
    (
        "AIR-024", "F5", "Fase 5: Despliegue y Operación", "MANAGE", "MANAGE-2",
        "Plan de contingencia",
        "¿Existe un procedimiento documentado y probado para la desactivación, reversión o sustitución segura del sistema?",
        "Plan de contingencia, rollback, criterios de suspensión y resultados de pruebas.", 24
    ),
    (
        "AIR-025", "F5", "Fase 5: Despliegue y Operación", "MANAGE", "MANAGE-4",
        "Gestión de incidentes",
        "¿Existe un canal y un proceso para reportar, investigar y tratar comportamientos anómalos o impactos adversos del sistema?",
        "Procedimiento de incidentes de IA, canal de reporte, registros y lecciones aprendidas.", 25
    ),
]

# La evaluación de riesgos no mantiene una escala de madurez separada.
# Reutiliza directamente AI_STATUS_SCORE y AI_MADUREZ_LEVELS, que son
# los parámetros definidos para el módulo de madurez de IA.


# ============================================================
# DB INDEPENDIENTE
# ============================================================

def get_ai_madurez_conn():
    os.makedirs(app.instance_path, exist_ok=True)
    conn = sqlite3.connect(AI_MADUREZ_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_ai_madurez_db():
    conn = get_ai_madurez_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ai_madurez_preguntas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            capitulo TEXT NOT NULL,
            capitulo_codigo TEXT,
            categoria TEXT,
            categoria_codigo TEXT,
            orden INTEGER NOT NULL DEFAULT 0,
            pregunta TEXT NOT NULL,
            activo INTEGER NOT NULL DEFAULT 1
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ai_madurez_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            consecutivo TEXT NOT NULL,
            user_id INTEGER,
            estado TEXT NOT NULL DEFAULT 'BORRADOR',
            progreso_pct INTEGER NOT NULL DEFAULT 0,
            resumen_json TEXT NOT NULL DEFAULT '{}',
            pct_general REAL NOT NULL DEFAULT 0,
            radar_overall_b64 TEXT,
            informe_ejecutivo_ai TEXT,
            informe_ejecutivo_editado TEXT,
            plan_trabajo_ai TEXT,
            plan_trabajo_editado TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ai_madurez_respuestas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            pregunta_id INTEGER NOT NULL,
            estado TEXT NOT NULL,
            comentario TEXT,
            UNIQUE(run_id, pregunta_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ai_madurez_categoria_analisis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            capitulo TEXT NOT NULL,
            categoria_codigo TEXT NOT NULL,
            estado_actual TEXT,
            estado_requerido TEXT,
            plan_accion_ai TEXT,
            plan_accion_editado TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(run_id, capitulo, categoria_codigo)
        )
    """)

    # Tablas independientes del submódulo Evaluación de Riesgos — NIST AI RMF.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ai_risk_preguntas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL UNIQUE,
            fase_codigo TEXT NOT NULL,
            fase TEXT NOT NULL,
            nist_funcion TEXT NOT NULL,
            nist_categoria TEXT NOT NULL,
            titulo TEXT NOT NULL,
            pregunta TEXT NOT NULL,
            evidencia_sugerida TEXT,
            orden INTEGER NOT NULL DEFAULT 0,
            activo INTEGER NOT NULL DEFAULT 1
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ai_risk_evaluaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            consecutivo TEXT NOT NULL,
            nombre_proyecto TEXT NOT NULL,
            responsable TEXT,
            caso_uso TEXT,
            descripcion TEXT,
            clasificacion_riesgo TEXT,
            user_id INTEGER,
            estado TEXT NOT NULL DEFAULT 'BORRADOR',
            progreso_pct INTEGER NOT NULL DEFAULT 0,
            cumplimiento_pct REAL NOT NULL DEFAULT 0,
            exposicion_pct REAL NOT NULL DEFAULT 100,
            nivel_riesgo TEXT NOT NULL DEFAULT 'Nivel 1: Ejecutado (Performed)',
            resumen_json TEXT NOT NULL DEFAULT '{}',
            analisis_ai TEXT,
            plan_tratamiento_ai TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ai_risk_respuestas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evaluacion_id INTEGER NOT NULL,
            pregunta_id INTEGER NOT NULL,
            estado TEXT NOT NULL,
            comentario TEXT,
            evidencia TEXT,
            UNIQUE(evaluacion_id, pregunta_id)
        )
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_ai_risk_eval_usuario
        ON ai_risk_evaluaciones(user_id, estado, updated_at)
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_ai_risk_resp_evaluacion
        ON ai_risk_respuestas(evaluacion_id, pregunta_id)
    """)

    # Carga y mantiene sincronizadas las 25 preguntas del documento Word.
    for item in AI_RISK_QUESTION_CATALOG:
        (
            codigo, fase_codigo, fase, nist_funcion, nist_categoria,
            titulo, pregunta, evidencia_sugerida, orden
        ) = item

        cur.execute("""
            INSERT OR IGNORE INTO ai_risk_preguntas (
                codigo, fase_codigo, fase, nist_funcion, nist_categoria,
                titulo, pregunta, evidencia_sugerida, orden, activo
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, item)

        cur.execute("""
            UPDATE ai_risk_preguntas
            SET fase_codigo = ?,
                fase = ?,
                nist_funcion = ?,
                nist_categoria = ?,
                titulo = ?,
                pregunta = ?,
                evidencia_sugerida = ?,
                orden = ?,
                activo = 1
            WHERE codigo = ?
        """, (
            fase_codigo,
            fase,
            nist_funcion,
            nist_categoria,
            titulo,
            pregunta,
            evidencia_sugerida,
            orden,
            codigo
        ))


    conn.commit()
    conn.close()


init_ai_madurez_db()

def ai_madurez_corregir_codigos_tildes():
    """
    Corrige códigos dañados tipo CONTEXTO_DE_LA_ORGANIZACI_N
    en preguntas, análisis y resumen_json de revisiones existentes.
    No borra respuestas.
    """
    conn = get_ai_madurez_conn()
    cur = conn.cursor()

    reemplazos = {
        "CONTEXTO_DE_LA_ORGANIZACI_N": "CONTEXTO_DE_LA_ORGANIZACION",
        "PLANIFICACI_N": "PLANIFICACION",
        "OPERACI_N": "OPERACION",
        "EVALUACI_N_DEL_DESEMPE_O": "EVALUACION_DEL_DESEMPENO",
        "EVALUACI_N": "EVALUACION",
        "DESEMPE_O": "DESEMPENO",
        "GESTI_N": "GESTION",
        "INFORMACI_N": "INFORMACION",
    }

    for viejo, nuevo in reemplazos.items():
        cur.execute("""
            UPDATE ai_madurez_preguntas
            SET categoria_codigo = REPLACE(categoria_codigo, ?, ?),
                capitulo_codigo = REPLACE(capitulo_codigo, ?, ?)
            WHERE categoria_codigo LIKE '%' || ? || '%'
               OR capitulo_codigo LIKE '%' || ? || '%'
        """, (viejo, nuevo, viejo, nuevo, viejo, viejo))

        cur.execute("""
            UPDATE ai_madurez_categoria_analisis
            SET categoria_codigo = REPLACE(categoria_codigo, ?, ?),
                capitulo = REPLACE(capitulo, ?, ?)
            WHERE categoria_codigo LIKE '%' || ? || '%'
               OR capitulo LIKE '%' || ? || '%'
        """, (viejo, nuevo, viejo, nuevo, viejo, viejo))

    runs = cur.execute("SELECT id, resumen_json FROM ai_madurez_runs").fetchall()

    for run in runs:
        raw = run["resumen_json"] or "{}"

        for viejo, nuevo in reemplazos.items():
            raw = raw.replace(viejo, nuevo)

        try:
            obj = json.loads(raw)
            nuevo_resumen = {}

            for cap, cats in (obj or {}).items():
                cap_limpio = cap
                for viejo, nuevo in reemplazos.items():
                    cap_limpio = cap_limpio.replace(viejo, nuevo)

                nuevo_resumen.setdefault(cap_limpio, {})

                for cat_code, data in (cats or {}).items():
                    cat_limpio = cat_code
                    for viejo, nuevo in reemplazos.items():
                        cat_limpio = cat_limpio.replace(viejo, nuevo)

                    nuevo_resumen[cap_limpio][cat_limpio] = data

            raw = json.dumps(nuevo_resumen, ensure_ascii=False)

        except Exception:
            pass

        cur.execute("""
            UPDATE ai_madurez_runs
            SET resumen_json = ?,
                radar_overall_b64 = NULL,
                updated_at = ?
            WHERE id = ?
        """, (raw, _ai_now(), run["id"]))

    conn.commit()
    conn.close()


# ============================================================
# HELPERS
# ============================================================

def _ai_now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# Ejecutar corrección automática de códigos con tildes
try:
    ai_madurez_corregir_codigos_tildes()
except Exception as e:
    print("Corrección automática ISO 42001:", e)


def _ai_normalizar_texto(v):
    if v is None:
        return ""

    if isinstance(v, (dict, list)):
        try:
            return json.dumps(v, ensure_ascii=False, indent=2).strip()
        except Exception:
            return str(v).strip()

    return str(v or "").replace("\r\n", "\n").replace("\r", "\n").strip()

def _ai_estado_normalizado(v):
    estado = str(v or "").strip().upper()
    estado = estado.replace(" ", "")
    estado = estado.replace(".", "")
    estado = estado.replace("-", "")
    estado = estado.replace("/", "")

    if estado in ("SI", "SÍ", "YES"):
        return "SI"

    if estado in ("PARCIAL", "PARCIALMENTE", "PARTIAL"):
        return "PARCIAL"

    if estado in ("NO", "N"):
        return "NO"

    if estado in ("NA", "N/A", "NOAPLICA", "NOAPLICABLE", "NOTAPPLICABLE"):
        return "NA"

    return ""

def _ai_key(v):
    txt = str(v or "").strip()

    txt = txt.replace("ORGANIZACI_N", "ORGANIZACION")
    txt = txt.replace("PLANIFICACI_N", "PLANIFICACION")
    txt = txt.replace("OPERACI_N", "OPERACION")
    txt = txt.replace("EVALUACI_N", "EVALUACION")
    txt = txt.replace("DESEMPE_O", "DESEMPENO")
    txt = txt.replace("GESTI_N", "GESTION")
    txt = txt.replace("INFORMACI_N", "INFORMACION")

    txt = unicodedata.normalize("NFKD", txt)
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    txt = txt.upper()
    txt = re.sub(r"[^A-Z0-9]+", "_", txt)
    txt = re.sub(r"_+", "_", txt).strip("_")
    return txt

def _ai_codigo_limpio(v):
    txt = str(v or "").strip()

    reemplazos = {
        "CONTEXTO_DE_LA_ORGANIZACI_N": "CONTEXTO_DE_LA_ORGANIZACION",
        "PLANIFICACI_N": "PLANIFICACION",
        "OPERACI_N": "OPERACION",
        "EVALUACI_N_DEL_DESEMPE_O": "EVALUACION_DEL_DESEMPENO",
        "EVALUACI_N": "EVALUACION",
        "DESEMPE_O": "DESEMPENO",
        "GESTI_N": "GESTION",
        "INFORMACI_N": "INFORMACION",
    }

    for viejo, nuevo in reemplazos.items():
        txt = txt.replace(viejo, nuevo)

    return txt


def _ai_codigo_visible(v):
    txt = _ai_codigo_limpio(v)

    nombres = {
        "CONTEXTO_DE_LA_ORGANIZACION": "Contexto de la Organización",
        "PLANIFICACION": "Planificación",
        "OPERACION": "Operación",
        "EVALUACION_DEL_DESEMPENO": "Evaluación del Desempeño",
        "GESTION": "Gestión",
        "INFORMACION": "Información",
    }

    return nombres.get(txt, txt.replace("_", " ").title())

def _ai_texto_plano_desde_valor(v):
    """
    Convierte respuestas IA tipo string, dict o list en texto legible.
    Evita que se muestre JSON crudo en Estado actual / Estado requerido.
    """
    if v is None:
        return ""

    if isinstance(v, str):
        return _ai_normalizar_texto(v)

    if isinstance(v, list):
        partes = []
        for i, item in enumerate(v, start=1):
            txt = _ai_texto_plano_desde_valor(item)
            if txt:
                partes.append(f"{i}. {txt}")
        return "\n".join(partes).strip()

    if isinstance(v, dict):
        partes = []

        for k, val in v.items():
            if isinstance(val, dict):
                subpartes = []
                for sk, sv in val.items():
                    txt = _ai_texto_plano_desde_valor(sv)
                    if txt:
                        subpartes.append(f"{sk}: {txt}")

                if subpartes:
                    partes.append(f"{k}:\n" + "\n".join(subpartes))

            elif isinstance(val, list):
                txt = _ai_texto_plano_desde_valor(val)
                if txt:
                    partes.append(f"{k}:\n{txt}")

            else:
                txt = _ai_texto_plano_desde_valor(val)
                if txt:
                    partes.append(f"{k}: {txt}")

        return "\n\n".join(partes).strip()

    return str(v).strip()


def _ai_permiso(user):
    if not user:
        return False
    if user.role in ("admin", "auditor"):
        return True
    return verificar_permiso(user, AI_MADUREZ_PERMISO)


def _ai_read_only(user):
    return bool(user and user.role == "auditor")


def _ai_escape(v):
    return escape(v or "")


AI_MADUREZ_PROGRESS_JS = """
<script>
(function () {
    window.ai42001Progress = function (mensaje) {
        try {
            if (typeof window.showSGSIProgress === "function") {
                window.showSGSIProgress(
                    mensaje || "Generando y procesando información..."
                );
            }
        } catch (e) {
            console.log("Progreso IA ISO 42001:", e);
        }

        return true;
    };
})();
</script>
"""


def _ai_parse_rango_pct(rango):
    if not rango:
        return None, None
    s = str(rango).replace("%", "").replace("–", "-").strip()
    parts = [p.strip() for p in s.split("-")]
    if len(parts) != 2:
        return None, None
    try:
        return float(parts[0]), float(parts[1])
    except Exception:
        return None, None


def ai_nivel_visual_por_pct(pct):
    try:
        p = float(pct or 0)
    except Exception:
        p = 0.0
    p = max(0.0, min(100.0, p))

    color_map = {
        1: "#dc3545",
        2: "#fd7e14",
        3: "#ffc107",
        4: "#0d6efd",
        5: "#198754",
    }

    for lvl in AI_MADUREZ_LEVELS:
        lo, hi = _ai_parse_rango_pct(lvl.get("rango_pct", ""))
        if lo is None:
            continue
        if lo <= p <= hi:
            score = int(lvl.get("score", 0) or 0)
            return {
                "nivel": lvl.get("nivel", ""),
                "score": score,
                "color": color_map.get(score, "#6c757d"),
            }

    return {"nivel": "Nivel no definido", "score": 0, "color": "#6c757d"}


def _ai_limpiar_texto_rico_guardado(texto):
    txt = (texto or "").strip()
    if not txt:
        return ""

    txt = txt.replace("\r\n", "\n").replace("\r", "\n")
    txt = html.unescape(txt)
    txt = txt.replace("```json", "").replace("```", "").strip()

    try:
        obj = json.loads(txt)
        if isinstance(obj, dict):
            for k in ("informe_ejecutivo", "plan_trabajo", "texto"):
                val = obj.get(k)
                if isinstance(val, str) and val.strip():
                    txt = val.strip()
                    break
    except Exception:
        pass

    txt = html.unescape(txt)
    txt = re.sub(r"<\s*br\s*/?\s*>", "\n", txt, flags=re.IGNORECASE)
    txt = re.sub(r"<[^>]+>", "", txt)
    txt = txt.replace("**", "").replace("__", "")
    txt = re.sub(r"^\s*(INFORME EJECUTIVO|RESUMEN EJECUTIVO)\s*[:\-–—]?\s*", "", txt, flags=re.IGNORECASE)
    txt = re.sub(r"[ \t]+\n", "\n", txt)
    txt = re.sub(r"\n[ \t]+", "\n", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt)

    return txt.strip()


def _ai_extraer_json_objeto(raw):
    txt = (raw or "").strip()
    if not txt:
        return {}

    txt = txt.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(txt)
    except Exception:
        pass

    try:
        start = txt.find("{")
        end = txt.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(txt[start:end + 1])
    except Exception:
        pass

    return {}


def _ai_build_plan_accion_texto(plan_list):
    if not isinstance(plan_list, list):
        return ""

    lines = []
    for i, it in enumerate(plan_list, start=1):
        accion = _ai_normalizar_texto(it.get("accion"))
        prioridad = _ai_normalizar_texto(it.get("prioridad"))
        responsable = _ai_normalizar_texto(it.get("responsable_sugerido"))
        plazo = _ai_normalizar_texto(it.get("plazo"))
        evidencia = _ai_normalizar_texto(it.get("evidencia_esperada"))

        lines.append(
            f"{i}. Acción: {accion or 'Sin definir'}\n"
            f"   Prioridad: {prioridad or 'Sin definir'}\n"
            f"   Responsable sugerido: {responsable or 'Sin definir'}\n"
            f"   Plazo: {plazo or 'Sin definir'}\n"
            f"   Evidencia esperada: {evidencia or 'Sin definir'}"
        )

    return "\n\n".join(lines).strip()


def _ai_normalizar_plan_accion_texto(texto_raw):
    txt = (texto_raw or "").strip()
    if not txt:
        return ""

    txt = txt.replace("```json", "").replace("```", "").strip()
    obj = _ai_extraer_json_objeto(txt)

    if isinstance(obj, dict):
        plan_list = obj.get("plan_accion") or obj.get("plan") or obj.get("acciones")
        plan_txt = _ai_build_plan_accion_texto(plan_list or [])
        if plan_txt:
            return plan_txt

        bloques = []
        if obj.get("estado_actual"):
            bloques.append("Estado actual:\n" + _ai_normalizar_texto(obj.get("estado_actual")))
        if obj.get("estado_requerido"):
            bloques.append("Estado requerido:\n" + _ai_normalizar_texto(obj.get("estado_requerido")))
        if bloques:
            return "\n\n".join(bloques).strip()

    return txt


def ai_cargar_preguntas():
    init_ai_madurez_db()
    conn = get_ai_madurez_conn()
    rows = conn.execute("""
        SELECT * FROM ai_madurez_preguntas
        WHERE activo = 1
        ORDER BY capitulo ASC, categoria_codigo ASC, orden ASC, id ASC
    """).fetchall()
    conn.close()
    return rows


def ai_cargar_respuestas(run_id):
    out = {}
    if not run_id:
        return out

    conn = get_ai_madurez_conn()
    rows = conn.execute(
        "SELECT * FROM ai_madurez_respuestas WHERE run_id = ?",
        (run_id,)
    ).fetchall()
    conn.close()

    for r in rows:
        out[int(r["pregunta_id"])] = {
            "estado": _ai_estado_normalizado(r["estado"]),
            "comentario": (r["comentario"] or "").strip(),
        }

    return out


def ai_obtener_borrador(user_id):
    if not user_id:
        return None

    conn = get_ai_madurez_conn()
    row = conn.execute("""
        SELECT * FROM ai_madurez_runs
        WHERE user_id = ? AND estado = 'BORRADOR'
        ORDER BY updated_at DESC, id DESC
        LIMIT 1
    """, (user_id,)).fetchone()
    conn.close()
    return row


def ai_calcular_progreso(preguntas, form_data=None, respuestas_db=None):
    total = len(preguntas)
    respondidas = 0

    for q in preguntas:
        qid = int(q["id"])
        estado = ""

        if form_data is not None:
            estado = _ai_estado_normalizado(form_data.get(f"st_{qid}"))
        elif respuestas_db is not None:
            estado = _ai_estado_normalizado(respuestas_db.get(qid, {}).get("estado"))

        if estado in ("SI", "PARCIAL", "NO", "NA"):
            respondidas += 1

    pct = int(round((respondidas / total) * 100)) if total else 0
    return respondidas, total, pct


def ai_group_questions():
    preguntas = ai_cargar_preguntas()
    grouped = {}

    for q in preguntas:
        cap = q["capitulo"] or "Sin capítulo"
        cat_code = q["categoria_codigo"] or cap
        categoria = q["categoria"] or cap

        grouped.setdefault(cap, {})
        grouped[cap].setdefault(cat_code, {"categoria": categoria, "items": []})
        grouped[cap][cat_code]["items"].append(q)

    return grouped


def ai_resumen_desde_run(run_id):
    conn = get_ai_madurez_conn()

    rows = conn.execute("""
        SELECT
            p.capitulo,
            COALESCE(p.categoria_codigo, p.capitulo) AS categoria_codigo,
            COALESCE(p.categoria, p.capitulo) AS categoria,
            r.estado
        FROM ai_madurez_respuestas r
        INNER JOIN ai_madurez_preguntas p ON p.id = r.pregunta_id
        WHERE r.run_id = ?
        ORDER BY p.capitulo ASC, p.categoria_codigo ASC, p.orden ASC
    """, (run_id,)).fetchall()

    conn.close()

    resumen = {}

    for row in rows:
        estado = _ai_estado_normalizado(row["estado"])

        if estado not in ("SI", "PARCIAL", "NO", "NA"):
            continue

        cap = row["capitulo"] or "Sin capítulo"
        cat = _ai_codigo_limpio(row["categoria_codigo"] or cap)
        cat_name = row["categoria"] or _ai_codigo_visible(cat)

        resumen.setdefault(cap, {})
        resumen[cap].setdefault(cat, {
            "categoria": cat_name,
            "total": 0,
            "total_respondidas": 0,
            "validos": 0,
            "si": 0,
            "parcial": 0,
            "no": 0,
            "na": 0,
            "score": 0.0,
            "pct": 0.0,
        })

        d = resumen[cap][cat]
        d["total"] += 1
        d["total_respondidas"] += 1

        # N/A cuenta como respondida, pero NO entra al porcentaje
        if estado == "NA":
            d["na"] += 1
            continue

        score = AI_STATUS_SCORE.get(estado)

        if score is None:
            continue

        d["validos"] += 1
        d["score"] += float(score)

        if estado == "SI":
            d["si"] += 1
        elif estado == "PARCIAL":
            d["parcial"] += 1
        elif estado == "NO":
            d["no"] += 1

    # Calcula porcentaje por categoría
    categorias_validas_pct = []

    for cap, cats in resumen.items():
        for cat, d in cats.items():
            validos = int(d.get("validos") or 0)
            score = float(d.get("score") or 0)

            if validos > 0:
                d["pct"] = round((score / validos) * 100, 2)
                categorias_validas_pct.append(float(d["pct"]))
            else:
                d["pct"] = 0.0

    # Cálculo general correcto:
    # promedio simple de categorías válidas,
    # NO promedio por cantidad de preguntas.
    pct_general = (
        round(sum(categorias_validas_pct) / len(categorias_validas_pct), 2)
        if categorias_validas_pct
        else 0.0
    )

    return resumen, pct_general

def ai_pct_por_capitulo(resumen):
    labels = []
    values = []

    ordered = []

    for cap in AI_CAP_ORDER_DEFAULT:
        if cap in (resumen or {}):
            ordered.append(cap)

    for cap in (resumen or {}).keys():
        if cap not in ordered:
            ordered.append(cap)

    for cap in ordered:
        cats = (resumen or {}).get(cap, {}) or {}
        pcts_validos = []

        for _cat_code, d in cats.items():
            validos = int(d.get("validos", 0) or 0)

            if validos <= 0:
                continue

            pcts_validos.append(float(d.get("pct", 0) or 0))

        labels.append(cap)
        values.append(
            round(sum(pcts_validos) / len(pcts_validos), 2)
            if pcts_validos
            else 0.0
        )

    return labels, values

def ai_recalcular_y_actualizar_run(run_id):
    conn = get_ai_madurez_conn()

    rows = conn.execute("""
        SELECT id, estado
        FROM ai_madurez_respuestas
        WHERE run_id = ?
    """, (run_id,)).fetchall()

    for r in rows:
        estado_norm = _ai_estado_normalizado(r["estado"])

        if estado_norm:
            conn.execute("""
                UPDATE ai_madurez_respuestas
                SET estado = ?
                WHERE id = ?
            """, (estado_norm, r["id"]))

    conn.commit()
    conn.close()

    resumen, pct_general = ai_resumen_desde_run(run_id)

    conn = get_ai_madurez_conn()
    conn.execute("""
        UPDATE ai_madurez_runs
        SET resumen_json = ?,
            pct_general = ?,
            radar_overall_b64 = NULL,
            updated_at = ?
        WHERE id = ?
    """, (
        json.dumps(resumen, ensure_ascii=False),
        pct_general,
        _ai_now(),
        run_id
    ))

    conn.commit()
    conn.close()

    return resumen, pct_general


def ai_radar_b64(labels, values, title="Radar ISO 42001"):
    if not labels:
        return ""

    vals = [max(0.0, min(100.0, float(v or 0))) for v in values]
    N = len(labels)

    angles = [n / float(N) * 2 * math.pi for n in range(N)]
    angles += angles[:1]
    plot_vals = vals + vals[:1]

    fig = plt.figure(figsize=(3.55, 3.55), dpi=170)
    ax = plt.subplot(111, polar=True)
    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=6.6)
    ax.tick_params(axis="x", pad=9)
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=7)
    ax.plot(angles, plot_vals, linewidth=2.0)
    ax.fill(angles, plot_vals, alpha=0.16)
    ax.set_title(title, fontsize=9.5, pad=14)
    fig.subplots_adjust(top=0.83, bottom=0.10, left=0.10, right=0.90)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", transparent=True, bbox_inches="tight", pad_inches=0.22)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def ai_importar_instrumento_desde_excel(path_excel, force=False):
    if not os.path.exists(path_excel):
        raise FileNotFoundError(f"No existe el archivo del instrumento: {path_excel}")

    init_ai_madurez_db()

    conn = get_ai_madurez_conn()
    cur = conn.cursor()

    total_actual = cur.execute("SELECT COUNT(*) AS c FROM ai_madurez_preguntas").fetchone()["c"]
    if total_actual and not force:
        conn.close()
        return 0

    if force:
        cur.execute("DELETE FROM ai_madurez_categoria_analisis")
        cur.execute("DELETE FROM ai_madurez_respuestas")
        cur.execute("DELETE FROM ai_madurez_runs")
        cur.execute("DELETE FROM ai_madurez_preguntas")
        conn.commit()

    wb = load_workbook(path_excel, data_only=True)
    ws = wb[wb.sheetnames[0]]

    capitulo_actual = "General"
    categoria_actual = "General"
    categoria_codigo = "GENERAL"
    orden = 0
    insertados = 0

    for row in ws.iter_rows(min_row=1, values_only=True):
        pregunta = row[0] if row and len(row) else None
        texto = str(pregunta or "").strip()

        if not texto:
            continue

        lower = texto.lower()

        if lower in ("pregunta", "preguntas"):
            continue

        # Encabezados tipo: "Cláusula – Contexto de la Organización"
        if lower.startswith("cláusula") or lower.startswith("clausula") or lower.startswith("anexo") or lower.startswith("annex"):
            limpio = texto
            limpio = re.sub(r"^cl[áa]usula\s*[–—-]\s*", "", limpio, flags=re.IGNORECASE).strip()
            limpio = re.sub(r"^anexo\s*[–—-]?\s*", "Anexo ", limpio, flags=re.IGNORECASE).strip()
            capitulo_actual = limpio or texto
            categoria_actual = capitulo_actual
            categoria_codigo = _ai_key(capitulo_actual) or "GENERAL"
            continue

        # Filas normales de pregunta
        orden += 1
        cur.execute("""
            INSERT INTO ai_madurez_preguntas
            (capitulo, capitulo_codigo, categoria, categoria_codigo, orden, pregunta, activo)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (
            capitulo_actual,
            categoria_codigo,
            categoria_actual,
            categoria_codigo,
            orden,
            texto,
        ))
        insertados += 1

    conn.commit()
    conn.close()
    return insertados


def _ai_items_categoria(run_id, cap_u, cat_u):
    cap_u = (cap_u or "").upper().strip()
    cat_u = (cat_u or "").upper().strip()

    conn = get_ai_madurez_conn()

    rows = conn.execute("""
        SELECT p.capitulo, p.categoria_codigo, p.categoria, p.pregunta, r.estado, r.comentario
        FROM ai_madurez_respuestas r
        INNER JOIN ai_madurez_preguntas p ON p.id = r.pregunta_id
        WHERE r.run_id = ?
          AND (
                UPPER(TRIM(p.capitulo)) = ?
             OR UPPER(TRIM(COALESCE(p.categoria_codigo, ''))) = ?
             OR UPPER(TRIM(COALESCE(p.categoria, ''))) = ?
          )
        ORDER BY p.orden ASC, p.id ASC
    """, (run_id, cap_u, cat_u, cat_u)).fetchall()

    conn.close()

    items = []
    for r in rows:
        estado = (r["estado"] or "").strip().upper()

        if estado not in ("SI", "PARCIAL", "NO", "NA"):
            continue

        items.append({
            "pregunta": _ai_normalizar_texto(r["pregunta"] or ""),
            "estado": estado,
            "comentario": _ai_normalizar_texto(r["comentario"] or ""),
        })

    return items


# ============================================================
# PROMPTS IA
# ============================================================

def _ai_prompt_categoria(capitulo, categoria_codigo, categoria_nombre, pct, items):
    bullets = []
    for it in items[:80]:
        pregunta = (it.get("pregunta") or "")[:320].replace("\n", " ")
        comentario = (it.get("comentario") or "")[:420].replace("\n", " ")
        estado = (it.get("estado") or "").strip().upper()

        linea = f"- Estado: {estado}. Pregunta: {pregunta}"
        if comentario:
            linea += f" Evidencia/comentario: {comentario}"

        bullets.append(linea)

    joined = "\n".join(bullets) if bullets else "- Sin evidencias registradas."

    return f"""
Eres un consultor experto en ISO/IEC 42001, gobierno de IA, gestión de riesgos de IA, seguridad de la información y sistemas de gestión.

CONTEXTO:
Capítulo: {capitulo}
Categoría: {categoria_codigo}
Nombre categoría: {categoria_nombre}
Cumplimiento actual: {pct:.2f}%

EVIDENCIAS:
{joined}

INSTRUCCIONES:
Devuelve únicamente JSON válido.
No uses markdown.
No devuelvas objetos anidados.
No agrupes por capítulo.
No uses llaves internas como SI, PARCIAL, NO o TODOS.
Cada campo debe ser texto plano.

ESTRUCTURA EXACTA:
{{
  "estado_actual": "Texto ejecutivo en párrafo, claro y profesional.",
  "estado_requerido": "Texto ejecutivo en párrafo, claro y profesional.",
  "plan_accion": [
    {{
      "accion": "Texto de la acción.",
      "prioridad": "Alta",
      "responsable_sugerido": "Texto del responsable sugerido.",
      "plazo": "Texto del plazo.",
      "evidencia_esperada": "Texto de la evidencia esperada."
    }}
  ]
}}

REGLAS:
Escribe en español.
El estado actual debe explicar qué muestran las respuestas SI, PARCIAL, NO y NA.
El estado requerido debe describir la condición objetivo para cumplir ISO/IEC 42001.
El plan de acción debe tener entre 3 y 6 acciones.
Si falta evidencia, indícalo dentro del texto ejecutivo, no como JSON.
""".strip()


def _ai_prompt_informe_ejecutivo(run, resumen):
    partes = []
    labels, vals = ai_pct_por_capitulo(resumen)
    pct_por_cap = dict(zip(labels, vals))

    for cap, cats in (resumen or {}).items():
        lineas = []
        for cat_code, d in cats.items():
            lineas.append(
                f"  * {cat_code} - {d.get('categoria','')}: {float(d.get('pct',0) or 0):.2f}% "
                f"({int(d.get('total',0) or 0)} ítems)"
            )
        partes.append(f"- {cap}: {pct_por_cap.get(cap, 0):.2f}%\n" + "\n".join(lineas[:25]))

    detalle = "\n".join(partes)

    return f"""
Eres un consultor senior en ISO/IEC 42001, gobierno de Inteligencia Artificial, seguridad de la información y gestión de riesgos.
Debes redactar un INFORME EJECUTIVO para alta dirección, claro, breve, profesional y accionable.

DATOS GENERALES
Consecutivo: {run["consecutivo"]}
Cumplimiento general: {float(run["pct_general"] or 0):.2f}%
Nivel general: {ai_nivel_visual_por_pct(run["pct_general"]).get("nivel","")}

RESULTADOS POR CAPÍTULO Y CATEGORÍA
{detalle}

INSTRUCCIONES
Devuelve solamente JSON válido.
Estructura exacta:
{{"informe_ejecutivo":"texto"}}

REGLAS DEL TEXTO
Escribe en español.
Extensión aproximada: 4 a 7 párrafos cortos.
Incluye: resumen general, fortalezas, brechas, capítulos más débiles, riesgos ejecutivos y prioridades de 90 días.
No uses markdown ni viñetas.
No inventes herramientas específicas.
""".strip()


def _ai_prompt_plan_trabajo(run, resumen):
    partes = []
    for cap, cats in (resumen or {}).items():
        for cat_code, d in cats.items():
            pct = float(d.get("pct", 0) or 0)
            partes.append(
                f"- {cap} | {cat_code} - {d.get('categoria','')}: "
                f"{pct:.2f}% | brecha {100-pct:.2f}% | {int(d.get('total',0) or 0)} ítems"
            )

    detalle = "\n".join(partes)

    return f"""
Eres un consultor senior en ISO/IEC 42001 y gobierno de Inteligencia Artificial.
Construye un PLAN DE TRABAJO GENERAL para cerrar brechas de madurez del sistema de gestión de IA.

DATOS GENERALES
Consecutivo: {run["consecutivo"]}
Cumplimiento general: {float(run["pct_general"] or 0):.2f}%
Nivel general: {ai_nivel_visual_por_pct(run["pct_general"]).get("nivel","")}

RESULTADOS
{detalle}

INSTRUCCIONES
Devuelve solamente JSON válido.
Estructura exacta:
{{"plan_trabajo":[{{"frente":"string","actividad":"string","prioridad":"Alta|Media|Baja","responsable_sugerido":"string","plazo":"string","entregable":"string"}}]}}

REGLAS
Genera entre 8 y 15 actividades.
Prioriza categorías con menor cumplimiento.
Usa lenguaje ejecutivo y accionable.
No inventes herramientas específicas.
""".strip()


def _ai_call_text(prompt, max_tokens=1200):
    try:
        prompt = (prompt or "").strip()
        if not prompt:
            raise RuntimeError("Prompt vacío para IA.")

        try:
            return _ai_text(prompt, max_tokens=max_tokens)
        except TypeError:
            return _ai_text(prompt)

    except NameError:
        raise RuntimeError("No existe el helper global _ai_text(). Integra este módulo después del helper IA usado por NIST.")
    except Exception as e:
        raise RuntimeError(f"Error real llamando IA: {e}")


# ============================================================
# CSS BASE — MISMO PATRÓN NIST CSF 2.0
# ============================================================

def ai_css(prefix="aimad", icon="🤖", tag="SGSI · ISO 42001"):
    return f"""
<style>
  .bg-purple{{ background-color:#6f42c1 !important; }}
  .badge.bg-purple{{ color:#ffffff !important; }}

  body{{
    background-image:url('/static/img/ccsgsi.jpg');
    background-size:cover;
    background-position:center;
    background-attachment:fixed;
    background-repeat:no-repeat;
  }}

  .{prefix}-shell{{
    width:96%;
    max-width:1600px;
    margin:26px auto 24px auto;
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
    margin-bottom:14px;
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
    background:transparent !important;
    padding:0 !important;
    position:relative;
    z-index:1;
  }}

  .{prefix}-header-overlay::before{{
    content:"{icon}";
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

  .{prefix}-header-text{{
    max-width:1100px;
    width:100%;
    display:block !important;
  }}

  .{prefix}-header-text::before{{
    content:"{tag}";
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
    margin:0 !important;
    text-shadow:0 3px 10px rgba(0,0,0,.35);
  }}

  .{prefix}-subtitle{{
    color:rgba(255,255,255,.95);
    font-size:.78rem;
    margin-top:4px;
  }}

  .{prefix}-header-actions{{
    display:flex;
    justify-content:center;
    gap:10px;
    flex-wrap:wrap;
    margin:10px 0 14px;
  }}

  .{prefix}-header-actions .btn,
  .btn{{
    border-radius:10px !important;
    font-weight:900;
  }}

  .{prefix}-btn-main{{
    background:#ffffff;
    color:#0f172a !important;
    border:1px solid #cfd8e3 !important;
  }}

  .{prefix}-btn-main:hover{{
    background:#edf5ff;
    color:#0b65d8 !important;
  }}

  .{prefix}-btn-soft{{
    background:rgba(255,255,255,.88);
    color:#111 !important;
    border:1px solid rgba(108,117,125,.35);
  }}

  .{prefix}-card,
  .card{{
    background:rgba(255,255,255,.96) !important;
    border-radius:18px !important;
    backdrop-filter:blur(8px);
    box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
  }}

  .card-body{{ padding:18px; }}

  .{prefix}-section-title{{
    color:#1d4f8f;
    font-weight:950;
    font-size:1rem;
    margin-bottom:10px;
  }}

  .table-responsive{{
    max-height:72vh;
    overflow:auto;
    border-radius:14px;
    background:#ffffff;
  }}

  .table thead th{{
    position:sticky;
    top:0;
    background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
    color:#ffffff !important;
    font-size:.78rem;
    font-weight:900;
    text-align:center;
    z-index:2;
  }}

  .table tbody td{{
    font-size:.82rem;
    padding:9px;
    vertical-align:top;
  }}

  .table tbody tr:nth-child(even){{ background:#f8fbff; }}
  .table tbody tr:hover{{ background:#eef6ff; }}

  .form-control,
  .form-select{{
    border-radius:10px;
    border:1px solid #d9e3f0;
    min-height:40px;
  }}

  .form-control:focus,
  .form-select:focus{{
    border-color:#3f86d6;
    box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
  }}

  .ai-progress-wrap{{
    background:rgba(255,255,255,.92);
    border-radius:16px;
    padding:12px 16px;
    box-shadow:0 8px 20px rgba(15,23,42,.14);
  }}

  .ai-progress-bar{{
    height:18px;
    border-radius:999px;
    overflow:hidden;
    background:#e9eef6;
  }}

  .ai-progress-fill{{
    height:100%;
    background:linear-gradient(135deg,#0b4a8f,#1d5fae);
    color:#fff;
    font-size:.72rem;
    font-weight:900;
    text-align:center;
    line-height:18px;
  }}

  .ai-kpi{{
    border-radius:16px;
    background:#ffffff;
    border:1px solid #e2e8f0;
    padding:8px 7px;
    height:100%;
  }}

  .ai-kpi-value{{
    font-size:1.45rem;
    font-weight:950;
    color:#0b4a8f;
  }}

  .ai-kpi-label{{
    color:#475569;
    font-size:.78rem;
    font-weight:800;
  }}

  @media (max-width:768px){{
    .{prefix}-header-overlay{{
      flex-direction:column;
      text-align:center;
      gap:10px;
    }}

    .{prefix}-header-overlay::before{{ margin:0; }}

    .{prefix}-header-text::before{{
      margin-left:auto;
      margin-right:auto;
    }}

    .{prefix}-title,
    .{prefix}-subtitle{{ text-align:center; }}

    .{prefix}-header-actions .btn{{ width:100%; }}
  }}
</style>
"""


def ai_header(prefix, title, subtitle, icon="🤖", tag="SGSI · ISO 42001"):
    return f"""
<div class="{prefix}-header-card">
  <div class="{prefix}-header-overlay">
    <div class="{prefix}-header-text">
      <h3 class="{prefix}-title m-0">{title}</h3>
      <div class="{prefix}-subtitle">{subtitle}</div>
    </div>
  </div>
</div>
{ai_css(prefix, icon, tag)}
"""


# ============================================================
# RUTAS
# ============================================================

@ai_madurez_bp.route("/", methods=["GET"])
@login_required
def home():
    init_ai_madurez_db()
    user = User.query.get(session.get("user_id"))

    if not _ai_permiso(user):
        flash("No tiene permiso para acceder al módulo de Nivel de Madurez de Gestión de Inteligencia Artificial.", "danger")
        return redirect(url_for("menu"))

    read_only = _ai_read_only(user)
    conn = get_ai_madurez_conn()
    total = conn.execute("SELECT COUNT(*) AS c FROM ai_madurez_preguntas").fetchone()["c"]
    conn.close()

    if read_only:
        ingreso_btn = """
          <button class="btn btn-secondary rounded-pill px-4 fw-bold" disabled
                  title="El rol Auditor no puede ingresar información">
            <i class="bi bi-pencil-square me-2"></i>Ingresar la información
          </button>
        """
        parametros_btn = """
          <button class="btn btn-outline-secondary rounded-pill px-3" disabled
                  title="El rol Auditor no tiene acceso a Parámetros">
            <i class="bi bi-gear me-2"></i>Parámetros
          </button>
        """
    else:
        ingreso_btn = f"""
          <a href="{url_for('madurez_ai.ingreso')}" class="btn btn-primary rounded-pill px-4 fw-bold grac-nav-blue-btn">
            <i class="bi bi-pencil-square me-2"></i>Ingresar la información
          </a>
        """
        parametros_btn = f"""
          <a href="{url_for('madurez_ai.parametros')}" class="btn btn-outline-secondary rounded-pill px-3">
            <i class="bi bi-gear me-2"></i>Parámetros
          </a>
        """

    if total == 0:
        badge = '<span class="badge bg-danger ms-2">Instrumento NO cargado</span>'
        hint = "Primero entra a Parámetros y realiza la importación del instrumento ISO 42001."
    else:
        badge = '<span class="badge bg-success ms-2">Instrumento cargado</span>'
        hint = "Puedes ingresar la información o consultar el historial de revisiones."

    content = f"""
<div class="aimad-shell">

  {ai_header(
      "aimad",
      "Nivel de Madurez — Sistema de Gestión de Inteligencia Artificial",
      "Evaluación de madurez del Sistema de Gestión de IA basada en ISO/IEC 42001 y controles asociados.",
      "🤖",
      "SGSI · ISO 42001"
  )}

  <div class="aimad-header-actions">
    {ingreso_btn}
    <a href="{url_for('madurez_ai.historial')}" class="btn aimad-btn-soft rounded-pill px-4">
      <i class="bi bi-clock-history me-2"></i>Historial de Revisiones
    </a>
    <a href="{url_for('madurez_ai.ai_risk_home')}" class="btn btn-warning rounded-pill px-4 fw-bold">
      <i class="bi bi-exclamation-diamond-fill me-2"></i>Nivel de Madurez de Riesgos — NIST AI RMF
    </a>
  </div>

  <div class="row g-3 mt-2">
    <div class="col-12 col-lg-8">
      <div class="aimad-card p-4 h-100">
        <div class="aimad-section-title">Estado del instrumento</div>

        <div class="d-flex justify-content-between align-items-start flex-wrap gap-3">
          <div>
            <div class="fw-bold">Estado del instrumento {badge}</div>
            <div class="text-muted small mt-1">Preguntas cargadas: <b>{total}</b></div>
            <div class="mt-2 small">{hint}</div>
          </div>

          <div class="text-end">
            <div class="text-muted small">Acceso rápido</div>
            <div class="d-flex gap-2 flex-wrap justify-content-end mt-2">
              {parametros_btn}
            </div>
          </div>
        </div>

        <div class="alert alert-info mt-3 mb-0 small">
          <b>Sugerencia:</b> Usa <b>Parámetros</b> para cargar el instrumento y revisar la escala de madurez 1–5.
        </div>
      </div>
    </div>

    <div class="col-12 col-lg-4">
      <div class="aimad-card p-4 h-100">
        <div class="aimad-section-title">¿Qué puedes hacer aquí?</div>
        <ul class="small mb-0 text-black ps-3">
          <li><b>Ingresar información:</b> responder Sí/Parcial/No/N/A con comentarios.</li>
          <li><b>Historial:</b> consultar evaluaciones previas.</li>
          <li><b>Detalle:</b> ver cumplimiento, radar, informe IA, plan de trabajo y PDF.</li>
          <li><b>Riesgos de IA:</b> evaluar proyectos durante todo su ciclo de vida con NIST AI RMF.</li>
        </ul>
      </div>
    </div>
  </div>
</div>
"""
    return render_template_string(BASE, title="Madurez Gestión IA", content=content)


@ai_madurez_bp.route("/parametros", methods=["GET"])
@login_required
def parametros():
    init_ai_madurez_db()
    user = User.query.get(session.get("user_id"))

    if not _ai_permiso(user):
        flash("No tiene permiso para acceder a Parámetros del módulo de Gestión de IA.", "danger")
        return redirect(url_for("menu"))

    if user.role == "auditor":
        flash("El rol Auditor no tiene acceso a Parámetros.", "warning")
        return redirect(url_for("madurez_ai.home"))

    conn = get_ai_madurez_conn()
    total = conn.execute("SELECT COUNT(*) AS c FROM ai_madurez_preguntas").fetchone()["c"]
    conn.close()

    badge = '<span class="badge bg-danger ms-2">Instrumento NO cargado</span>' if total == 0 else '<span class="badge bg-success ms-2">Instrumento cargado</span>'

    rows = ""
    for lvl in AI_MADUREZ_LEVELS:
        rows += f"""
        <tr>
          <td class="fw-semibold">{escape(lvl["nivel"])}</td>
          <td class="text-muted">{escape(lvl["descripcion"])}</td>
          <td class="text-center fw-bold">{lvl["score"]}</td>
          <td class="text-center">{escape(lvl["rango_pct"])}</td>
          <td class="text-muted">{escape(lvl["logica"])}</td>
        </tr>
        """

    content = f"""
<div class="aipar-shell">
  {ai_header(
      "aipar",
      "Parámetros — Madurez Gestión de Inteligencia Artificial",
      "Configuración del instrumento ISO 42001 y definición de niveles de madurez.",
      "⚙️",
      "SGSI · Parámetros ISO 42001"
  )}

  <div class="aipar-header-actions">
    <a href="{url_for('madurez_ai.home')}" class="btn aipar-btn-main rounded-pill px-4 fw-bold">
      <i class="bi bi-arrow-left me-2"></i>Volver al Menú Principal de Madurez IA
    </a>
  </div>

  <div class="row g-3 mt-2">
    <div class="col-12 col-lg-5">
      <div class="aipar-card p-4 h-100">
        <div class="aipar-section-title">Instrumento</div>

        <div class="text-muted small">
          Preguntas cargadas: <b>{total}</b> {badge}
        </div>

        <div class="d-flex gap-2 flex-wrap mt-3">
          <form method="POST" action="{url_for('madurez_ai.importar_instrumento')}">
            <button class="btn btn-danger rounded-pill px-4">
              <i class="bi bi-database-add me-2"></i>Importar instrumento
            </button>
          </form>

          <form method="POST" action="{url_for('madurez_ai.importar_instrumento', force=1)}">
            <button class="btn btn-outline-danger rounded-pill px-4">
              <i class="bi bi-arrow-repeat me-2"></i>Re-importar force
            </button>
          </form>
        </div>

        <div class="alert alert-warning mt-3 mb-0 small">
          <b>Nota:</b> “Re-importar force” elimina preguntas, runs, respuestas y análisis del módulo IA.
        </div>

        <div class="mt-3">
          <a href="{url_for('madurez_ai.ingreso')}" class="btn btn-primary rounded-pill px-4 w-100 fw-semibold grac-nav-blue-btn">
            <i class="bi bi-pencil-square me-2"></i>Ir a Ingresar la información
          </a>
        </div>
      </div>
    </div>

    <div class="col-12 col-lg-7">
      <div class="aipar-card p-4 h-100">
        <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-2">
          <div class="aipar-section-title mb-0">📌 Niveles de Madurez</div>
          <span class="badge bg-secondary">1 a 5</span>
        </div>

        <div class="table-responsive">
          <table class="table table-sm align-middle mb-0">
            <thead>
              <tr>
                <th style="width:28%;">Nivel de Madurez</th>
                <th>Descripción</th>
                <th style="width:70px;">Score</th>
                <th style="width:110px;">Rango %</th>
                <th style="width:22%;">Lógica</th>
              </tr>
            </thead>
            <tbody>{rows}</tbody>
          </table>
        </div>

        <div class="small text-muted mt-3">
          El puntaje se calcula por cumplimiento: Sí = 100%, Parcial = 50%, No = 0%, N/A se excluye.
        </div>
      </div>
    </div>
  </div>
</div>
"""
    return render_template_string(BASE, title="Parámetros Madurez IA", content=content)


@ai_madurez_bp.route("/parametros/importar", methods=["POST"])
@login_required
def importar_instrumento():
    user = User.query.get(session.get("user_id"))

    if not _ai_permiso(user) or user.role == "auditor":
        flash("No tiene permiso para importar el instrumento de Gestión de IA.", "danger")
        return redirect(url_for("madurez_ai.home"))

    force = str(request.args.get("force", "")).strip() == "1"

    try:
        insertados = ai_importar_instrumento_desde_excel(AI_INSTRUMENTO_DEFAULT, force=force)
        if insertados == 0:
            flash("ℹ️ El instrumento ya estaba cargado. Usa Re-importar force si deseas recargarlo.", "info")
        else:
            flash(f"✅ Instrumento ISO 42001 importado correctamente. Preguntas cargadas: {insertados}.", "success")
    except Exception as e:
        flash(f"❌ Error importando instrumento: {e}", "danger")

    return redirect(url_for("madurez_ai.parametros"))


@ai_madurez_bp.route("/ingreso", methods=["GET"])
@login_required
def ingreso():
    init_ai_madurez_db()
    user = User.query.get(session.get("user_id"))

    if not _ai_permiso(user):
        flash("No tiene permiso para acceder al módulo de nivel de madurez de Gestión de Inteligencia Artificial.", "danger")
        return redirect(url_for("menu"))

    if user.role == "auditor":
        flash("El rol Auditor no puede ingresar la información en este módulo.", "warning")
        return redirect(url_for("madurez_ai.home"))

    preguntas = ai_cargar_preguntas()

    if not preguntas:
        flash("⚠️ Primero debes importar el instrumento ISO 42001.", "warning")
        return redirect(url_for("madurez_ai.parametros"))

    draft = ai_obtener_borrador(user.id if user else None)
    respuestas_guardadas = ai_cargar_respuestas(draft["id"]) if draft else {}
    consecutivo_val = (draft["consecutivo"] if draft else "") or ""

    _, _, progreso_inicial = ai_calcular_progreso(
        preguntas,
        respuestas_db=respuestas_guardadas
    )

    grouped = ai_group_questions()

    acc_html = []
    acc_id = 0

    def esc(x):
        return escape(x or "")

    for cap_name, cats in grouped.items():
        acc_id += 1
        func_key = f"func{acc_id}"
        inner = []

        for cat_code, payload in cats.items():
            rows = []

            for q in payload["items"]:
                qid = int(q["id"])
                saved = respuestas_guardadas.get(qid, {})
                saved_estado = (saved.get("estado") or "").strip().upper()
                saved_com = esc(saved.get("comentario") or "")
                qtext = q["pregunta"] or ""
                orden = q["orden"] or 0

                chk_na = "checked" if saved_estado == "NA" else ""
                chk_si = "checked" if saved_estado == "SI" else ""
                chk_pa = "checked" if saved_estado == "PARCIAL" else ""
                chk_no = "checked" if saved_estado == "NO" else ""

                rows.append(f"""
                <div class="col-12 col-xl-6">
                  <div class="nistform-qcard h-100">
                    <div class="nistform-qhead">
                      <div class="d-flex align-items-center gap-2 flex-wrap">
                        <span class="badge rounded-pill text-bg-light border fw-semibold">
                          {esc(cat_code)}
                        </span>
                        <span class="badge rounded-pill text-bg-primary">
                          Orden {orden}
                        </span>
                      </div>
                    </div>

                    <div class="nistform-qtext">
                      {esc(qtext)}
                    </div>

                    <div class="nistform-radio-row">
                      <label class="nistform-radio-card">
                        <input class="form-check-input" type="radio" name="st_{qid}" value="NA" {chk_na}>
                        <span>N/A</span>
                      </label>

                      <label class="nistform-radio-card">
                        <input class="form-check-input" type="radio" name="st_{qid}" value="SI" {chk_si}>
                        <span>Sí</span>
                      </label>

                      <label class="nistform-radio-card">
                        <input class="form-check-input" type="radio" name="st_{qid}" value="PARCIAL" {chk_pa}>
                        <span>Parcial</span>
                      </label>

                      <label class="nistform-radio-card">
                        <input class="form-check-input" type="radio" name="st_{qid}" value="NO" {chk_no}>
                        <span>No</span>
                      </label>
                    </div>

                    <div class="mt-3">
                      <label class="form-label small fw-bold text-black mb-1">Comentarios / evidencia</label>
                      <textarea class="form-control form-control-sm"
                                name="cm_{qid}"
                                rows="3"
                                placeholder="Comentarios / evidencia">{saved_com}</textarea>
                    </div>
                  </div>
                </div>
                """)

            inner.append(f"""
            <div class="nistform-cat-block">
              <div class="nistform-cat-title">
                <div>
                  <div class="nistform-cat-code">{esc(cat_code)}</div>
                  <div class="nistform-cat-name">{esc(payload.get('categoria', ''))}</div>
                </div>
                <div>
                  <span class="badge rounded-pill text-bg-secondary">{len(payload["items"])} preguntas</span>
                </div>
              </div>

              <div class="row g-3">
                {''.join(rows)}
              </div>
            </div>
            """)

        acc_html.append(f"""
        <div class="accordion-item nistform-acc-item">
          <h2 class="accordion-header" id="h{func_key}">
            <button class="accordion-button {'collapsed' if acc_id != 1 else ''} nistform-acc-btn"
                    type="button"
                    data-bs-toggle="collapse"
                    data-bs-target="#c{func_key}"
                    aria-expanded="{str(acc_id == 1).lower()}"
                    aria-controls="c{func_key}">
              <div class="nistform-acc-inner">
                <div class="nistform-acc-title-wrap">
                  <i class="bi bi-folder2-open me-2"></i>
                  <span class="nistform-acc-title">{esc(cap_name)}</span>
                </div>
                <span class="badge rounded-pill text-bg-light border">
                  {sum(len(v["items"]) for v in cats.values())} preguntas
                </span>
              </div>
            </button>
          </h2>

          <div id="c{func_key}"
               class="accordion-collapse collapse {'show' if acc_id == 1 else ''}">
            <div class="accordion-body nistform-acc-body">
              {''.join(inner)}
            </div>
          </div>
        </div>
        """)

    alerta_borrador = ""
    if draft:
        alerta_borrador = f"""
        <div class="alert alert-info rounded-4 border-0 shadow-sm">
          <i class="bi bi-info-circle-fill me-2"></i>
          Tienes un borrador cargado automáticamente.
          <strong>Progreso actual:</strong> {progreso_inicial}%.
        </div>
        """

    disabled_analizar = "" if progreso_inicial == 100 else "disabled"

    content = f"""
    <div class="nistform-shell">

      <div class="nistform-header-card">
        <div class="nistform-header-overlay">
          <div class="nistform-header-text">
            <h3 class="nistform-title m-0">Nivel de Madurez — Sistema de Gestión de Inteligencia Artificial</h3>
            <div class="nistform-subtitle">
              Registro de respuestas del instrumento de evaluación basado en
              ISO/IEC 42001 para el Sistema de Gestión de Inteligencia Artificial.
            </div>
          </div>
        </div>
      </div>

      <div class="nistform-header-actions">
        <a href="{url_for('madurez_ai.home')}"
           class="btn nistform-btn-main rounded-pill px-4 fw-bold">
          <i class="bi bi-arrow-left me-2"></i>Volver a Madurez IA
        </a>
      </div>

      <div class="nistform-card p-4">

        {alerta_borrador}

        <form id="nistIngresoForm"
              method="POST"
              action="{url_for('madurez_ai.guardar')}"
              novalidate
              autocomplete="off">

          <input type="hidden" name="draft_id" value="{draft['id'] if draft else ''}">

          <div class="nistform-section-title">
            Información de la revisión
          </div>

          <div class="mb-4">
            <label class="text-black form-label fw-semibold" for="nistConsecutivoRevision">
              Consecutivo de la Revisión <span class="text-danger">*</span>
            </label>

            <input type="text"
                   class="form-control"
                   name="consecutivo"
                   id="nistConsecutivoRevision"
                   value="{esc(consecutivo_val)}"
                   autocomplete="off"
                   required>

            <div id="nistConsecutivoRevisionError"
                 class="invalid-feedback d-none fw-bold mt-2">
              Debes ingresar el consecutivo de la Revisión.
            </div>
          </div>

          <div class="nistform-section-title">
            📊 Progreso del instrumento
          </div>

          <div class="mb-4">
            <div class="progress nistform-progress">
              <div id="nistProgressBar"
                   class="progress-bar progress-bar-striped progress-bar-animated"
                   role="progressbar"
                   style="width:{progreso_inicial}%"
                   aria-valuemin="0"
                   aria-valuemax="100"
                   aria-valuenow="{progreso_inicial}">
                {progreso_inicial}%
              </div>
            </div>

            <div class="text-center small text-muted mt-2">
              <span id="nistProgressText">{progreso_inicial}%</span> del instrumento completado
            </div>
          </div>

          <div class="nistform-section-title">
            Instrumento de evaluación
          </div>

          <div class="accordion nistform-accordion" id="accNist">
            {''.join(acc_html)}
          </div>

          <div class="d-flex justify-content-center gap-3 flex-wrap mt-4">
            <button id="btnGuardarNist"
                    class="btn btn-outline-primary btn-lg rounded-pill px-5 shadow fw-semibold nist-submit-btn"
                    type="submit"
                    name="accion"
                    value="guardar"
                    data-accion="guardar">
              <i class="bi bi-save2 me-2"></i>
              Guardar
            </button>

            <button id="btnAnalizarNist"
                    class="btn btn-primary btn-lg rounded-pill px-5 shadow fw-semibold nist-submit-btn"
                    type="submit"
                    name="accion"
                    value="analizar"
                    data-accion="analizar"
                    {disabled_analizar}>
              <i class="bi bi-bar-chart-line-fill me-2"></i>
              Analizar
            </button>
          </div>

        </form>

      </div>

    </div>

    <script>
    (function() {{

        let NIST_BLOQUEAR_LOADER = false;

        function nistOcultarLoaderGlobal() {{
            const ids = [
                "SGSI_PROGRESS_GLOBAL",
                "globalLoader",
                "loader",
                "progressOverlay",
                "sgsiProgressGlobal",
                "globalProgress",
                "overlayProgress",
                "loadingOverlay"
            ];

            ids.forEach(function(id) {{
                const el = document.getElementById(id);
                if (el) {{
                    el.style.display = "none";
                    el.style.visibility = "hidden";
                    el.style.opacity = "0";
                    el.style.pointerEvents = "none";
                    el.classList.add("d-none");
                    el.classList.remove("show");
                }}
            }});

            document.querySelectorAll(
                ".modal-backdrop, " +
                ".progress-overlay, " +
                ".loader-overlay, " +
                ".sgsi-loader, " +
                ".sgsi-progress, " +
                ".loading-overlay, " +
                ".global-loader, " +
                ".global-progress, " +
                ".progress-global"
            ).forEach(function(el) {{
                el.style.display = "none";
                el.style.visibility = "hidden";
                el.style.opacity = "0";
                el.style.pointerEvents = "none";
                el.classList.add("d-none");
                el.classList.remove("show");
            }});

            document.body.classList.remove("modal-open");
            document.body.style.overflow = "";
            document.body.style.paddingRight = "";
        }}

        function nistValidarConsecutivoRevision() {{
            const input = document.getElementById("nistConsecutivoRevision");
            const error = document.getElementById("nistConsecutivoRevisionError");

            const valor = input ? input.value.trim() : "";

            if (!valor) {{
                NIST_BLOQUEAR_LOADER = true;
                nistOcultarLoaderGlobal();

                if (input) {{
                    input.classList.add("is-invalid");
                    input.setAttribute("aria-invalid", "true");
                    input.focus();
                }}

                if (error) {{
                    error.classList.remove("d-none");
                    error.style.display = "block";
                }}

                return false;
            }}

            NIST_BLOQUEAR_LOADER = false;

            if (input) {{
                input.classList.remove("is-invalid");
                input.setAttribute("aria-invalid", "false");
            }}

            if (error) {{
                error.classList.add("d-none");
                error.style.display = "none";
            }}

            return true;
        }}

        function actualizarProgresoNist() {{
            const radios = document.querySelectorAll('input[type="radio"][name^="st_"]');
            const nombres = [...new Set(Array.from(radios).map(r => r.name))];
            const total = nombres.length;

            let respondidas = 0;

            nombres.forEach(function(nombre) {{
                const marcado = document.querySelector('input[name="' + nombre + '"]:checked');
                if (marcado) {{
                    respondidas++;
                }}
            }});

            const porcentaje = total > 0 ? Math.round((respondidas / total) * 100) : 0;

            const bar = document.getElementById("nistProgressBar");
            const text = document.getElementById("nistProgressText");
            const btnAnalizar = document.getElementById("btnAnalizarNist");

            if (bar) {{
                bar.style.width = porcentaje + "%";
                bar.innerText = porcentaje + "%";
                bar.setAttribute("aria-valuenow", porcentaje);
            }}

            if (text) {{
                text.innerText = porcentaje + "%";
            }}

            if (btnAnalizar) {{
                btnAnalizar.disabled = porcentaje < 100;
                btnAnalizar.classList.toggle("disabled", porcentaje < 100);
            }}
        }}

        const posiblesLoaders = [
            "showLoader",
            "mostrarLoader",
            "showGlobalLoader",
            "mostrarProgresoGlobal",
            "showProgress",
            "openLoader",
            "activarLoader",
            "SGSI_showLoader"
        ];

        posiblesLoaders.forEach(function(nombreFuncion) {{
            const original = window[nombreFuncion];

            if (typeof original === "function" && !original.__nistInterceptado) {{
                const wrapper = function() {{
                    if (NIST_BLOQUEAR_LOADER || !nistValidarConsecutivoRevision()) {{
                        nistOcultarLoaderGlobal();
                        return false;
                    }}

                    return original.apply(this, arguments);
                }};

                wrapper.__nistInterceptado = true;
                window[nombreFuncion] = wrapper;
            }}
        }});

        document.addEventListener("change", function(e) {{
            if (e.target.matches('input[type="radio"][name^="st_"]')) {{
                actualizarProgresoNist();
            }}
        }});

        document.addEventListener("click", function(e) {{
            const btn = e.target.closest(".nist-submit-btn");

            if (!btn) {{
                return;
            }}

            if (!nistValidarConsecutivoRevision()) {{
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();

                NIST_BLOQUEAR_LOADER = true;
                nistOcultarLoaderGlobal();

                return false;
            }}
        }}, true);

        window.addEventListener("DOMContentLoaded", function() {{
            const form = document.getElementById("nistIngresoForm");
            const input = document.getElementById("nistConsecutivoRevision");

            if (input) {{
                input.addEventListener("input", function() {{
                    nistValidarConsecutivoRevision();
                }});

                input.addEventListener("blur", function() {{
                    nistValidarConsecutivoRevision();
                }});
            }}

            if (form) {{
                form.addEventListener("submit", function(e) {{
                    if (!nistValidarConsecutivoRevision()) {{
                        e.preventDefault();
                        e.stopPropagation();
                        e.stopImmediatePropagation();

                        NIST_BLOQUEAR_LOADER = true;
                        nistOcultarLoaderGlobal();

                        return false;
                    }}
                }}, true);
            }}

            actualizarProgresoNist();
            nistOcultarLoaderGlobal();
        }});

        window.addEventListener("pageshow", function() {{
            nistOcultarLoaderGlobal();
        }});

    }})();
    </script>

    <style>
      .bg-purple{{ background-color:#6f42c1 !important; }}
      .badge.bg-purple{{ color:#ffffff !important; }}

      body{{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }}

      .nistform-shell{{
        width:96%;
        max-width:1600px;
        margin:26px auto 24px auto;
      }}

      .nistform-header-card{{
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

      .nistform-header-card::before{{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }}

      .nistform-header-overlay{{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        background:transparent !important;
        padding:0 !important;
        position:relative;
        z-index:1;
      }}

      .nistform-header-overlay::before{{
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
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }}

      .nistform-header-text{{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
      }}

      .nistform-header-text::before{{
        content:"SGSI · Evaluación ISO 42001";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }}

      .nistform-title{{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
      }}

      .nistform-subtitle{{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }}

      .nistform-header-actions{{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }}

      .nistform-header-actions .btn,
      .btn{{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }}

      .nistform-header-actions .btn{{
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }}

      .nistform-btn-main,
      .btn-outline-light{{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }}

      .nistform-btn-main:hover,
      .btn-outline-light:hover{{
        background:#edf5ff;
        color:#0b65d8 !important;
        border-color:#9ec5fe !important;
      }}

      .nistform-card,
      .card,
      .card-soft,
      .report-card{{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }}

      .nistform-card.p-4{{
        padding:1.5rem !important;
      }}

      .nistform-section-title{{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        padding-bottom:8px;
        border-bottom:2px solid rgba(59,130,246,.18);
        margin-bottom:16px;
      }}

      .nistform-progress{{
        height:22px;
        border-radius:999px;
        overflow:hidden;
        background:#e5edf7;
        box-shadow:inset 0 1px 3px rgba(15,23,42,.12);
      }}

      .progress-bar{{
        font-weight:900;
      }}

      .form-label{{
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
      }}

      .form-control,
      .form-select,
      .report-textarea{{
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
        box-shadow:none !important;
      }}

      textarea.form-control,
      .report-textarea{{
        min-height:90px;
      }}

      .form-control:focus,
      .form-select:focus,
      .report-textarea:focus{{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
        background:#ffffff;
      }}

      .form-control.is-invalid{{
        border-color:#dc3545 !important;
        background:#fff5f5 !important;
        box-shadow:0 0 0 .15rem rgba(220,53,69,.15) !important;
      }}

      .invalid-feedback{{
        color:#b42318;
        background:#fff1f1;
        border:1px solid #ffd4d4;
        border-radius:10px;
        padding:8px 12px;
      }}

      .nistform-accordion{{
        --bs-accordion-border-color:transparent;
        --bs-accordion-btn-focus-box-shadow:0 0 0 .2rem rgba(63,134,214,.12);
      }}

      .nistform-acc-item,
      .accordion-item{{
        border:1px solid #dbe6f4 !important;
        border-radius:0 20px 20px 0 !important;
        overflow:hidden;
        margin-bottom:12px;
        background:#ffffff !important;
        box-shadow:0 6px 14px rgba(15,23,42,.06);
      }}

      .nistform-acc-btn,
      .accordion-button{{
        background:#eef5ff !important;
        color:#0f172a !important;
        font-weight:900;
        padding:18px 22px !important;
        box-shadow:none !important;
        border-bottom:1px solid #dbe6f4;
      }}

      .nistform-acc-btn:not(.collapsed),
      .accordion-button:not(.collapsed){{
        background:#dbeafe !important;
        color:#0b4a8f !important;
        box-shadow:none !important;
      }}

      .nistform-acc-inner{{
        width:100%;
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:12px;
        padding-right:10px;
      }}

      .nistform-acc-title-wrap{{
        display:flex;
        align-items:center;
        gap:6px;
        min-width:0;
      }}

      .nistform-acc-title{{
        font-size:1rem;
        font-weight:950;
        color:#1e293b;
      }}

      .nistform-acc-body,
      .accordion-body{{
        background:rgba(255,255,255,.96) !important;
        padding:18px !important;
      }}

      .nistform-cat-block{{
        background:#f8fafc;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:16px;
        margin-bottom:16px;
      }}

      .nistform-cat-title{{
        display:flex;
        justify-content:space-between;
        align-items:flex-start;
        gap:12px;
        margin-bottom:14px;
        padding-bottom:10px;
        border-bottom:1px solid #dbe6f4;
      }}

      .nistform-cat-code{{
        font-size:.92rem;
        font-weight:950;
        color:#0b4a8f;
        line-height:1.15;
      }}

      .nistform-cat-name{{
        font-size:.78rem;
        color:#334155;
        margin-top:3px;
        line-height:1.25;
      }}

      .nistform-qcard{{
        background:#ffffff;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:8px 7px;
        box-shadow:0 4px 10px rgba(15,23,42,.05);
        height:100%;
        transition:.2s ease;
      }}

      .nistform-qcard:hover{{
        transform:translateY(-2px);
        box-shadow:0 8px 20px rgba(15,23,42,.10);
      }}

      .nistform-qhead{{
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:10px;
        margin-bottom:10px;
      }}

      .nistform-qtext{{
        font-size:.92rem;
        color:#0f172a;
        font-weight:700;
        line-height:1.45;
      }}

      .nistform-radio-row{{
        display:grid;
        grid-template-columns:repeat(4,1fr);
        gap:10px;
        margin-top:14px;
      }}

      .nistform-radio-card{{
        display:flex;
        align-items:center;
        justify-content:center;
        gap:6px;
        background:#f8fafc;
        border:1px solid #dbe4ee;
        border-radius:12px;
        min-height:46px;
        font-weight:900;
        color:#101827;
        cursor:pointer;
        transition:.2s;
        padding:8px 10px;
      }}

      .nistform-radio-card:hover{{
        background:#eef6ff;
        border-color:#93c5fd;
      }}

      .nistform-radio-card input[type="radio"]{{
        transform:scale(1.08);
      }}

      .badge{{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }}

      @media (max-width:1200px){{
        .nistform-radio-row{{
          grid-template-columns:repeat(2,1fr);
        }}
      }}

      @media (max-width:991.98px){{
        .nistform-shell{{
          width:98%;
          margin:8px auto 22px auto;
        }}

        .nistform-header-card{{
          min-height:88px;
        }}

        .nistform-title{{
          font-size:1.20rem;
        }}

        .nistform-subtitle{{
          font-size:.68rem;
        }}
      }}

      @media (max-width:768px){{
        .nistform-header-overlay{{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }}

        .nistform-header-overlay::before{{
          margin:0;
        }}

        .nistform-header-text::before{{
          margin-left:auto;
          margin-right:auto;
        }}

        .nistform-title,
        .nistform-subtitle{{
          text-align:center;
        }}

        .nistform-header-actions .btn{{
          width:100%;
        }}

        .nistform-acc-inner,
        .nistform-cat-title{{
          flex-direction:column;
          align-items:flex-start;
        }}

        .nistform-radio-row{{
          grid-template-columns:1fr;
        }}
      }}
    </style>
    """

    return render_template_string(BASE, title="Ingreso Madurez IA", content=content)


