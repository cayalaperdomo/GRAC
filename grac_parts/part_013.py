@app.route("/chatgpt_view", methods=["GET"])
@login_required
def chatgpt_view():
    html = """
    <div class="chatsgsi-shell">

      <div class="chatsgsi-header-card">
        <div class="chatsgsi-header-overlay">
          <div class="chatsgsi-header-text">
            <h3 class="chatsgsi-title m-0">Asistente SGSI (ChatGPT)</h3>
            <div class="chatsgsi-subtitle">
              Consulta dudas, orientación y apoyo sobre tu SGSI directamente desde el asistente integrado.
            </div>
          </div>
        </div>
      </div>

      <div class="chatsgsi-card p-0">
        <div class="chatsgsi-card-header">
          Chat con el asistente
        </div>

        <div class="chatsgsi-card-body">

          <div id="chat-box" class="chatsgsi-box"></div>

          <div class="d-flex gap-2 mt-3">
            <input type="text"
                   id="user-input"
                   class="form-control"
                   placeholder="Escribe tu pregunta sobre el SGSI..."
                   autocomplete="off">

            <button id="chat-send-btn"
                    class="chat-send-clean"
                    type="button"
                    onclick="consultarAIChatGPT()">
              Enviar
            </button>
          </div>

        </div>
      </div>
    </div>

    <script>
      window.SGSI_DISABLE_GLOBAL_LOADER = true;
      window.SGSI_PROGRESS_GLOBAL_DISABLED = true;

      function ocultarLoaderChatGPT() {
        const ids = [
          'SGSI_PROGRESS_GLOBAL',
          'sgsi-progress-global',
          'global-loader',
          'loader',
          'loadingOverlay',
          'progressOverlay',
          'progressGlobal',
          'SGSI_PROGRESS_OVERLAY'
        ];

        ids.forEach(function(id) {
          const el = document.getElementById(id);
          if (el) {
            el.style.display = 'none';
            el.style.visibility = 'hidden';
            el.style.opacity = '0';
            el.style.pointerEvents = 'none';
          }
        });
      }

      function appendMessage(text, who) {
        const chatBox = document.getElementById('chat-box');

        const wrapper = document.createElement('div');
        wrapper.className = 'mb-2 d-flex ' + (who === 'user' ? 'justify-content-end' : 'justify-content-start');

        const bubble = document.createElement('div');
        bubble.className = 'px-3 py-2 rounded-3 chatsgsi-bubble ' + (who === 'user' ? 'chatsgsi-user' : 'chatsgsi-bot');
        bubble.style.maxWidth = '75%';
        bubble.innerText = text;

        wrapper.appendChild(bubble);
        chatBox.appendChild(wrapper);
        chatBox.scrollTop = chatBox.scrollHeight;
      }

      async function consultarAIChatGPT() {
        ocultarLoaderChatGPT();

        const userInput = document.getElementById('user-input');
        const sendBtn = document.getElementById('chat-send-btn');
        const chatBox = document.getElementById('chat-box');

        const text = (userInput.value || '').trim();
        if (!text) return false;

        appendMessage(text, 'user');

        userInput.value = '';
        userInput.focus();

        sendBtn.disabled = true;
        sendBtn.innerText = 'Consultando IA...';

        const thinkingId = 'thinking-' + Date.now();

        const thinkingDiv = document.createElement('div');
        thinkingDiv.id = thinkingId;
        thinkingDiv.className = 'mb-2 d-flex justify-content-start';
        thinkingDiv.innerHTML = '<div class="px-3 py-2 rounded-3 chatsgsi-bubble chatsgsi-thinking text-muted small">Pensando...</div>';

        chatBox.appendChild(thinkingDiv);
        chatBox.scrollTop = chatBox.scrollHeight;

        const controller = new AbortController();

        // 300 segundos para evitar corte prematuro del chat
        const timeoutId = setTimeout(function() {
          controller.abort();
        }, 300000);

        try {
          const resp = await fetch("{{ url_for('chatgpt_api') }}", {
            method: "POST",
            credentials: "same-origin",
            signal: controller.signal,
            headers: {
              "Content-Type": "application/json",
              "X-No-Loader": "1"
            },
            body: JSON.stringify({
              message: text
            })
          });

          clearTimeout(timeoutId);

          const raw = await resp.text();

          let data = {};
          try {
            data = JSON.parse(raw);
          } catch (e) {
            data = {
              error: "Respuesta no válida del servidor: " + raw.substring(0, 300)
            };
          }

          const t = document.getElementById(thinkingId);
          if (t) t.remove();

          if (!resp.ok) {
            appendMessage("⚠ Error HTTP " + resp.status + ": " + (data.error || raw), 'bot');
          } else if (data.reply) {
            appendMessage(data.reply, 'bot');
          } else if (data.error) {
            appendMessage("⚠ " + data.error, 'bot');
          } else {
            appendMessage("No se recibió una respuesta válida del asistente.", 'bot');
          }

        } catch (err) {
          clearTimeout(timeoutId);

          const t = document.getElementById(thinkingId);
          if (t) t.remove();

          if (err.name === 'AbortError') {
            appendMessage("⚠ La consulta tardó demasiado. Valida que OpenRouter/Ollama esté activo y que el modelo responda correctamente.", 'bot');
          } else {
            appendMessage("⚠ Error de conexión consultando la IA: " + err.message, 'bot');
          }

          console.error(err);

        } finally {
          sendBtn.disabled = false;
          sendBtn.innerText = 'Enviar';
          userInput.focus();
          ocultarLoaderChatGPT();
        }

        return false;
      }

      document.addEventListener('DOMContentLoaded', function() {
        ocultarLoaderChatGPT();

        const userInput = document.getElementById('user-input');

        userInput.addEventListener('keydown', function(e) {
          if (e.key === 'Enter') {
            e.preventDefault();
            consultarAIChatGPT();
          }
        });

        userInput.focus();
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

      #SGSI_PROGRESS_GLOBAL,
      #sgsi-progress-global,
      #global-loader,
      #loader,
      #loadingOverlay,
      #progressOverlay,
      #progressGlobal,
      #SGSI_PROGRESS_OVERLAY{
        display:none !important;
        visibility:hidden !important;
        opacity:0 !important;
        pointer-events:none !important;
      }

      .chatsgsi-shell{
        width:96%;
        max-width:1200px;
        margin:26px auto 24px auto;
        overflow:hidden;
      }

      .chatsgsi-header-card{
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

      .chatsgsi-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }

      .chatsgsi-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
      }

      .chatsgsi-header-overlay::before{
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
      }

      .chatsgsi-header-text::before{
        content:"SGSI · Asistente Inteligente";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .chatsgsi-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 4px 14px rgba(0,0,0,.45);
      }

      .chatsgsi-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        line-height:1.25;
        margin-top:3px;
      }

      .chatsgsi-card{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
        overflow:hidden;
      }

      .chatsgsi-card-header{
        background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
        color:#ffffff;
        font-weight:950;
        padding:14px 18px;
      }

      .chatsgsi-card-body{
        padding:18px;
        overflow:hidden;
      }

      .chatsgsi-box{
        height:500px;
        border:1px solid #e2ebf5;
        border-radius:14px;
        padding:12px;
        overflow:auto;
        background:#f8fbff;
      }

      .chatsgsi-bubble{
        box-shadow:0 4px 12px rgba(15,23,42,.08);
        border-radius:14px;
        padding:10px 14px;
        margin-bottom:8px;
        max-width:85%;
        overflow-wrap:break-word;
        word-break:break-word;
        line-height:1.45;
        font-size:.90rem;
      }

      .chatsgsi-user{
        background:linear-gradient(135deg,#0b4a8f,#1d5fae);
        color:#ffffff;
        margin-left:auto;
      }

      .chatsgsi-bot,
      .chatsgsi-thinking{
        background:#ffffff;
        border:1px solid #e2ebf5;
        color:#334155;
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

      .chat-send-clean{
        border:none;
        border-radius:999px;
        min-width:110px;
        padding:0 22px;
        background:#198754;
        color:#ffffff;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }

      .chat-send-clean:disabled{
        opacity:.75;
        cursor:not-allowed;
      }

      @media (max-width:992px){
        .chatsgsi-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .chatsgsi-box{
          height:420px;
        }
      }

      @media (max-width:768px){
        .chatsgsi-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .chatsgsi-header-overlay::before{
          margin:0;
        }

        .chatsgsi-title,
        .chatsgsi-subtitle{
          text-align:center;
        }

        .chatsgsi-bubble{
          max-width:100%;
        }
      }
    </style>
    """

    inner = render_template_string(html)
    return render_template_string(BASE, content=Markup(inner))


# ==========================================================================================================================================
#                                                               Fin del Módulo ChatBox
# ==========================================================================================================================================

# ==========================================================================================================================================
#                                                               Módulo Nivel de Madurez ISO 27001:2022
# ==========================================================================================================================================

def calcular_progreso_formulario(preguntas, form_data=None, respuestas_db=None):
    """
    Retorna: (respondidas, total, porcentaje)
    - form_data: request.form
    - respuestas_db: dict {pregunta_id: {"opcion": "...", "comentario": "..."}}
    """
    total = sum(1 for p in preguntas if p.tipo == "q")
    respondidas = 0

    for p in preguntas:
        if p.tipo != "q":
            continue

        opcion = ""
        if form_data is not None:
            opcion = (form_data.get(f"r_{p.id}") or "").strip()
        elif respuestas_db is not None:
            opcion = (respuestas_db.get(p.id, {}).get("opcion") or "").strip()

        if opcion:
            respondidas += 1

    porcentaje = int(round((respondidas / total) * 100)) if total > 0 else 0
    return respondidas, total, porcentaje


def obtener_borrador_madurez(user_id):
    """
    Busca el borrador activo más reciente del usuario.
    """
    if not user_id:
        return None

    return (
        MadurezRun.query
        .filter(
            MadurezRun.user_id == user_id,
            MadurezRun.estado == "BORRADOR"
        )
        .order_by(MadurezRun.updated_at.desc().nullslast(), MadurezRun.id.desc())
        .first()
    )


def cargar_respuestas_run(run_id):
    """
    Retorna dict:
    {
      pregunta_id: {"opcion": "...", "comentario": "..."}
    }
    """
    out = {}
    if not run_id:
        return out

    rows = (
        MadurezRespuesta.query
        .filter_by(run_id=run_id)
        .all()
    )

    for r in rows:
        out[r.pregunta_id] = {
            "opcion": (r.opcion or "").strip(),
            "comentario": (r.comentario or "").strip()
        }

    return out

def normalize_control_code(v) -> str:
    """
    Convierte el código de control de ANEXO A a texto estable:
    - Si Excel lo convirtió a fecha (05/06/2026) => "5.6"
    - Si viene numérico 5.1 => "5.1"
    - Si viene string => strip()
    """
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""

    # pandas Timestamp / datetime
    if isinstance(v, (pd.Timestamp, datetime, date)):
        # Excel te lo convirtió a fecha "05/06/2026" => day=5 month=6 => "5.6"
        return f"{int(v.day)}.{int(v.month)}"

    # numérico (float/int)
    if isinstance(v, (int, float, np.number)):
        s = str(v)
        return s.rstrip("0").rstrip(".")  # "5.0" -> "5", "5.10" -> "5.1"

    # texto
    return str(v).strip()

# ==========================
# IA HARDENING (NO CONDICIONAL)
# ==========================
_CONDITIONAL_PATTERNS = [
    r"\bpodr[ií]a\b",
    r"\bdeber[ií]a\b",
    r"\bser[ií]a\b",
    r"\bquiz[aá]s\b",
    r"\btal\s+vez\b",
    r"\bposiblemente\b",
    r"\bpuede\s+que\b",
    r"\bes\s+posible\s+que\b",
    r"\bprobablemente\b",
    r"\bse\s+recomendar[ií]a\b",
    r"\bse\s+podr[ií]a\b",
]

def harden_no_conditionals(text: str) -> str:
    """
    Normaliza salida IA para evitar lenguaje condicional.
    Reemplaza por redacción verificable (imperativo/indicativo).
    """
    s = (text or "").strip()

    # Reemplazos directos (pragmáticos)
    replacements = {
        "podría": "puede",
        "podria": "puede",
        "debería": "debe",
        "deberia": "debe",
        "sería": "es",
        "seria": "es",
        "quizás": "",
        "quizas": "",
        "tal vez": "",
        "posiblemente": "",
        "puede que": "se requiere que",
        "es posible que": "se requiere que",
        "probablemente": "",
        "se recomendaría": "se recomienda",
        "se recomendaria": "se recomienda",
        "se podría": "se debe",
        "se podria": "se debe",
    }

    # Aplica reemplazos case-insensitive básicos
    for k, v in replacements.items():
        s = re.sub(rf"\b{k}\b", v, s, flags=re.IGNORECASE)

    # Limpieza de dobles espacios
    s = re.sub(r"[ \t]{2,}", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)

    # Si aún quedan patrones condicionales, los corta por seguridad
    for pat in _CONDITIONAL_PATTERNS:
        s = re.sub(pat, "", s, flags=re.IGNORECASE)

    s = re.sub(r"[ \t]{2,}", " ", s).strip()
    return s

def _b64_to_rl_image(b64: str, width: float = 6.8*inch):
    if not b64:
        return None
    try:
        raw = base64.b64decode(b64)
        bio = io.BytesIO(raw)
        img = Image(bio)
        # conserva ratio
        iw, ih = img.imageWidth, img.imageHeight
        if iw and ih:
            ratio = ih / float(iw)
            img.drawWidth = width
            img.drawHeight = width * ratio
        else:
            img.drawWidth = width
        return img
    except Exception:
        return None

def _p(text: str, styles, style_name="BodyText"):
    t = (text or "").strip()
    t = t.replace("\n", "<br/>")
    return Paragraph(t, styles[style_name])

def _badge_color_for_score(pct: float):
    try:
        p = float(pct or 0)
    except Exception:
        p = 0.0
    if p >= 80: return colors.HexColor("#198754")  # verde
    if p >= 60: return colors.HexColor("#0d6efd")  # azul
    if p >= 40: return colors.HexColor("#ffc107")  # amarillo
    return colors.HexColor("#dc3545")              # rojo

def _badge_color_for_gap(level: str):
    lvl = (level or "").strip().lower()
    if lvl == "bajo": return colors.HexColor("#198754")
    if lvl == "medio": return colors.HexColor("#ffc107")
    if lvl == "alto": return colors.HexColor("#dc3545")
    if lvl in ("critico", "crítico"): return colors.HexColor("#212529")
    return colors.HexColor("#6c757d")


def gap_from_maturity_pct(pct_madurez: float) -> dict:
    """
    Brecha = 100 - madurez.
    Retorna: {gap_pct, nivel_brecha, interpretacion}
    """
    p = _to_float(pct_madurez, 0.0)
    # clamp
    if p < 0: p = 0.0
    if p > 100: p = 100.0

    gap_pct = round(100.0 - p, 2)
    gl = get_gap_level_for_pct(gap_pct)
    return {
        "gap_pct": gap_pct,
        "nivel_brecha": gl.get("nivel_brecha", ""),
        "interpretacion": gl.get("interpretacion", ""),
    }

def ensure_control_ai_fields(data: dict, kpi: dict = None) -> dict:
    """
    Garantiza que estado_actual, estado_requerido y plan_accion_sugerido
    existan y tengan contenido suficiente, sin crear campos adicionales.
    """
    if not isinstance(data, dict):
        data = {}

    ea = harden_no_conditionals(to_text(data.get("estado_actual")).strip())
    er = harden_no_conditionals(to_text(data.get("estado_requerido")).strip())
    pa = harden_no_conditionals(to_text(data.get("plan_accion_sugerido")).strip())

    if not ea:
        ea = (
            "El control presenta implementación parcial con evidencia disponible en varios requisitos evaluados. "
            "Sin embargo, aún existen brechas en consistencia operativa, seguimiento periódico y trazabilidad "
            "de los aspectos que no están completamente cerrados."
        )

    if not er:
        er = (
            "El control debe operar con un proceso definido, evidencia verificable, revisión periódica, "
            "seguimiento de brechas y sostenibilidad en el tiempo, asegurando que todos los requisitos "
            "aplicables se mantengan cubiertos de forma consistente."
        )

    if not pa:
        pa = (
            "1. Formalizar y documentar el proceso asociado al control con responsables y criterios de revisión.\n"
            "2. Cerrar las brechas identificadas en estados PARCIAL, NO y SIN_MARCAR mediante evidencia verificable.\n"
            "3. Establecer seguimiento periódico con revisión de vigencia, resultados y oportunidades de mejora."
        )

    return {
        "estado_actual": ea,
        "estado_requerido": er,
        "plan_accion_sugerido": pa
    }

def rl_pct_chip_cell(pct: float, label: str, style, chip_w=0.10*inch):
    """
    Celda compuesta: [chip color | texto % (madurez)].
    - chip_w controla qué tan pequeño queda el color al lado del porcentaje.
    """
    chip_color = rl_badge_bg_for_pct(pct)
    txt_color = rl_badge_fg_for_pct(pct)

    inner = Table(
        [["", Paragraph(xml_escape(label), style)]],
        colWidths=[chip_w, None]
    )
    inner.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,0), chip_color),
        ("TEXTCOLOR",  (1,0), (1,0), txt_color),

        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING",(0,0), (-1,-1), 0),
        ("TOPPADDING",  (0,0), (-1,-1), 0),
        ("BOTTOMPADDING",(0,0),(-1,-1), 0),

        # opcional: un poquito de aire a la izquierda del texto
        ("LEFTPADDING", (1,0), (1,0), 4),
    ]))
    return inner

def pdf_questions_table(items_c: list):
    # Encabezados iguales a UI
    data = [[
        "Capítulo", "Ref", "Estado", "Pregunta/Requisito",
        "Comentarios", "Procesos", "%Brecha", "Nivel brecha", "Interpretación"
    ]]

    # Limita para evitar PDFs gigantescos (puedes subirlo si quieres)
    items_sorted = sorted(items_c or [], key=lambda x: int(x.get("row", 0) or 0))
    for it in items_sorted[:500]:
        st = (it.get("status") or "").strip()
        if st == "SIN_MARCAR":
            st_vis = ""
        else:
            st_vis = st

        bp = it.get("brecha_pct", None)
        bp_txt = "" if bp is None else f"{float(bp):.0f}%"

        data.append([
            str(it.get("sheet","") or ""),
            str(it.get("ref","") or "—"),
            st_vis,
            str(it.get("requisito","") or ""),
            str(it.get("comment","") or ""),
            str(it.get("procesos","") or ""),
            bp_txt,
            str(it.get("brecha_nivel","") or ""),
            str(it.get("brecha_interp","") or ""),
        ])

    t = Table(data, colWidths=[
        1.0*inch, 0.7*inch, 0.75*inch, 3.0*inch,
        1.6*inch, 1.2*inch, 0.7*inch, 0.9*inch, 2.0*inch
    ])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0b1b2b")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,0), 8),
        ("FONTSIZE", (0,1), (-1,-1), 7),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("GRID", (0,0), (-1,-1), 0.25, colors.lightgrey),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.whitesmoke, colors.HexColor("#f7f7f7")]),
    ]))
    return t


def control_ai_is_complete(d: dict) -> bool:
    """
    True si existen las 3 llaves y tienen texto.
    """
    if not isinstance(d, dict):
        return False
    return bool((d.get("estado_actual") or "").strip()) and bool((d.get("estado_requerido") or "").strip()) and bool((d.get("plan_accion_sugerido") or "").strip())


def summarize_plan_action(text: str) -> str:
    """
    Plan de acción sugerido (MUY resumido):
    - 1 sola frase (1 línea)
    - Sin responsable
    - Sin bullets
    - Sin tiempos 0–30 / 31–60 / 61–90
    - Sin detalle por ítem
    """
    s = (text or "").strip()
    if not s:
        return ""

    s = s.replace("\r\n", "\n").replace("\r", "\n")

    # Quitar referencias a fases/tiempos
    s = re.sub(r"\b0[\-–]\s*30\b", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\b31[\-–]\s*60\b", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\b61[\-–]\s*90\b", "", s, flags=re.IGNORECASE)

    # Quitar líneas con "responsable" explícito (por si la IA lo trae)
    s = re.sub(r"(?i)\bresponsable\s*:\s*.*", "", s).strip()

    # Extraer posibles líneas (si venía con bullets) y quedarnos con ideas
    lines = []
    for ln in s.split("\n"):
        ln = ln.strip().lstrip("•-–\t ").strip()
        if ln:
            lines.append(ln)

    # Si es un párrafo, partir por frases
    if len(lines) <= 1:
        chunks = re.split(r"[.;]\s+", s)
        lines = [c.strip().lstrip("•-–\t ").strip() for c in chunks if c.strip()]

    # Deduplicar
    uniq = []
    seen = set()
    for ln in lines:
        key = re.sub(r"\s+", " ", ln.lower()).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        uniq.append(ln)
        if len(uniq) >= 8:
            break

    # Elegir 2–3 acciones genéricas (sin detalle por ítem)
    verbs = ("definir", "documentar", "establecer", "implementar", "actualizar",
             "formalizar", "evidenciar", "medir", "revisar", "aprobar", "registrar", "cerrar")
    prioritized = sorted(
        uniq,
        key=lambda t: (0 if any(t.lower().startswith(v) for v in verbs) else 1, len(t))
    )

    # Construir 1 sola frase “macro”
    # Si la IA venía muy específica, igual lo compactamos.
    macro_actions = []

    for ln in prioritized:
        t = re.sub(r"\s{2,}", " ", (ln or "").strip())

        # Elimina rastros de "Responsable ..." en medio de la frase
        t = re.sub(r"(?i)\bresponsable\b.*", "", t).strip()

        # Evitar frases ultra-específicas por ítem: si menciona "ítem", "subítem", "pregunta", las ignoramos
        if re.search(r"(?i)\bítem\b|\bsub[ií]tem\b|\bpregunta\b", t):
            continue

        if t:
            macro_actions.append(t)
        if len(macro_actions) >= 3:
            break

    # Si no hay material usable, usar una frase estándar
    if not macro_actions:
        return (
            "Definir y documentar el proceso del control, cerrar las brechas (NO/PARCIAL/SIN_MARCAR) con evidencia verificable y "
            "establecer revisión periódica con medición y seguimiento."
        )

    # Unir en una sola frase, sin bullets
    joined = "; ".join(macro_actions)

    # Asegurar cierre con punto
    joined = joined.rstrip(" .;")
    joined = joined + "."

    # Recortar si es demasiado largo
    if len(joined) > 220:
        joined = joined[:220].rstrip() + "…"

    return joined

def build_control_support_text(items: list, max_lines: int = 40) -> str:
    """
    Construye el bloque 'soporte' para IA con preguntas/requisitos del control.
    Prioriza brechas (NO/PARCIAL/SIN_MARCAR) y luego SI.
    Incluye comentario/procesos si existen. Excluye NA.
    """
    if not items:
        return "N/A"

    # Solo aplicables y no NA
    applicable = [
        x for x in (items or [])
        if x.get("applicable", True) and (x.get("status") != "NA")
    ]

    def _prio(st: str) -> int:
        st = (st or "").strip()
        if st in ("NO", "SIN_MARCAR"):
            return 0
        if st == "PARCIAL":
            return 1
        if st == "SI":
            return 2
        return 3

    # Orden: primero brechas, luego SI; dentro por fila
    applicable_sorted = sorted(
        applicable,
        key=lambda x: (_prio(x.get("status")), int(x.get("row", 0) or 0))
    )

    lines = []
    for it in applicable_sorted[:max_lines]:
        st = (it.get("status") or "").strip()
        ref = (it.get("ref") or "—").strip()
        req = (it.get("requisito") or "").strip()
        com = (it.get("comment") or "").strip()
        prc = (it.get("procesos") or "").strip()

        extra = []
        if com:
            extra.append(f"comentarios: {com}")
        if prc:
            extra.append(f"procesos: {prc}")

        extra_txt = (" | " + " ; ".join(extra)) if extra else ""
        if req:
            lines.append(f"- [{st}] ({ref}) {req}{extra_txt}")

    return "\n".join(lines) if lines else "N/A"


def is_control_optimo(kpi: dict) -> bool:
    """
    True si el control se considera Óptimo por porcentaje o por etiqueta de madurez.
    - pct >= 80
    - madurez == 'optimo' (ignorando tildes y mayúsculas)
    """
    try:
        pctv = float((kpi or {}).get("pct", 0) or 0)
    except Exception:
        pctv = 0.0

    mad = ((kpi or {}).get("madurez") or "").strip().lower()
    mad = unicodedata.normalize("NFD", mad)
    mad = "".join(ch for ch in mad if unicodedata.category(ch) != "Mn")  # quita tildes

    return (pctv >= 80) or (mad == "optimo")


def build_ai_methodology_iso27001(company_name: str) -> str:
    """
    Texto auditoría-ready. No usa condicional. Orientado a ISO 27001:2022.
    """
    txt = f"""
Criterio metodológico de análisis (ISO/IEC 27001:2022)

Este informe presenta los resultados de madurez y brechas del Sistema de Gestión de la Seguridad de la Información (SGSI), calculados a partir de las respuestas del instrumento aplicado y los parámetros de evaluación definidos por la organización.

Los resultados incluyen análisis por capítulo y por control, permitiendo identificar el nivel de cumplimiento y las brechas existentes para apoyar la toma de decisiones y la mejora continua del SGSI.

Consecutivo: {company_name}
"""
    return harden_no_conditionals(txt.strip())

def textarea_escape(s: str) -> str:
    s = s or ""
    s = s.replace("</textarea>", "</tex&#116;area>")
    return xml_escape(s)


def format_executive_summary(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        lines = []
        for x in value:
            t = to_text(x).strip()
            if t:
                if t.startswith(("•", "-", "–")):
                    lines.append(t)
                else:
                    lines.append("• " + t)
        return "\n".join(lines).strip()
    if isinstance(value, dict):
        lines = []
        for k, v in value.items():
            vt = to_text(v).strip()
            if vt:
                lines.append(f"• {k}: {vt}")
        return "\n".join(lines).strip()
    return to_text(value).strip()

def ratio_text(done, total) -> str:
    try:
        d = int(done or 0)
        t = int(total or 0)
        return f"{d}/{t}"
    except Exception:
        return "0/0"

def format_ai_report(report_value) -> str:
    if report_value is None:
        return ""
    if isinstance(report_value, str):
        return report_value.strip()

    if isinstance(report_value, dict):
        lines = []
        ordered_keys = [k for k in CHAPTER_SHEETS if k in report_value] + [
            k for k in report_value.keys() if k not in CHAPTER_SHEETS
        ]

        for cap in ordered_keys:
            sec = report_value.get(cap)
            if sec is None:
                continue
            lines.append(f"{cap}")
            lines.append("-" * len(cap))

            if isinstance(sec, dict):
                key_map = [
                    ("análisis", "Análisis"),
                    ("analisis", "Análisis"),
                    ("riesgos", "Riesgos"),
                    ("quick_wins", "Quick wins"),
                    ("quickwins", "Quick wins"),
                    ("recomendaciones", "Recomendaciones"),
                    ("acciones", "Acciones"),
                ]
                printed = set()
                for k, label in key_map:
                    if k in sec and k not in printed:
                        txt = to_text(sec.get(k)).strip()
                        if txt:
                            lines.append(f"{label}: {txt}")
                        printed.add(k)

                for k, v in sec.items():
                    if k in printed:
                        continue
                    txt = to_text(v).strip()
                    if txt:
                        lines.append(f"{k.capitalize()}: {txt}")
            else:
                txt = to_text(sec).strip()
                if txt:
                    lines.append(txt)

            lines.append("")
        return "\n".join(lines).strip()

    if isinstance(report_value, list):
        return "\n".join(to_text(x).strip() for x in report_value if to_text(x).strip()).strip()

    return to_text(report_value).strip()


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _to_float(x, default=None):
    try:
        if x is None:
            return default
        return float(str(x).strip())
    except Exception:
        return default


def _ranges_overlap(a_min, a_max, b_min, b_max):
    return not (a_max < b_min or b_max < a_min)

def _is_optimo(kpi_dict: dict) -> bool:
                pctv = float(kpi_dict.get("pct", 0) or 0)
                madv = (kpi_dict.get("madurez") or "").strip().lower()
                madv = unicodedata.normalize("NFD", madv)
                madv = "".join(ch for ch in madv if unicodedata.category(ch) != "Mn")
                return (pctv >= 80) or (madv == "optimo")

def get_maturity_label_for_pct(pct: float) -> str:
    pct = _to_float(pct, 0.0)

    rows = (ComplianceMaturityMap.query
            .join(MaturityLevel, ComplianceMaturityMap.maturity_id == MaturityLevel.id)
            .order_by(ComplianceMaturityMap.pct_min.asc(), ComplianceMaturityMap.pct_max.asc())
            .all())

    for r in rows:
        if r.pct_min <= pct <= r.pct_max:
            return r.maturity.madurez if r.maturity else ""
    return ""


def get_gap_level_for_pct(pct_brecha: float) -> dict:
    pct_brecha = _to_float(pct_brecha, 0.0)
    rows = GapLevelConfig.query.order_by(GapLevelConfig.pct_min.asc(), GapLevelConfig.pct_max.asc()).all()
    for r in rows:
        if r.pct_min <= pct_brecha <= r.pct_max:
            return {"nivel_brecha": r.nivel_brecha, "interpretacion": r.interpretacion or ""}
    return {"nivel_brecha": "", "interpretacion": ""}


def norm_txt(x) -> str:
    if x is None:
        return ""
    if isinstance(x, float) and math.isnan(x):
        return ""
    s = str(x).strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower().strip()


def is_marked_x(val) -> bool:
    s = norm_txt(val)
    if s in ("x", "✓", "si", "sí", "1", "true", "ok"):
        return True
    if isinstance(val, (int, float)) and val == 1:
        return True
    return False


def is_excluded_row(desc: str) -> bool:
    s = norm_txt(desc)
    if "diagnostico" in s:
        return True
    if s.startswith("promedio"):
        return True
    return False


def is_note_row(desc: str) -> bool:
    s = norm_txt(desc)
    if not s:
        return False
    if s.startswith("nota") or s.startswith("notas") or "nota:" in s:
        return True
    return False


def is_grey_header_title(requisito: str) -> bool:
    s = norm_txt(requisito)
    if not s:
        return False
    targets = [
        "no aplica", "n/a", "na",
        "si", "sí",
        "parcial", "parcialmente",
        "no",
        "coment", "observ", "proces", "asociad",
        "estado", "cumplimiento"
    ]
    hits = sum(1 for t in targets if t in s)
    return hits >= 2


def is_title_row_by_marks(ref_txt: str, requisito: str, v_na, v_si, v_pa, v_no, comment: str, procesos: str) -> bool:
    if not requisito:
        return False
    if is_marked_x(v_na) or is_marked_x(v_si) or is_marked_x(v_pa) or is_marked_x(v_no):
        return False
    if (comment or "").strip() or (procesos or "").strip():
        return False
    if is_grey_header_title(requisito):
        return True
    s = norm_txt(requisito)
    header_words = ("criterio", "requisito", "control", "comentarios", "procesos asociados", "evidencia")
    if any(w in s for w in header_words) and len(s) <= 120:
        return True
    return False


def extract_subkey(sheet_name: str, ref_raw: str) -> str:
    ref = (ref_raw or "").strip()
    if not ref:
        return ""
    if "anexo" in norm_txt(sheet_name) or ref.upper().startswith("A"):
        m = re.match(r"^(A\.\d+)", ref.strip(), re.IGNORECASE)
        return m.group(1).upper() if m else ""
    m = re.match(r"^(\d+\.\d+)", ref.strip())
    return m.group(1) if m else ""


def detect_header_item_subitem(df: "pd.DataFrame"):
    max_scan = min(50, df.shape[0])

    def is_item(s): return s == "item"
    def is_subitem(s): return s == "subitem"
    def is_preg(s): return ("pregunta" in s) or ("requisito" in s)
    def is_na(s): return ("no aplica" in s) or ("n/a" in s) or (s in ("na", "n a"))
    def is_si(s): return s in ("si", "sí")
    def is_parcial(s): return "parcial" in s
    def is_no(s): return s == "no"
    def is_com(s): return ("coment" in s) or ("observ" in s)

    best = None

    for r in range(max_scan):
        col_map = {}
        for c in range(df.shape[1]):
            s = norm_txt(df.iat[r, c])
            if not s:
                continue

            if "item_col" not in col_map and is_item(s):
                col_map["item_col"] = c
            elif "subitem_col" not in col_map and is_subitem(s):
                col_map["subitem_col"] = c
            elif "preg_col" not in col_map and is_preg(s):
                col_map["preg_col"] = c
            elif "na_col" not in col_map and is_na(s):
                col_map["na_col"] = c
            elif "si_col" not in col_map and is_si(s):
                col_map["si_col"] = c
            elif "parcial_col" not in col_map and is_parcial(s):
                col_map["parcial_col"] = c
            elif "no_col" not in col_map and is_no(s):
                col_map["no_col"] = c
            elif "comments_col" not in col_map and is_com(s):
                col_map["comments_col"] = c

        score = 0
        for k in ("item_col", "preg_col"):
            if k in col_map:
                score += 5
        for k in ("na_col", "si_col", "parcial_col", "no_col"):
            if k in col_map:
                score += 2
        if "comments_col" in col_map:
            score += 1

        if best is None or score > best["score"]:
            best = {"score": score, "row": r, "col_map": col_map}

        if ("item_col" in col_map and "preg_col" in col_map and
            "si_col" in col_map and "no_col" in col_map):
            return r, col_map

    if best and best["score"] >= 10 and "item_col" in best["col_map"] and "preg_col" in best["col_map"]:
        return best["row"], best["col_map"]

    return None, None


def _clean_cell_text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and math.isnan(v):
        return ""
    s = str(v).strip()
    if s.lower() == "nan":
        return ""
    return s


def eval_status_from_row_item_subitem(df: "pd.DataFrame", r: int, col_map: dict):
    item_col = col_map.get("item_col")
    subitem_col = col_map.get("subitem_col")
    preg_col = col_map.get("preg_col")
    na_col = col_map.get("na_col")
    si_col = col_map.get("si_col")
    parcial_col = col_map.get("parcial_col")
    no_col = col_map.get("no_col")
    comments_col = col_map.get("comments_col")

    item_val = df.iat[r, item_col] if item_col is not None and item_col < df.shape[1] else None
    sub_val  = df.iat[r, subitem_col] if subitem_col is not None and subitem_col < df.shape[1] else None
    preg_val = df.iat[r, preg_col] if preg_col is not None and preg_col < df.shape[1] else None

    item_txt = _clean_cell_text(item_val)
    sub_txt  = _clean_cell_text(sub_val)
    preg_txt = _clean_cell_text(preg_val)

    if not item_txt and not preg_txt and not sub_txt:
        return None, None, None, None, None, None, None

    v_na = df.iat[r, na_col] if na_col is not None and na_col < df.shape[1] else None
    v_si = df.iat[r, si_col] if si_col is not None and si_col < df.shape[1] else None
    v_pa = df.iat[r, parcial_col] if parcial_col is not None and parcial_col < df.shape[1] else None
    v_no = df.iat[r, no_col] if no_col is not None and no_col < df.shape[1] else None

    v_co = df.iat[r, comments_col] if comments_col is not None and comments_col < df.shape[1] else None
    comment = _clean_cell_text(v_co)

    if is_marked_x(v_na):
        return item_txt, sub_txt, preg_txt, False, "NA", None, comment

    if is_marked_x(v_si):
        return item_txt, sub_txt, preg_txt, True, "SI", 100, comment

    if is_marked_x(v_pa):
        return item_txt, sub_txt, preg_txt, True, "PARCIAL", 50, comment

    if is_marked_x(v_no):
        return item_txt, sub_txt, preg_txt, True, "NO", 0, comment

    return item_txt, sub_txt, preg_txt, True, "SIN_MARCAR", 0, comment

# ============================================================
# CONTROL ID + GRUPO + AGREGACIÓN POR CONTROL
# ============================================================
def get_control_id(sheet_name: str, ref_txt: str) -> str:
    ref = (ref_txt or "").strip().upper()
    sh = norm_txt(sheet_name)

    if not ref:
        return ""

    if "anexo" in sh or ref.startswith("A."):
        m = re.match(r"^(A\.\d+\.\d+)", ref)
        return m.group(1) if m else "A."

    m = re.match(r"^(\d+\.\d+)", ref)
    return m.group(1) if m else ""


def resolve_control_id(sheet_name: str, item_id: str = "", subitem_id: str = "", ref_txt: str = "") -> str:
    for candidate in (item_id, subitem_id, ref_txt):
        cid = get_control_id(sheet_name, candidate)
        if cid:
            return cid
    return ""


def get_item_subitem_ids(sheet_name: str, ref_txt: str, control_id: str) -> tuple[str, str]:
    ref = (ref_txt or "").strip().upper()
    cid = (control_id or "").strip().upper()
    sh = norm_txt(sheet_name)

    if not ref or not cid:
        return "", ""

    if "anexo" in sh or cid.startswith("A."):
        m4 = re.match(r"^(A\.\d+\.\d+)\.(\d+)\.(\d+)", ref)
        if m4:
            base = m4.group(1)
            item = f"{base}.{m4.group(2)}"
            subitem = f"{item}.{m4.group(3)}"
            return item, subitem

        m3 = re.match(r"^(A\.\d+\.\d+)\.(\d+)", ref)
        if m3:
            item = f"{m3.group(1)}.{m3.group(2)}"
            return item, ""

        m2 = re.match(r"^(A\.\d+\.\d+)", ref)
        if m2:
            return m2.group(1), ""

        return cid, ""

    m4 = re.match(r"^(\d+\.\d+)\.(\d+)\.(\d+)", ref)
    if m4:
        base = m4.group(1)
        item = f"{base}.{m4.group(2)}"
        subitem = f"{item}.{m4.group(3)}"
        return item, subitem

    m3 = re.match(r"^(\d+\.\d+)\.(\d+)", ref)
    if m3:
        item = f"{m3.group(1)}.{m3.group(2)}"
        return item, ""

    m2 = re.match(r"^(\d+\.\d+)", ref)
    if m2:
        return m2.group(1), ""

    return cid, ""


def get_control_group_from_control_id(control_id: str) -> str:
    cid = (control_id or "").strip().upper()
    if not cid:
        return "Sin clasificar"
    if cid.startswith("A."):
        return "Anexo A"

    for group, ids in CONTROL_GROUPS.items():
        if group == "Anexo A":
            continue
        if cid in ids:
            return group

    return "Sin clasificar"


def aggregate_by_control(items: list) -> dict:
    acc = {}

    for it in items or []:
        cid = (it.get("control_id") or "").strip()
        if not cid:
            continue

        if not it.get("applicable", True) or (it.get("status") == "NA"):
            continue

        if cid not in acc:
            acc[cid] = {"total": 0, "done": 0, "score_sum": 0, "counts": {"SI":0,"PARCIAL":0,"NO":0,"SIN_MARCAR":0}}

        acc[cid]["total"] += 1
        st = (it.get("status") or "SIN_MARCAR").strip()
        if st not in acc[cid]["counts"]:
            st = "SIN_MARCAR"
        acc[cid]["counts"][st] += 1

        acc[cid]["score_sum"] += int(it.get("score", 0) or 0)
        if st == "SI":
            acc[cid]["done"] += 1

    out = {}
    for cid, v in acc.items():
        total = v["total"]
        pct = round((v["score_sum"] / (total * 100) * 100) if total else 0.0, 2)
        gap_info = gap_from_maturity_pct(pct)

        out[cid] = {
            "pct": pct,
            "done": v["done"],
            "total": total,
            "counts": v["counts"],
            "group": get_control_group_from_control_id(cid),
            "madurez": get_maturity_label_for_pct(pct),

            # ✅ NUEVO: brecha por control
            "brecha_pct": gap_info["gap_pct"],
            "brecha_nivel": gap_info["nivel_brecha"],
            "brecha_interp": gap_info["interpretacion"],
        }

    ordered = {}
    for cid in CONTROL_ORDER:
        if cid in out:
            ordered[cid] = out[cid]

    annex = sorted([k for k in out.keys() if k.startswith("A.")])
    for cid in annex:
        ordered[cid] = out[cid]

    rest = sorted([k for k in out.keys() if k not in ordered])
    for cid in rest:
        ordered[cid] = out[cid]

    return ordered


def detect_header_and_columns(df: "pd.DataFrame"):
    max_scan = min(120, df.shape[0])

    def is_ref(s):
        return ("ref" == s) or ("refer" in s) or ("control" in s) or (s == "id") or (s == "codigo")
    def is_preg(s):
        return ("pregunta" in s) or ("preguntas" in s) or ("requisito" in s) or ("criterio" in s) or ("enunciado" in s)
    def is_na(s): return ("no aplica" in s) or ("n/a" in s) or (s in ("na", "n a"))
    def is_si(s): return s in ("si", "sí")
    def is_parcial(s): return "parcial" in s
    def is_no(s): return s == "no"
    def is_com(s): return ("coment" in s) or ("observ" in s) or ("nota" in s)
    def is_proc(s): return ("proces" in s) or ("asociad" in s) or ("document" in s) or ("evidenc" in s)

    best = {"score": -1, "row": 0, "col_map": {}}

    for r in range(max_scan):
        col_map = {}
        for c in range(df.shape[1]):
            s = norm_txt(df.iat[r, c])
            if not s:
                continue

            if "ref_col" not in col_map and is_ref(s):
                col_map["ref_col"] = c
            elif "preg_col" not in col_map and is_preg(s):
                col_map["preg_col"] = c
            elif "na_col" not in col_map and is_na(s):
                col_map["na_col"] = c
            elif "si_col" not in col_map and is_si(s):
                col_map["si_col"] = c
            elif "parcial_col" not in col_map and is_parcial(s):
                col_map["parcial_col"] = c
            elif "no_col" not in col_map and is_no(s):
                col_map["no_col"] = c
            elif "comments_col" not in col_map and is_com(s):
                col_map["comments_col"] = c
            elif "proc_col" not in col_map and is_proc(s):
                col_map["proc_col"] = c

        score = 0
        for k in ("si_col", "no_col"):
            if k in col_map:
                score += 5
        for k in ("na_col", "parcial_col"):
            if k in col_map:
                score += 3
        for k in ("preg_col", "ref_col"):
            if k in col_map:
                score += 3
        if "comments_col" in col_map:
            score += 2
        if "proc_col" in col_map:
            score += 1

        if score > best["score"]:
            best = {"score": score, "row": r, "col_map": col_map}

        if ("si_col" in col_map and "no_col" in col_map and "preg_col" in col_map):
            return r, col_map

    if best["score"] >= 8:
        return best["row"], best["col_map"]

    return 0, {"ref_col": 0, "preg_col": 1, "na_col": 2, "si_col": 3, "parcial_col": 4, "no_col": 5, "comments_col": 6, "proc_col": 7}


def _row_has_any_mark(df, r, col_map):
    for k in ("na_col", "si_col", "parcial_col", "no_col"):
        c = col_map.get(k)
        if c is None or c >= df.shape[1]:
            continue
        if is_marked_x(df.iat[r, c]):
            return True
    return False


def display_estado(status: str) -> str:
    s = (status or "").strip()
    if s == "SIN_MARCAR":
        return ""
    return s


def brecha_pct_from_status(status: str):
    st = (status or "").strip()
    if st == "SI":
        return 0.0
    if st == "PARCIAL":
        return 50.0
    if st == "NO":
        return 100.0
    if st == "SIN_MARCAR":
        return 100.0
    if st == "NA":
        return None
    return 100.0


def eval_status_from_row(df: "pd.DataFrame", r: int, col_map: dict, requisito: str, ref_txt: str):
    na_col = col_map.get("na_col")
    si_col = col_map.get("si_col")
    parcial_col = col_map.get("parcial_col")
    no_col = col_map.get("no_col")
    comments_col = col_map.get("comments_col")
    proc_col = col_map.get("proc_col")

    v_na = df.iat[r, na_col] if na_col is not None and na_col < df.shape[1] else None
    v_si = df.iat[r, si_col] if si_col is not None and si_col < df.shape[1] else None
    v_pa = df.iat[r, parcial_col] if parcial_col is not None and parcial_col < df.shape[1] else None
    v_no = df.iat[r, no_col] if no_col is not None and no_col < df.shape[1] else None
    v_co = df.iat[r, comments_col] if comments_col is not None and comments_col < df.shape[1] else None
    v_pr = df.iat[r, proc_col] if proc_col is not None and proc_col < df.shape[1] else None

    comment = _clean_cell_text(v_co)
    procesos = _clean_cell_text(v_pr)

    is_title = is_title_row_by_marks(ref_txt, requisito, v_na, v_si, v_pa, v_no, comment, procesos)
    if is_title:
        return False, "", None, comment, procesos, True

    if is_marked_x(v_na):
        return False, "NA", None, comment, procesos, False

    if is_marked_x(v_si):
        return True, "SI", 100, comment, procesos, False
    if is_marked_x(v_pa):
        return True, "PARCIAL", 50, comment, procesos, False
    if is_marked_x(v_no):
        return True, "NO", 0, comment, procesos, False

    return True, "SIN_MARCAR", 0, comment, procesos, False


def parse_sheet_xls(excel_path: str, sheet_name: str):
    df = pd.read_excel(excel_path, sheet_name=sheet_name, header=None, engine="xlrd")

    # 1) Intentar formato NUEVO (Item/Subitem/Pregunta…)
    hdr2, col_map2 = detect_header_item_subitem(df)

    # FORMATO NUEVO
    if hdr2 is not None and col_map2 is not None:
        items = []
        last_ref = ""
        last_cid = ""

        for r in range(hdr2 + 1, df.shape[0]):
            item_id, subitem_id, pregunta, applicable, status, score, comment = \
                eval_status_from_row_item_subitem(df, r, col_map2)

            if item_id is None and pregunta is None and subitem_id is None:
                continue

            item_txt = _clean_cell_text(item_id)
            sub_txt  = _clean_cell_text(subitem_id)
            preg_txt = _clean_cell_text(pregunta)
            comm_txt = _clean_cell_text(comment)

            ref_comp = f"{item_txt}{('.' + sub_txt) if sub_txt else ''}".strip()

            if not ref_comp and last_ref:
                ref_comp = last_ref

            has_mark = (status in ("SI", "PARCIAL", "NO", "NA")) or (status == "SIN_MARCAR" and bool(item_txt))
            if (not preg_txt) and (not comm_txt) and (not has_mark):
                continue

            if is_excluded_row(preg_txt) or is_note_row(preg_txt):
                continue

            control_id = resolve_control_id(sheet_name, item_id=item_txt, subitem_id=sub_txt, ref_txt=ref_comp)

            if not control_id and last_cid:
                control_id = last_cid

            if control_id:
                last_cid = control_id
            if ref_comp:
                last_ref = ref_comp

            control_group = get_control_group_from_control_id(control_id)

            it = {
                "sheet": sheet_name,
                "row": r + 1,
                "ref": ref_comp or "—",
                "requisito": preg_txt or "(Sin pregunta / evidencia en comentarios)",
                "applicable": bool(applicable) if applicable is not None else True,
                "status": status or "SIN_MARCAR",
                "score": 0 if score is None else int(score),
                "cumple": (status == "SI"),
                "comment": comm_txt or "",
                "procesos": "",
                "subkey": extract_subkey(sheet_name, ref_comp),
                "control_id": control_id,
                "control_group": control_group,
                "item_id": item_txt,
                "subitem_id": sub_txt,
            }

            bp = brecha_pct_from_status(it["status"])
            it["brecha_pct"] = bp if bp is not None else None
            if bp is not None:
                gl = get_gap_level_for_pct(bp)
                it["brecha_nivel"] = gl.get("nivel_brecha", "")
                it["brecha_interp"] = gl.get("interpretacion", "")
            else:
                it["brecha_nivel"] = ""
                it["brecha_interp"] = ""

            items.append(it)

        applicable_items = [it for it in items if it["applicable"] and it["status"] != "NA"]
        total = len(applicable_items)
        done = sum(1 for it in applicable_items if it["status"] == "SI")
        score_sum = sum(it["score"] for it in applicable_items) if total else 0
        pct = round((score_sum / (total * 100) * 100) if total else 0.0, 2)

        return items, pct, done, total, {}

    # FORMATO GENERAL
    hdr, col_map = detect_header_and_columns(df)

    ref_col = col_map.get("ref_col", 0)
    preg_col = col_map.get("preg_col", 1)

    items = []
    last_ref_txt = ""
    last_cid = ""

    for r in range(hdr + 1, df.shape[0]):
        ref_val = df.iat[r, ref_col] if ref_col is not None and ref_col < df.shape[1] else None
        preg_val = df.iat[r, preg_col] if preg_col is not None and preg_col < df.shape[1] else None

        ref_txt = _clean_cell_text(ref_val)
        requisito = _clean_cell_text(preg_val)

        applicable, status, score, comment, procesos, is_title = eval_status_from_row(
            df, r, col_map, requisito=requisito, ref_txt=ref_txt
        )

        comm_txt = _clean_cell_text(comment)
        proc_txt = _clean_cell_text(procesos)
        has_mark = _row_has_any_mark(df, r, col_map)

        if is_title:
            continue

        if (not requisito) and (not comm_txt) and (not proc_txt) and (not has_mark) and (not ref_txt):
            continue

        if is_excluded_row(requisito) or is_note_row(requisito):
            continue

        if not ref_txt and last_ref_txt:
            ref_txt = last_ref_txt

        control_id = get_control_id(sheet_name, ref_txt)
        if not control_id and last_cid:
            control_id = last_cid

        if ref_txt:
            last_ref_txt = ref_txt
        if control_id:
            last_cid = control_id

        control_group = get_control_group_from_control_id(control_id)

        item = {
            "sheet": sheet_name,
            "row": r + 1,
            "ref": ref_txt or "—",
            "requisito": requisito or "(Sin pregunta / evidencia en comentarios)",
            "applicable": bool(applicable) if applicable is not None else True,
            "status": status or "SIN_MARCAR",
            "score": 0 if score is None else int(score),
            "cumple": (status == "SI"),
            "comment": comm_txt,
            "procesos": proc_txt,
            "subkey": extract_subkey(sheet_name, ref_txt),
            "control_id": control_id,
            "control_group": control_group,
            "item_id": "",
            "subitem_id": "",
        }

        bp = brecha_pct_from_status(item["status"])
        item["brecha_pct"] = bp if bp is not None else None
        if bp is not None:
            gl = get_gap_level_for_pct(bp)
            item["brecha_nivel"] = gl.get("nivel_brecha", "")
            item["brecha_interp"] = gl.get("interpretacion", "")
        else:
            item["brecha_nivel"] = ""
            item["brecha_interp"] = ""

        items.append(item)

    applicable_items = [it for it in items if it["applicable"] and it["status"] != "NA"]
    total = len(applicable_items)
    done = sum(1 for it in applicable_items if it["status"] == "SI")
    score_sum = sum(it["score"] for it in applicable_items) if total else 0
    pct = round((score_sum / (total * 100) * 100) if total else 0.0, 2)

    detail_map = {}
    for it in applicable_items:
        sk = it.get("subkey") or ""
        if not sk:
            continue
        detail_map.setdefault(sk, {"score_sum": 0, "total": 0, "pct": 0.0})
        detail_map[sk]["total"] += 1
        detail_map[sk]["score_sum"] += it["score"]

    for sk, v in detail_map.items():
        v["pct"] = round((v["score_sum"] / (v["total"] * 100) * 100) if v["total"] else 0.0, 2)
        v.pop("score_sum", None)

    return items, pct, done, total, detail_map


# ==========================
# GRÁFICOS
# ==========================
def make_radar_base64(labels, values, title="Araña de madurez", max_label_len=22):
    # 1) recorte general
    labels2 = [l if len(l) <= max_label_len else (l[:max_label_len] + "…") for l in labels]

    # 2) ✅ FIX SOLO para 6 Planificación y 10 Mejora: poner salto de línea
    #    (funciona aunque vengan como "6 Planificación", "6 Planificación (algo)", etc.)
    def _wrap_special(s: str) -> str:
        ss = (s or "").strip()
        low = ss.lower()

        # ✅ número a la IZQUIERDA, misma línea
        if low.startswith("6 ") and "planific" in low:
            return ss  # ya viene correcto: "6 Planificación"

        if low.startswith("10 ") and "mejora" in low:
            return ss  # ya viene correcto: "10 Mejora"

        return ss

    labels2 = [_wrap_special(x) for x in labels2]

    N = len(labels2)
    if N == 0:
        return ""

    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    vals = values + values[:1]
    angs = angles + angles[:1]

    fig = plt.figure(figsize=(6.8, 6.8))
    ax = plt.subplot(111, polar=True)

    ax.plot(angs, vals, linewidth=2)
    ax.fill(angs, vals, alpha=0.22)

    # ✅ más separación entre etiquetas y círculo
    ax.tick_params(axis="x", pad=12)

    # coloca los labels
    ax.set_thetagrids(np.degrees(angles), labels2, fontsize=8)

    # ✅ FIX: rotación + alineación por ángulo para evitar sobreposición visual
    for lbl, ang in zip(ax.get_xticklabels(), angles):
        txt = (lbl.get_text() or "").lower()
        ang_deg = np.degrees(ang)

        # ✅ CASO ESPECIAL: 6 Planificación / 10 Mejora → CENTRADO
        if txt.startswith("6 ") or txt.startswith("10 "):
            lbl.set_rotation(0)                     # horizontal
            lbl.set_horizontalalignment("center")   # 🔥 centrado
            lbl.set_verticalalignment("center")
            lbl.set_rotation_mode("anchor")
            continue
        
            # Rota el texto para que "siga" el círculo y se lea mejor
        # y alinea según el lado (derecha/izquierda) del radar
        if 90 <= ang_deg <= 270:
            lbl.set_horizontalalignment("right")
            lbl.set_rotation(ang_deg + 180)
        else:
            lbl.set_horizontalalignment("left")
            lbl.set_rotation(ang_deg)

        lbl.set_rotation_mode("anchor")

    ax.set_ylim(0, 100)
    ax.set_title(title, y=1.12)

    buf = io.BytesIO()

    # ✅ deja aire arriba para el título (evita que tight_layout lo empuje)
    plt.tight_layout(rect=[0, 0, 1, 0.95])

    fig.savefig(buf, format="png", dpi=170)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("utf-8")



def make_bar_base64(labels, values, title="Madurez por capítulo", max_label_len=26):
    labs = [l if len(l) <= max_label_len else (l[:max_label_len] + "…") for l in labels]
    if not labs:
        return ""

    fig = plt.figure(figsize=(10.5, 4.2))
    ax = plt.subplot(111)

    x = np.arange(len(labs))
    bars = ax.bar(x, values)

    # ✅ deja aire arriba (dinámico) para que SIEMPRE haya espacio para etiquetas
    vmax = 0
    try:
        vmax = max(float(x) for x in values) if values else 0
    except Exception:
        vmax = 0
    ax.set_ylim(0, max(110, vmax + 12))

    ax.set_xticks(x)
    ax.set_xticklabels(labs, rotation=25, ha="right", fontsize=9)
    ax.set_ylabel("%")
    ax.set_title(title, pad=14)

    # ✅ SIEMPRE etiqueta arriba de la barra
    top_y = ax.get_ylim()[1]
    for i, v in enumerate(values):
        try:
            vv = float(v)
            label = f"{vv:.0f}%"
            y = min(vv + 2, top_y - 2)   # arriba, pero sin salirse del marco
            ax.text(i, y, label, ha="center", va="bottom", fontsize=8)
        except Exception:
            pass
    

    ax.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.4)

    buf = io.BytesIO()
    plt.tight_layout()
    fig.savefig(buf, format="png", dpi=170)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("utf-8")

def make_bar_chapters_plus_annexA_with_box_base64(chapter_results: dict, control_results: dict, title: str = "Madurez por capítulo + Anexo A (%)") -> str:
    """
    Gráfico de barras por capítulo (incluye 'Anexo A' como un capítulo más).
    - Usa chapter_results para los capítulos (4–10 y Anexo A).
    - Si chapter_results no trae "Anexo A" o viene en 0, intenta estimarlo desde control_results (promedio de A.*).
    Retorna PNG base64.
    """
    if not isinstance(chapter_results, dict):
        chapter_results = {}

    labels = []
    values = []

    # Orden UI esperado
    ordered = list(CHAPTER_SHEETS)

    # 1) construir valores base desde chapter_results
    for sh in ordered:
        v = chapter_results.get(sh, {}) if isinstance(chapter_results.get(sh, {}), dict) else {}
        pct = v.get("pct", 0)
        try:
            pct = float(pct or 0)
        except Exception:
            pct = 0.0

        labels.append(sh)
        values.append(pct)

    # 2) Si "Anexo A" está vacío o no existe, estimarlo desde control_results (promedio de A.*)
    try:
        idx_annex = labels.index("Anexo A")
    except ValueError:
        idx_annex = -1

    if idx_annex >= 0:
        annex_pct = values[idx_annex]
        if annex_pct == 0.0 and isinstance(control_results, dict):
            a_pcts = []
            for cid, kpi in control_results.items():
                cid_u = str(cid).strip().upper()
                if cid_u.startswith("A."):
                    try:
                        a_pcts.append(float((kpi or {}).get("pct", 0) or 0))
                    except Exception:
                        pass
            if a_pcts:
                values[idx_annex] = round(sum(a_pcts) / len(a_pcts), 2)

    # 3) generar el gráfico
    return make_bar_base64(labels, values, title=title, max_label_len=26)


def make_bar_controls_4_10_base64(control_results: dict) -> str:
    """
    Barras SOLO para controles 4.1..10.2 (los de CONTROL_ORDER).
    """
    # control_results viene como dict: {cid: {"pct":..., ...}}
    labels = []
    values = []

    for cid in CONTROL_ORDER:
        if cid in control_results:
            labels.append(cid)
            values.append(float(control_results[cid].get("pct", 0) or 0))

    return make_bar_base64(labels, values, title="Madurez por control (4–10) (%)", max_label_len=10)


def make_bar_annexA_lowest_base64(control_results: dict, top_n: int = 20) -> str:
    """
    Barras resumidas del Anexo A: muestra los N controles con menor % (peores) para mantenerlo 'resumido'.
    Si no hay A.*, retorna "".
    """
    a_items = []
    for cid, v in (control_results or {}).items():
        cid_u = str(cid).strip().upper()
        if cid_u.startswith("A."):
            pct = float(v.get("pct", 0) or 0)
            a_items.append((cid_u, pct))

    if not a_items:
        return ""

    # Orden ascendente: peores primero (menor %)
    a_items.sort(key=lambda x: x[1])
    a_items = a_items[:max(1, int(top_n))]

    labels = [x[0] for x in a_items]
    values = [x[1] for x in a_items]

    return make_bar_base64(labels, values, title=f"Anexo A – Controles con menor madurez (Top {len(labels)}) (%)", max_label_len=14)

PLAN_SCHEMA_JSON = """
{
  "action_plan": [
    {
      "fase": "0-30|31-60|61-90|90+",
      "capitulo": "Contexto|Liderazgo|Planificación|Soporte|Operación|Evaluación de desempeño|Mejora|Anexo A",
      "requisito": "Requisito ISO 27001:2022 (ej: 6.1, 10.2, A.5.1, etc.) o 'Dominio' si aplica",
      "accion": "Acción detallada, ejecutable, verificable (NO condicional)",
      "evidencia": "Evidencia verificable esperada (política/procedimiento/registro/acta/indicador)",
      "responsable": "Rol responsable (ej: Líder SGSI / Dueño de proceso / TI / RRHH / Riesgos / Alta Dirección)",
      "prioridad": "Alta|Media|Baja"
    }
  ]
}
""".strip()

# ==========================
# IA
# ==========================

def normalize_plan_response(raw: str) -> dict:
    """
    Acepta:
      - {"action_plan":[...]}
      - {"plan":[...]}
      - [{...}, {...}]  <-- lista directa (tu caso)
    Retorna SIEMPRE dict: {"action_plan":[...]} con llaves normalizadas.
    """
    parsed = json.loads((raw or "").strip() or "{}")

    # 1) obtener lista de filas
    if isinstance(parsed, list):
        rows = parsed
    elif isinstance(parsed, dict):
        rows = parsed.get("action_plan") or parsed.get("plan") or parsed.get("acciones") or []
    else:
        rows = []

    if not isinstance(rows, list):
        rows = []

    # 2) normalizar llaves (acentos -> sin acentos) y a tu schema UI
    def _get(r, *keys):
        for k in keys:
            if k in r:
                return r.get(k)
        return None

    cleaned = []
    for r in rows:
        if not isinstance(r, dict):
            continue

        accion = _get(r, "accion", "acción", "Acción", "ACCION")
        proposito = _get(r, "proposito", "propósito", "Propósito", "PROPOSITO")
        evidencia = _get(r, "evidencia", "Evidencia", "EVIDENCIA")
        prioridad = _get(r, "prioridad", "Prioridad", "PRIORIDAD")
        horizonte = _get(r, "horizonte", "Horizonte", "HORIZONTE")
        dependencia = _get(r, "dependencia", "Dependencia", "DEPENDENCIA")
        responsable = _get(r, "responsable", "Responsable", "RESPONSABLE")
        requisito = _get(r, "requisito", "Requisito", "REQUISITO")
        capitulo = _get(r, "capitulo", "capítulo", "Capítulo", "CAPITULO")
        fase = _get(r, "fase", "Fase", "FASE")

        cleaned.append({
            "accion": harden_no_conditionals(to_text(accion)).strip(),
            "proposito": harden_no_conditionals(to_text(proposito)).strip(),
            "evidencia": harden_no_conditionals(to_text(evidencia)).strip(),
            "prioridad": (to_text(prioridad) or "").strip(),
            "horizonte": (to_text(horizonte) or "").strip(),
            "dependencia": harden_no_conditionals(to_text(dependencia)).strip(),
            "responsable": harden_no_conditionals(to_text(responsable)).strip(),
            "requisito": harden_no_conditionals(to_text(requisito)).strip(),
            "capitulo": (to_text(capitulo) or "").strip(),
            "fase": (to_text(fase) or "").strip(),
        })

    return {"action_plan": cleaned}


def get_openai_client():
    """
    Mantiene el mismo nombre para no romper el módulo,
    pero ahora devuelve configuración dinámica para:
    - OpenRouter
    - Ollama
    """
    provider = (get_ai_provider() or "openrouter").strip().lower()

    if provider == "ollama":
        return {
            "provider": "ollama",
            "base_url": (get_ollama_base_url() or "http://localhost:11434").strip().rstrip("/"),
            "model": (get_ollama_model() or "llama3.1").strip()
        }

    api_key = (get_openrouter_api_key() or "").strip()
    if not api_key:
        raise RuntimeError("No hay OPENROUTER_API_KEY configurada. Ve a Administración → OpenRouter API Key.")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        default_headers={
            "HTTP-Referer": "https://sgsi.local",
            "X-Title": "SGSI ISO 27001 Analyzer"
        }
    )

    return {
        "provider": "openrouter",
        "client": client,
        "model": "openai/gpt-4o-mini"
    }

def openai_call_with_retry(
    client: OpenAI, *, model: str, messages: list, response_format: dict,
    temperature: float = 0.2, max_tokens: int = None, max_retries: int = 6
):
    last_err = None
    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                response_format=response_format,
                max_tokens=max_tokens if max_tokens is not None else OPENROUTER_MAX_TOKENS,
            )
        except OpenAIError as e:
            msg = str(e).lower()
            last_err = e
            if "rate_limit" in msg or "429" in msg:
                sleep_s = min(30, (2 ** attempt)) + random.uniform(0.2, 1.0)
                time.sleep(sleep_s)
                continue
            raise
    raise last_err

def ai_json_iso(prompt: str,
                system_prompt: str = "Devuelve SOLO JSON válido. No agregues texto fuera del JSON.",
                model_openrouter: str = "openai/gpt-4o-mini",
                max_tokens: int = None) -> dict:
    """
    Helper IA para ISO 27001.
    Devuelve siempre dict JSON usando:
    - OpenRouter
    - Ollama
    """
    cfg = get_openai_client()
    provider = cfg.get("provider")

    print("DEBUG IA ISO - provider activo:", provider)

    # =========================
    # OLLAMA
    # =========================
    if provider == "ollama":
        base_url = (cfg.get("base_url") or "").rstrip("/")
        model = (cfg.get("model") or "").strip()

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
                    "temperature": 0.2
                }
            },
            timeout=300
        )
        resp.raise_for_status()

        payload = resp.json() or {}

        raw = (payload.get("response") or "").strip()
        if not raw:
            raw = (payload.get("message") or "").strip()

        if not raw:
            raise RuntimeError(f"Ollama respondió sin contenido. Payload: {str(payload)[:500]}")

        print("DEBUG IA ISO - RAW:", raw[:1500])
        return normalize_plan_response(raw)

    # =========================
    # OPENROUTER
    # =========================
    client = cfg["client"]
    model_name = cfg.get("model") or model_openrouter

    resp = openai_call_with_retry(
        client,
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=max_tokens
    )

    raw = (resp.choices[0].message.content or "").strip() or "{}"

    return normalize_plan_response(raw)

def ai_json_iso_generic(prompt: str,
                        system_prompt: str = "Devuelve SOLO JSON válido. No agregues texto fuera del JSON.",
                        model_openrouter: str = "openai/gpt-4o-mini",
                        max_tokens: int = None) -> dict:
    """
    Helper IA genérico para ISO 27001.
    Devuelve un dict JSON y soporta:
    - OpenRouter
    - Ollama
    """
    cfg = get_openai_client()
    provider = cfg.get("provider")

    print("DEBUG IA ISO GENERIC - provider activo:", provider)

    # =========================
    # OLLAMA
    # =========================
    if provider == "ollama":
        base_url = (cfg.get("base_url") or "").rstrip("/")
        model = (cfg.get("model") or "").strip()

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
                    "temperature": 0.2
                }
            },
            timeout=300
        )
        resp.raise_for_status()

        payload = resp.json() or {}

        raw = (payload.get("response") or "").strip()
        if not raw:
            raw = (payload.get("message") or "").strip()

        if not raw:
            raise RuntimeError(f"Ollama respondió sin contenido. Payload: {str(payload)[:500]}")

        return _extraer_json_objeto(raw)

    # =========================
    # OPENROUTER
    # =========================
    client = cfg["client"]
    model_name = cfg.get("model") or model_openrouter

    resp = openai_call_with_retry(
        client,
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=max_tokens
    )

    raw = (resp.choices[0].message.content or "").strip() or "{}"

    return _extraer_json_objeto(raw)

def ai_generate_report_and_plan(company_name: str, chapter_results: dict, control_results: dict) -> dict:
    resumen_cap = "\n".join(
        [f"- {k}: {v.get('pct',0)}%" for k, v in chapter_results.items()]
    )

    resumen_ctrl = "\n".join(
        [f"- {cid} ({v.get('group','')}): {v.get('pct',0)}%"
         for cid, v in list(control_results.items())[:200]]
    )

    prompt = f"""
Eres un consultor experto en ISO/IEC 27001:2022 y sistemas de gestión de seguridad de la información.

Organización evaluada: {company_name}

Resumen por capítulo:
{resumen_cap}

Resumen por controles:
{resumen_ctrl}

Tareas:
1. Genera un executive_summary claro, ejecutivo y sin lenguaje condicional.
2. Genera un report con análisis ejecutivo de fortalezas, brechas y enfoque de mejora.
3. Genera un action_plan con acciones ejecutables y verificables.

Devuelve SOLO JSON válido con esta estructura:
{{
  "executive_summary": "texto",
  "report": "texto",
  "action_plan": [
    {{
      "fase": "0-30|31-60|61-90|90+",
      "capitulo": "Contexto|Liderazgo|Planificación|Soporte|Operación|Evaluación de desempeño|Mejora|Anexo A",
      "requisito": "Requisito ISO 27001:2022 (ej: 6.1, 10.2, A.5.1, etc.) o 'Dominio' si aplica",
      "accion": "Acción detallada, ejecutable, verificable",
      "evidencia": "Evidencia verificable esperada",
      "responsable": "Rol responsable",
      "prioridad": "Alta|Media|Baja"
    }}
  ]
}}
    """.strip()

    try:
        data = ai_json_iso(
            prompt=prompt,
            system_prompt="Devuelve SOLO JSON válido. No agregues texto fuera del JSON.",
            model_openrouter="open/gpt-4.1-mini",
            max_tokens=OPENROUTER_MAX_TOKENS
        )

        data["executive_summary"] = harden_no_conditionals(to_text(data.get("executive_summary")))
        data["report"] = harden_no_conditionals(to_text(data.get("report")))

        ap = data.get("action_plan", [])
        if isinstance(ap, list):
            for row in ap:
                if isinstance(row, dict):
                    for k in ("accion", "evidencia", "responsable", "requisito", "proposito", "dependencia", "fase", "capitulo"):
                        if k in row:
                            row[k] = harden_no_conditionals(to_text(row.get(k)))
        data["action_plan"] = ap

        return data

    except AuthenticationError:
        raise RuntimeError("API Key inválida o no autorizada (401). Revisa tu OPENROUTER_API_KEY.")
    except OpenAIError as e:
        if "rate_limit" in str(e).lower() or "429" in str(e):
            raise RuntimeError("⚠️ Límite de uso de IA alcanzado (429). El informe base y el PDF siguen funcionando.")
        raise RuntimeError(f"Error OpenAI: {e}")
    except Exception as e:
        raise RuntimeError(f"Error procesando respuesta IA ISO 27001: {e}")

def build_controls_prompt_summary(control_results: dict, top_n: int = 60, annex_top_n: int = 25) -> str:
    """
    Reduce tokens del prompt:
    - Toma los peores controles (menor % o mayor brecha).
    - Para Anexo A, limita aún más (annex_top_n) porque suele ser enorme.
    """
    if not isinstance(control_results, dict) or not control_results:
        return "N/A"

    rows = []
    for cid, v in control_results.items():
        cid_u = str(cid).strip().upper()
        vv = v or {}
        try:
            pct = float(vv.get("pct", 0) or 0)
        except Exception:
            pct = 0.0
        brecha_nivel = (vv.get("brecha_nivel", "") or "").strip()
        try:
            brecha_pct = float(vv.get("brecha_pct", 0) or 0)
        except Exception:
            brecha_pct = 0.0
        group = (vv.get("group", "") or "").strip()

        rows.append({
            "cid": cid_u,
            "pct": pct,
            "brecha_pct": brecha_pct,
            "brecha_nivel": brecha_nivel,
            "group": group,
        })

    # peores primero: menor % (equivale a mayor brecha)
    rows.sort(key=lambda x: (x["pct"], -x["brecha_pct"]))

    # separa anexoA y no-anexo
    non_a = [r for r in rows if not r["cid"].startswith("A.")]
    annex = [r for r in rows if r["cid"].startswith("A.")]

    non_a = non_a[:max(10, int(top_n))]
    annex = annex[:max(0, int(annex_top_n))]

    out_lines = []
    for r in non_a + annex:
        out_lines.append(
            f"- {r['cid']} ({r['group']}): {r['pct']}% | Brecha {r['brecha_pct']}% ({r['brecha_nivel']})"
        )

    return "\n".join(out_lines) if out_lines else "N/A"

def ai_generate_general_action_plan(company_name: str, chapter_results: dict, control_results: dict) -> dict:
    """
    Genera SOLO:
      - action_plan (lista detallada a nivel general)
    Puede usar capítulos + un resumen reducido de controles para priorización.
    """
    client = get_openai_client()
    raw = "{}"

    resumen_cap = "\n".join(
        [f"- {k}: {v.get('pct', 0)}% (Brecha {v.get('brecha_pct', 0)}% - {v.get('brecha_nivel','')})"
         for k, v in (chapter_results or {}).items()]
    )

    resumen_ctrl = build_controls_prompt_summary(
        control_results=control_results,
        top_n=60,
        annex_top_n=25
    )

    prompt = f"""
Actúa como consultor senior ISO/IEC 27001:2022 y auditor líder.

Empresa: {company_name}

Debes generar SOLO un "Plan de acción general" DETALLADO (a nivel de control/capítulo, no por pregunta/ítem).

REGLAS:
- NO inventes hechos específicos del cliente.
- Redacción verificable (Se debe / Se requiere / Se evidencia / Se mantiene / Se revisa / Se mide).
- NO uses lenguaje condicional.
- NO incluyas “Resumen ejecutivo” ni “Informe detallado”.
- El plan debe ser accionable: acción, propósito, evidencia genérica, prioridad, horizonte y dependencia.

ENTRADAS (capítulos):
{resumen_cap if resumen_cap else "N/A"}

ENTRADAS (controles resumidos - peores):
{resumen_ctrl if resumen_ctrl else "N/A"}

Devuelve SOLO JSON válido con esta estructura EXACTA:

REGLA CRÍTICA:
- NO dejes ningún campo vacío. Si no aplica un requisito exacto, usa el dominio o control más cercano.
- 'responsable' debe ser un rol (no un nombre propio).


IMPORTANT: Return ONLY valid JSON.
""".strip()

    try:
        resp = openai_call_with_retry(
            client,
            model=OPENROUTER_MODEL_SGSI,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            response_format={"type": "json_object"},
            max_tokens=16500,   # ✅ clave: obliga respuesta larga
        )
        raw = (resp.choices[0].message.content or "{}").strip() or "{}"

        # ✅ FIX: normaliza si la IA devolvió LISTA raíz
        data = normalize_plan_response(raw)   # SIEMPRE dict {"action_plan":[...]}

        ap = data.get("action_plan", [])
        if not isinstance(ap, list):
            ap = []

        cleaned = []
        for row in ap:
            if not isinstance(row, dict):
                continue
            cleaned.append({
                "accion": harden_no_conditionals(to_text(row.get("accion"))),
                "proposito": harden_no_conditionals(to_text(row.get("proposito"))),
                "evidencia": harden_no_conditionals(to_text(row.get("evidencia"))),
                "prioridad": (to_text(row.get("prioridad")) or "").strip(),
                "horizonte": (to_text(row.get("horizonte")) or "").strip(),
                "dependencia": harden_no_conditionals(to_text(row.get("dependencia"))),
            })

        return {"action_plan": cleaned}

    except AuthenticationError:
        raise RuntimeError("API Key inválida o no autorizada (401). Revisa tu OPENAI_API_KEY.")
    except OpenAIError as e:
        if "rate_limit" in str(e).lower() or "429" in str(e):
            raise RuntimeError("⚠️ Límite de uso de IA alcanzado (429). El informe base y el PDF siguen funcionando.")
        raise RuntimeError(f"Error OpenAI: {e}")
    except Exception as e:
        snippet = raw[:800] if isinstance(raw, str) else str(raw)
        raise RuntimeError(f"Error procesando respuesta IA: {e}. Respuesta cruda (parcial): {snippet}")

def ai_generate_exec_summary_and_general_plan(company_name: str, chapter_results: dict, control_results: dict) -> dict:
    """
    Genera:
      - executive_summary (texto)
      - action_plan (lista detallada a nivel general, NO por pregunta/ítem)
    NO genera informe detallado.
    """
    client = get_openai_client()
    raw = "{}"

    # Resumen por capítulo
    resumen_cap = "\n".join(
        [f"- {k}: {v.get('pct', 0)}% (Brecha {v.get('brecha_pct', 0)}% - {v.get('brecha_nivel','')})"
         for k, v in (chapter_results or {}).items()]
    )

    # Resumen por control (limitar para prompt)
    resumen_ctrl = build_controls_prompt_summary(
        control_results=control_results,
        top_n=60,        # NO Anexo A
        annex_top_n=25   # solo peores 25 del Anexo A
    )

    prompt = f"""
Actúa como consultor senior ISO/IEC 27001:2022 y auditor líder.

Empresa: {company_name}

Debes generar SOLO un "Plan de acción general" DETALLADO (a nivel de control/capítulo, no por pregunta/ítem).

REGLAS:
- NO inventes hechos específicos del cliente.
- Redacción verificable (Se debe / Se requiere / Se evidencia / Se mantiene / Se revisa / Se mide).
- NO uses lenguaje condicional.
- El plan debe diligenciar TODOS los campos: Fase, Capítulo, Requisito, Acción, Evidencia, Responsable, Prioridad.
- NO incluyas otros campos diferentes a los del schema.

ENTRADAS (capítulos):
{resumen_cap if resumen_cap else "N/A"}

ENTRADAS (controles resumidos - peores):
{resumen_ctrl if resumen_ctrl else "N/A"}

Devuelve SOLO JSON válido con esta estructura EXACTA:
{PLAN_SCHEMA_JSON}

IMPORTANT: Return ONLY valid JSON.
""".strip()

    try:
        resp = openai_call_with_retry(
            client,
            model=OPENROUTER_MODEL_SGSI,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        raw = (resp.choices[0].message.content or "{}").strip() or "{}"

        # ✅ FIX: normaliza plan incluso si viene como LISTA
        data = normalize_plan_response(raw)   # -> {"action_plan":[...]} (y soporta keys con acentos)

        # executive_summary puede no venir en este endpoint; no lo fuerces si no existe
        if "executive_summary" in data:
            data["executive_summary"] = harden_no_conditionals(to_text(data.get("executive_summary")))

        ap = data.get("action_plan", [])
        if not isinstance(ap, list):
            ap = []

        def _norm_choice(x: str, allowed: set, default: str) -> str:
            v = (to_text(x) or "").strip()
            return v if v in allowed else default

        FASES = {"0-30", "31-60", "61-90", "90+"}
        CAPS = {
            "Contexto", "Liderazgo", "Planificación", "Soporte",
            "Operación", "Evaluación de desempeño", "Mejora", "Anexo A"
        }
        PRIOS = {"Alta", "Media", "Baja"}

        cleaned = []
        for row in ap:
            if not isinstance(row, dict):
                continue

            fase = _norm_choice(row.get("fase"), FASES, "31-60")
            capitulo = _norm_choice(row.get("capitulo"), CAPS, "Planificación")
            prioridad = _norm_choice(row.get("prioridad"), PRIOS, "Media")

            requisito = harden_no_conditionals(to_text(row.get("requisito"))).strip()
            accion = harden_no_conditionals(to_text(row.get("accion"))).strip()
            evidencia = harden_no_conditionals(to_text(row.get("evidencia"))).strip()
            responsable = harden_no_conditionals(to_text(row.get("responsable"))).strip()

            # ✅ Nunca vacío
            if not requisito:
                requisito = "Dominio/Control aplicable (no especificado)"
            if not accion:
                accion = "Definir e implementar la acción requerida con evidencia verificable y seguimiento."
            if not evidencia:
                evidencia = "Procedimiento/registro/acta/indicador verificable."
            if not responsable:
                responsable = "Líder SGSI"

            cleaned.append({
                "fase": fase,
                "capitulo": capitulo,
                "requisito": requisito,
                "accion": accion,
                "evidencia": evidencia,
                "responsable": responsable,
                "prioridad": prioridad,
            })

        return {"action_plan": cleaned}

    except AuthenticationError:
        raise RuntimeError("API Key inválida o no autorizada (401). Revisa tu OPENAI_API_KEY.")
    except OpenAIError as e:
        if "rate_limit" in str(e).lower() or "429" in str(e):
            raise RuntimeError("⚠️ Límite de uso de IA alcanzado (429). El informe base y el PDF siguen funcionando.")
        raise RuntimeError(f"Error OpenAI: {e}")
    except Exception as e:
        snippet = raw[:800] if isinstance(raw, str) else str(raw)
        raise RuntimeError(f"Error procesando respuesta IA: {e}. Respuesta cruda (parcial): {snippet}")

def ai_generate_executive_summary_from_domains(company_name: str, chapter_results: dict) -> dict:
    """
    Genera SOLO:
      - executive_summary (texto)
    Basado SOLO en chapter_results (dominios/capítulos). NO usa control_results.
    Compatible con OpenRouter y Ollama.

    Si la IA falla, devuelve un resumen ejecutivo automático y útil
    para no bloquear el flujo.
    """
    resumen_cap = "\n".join(
        [f"- {k}: {v.get('pct', 0)}% (Brecha {v.get('brecha_pct', 0)}% - {v.get('brecha_nivel','')})"
         for k, v in (chapter_results or {}).items()]
    )

    prompt = f"""
Actúa como consultor senior ISO/IEC 27001:2022, auditor líder y asesor de alta dirección.

Empresa: {company_name}

Dispones únicamente de resultados de madurez y brecha por DOMINIO/CAPÍTULO del SGSI.
Debes generar un RESUMEN EJECUTIVO AMPLIO, DETALLADO y ORIENTADO A DIRECCIÓN.

OBJETIVO
El resumen debe explicar con profundidad:
1. El panorama general del nivel de madurez del SGSI.
2. Qué dominios muestran mayor fortaleza y por qué eso es relevante.
3. Qué dominios presentan mayores brechas y qué implicaciones tienen.
4. Cómo esas brechas afectan gobierno, operación, cumplimiento, evidencia y mejora continua.
5. Qué prioridades estratégicas debe considerar la dirección.
6. Una conclusión ejecutiva clara sobre el estado global del SGSI.

REGLAS OBLIGATORIAS
- BASARTE ÚNICAMENTE en los resultados por capítulo/dominio.
- NO inventar hechos específicos del cliente.
- NO inventar herramientas, documentos, incidentes ni tecnologías concretas.
- NO usar lenguaje condicional.
- NO incluir plan de acción detallado.
- NO incluir markdown.
- NO incluir tablas.
- NO incluir texto fuera del JSON.

ENTRADAS (capítulos / dominios):
{resumen_cap if resumen_cap else "N/A"}

FORMATO ACEPTADO DE RESPUESTA

OPCIÓN 1:
{{
  "executive_summary": "texto amplio, detallado y ejecutivo"
}}

OPCIÓN 2:
{{
  "panorama_general": "...",
  "fortalezas": "... o {{...}}",
  "brechas": "... o {{...}}",
  "implicaciones": "... o {{...}}",
  "prioridades": "... o {{...}}",
  "conclusion": "... o {{...}}",
  "hallazgos_clave": ["...", "..."]
}}
""".strip()

    def _clean_text(txt) -> str:
        return harden_no_conditionals(to_text(txt)).strip()

    def _dict_to_text_block(obj) -> str:
        """
        Convierte dict/list/str a texto limpio, sin mostrar llaves JSON.
        """
        if obj is None:
            return ""

        if isinstance(obj, str):
            return _clean_text(obj)

        if isinstance(obj, (int, float)):
            return str(obj)

        if isinstance(obj, list):
            out = []
            for x in obj:
                txt = _dict_to_text_block(x)
                if txt:
                    if "\n" in txt:
                        out.append(txt)
                    elif txt.startswith(("•", "-", "–")):
                        out.append(txt)
                    else:
                        out.append(f"• {txt}")
            return "\n".join([x for x in out if x.strip()]).strip()

        if isinstance(obj, dict):
            out = []
            for k, v in obj.items():
                val = _dict_to_text_block(v)
                if not val:
                    continue

                key_txt = _clean_text(str(k)).replace("_", " ").strip().capitalize()

                # si es texto simple, lo presentamos elegante
                if "\n" not in val and not val.startswith("•"):
                    out.append(f"{key_txt}: {val}")
                else:
                    out.append(f"{key_txt}:\n{val}")
            return "\n".join([x for x in out if x.strip()]).strip()

        return _clean_text(obj)

    def _get_first(data: dict, *keys):
        for k in keys:
            if k in data:
                return data.get(k)
        return None

    def _compose_executive_summary_from_sections(data: dict) -> str:
        sections = []

        panorama = _dict_to_text_block(_get_first(data, "panorama_general"))
        if panorama:
            sections.append(panorama)

        fortalezas = _dict_to_text_block(_get_first(
            data,
            "lectura_ejecutiva_de_fortalezas",
            "fortalezas"
        ))
        if fortalezas:
            sections.append("Fortalezas relevantes:\n" + fortalezas)

        brechas = _dict_to_text_block(_get_first(
            data,
            "lectura_ejecutiva_de_brechas",
            "brechas"
        ))
        if brechas:
            sections.append("Brechas relevantes:\n" + brechas)

        implicaciones = _dict_to_text_block(_get_first(
            data,
            "implicaciones_para_dirección_y_sostenibilidad_del_sistema",
            "implicaciones"
        ))
        if implicaciones:
            sections.append("Implicaciones para la dirección y la sostenibilidad del sistema:\n" + implicaciones)

        prioridades = _dict_to_text_block(_get_first(
            data,
            "prioridades_estratégicas_de_intervención",
            "prioridades"
        ))
        if prioridades:
            sections.append("Prioridades estratégicas de intervención:\n" + prioridades)

        conclusion = _dict_to_text_block(_get_first(
            data,
            "conclusión_ejecutiva_final",
            "conclusion"
        ))
        if conclusion:
            sections.append("Conclusión ejecutiva:\n" + conclusion)

        hallazgos = _dict_to_text_block(_get_first(data, "hallazgos_clave"))
        if hallazgos:
            sections.append("Hallazgos clave:\n" + hallazgos)

        return "\n\n".join([s for s in sections if s.strip()]).strip()

    def _fallback_executive_summary(company_name: str, chapter_results: dict) -> str:
        rows = []
        for k, v in (chapter_results or {}).items():
            try:
                pct = float(v.get("pct", 0) or 0)
            except Exception:
                pct = 0.0
            try:
                gap_pct = float(v.get("brecha_pct", 0) or 0)
            except Exception:
                gap_pct = 0.0

            rows.append({
                "capitulo": k,
                "pct": pct,
                "gap_pct": gap_pct,
                "gap_level": (v.get("brecha_nivel") or "").strip()
            })

        if not rows:
            return (
                f"Para la organización {company_name}, no se encontraron datos suficientes por capítulo "
                f"para construir el resumen ejecutivo del SGSI."
            )

        rows_sorted_best = sorted(rows, key=lambda x: x["pct"], reverse=True)
        rows_sorted_worst = sorted(rows, key=lambda x: x["pct"])

        top_strengths = rows_sorted_best[:3]
        top_gaps = rows_sorted_worst[:4]

        overall = round(sum(r["pct"] for r in rows) / max(1, len(rows)), 2)

        strengths_txt = ", ".join([f"{r['capitulo']} ({r['pct']}%)" for r in top_strengths])
        gaps_txt = ", ".join([f"{r['capitulo']} ({r['pct']}%)" for r in top_gaps])

        bullets = []
        bullets.append(f"• Madurez promedio estimada del SGSI: {overall}%.")
        bullets.append(f"• Dominios con mayor solidez: {strengths_txt}.")
        bullets.append(f"• Dominios con mayores brechas: {gaps_txt}.")
        bullets.append("• Las principales prioridades se concentran en fortalecer gobierno, operación, soporte y seguimiento.")
        bullets.append("• La sostenibilidad del SGSI depende de mantener evidencia verificable, revisión periódica y cierre de brechas.")

        texto = f"""
El análisis ejecutivo del SGSI para {company_name} evidencia un nivel de madurez promedio de {overall}%, lo que refleja un sistema con bases implementadas y avances relevantes en varios dominios, aunque todavía con brechas que requieren atención prioritaria para consolidar su sostenibilidad.

Desde una perspectiva directiva, los dominios con mejor desempeño son {strengths_txt}. Esto indica que la organización ya cuenta con capacidades relevantes en componentes esenciales del sistema, lo que representa una base favorable para sostener el cumplimiento y fortalecer la mejora continua.

No obstante, los capítulos con menor nivel de madurez son {gaps_txt}. Estas brechas muestran que aún existen debilidades que afectan la consistencia operativa del SGSI y que pueden limitar la eficacia del modelo de gobierno, la trazabilidad de la evidencia, el seguimiento del desempeño y la consolidación del enfoque de mejora.

En términos ejecutivos, estas diferencias de madurez indican que el sistema no debe evaluarse únicamente por sus fortalezas visibles, sino por la capacidad de operar de forma homogénea en todos los dominios relevantes. Cuando persisten brechas en capítulos clave, la organización puede mantener componentes bien estructurados, pero todavía con limitaciones para demostrar sostenibilidad, control y mejora continua de manera integral.

Para la dirección, la prioridad debe centrarse en cerrar las brechas de los dominios con menor desempeño, reforzar la disciplina de seguimiento y asegurar que las actividades del SGSI mantengan evidencia verificable, revisión periódica y control efectivo sobre su evolución. Esto es particularmente importante para sostener la capacidad de respuesta, el cumplimiento y la gobernanza del sistema.

En conclusión, el SGSI presenta una base de madurez relevante, pero aún requiere una intervención focalizada en los dominios más rezagados para asegurar un nivel de desempeño más equilibrado y sostenible. La dirección debe orientar sus esfuerzos a cerrar brechas, fortalecer la consistencia del sistema y mantener una visión integral de cumplimiento, operación y mejora continua.

Hallazgos clave:
{chr(10).join(bullets)}
        """.strip()

        return harden_no_conditionals(texto)

    try:
        data = ai_json_iso_generic(
            prompt=prompt,
            system_prompt=(
                "Devuelve SOLO JSON válido. "
                "Genera un resumen ejecutivo amplio, detallado y orientado a dirección. "
                "No agregues texto fuera del JSON."
            ),
            model_openrouter=OPENROUTER_MODEL_SGSI,
            max_tokens=3200
        )

        if not isinstance(data, dict):
            data = {}

        summary = (
            _clean_text(data.get("executive_summary"))
            or _clean_text(data.get("resumen_ejecutivo"))
            or _clean_text(data.get("summary"))
            or _clean_text(data.get("resumen"))
            or _clean_text(data.get("texto"))
        )

        if not summary:
            summary = _compose_executive_summary_from_sections(data)

        if not summary and isinstance(data, dict):
            bloques = []
            for _, v in data.items():
                txt = _dict_to_text_block(v)
                if txt and len(txt) > 40:
                    bloques.append(txt)
            summary = "\n\n".join(bloques).strip()

        summary = harden_no_conditionals(summary)

        if not summary:
            summary = _fallback_executive_summary(company_name, chapter_results)

        return {
            "executive_summary": summary
        }

    except Exception as e:
        print("DEBUG RESUMEN EJECUTIVO IA ERROR:", str(e))
        return {
            "executive_summary": _fallback_executive_summary(company_name, chapter_results)
        }

def ai_generate_item_analysis(company_name: str, control_id: str, item_block: dict) -> dict:
    """
    IA por CONTROL -> SOLO ITEMS (sin subitems)
    Devuelve:
      {
        "items": {
          "<ITEM_ID>": {
            "analisis_item": "texto auditoria-ready"
          }
        }
      }
    """
    client = get_openai_client()
    raw = "{}"

    items = (item_block.get("items") or {}) if isinstance(item_block, dict) else {}

    def summarize_counts(kpi: dict) -> str:
        c = (kpi or {}).get("counts") or {}
        return (
          f"madurez={kpi.get('madurez','')} "
          f"NO={c.get('NO',0)} PARCIAL={c.get('PARCIAL',0)} SIN_MARCAR={c.get('SIN_MARCAR',0)}"
        )

    items_lines = []
    for item_id, pack in items.items():
        ikpi = (pack.get("item_kpi") or {})
        items_lines.append(f"- ITEM {item_id}: {summarize_counts(ikpi)}")

    prompt = f"""
Actúa como consultor senior ISO/IEC 27001:2022 y auditor líder.
Empresa: {company_name}
Control: {control_id} - {control_title(control_id)}

Tengo resultados por Ítem (porcentaje y madurez según parámetros del sistema).
Necesito que para cada Ítem generes un análisis verificable y accionable, alineado a auditoría, que incluya:
- Intención del ítem (en términos de control interno y cumplimiento)
- Qué falta para llevarlo a Óptimo (proceso + evidencia + responsables + periodicidad + métricas)
- Qué mantener si ya está alto/óptimo (control de vigencia, revisión, medición)

IMPORTANTE:
- NO inventes hechos concretos de la empresa (nombres de herramientas, documentos reales, tecnologías).
- Redacta en modo auditoría (Se debe / Se requiere / Se evidencia / Se mantiene).
- NO repitas porcentajes en el texto final.

Items:
{chr(10).join(items_lines) if items_lines else "N/A"}

Devuelve SOLO JSON válido con esta estructura exacta:
{{
  "items": {{
    "<ITEM_ID>": {{
      "analisis_item": "texto"
    }}
  }}
}}
"""
    prompt += "\n\nIMPORTANT: Return ONLY valid JSON."

    try:
        resp = openai_call_with_retry(
            client,
            model=OPENROUTER_MODEL_SGSI,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        raw = (resp.choices[0].message.content or "{}").strip() or "{}"
        data = json.loads(raw)

        # Normaliza texto
        if isinstance(data.get("items"), dict):
            for k, v in data["items"].items():
                if isinstance(v, dict):
                    v["analisis_item"] = harden_no_conditionals(to_text(v.get("analisis_item")))

        return data
    except Exception as e:
        return {"items": {}, "error": str(e)}
    
def ai_generate_control_analysis(run, control_id: str, kpi: dict = None, items: list = None):
    """
    Genera análisis IA por control y lo guarda en run.control_ai_json.
    Compatible con OpenRouter y Ollama.
    El análisis profundo se concentra SOLO en:
    - estado_actual
    - estado_requerido
    - plan_accion_sugerido
    """
    if not run:
        raise RuntimeError("No se encontró la corrida de análisis ISO.")

    control_id = (control_id or "").strip().upper()
    if not control_id:
        raise RuntimeError("No se recibió el control a procesar.")

    if kpi is None or items is None:
        ctx = build_report_context(run)
        control_items = ctx.get("control_items", {}) or {}
        items = control_items.get(control_id, []) or []
        kpi = compute_control_kpis(control_id, items)

    if not isinstance(items, list):
        items = []

    if not isinstance(kpi, dict):
        kpi = {}

    soporte = build_control_support_text(items, max_lines=80)
    pct = float(kpi.get("pct", 0) or 0)
    madurez = (kpi.get("madurez") or "").strip()
    group = (kpi.get("group") or "").strip()
    total = int(kpi.get("total", 0) or 0)
    done = int(kpi.get("done", 0) or 0)
    counts = kpi.get("counts") or {}

    prompt = f"""
Eres un consultor senior y auditor líder experto en ISO/IEC 27001:2022 y SGSI.

Debes generar un análisis PROFUNDO del control evaluado, pero SOLO usando estos tres campos:
- estado_actual
- estado_requerido
- plan_accion_sugerido

DATOS DEL CONTROL
- Organización: {run.company_name}
- Control: {control_id}
- Grupo: {group}
- Nivel de madurez: {madurez}
- Porcentaje de cumplimiento: {pct:.2f}%
- Cumplidas: {done}
- Total aplicables: {total}
- Conteos: SI={counts.get("SI",0)}, PARCIAL={counts.get("PARCIAL",0)}, NO={counts.get("NO",0)}, SIN_MARCAR={counts.get("SIN_MARCAR",0)}

DETALLE DE SOPORTE
{soporte}

INSTRUCCIONES OBLIGATORIAS
1. El estado_actual debe ser profundo, técnico y explicativo.
2. El estado_actual debe describir qué está implementado, qué está parcial, qué brechas persisten y qué implicación tienen.
3. El estado_requerido debe ser profundo, técnico y orientado a auditoría.
4. El estado_requerido debe explicar cómo debe operar el control en un nivel sólido u óptimo.
5. El plan_accion_sugerido debe ser detallado y venir numerado, mínimo 3 pasos y máximo 6.
6. No uses markdown.
7. No incluyas texto fuera del JSON.
8. No uses lenguaje condicional.
9. No respondas con etiquetas cortas como “Gestionado”, “Implementado” o frases de una sola línea.

EXTENSIÓN ESPERADA
- estado_actual: entre 80 y 180 palabras
- estado_requerido: entre 80 y 180 palabras
- plan_accion_sugerido: entre 3 y 6 acciones numeradas

Devuelve SOLO JSON válido con esta estructura exacta:
{{
  "estado_actual": "texto profundo",
  "estado_requerido": "texto profundo",
  "plan_accion_sugerido": "1. ...\\n2. ...\\n3. ..."
}}
""".strip()

    provider = (get_ai_provider() or "openrouter").strip().lower()

    raw = ""

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

        resp = requests.post(
            f"{base_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.15
                }
            },
            timeout=300
        )
        resp.raise_for_status()

        payload = resp.json() or {}

        raw = (payload.get("response") or "").strip()
        if not raw:
            raw = (payload.get("message") or "").strip()

        if not raw:
            raise RuntimeError(f"Ollama respondió sin contenido. Payload: {str(payload)[:500]}")

    # =========================
    # OPENROUTER
    # =========================
    else:
        api_key = (get_openrouter_api_key() or "").strip()
        if not api_key:
            raise RuntimeError("No hay OPENROUTER_API_KEY configurada en Administración.")

        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "https://sgsi.local",
                "X-Title": "SGSI ISO 27001 Analyzer"
            }
        )

        resp = client.chat.completions.create(
            model="openai/gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "Devuelve SOLO JSON válido. No agregues texto fuera del JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.15,
            max_tokens=1800,
            response_format={"type": "json_object"},
        )

        raw = (resp.choices[0].message.content or "").strip()
        if not raw:
            raise RuntimeError("OpenRouter respondió sin contenido.")

    data = _extraer_json_objeto(raw)
    data = ensure_control_ai_fields(data, kpi)

    print("DEBUG IA ISO CONTROL - DATA FINAL:", data)

    actual = {}
    try:
        actual = json.loads(run.control_ai_json or "{}")
        if not isinstance(actual, dict):
            actual = {}
    except Exception:
        actual = {}

    actual[control_id] = {
        "estado_actual": data.get("estado_actual", ""),
        "estado_requerido": data.get("estado_requerido", ""),
        "plan_accion_sugerido": data.get("plan_accion_sugerido", "")
    }

    run.control_ai_json = json.dumps(actual, ensure_ascii=False)
    return actual[control_id] 

def build_unified_control_analysis(cid: str, kpi: dict, items: list) -> dict:
    """
    Devuelve un análisis consistente por control, estructurado y dependiente del nivel de madurez.
    NO usa IA. Usa CONTROL_STRATEGY + preguntas en brecha.
    """
    cid_u = (cid or "").strip().upper()
    cfg = CONTROL_STRATEGY.get(cid_u, {})

    mad = (kpi.get("madurez") or "").strip()
    pct = float(kpi.get("pct", 0) or 0)
    c = (kpi.get("counts") or {})
    no = int(c.get("NO", 0) or 0)
    parcial = int(c.get("PARCIAL", 0) or 0)
    sm = int(c.get("SIN_MARCAR", 0) or 0)
    total = int(kpi.get("total", 0) or 0)

    intent = cfg.get("intent", "Asegurar la implementación efectiva del control según ISO/IEC 27001:2022.")
    must_have = cfg.get("must_have", [])
    evidence = cfg.get("evidence", [])
    roles = cfg.get("roles", [])
    cadence = cfg.get("cadence", "")
    metrics = cfg.get("kpis", [])

    def _norm_plain(s: str) -> str:
        s = (s or "").strip().lower()
        s = unicodedata.normalize("NFD", s)
        s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
        return s

    mad_n = _norm_plain(mad)

    # Top brechas
    gaps = [x for x in (items or []) if x.get("status") in ("NO", "PARCIAL", "SIN_MARCAR")]
    gaps = sorted(gaps, key=lambda x: float(x.get("brecha_pct", 100) or 100), reverse=True)[:8]
    brechas_top = []
    for g in gaps:
        q = (g.get("requisito") or "").strip()
        st = (g.get("status") or "").strip()
        if q:
            brechas_top.append(f"• [{st}] {q}")

    # Estado por madurez (prioriza la etiqueta; fallback por pct)
    if mad_n == "optimo" or pct >= 80:
        estado = "Óptimo"
        diagnostico = "El control opera de forma consistente, con trazabilidad y evidencia vigente."
        foco = "Sostener la disciplina: vigencia documental, revisión periódica, métricas y mejora continua."
        acciones = [
            "Mantener evidencias vigentes con control de cambios y versionado.",
            "Ejecutar revisión periódica y registrar decisiones/acciones.",
            "Asegurar medición del control (KPIs) y reporte a comité/dirección."
        ]
    elif mad_n == "gestionado" or pct >= 60:
        estado = "Gestionado"
        diagnostico = "El control está implementado y es repetible, pero aún presenta brechas de consistencia y evidencia."
        foco = "Cerrar pendientes (PARCIAL/SIN_MARCAR) y fortalecer trazabilidad y medición."
        acciones = [
            "Convertir PARCIAL en SI con evidencia verificable (registros, actas, aprobaciones).",
            "Resolver SIN_MARCAR: completar evaluación y evidencia.",
            "Alinear responsables y cadencia de revisión, con KPIs."
        ]
    elif mad_n == "en desarrollo" or pct >= 40:
        estado = "En desarrollo"
        diagnostico = "El control existe parcialmente; la evidencia es inconsistente y la operación no es homogénea."
        foco = "Estandarizar proceso mínimo, responsables y evidencia base."
        acciones = [
            "Definir el proceso del control (entradas/actividades/salidas) y un responsable.",
            "Crear evidencia mínima: procedimiento + formatos/registros + aprobaciones.",
            "Implementar ciclo de revisión (mensual/trimestral) y seguimiento de hallazgos."
        ]
    else:
        estado = "Inicial"
        diagnostico = "El control no está implementado o es ad-hoc; existe alto riesgo de incumplimiento y falta de evidencia."
        foco = "Implementación prioritaria: diseño + operación + evidencia mínima inmediata."
        acciones = [
            "Definir política/procedimiento base del control y asignar responsables.",
            "Implementar evidencias iniciales (registros, listas, matrices, actas) desde el primer ciclo.",
            "Establecer un plan de cierre de NO/SIN_MARCAR con fechas y seguimiento."
        ]

    return {
        "estado": estado + (f" ({mad})" if mad else ""),
        "intencion": intent,
        "diagnostico": diagnostico,
        "foco": foco,
        "impacto": "Se identifican brechas en requisitos aplicables que requieren cierre y evidencia verificable.",
        "componentes_minimos": must_have,
        "acciones_clave": acciones,
        "evidencias_esperadas": evidence,
        "roles_clave": roles,
        "cadencia": cadence,
        "metricas": metrics,
        "brechas_top": brechas_top,
    }


# ==========================
# BADGES
# ==========================
def score_badge(pct: float) -> str:
    if pct >= 80:
        return "bg-success"              # Verde
    if pct >= 60:
        return "bg-primary"              # Azul
    if pct >= 40:
        return "bg-warning text-dark"    # 🟡 Amarillo
    return "bg-purple text-white"        # 🟣 Morado


def gap_badge(level: str) -> str:
    lvl = (level or "").strip().lower()
    if lvl == "bajo":
        return "bg-success"
    if lvl == "medio":
        return "bg-warning text-dark"
    if lvl == "alto":
        return "bg-purple text-white"
    if lvl in ("critico", "crítico"):
        return "bg-dark"
    return "bg-secondary"


# ============================================================
# CONTROLES POR CAPÍTULO
# ============================================================
def _status_counts(items: list) -> dict:
    c = {"SI": 0, "PARCIAL": 0, "NO": 0, "SIN_MARCAR": 0, "NA": 0}
    for it in items or []:
        st = (it.get("status") or "").strip()
        if st in c:
            c[st] += 1
        else:
            c["SIN_MARCAR"] += 1
    return c

def compute_control_kpis(cid: str, items: list) -> dict:
    applicable = [x for x in (items or []) if x.get("applicable", True) and (x.get("status") != "NA")]
    total = len(applicable)

    if total == 0:
        pct = 0.0
        mad = get_maturity_label_for_pct(0)
        done = 0
        counts = _status_counts(items or [])
    else:
        score_sum = sum(int(x.get("score", 0) or 0) for x in applicable)
        pct = round((score_sum / (total * 100) * 100) if total else 0.0, 2)
        mad = get_maturity_label_for_pct(pct)
        done = sum(1 for x in applicable if (x.get("status") == "SI"))
        counts = _status_counts(applicable)

    # ✅ NUEVO: brecha por control (100 - pct) + nivel/interpretación parametrizados
    gap_info = gap_from_maturity_pct(pct)

    return {
        "control_id": cid,
        "title": control_title(cid),
        "pct": pct,
        "madurez": mad,
        "total": total,
        "done": done,
        "counts": counts,

        # ✅ NUEVO
        "brecha_pct": gap_info["gap_pct"],
        "brecha_nivel": gap_info["nivel_brecha"],
        "brecha_interp": gap_info["interpretacion"],
    }

def build_control_summary_text(kpi: dict) -> str:
    pct = float(kpi.get("pct", 0) or 0)
    mad = (kpi.get("madurez") or "").strip()
    total = int(kpi.get("total", 0) or 0)
    done = int(kpi.get("done", 0) or 0)
    c = kpi.get("counts") or {}
    parcial = int(c.get("PARCIAL", 0) or 0)
    no = int(c.get("NO", 0) or 0)
    sm = int(c.get("SIN_MARCAR", 0) or 0)

    if pct >= 80:
        estado = "Óptimo / muy sólido"
    elif pct >= 60:
        estado = "Gestionado / consistente"
    elif pct >= 40:
        estado = "En desarrollo / parcial"
    else:
        estado = "Débil / prioritario"

    return (
        f"Estado: {estado}. "
        + f"Cumplimiento: {pct}%"
        + (f" ({mad}). " if mad else ". ")
        + "Se identifican brechas que requieren cierre y evidencias verificables."
    )


def build_control_detail_text(kpi: dict, items: list) -> str:
    pct = float(kpi.get("pct", 0) or 0)
    mad = (kpi.get("madurez") or "").strip()
    c = kpi.get("counts") or {}
    parcial = int(c.get("PARCIAL", 0) or 0)
    no = int(c.get("NO", 0) or 0)
    sm = int(c.get("SIN_MARCAR", 0) or 0)

    def brecha_val(x):
        bp = x.get("brecha_pct", None)
        if bp is None:
            return -1
        try:
            return float(bp)
        except Exception:
            return 0.0

    gaps_sorted = sorted(
        [x for x in (items or []) if x.get("status") in ("NO", "PARCIAL", "SIN_MARCAR")],
        key=brecha_val,
        reverse=True
    )
    top = gaps_sorted[:8]
    bullets = []
    for it in top:
        req = (it.get("requisito") or "").strip()
        st = (it.get("status") or "").strip()
        com = (it.get("comment") or "").strip()
        prc = (it.get("procesos") or "").strip()
        extra = []
        if com:
            extra.append(f"coment: {com}")
        if prc:
            extra.append(f"proc: {prc}")
        extra_txt = (" (" + " | ".join(extra) + ")") if extra else ""
        if req:
            bullets.append(f"• [{st}] {req}{extra_txt}")

    if pct >= 80:
        txt = (
            f"El control se considera sólido/óptimo porque la mayoría de requisitos están en 'SI' "
            f"y los hallazgos residuales son menores (PARCIAL={parcial}, NO={no}, SIN MARCAR={sm}). "
            f"Para sostener el nivel {mad or ''}, asegure evidencia vigente, revisión periódica, "
            f"y trazabilidad (responsables, aprobación, métricas y seguimiento)."
        )
        if bullets:
            txt += "\n\nPuntos a vigilar (mejora continua):\n" + "\n".join(bullets)
        return txt.strip()

    txt = (
        f"Para llevar este control a un nivel óptimo, debes cerrar primero los ítems en 'NO' y "
        f"convertir los 'PARCIAL' en 'SI'. También se deben resolver los 'SIN MARCAR' porque por política "
        f"se tratan como brecha.\n"
        f"Impacto actual: NO={no}, PARCIAL={parcial}, SIN MARCAR={sm}."
    )
    if bullets:
        txt += "\n\nBrechas principales (basadas en tus preguntas):\n" + "\n".join(bullets)
    else:
        txt += "\n\nNo hay detalle de preguntas en brecha para este control (revisar instrumento)."
    return txt.strip()


def build_control_strategic_text(cid: str, kpi: dict, items: list) -> dict:
    cid_u = (cid or "").strip().upper()
    cfg = CONTROL_STRATEGY.get(cid_u, {})
    intent = cfg.get("intent", "Asegurar la implementación efectiva del control según ISO 27001.")
    must_have = cfg.get("must_have", [])
    evidence = cfg.get("evidence", [])
    roles = cfg.get("roles", [])
    cadence = cfg.get("cadence", "")
    kpis = cfg.get("kpis", [])

    c = (kpi.get("counts") or {})
    no = int(c.get("NO", 0) or 0)
    parcial = int(c.get("PARCIAL", 0) or 0)
    sm = int(c.get("SIN_MARCAR", 0) or 0)
    total = int(kpi.get("total", 0) or 0)
    pct = float(kpi.get("pct", 0) or 0)
    mad = (kpi.get("madurez") or "").strip()

    gaps = [x for x in (items or []) if x.get("status") in ("NO", "PARCIAL", "SIN_MARCAR")]
    gaps = sorted(gaps, key=lambda x: float(x.get("brecha_pct", 100) or 100), reverse=True)[:6]
    top_gap_questions = []
    for it in gaps:
        q = (it.get("requisito") or "").strip()
        st = (it.get("status") or "").strip()
        if q:
            top_gap_questions.append(f"• [{st}] {q}")

    if pct >= 80:
        estado = "Óptimo"
        foco = "Sostener el control: disciplina operativa, evidencia vigente y mejora continua."
        riesgo = "Riesgo residual controlado; riesgo principal: perder vigencia por falta de revisión."
    elif pct >= 60:
        estado = "Gestionado"
        foco = "Cerrar consistencia: convertir PARCIAL/SIN_MARCAR en evidencia verificable y repetible."
        riesgo = "Riesgo moderado por ejecución desigual o falta de trazabilidad."
    elif pct >= 40:
        estado = "En desarrollo"
        foco = "Estandarizar: proceso, dueños, evidencia mínima y ciclo de revisión."
        riesgo = "Riesgo alto por brechas operativas que pueden materializar incidentes o incumplimientos."
    else:
        estado = "Crítico"
        foco = "Implementación prioritaria: definir y operar el control con evidencias básicas cuanto antes."
        riesgo = "Riesgo crítico de incumplimiento ISO y exposición material a incidentes."

    acciones = []
    if no or parcial or sm:
        acciones.append("Formalizar proceso: entradas, actividades, salidas, responsable y aprobación.")
        acciones.append("Crear/actualizar evidencia mínima con versionado y trazabilidad.")
        acciones.append("Definir revisión periódica y seguimiento (acciones, responsables, fechas).")
        acciones.append("Incorporar métricas y revisión por la dirección cuando aplique.")
    else:
        acciones.append("Mantener evidencia vigente y revisiones periódicas (no solo documentos creados).")
        acciones.append("Mejora continua: lecciones aprendidas, auditorías, KPIs y ajustes por cambios.")

    return {
        "estado": estado + (f" ({mad})" if mad else ""),
        "intencion": intent,
        "riesgo": riesgo,
        "foco": foco,
        "faltantes": [f for f in must_have],
        "acciones_estrategicas": acciones,
        "evidencias_esperadas": evidence,
        "roles_clave": roles,
        "cadencia": cadence,
        "metricas": kpis,
        "brechas_top": top_gap_questions,
        "impacto_operativo": "Se identifican brechas operativas en el control que requieren cierre, trazabilidad y evidencia."
    }


def render_control_items_table(items: list) -> str:
    if not items:
        return "<div class='text-muted small'>Sin preguntas registradas para este control.</div>"

    items_sorted = sorted(items, key=lambda x: int(x.get("row", 0) or 0))
    tr = ""
    for it in items_sorted[:500]:
        st = display_estado(it.get("status"))
        com = (it.get("comment") or "").strip()
        prc = (it.get("procesos") or "").strip()

        if st == "":
            com_vis = ""
            prc_vis = ""
        else:
            com_vis = com if com else "ninguno"
            prc_vis = prc if prc else "ninguno"

        bp = it.get("brecha_pct", None)
        bp_txt = "" if bp is None else f"{float(bp):.0f}%"
        blevel = (it.get("brecha_nivel") or "").strip()
        binterp = (it.get("brecha_interp") or "").strip()

        tr += f"""
        <tr class="cell-small">
          <td class="text-muted">{xml_escape(it.get("sheet",""))}</td>
          <td class="text-muted">{xml_escape(st)}</td>
          <td class="wrap" style="min-width:420px;">{xml_escape(it.get("requisito",""))}</td>
          <td class="wrap" style="min-width:220px;">{xml_escape(com_vis)}</td>
        </tr>
        """

    return f"""
    <div class="table-responsive" style="max-height: 420px; overflow:auto;">
      <table class="table table-sm table-striped align-middle table-tight">
        <thead>
          <tr>
            <th style="min-width:160px;">Capítulo</th>
            <th style="min-width:90px;">Estado</th>
            <th>Pregunta/Requisito</th>
            <th>Comentarios</th>
          </tr>
        </thead>
        <tbody>{tr if tr else "<tr><td colspan='4' class='text-muted'>Sin datos.</td></tr>"}</tbody>
      </table>
    </div>
    """


# ============================================================
# NUEVO: AGREGACIÓN POR ÍTEM/SUBÍTEM
# ============================================================
def compute_kpis_for_bucket(bucket_id: str, questions: list) -> dict:
    applicable = [x for x in (questions or []) if x.get("applicable", True) and (x.get("status") != "NA")]
    total = len(applicable)
    if total == 0:
        return {
            "id": bucket_id,
            "pct": 0.0,
            "madurez": get_maturity_label_for_pct(0),
            "total": 0,
            "done": 0,
            "counts": _status_counts([]),
        }

    score_sum = sum(int(x.get("score", 0) or 0) for x in applicable)
    pct = round((score_sum / (total * 100) * 100) if total else 0.0, 2)
    done = sum(1 for x in applicable if (x.get("status") == "SI"))
    return {
        "id": bucket_id,
        "pct": pct,
        "madurez": get_maturity_label_for_pct(pct),
        "total": total,
        "done": done,
        "counts": _status_counts(applicable),
    }


def build_item_results(control_items: dict) -> dict:
    out = {}

    for cid, questions in (control_items or {}).items():
        cid_u = (cid or "").strip()
        if not cid_u:
            continue

        control_kpi = compute_control_kpis(cid_u, questions)

        item_map = {}
        for q in (questions or []):
            item_id = (q.get("item_id") or "").strip()
            sub_id  = (q.get("subitem_id") or "").strip()

            if not item_id:
                ref = q.get("ref", "")
                sh = q.get("sheet", "")
                item_id2, sub_id2 = get_item_subitem_ids(sh, ref, cid_u)
                item_id = (item_id2 or cid_u).strip()
                sub_id = (sub_id2 or "").strip()

            item_id = (item_id or cid_u).strip()

            item_map.setdefault(item_id, {"questions": [], "subitems": {}})
            item_map[item_id]["questions"].append(q)

            if sub_id:
                item_map[item_id]["subitems"].setdefault(sub_id, [])
                item_map[item_id]["subitems"][sub_id].append(q)

        items_out = {}
        for item_id, pack in item_map.items():
            item_kpi = compute_kpis_for_bucket(item_id, pack["questions"])

            subs_out = {}
            for sub_id, qlist in (pack.get("subitems") or {}).items():
                subs_out[sub_id] = {"subitem_kpi": compute_kpis_for_bucket(sub_id, qlist)}

            items_out[item_id] = {"item_kpi": item_kpi, "subitems": subs_out}

        out[cid_u] = {"control_kpi": control_kpi, "items": items_out}

    return out


def fallback_ai_para_optimo(kpi: dict) -> str:
    pct = float((kpi or {}).get("pct", 0) or 0)

    if pct >= 80:
        return "" # ✅ no mostrar texto por defecto cuando está Óptimo
    if pct >= 60:
        return "" # ✅ no mostrar texto por defecto cuando está Óptimo
    if pct >= 40:
        return "" # ✅ no mostrar texto por defecto cuando está Óptimo
    return "" # ✅ no mostrar texto por defecto cuando está Óptimo


def render_items_ui_only(cid: str, item_block: dict, ai_block: dict) -> str:
    """
    UI SOLO ITEMS. No renderiza subitems.
    """
    items = (item_block.get("items") or {})
    ai_items = (ai_block.get("items") or {})

    if not items:
        return "<div class='text-muted small'>Este control no tiene Ítems identificables.</div>"

    def _title_from_questions(qlist: list, fallback: str = "") -> str:
        for q in (qlist or []):
            t = (q.get("requisito") or "").strip()
            if t and not t.lower().startswith(("promedio", "nota")):
                return t[:160] + ("…" if len(t) > 160 else "")
        return fallback

    html = ""
    for item_id, pack in items.items():
        ikpi = (pack.get("item_kpi") or {})
        ibadge = score_badge(float(ikpi.get("pct", 0) or 0))
        imad = (ikpi.get("madurez") or "").strip()

        item_questions = (pack.get("questions") or [])
        item_title = _title_from_questions(item_questions, fallback="(Sin título de Ítem)")

        ai_i = ai_items.get(item_id, {}) if isinstance(ai_items, dict) else {}
        analisis = (ai_i.get("analisis_item") or "").strip()

        if not analisis:
            analisis = "<span class='text-muted'>Aún no se ha generado IA para este ítem.</span>"
        else:
            analisis = xml_escape(analisis).replace("\\n", "<br/>")

        html += f"""
        <div class="border rounded-3 p-3 mb-3" style="background: rgba(255,255,255,.10);">
          <div class="d-flex flex-wrap align-items-center gap-2">
            <div class="fw-bold">Ítem: {xml_escape(item_id)}</div>
            <span class="badge {ibadge}">{ikpi.get("pct",0)}%</span>
            {"<span class='text-muted small'>(" + xml_escape(imad) + ")</span>" if imad else ""}
          </div>

          <div class="small text-muted mt-1">{xml_escape(item_title)}</div>

          <div class="mt-2">
            <div class="small fw-semibold">🧠 Análisis IA (Ítem)</div>
            <div class="small wrap text-muted">{analisis}</div>
          </div>
        </div>
        """

    return html

# ==========================
# UI (Bootstrap + Modal progreso IA)
# ==========================
BASE_HTML = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{{ title }}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body {
      background: radial-gradient(1200px 700px at 20% -10%, rgba(13,110,253,.25), transparent 55%),
                  radial-gradient(900px 600px at 90% 0%, rgba(25,135,84,.20), transparent 55%),
                  #0b1b2b;
      color: #e9f1fb;
    }
    .card { border-radius: 18px; border: 0; }
    .card-soft { background: rgba(255,255,255,.92); color:#0b1b2b; }
    .muted { color: rgba(233,241,251,.80); }
    .wrap { white-space: normal; word-break: break-word; }
    .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }
    .pill { border-radius: 999px; }
    .shadow-soft { box-shadow: 0 12px 40px rgba(0,0,0,.18); }
    .progress-h { height: 10px; }
    .sticky-top2 { position: sticky; top: 12px; z-index: 10; }
    .kpi { font-size: 28px; font-weight: 800; line-height: 1; }
    table td, table th { vertical-align: top !important; }
    .table thead th { position: sticky; top: 0; z-index: 2; background: rgba(255,255,255,.97); }
    .table-tight td { padding-top: .45rem; padding-bottom: .45rem; }
    .cell-small { font-size: 12px; }
    .btn-purple{
      background-color:#6f42c1 !important;
      border-color:#6f42c1 !important;
      color:#fff !important;
    }
    .btn-purple:hover{
      background-color:#5a35a8 !important;
      border-color:#5a35a8 !important;
      color:#fff !important;

  </style>
</head>
<body>
<div class="container py-4">
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      {% for cat, msg in messages %}
        <div class="alert alert-{{ cat }} shadow-soft">{{ msg }}</div>
      {% endfor %}
    {% endif %}
  {% endwith %}
  {{ content|safe }}
</div>

<div class="modal fade" id="progressModal" tabindex="-1" aria-hidden="true">
  <div class="modal-dialog modal-dialog-centered">
    <div class="modal-content" style="border-radius:18px;">
      <div class="modal-header">
        <h5 class="modal-title">Procesando análisis IA…</h5>
      </div>
      <div class="modal-body">
        <div class="d-flex justify-content-between small text-muted">
          <div id="pmMsg">Generando…</div>
          <div id="pmPct">0%</div>
        </div>
        <div class="progress mt-2" style="height:12px;">
          <div id="pmBar" class="progress-bar progress-bar-striped progress-bar-animated bg-purple" style="width:0%;"></div>
        </div>
        <div class="mt-3 small text-muted">
          Esto puede tardar unos segundos (dependiendo del tamaño del instrumento y del modelo).
        </div>
      </div>
    </div>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>

<script>
  function attachProgress(formId, boxId, barId, pctId, msgId, msgText) {
    const form = document.getElementById(formId);
    const box  = document.getElementById(boxId);
    const bar  = document.getElementById(barId);
    const pct  = document.getElementById(pctId);
    const msg  = document.getElementById(msgId);
    if (!form || !box || !bar || !pct || !msg) return;

    let timer = null;
    let p = 0;

    function setP(v) {
      p = Math.max(0, Math.min(95, v));
      bar.style.width = p + '%';
      pct.textContent = p + '%';
    }

    form.addEventListener('submit', function() {
      box.style.display = 'block';
      msg.textContent = msgText;
      setP(5);

      timer = setInterval(() => {
        if (p < 70) setP(p + 6);
        else if (p < 88) setP(p + 2);
        else setP(90);
      }, 220);
    });

    window.addEventListener('pageshow', () => {
      if (timer) clearInterval(timer);
      box.style.display = 'none';
      bar.style.width = '0%';
      pct.textContent = '0%';
    });
  }

  function attachProgressModal(formId, modalId, barId, pctId, msgId, msgText) {
    const form = document.getElementById(formId);
    const modalEl = document.getElementById(modalId);
    const bar  = document.getElementById(barId);
    const pct  = document.getElementById(pctId);
    const msg  = document.getElementById(msgId);
    if (!form || !modalEl || !bar || !pct || !msg) return;

    let timer = null;
    let p = 0;

    const modal = bootstrap.Modal.getOrCreateInstance(modalEl, {
      backdrop: 'static',
      keyboard: false
    });

    function setP(v) {
      p = Math.max(0, Math.min(95, v));
      bar.style.width = p + '%';
      pct.textContent = p + '%';
    }

    function reset() {
      if (timer) clearInterval(timer);
      timer = null;
      p = 0;
      bar.style.width = '0%';
      pct.textContent = '0%';
      msg.textContent = 'Generando…';
    }

    form.addEventListener('submit', function(e) {
      e.preventDefault();

      const btn = form.querySelector('button[type="submit"]');
      if (btn) btn.disabled = true;

      reset();
      msg.textContent = msgText;
      setP(8);
      modal.show();

      timer = setInterval(() => {
        if (p < 65) setP(p + 7);
        else if (p < 85) setP(p + 3);
        else setP(90);
      }, 240);

      setTimeout(() => { form.submit(); }, 80);
    });

    window.addEventListener('pageshow', () => {
      reset();
      try { modal.hide(); } catch(e) {}
      const btn = form.querySelector('button[type="submit"]');
      if (btn) btn.disabled = false;
    });
  }
</script>
</body>
</html>
"""


# ==========================
# ROUTES - PARÁMETROS
# ==========================
@madurez_bp.route("/report/<int:run_id>/nist", methods=["GET"])
@login_required
def report_nist(run_id: int):
    run = AnalysisRun.query.get_or_404(run_id)

    nist = calcular_nist_desde_iso(run.id) or {}
    detalle = nist.get("detalle") or {}
    nivel_general = nist.get("nivel_general", 0)
    error = (nist.get("error") or "").strip()

    # Orden recomendado NIST (ajusta si tu mapeo usa otros nombres)
    orden_funciones = ["GOVERN", "IDENTIFY", "PROTECT", "DETECT", "RESPOND", "RECOVER"]

    # normaliza llaves a mayúscula para ordenar sin perder el texto original
    funcs = list(detalle.keys())
    def sort_func(f):
        fu = (f or "").strip().upper()
        return (orden_funciones.index(fu) if fu in orden_funciones else 999, fu)

    funcs_sorted = sorted(funcs, key=sort_func)

    def badge_by_score(x):
        try:
            v = float(x)
        except Exception:
            v = 0
        # escala simple (si manejas 0-5 o 0-100, ajusta aquí)
        if v >= 4:
            return "bg-success"
        if v >= 3:
            return "bg-primary"
        if v >= 2:
            return "bg-warning text-dark"
        return "bg-danger"

    # ==========================
    # Construye HTML por función (PRESENTABLE)
    # ==========================
    blocks = ""

    def _to_float(x, default=0.0):
        try:
            return float(x)
        except Exception:
            return default

    def badge_by_score_0_5(score):
        v = _to_float(score, 0.0)
        if v >= 4.0:
            return "bg-success"
        if v >= 3.0:
            return "bg-primary"
        if v >= 2.0:
            return "bg-warning text-dark"
        return "bg-danger"

    def badge_by_pct(pct):
        p = _to_float(pct, 0.0)
        if p >= 85: return "bg-success"
        if p >= 70: return "bg-primary"
        if p >= 50: return "bg-warning text-dark"
        return "bg-danger"

    for f in funcs_sorted:
        cats = detalle.get(f, {}) or {}

        # Promedio de la función usando score (0..5)
        vals = []
        for _, cat_obj in cats.items():
            if isinstance(cat_obj, dict):
                vals.append(_to_float(cat_obj.get("score"), 0.0))
            else:
                vals.append(_to_float(cat_obj, 0.0))
        avg_f = round(sum(vals) / len(vals), 2) if vals else 0.0
        avg_f_pct = round(avg_f * 20.0, 2)  # 0..100

        # Acordeón por categorías
        cat_acc = ""
        safe_f = re.sub(r"[^a-zA-Z0-9_]+", "_", f"nist_{f}")

        for cat, cat_obj in sorted(cats.items(), key=lambda t: (t[0] or "").upper()):
            # Soporta tanto dict nuevo como float viejo
            if isinstance(cat_obj, dict):
                score = _to_float(cat_obj.get("score"), 0.0)
                items = cat_obj.get("items") or []
                faltantes = cat_obj.get("faltantes") or []
                no_eval = cat_obj.get("no_evaluadas") or []
            else:
                score = _to_float(cat_obj, 0.0)
                items, faltantes, no_eval = [], [], []

            score_pct = round(score * 20.0, 2)

            safe_cat = re.sub(r"[^a-zA-Z0-9_]+", "_", f"{safe_f}_{cat}")

            # Tabla items (refs mapeadas con % y brecha)
            rows_items = ""
            for it in (items or []):
                ref = (it.get("ref") or "").strip()
                tipo = (it.get("tipo") or "").strip()
                pct = _to_float(it.get("pct"), 0.0)
                gap = _to_float(it.get("gap"), 0.0)
                is_fail = pct < 100.0

                rows_items += f"""
                <tr class="{'table-warning' if is_fail else ''}">
                  <td class="fw-semibold">{xml_escape(ref)}</td>
                  <td class="text-muted">{xml_escape(tipo)}</td>
                  <td style="width:160px">
                    <span class="badge {badge_by_pct(pct)}">{pct:.2f}%</span>
                  </td>
                  <td style="width:140px">
                    <span class="badge bg-dark">{gap:.2f}%</span>
                  </td>
                </tr>
                """

            if not rows_items:
                rows_items = "<tr><td colspan='4' class='text-muted'>Sin referencias ISO mapeadas/evaluadas para esta categoría.</td></tr>"

            # Resumen faltantes (solo <100)
            falt_txt = ""
            if faltantes:
                falt_txt = f"""
                <div class="mt-2 small">
                  <span class="badge bg-danger">Faltantes</span>
                  <span class="text-muted">Elementos por debajo de 100%</span>
                </div>
                """

            # No evaluadas (refs que están en el Excel pero no existen en el run ISO)
            noeval_txt = ""
            if no_eval:
                li = "".join([f"<li class='small text-muted'>{xml_escape(str(x))}</li>" for x in no_eval[:200]])
                noeval_txt = f"""
                <div class="mt-3">
                  <div class="small fw-semibold">No evaluadas (no existen en el run ISO)</div>
                  <ul class="mb-0">{li}</ul>
                </div>
                """

            cat_acc += f"""
            <div class="accordion-item">
              <h2 class="accordion-header" id="h_{safe_cat}">
                <button class="accordion-button collapsed" type="button"
                        data-bs-toggle="collapse" data-bs-target="#c_{safe_cat}">
                  <div class="d-flex flex-wrap gap-2 align-items-center w-100">
                    <div class="fw-bold">{xml_escape(str(cat))}</div>
                    <div class="ms-auto d-flex align-items-center gap-2">
                      <span class="badge {badge_by_score_0_5(score)}">{score:.2f}/5</span>
                      <span class="badge {badge_by_pct(score_pct)}">{score_pct:.2f}%</span>
                    </div>
                  </div>
                </button>
              </h2>

              <div id="c_{safe_cat}" class="accordion-collapse collapse">
                <div class="accordion-body">

                  <div class="row g-2">
                    <div class="col-md-4">
                      <div class="card card-soft p-3">
                        <div class="fw-semibold small text-muted">Puntaje categoría</div>
                        <div class="display-6 mb-0">{score:.2f}/5</div>
                        <div class="text-muted small">Equivale a {score_pct:.2f}%</div>
                      </div>
                    </div>
                    <div class="col-md-8">
                      <div class="card card-soft p-3">
                        <div class="fw-semibold small text-muted">Detalle por referencia ISO (lo que baja el %)</div>
                        {falt_txt}
                        <div class="table-responsive mt-2">
                          <table class="table table-sm table-hover align-middle mb-0">
                            <thead class="table-dark">
                              <tr>
                                <th>Referencia</th>
                                <th>Tipo</th>
                                <th>% actual</th>
                                <th>Brecha</th>
                              </tr>
                            </thead>
                            <tbody>
                              {rows_items}
                            </tbody>
                          </table>
                        </div>
                        {noeval_txt}
                      </div>
                    </div>
                  </div>

                </div>
              </div>
            </div>
            """

        blocks += f"""
        <div class="card card-soft p-3 mb-3">
          <div class="d-flex flex-wrap justify-content-between align-items-center gap-2">
            <div class="fw-bold">Función: {xml_escape(str(f))}</div>
            <div class="small text-muted">Promedio función</div>
            <span class="badge {badge_by_score_0_5(avg_f)}">{avg_f:.2f}/5</span>
            <span class="badge {badge_by_pct(avg_f_pct)}">{avg_f_pct:.2f}%</span>
          </div>

          <div class="accordion mt-3" id="acc_{safe_f}">
            {cat_acc if cat_acc else "<div class='text-muted'>Sin categorías mapeadas.</div>"}
          </div>
        </div>
        """

    content = render_template_string("""
    <div class="menu-wrap">

      <div class="plan-hero">
        <div class="plan-hero-overlay">
          <div class="plan-hero-centered">
            <h2 class="plan-title">Nivel de Madurez acorde con NIST</h2>
            <div class="plan-subtitle">
              Run ISO #{{ run.id }} • {{ run.company_name }} • {{ run.created_at.strftime('%Y-%m-%d %H:%M') }}
            </div>
          </div>
        </div>
      </div>

      <div class="volver-center">
        <a class="btn btn-light rounded-pill plan-btn-main"
           href="{{ url_for('madurez.view_report', run_id=run.id) }}">
          ⬅ Volver al reporte ISO
        </a>
      </div>

      {% if error %}
        <div class="alert alert-danger shadow-sm">
          <b>No se pudo calcular NIST</b><br/>
          {{ error }}
        </div>
      {% endif %}

      <div class="row g-3">
        <div class="col-md-4">
          <div class="card card-soft p-3">
            <div class="fw-bold mb-1">📊 Nivel general NIST</div>
            <div class="display-6">{{ nivel_general }}</div>
            <div class="text-muted small">Promedio de categorías mapeadas</div>
          </div>
        </div>

        <div class="col-md-8">
          <div class="card card-soft p-3">
            <div class="fw-bold mb-2">ℹ️ ¿Cómo se calcula?</div>
            <div class="small text-muted">
              Se toma el nivel alcanzado en ISO 27001 (por cláusula/control) guardado en este run,
              se cruza con el archivo de mapeo CSF→ISO y se promedia por <b>Función</b> y <b>Categoría</b>.
            </div>
          </div>
        </div>
      </div>

      <div class="mt-4">
        {{ blocks|safe }}
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

      .menu-wrap{
        width:96%;
        max-width:1200px;
        margin:26px auto 24px auto;
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

      .plan-hero-overlay{
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

      .plan-hero-overlay::before{
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
        font-size:1.45rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }

      .plan-hero-centered{
        max-width:1000px;
        width:100%;
        display:block !important;
        transform:none !important;
      }

      .plan-hero-centered::before{
        content:"SGSI · Gestión";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .plan-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-align:left;
        margin:0 !important;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
      }

      .plan-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        text-align:left;
        line-height:1.25;
      }

      .volver-center{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px 0;
      }

      .volver-center .btn,
      .plan-btn-main{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .plan-btn-main{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }

      .plan-btn-main:hover{
        background:#edf5ff;
        color:#0b65d8 !important;
        border-color:#9ec5fe !important;
      }

      .card,
      .card-soft{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }

      .card-body{
        padding:18px;
      }

      .table-responsive{
        max-height:72vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
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
        border:none !important;
        white-space:nowrap;
        vertical-align:middle;
        text-align:center;
        padding:9px 8px;
      }

      .table tbody td{
        vertical-align:top;
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

      @media (max-width:991.98px){
        .menu-wrap{
          width:98%;
          margin:8px auto 22px auto;
        }

        .plan-hero{
          min-height:88px;
        }

        .plan-title{
          font-size:1.20rem;
        }

        .card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .plan-hero-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .plan-hero-overlay::before{
          margin:0;
        }

        .plan-hero-centered::before{
          margin-left:auto;
          margin-right:auto;
        }

        .plan-title,
        .plan-subtitle{
          text-align:center;
        }

        .volver-center .btn{
          width:100%;
        }
      }
    </style>
    """, run=run, nivel_general=nivel_general, blocks=blocks, error=error)

    return render_template_string(BASE, content=content)


# ==========================
# Parametro de Madurez
# ==========================

@madurez_bp.route("/parametros/madurez", methods=["GET", "POST"])
@login_required
def param_maturity_levels():
    if request.method == "POST":
        nivel = request.form.get("nivel")
        madurez = (request.form.get("madurez") or "").strip()
        descripcion = (request.form.get("descripcion") or "").strip()

        try:
            nivel_i = int(nivel)
        except Exception:
            flash("Nivel debe ser numérico.", "danger")
            return redirect(url_for("madurez.param_maturity_levels"))

        if not madurez:
            flash("Madurez (texto) es requerida.", "danger")
            return redirect(url_for("madurez.param_maturity_levels"))

        exists = MaturityLevel.query.filter(
            (MaturityLevel.nivel == nivel_i) | (MaturityLevel.madurez.ilike(madurez))
        ).first()
        if exists:
            flash("Ya existe un nivel o nombre de madurez igual.", "warning")
            return redirect(url_for("madurez.param_maturity_levels"))

        db.session.add(MaturityLevel(nivel=nivel_i, madurez=madurez, descripcion=descripcion))
        db.session.commit()
        flash("✅ Nivel de madurez creado.", "success")
        return redirect(url_for("madurez.param_maturity_levels"))

    rows = MaturityLevel.query.order_by(MaturityLevel.nivel.asc()).all()
    tr = ""
    for r in rows:
        tr += f"""
        <tr>
          <td class="text-muted">{r.nivel}</td>
          <td class="fw-semibold">{xml_escape(r.madurez)}</td>
          <td class="wrap">{xml_escape(r.descripcion or "")}</td>
          <td class="text-end">
            <form method="POST" action="{url_for("madurez.param_maturity_delete", mid=r.id)}" style="display:inline;"
              onsubmit="return confirm('¿Eliminar {xml_escape(r.madurez)}?');">
              <button class="btn btn-sm btn-outline-danger pill" type="submit">Eliminar</button>
            </form>
          </td>
        </tr>
        """

    content = f"""
    <div class="madlvl-shell">

      <!-- CABECERA -->
      <div class="madlvl-header-card">
        <div class="madlvl-header-overlay">
          <div class="madlvl-header-text">
            <h3 class="madlvl-title m-0">Modelo Nivel de Madurez</h3>
            <div class="madlvl-subtitle">
              Catálogo de niveles de madurez utilizados para clasificar el estado del SGSI
              según el porcentaje de cumplimiento del instrumento.
            </div>
          </div>
        </div>
      </div>

      <!-- BOTÓN VOLVER -->
      <div class="madlvl-header-actions">
          <a href="{url_for("madurez.parametros_menu")}"
             class="btn madlvl-btn-main rounded-pill px-4 fw-bold">
            ⬅ Parámetros
          </a>
      </div>

      <div class="row g-3">

        <!-- FORMULARIO -->
        <div class="col-lg-4">
          <div class="madlvl-card p-4">

            <div class="madlvl-section-title">
              Agregar nivel
            </div>

            <form method="POST">

              <div class="mb-3">
                <label class="form-label fw-semibold">
                  Nivel (numérico)
                </label>

                <input class="form-control"
                       name="nivel"
                       type="number"
                       min="0"
                       required>
              </div>

              <div class="mb-3">
                <label class="form-label fw-semibold">
                  Madurez (texto)
                </label>

                <input class="form-control"
                       name="madurez"
                       required
                       placeholder="Ej: Inicial, Gestionado, Óptimo">
              </div>

              <div class="mb-3">
                <label class="form-label fw-semibold">
                  Descripción
                </label>

                <textarea class="form-control"
                          name="descripcion"
                          rows="3"></textarea>
              </div>

              <div class="text-center">
                <button class="btn btn-primary rounded-pill px-4 fw-semibold"
                        type="submit">
                  Guardar
                </button>
              </div>

            </form>

          </div>
        </div>


        <!-- TABLA -->
        <div class="col-lg-8">
          <div class="madlvl-card p-4">

            <div class="madlvl-section-title">
              Listado de niveles
            </div>

            <div class="table-responsive madlvl-table-wrap">

              <table class="table table-sm align-middle table-hover mb-0">

                <thead class="madlvl-table-head">
                  <tr>
                    <th>Nivel</th>
                    <th>Madurez</th>
                    <th>Descripción</th>
                    <th></th>
                  </tr>
                </thead>

                <tbody>
                  {tr if tr else "<tr><td colspan='4' class='text-muted'>Sin registros.</td></tr>"}
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

      .madlvl-shell{{
        width:96%;
        max-width:1350px;
        margin:26px auto 24px auto;
      }}

      .madlvl-header-card{{
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

      .madlvl-header-card::before{{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }}

      .madlvl-header-overlay{{
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

      .madlvl-header-overlay::before{{
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
        font-size:1.45rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }}

      .madlvl-header-text{{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
      }}

      .madlvl-header-text::before{{
        content:"SGSI · Niveles de Madurez";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }}

      .madlvl-title{{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }}

      .madlvl-subtitle{{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }}

      .madlvl-header-actions{{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }}

      .madlvl-header-actions .btn,
      .madlvl-btn-main,
      .btn{{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }}

      .madlvl-btn-main{{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }}

      .madlvl-btn-main:hover{{
        background:#edf5ff;
        color:#0b65d8 !important;
        border-color:#9ec5fe !important;
      }}

      .madlvl-card,
      .card{{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }}

      .madlvl-card .card-body{{
        padding:20px;
      }}

      .madlvl-section-title,
      .card h5,
      .card h6{{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:16px;
      }}

      .madlvl-section-title{{
        padding-bottom:8px;
        border-bottom:2px solid rgba(59,130,246,.18);
      }}

      .madlvl-table-wrap,
      .table-responsive{{
        max-height:72vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
      }}

      .madlvl-table-wrap .table,
      .table{{
        margin-bottom:0;
      }}

      .madlvl-table-wrap thead th,
      .madlvl-table-head th,
      .table thead th{{
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
      }}

      .madlvl-table-wrap tbody td,
      .table tbody td{{
        vertical-align:middle;
        font-size:.82rem;
        padding:9px 8px;
        border-bottom:1px solid #e5edf7;
        color:#101827;
      }}

      .madlvl-table-wrap tbody tr:last-child td{{
        border-bottom:none;
      }}

      .table tbody tr:nth-child(even){{
        background:#f8fbff;
      }}

      .table tbody tr:hover{{
        background:#eef6ff;
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

      .input-group-text{{
        border-radius:0 10px 10px 0;
        background:#eef5ff;
        border:1px solid #d9eaff;
        color:#0b4a8f;
        font-weight:900;
      }}

      .badge{{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }}

      @media (max-width:992px){{
        .madlvl-shell{{
          width:98%;
          margin:8px auto 22px auto;
        }}

        .madlvl-header-card{{
          min-height:88px;
        }}

        .madlvl-title{{
          font-size:1.20rem;
        }}

        .madlvl-subtitle{{
          font-size:.68rem;
        }}

        .madlvl-card .card-body{{
          padding:16px;
        }}
      }}

      @media (max-width:768px){{
        .madlvl-header-overlay{{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }}

        .madlvl-header-overlay::before{{
          margin:0;
        }}

        .madlvl-header-text::before{{
          margin-left:auto;
          margin-right:auto;
        }}

        .madlvl-title,
        .madlvl-subtitle{{
          text-align:center;
        }}

        .madlvl-header-actions .btn{{
          width:100%;
        }}
      }}
    </style>
    """
    return render_template_string(BASE, title="Parámetro: Madurez", content=content)


@madurez_bp.route("/parametros/madurez/<int:mid>/delete", methods=["POST"])
@login_required
def param_maturity_delete(mid: int):
    r = MaturityLevel.query.get_or_404(mid)

    used = ComplianceMaturityMap.query.filter_by(maturity_id=r.id).first()
    if used:
        flash("No se puede eliminar: este nivel está asignado en la relación Cumplimiento→Madurez.", "danger")
        return redirect(url_for("madurez.param_maturity_levels"))

    db.session.delete(r)
    db.session.commit()
    flash("🗑️ Eliminado.", "success")
    return redirect(url_for("madurez.param_maturity_levels"))

# =================================
# Parametro Cumplimiento de Madurez
# =================================

@madurez_bp.route("/parametros/cumplimiento-madurez", methods=["GET", "POST"])
@login_required
def param_compliance_map():
    levels = MaturityLevel.query.order_by(MaturityLevel.nivel.asc()).all()
    if not levels:
        flash("Primero crea los niveles de madurez (punto 1).", "warning")
        return redirect(url_for("madurez.param_maturity_levels"))

    if request.method == "POST":
        pct_min = _to_float(request.form.get("pct_min"), None)
        pct_max = _to_float(request.form.get("pct_max"), None)
        maturity_id = request.form.get("maturity_id")

        if pct_min is None or pct_max is None:
            flash("Rangos % inválidos.", "danger")
            return redirect(url_for("madurez.param_compliance_map"))

        if pct_min < 0 or pct_max > 100 or pct_min > pct_max:
            flash("El rango debe estar entre 0 y 100 y min <= max.", "danger")
            return redirect(url_for("madurez.param_compliance_map"))

        try:
            maturity_id = int(maturity_id)
        except Exception:
            flash("Selecciona un nivel de madurez válido.", "danger")
            return redirect(url_for("madurez.param_compliance_map"))

        for e in ComplianceMaturityMap.query.all():
            if _ranges_overlap(pct_min, pct_max, e.pct_min, e.pct_max):
                flash(f"El rango {pct_min}-{pct_max} se solapa con {e.pct_min}-{e.pct_max}. Ajusta rangos.", "danger")
                return redirect(url_for("madurez.param_compliance_map"))

        db.session.add(ComplianceMaturityMap(pct_min=pct_min, pct_max=pct_max, maturity_id=maturity_id))
        db.session.commit()
        flash("✅ Relación creada.", "success")
        return redirect(url_for("madurez.param_compliance_map"))

    rows = (ComplianceMaturityMap.query
            .join(MaturityLevel)
            .order_by(ComplianceMaturityMap.pct_min.asc())
            .all())

    tr = ""
    for r in rows:
        tr += f"""
        <tr>
          <td class="text-muted">{r.pct_min:.0f}%</td>
          <td class="text-muted">{r.pct_max:.0f}%</td>
          <td class="fw-semibold">{xml_escape(r.maturity.madurez if r.maturity else "")}</td>
          <td class="text-end">
            <form method="POST" action="{url_for("madurez.param_compliance_delete", rid=r.id)}" style="display:inline;"
              onsubmit="return confirm('¿Eliminar rango {r.pct_min}-{r.pct_max}?');">
              <button class="btn btn-sm btn-outline-danger pill" type="submit">Eliminar</button>
            </form>
          </td>
        </tr>
        """

    opts = "".join([f"<option value='{lv.id}'>{xml_escape(lv.madurez)} (nivel {lv.nivel})</option>" for lv in levels])

    content = f"""
    <div class="madmap-shell">

      <!-- CABECERA -->
      <div class="madmap-header-card">
        <div class="madmap-header-overlay">
          <div class="madmap-header-text">
            <h3 class="madmap-title m-0">Relación Cumplimiento → Madurez</h3>
            <div class="madmap-subtitle">
              Define los rangos porcentuales de cumplimiento y el nivel de madurez
              que representan dentro del modelo de evaluación del SGSI.
            </div>
          </div>
        </div>
      </div>

      <!-- BOTÓN VOLVER -->
      <div class="madmap-header-actions">
        <a href="{url_for("madurez.parametros_menu")}"
           class="btn madmap-btn-main rounded-pill px-4 fw-bold">
          ⬅ Parámetros
        </a>
      </div>

      <div class="row g-3">

        <!-- FORMULARIO -->
        <div class="col-lg-4">
          <div class="madmap-card p-4">

            <div class="madmap-section-title">
              Agregar rango
            </div>

            <form method="POST">

              <div class="mb-3">
                <label class="form-label fw-semibold">% mínimo</label>
                <input class="form-control"
                       name="pct_min"
                       type="number"
                       min="0"
                       max="100"
                       step="1"
                       required>
              </div>

              <div class="mb-3">
                <label class="form-label fw-semibold">% máximo</label>
                <input class="form-control"
                       name="pct_max"
                       type="number"
                       min="0"
                       max="100"
                       step="1"
                       required>
              </div>

              <div class="mb-3">
                <label class="form-label fw-semibold">Nivel de madurez</label>
                <select class="form-select" name="maturity_id" required>
                  {opts}
                </select>
              </div>

              <div class="text-center">
                <button class="btn btn-primary rounded-pill px-4 fw-semibold" type="submit">
                  Guardar
                </button>
              </div>

            </form>

            <div class="madmap-note mt-4">
              <strong>Recomendación:</strong>
              usa rangos contiguos y sin solapamientos, por ejemplo:
              0-39, 40-59, 60-79, 80-100.
            </div>

          </div>
        </div>

        <!-- TABLA -->
        <div class="col-lg-8">
          <div class="madmap-card p-4">

            <div class="madmap-section-title">
              Rangos configurados
            </div>

            <div class="table-responsive madmap-table-wrap">
              <table class="table table-sm align-middle table-hover mb-0">
                <thead class="madmap-table-head">
                  <tr>
                    <th>% Min</th>
                    <th>% Max</th>
                    <th>Madurez</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {tr if tr else "<tr><td colspan='4' class='text-muted'>Sin rangos. Agrega al menos uno.</td></tr>"}
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

      .madmap-shell{{
        width:96%;
        max-width:1350px;
        margin:26px auto 24px auto;
      }}

      .madmap-header-card{{
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

      .madmap-header-card::before{{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }}

      .madmap-header-overlay{{
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

      .madmap-header-overlay::before{{
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
        font-size:1.45rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }}

      .madmap-header-text{{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
      }}

      .madmap-header-text::before{{
        content:"SGSI · Mapeo de Madurez";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }}

      .madmap-title{{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }}

      .madmap-subtitle{{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }}

      .madmap-header-actions{{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }}

      .madmap-header-actions .btn,
      .madmap-btn-main,
      .btn{{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }}

      .madmap-btn-main{{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }}

      .madmap-btn-main:hover{{
        background:#edf5ff;
        color:#0b65d8 !important;
        border-color:#9ec5fe !important;
      }}

      .madmap-card,
      .card{{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }}

      .madmap-card .card-body{{
        padding:20px;
      }}

      .madmap-section-title,
      .card h5,
      .card h6{{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:16px;
      }}

      .madmap-section-title{{
        padding-bottom:8px;
        border-bottom:2px solid rgba(59,130,246,.18);
      }}

      .madmap-note{{
        background:#f8fafc;
        border:1px solid #dbeafe;
        color:#334155;
        border-radius:12px;
        padding:12px 14px;
        font-size:.78rem;
        line-height:1.45;
      }}

      .madmap-table-wrap,
      .table-responsive{{
        max-height:72vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
      }}

      .madmap-table-wrap .table,
      .table{{
        margin-bottom:0;
      }}

      .madmap-table-wrap thead th,
      .madmap-table-head th,
      .table thead th{{
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
      }}

      .madmap-table-wrap tbody td,
      .table tbody td{{
        vertical-align:middle;
        font-size:.82rem;
        padding:9px 8px;
        border-bottom:1px solid #e5edf7;
        color:#101827;
      }}

      .madmap-table-wrap tbody tr:last-child td{{
        border-bottom:none;
      }}

      .table tbody tr:nth-child(even){{
        background:#f8fbff;
      }}

      .table tbody tr:hover{{
        background:#eef6ff;
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

      .input-group-text{{
        border-radius:0 10px 10px 0;
        background:#eef5ff;
        border:1px solid #d9eaff;
        color:#0b4a8f;
        font-weight:900;
      }}

      .badge{{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }}

      @media (max-width:992px){{
        .madmap-shell{{
          width:98%;
          margin:8px auto 22px auto;
        }}

        .madmap-header-card{{
          min-height:88px;
        }}

        .madmap-title{{
          font-size:1.20rem;
        }}

        .madmap-subtitle{{
          font-size:.68rem;
        }}

        .madmap-card .card-body{{
          padding:16px;
        }}
      }}

      @media (max-width:768px){{
        .madmap-header-overlay{{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }}

        .madmap-header-overlay::before{{
          margin:0;
        }}

        .madmap-header-text::before{{
          margin-left:auto;
          margin-right:auto;
        }}

        .madmap-title,
        .madmap-subtitle{{
          text-align:center;
        }}

        .madmap-header-actions .btn{{
          width:100%;
        }}
      }}
    </style>
    """
    return render_template_string(BASE, title="Parámetro: Cumplimiento→Madurez", content=content)


@madurez_bp.route("/parametros/cumplimiento-madurez/<int:rid>/delete", methods=["POST"])
@login_required
def param_compliance_delete(rid: int):
    r = ComplianceMaturityMap.query.get_or_404(rid)
    db.session.delete(r)
    db.session.commit()
    flash("🗑️ Rango eliminado.", "success")
    return redirect(url_for("madurez.param_compliance_map"))

# =================
# Parametro Brechas
# =================

@madurez_bp.route("/parametros/brechas", methods=["GET", "POST"])
@login_required
def param_gap_levels():
    if request.method == "POST":
        pct_min = _to_float(request.form.get("pct_min"), None)
        pct_max = _to_float(request.form.get("pct_max"), None)
        nivel_brecha = (request.form.get("nivel_brecha") or "").strip()
        interpretacion = (request.form.get("interpretacion") or "").strip()

        if pct_min is None or pct_max is None:
            flash("Rangos % inválidos.", "danger")
            return redirect(url_for("madurez.param_gap_levels"))
        if pct_min < 0 or pct_max > 100 or pct_min > pct_max:
            flash("El rango debe estar entre 0 y 100 y min <= max.", "danger")
            return redirect(url_for("madurez.param_gap_levels"))

        allowed = {"Bajo", "Medio", "Alto", "Critico"}
        if nivel_brecha not in allowed:
            flash("Nivel de brecha inválido. Use Bajo/Medio/Alto/Critico.", "danger")
            return redirect(url_for("madurez.param_gap_levels"))

        for e in GapLevelConfig.query.all():
            if _ranges_overlap(pct_min, pct_max, e.pct_min, e.pct_max):
                flash(f"El rango {pct_min}-{pct_max} se solapa con {e.pct_min}-{e.pct_max}.", "danger")
                return redirect(url_for("madurez.param_gap_levels"))

        db.session.add(GapLevelConfig(
            pct_min=pct_min, pct_max=pct_max, nivel_brecha=nivel_brecha, interpretacion=interpretacion
        ))
        db.session.commit()
        flash("✅ Nivel de brecha creado.", "success")
        return redirect(url_for("madurez.param_gap_levels"))

    rows = GapLevelConfig.query.order_by(GapLevelConfig.pct_min.asc()).all()
    tr = ""
    for r in rows:
        tr += f"""
        <tr>
          <td class="text-muted">{r.pct_min:.0f}%</td>
          <td class="text-muted">{r.pct_max:.0f}%</td>
          <td class="fw-semibold">{xml_escape(r.nivel_brecha)}</td>
          <td class="wrap">{xml_escape(r.interpretacion or "")}</td>
          <td class="text-end">
            <form method="POST" action="{url_for("madurez.param_gap_delete", gid=r.id)}" style="display:inline;"
              onsubmit="return confirm('¿Eliminar rango {r.pct_min}-{r.pct_max}?');">
              <button class="btn btn-sm btn-outline-danger pill" type="submit">Eliminar</button>
            </form>
          </td>
        </tr>
        """

    content = f"""
    <div class="madgap-shell">

      <!-- CABECERA -->
      <div class="madgap-header-card">
        <div class="madgap-header-overlay">
          <div class="madgap-header-text">
            <h3 class="madgap-title m-0">Calificación nivel de brecha</h3>
            <div class="madgap-subtitle">
              Define los rangos porcentuales de brecha y su clasificación
              en Bajo, Medio, Alto o Crítico junto con su interpretación.
            </div>
          </div>
        </div>
      </div>

      <!-- BOTÓN VOLVER -->
      <div class="madgap-header-actions">
        <a href="{url_for("madurez.parametros_menu")}"
           class="btn madgap-btn-main rounded-pill px-4 fw-bold">
          ⬅ Parámetros
        </a>
      </div>

      <div class="row g-3">

        <!-- FORMULARIO -->
        <div class="col-lg-4">
          <div class="madgap-card p-4">

            <div class="madgap-section-title">
              Agregar rango
            </div>

            <form method="POST">

              <div class="mb-3">
                <label class="form-label fw-semibold">% brecha mínimo</label>
                <input class="form-control"
                       name="pct_min"
                       type="number"
                       min="0"
                       max="100"
                       step="1"
                       required>
              </div>

              <div class="mb-3">
                <label class="form-label fw-semibold">% brecha máximo</label>
                <input class="form-control"
                       name="pct_max"
                       type="number"
                       min="0"
                       max="100"
                       step="1"
                       required>
              </div>

              <div class="mb-3">
                <label class="form-label fw-semibold">Nivel de brecha</label>
                <select class="form-select" name="nivel_brecha" required>
                  <option>Bajo</option>
                  <option>Medio</option>
                  <option>Alto</option>
                  <option>Critico</option>
                </select>
              </div>

              <div class="mb-3">
                <label class="form-label fw-semibold">Interpretación</label>
                <textarea class="form-control"
                          name="interpretacion"
                          rows="3"></textarea>
              </div>

              <div class="text-center">
                <button class="btn btn-primary rounded-pill px-4 fw-semibold"
                        type="submit">
                  Guardar
                </button>
              </div>

            </form>

          </div>
        </div>

        <!-- TABLA -->
        <div class="col-lg-8">
          <div class="madgap-card p-4">

            <div class="madgap-section-title">
              Rangos configurados
            </div>

            <div class="table-responsive madgap-table-wrap">

              <table class="table table-sm align-middle table-hover mb-0">

                <thead class="madgap-table-head">
                  <tr>
                    <th>% Min</th>
                    <th>% Max</th>
                    <th>Nivel</th>
                    <th>Interpretación</th>
                    <th></th>
                  </tr>
                </thead>

                <tbody>
                  {tr if tr else "<tr><td colspan='5' class='text-muted'>Sin rangos.</td></tr>"}
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

      .madgap-shell{{
        width:96%;
        max-width:1350px;
        margin:26px auto 24px auto;
      }}

      .madgap-header-card{{
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

      .madgap-header-card::before{{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }}

      .madgap-header-overlay{{
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

      .madgap-header-overlay::before{{
        content:"📉";
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

      .madgap-header-text{{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
      }}

      .madgap-header-text::before{{
        content:"SGSI · Brechas de Madurez";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }}

      .madgap-title{{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }}

      .madgap-subtitle{{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }}

      .madgap-header-actions{{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }}

      .madgap-header-actions .btn,
      .madgap-btn-main,
      .btn{{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }}

      .madgap-btn-main{{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }}

      .madgap-btn-main:hover{{
        background:#edf5ff;
        color:#0b65d8 !important;
        border-color:#9ec5fe !important;
      }}

      .madgap-card,
      .card{{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }}

      .madgap-section-title,
      .card h5,
      .card h6{{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:16px;
      }}

      .madgap-section-title{{
        padding-bottom:8px;
        border-bottom:2px solid rgba(59,130,246,.18);
      }}

      .madgap-table-wrap,
      .table-responsive{{
        max-height:72vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
      }}

      .madgap-table-wrap .table,
      .table{{
        margin-bottom:0;
      }}

      .madgap-table-wrap thead th,
      .madgap-table-head th,
      .table thead th{{
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
      }}

      .madgap-table-wrap tbody td,
      .table tbody td{{
        vertical-align:middle;
        font-size:.82rem;
        padding:9px 8px;
        border-bottom:1px solid #e5edf7;
        color:#101827;
      }}

      .madgap-table-wrap tbody tr:last-child td{{
        border-bottom:none;
      }}

      .table tbody tr:nth-child(even){{
        background:#f8fbff;
      }}

      .table tbody tr:hover{{
        background:#eef6ff;
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

      .input-group-text{{
        border-radius:0 10px 10px 0;
        background:#eef5ff;
        border:1px solid #d9eaff;
        color:#0b4a8f;
        font-weight:900;
      }}

      .badge{{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }}

      @media (max-width:992px){{
        .madgap-shell{{
          width:98%;
          margin:8px auto 22px auto;
        }}

        .madgap-header-card{{
          min-height:88px;
        }}

        .madgap-title{{
          font-size:1.20rem;
        }}

        .madgap-subtitle{{
          font-size:.68rem;
        }}
      }}

      @media (max-width:768px){{
        .madgap-header-overlay{{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }}

        .madgap-header-overlay::before{{
          margin:0;
        }}

        .madgap-header-text::before{{
          margin-left:auto;
          margin-right:auto;
        }}

        .madgap-title,
        .madgap-subtitle{{
          text-align:center;
        }}

        .madgap-header-actions .btn{{
          width:100%;
        }}
      }}
    </style>
    """
    return render_template_string(BASE, title="Parámetro: Brechas", content=content)

def safe_str(x):
    """Convierte NaN/None a '' y todo lo demás a string limpio."""
    try:
        import pandas as pd
        if x is None:
            return ""
        # pandas NaN
        if isinstance(x, float) and x != x:
            return ""
        if "pd" in globals() and pd.isna(x):
            return ""
    except Exception:
        pass
    return str(x).replace("\ufeff", "").strip()

@madurez_bp.route("/parametros/brechas/<int:gid>/delete", methods=["POST"])
@login_required
def param_gap_delete(gid: int):
    r = GapLevelConfig.query.get_or_404(gid)
    db.session.delete(r)
    db.session.commit()
    flash("🗑️ Rango eliminado.", "success")
    return redirect(url_for("madurez.param_gap_levels"))

def safe_str(x):
    try:
        if x is None:
            return ""
        s = str(x)
        return s.replace("\ufeff", "").strip()
    except Exception:
        return ""

def normalize_anexo_control(raw_control: str, tema: str = "") -> str:
    c = (raw_control or "").strip()

    # 1) Normal "5.1"
    m = re.match(r"^(\d+)\.(\d+)$", c)
    c_norm = f"{int(m.group(1))}.{int(m.group(2))}" if m else ""

    # 2) Si Excel lo trae como fecha "YYYY-MM-DD ..." -> dd.mm  (ej 2026-06-05 => 5.6)
    if not c_norm and re.match(r"^\d{4}-\d{2}-\d{2}", c):
        try:
            date_part = c.split(" ", 1)[0]
            _, mm, dd = date_part.split("-")
            c_norm = f"{int(dd)}.{int(mm)}"
        except Exception:
            c_norm = ""

    # 3) Fix 5.10 mal digitado como 5.1 (tema Uso aceptable)
    tema_l = (tema or "").strip().lower()
    if c_norm == "5.1" and ("uso aceptable" in tema_l):
        c_norm = "5.10"

    return c_norm



@madurez_bp.route("/admin/importar_instrumento", methods=["POST"])
@login_required
def importar_instrumento_admin():
    force = (request.args.get("force") == "1") or (request.form.get("force") == "1")

    if force:
        MadurezRespuesta.query.delete()
        MadurezPregunta.query.delete()
        db.session.commit()
        flash("🧹 Instrumento anterior borrado. Reimportando…", "info")

    if MadurezPregunta.query.first() and not force:
        flash("El instrumento ya está cargado en la base de datos.", "warning")
        return redirect(url_for("madurez.parametros_menu"))

    base_dir = os.path.dirname(os.path.abspath(__file__))

    # ✅ Usa el nombre REAL (con fallback bien indentado)
    xlsx_path = os.path.join(base_dir, "static/templates/Instrumento de Evaluación-ISO-27001 2022.xlsx")
    if not os.path.exists(xlsx_path):
        xlsx_path2 = os.path.join(base_dir, "static/templates/Instrumento de Evaluación-ISO-27001 2022.xlsx")
        if os.path.exists(xlsx_path2):
            xlsx_path = xlsx_path2

    if not os.path.exists(xlsx_path):
        flash(f"No se encontró el archivo para importar: {xlsx_path}", "danger")
        return redirect(url_for("madurez.parametros_menu"))

    xls = pd.ExcelFile(xlsx_path)
    orden_global = 0

    for sheet in xls.sheet_names:
        df = xls.parse(sheet, header=None)
        sheet_name = str(sheet).strip()

        # -------------------------
        # ANEXO A
        # -------------------------
        if sheet_name.upper() == "ANEXO A":
            # Header del anexo
            db.session.add(MadurezPregunta(
                sheet="ANEXO A",
                orden=orden_global,
                tipo="h",
                seccion=None,
                pregunta="ANEXO A — CONTROLES ISO/IEC 27001:2022"
            ))
            orden_global += 1

            # ✅ En TU Excel real: todo está en la columna A (índice 0)
            # Fila 0 tiene "ANEXO A - 27002" y encabezados "No Aplica / Si / Parcialmente / No / Comentarios"
            # Empezamos desde la fila 1
            last_control = None

            for r in range(1, len(df)):
                t = safe_str(df.iloc[r, 0]).replace("\ufeff", "").strip()  # <- columna A
                if not t:
                    continue

                # 1) Encabezados de familia: "5. CONTROLES ORGANIZACIONALES"
                #    (nota: lleva punto después del número)
                if re.match(r"^\d+\.\s", t) and not t.startswith("¿"):
                    db.session.add(MadurezPregunta(
                        sheet="ANEXO A",
                        orden=orden_global,
                        tipo="h",
                        seccion=None,
                        pregunta=t
                    ))
                    orden_global += 1
                    last_control = None
                    continue

                # 2) Encabezados de control: "5.1 Políticas..."  (NO es pregunta)
                m_ctrl = re.match(r"^(\d+)\.(\d+)\s+", t)
                if m_ctrl and not t.startswith("¿"):
                    last_control = f"{int(m_ctrl.group(1))}.{int(m_ctrl.group(2))}"
                    db.session.add(MadurezPregunta(
                        sheet="ANEXO A",
                        orden=orden_global,
                        tipo="h",
                        seccion=last_control,
                        control=last_control,   # ✅ consistente
                        tema="",                # ✅ opcional
                        pregunta=t
                    ))
                    orden_global += 1
                    continue

                # 3) Preguntas: empiezan con ¿
                if t.startswith("¿"):
                    # si no hay control detectado, igual guarda la pregunta, pero el análisis necesita control cuando exista
                    db.session.add(MadurezPregunta(
                        sheet="ANEXO A",
                        orden=orden_global,
                        tipo="q",
                        seccion=last_control,          # UI
                        control=last_control or "",    # ✅ CLAVE para el análisis (A.5.1 ...)
                        tema="",                       # ✅ puedes dejarlo vacío o llenarlo luego
                        pregunta=t
                    ))
                    orden_global += 1
                    continue

            continue

        # -------------------------
        # CAPÍTULOS 4–10
        # -------------------------
        seccion_actual = None

        # Guardar título del capítulo (fila 0, col 1)
        titulo = safe_str(df.iloc[0, 1]) if df.shape[1] > 1 else ""
        if titulo:
            db.session.add(MadurezPregunta(
                sheet=sheet_name,
                orden=orden_global,
                tipo="h",
                seccion=None,
                pregunta=titulo
            ))
            orden_global += 1

        for r in range(1, len(df)):
            txt = df.iloc[r, 1] if df.shape[1] > 1 else None
            t = safe_str(txt)
            if not t:
                continue

            # Subtítulos/secciones: 4.1 / 6.1.1 / 10.2 etc
            if (len(t) < 250) and re.match(r"^(4|5|6|7|8|9|10)\.\d", t):
                seccion_actual = t
                db.session.add(MadurezPregunta(
                    sheet=sheet_name,
                    orden=orden_global,
                    tipo="h",
                    seccion=seccion_actual,
                    pregunta=t
                ))
                orden_global += 1
                continue

            # Preguntas
            if t.startswith("¿"):
                db.session.add(MadurezPregunta(
                    sheet=sheet_name,
                    orden=orden_global,
                    tipo="q",
                    seccion=seccion_actual,
                    pregunta=t
                ))
                orden_global += 1
                
    flash("ANEXO A: " + str(MadurezPregunta.query.filter_by(sheet="ANEXO A", tipo="q").count()) + " preguntas tipo q", "info")
    db.session.commit()
    flash("✅ Instrumento importado y guardado en la base de datos.", "success")
    return redirect(url_for("madurez.ingreso"))

def _nist_parse_heading_funcion(txt: str):
    """
    Ej: "GOVERN (GV)" -> ("GOVERN", "GV")
    """
    t = (txt or "").strip()
    m = re.match(r"^([A-Za-z ]+)\s*\(([A-Z]{1,4})\)\s*$", t)
    if not m:
        return None
    return (m.group(1).strip().upper(), m.group(2).strip().upper())

def _nist_parse_heading_categoria(txt: str):
    """
    Ej: "Organizational Context (GV.OC)" -> ("Organizational Context", "GV.OC")
    """
    t = (txt or "").strip()
    m = re.match(r"^(.+?)\s*\(([A-Z]{1,4}\.[A-Z0-9]{1,6})\)\s*$", t)
    if not m:
        return None
    return (m.group(1).strip(), m.group(2).strip().upper())

def _translate_to_es_cached(text: str) -> str:
    """
    Traduce EN->ES usando tu cliente OpenRouter ya existente.
    Si falla, devuelve el texto original.
    """
    t = (text or "").strip()
    if not t:
        return t

    # caching simple (en memoria) para no repetir en la misma ejecución
    if not hasattr(_translate_to_es_cached, "_cache"):
        _translate_to_es_cached._cache = {}
    cache = _translate_to_es_cached._cache
    if t in cache:
        return cache[t]

    try:
        # Traducción directa, sin adornos
        client = get_openai_client()
        resp = client.chat.completions.create(
            model=OPENROUTER_MODEL_SGSI,
            messages=[
                {"role": "system", "content": "Eres un traductor profesional EN->ES para ciberseguridad. Traduce fielmente, sin agregar texto extra."},
                {"role": "user", "content": t}
            ],
            max_tokens=1200
        )
        out = (resp.choices[0].message.content or "").strip()
        if out:
            cache[t] = out
            if _GRAC_RENDER_LOW_MEMORY and len(cache) > 384:
                for _ in range(128):
                    cache.pop(next(iter(cache)), None)
            return out
    except Exception:
        pass

    cache[t] = t
    if _GRAC_RENDER_LOW_MEMORY and len(cache) > 384:
        # La traducción permanece disponible; solo se descartan traducciones antiguas.
        for _ in range(128):
            cache.pop(next(iter(cache)), None)
    return t


@nist_madurez_bp.route("/admin/importar_instrumento", methods=["POST"])
@login_required
def nist_importar_instrumento_admin():
    force = (request.args.get("force") == "1") or (request.form.get("force") == "1")

    if (NistMadurezPregunta.query.count() > 0) and not force:
        flash("⚠️ El instrumento NIST ya fue importado. (Usa force=1 si deseas reiniciar).", "warning")
        return redirect(url_for("madurez_nist.home"))

    if force:
        # borra todo para reimportar limpio
        try:
            NistMadurezRespuesta.query.delete()
            NistMadurezRun.query.delete()
            NistMadurezPregunta.query.delete()
            db.session.commit()
        except Exception:
            db.session.rollback()

    if not os.path.exists(NIST_INSTRUMENTO_TEMPLATE_XLSX):
        flash(f"❌ No se encontró el Excel NIST en: {NIST_INSTRUMENTO_TEMPLATE_XLSX}", "danger")
        return redirect(url_for("madurez_nist.home"))

    try:
        wb = load_workbook(NIST_INSTRUMENTO_TEMPLATE_XLSX)
    except Exception as e:
        flash(f"❌ No se pudo abrir el Excel NIST: {e}", "danger")
        return redirect(url_for("madurez_nist.home"))

    if "NIST CSF 2.0" not in wb.sheetnames:
        flash(f"❌ La hoja 'NIST CSF 2.0' no existe. Hojas: {wb.sheetnames}", "danger")
        return redirect(url_for("madurez_nist.home"))

    ws = wb["NIST CSF 2.0"]

    funcion = None
    funcion_cod = None
    cat = None
    cat_cod = None
    orden = 0
    created = 0

    # Columna A trae todo el texto (encabezados + preguntas)
    for r in range(1, ws.max_row + 1):
        val = ws.cell(r, 1).value
        txt = ("" if val is None else str(val)).strip()
        if not txt:
            continue

        # Ignora título general
        if r == 1 and "NIST" in txt.upper():
            continue

        fx = _nist_parse_heading_funcion(txt)
        if fx:
            funcion, funcion_cod = fx
            cat, cat_cod = None, None
            continue

        cx = _nist_parse_heading_categoria(txt)
        if cx:
            cat, cat_cod = cx
            continue

        # Si llegamos aquí, es pregunta
        if not funcion:
            continue  # defensivo

        orden += 1
        pregunta_en = txt
        # ====== Lee texto EN (col A) y opcionalmente ES (col B) sin IA ======
        pregunta_en = txt  # txt viene de la columna A (NIST_COL_EN)

        # intenta leer español desde la columna configurada (por defecto B)
        val_es = ws.cell(r, NIST_COL_ES).value if NIST_COL_ES else None
        pregunta_es_excel = ("" if val_es is None else str(val_es)).strip()

        if NIST_TRADUCIR_EN_IMPORTACION:
            # (solo si algún día decides volver a traducir con IA)
            pregunta_es = _translate_to_es_cached(pregunta_en)
        else:
            # ✅ NO IA: toma español del Excel si existe; si no, deja None
            pregunta_es = pregunta_es_excel if pregunta_es_excel else None

        db.session.add(NistMadurezPregunta(
            funcion=funcion,
            funcion_codigo=funcion_cod,
            categoria=cat,
            categoria_codigo=cat_cod,
            orden=orden,
            pregunta_en=pregunta_en,
            pregunta_es=pregunta_es,
            activo=True
        ))
        created += 1

    db.session.commit()
    flash(f"✅ Instrumento NIST importado correctamente. Preguntas creadas: {created}", "success")
    return redirect(url_for("madurez_nist.home"))

# ==========================
# Pantalla Principal ISO 27001
# ==========================
@madurez_bp.route("/", methods=["GET"])
@login_required
def home():
    user = User.query.get(session.get('user_id'))

    if user.role not in ('admin', 'auditor') and not verificar_permiso(user, "Nivel de madurez ISO 27001:2022"):
        flash("No tiene permiso para acceder al módulo de nivel de madurez ISO 27001:2022.", "danger")
        return redirect(url_for('menu'))

    read_only = (user.role == 'auditor')

    if read_only:
        ingreso_btn = """
          <button class="btn btn-secondary rounded-pill px-4 fw-bold" disabled
                  title="El rol Auditor no puede ingresar información">
            <i class="bi bi-pencil-square me-2"></i>Ingresar la información
          </button>
        """
    else:
        ingreso_btn = f"""
          <a href="{url_for('madurez.ingreso')}" class="btn btn-primary rounded-pill px-4 fw-bold">
            <i class="bi bi-pencil-square me-2"></i>Ingresar la información
          </a>
        """

    if read_only:
        parametros_btn = """
          <button class="btn btn-outline-secondary rounded-pill px-3" disabled
                  title="El rol Auditor no tiene acceso a Parámetros">
            <i class="bi bi-gear me-2"></i>Parámetros
          </button>
        """
    else:
        parametros_btn = f"""
          <a href="{url_for('madurez.parametros_menu')}"
             class="btn btn-outline-secondary rounded-pill px-3">
            <i class="bi bi-gear me-2"></i>Parámetros
          </a>
        """

    total = MadurezPregunta.query.count()

    if total == 0:
        badge = '<span class="badge bg-danger ms-2">Instrumento NO cargado</span>'
        hint = "Primero entra a Parámetros y realiza la importación del instrumento (1 vez)."
    else:
        badge = '<span class="badge bg-success ms-2">Instrumento cargado</span>'
        hint = "Puedes ingresar la información o consultar el historial de revisiones."

    company = (request.args.get("company") or "").strip()

    q = AnalysisRun.query
    if company:
        q = q.filter(AnalysisRun.company_name.ilike(f"%{company}%"))
    last = q.order_by(AnalysisRun.id.desc()).limit(20).all()

    rows = ""
    for a in last:
        if read_only:
            delete_btn = """
            <button class="btn btn-sm btn-outline-secondary rounded-pill" type="button" disabled
                    title="El rol Auditor no puede eliminar informes">
              Eliminar
            </button>
            """
        else:
            delete_btn = f"""
            <form method="POST"
                  action="{url_for('madurez.delete_report', run_id=a.id)}"
                  style="display:inline;"
                  onsubmit="return confirm('¿Eliminar el informe #{a.id} de {xml_escape(a.company_name or "")}?');">
              <button class="btn btn-sm btn-outline-danger rounded-pill" type="submit">Eliminar</button>
            </form>
            """

        rows += f"""
        <tr>
          <td class="text-muted">{a.id}</td>
          <td>{xml_escape(a.company_name or "")}</td>
          <td class="wrap">{xml_escape(a.filename or "")}</td>
          <td class="text-muted">{a.created_at.strftime('%Y-%m-%d %H:%M') if a.created_at else ''}</td>
          <td class="text-end">
            <a class="btn btn-sm btn-outline-info rounded-pill"
               href="{url_for('madurez.view_report', run_id=a.id)}">Ver</a>
            <a class="btn btn-sm btn-outline-warning rounded-pill"
               href="{url_for('madurez.report_pdf', run_id=a.id)}">PDF</a>
            {delete_btn}
          </td>
        </tr>
        """

    content = f"""
    <div class="nistmad-shell">

      <div class="nistmad-header-card">
        <div class="nistmad-header-overlay">
          <div class="nistmad-header-text">
            <h3 class="nistmad-title m-0">Nivel de Madurez Estandar ISO 27001:2022</h3>
            <div class="nistmad-subtitle">
              Evaluación del nivel de madurez del SGSI con base en los capítulos
              de ISO 27001:2022 y el Anexo A.
            </div>
          </div>
        </div>
      </div>

      <div class="nistmad-header-actions">
        

        {ingreso_btn}
      </div>

      {"<div class='alert alert-info mt-3'>🔒 El perfil Auditor está en modo solo lectura. En Historial de Revisiones no puede eliminar informes.</div>" if read_only else ""}

      <div class="row g-3 mt-2">

        <div class="col-12 col-lg-8">
          <div class="nistmad-card p-4 h-100">

            <div class="nistmad-section-title">
              Estado del instrumento
            </div>

            <div class="d-flex justify-content-between align-items-start flex-wrap gap-3">
              <div>
                <div class="fw-bold">
                  Estado del instrumento {badge}
                </div>

                <div class="text-muted small mt-1">
                  Preguntas cargadas: <b>{total}</b>
                </div>

                <div class="mt-2 small">
                  {hint}
                </div>
              </div>

              <div class="text-end">
                <div class="text-muted small">Acceso rápido</div>
                <div class="d-flex gap-2 flex-wrap justify-content-end mt-2">
                  {parametros_btn}
                </div>
              </div>
            </div>

            <div class="alert alert-info mt-3 mb-0 small">
              <b>Sugerencia:</b> Usa <b>Parámetros</b> para importar el instrumento,
              administrar configuraciones y preparar la evaluación de madurez.
            </div>

          </div>
        </div>

        <div class="col-12 col-lg-4">
          <div class="nistmad-card p-4 h-100">

            <div class="nistmad-section-title">
              ¿Qué puedes hacer aquí?
            </div>

            <ul class="small mb-0 text-black ps-3">
              <li><b>Ingresar la información:</b> diligenciar respuestas (Sí/Parcial/No/N/A) con evidencia.</li>
              <li><b>Historial:</b> revisar evaluaciones previas y consultar informes generados.</li>
              <li><b>Parámetros:</b> gestionar el instrumento y configuraciones del módulo.</li>
            </ul>

          </div>
        </div>

      </div>

      <div class="row g-3 mt-3" id="historialRevisiones">
        <div class="col-12">
          <div class="nistmad-card p-4 h-100">

            <div class="nistmad-section-title">
              📚 Historial de Revisiones
            </div>

            <form class="row g-2 mb-3" method="GET" action="{url_for('madurez.home')}">
              <div class="col">
                <input class="form-control form-control-sm"
                       name="company"
                       value="{xml_escape(company)}"
                       placeholder="Filtrar por consecutivo...">
              </div>

              <div class="col-auto">
                <button class="btn btn-sm btn-outline-dark rounded-pill" type="submit">
                  Buscar
                </button>
              </div>
            </form>

            <div class="table-responsive nistmad-table-wrap" style="max-height:560px;overflow:auto;">
              <table class="table table-sm table-hover align-middle mb-0">
                <thead class="nistmad-table-head">
                  <tr>
                    <th>ID</th>
                    <th>Consecutivo</th>
                    <th>Archivo</th>
                    <th>Fecha</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {rows if rows else "<tr><td colspan='5' class='text-muted'>Aún no hay análisis guardados.</td></tr>"}
                </tbody>
              </table>
            </div>

          </div>
        </div>
      </div>

    </div>

    <style>
  html {{
    scroll-behavior:smooth;
  }}

      body {{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }}

      .nistmad-shell {{
        width:96%;
        max-width:1600px;
        margin:26px auto 24px auto;
      }}

      .nistmad-header-card {{
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

      .nistmad-header-card::before {{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }}

      .nistmad-header-overlay {{
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

      .nistmad-header-overlay::before {{
        content:"📊️";
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

      .nistmad-header-text {{
        max-width:1200px;
        width:100%;
        display:block !important;
        transform:none !important;
      }}

      .nistmad-header-text::before {{
        content:"SGSI · Madurez NIST CSF";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }}

      .nistmad-title {{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }}

      .nistmad-subtitle {{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }}

      .nistmad-header-actions {{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }}

      .nistmad-header-actions .btn,
      .nistmad-btn-main {{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }}

      .nistmad-btn-main {{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }}

      .nistmad-btn-main:hover {{
        background:#edf5ff;
        color:#0b65d8 !important;
        border-color:#9ec5fe !important;
      }}

      .nistmad-card {{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }}

      .nistmad-card .card-body {{
        padding:18px;
      }}

      .nistmad-section-title {{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:10px 0 12px;
      }}

      .nistmad-table-wrap {{
        max-height:72vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
      }}

      .nistmad-table-wrap .table {{
        margin-bottom:0;
      }}

      .nistmad-table-wrap thead th,
      .nistmad-table-head th {{
        position:sticky;
        top:0;
        z-index:10;
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff !important;
        font-weight:900;
        border:none !important;
        vertical-align:middle;
        white-space:nowrap;
        text-align:center;
        font-size:.78rem;
        padding:9px 8px;
      }}

      .nistmad-table-wrap tbody td {{
        vertical-align:middle;
        font-size:.82rem;
        padding:9px 8px;
        border-bottom:1px solid #e5edf7;
        color:#101827;
      }}

      .nistmad-table-wrap tbody tr:nth-child(even) {{
        background:#f8fbff;
      }}

      .nistmad-table-wrap tbody tr:hover {{
        background:#eef6ff;
      }}

      .wrap {{
        white-space:normal !important;
        word-break:break-word;
        overflow-wrap:anywhere;
      }}

      .form-label {{
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
      .form-select {{
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
        box-shadow:none !important;
      }}

      .form-control:focus,
      .form-select:focus {{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18) !important;
        background:#ffffff;
      }}

      .btn {{
        border-radius:10px !important;
        font-weight:900;
      }}

      .badge {{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }}

      @media (max-width:992px) {{
        .nistmad-shell {{
          width:98%;
          margin:8px auto 22px auto;
        }}

        .nistmad-header-card {{
          min-height:88px;
        }}

        .nistmad-title {{
          font-size:1.20rem;
        }}

        .nistmad-card .card-body {{
          padding:8px 7px;
        }}
      }}

      @media (max-width:768px) {{
        .nistmad-header-overlay {{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }}

        .nistmad-header-overlay::before {{
          margin:0;
        }}

        .nistmad-header-text::before {{
          margin-left:auto;
          margin-right:auto;
        }}

        .nistmad-header-actions .btn {{
          width:100%;
        }}
      }}
    </style>
    """

    return render_template_string(BASE, title="Nivel de Madurez ISO 27001:2022", content=content)

# ==========================
# ROUTES - PARÁMETROS
# ==========================
@madurez_bp.route("/parametros", methods=["GET"])
@login_required
def parametros_menu():
    content = f"""
    <div class="madpar-shell">

      <!-- CABECERA -->
      <div class="madpar-header-card">
        <div class="madpar-header-overlay">
          <div class="madpar-header-text">
            <h3 class="madpar-title m-0">Parámetros de Madurez – ISO 27001</h3>
            <div class="madpar-subtitle">
              Configuración del modelo de niveles de madurez, relación entre cumplimiento y madurez,
              y clasificación de niveles de brecha para el análisis del SGSI
            </div>
          </div>
        </div>
      </div>

      <!-- BOTÓN VOLVER -->
      <div class="madpar-header-actions">
          <a href="{url_for("madurez.home")}"
             class="btn madpar-btn-main rounded-pill px-5 fw-bold">
            ⬅ Inicio
          </a>
      </div>

      <div class="row g-3">

        <!-- MODELO MADUREZ -->
        <div class="col-lg-4">
          <div class="madpar-card p-4 h-100">
            <div class="madpar-section-title">Modelo nivel de madurez</div>

            <div class="text-muted small mb-3">
              Define el catálogo de niveles utilizados para clasificar la madurez
              del sistema de gestión de seguridad de la información.
            </div>

            <div class="text-center">
              <a class="btn btn-primary rounded-pill px-4 fw-semibold"
                 href="{url_for("madurez.param_maturity_levels")}">
                Gestionar
              </a>
            </div>
          </div>
        </div>

        <!-- RELACIÓN CUMPLIMIENTO -->
        <div class="col-lg-4">
          <div class="madpar-card p-4 h-100">
            <div class="madpar-section-title">2) Relación cumplimiento - Madurez</div>

            <div class="text-muted small mb-3">
              Define los rangos porcentuales que determinan el nivel de madurez
              según el porcentaje de cumplimiento obtenido en la evaluación.
            </div>

            <div class="text-center">
              <a class="btn btn-primary rounded-pill px-4 fw-semibold"
                 href="{url_for("madurez.param_compliance_map")}">
                Gestionar
              </a>
            </div>
          </div>
        </div>

        <!-- BRECHAS -->
        <div class="col-lg-4">
          <div class="madpar-card p-4 h-100">
            <div class="madpar-section-title">Calificación nivel de brecha</div>

            <div class="text-muted small mb-3">
              Define los rangos porcentuales de brecha que determinan el nivel
              de criticidad (Bajo, Medio, Alto o Crítico).
            </div>

            <div class="text-center">
              <a class="btn btn-primary rounded-pill px-4 fw-semibold"
                 href="{url_for("madurez.param_gap_levels")}">
                Gestionar
              </a>
            </div>
          </div>
        </div>

      </div>

      <!-- SEED -->
      <div class="madpar-card p-4 mt-3">
        <div class="madpar-section-title">🚀 Seed (carga rápida de parámetros base)</div>

        <div class="text-muted small mb-3">
          Si estás empezando, puedes cargar automáticamente los parámetros base del modelo:
          niveles de madurez, rangos de cumplimiento y clasificación de brechas.
        </div>

        <div class="d-flex justify-content-center">
          <a class="btn btn-outline-primary rounded-pill px-4 fw-semibold"
             href="{url_for("madurez.param_seed")}">
            Cargar parámetros base
          </a>
        </div>
      </div>

      <!-- IMPORTAR INSTRUMENTO -->
      <div class="madpar-card p-4 mt-3 text-center">
        <div class="madpar-section-title">Importar instrumento de evaluación</div>

        <div class="text-muted small mb-3">
          Este proceso importa el instrumento oficial de evaluación de madurez.
          Debe ejecutarse solo una vez durante la configuración inicial.
        </div>

        <form method="POST"
              action="{url_for('madurez.importar_instrumento_admin', force=1)}">

          <button class="btn btn-danger rounded-pill px-4 fw-semibold">
            <i class="bi bi-database-add me-2"></i>
            Importar instrumento
          </button>

        </form>
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

      .madpar-shell{{
        width:96%;
        max-width:1350px;
        margin:26px auto 24px auto;
      }}

      .madpar-header-card{{
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

      .madpar-header-card::before{{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }}

      .madpar-header-overlay{{
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

      .madpar-header-overlay::before{{
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
      }}

      .madpar-header-text{{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
      }}

      .madpar-header-text::before{{
        content:"SGSI · Parámetros de Madurez";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }}

      .madpar-title{{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }}

      .madpar-subtitle{{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }}

      .madpar-header-actions{{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }}

      .madpar-header-actions .btn,
      .madpar-btn-main{{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }}

      .madpar-btn-main{{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }}

      .madpar-btn-main:hover{{
        background:#edf5ff;
        color:#0b65d8 !important;
        border-color:#9ec5fe !important;
      }}

      .madpar-card{{
        background:rgba(255,255,255,.96)!important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }}

      .madpar-card .card-body{{
        padding:18px;
      }}

      .madpar-section-title{{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        padding:9px 12px;
        border-radius:12px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        margin:10px 0 12px;
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

      .input-group-text{{
        border-radius:0 10px 10px 0;
        background:#eef5ff;
        border:1px solid #d9eaff;
        color:#0b4a8f;
        font-weight:900;
      }}

      .badge{{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }}

      .btn{{
        border-radius:10px !important;
        font-weight:900;
      }}

      @media (max-width:992px){{
        .madpar-shell{{
          width:98%;
          margin:8px auto 22px auto;
        }}

        .madpar-header-card{{
          min-height:88px;
        }}

        .madpar-title{{
          font-size:1.20rem;
        }}

        .madpar-card .card-body{{
          padding:8px 7px;
        }}
      }}

      @media (max-width:768px){{
        .madpar-header-overlay{{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }}

        .madpar-header-overlay::before{{
          margin:0;
        }}

        .madpar-header-text::before{{
          margin-left:auto;
          margin-right:auto;
        }}

        .madpar-header-actions .btn{{
          width:100%;
        }}
      }}
    </style>
    """
    return render_template_string(BASE, title="Parámetros", content=content)


@madurez_bp.route("/parametros/seed", methods=["GET"])
@login_required
def param_seed():
    # No duplica si ya hay datos
    if MaturityLevel.query.count() == 0:
        db.session.add_all([
            MaturityLevel(nivel=1, madurez="Inicial", descripcion="Prácticas ad-hoc o inexistentes; evidencia limitada."),
            MaturityLevel(nivel=2, madurez="En desarrollo", descripcion="Implementación parcial; evidencia inconsistente."),
            MaturityLevel(nivel=3, madurez="Gestionado", descripcion="Proceso definido y repetible; evidencia consistente."),
            MaturityLevel(nivel=4, madurez="Óptimo", descripcion="Mejora continua; medición y control maduros."),
        ])
        db.session.commit()

    if ComplianceMaturityMap.query.count() == 0:
        lv = {x.madurez: x.id for x in MaturityLevel.query.all()}
        # Rangos recomendados (contiguos)
        db.session.add_all([
            ComplianceMaturityMap(pct_min=0,  pct_max=39, maturity_id=lv.get("Inicial")),
            ComplianceMaturityMap(pct_min=40, pct_max=59, maturity_id=lv.get("En desarrollo")),
            ComplianceMaturityMap(pct_min=60, pct_max=79, maturity_id=lv.get("Gestionado")),
            ComplianceMaturityMap(pct_min=80, pct_max=100, maturity_id=lv.get("Óptimo")),
        ])
        db.session.commit()

    if GapLevelConfig.query.count() == 0:
        db.session.add_all([
            GapLevelConfig(pct_min=0,  pct_max=24, nivel_brecha="Bajo",    interpretacion="Brecha menor; mantener y asegurar vigencia."),
            GapLevelConfig(pct_min=25, pct_max=49, nivel_brecha="Medio",   interpretacion="Brecha moderada; requiere acciones planificadas."),
            GapLevelConfig(pct_min=50, pct_max=79, nivel_brecha="Alto",    interpretacion="Brecha alta; priorizar cierre y evidencias."),
            GapLevelConfig(pct_min=80, pct_max=100, nivel_brecha="Critico", interpretacion="Brecha crítica; alto riesgo de incumplimiento/impacto."),
        ])
        db.session.commit()

    flash("✅ Parámetros base cargados (si estaban vacíos).", "success")
    return redirect(url_for("madurez.parametros_menu"))

# ===============================
# Pantalla Ingreso de información
# ===============================

@madurez_bp.route("/ingreso", methods=["GET"])
@login_required
def ingreso():
    user = User.query.get(session.get("user_id"))

    # =========================
    # PERMISOS
    # =========================
    if user and user.role not in ("admin", "auditor") and not verificar_permiso(user, "Nivel de Madurez ISO 27001:2022"):
        flash("No tiene permiso para acceder al módulo de nivel de madurez ISO 27001:2022.", "danger")
        return redirect(url_for("menu"))

    if user and user.role == "auditor":
        flash("El rol Auditor no puede ingresar la información en este módulo.", "warning")
        return redirect(url_for("madurez.home"))

    preguntas = MadurezPregunta.query.order_by(
        MadurezPregunta.orden.asc()
    ).all()

    if not preguntas:
        content = """
        <div class="alert alert-warning">
          No hay instrumento cargado en la base de datos.
          (Admin) Importa el instrumento para habilitar el formulario.
        </div>
        """
        return render_template_string(BASE, title=APP_TITLE, content=content)

    # =========================
    # CARGAR BORRADOR ACTIVO
    # =========================
    draft = obtener_borrador_madurez(user.id if user else None)
    respuestas_guardadas = cargar_respuestas_run(draft.id) if draft else {}

    company_name_value = (draft.company_name if draft else "") or ""

    _, _, progreso_inicial = calcular_progreso_formulario(
        preguntas,
        respuestas_db=respuestas_guardadas
    )

    # =========================
    # AGRUPAR POR HOJA
    # =========================
    by_sheet = {}
    for p in preguntas:
        by_sheet.setdefault((p.sheet or "Sin categoría"), []).append(p)

    acc_html = []
    acc_id = 0

    def esc(x):
        return escape(x or "")

    for sheet, items in by_sheet.items():
        acc_id += 1
        sheet_key = f"sheet{acc_id}"
        inner_blocks = []

        items = sorted(items, key=lambda x: (x.orden or 0))

        current_header = ""
        rows = []

        def flush_block():
            nonlocal rows, current_header, inner_blocks

            if not rows:
                return

            inner_blocks.append(f"""
            <div class="isoform-cat-block">
              <div class="isoform-cat-title">
                <div>
                  <div class="isoform-cat-code">{esc(sheet)}</div>
                  <div class="isoform-cat-name">{esc(current_header)}</div>
                </div>
                <div>
                  <span class="badge rounded-pill text-bg-secondary">{len(rows)} preguntas</span>
                </div>
              </div>

              <div class="row g-3">
                {''.join(rows)}
              </div>
            </div>
            """)

            rows = []

        for p in items:
            if p.tipo == "h":
                flush_block()
                current_header = p.pregunta or ""
                continue

            if p.tipo != "q":
                continue

            saved = respuestas_guardadas.get(p.id, {})
            saved_opt = (saved.get("opcion") or "").strip().upper()
            saved_com = esc(saved.get("comentario") or "")

            chk_na = "checked" if saved_opt == "NA" else ""
            chk_si = "checked" if saved_opt == "SI" else ""
            chk_pa = "checked" if saved_opt == "PAR" else ""
            chk_no = "checked" if saved_opt == "NO" else ""

            question_badge = f"Orden {p.orden or 0}"
            question_text = p.pregunta or ""

            rows.append(f"""
            <div class="col-12 col-xl-6">
              <div class="isoform-qcard h-100">

                <div class="isoform-qhead">
                  <div class="d-flex align-items-center gap-2 flex-wrap">
                    <span class="badge rounded-pill text-bg-light border fw-semibold">
                      {esc(sheet)}
                    </span>
                    <span class="badge rounded-pill text-bg-primary">
                      {esc(question_badge)}
                    </span>
                  </div>
                </div>

                <div class="isoform-qtext">
                  {esc(question_text)}
                </div>

                <div class="isoform-radio-row">
                  <label class="isoform-radio-card">
                    <input class="form-check-input" type="radio" name="r_{p.id}" value="NA" {chk_na}>
                    <span>N/A</span>
                  </label>

                  <label class="isoform-radio-card">
                    <input class="form-check-input" type="radio" name="r_{p.id}" value="SI" {chk_si}>
                    <span>Sí</span>
                  </label>

                  <label class="isoform-radio-card">
                    <input class="form-check-input" type="radio" name="r_{p.id}" value="PAR" {chk_pa}>
                    <span>Parcial</span>
                  </label>

                  <label class="isoform-radio-card">
                    <input class="form-check-input" type="radio" name="r_{p.id}" value="NO" {chk_no}>
                    <span>No</span>
                  </label>
                </div>

                <div class="mt-3">
                  <label class="form-label small fw-bold text-black mb-1">
                    Comentarios / evidencia
                  </label>

                  <textarea class="form-control form-control-sm"
                            name="c_{p.id}"
                            rows="3"
                            placeholder="Comentarios / evidencia">{saved_com}</textarea>
                </div>

              </div>
            </div>
            """)

        flush_block()

        if not inner_blocks:
            inner_blocks.append("""
            <div class="alert alert-light border rounded-4 mb-0">
              No hay preguntas disponibles en esta sección.
            </div>
            """)

        acc_html.append(f"""
        <div class="accordion-item isoform-acc-item">
          <h2 class="accordion-header" id="h{sheet_key}">
            <button class="accordion-button {'collapsed' if acc_id != 1 else ''} isoform-acc-btn"
                    type="button"
                    data-bs-toggle="collapse"
                    data-bs-target="#c{sheet_key}"
                    aria-expanded="{str(acc_id == 1).lower()}"
                    aria-controls="c{sheet_key}">
              <div class="isoform-acc-inner">
                <div class="isoform-acc-title-wrap">
                  <i class="bi bi-folder2-open me-2"></i>
                  <span class="isoform-acc-title">{esc(sheet)}</span>
                </div>

                <span class="badge rounded-pill text-bg-light border">
                  {sum(1 for x in items if x.tipo == 'q')} preguntas
                </span>
              </div>
            </button>
          </h2>

          <div id="c{sheet_key}"
               class="accordion-collapse collapse {'show' if acc_id == 1 else ''}">
            <div class="accordion-body isoform-acc-body">
              {''.join(inner_blocks)}
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
    <div class="isoform-shell">

      <div class="isoform-header-card">
        <div class="isoform-header-overlay">
          <div class="isoform-header-text">
            <h3 class="isoform-title m-0">Nivel de Madurez — ISO 27001:2022</h3>
            <div class="isoform-subtitle">
              Registro de respuestas del instrumento de evaluación del SGSI
              basado en ISO 27001:2022 para su posterior análisis y generación de resultados.
            </div>
          </div>
        </div>
      </div>

      <div class="isoform-header-actions">
        <a href="{url_for('madurez.home')}"
           class="btn isoform-btn-main rounded-pill px-4 fw-bold">
          <i class="bi bi-arrow-left me-2"></i>Volver a Madurez ISO
        </a>
      </div>

      <div class="isoform-card p-4">

        {alerta_borrador}

        <form id="isoIngresoForm"
              method="POST"
              action="{url_for('madurez.ingreso_guardar')}"
              novalidate
              autocomplete="off">

          <input type="hidden" name="draft_id" value="{draft.id if draft else ''}">

          <div class="isoform-section-title">
            Información de la revisión
          </div>

          <div class="mb-4">
            <label class="text-black form-label fw-semibold" for="isoConsecutivoRevision">
              Consecutivo de la Revisión <span class="text-danger">*</span>
            </label>

            <input type="text"
                   class="form-control"
                   name="company_name"
                   id="isoConsecutivoRevision"
                   value="{esc(company_name_value)}"
                   autocomplete="off"
                   required>

            <div id="isoConsecutivoRevisionError"
                 class="invalid-feedback d-none fw-bold mt-2">
              Debes ingresar el consecutivo de la Revisión.
            </div>
          </div>

          <div class="isoform-section-title">
            📊 Progreso del instrumento
          </div>

          <div class="mb-4">
            <div class="progress isoform-progress">
              <div id="instrumentProgressBar"
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
              <span id="instrumentProgressText">{progreso_inicial}%</span> del instrumento completado
            </div>
          </div>

          <div class="isoform-section-title">
            Instrumento de evaluación
          </div>

          <div class="accordion isoform-accordion" id="accInstrumentoIso">
            {''.join(acc_html)}
          </div>

          <div class="d-flex justify-content-center gap-3 flex-wrap mt-4">

            <button id="btnGuardar"
                    class="btn btn-outline-primary btn-lg rounded-pill px-5 shadow fw-semibold iso-submit-btn"
                    type="submit"
                    name="accion"
                    value="guardar"
                    data-accion="guardar">
              <i class="bi bi-save2 me-2"></i>
              Guardar
            </button>

            <button id="btnAnalizar"
                    class="btn btn-primary btn-lg rounded-pill px-5 shadow fw-semibold iso-submit-btn"
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

        let ISO_BLOQUEAR_LOADER = false;

        function isoOcultarLoaderGlobal() {{
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

        function isoValidarConsecutivoRevision() {{
            const input = document.getElementById("isoConsecutivoRevision");
            const error = document.getElementById("isoConsecutivoRevisionError");

            const valor = input ? input.value.trim() : "";

            if (!valor) {{
                ISO_BLOQUEAR_LOADER = true;
                isoOcultarLoaderGlobal();

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

            ISO_BLOQUEAR_LOADER = false;

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

        function actualizarProgresoInstrumento() {{
            const radios = document.querySelectorAll('input[type="radio"][name^="r_"]');
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

            const bar = document.getElementById("instrumentProgressBar");
            const text = document.getElementById("instrumentProgressText");
            const btnAnalizar = document.getElementById("btnAnalizar");

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

        /*
          BLOQUEO DE LOADERS EXTERNOS:
          Si en BASE existe showLoader(), showGlobalLoader(), mostrarLoader(), etc.,
          se interceptan para que NO aparezcan cuando el consecutivo está vacío.
        */
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

            if (typeof original === "function" && !original.__isoInterceptado) {{
                const wrapper = function() {{
                    if (ISO_BLOQUEAR_LOADER || !isoValidarConsecutivoRevision()) {{
                        isoOcultarLoaderGlobal();
                        return false;
                    }}

                    return original.apply(this, arguments);
                }};

                wrapper.__isoInterceptado = true;
                window[nombreFuncion] = wrapper;
            }}
        }});

        document.addEventListener("change", function(e) {{
            if (e.target.matches('input[type="radio"][name^="r_"]')) {{
                actualizarProgresoInstrumento();
            }}
        }});

        document.addEventListener("click", function(e) {{
            const btn = e.target.closest(".iso-submit-btn");

            if (!btn) {{
                return;
            }}

            if (!isoValidarConsecutivoRevision()) {{
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();

                ISO_BLOQUEAR_LOADER = true;
                isoOcultarLoaderGlobal();

                return false;
            }}
        }}, true);

        window.addEventListener("DOMContentLoaded", function() {{
            const form = document.getElementById("isoIngresoForm");
            const input = document.getElementById("isoConsecutivoRevision");

            if (input) {{
                input.addEventListener("input", function() {{
                    isoValidarConsecutivoRevision();
                }});

                input.addEventListener("blur", function() {{
                    isoValidarConsecutivoRevision();
                }});
            }}

            if (form) {{
                form.addEventListener("submit", function(e) {{
                    if (!isoValidarConsecutivoRevision()) {{
                        e.preventDefault();
                        e.stopPropagation();
                        e.stopImmediatePropagation();

                        ISO_BLOQUEAR_LOADER = true;
                        isoOcultarLoaderGlobal();

                        return false;
                    }}
                }}, true);
            }}

            actualizarProgresoInstrumento();
            isoOcultarLoaderGlobal();
        }});

        window.addEventListener("pageshow", function() {{
            isoOcultarLoaderGlobal();
        }});

    }})();
    </script>

    <style>
      body {{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }}

      .isoform-shell {{
        width:96%;
        max-width:1600px;
        margin:26px auto 24px auto;
      }}

      .isoform-header-card {{
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

      .isoform-header-card::before {{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
      }}

      .isoform-header-overlay {{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        position:relative;
        z-index:1;
      }}

      .isoform-header-overlay::before {{
        content:"📌";
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
      }}

      .isoform-header-text::before {{
        content:"SGSI · Evaluación ISO";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#fff;
      }}

      .isoform-title {{
        color:#fff;
        font-weight:950;
        font-size:1.32rem;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
      }}

      .isoform-subtitle {{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
      }}

      .isoform-header-actions {{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }}

      .isoform-btn-main {{
        background:#fff;
        color:#0f172a;
        border:1px solid #cfd8e3;
        border-radius:10px;
        padding:8px 22px;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }}

      .isoform-btn-main:hover {{
        background:#edf5ff;
        color:#0b65d8;
      }}

      .isoform-card {{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
      }}

      .isoform-card.p-4 {{
        padding:18px !important;
      }}

      .isoform-section-title {{
        font-weight:950;
        font-size:.78rem;
        color:#0b4a8f;
        background:#eef5ff;
        border:1px solid #d9eaff;
        padding:9px 12px;
        border-radius:12px;
        margin-bottom:12px;
      }}

      .isoform-progress {{
        height:22px;
        border-radius:999px;
        overflow:hidden;
        background:#e5edf7;
      }}

      .progress-bar {{
        font-weight:900;
      }}

      .form-label {{
        font-size:.72rem;
        font-weight:900;
        color:#0b4a8f;
        background:#eef5ff;
        border:1px solid #d9eaff;
        padding:6px 10px;
        border-radius:10px;
      }}

      .form-control,
      .form-select {{
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        background:#f8fafc;
      }}

      .form-control:focus,
      .form-select:focus {{
        border-color:#3f86d6;
        box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
        background:#fff;
      }}

      .form-control.is-invalid {{
        border-color:#dc3545 !important;
        background:#fff5f5 !important;
        box-shadow:0 0 0 .15rem rgba(220,53,69,.15) !important;
      }}

      .invalid-feedback {{
        color:#b42318;
        background:#fff1f1;
        border:1px solid #ffd4d4;
        border-radius:10px;
        padding:8px 12px;
      }}

      .isoform-acc-item {{
        border:1px solid #dbe6f4;
        background:#fff;
        border-radius:16px;
        margin-bottom:14px;
        box-shadow:0 6px 14px rgba(0,0,0,.06);
        overflow:hidden;
      }}

      .isoform-acc-btn {{
        background:#eef5ff;
        font-weight:900;
        padding:16px 18px;
        border-bottom:1px solid #dbe6f4;
      }}

      .isoform-acc-btn:not(.collapsed) {{
        background:#dbeafe;
      }}

      .isoform-acc-inner {{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:12px;
      }}

      .isoform-acc-title-wrap {{
        display:flex;
        align-items:center;
        gap:4px;
      }}

      .isoform-acc-title {{
        font-weight:950;
        color:#0f172a;
      }}

      .isoform-acc-body {{
        padding:16px;
      }}

      .isoform-cat-block {{
        background:#f8fbff;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:8px 7px;
        margin-bottom:14px;
      }}

      .isoform-cat-title {{
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:12px;
        margin-bottom:14px;
        border-bottom:1px solid #e5edf7;
        padding-bottom:10px;
      }}

      .isoform-cat-code {{
        font-size:.72rem;
        font-weight:950;
        color:#0b4a8f;
      }}

      .isoform-cat-name {{
        font-size:.95rem;
        font-weight:950;
        color:#0f172a;
      }}

      .isoform-qcard {{
        background:#fff;
        border:1px solid #e5edf7;
        border-radius:14px;
        padding:8px 7px;
        transition:.2s;
      }}

      .isoform-qcard:hover {{
        transform:translateY(-2px);
        box-shadow:0 8px 18px rgba(0,0,0,.08);
      }}

      .isoform-qhead {{
        margin-bottom:10px;
      }}

      .isoform-qtext {{
        color:#0f172a;
        font-weight:800;
        font-size:.86rem;
        line-height:1.45;
      }}

      .isoform-radio-row {{
        display:grid;
        grid-template-columns:repeat(4,1fr);
        gap:10px;
        margin-top:14px;
      }}

      .isoform-radio-card {{
        background:#f8fafc;
        border:1px solid #dbe4ee;
        border-radius:12px;
        display:flex;
        justify-content:center;
        align-items:center;
        gap:6px;
        padding:10px;
        font-weight:800;
        cursor:pointer;
        transition:.2s;
      }}

      .isoform-radio-card:hover {{
        background:#eef6ff;
        border-color:#93c5fd;
      }}

      .isoform-radio-card input:checked + span {{
        color:#0b4a8f;
        font-weight:950;
      }}

      @media (max-width:1200px) {{
        .isoform-radio-row {{
          grid-template-columns:repeat(2,1fr);
        }}
      }}

      @media (max-width:768px) {{
        .isoform-radio-row {{
          grid-template-columns:1fr;
        }}

        .isoform-header-overlay {{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }}

        .isoform-header-overlay::before {{
          margin-right:0;
        }}

        .isoform-acc-inner {{
          flex-direction:column;
          align-items:flex-start;
        }}
      }}
    </style>
    """

    return render_template_string(BASE, title=APP_TITLE, content=content)

# ===============================
# Pantalla Ingreso Guardar / Analizar
# ===============================

@madurez_bp.route("/ingreso/guardar", methods=["POST"])
@login_required
def ingreso_guardar():
    user = User.query.get(session.get("user_id"))

    company_name = (request.form.get("company_name") or "").strip()
    accion = (request.form.get("accion") or "guardar").strip().lower()
    draft_id = (request.form.get("draft_id") or "").strip()

    if not company_name:
        flash("Debes ingresar el consecutivo de la Revisión.", "warning")
        return redirect(url_for("madurez.ingreso"))

    preguntas = MadurezPregunta.query.order_by(MadurezPregunta.orden.asc()).all()
    preguntas_q = [p for p in preguntas if p.tipo == "q"]

    respondidas, total, progreso_pct = calcular_progreso_formulario(
        preguntas,
        form_data=request.form
    )

    try:
        run_form = None

        if draft_id:
            run_form = MadurezRun.query.filter_by(id=int(draft_id)).first()

            if run_form and user and run_form.user_id != user.id:
                flash("No tienes permiso para modificar este borrador.", "danger")
                return redirect(url_for("madurez.ingreso"))

        if not run_form:
            run_form = obtener_borrador_madurez(user.id if user else None)

        if not run_form:
            run_form = MadurezRun(
                company_name=company_name,
                user_id=user.id if user else None,
                estado="BORRADOR",
                progreso_pct=0
            )
            db.session.add(run_form)
            db.session.flush()

        run_form.company_name = company_name
        run_form.progreso_pct = progreso_pct
        run_form.updated_at = datetime.now(timezone.utc)

        MadurezRespuesta.query.filter_by(run_id=run_form.id).delete()

        for p in preguntas_q:
            opcion = (request.form.get(f"r_{p.id}") or "").strip().upper()
            comentario = (request.form.get(f"c_{p.id}") or "").strip()

            if opcion:
                db.session.add(MadurezRespuesta(
                    run_id=run_form.id,
                    pregunta_id=p.id,
                    opcion=opcion,
                    comentario=comentario
                ))

        db.session.flush()

        if accion == "guardar":
            run_form.estado = "BORRADOR"
            db.session.commit()
            flash(f"✅ Borrador guardado correctamente. Progreso actual: {progreso_pct}%.", "success")
            return redirect(url_for("madurez.ingreso"))

        if accion == "analizar":
            if progreso_pct < 100 or respondidas < total:
                db.session.commit()
                flash(
                    f"⚠️ El análisis solo se habilita cuando el instrumento esté al 100%. Actualmente llevas {progreso_pct}%.",
                    "warning"
                )
                return redirect(url_for("madurez.ingreso"))

            run_form.estado = "FINALIZADO"
            run_form.progreso_pct = 100
            db.session.commit()

            df = build_df_from_db(run_form.id)
            analysis_run_id = run_analysis_from_df(company_name, df)

            try:
                resultado_nist = calcular_nist_desde_iso(analysis_run_id)
                if resultado_nist:
                    nuevo_nist = NistAnalysisRun(
                        iso_analysis_id=analysis_run_id,
                        nivel_promedio_general=resultado_nist["nivel_general"],
                        resultados_json=json.dumps(resultado_nist["detalle"], ensure_ascii=False)
                    )
                    db.session.add(nuevo_nist)
                    db.session.commit()
            except Exception as e:
                print("⚠️ Error generando NIST automáticamente:", e)

            flash("✅ Información guardada y análisis generado correctamente.", "success")
            return redirect(url_for("madurez.view_report", run_id=analysis_run_id))

        db.session.commit()
        flash("✅ Información procesada correctamente.", "success")
        return redirect(url_for("madurez.ingreso"))

    except Exception as e:
        db.session.rollback()
        flash(f"⚠️ Error en el proceso: {e}", "danger")
        return redirect(url_for("madurez.ingreso"))

def build_df_from_db(run_id: int):
    import pandas as pd

    rows = db.session.query(
        MadurezPregunta.sheet,
        MadurezPregunta.seccion,
        MadurezPregunta.control,
        MadurezPregunta.tema,
        MadurezPregunta.pregunta,
        MadurezRespuesta.opcion,
        MadurezRespuesta.comentario
    ).join(
        MadurezRespuesta, MadurezRespuesta.pregunta_id == MadurezPregunta.id
    ).filter(
        MadurezRespuesta.run_id == run_id,
        MadurezPregunta.tipo == "q"
    ).order_by(
        MadurezPregunta.orden.asc()
    ).all()

    data = []
    for r in rows:
        sheet_name = (r.sheet or "").strip()
        control_val = (r.control or "").strip()

        if sheet_name.upper() == "ANEXO A":
            control_val = normalize_anexo_control(control_val, r.tema or "")
            
        data.append({
            "Sheet": sheet_name,
            "Seccion": r.seccion,
            "Control": control_val,
            "Tema": r.tema,
            "Pregunta": r.pregunta,
            "Respuesta": r.opcion,
            "Comentarios": r.comentario
        })

    return pd.DataFrame(data)

def _status_score_from_option(opt: str):
    """
    Convierte opción del formulario (NA/SI/PAR/NO) a status y score.
    Mantiene consistencia con tu motor.
    """
    opt = (opt or "").strip().upper()
    if opt == "NA":
        return "NA", 0
    if opt == "SI":
        return "SI", 100
    if opt == "PAR":
        return "PAR", 50
    if opt == "NO":
        return "NO", 0
    # fallback (no debería pasar si el radio es required)
    return "SIN_MARCAR", 0


def parse_sheet_df(df_sheet: "pd.DataFrame", sheet_name: str):
    """
    Emula parse_sheet_xls pero usando DataFrame (BD/formulario).
    Espera columnas: Sheet, Seccion, Control, Tema, Pregunta, Respuesta, Comentarios
    Retorna: items, pct, done, total, detail_map
    """
    items = []
    detail_map = {}

    # normaliza columnas por seguridad
    cols = {c.lower(): c for c in df_sheet.columns}
    col_seccion = cols.get("seccion", "Seccion")
    col_control = cols.get("control", "Control")
    col_tema = cols.get("tema", "Tema")
    col_preg = cols.get("pregunta", "Pregunta")
    col_resp = cols.get("respuesta", "Respuesta")
    col_comm = cols.get("comentarios", "Comentarios")

    for i, row in df_sheet.iterrows():
        pregunta = (row.get(col_preg) or "").strip()
        if not pregunta:
            continue

        opcion = (row.get(col_resp) or "").strip().upper()
        comentario = (row.get(col_comm) or "").strip()

        status, score = _status_score_from_option(opcion)
        applicable = (status != "NA")

        seccion = (row.get(col_seccion) or "").strip()
        control = (row.get(col_control) or "").strip()
        tema = (row.get(col_tema) or "").strip()

        # ----- control_id compatible con tu reporte -----
        # Para ANEXO A: prefijo "A." para no mezclar con 4-10
        control_id = "Sin control"
        if (sheet_name or "").strip().upper() == "ANEXO A":
            c = (control or "").strip()
            # Solo aceptar numerales tipo 5.1, 5.16, 8.34, etc.
            if re.match(r"^\d+\.\d+$", c):
                control_id = f"A.{c}"
            else:
                control_id = "SIN CONTROL"   # 👈 sin prefijo A.
        else:
            m = re.match(r"^(\d+\.\d+)", seccion)
            control_id = m.group(1) if m else (sheet_name or "Sin control")


        item = {
            "sheet": sheet_name,
            "row": int(i) + 1,
            "ref": "",                 # no hay ref de Excel aquí
            "requisito": pregunta,     # lo que evalúas
            "applicable": bool(applicable),
            "status": status,
            "score": int(score),
            "comment": comentario,
            "procesos": "",            # si luego lo agregas al form, lo conectas aquí
            "brecha_pct": brecha_pct_from_status(status),
            "brecha_nivel": "",        # se puede completar luego si quieres
            "brecha_interp": "",
            "control_id": control_id,
            "item_id": "",             # opcional
            "subitem_id": "",          # opcional
        }
        items.append(item)

    applicable_items = [it for it in items if it["status"] != "NA"]
    total = len(applicable_items)
    done = sum(1 for it in applicable_items if it["status"] == "SI")
    score_sum = sum(it["score"] for it in applicable_items)
    pct = (score_sum / (total * 100.0) * 100.0) if total > 0 else 0.0

    return items, float(round(pct, 2)), int(done), int(total), detail_map


def run_analysis_from_df(company_name: str, df: "pd.DataFrame") -> int:
    """
    Ejecuta el MISMO flujo de análisis que /analyze, pero usando DF (formulario/BD).
    Crea un AnalysisRun y retorna su ID.
    """
    chapter_results = {}
    all_items = []

    # IMPORTANT: df["Sheet"] puede venir con mayúsc/minúsc. Normalizamos.
    df = df.copy()
    if "Sheet" in df.columns:
        df["Sheet"] = df["Sheet"].astype(str)

    for sh in CHAPTER_SHEETS:
        df_sh = df[df["Sheet"].str.strip().str.upper() == str(sh).strip().upper()]
        items, pct, done, total, _detail_map = parse_sheet_df(df_sh, sh)

        gap_info = gap_from_maturity_pct(pct)
        chapter_results[sh] = {
            "pct": pct,
            "done": done,
            "total": total,
            "brecha_pct": gap_info["gap_pct"],
            "brecha_nivel": gap_info["nivel_brecha"],
            "brecha_interp": gap_info["interpretacion"],
        }
        all_items.extend(items)

    gaps = [it for it in all_items if it.get("applicable") and it.get("status") != "SI"]

    control_results = aggregate_by_control(all_items)

    control_items = {}
    for it in all_items:
        cid = (it.get("control_id") or "").strip() or "Sin control"
        control_items.setdefault(cid, []).append({
            "sheet": it.get("sheet"),
            "row": it.get("row"),
            "ref": it.get("ref"),
            "requisito": it.get("requisito"),
            "applicable": bool(it.get("applicable", True)),
            "status": it.get("status"),
            "score": int(it.get("score", 0) or 0),
            "comment": it.get("comment"),
            "procesos": it.get("procesos"),
            "brecha_pct": it.get("brecha_pct"),
            "brecha_nivel": it.get("brecha_nivel"),
            "brecha_interp": it.get("brecha_interp"),
            "item_id": it.get("item_id", ""),
            "subitem_id": it.get("subitem_id", ""),
        })

    item_results = build_item_results(control_items)

    gaps_by_control = {}
    for g in gaps:
        cid = (g.get("control_id") or "").strip() or "Sin control"
        gaps_by_control.setdefault(cid, []).append(g)

    labels = list(chapter_results.keys())
    values = [chapter_results[k]["pct"] for k in labels]

    radar_overall_b64 = make_radar_base64(labels, values, title="Araña Consolidada – ISO 27001:2022")

    bar_chapters_b64 = make_bar_chapters_plus_annexA_with_box_base64(
        chapter_results=chapter_results,
        control_results=control_results,
        title="Madurez por capítulo + Anexo A (%)"
    )

    bar_controls_4_10_b64 = make_bar_controls_4_10_base64(control_results)

    extra_graphs = {
        "bar_chapters": bar_chapters_b64,
        "bar_controls_4_10": bar_controls_4_10_b64,
    }

    run = AnalysisRun(
        company_name=company_name,
        filename="FORMULARIO",
        excel_path="",
        chapter_results_json=json.dumps(chapter_results, ensure_ascii=False),
        gaps_json=json.dumps(gaps, ensure_ascii=False),
        control_results_json=json.dumps(control_results, ensure_ascii=False),
        gaps_by_control_json=json.dumps(gaps_by_control, ensure_ascii=False),
        control_items_json=json.dumps(control_items, ensure_ascii=False),
        item_results_json=json.dumps(item_results, ensure_ascii=False),
        control_ai_json="{}",
        item_ai_json="{}",
        radar_overall_b64=radar_overall_b64,
        radar_by_sheet_json=json.dumps(extra_graphs, ensure_ascii=False),
        executive_summary=None,
        ai_report_text=None,
        action_plan_json=None,
    )

    db.session.add(run)
    db.session.commit()
    return int(run.id)

# ===============================
# Analysis
# ===============================

@madurez_bp.route("/analyze", methods=["POST"])
@login_required
def analyze():
    company_name = (request.form.get("company_name") or "").strip()
    if not company_name:
        flash("Debes ingresar el nombre de la empresa.", "warning")
        return redirect(url_for("madurez.home"))

    file = request.files.get("file")
    if not file or file.filename == "":
        flash("Debes seleccionar un archivo .xls.", "warning")
        return redirect(url_for("madurez.home"))

    if not allowed_file(file.filename):
        flash("Formato inválido. Solo se permite .xls.", "danger")
        return redirect(url_for("madurez.home"))

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_name = re.sub(r"[^a-zA-Z0-9._-]+", "_", file.filename)
    safe_company = re.sub(r"[^a-zA-Z0-9._-]+", "_", company_name)[:80]
    excel_path = os.path.join(UPLOAD_DIR, f"{ts}_{safe_company}_{safe_name}")
    file.save(excel_path)

    chapter_results = {}
    all_items = []

    for sh in CHAPTER_SHEETS:
        try:
            items, pct, done, total, _detail_map = parse_sheet_xls(excel_path, sh)
        except Exception as e:
            flash(f"Error leyendo hoja '{sh}': {e}", "danger")
            return redirect(url_for("madurez.home"))

        gap_info = gap_from_maturity_pct(pct)
        chapter_results[sh] = {
            "pct": pct,
            "done": done,
            "total": total,

            # ✅ NUEVO: brecha por capítulo
            "brecha_pct": gap_info["gap_pct"],
            "brecha_nivel": gap_info["nivel_brecha"],
            "brecha_interp": gap_info["interpretacion"],
        }

        all_items.extend(items)

    # Brechas “aplicables no SI”
    gaps = [it for it in all_items if it.get("applicable") and it.get("status") != "SI"]

    # ✅ Resultados por Control (FIX)
    control_results = aggregate_by_control(all_items)

    # ✅ Guardar preguntas por control (FIX: guardar TODO, incluso NA; el KPI excluye NA)
    control_items = {}
    for it in all_items:
        cid = (it.get("control_id") or "").strip() or "Sin control"
        control_items.setdefault(cid, []).append({
            "sheet": it.get("sheet"),
            "row": it.get("row"),
            "ref": it.get("ref"),
            "requisito": it.get("requisito"),
            "applicable": bool(it.get("applicable", True)),
            "status": it.get("status"),
            "score": int(it.get("score", 0) or 0),
            "comment": it.get("comment"),
            "procesos": it.get("procesos"),
            "brecha_pct": it.get("brecha_pct"),
            "brecha_nivel": it.get("brecha_nivel"),
            "brecha_interp": it.get("brecha_interp"),
            "item_id": it.get("item_id", ""),
            "subitem_id": it.get("subitem_id", ""),
        })
    item_results = build_item_results(control_items)

    # Brechas por Control (compat)
    gaps_by_control = {}
    for g in gaps:
        cid = (g.get("control_id") or "").strip() or "Sin control"
        gaps_by_control.setdefault(cid, []).append(g)

    labels = list(chapter_results.keys())
    values = [chapter_results[k]["pct"] for k in labels]

    radar_overall_b64 = make_radar_base64(labels, values, title="Araña Consolidada – ISO 27001:2022")

    bar_chapters_b64 = make_bar_chapters_plus_annexA_with_box_base64(
        chapter_results=chapter_results,
        control_results=control_results,
        title="Madurez por capítulo + Anexo A (%)"
    )

    # ✅ NUEVO: barras por control (4–10) y resumen Anexo A (peores N)
    bar_controls_4_10_b64 = make_bar_controls_4_10_base64(control_results)

    extra_graphs = {
        "bar_chapters": bar_chapters_b64,
        "bar_controls_4_10": bar_controls_4_10_b64,
    }

    run = AnalysisRun(
        company_name=company_name,
        filename=file.filename,
        excel_path=excel_path,
        chapter_results_json=json.dumps(chapter_results, ensure_ascii=False),
        gaps_json=json.dumps(gaps, ensure_ascii=False),
        control_results_json=json.dumps(control_results, ensure_ascii=False),
        gaps_by_control_json=json.dumps(gaps_by_control, ensure_ascii=False),
        control_items_json=json.dumps(control_items, ensure_ascii=False),
        item_results_json=json.dumps(item_results, ensure_ascii=False),
        control_ai_json="{}",
        item_ai_json="{}",
        radar_overall_b64=radar_overall_b64,
        radar_by_sheet_json=json.dumps(extra_graphs, ensure_ascii=False),
        executive_summary=None,
        ai_report_text=None,
        action_plan_json=None,
    )

    db.session.add(run)
    db.session.commit()

    # ==========================
    # ✅ AUTO-CÁLCULO NIST (DESPUÉS DE GUARDAR ISO)
    # ==========================
    try:
        resultado_nist = calcular_nist_desde_iso(run.id)
        if resultado_nist:
            nuevo_nist = NistAnalysisRun(
                iso_analysis_id=run.id,
                nivel_promedio_general=resultado_nist["nivel_general"],
                resultados_json=json.dumps(resultado_nist["detalle"], ensure_ascii=False)
            )
            db.session.add(nuevo_nist)
            db.session.commit()
    except Exception as e:
        # No bloquea el flujo ISO si NIST falla
        print("⚠️ Error generando NIST automáticamente:", e)

    flash("✅ Análisis generado y guardado correctamente.", "success")
    return redirect(url_for("madurez.view_report", run_id=run.id))

@madurez_bp.route("/report/<int:run_id>/generate-ai-control", methods=["POST"])
@login_required
def generate_ai_control(run_id: int):
    user = User.query.get(session.get("user_id"))

    if user and user.role == "auditor":
        flash("El perfil Auditor no puede generar análisis con IA por control.", "danger")
        return redirect(url_for("madurez.view_report", run_id=run_id))

    if user and user.role not in ("admin", "auditor") and not verificar_permiso(user, "Nivel de Madurez ISO 27001:2022"):
        flash("No tiene permiso para generar análisis con IA.", "danger")
        return redirect(url_for("menu"))

    run = AnalysisRun.query.get_or_404(run_id)

    control_id = (request.form.get("control_id") or request.args.get("control_id") or "").strip().upper()
    if not control_id:
        flash("No se recibió el control a procesar.", "warning")
        return redirect(url_for("madurez.view_report", run_id=run.id))

    try:
        ctx = build_report_context(run)
        control_items = ctx.get("control_items", {}) or {}

        items = control_items.get(control_id, []) or []
        kpi = compute_control_kpis(control_id, items)

        ai_generate_control_analysis(run, control_id, kpi, items)

        db.session.add(run)
        db.session.commit()

        flash(f"✅ Análisis IA generado para el control {control_id}.", "success")

    except Exception as e:
        db.session.rollback()
        print("DEBUG ISO CONTROL - ERROR:", str(e))
        traceback.print_exc()
        flash(f"❌ Error generando IA para el control {control_id}: {e}", "danger")

    return redirect(url_for("madurez.view_report", run_id=run.id))

@madurez_bp.route("/report/<int:run_id>/generate-ai-informe", methods=["POST"])
@login_required
def generate_ai_informe(run_id: int):
    user = User.query.get(session.get("user_id"))

    if user and user.role == "auditor":
        flash("El perfil Auditor no puede generar el resumen ejecutivo con IA.", "danger")
        return redirect(url_for("madurez.view_report", run_id=run_id))

    if user and user.role not in ("admin", "auditor") and not verificar_permiso(user, "Nivel de Madurez ISO 27001:2022"):
        flash("No tiene permiso para generar el resumen ejecutivo con IA.", "danger")
        return redirect(url_for("menu"))

    run = AnalysisRun.query.get_or_404(run_id)

    try:
        chapter_results = json.loads(run.chapter_results_json or "{}")

        data = ai_generate_executive_summary_from_domains(
            company_name=run.company_name,
            chapter_results=chapter_results
        )

        run.executive_summary = (data.get("executive_summary") or "").strip()
        db.session.commit()

        flash("✅ Resumen ejecutivo generado con IA.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error generando resumen ejecutivo con IA: {e}", "danger")

    return redirect(url_for("madurez.view_report", run_id=run.id))

@madurez_bp.route("/report/<int:run_id>/ai/plan", methods=["POST"])
@login_required
def generate_ai_plan(run_id: int):
    run = AnalysisRun.query.get_or_404(run_id)

    chapter_results = json.loads(run.chapter_results_json or "{}")
    control_results = json.loads(run.control_results_json or "{}")

    try:
        out = ai_generate_general_action_plan(
            company_name=run.company_name,
            chapter_results=chapter_results,
            control_results=control_results
        )

        # ✅ Guarda SOLO plan
        run.action_plan_json = json.dumps(out.get("action_plan", []), ensure_ascii=False)

        # ✅ No tocar resumen ejecutivo aquí
        # run.executive_summary = run.executive_summary (no hacer nada)

        db.session.commit()
        flash("✅ IA Plan generada: SOLO Plan de acción general.", "success")

    except Exception as e:
        flash(f"⚠️ No se pudo generar Plan de acción IA. Error: {e}", "danger")

    return redirect(url_for("madurez.view_report", run_id=run.id))

def build_report_context(run: AnalysisRun) -> dict:
    # JSON base
    chapter_results = json.loads(run.chapter_results_json or "{}")
    control_results = json.loads(run.control_results_json or "{}")
    control_items = json.loads(run.control_items_json or "{}")

    # Normaliza claves control_items a UPPER (como ya haces en IA)
    norm_control_items = {}
    for k, v in (control_items or {}).items():
        kk = (str(k) or "").strip().upper()
        if kk:
            norm_control_items[kk] = v or []
    control_items = norm_control_items

    # control_ai
    try:
        control_ai = json.loads(run.control_ai_json or "{}") if run.control_ai_json else {}
    except Exception:
        control_ai = {}

    # item_results (si no existe guardado, lo reconstruye)
    try:
        item_results = json.loads(run.item_results_json or "{}") if run.item_results_json else {}
    except Exception:
        item_results = {}

    if not item_results:
        item_results = build_item_results(control_items)

    # item_ai
    try:
        item_ai = json.loads(run.item_ai_json or "{}") if getattr(run, "item_ai_json", None) else {}
    except Exception:
        item_ai = {}

    # gráficas extra (barras)
    try:
        extra_graphs = json.loads(run.radar_by_sheet_json or "{}") if run.radar_by_sheet_json else {}
    except Exception:
        extra_graphs = {}

    bar_chapters_b64 = extra_graphs.get("bar_chapters", "")
    bar_controls_4_10_b64 = extra_graphs.get("bar_controls_4_10", "")

    # plan
    plan = json.loads(run.action_plan_json or "[]") if run.action_plan_json else []

    # textos
    executive_text = format_executive_summary(run.executive_summary)
    ai_text = format_ai_report(run.ai_report_text)
    methodology_text = (getattr(run, "ai_methodology_text", "") or "").strip()

    # KPIs globales
    overall = round(sum(v.get("pct", 0) for v in chapter_results.values()) / max(1, len(chapter_results)), 2)
    overall_maturity = get_maturity_label_for_pct(overall)

    # Orden de controles para imprimir (igual que UI)
    controls_to_process = []
    for cid in control_items.keys():
        if cid and cid != "SIN CONTROL":
            controls_to_process.append(cid)

    def _order_key(x: str):
        xu = (x or "").strip().upper()
        if xu in CONTROL_ORDER:
            return (0, CONTROL_ORDER.index(xu), xu)
        if xu.startswith("A."):
            return (1, 9999, xu)
        return (2, 9999, xu)

    controls_to_process = sorted(set(controls_to_process), key=_order_key)

    return {
        "run": run,
        "chapter_results": chapter_results,
        "control_results": control_results,
        "control_items": control_items,
        "control_ai": control_ai,
        "item_results": item_results,
        "item_ai": item_ai,
        "plan": plan,
        "executive_text": executive_text,
        "ai_text": ai_text,
        "methodology_text": methodology_text,
        "overall": overall,
        "overall_maturity": overall_maturity,
        "radar_overall_b64": (run.radar_overall_b64 or ""),
        "bar_chapters_b64": bar_chapters_b64,
        "bar_controls_4_10_b64": bar_controls_4_10_b64,
        "controls_to_process": controls_to_process,
    }

# ==========================
# VIEW REPORT (UI)
# ==========================
@madurez_bp.route("/report/<int:run_id>", methods=["GET"])
@login_required
def view_report(run_id: int):
    run = AnalysisRun.query.get_or_404(run_id)
    user = User.query.get(session.get("user_id"))

    # =========================
    # PERMISOS
    # =========================
    if user and user.role not in ("admin", "auditor") and not verificar_permiso(user, "Nivel de Madurez ISO 27001:2022"):
        flash("No tiene permiso para acceder al informe de madurez ISO 27001:2022.", "danger")
        return redirect(url_for("menu"))

    read_only = bool(user and user.role == "auditor")

    ctx = build_report_context(run)
    nist = calcular_nist_desde_iso(run.id)
    ctx["nist_from_iso"] = nist

    chapter_results = ctx["chapter_results"]
    control_results = ctx["control_results"]
    control_items = ctx["control_items"]
    control_ai = ctx["control_ai"]
    item_results = ctx["item_results"]
    item_ai = ctx["item_ai"]
    plan = ctx["plan"]
    bar_chapters_b64 = ctx["bar_chapters_b64"]
    bar_controls_4_10_b64 = ctx["bar_controls_4_10_b64"]
    overall = ctx["overall"]
    overall_maturity = ctx["overall_maturity"]

    rows = ""
    for k in CHAPTER_SHEETS:
        v = chapter_results.get(k, {"pct": 0, "done": 0, "total": 0})
        maturity = get_maturity_label_for_pct(v.get("pct", 0))

        bp = float(v.get("brecha_pct", 0) or 0)
        bn = (v.get("brecha_nivel") or "").strip()
        bi = (v.get("brecha_interp") or "").strip()

        brecha_txt = ""
        if bi:
            brecha_txt = f"<div class='small text-muted mt-1 wrap'>{xml_escape(bi)}</div>"

        rows += f"""
        <tr>
          <td class="fw-semibold">{xml_escape(k)}</td>
          <td>
            <span class="badge {score_badge(float(v.get("pct",0)))}">{v.get("pct",0)}%</span>
            {"<span class='text-muted small ms-2'>(" + xml_escape(maturity) + ")</span>" if maturity else ""}
          </td>
          <td>
            <span class="badge {gap_badge(bn)}">{bp:.0f}%</span>
            {"<span class='text-muted small ms-2'>(" + xml_escape(bn) + ")</span>" if bn else ""}
            {brecha_txt}
          </td>
        </tr>
        """

    control_rows = ""
    for cid, v in control_results.items():
        if str(cid).upper().startswith("A."):
            continue

        bp = float(v.get("brecha_pct", 0) or 0)
        bn = (v.get("brecha_nivel") or "").strip()
        bi = (v.get("brecha_interp") or "").strip()

        brecha_txt = ""
        if bi:
            brecha_txt = f"<div class='small text-muted mt-1 wrap'>{xml_escape(bi)}</div>"

        control_rows += f"""
        <tr>
          <td class="fw-semibold">
            {xml_escape(cid)} <span class="text-muted small">({xml_escape(v.get("group",""))})</span>
          </td>
          <td>
            <span class="badge {score_badge(float(v.get("pct",0)))}">{v.get("pct",0)}%</span>
            {"<span class='text-muted small ms-2'>(" + xml_escape(v.get("madurez","")) + ")</span>" if v.get("madurez") else ""}
          </td>
          <td>
            <span class="badge {gap_badge(bn)}">{bp:.0f}%</span>
            {"<span class='text-muted small ms-2'>(" + xml_escape(bn) + ")</span>" if bn else ""}
            {brecha_txt}
          </td>
        </tr>
        """

    if not control_rows:
        control_rows = "<tr><td colspan='3' class='text-muted'>Sin datos por control.</td></tr>"

    chapter_groups_ui = [
        "Contexto",
        "Liderazgo",
        "Planificación",
        "Soporte",
        "Operación",
        "Evaluación de desempeño",
        "Mejora",
        "Anexo A",
    ]

    def controls_for_group(group_name: str) -> list:
        ids = CONTROL_GROUPS.get(group_name, [])

        if group_name == "Anexo A":
            def a_sort_key(k: str):
                kk = (k or "").strip().upper()
                m = re.match(r"^A\.(\d+)\.(\d+)$", kk)
                if not m:
                    return (999, 999)
                return (int(m.group(1)), int(m.group(2)))

            all_a = []
            for k in control_items.keys():
                kk = (str(k) or "").strip().upper()
                if re.match(r"^A\.\d+\.\d+$", kk):
                    all_a.append(kk)

            return sorted(set(all_a), key=a_sort_key)

        return ids

    anexo_headers = MadurezPregunta.query.filter_by(sheet="ANEXO A", tipo="h") \
        .order_by(MadurezPregunta.orden.asc()).all()

    anexo_family_map = {}
    anexo_control_map = {}

    for p in anexo_headers:
        txt = (p.pregunta or "").strip()
        sec = (p.seccion or "").strip()

        m_fam = re.match(r"^(\d+)\.\s+", txt)
        if m_fam and not sec:
            anexo_family_map[m_fam.group(1)] = txt
            continue

        if re.match(r"^\d+\.\d+$", sec) and txt:
            anexo_control_map[sec] = txt

    controls_by_chapter_html = ""
    for grp in chapter_groups_ui:
        cids = controls_for_group(grp)
        chap_inner = ""
        last_anexo_family = None

        for cid in cids:
            items_c = control_items.get(cid, []) or []
            kpi = compute_control_kpis(cid, items_c)
            badge = score_badge(float(kpi.get("pct", 0) or 0))
            bp = float(kpi.get("brecha_pct", 0) or 0)
            bn = (kpi.get("brecha_nivel") or "").strip()
            bi = (kpi.get("brecha_interp") or "").strip()

            cid_u = (cid or "").strip().upper()
            is_anexo = cid_u.startswith("A.")
            cid_disp = cid_u[2:] if is_anexo else (cid or "").strip()

            if is_anexo:
                fam = cid_disp.split(".")[0] if "." in cid_disp else None
                if fam and fam != last_anexo_family:
                    fam_title = anexo_family_map.get(fam, f"{fam}.")
                    chap_inner += f"""
                    <div class="mt-3 fw-bold">{xml_escape(fam_title)}</div>
                    <hr class="my-2">
                    """
                    last_anexo_family = fam

                full_title = anexo_control_map.get(cid_disp, cid_disp)
                sub_title = re.sub(r"^\s*" + re.escape(cid_disp) + r"\s*", "", full_title).strip()
                title = sub_title or full_title
            else:
                title = control_title(cid)

            cai = (control_ai.get(cid) or {}) if isinstance(control_ai, dict) else {}

            safe_id = re.sub(r"[^a-zA-Z0-9_]+", "_", f"{grp}_{cid}")

            estado_actual = (cai.get("estado_actual") or "").strip()
            estado_req    = (cai.get("estado_requerido") or "").strip()
            plan_sug      = (cai.get("plan_accion_sugerido") or "").strip()

            ea_safe = textarea_escape(estado_actual)
            er_safe = textarea_escape(estado_req)
            pa_safe = textarea_escape(plan_sug)

            bloque1 = f"""
            <div class="mt-2">
              <div class="fw-semibold mb-1 text-dark">📍 Estado actual</div>
              <div class="small text-dark wrap">
                {xml_escape(estado_actual) if estado_actual else "<span class='text-muted'>Aún no se ha generado IA para este control.</span>"}
              </div>
            </div>

            <div class="mt-3">
              <div class="fw-semibold mb-1 text-dark">🎯 Estado requerido</div>
              <div class="small text-dark wrap">
                {xml_escape(estado_req) if estado_req else "<span class='text-muted'>Sin contenido.</span>"}
              </div>
            </div>
            """

            bloque2 = f"""
            <div class="mt-3">
              <div class="fw-semibold mb-1 text-dark">🛠 Plan de acción sugerido</div>
              <div class="small text-dark wrap">
                {xml_escape(plan_sug) if plan_sug else "<span class='text-muted'>Sin contenido.</span>"}
              </div>
            </div>
            """

            if read_only:
                control_edit_form = """
                <div class="mt-3">
                  <button class="btn btn-sm btn-secondary pill" type="button" disabled
                          title="El perfil Auditor solo tiene permisos de consulta">
                    ✏️ Editar análisis (Control)
                  </button>
                </div>
                """
                btn_ai_control = """
                <button class="btn btn-sm btn-secondary pill" type="button" disabled
                        title="El perfil Auditor no puede generar IA por control">
                  🧠 Generar IA (Control)
                </button>
                """
            else:
                control_edit_form = f"""
                <div class="mt-3">
                  <button type="button"
                          class="btn btn-sm btn-outline-primary pill"
                          id="btnEditControl_{safe_id}"
                          onclick="toggleControlEdit('{safe_id}', true)">
                    ✏️ Editar análisis (Control)
                  </button>
                </div>

                <div class="card card-soft p-3 mt-3 d-none" id="editCard_{safe_id}">
                  <div class="fw-bold mb-2">✍️ Editar análisis por control</div>

                  <form method="POST" action="{url_for('madurez.save_control_ai', run_id=run.id, control_id=cid)}">
                    <div class="mb-2">
                      <label class="form-label fw-semibold small">Estado actual</label>
                      <textarea class="form-control" name="estado_actual" rows="4">{ea_safe}</textarea>
                    </div>

                    <div class="mb-2">
                      <label class="form-label fw-semibold small">Estado requerido</label>
                      <textarea class="form-control" name="estado_requerido" rows="4">{er_safe}</textarea>
                    </div>

                    <div class="mb-3">
                      <label class="form-label fw-semibold small">Plan de acción sugerido</label>
                      <textarea class="form-control" name="plan_accion_sugerido" rows="6">{pa_safe}</textarea>
                    </div>

                    <div class="d-flex flex-wrap gap-2">
                      <button class="btn btn-sm btn-success pill" type="submit">💾 Guardar edición (Control)</button>
                      <button type="button"
                              class="btn btn-sm btn-outline-secondary pill"
                              onclick="toggleControlEdit('{safe_id}', false)">
                        ↩️ Cancelar
                      </button>
                    </div>
                  </form>
                </div>
                """

                btn_ai_control = f"""
                <form method="POST" action="{url_for('madurez.generate_ai_control', run_id=run.id)}" style="display:inline;">
                  <input type="hidden" name="control_id" value="{xml_escape(cid_u)}">
                  <button class="btn btn-sm btn-purple pill" type="submit">🧠 Generar IA (Control)</button>
                </form>
                """

            control_ai_html = f"""
            <div class="card card-soft p-3">
              <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
                <div class="fw-bold">🧠 Análisis IA por control</div>
                <span class="badge bg-dark">{xml_escape(kpi.get("madurez","") or "")}</span>
                <span class="badge {score_badge(float(kpi.get("pct",0) or 0))}">{kpi.get("pct",0)}%</span>
                <span class="badge {gap_badge((kpi.get("brecha_nivel") or '').strip())}">
                  {float(kpi.get("brecha_pct",0) or 0):.0f}%
                </span>
                {"<div class='small text-muted mt-2 wrap'>" + xml_escape(kpi.get("brecha_interp","")) + "</div>" if (kpi.get("brecha_interp") or "").strip() else ""}
              </div>
              {bloque1}
              {bloque2}
            </div>
            """

            tabla = render_control_items_table(items_c)

            chap_inner += f"""
            <div class="accordion-item">
              <h2 class="accordion-header" id="h_{safe_id}">
                <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#c_{safe_id}">
                  <div class="d-flex flex-wrap gap-2 align-items-center w-100">
                    <div class="fw-bold">{xml_escape(cid_disp)}</div>
                    <div class="text-muted small">{xml_escape(title)}</div>
                    <div class="ms-auto d-flex align-items-center gap-2">
                      <span class="badge {badge}">{kpi.get("pct",0)}%</span>
                      {"<span class='text-muted small'>(" + xml_escape(kpi.get("madurez","")) + ")</span>" if kpi.get("madurez") else ""}
                      <span class="badge {gap_badge(bn)}">{bp:.0f}%</span>
                      {"<span class='text-muted small'>(" + xml_escape(bn) + ")</span>" if bn else ""}
                    </div>
                  </div>
                </button>
              </h2>
              <div id="c_{safe_id}" class="accordion-collapse collapse">
                <div class="accordion-body">

                  <div class="d-flex justify-content-end mb-2">
                    {btn_ai_control}
                  </div>

                  <div class="mt-2">
                    {control_ai_html}
                  </div>

                  {control_edit_form}

                  <div class="mt-3">
                    <div class="fw-semibold mb-2">Preguntas / requisitos del control (soporte)</div>
                    {tabla}
                  </div>

                </div>
              </div>
            </div>
            """

        if not chap_inner:
            chap_inner = "<div class='text-muted'>Sin controles disponibles en este capítulo.</div>"

        soporte_chap = ""
        for _cid in cids:
            items_cc = control_items.get(_cid, []) or []
            if not items_cc:
                continue

            soporte_chap += f"""
            <div class="mt-3">
              <div class="fw-semibold mb-2" style="color:#1e3a8a;">
                {_cid} — {xml_escape(control_title(_cid))}
              </div>
              {render_control_items_table(items_cc)}
            </div>
            """

        if not soporte_chap:
            soporte_chap = "<div class='text-muted'>Sin preguntas registradas para este capítulo.</div>"

        safe_grp = re.sub(r"[^a-zA-Z0-9_]+", "_", grp)

        grp_pcts = []
        for _cid in cids:
            vv = control_results.get(_cid, {})
            try:
                grp_pcts.append(float(vv.get("pct", 0) or 0))
            except Exception:
                pass

        grp_avg = round(sum(grp_pcts) / len(grp_pcts), 2) if grp_pcts else 0.0
        grp_gap = gap_from_maturity_pct(grp_avg)
        grp_bp = float(grp_gap.get("gap_pct", 0) or 0)
        grp_bn = (grp_gap.get("nivel_brecha", "") or "").strip()
        grp_bi = (grp_gap.get("interpretacion", "") or "").strip()

        grp_brecha_txt = ""
        if grp_bi:
            grp_brecha_txt = f"<div class='small text-muted mt-1 wrap'>{xml_escape(grp_bi)}</div>"

        controls_by_chapter_html += f"""
        <div class="card card-soft shadow-soft p-4 mt-3">
          <div class="d-flex flex-wrap justify-content-between align-items-center mb-2 gap-2">
            <div>
              <h5 class="mb-0">📌 Controles – Capítulo: {xml_escape(grp)}</h5>
              <div class="text-muted small">Análisis por control basado en las preguntas del instrumento.</div>
            </div>

            <div class="text-start">
              <div class="small fw-semibold">Brecha</div>
              <div class="d-flex align-items-center gap-2">
                <span class="badge {gap_badge(grp_bn)}">{grp_bp:.0f}%</span>
                {"<span class='text-muted small'>(" + xml_escape(grp_bn) + ")</span>" if grp_bn else ""}
              </div>
              {grp_brecha_txt}
            </div>
          </div>

          <div class="accordion" id="acc_{safe_grp}">
            {chap_inner}
          </div>

          <div class="mt-4">
            <button class="btn btn-outline-primary rounded-pill px-4"
                    type="button"
                    data-bs-toggle="collapse"
                    data-bs-target="#sup_{safe_grp}">
              📋 Preguntas / requisitos del control (soporte)
            </button>

            <div class="collapse mt-3" id="sup_{safe_grp}">
              {soporte_chap}
            </div>
          </div>
        </div>
        """

    plan_rows = ""
    if plan:
        for p in plan[:400]:
            pri = p.get("prioridad", "")
            pri_badge = "bg-secondary"
            if pri == "Alta":
                pri_badge = "bg-danger"
            elif pri == "Media":
                pri_badge = "bg-warning text-dark"

            plan_rows += f"""
            <tr class="cell-small">
              <td><span class="badge bg-dark">{xml_escape(p.get("fase",""))}</span></td>
              <td class="text-muted">{xml_escape(p.get("capitulo",""))}</td>
              <td class="wrap" style="min-width: 220px;">{xml_escape(p.get("requisito",""))}</td>
              <td class="wrap" style="min-width: 360px;">{xml_escape(p.get("accion",""))}</td>
              <td class="wrap" style="min-width: 240px;">{xml_escape(p.get("evidencia",""))}</td>
              <td style="min-width: 160px;">{xml_escape(p.get("responsable",""))}</td>
              <td><span class="badge {pri_badge}">{xml_escape(pri)}</span></td>
            </tr>
            """
    else:
        plan_rows = "<tr><td colspan='7' class='text-center text-muted'>Aún no has generado el plan con IA.</td></tr>"

    executive_text = format_executive_summary(run.executive_summary)
    ai_text = format_ai_report(run.ai_report_text)

    executive_safe = textarea_escape(executive_text)
    ai_safe = textarea_escape(ai_text)

    try:
        nist_btn = f"""
          <a class="btn btn-dark rounded-pill"
             href="{url_for('madurez.report_nist', run_id=run.id)}">
             🧩 Ver NIST (desde ISO)
          </a>
        """
    except Exception:
        nist_btn = ""

    if read_only:
        delete_btn = """
        <button class="btn btn-outline-secondary pill" type="button" disabled
                title="El perfil Auditor no puede eliminar informes">
          🗑️ Eliminar
        </button>
        """
        btn_ai_informe = """
        <button class="btn btn-secondary pill" type="button" disabled
                title="El perfil Auditor no puede generar resumen ejecutivo con IA">
          🧠 Generar IA (Resumen ejecutivo)
        </button>
        """
        executive_edit_block = f"""
        <div class="card card-soft shadow-soft p-4 mt-3">
          <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-2">
            <div>
              <h5 class="mb-0">🧾 Informe Ejecutivo</h5>
              <div class="text-muted small">Resumen ejecutivo generado por IA. Solo lectura para Auditor.</div>
            </div>
            <div>
              {btn_ai_informe}
            </div>
          </div>

          <div class="alert alert-info small">
            El perfil Auditor solo puede consultar el informe ejecutivo.
          </div>

          <div class="mb-3">
            <label class="form-label fw-semibold">Resumen ejecutivo</label>
            <textarea
              class="form-control report-textarea"
              rows="8"
              readonly
            >{executive_safe}</textarea>
          </div>
        </div>
        """
    else:
        delete_btn = f"""
        <form method="POST" action="{url_for('madurez.delete_report', run_id=run.id)}" style="display:inline;"
              onsubmit="return confirm('¿Eliminar el informe #{run.id}?');">
          <button class="btn btn-outline-danger pill" type="submit">🗑️ Eliminar</button>
        </form>
        """
        btn_ai_informe = f"""
        <form id="formAiInforme" method="POST" action="{url_for('madurez.generate_ai_informe', run_id=run.id)}" class="d-inline">
          <button class="btn btn-warning pill" type="submit">🧠 Generar IA (Resumen ejecutivo)</button>
        </form>
        """

        executive_edit_block = f"""
        <div class="card card-soft shadow-soft p-4 mt-3">
          <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-2">
            <div>
              <h5 class="mb-0">🧾 Informe Ejecutivo</h5>
              <div class="text-muted small">Resumen ejecutivo generado por IA y editable solo al presionar “Editar”.</div>
            </div>
            <div>
              {btn_ai_informe}
            </div>
          </div>

          <form method="POST" action="{url_for('madurez.save_edits', run_id=run.id)}" id="formExecutiveEdit">
            <div class="mb-3">
              <label class="form-label fw-semibold">Resumen ejecutivo</label>
              <textarea
                class="form-control report-textarea"
                id="executiveSummaryBox"
                name="executive_summary"
                rows="8"
                readonly
              >{executive_safe}</textarea>
            </div>

            <div class="d-flex flex-wrap gap-2">
              <button type="button" class="btn btn-outline-primary pill px-4" id="btnEditarExecutive">
                ✏️ Editar
              </button>

              <button type="button" class="btn btn-outline-secondary pill px-4 d-none" id="btnCancelarExecutive">
                ↩️ Cancelar
              </button>

              <button type="submit" class="btn btn-success pill px-4 d-none" id="btnGuardarExecutive">
                💾 Guardar edición
              </button>
            </div>
          </form>
        </div>

        <script>
          (function() {{
            const box = document.getElementById("executiveSummaryBox");
            const btnEditar = document.getElementById("btnEditarExecutive");
            const btnCancelar = document.getElementById("btnCancelarExecutive");
            const btnGuardar = document.getElementById("btnGuardarExecutive");

            if (!box || !btnEditar || !btnCancelar || !btnGuardar) return;

            let originalValue = box.value;

            btnEditar.addEventListener("click", function() {{
              originalValue = box.value;
              box.removeAttribute("readonly");
              box.focus();
              box.setSelectionRange(box.value.length, box.value.length);

              btnEditar.classList.add("d-none");
              btnCancelar.classList.remove("d-none");
              btnGuardar.classList.remove("d-none");
            }});

            btnCancelar.addEventListener("click", function() {{
              box.value = originalValue;
              box.setAttribute("readonly", "readonly");

              btnEditar.classList.remove("d-none");
              btnCancelar.classList.add("d-none");
              btnGuardar.classList.add("d-none");
            }});
          }})();
        </script>

        <script>
          attachProgressModal(
            "formAiInforme",
            "progressModal",
            "pmBar",
            "pmPct",
            "pmMsg",
            "Generando SOLO Resumen Ejecutivo (por dominios)…"
          );

          attachProgressModal(
            "formAiPlan",
            "progressModal",
            "pmBar",
            "pmPct",
            "pmMsg",
            "Generando SOLO Plan de acción general…"
          );
        </script>
        """

    top_actions = f"""
    <div class="report-header-actions">
      <a class="btn btn-outline-light pill" href="{url_for('madurez.home')}">⬅ Inicio</a>
      {nist_btn}
      <a class="btn btn-outline-light pill" href="{url_for('madurez.report_pdf', run_id=run.id)}">📄 PDF</a>
      {delete_btn}
    </div>
    """

    report_css = """
    <style>
      .bg-purple{ background-color:#6f42c1 !important; }
      .badge.bg-purple{ color:#ffffff !important; }

      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .report-shell{
        width:96%;
        max-width:1200px;
        margin:26px auto 24px auto;
      }

      .report-hero{
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

      .report-hero::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .report-hero-overlay{
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

      .report-hero-overlay::before{
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
        font-size:1.45rem;
        box-shadow:0 8px 18px rgba(0,0,0,.25);
        margin-right:14px;
      }

      .report-hero-centered{
        max-width:1000px;
        width:100%;
        display:block !important;
        transform:none !important;
      }

      .report-hero-centered::before{
        content:"SGSI · Informe Ejecutivo";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .report-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        margin:0 !important;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
      }

      .report-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
      }

      .report-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .report-header-actions .btn,
      .btn{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }

      .report-header-actions .btn{
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .btn-outline-light{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }

      .btn-outline-light:hover{
        background:#edf5ff;
        color:#0b65d8 !important;
        border-color:#9ec5fe !important;
      }

      .btn-purple{
        background:#6f42c1;
        border-color:#6f42c1;
        color:#ffffff;
      }

      .btn-purple:hover{
        background:#5b34a4;
        border-color:#5b34a4;
        color:#ffffff;
      }

      .pill{
        border-radius:999px !important;
      }

      .card,
      .report-card,
      .card-soft{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }

      .card-body{
        padding:18px;
      }

      .section-head{
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:12px;
        flex-wrap:wrap;
      }

      .section-head h5,
      .card h5,
      .card h6{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:0;
      }

      .section-sub,
      .muted{
        color:#475569;
        font-size:.82rem;
      }

      .kpi,
      .report-kpi-value{
        font-size:2rem;
        line-height:1.05;
        font-weight:950;
        color:#0b4a8f;
        letter-spacing:-0.5px;
      }

      .table-responsive{
        max-height:72vh;
        overflow-y:auto;
        overflow-x:auto;
        border:1px solid #dbe6f4;
        border-radius:14px;
        background:#ffffff;
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
        border:none !important;
        white-space:nowrap;
        vertical-align:middle;
        text-align:center;
        padding:9px 8px;
      }

      .table tbody td{
        vertical-align:top;
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

      .table-tight th,
      .table-tight td,
      .cell-small{
        font-size:.78rem !important;
      }

      .wrap{
        white-space:normal !important;
        word-break:break-word;
        overflow-wrap:anywhere;
      }

      .accordion-item{
        border:1px solid #dbe6f4 !important;
        border-radius:0 20px 20px 0 !important;
        overflow:hidden;
        margin-bottom:12px;
        background:#ffffff;
        box-shadow:0 6px 14px rgba(15,23,42,.06);
      }

      .accordion-button{
        background:#eef5ff !important;
        color:#0f172a !important;
        font-weight:900;
        box-shadow:none !important;
      }

      .accordion-button:not(.collapsed){
        background:#dbeafe !important;
        color:#0b4a8f !important;
      }

      .accordion-body{
        background:rgba(255,255,255,.96);
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
      .form-select,
      .report-textarea{
        border-radius:10px;
        border:1px solid #d9e3f0;
        min-height:40px;
        font-size:.86rem;
        background:#f8fafc;
        box-shadow:none !important;
      }

      .report-textarea{
        min-height:180px;
      }

      .form-control:focus,
      .form-select:focus,
      .report-textarea:focus{
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

      @media (max-width:991.98px){
        .report-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .report-hero{
          min-height:88px;
        }

        .report-title{
          font-size:1.20rem;
        }

        .report-subtitle{
          font-size:.68rem;
        }

        .kpi,
        .report-kpi-value{
          font-size:1.75rem;
        }

        .card-body{
          padding:8px 7px;
        }
      }

      @media (max-width:768px){
        .report-hero-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .report-hero-overlay::before{
          margin:0;
        }

        .report-hero-centered::before{
          margin-left:auto;
          margin-right:auto;
        }

        .report-title,
        .report-subtitle{
          text-align:center;
        }

        .report-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """

    content = f"""
    {report_css}

    <div class="report-shell">

      <div class="report-hero">
        <div class="report-hero-overlay">
          <div class="report-hero-centered">
            <h1 class="report-title">Informe de Madurez ISO 27001:2022</h1>
            <div class="report-subtitle">
              {xml_escape(run.company_name)} • ID #{run.id} • {run.created_at.strftime('%Y-%m-%d %H:%M')}
            </div>
          </div>
        </div>
      </div>

      {top_actions}

      {"<div class='alert alert-info'>🔒 El perfil Auditor está en modo solo lectura. No puede editar, eliminar ni generar contenido con IA.</div>" if read_only else ""}

      <div class="row g-3">
        <div class="col-lg-4">

          <div class="card card-soft shadow-soft p-4">
            <div class="text-muted small">Madurez promedio</div>
            <div class="kpi">
              {overall}%
              {"<span class='fs-6 text-muted'>(" + xml_escape(overall_maturity) + ")</span>" if overall_maturity else ""}
            </div>
          </div>

          <div class="card card-soft shadow-soft p-3 mt-3">
            <h6 class="mb-2">📊 Resultados por dominio</h6>
            <div class="table-responsive">
              <table class="table table-sm align-middle mb-0 table-tight">
                <thead>
                  <tr>
                    <th>Capítulo</th>
                    <th>% + Madurez</th>
                    <th>Brecha</th>
                  </tr>
                </thead>
                <tbody>{rows}</tbody>
              </table>
            </div>
          </div>

          <div class="card card-soft shadow-soft p-3 mt-3">
            <div class="d-flex justify-content-between align-items-center mb-2">
              <h6 class="mb-0">🧩 Resultados por control</h6>
              <span class="text-muted small">% + madurez + brecha</span>
            </div>

            <div class="table-responsive" style="max-height:360px; overflow:auto;">
              <table class="table table-sm align-middle mb-0 table-tight">
                <thead>
                  <tr>
                    <th style="min-width:180px;">Control</th>
                    <th style="min-width:140px;">% + Madurez</th>
                    <th style="min-width:220px;">Brecha</th>
                  </tr>
                </thead>
                <tbody>{control_rows}</tbody>
              </table>
            </div>
          </div>

          <div class="card card-soft shadow-soft p-3 mt-3">
            <h6 class="mb-2">🕸 Araña consolidada (obligatoria)</h6>
            <img class="img-fluid" alt="Radar consolidado" src="data:image/png;base64,{run.radar_overall_b64}">
          </div>

        </div>

        <div class="col-lg-8">
          <div class="card card-soft shadow-soft p-4">
            <div class="d-flex justify-content-between align-items-center">
              <h5 class="mb-0">📈 Madurez por capítulo (barras)</h5>
              <span class="text-muted small">Comparación directa por capítulo.</span>
            </div>
            <div class="mt-2">
              {"<img class='img-fluid' alt='Barras por capítulo' src='data:image/png;base64," + bar_chapters_b64 + "'>" if bar_chapters_b64 else "<div class='text-muted small'>Sin datos para graficar.</div>"}
            </div>
          </div>

          <div class="card card-soft shadow-soft p-4 mt-3">
            <div class="d-flex justify-content-between align-items-center">
              <h5 class="mb-0">📊 Madurez por control (4–10)</h5>
              <span class="text-muted small">Controles 4.1 a 10.2</span>
            </div>
            <div class="mt-2">
              {"<img class='img-fluid' alt='Barras por control 4-10' src='data:image/png;base64," + bar_controls_4_10_b64 + "'>" if bar_controls_4_10_b64 else "<div class='text-muted small'>Sin datos para graficar controles 4–10.</div>"}
            </div>
          </div>

          {controls_by_chapter_html}

          {executive_edit_block}

        </div>
      </div>
    </div>
    """

    content += """
    <script>
      function toggleControlEdit(safeId, show) {
        const card = document.getElementById("editCard_" + safeId);
        const btn = document.getElementById("btnEditControl_" + safeId);

        if (!card) return;

        if (show) {
          card.classList.remove("d-none");
          if (btn) btn.classList.add("d-none");
        } else {
          card.classList.add("d-none");
          if (btn) btn.classList.remove("d-none");
        }
      }
    </script>
    """

    return render_template_string(BASE, title=f"Informe – {run.company_name}", content=content)


@madurez_bp.route("/report/<int:run_id>/control/<control_id>/save", methods=["POST"])
@login_required
def save_control_ai(run_id: int, control_id: str):
    user = User.query.get(session.get("user_id"))

    if user and user.role == "auditor":
        flash("El perfil Auditor no puede editar análisis por control.", "danger")
        return redirect(url_for("madurez.view_report", run_id=run_id))

    if user and user.role not in ("admin", "auditor") and not verificar_permiso(user, "Nivel de Madurez ISO 27001:2022"):
        flash("No tiene permiso para editar análisis por control.", "danger")
        return redirect(url_for("menu"))

    run = AnalysisRun.query.get_or_404(run_id)

    cid = (control_id or "").strip().upper()
    control_ai = json.loads(run.control_ai_json or "{}") if run.control_ai_json else {}

    control_ai.setdefault(cid, {})
    control_ai[cid]["estado_actual"] = to_text(request.form.get("estado_actual")).strip()
    control_ai[cid]["estado_requerido"] = to_text(request.form.get("estado_requerido")).strip()
    control_ai[cid]["plan_accion_sugerido"] = to_text(request.form.get("plan_accion_sugerido")).strip()

    run.control_ai_json = json.dumps(control_ai, ensure_ascii=False)
    db.session.commit()

    flash(f"💾 Edición guardada para el control {cid}.", "success")
    return redirect(url_for("madurez.view_report", run_id=run.id))

@madurez_bp.route("/report/<int:run_id>/save", methods=["POST"])
@login_required
def save_edits(run_id: int):
    user = User.query.get(session.get("user_id"))

    if user and user.role == "auditor":
        flash("El perfil Auditor no puede editar el informe ejecutivo.", "danger")
        return redirect(url_for("madurez.view_report", run_id=run_id))

    if user and user.role not in ("admin", "auditor") and not verificar_permiso(user, "Nivel de Madurez ISO 27001:2022"):
        flash("No tiene permiso para editar el informe ejecutivo.", "danger")
        return redirect(url_for("menu"))

    run = AnalysisRun.query.get_or_404(run_id)

    run.executive_summary = to_text(request.form.get("executive_summary")).strip()
    run.ai_report_text = to_text(request.form.get("ai_report_text")).strip()

    db.session.commit()
    flash("💾 Informe ejecutivo editado y guardado correctamente.", "success")
    return redirect(url_for("madurez.view_report", run_id=run.id))


