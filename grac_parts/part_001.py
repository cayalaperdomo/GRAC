#madurez_bp = Blueprint# soa_iso27001_app.py
# Aplicación Flask autocontenida: Declaración de Aplicabilidad ISO 27001:2022 (todo en un archivo)
# Requisitos: pip install flask flask_sqlalchemy

#from flask import Flask, request, redirect, url_for, render_template_string, send_file, flash, session, Blueprint
# ============================================================
# PERFIL BAJO CONSUMO DE MEMORIA — RENDER / GRAC
# Reduce la memoria inicial sin deshabilitar módulos de la aplicación.
# Las librerías de Excel y gráficos se importan al primer uso real.
# ============================================================
import os as _grac_os
import sys as _grac_sys

# Debe establecerse ANTES de la primera importación de NumPy/Matplotlib.
_grac_os.environ.setdefault("MPLBACKEND", "Agg")
_grac_os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
_grac_os.environ.setdefault("OMP_NUM_THREADS", "1")
_grac_os.environ.setdefault("MKL_NUM_THREADS", "1")
_grac_os.environ.setdefault("NUMEXPR_MAX_THREADS", "1")
_grac_os.environ.setdefault("MALLOC_ARENA_MAX", "2")

# Rendimiento de GRAC Web en instancias Render con RAM restringida.
def _grac_env_enabled(name, default=False):
    value = _grac_os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off", ""}

_GRAC_RENDER_RUNTIME = bool(_grac_os.environ.get("RENDER") or _grac_os.environ.get("RENDER_SERVICE_ID"))
_GRAC_RENDER_LOW_MEMORY = _grac_env_enabled("GRAC_RENDER_LOW_MEMORY", _GRAC_RENDER_RUNTIME)

# Las importaciones de exportadores permanecen diferidas hasta que alguien los use.
# Esto evita cargar a la vez todos los generadores Word/PDF/Excel al iniciar GRAC.
class _GRACDeferredSymbol:
    __slots__ = ("module_name", "symbol_name", "_cached")

    def __init__(self, module_name, symbol_name):
        self.module_name = module_name
        self.symbol_name = symbol_name
        self._cached = None

    def _resolve(self):
        if self._cached is None:
            from importlib import import_module
            self._cached = getattr(import_module(self.module_name), self.symbol_name)
        return self._cached

    def __call__(self, *args, **kwargs):
        return self._resolve()(*args, **kwargs)

    def __getattr__(self, attr):
        return getattr(self._resolve(), attr)

    def __repr__(self):
        return "<deferred %s.%s>" % (self.module_name, self.symbol_name)

# Los nombres se definen antes de que se evalúen los tipos de los helpers.
for _grac_sym in ("Document",):
    globals()[_grac_sym] = _GRACDeferredSymbol("docx", _grac_sym)
for _grac_sym in ("Inches", "Pt"):
    globals()[_grac_sym] = _GRACDeferredSymbol("docx.shared", _grac_sym)
WD_ALIGN_PARAGRAPH = _GRACDeferredSymbol("docx.enum.text", "WD_ALIGN_PARAGRAPH")
WD_TABLE_ALIGNMENT = _GRACDeferredSymbol("docx.enum.table", "WD_TABLE_ALIGNMENT")
for _grac_sym in ("load_workbook", "Workbook"):
    globals()[_grac_sym] = _GRACDeferredSymbol("openpyxl", _grac_sym)
for _grac_sym in ("Font", "PatternFill", "Alignment"):
    globals()[_grac_sym] = _GRACDeferredSymbol("openpyxl.styles", _grac_sym)
# El nombre Image de ReportLab también se reutiliza en el código actual.
Image = _GRACDeferredSymbol("reportlab.platypus", "Image")
for _grac_sym in ("ImageReader",):
    globals()[_grac_sym] = _GRACDeferredSymbol("reportlab.lib.utils", _grac_sym)
for _grac_sym in ("ParagraphStyle", "getSampleStyleSheet"):
    globals()[_grac_sym] = _GRACDeferredSymbol("reportlab.lib.styles", _grac_sym)
for _grac_sym in ("SimpleDocTemplate", "Paragraph", "Spacer", "Table", "TableStyle", "PageBreak"):
    globals()[_grac_sym] = _GRACDeferredSymbol("reportlab.platypus", _grac_sym)
RLImage = _GRACDeferredSymbol("reportlab.platypus", "Image")


class _GRACLazyModule:
    """Proxy de módulo. No importa el paquete pesado hasta que se usa."""
    __slots__ = ("_name", "_real")

    def __init__(self, name):
        self._name = name
        self._real = None

    def _load(self):
        if self._real is None:
            import importlib
            self._real = importlib.import_module(self._name)
        return self._real

    def __getattr__(self, name):
        return getattr(self._load(), name)

    def __repr__(self):
        return "<GRAC deferred module %s>" % self._name

# Las anotaciones pandas de funciones se mantienen diferidas como cadenas.
pd = _GRACLazyModule("pandas")
np = _GRACLazyModule("numpy")
plt = _GRACLazyModule("matplotlib.pyplot")
patches = _GRACLazyModule("matplotlib.patches")
colors = _GRACLazyModule("reportlab.lib.colors")

def Wedge(*args, **kwargs):
    return patches.Wedge(*args, **kwargs)

def Circle(*args, **kwargs):
    return patches.Circle(*args, **kwargs)

def FancyArrowPatch(*args, **kwargs):
    return patches.FancyArrowPatch(*args, **kwargs)

def FigureCanvas(*args, **kwargs):
    import importlib
    cls = importlib.import_module("matplotlib.backends.backend_agg").FigureCanvasAgg
    return cls(*args, **kwargs)

from flask import Flask, request, redirect, url_for, render_template_string, send_file, flash, session, Blueprint, make_response
from flask_sqlalchemy import SQLAlchemy
from passlib.hash import ldap_salted_sha1 as ssha
import os, io, csv
from sqlalchemy import text
import pyotp
import json
import html
import qrcode
import datetime as datetime_module
import qrcode
from openai import OpenAI
import pyotp
import socket
from sqlalchemy.orm import selectinload, load_only
import io
import base64
from datetime import datetime
from datetime import datetime as dt
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from flask import abort
import re
# GRAC-RAM: importación diferida en el bloque de optimización
from markupsafe import Markup, escape
from werkzeug.utils import secure_filename
from io import BytesIO
from collections import Counter
import unicodedata
import smtplib
# GRAC-RAM: importación diferida: from reportlab.lib.utils import ImageReader
import secrets
import io
import math
# GRAC-RAM: importación diferida en el bloque de optimización
# GRAC-RAM: importación diferida en el bloque de optimización
# GRAC-RAM: MPLBACKEND=Agg definido antes de importar bibliotecas
# GRAC-RAM: importación diferida en el bloque de optimización
# GRAC-RAM: importación diferida en el bloque de optimización
# GRAC-RAM: importación diferida en el bloque de optimización
import shutil
# GRAC-RAM: importación diferida en el bloque de optimización
from werkzeug.utils import secure_filename
from uuid import uuid4
import requests
from requests.auth import HTTPBasicAuth
import string
from flask_sqlalchemy import SQLAlchemy
# GRAC-RAM: importación diferida: from reportlab.lib.styles import ParagraphStyle
# GRAC-RAM: colors se carga bajo demanda
# GRAC-RAM: importación diferida en el bloque de optimización
import os
from cryptography.fernet import Fernet
from werkzeug.utils import secure_filename
from flask_migrate import Migrate
import re
import secrets
# GRAC-RAM: importación diferida: from docx import Document
import requests
from requests.auth import HTTPBasicAuth
from cryptography.fernet import Fernet
# GRAC-RAM: importación diferida: from docx.shared import Inches
import traceback
# GRAC-RAM: importación diferida: from docx.enum.text import WD_ALIGN_PARAGRAPH
from email.message import EmailMessage
import datetime as dt
import string
from markupsafe import Markup, escape
from email.message import EmailMessage
from datetime import datetime
from reportlab.lib.enums import TA_CENTER
from flask import send_file
import ssl
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.x509.oid import NameOID
from flask_login import LoginManager
from flask_login import current_user
from sqlalchemy import inspect
from sqlalchemy import func, case
from werkzeug.utils import secure_filename
from sqlalchemy import Boolean, DateTime
from datetime import datetime
from datetime import date
from flask import send_from_directory
from werkzeug.utils import safe_join
from sqlalchemy.exc import IntegrityError
from urllib.parse import quote
from flask import request
from flask import jsonify
from sqlalchemy import func
import unicodedata
from sqlalchemy.orm import selectinload
import subprocess
from datetime import date, datetime
import uuid
import threading
import time
import signal
import pycountry
from flask import send_file
from werkzeug.utils import safe_join
from flask import abort
from markupsafe import Markup
from collections import defaultdict
import sqlite3
from markupsafe import Markup
import calendar
from sqlalchemy import and_
import re, json
from openai import OpenAI
import os
import sys
import re
import io
from collections import defaultdict, OrderedDict
from io import BytesIO
import math
import json
import random
import base64
import unicodedata
import time
from sqlalchemy import event
from sqlalchemy.engine import Engine
from datetime import datetime, timezone
from xml.sax.saxutils import escape as xml_escape
from openai import OpenAIError, AuthenticationError
from datetime import datetime, timezone, timedelta
# GRAC-RAM: importación diferida: from reportlab.platypus import Table, TableStyle
from flask import Blueprint
import traceback
# GRAC-RAM: importación diferida: from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
# GRAC-RAM: colors se carga bajo demanda
from werkzeug.exceptions import HTTPException
import uuid
# GRAC-RAM: importación diferida en el bloque de optimización
# GRAC-RAM: importación diferida: from openpyxl import load_workbook


from flask import (
    Flask, request, render_template_string, redirect, url_for, flash, send_file
)
from flask_sqlalchemy import SQLAlchemy

# GRAC-RAM: importación diferida en el bloque de optimización
# GRAC-RAM: importación diferida en el bloque de optimización



# ✅ Matplotlib sin GUI (macOS/Flask)
os.environ["MPLBACKEND"] = "Agg"
# GRAC-RAM: importación diferida en el bloque de optimización
# GRAC-RAM: MPLBACKEND=Agg definido antes de importar bibliotecas
# GRAC-RAM: importación diferida en el bloque de optimización

# OpenAI SDK
from openai import OpenAI
from openai import AuthenticationError, OpenAIError

# PDF (ReportLab) - PRO
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
# GRAC-RAM: colors se carga bajo demanda
# GRAC-RAM: importación diferida: from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
Image = _GRACDeferredSymbol("reportlab.platypus", "Image")
from reportlab.lib.enums import TA_LEFT, TA_CENTER
# GRAC-RAM: importación diferida en el bloque de optimización
# GRAC-RAM: MPLBACKEND=Agg definido antes de importar bibliotecas
# GRAC-RAM: importación diferida en el bloque de optimización
from flask import send_file
Image = _GRACDeferredSymbol("reportlab.platypus", "Image")
from reportlab.lib.pagesizes import A4, landscape
# GRAC-RAM: importación diferida: from reportlab.lib.styles import getSampleStyleSheet
# GRAC-RAM: colors se carga bajo demanda
from reportlab.lib.units import cm
import hashlib
import base64
from datetime import datetime
from cryptography.fernet import Fernet, InvalidToken
import socket
import ipaddress
import tempfile
import shlex
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

BASE_DIR = os.path.dirname(os.path.abspath(__file__))



# =========================
# OPENROUTER CONFIG (FIJO EN CÓDIGO)
# =========================

# ✅ MODELO SGSI (agregar esto)
OPENROUTER_MODEL = "deepseek/deepseek-chat"
OPENROUTER_MODEL_SGSI = OPENROUTER_MODEL
OPENROUTER_MAX_TOKENS = 1500
OPENROUTER_MAX_TOKENS_SGSI = OPENROUTER_MAX_TOKENS

# ==========================================================================================================================================
#                                                    Configuración Jira (integrada en Python)
# ==========================================================================================================================================

JIRA_CRYPTO_SECRET = os.getenv("JIRA_CRYPTO_SECRET", "dev-secret")

# ==========================================
# Cliente OpenRouter usando key cifrada
# ==========================================
# ==========================================
# Cliente IA dinámico (OpenRouter / Ollama)
# ==========================================
def get_openrouter_client():
    """
    Mantiene el mismo nombre para NO romper módulos existentes,
    pero internamente decide si usar OpenRouter u Ollama.
    """
    provider = (get_ai_provider() or "openrouter").strip().lower()

    if provider == "ollama":
        return {
            "provider": "ollama",
            "base_url": (get_ollama_base_url() or "http://localhost:11434").rstrip("/"),
            "model": (get_ollama_model() or "llama3.1").strip()
        }

    api_key = get_openrouter_api_key()

    if not api_key:
        raise RuntimeError("No existe OPENROUTER_API_KEY configurada en Administración.")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        default_headers={
            "HTTP-Referer": "http://localhost",
            "X-Title": "SGSI Flask App"
        }
    )

    return {
        "provider": "openrouter",
        "client": client,
        "model": (os.environ.get("OPENROUTER_MODEL") or OPENROUTER_MODEL or "deepseek/deepseek-chat")
    }

def ai_text_general(prompt: str, system_prompt: str | None = None, temperature: float = 0.2, max_tokens: int = 350) -> str:
    """
    Helper general de IA para todo el SGSI.
    Usa OpenRouter u Ollama según la configuración activa.
    """
    ai_cfg = get_openrouter_client()
    provider = ai_cfg.get("provider")

    if provider == "ollama":
        base_url = (ai_cfg.get("base_url") or "").rstrip("/")
        model = (ai_cfg.get("model") or "").strip()

        if not base_url:
            raise RuntimeError("No hay OLLAMA_BASE_URL configurada en Administración.")
        if not model:
            raise RuntimeError("No hay OLLAMA_MODEL configurado en Administración.")

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        try:
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

            data = resp.json() or {}

            texto = (data.get("response") or "").strip()

            if not texto:
                texto = (data.get("message") or "").strip()

            if not texto:
                raise RuntimeError(f"Ollama respondió sin contenido. Respuesta: {str(data)[:500]}")

            return limpiar_texto_ia_global(texto)

        finally:
            liberar_memoria_ollama_seguro()
            
    client = ai_cfg["client"]
    model_name = ai_cfg.get("model") or OPENROUTER_MODEL or "deepseek/deepseek-chat"
    max_tokens_safe = min(int(max_tokens or 350), 350)

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    resp = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens_safe
    )

    texto = (resp.choices[0].message.content or "").strip()
    if not texto:
        raise RuntimeError("OpenRouter respondió sin contenido.")
    return limpiar_texto_ia_global(texto)


# === MAPAS Y FUNCIÓN PARA CALCULAR RIESGO ===

mapa_probabilidad = {
    "Rara vez o Muy baja": 1,
    "Eventualmente o baja": 2,
    "Puede ocurrir o Moderada": 3,
    "Probable o Alta": 4,
    "Muy frecuente o Muy Alta": 5
}

mapa_impacto = {
    "Insignificante o Inferior": 1,
    "Menor": 2,
    "Moderado o Importante": 3,
    "Mayor": 4,
    "Catastrófico o Crítico": 5
}

def liberar_memoria_ollama_seguro():
    """
    Libera memoria del modelo activo en Ollama sin eliminarlo del disco.
    Funciona para TODOS los módulos.
    """
    try:
        if (get_ai_provider() or "").lower() != "ollama":
            return

        modelo = (get_ollama_model() or "").strip()
        if not modelo:
            return

        import subprocess
        subprocess.run(
            ["ollama", "stop", modelo],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        print(f"🧠 Ollama liberado en memoria: {modelo}")

    except Exception as e:
        print("⚠️ Error liberando memoria Ollama:", repr(e))

def limpiar_texto_ia_global(texto: str) -> str:
    if not texto:
        return ""

    # Quitar markdown tipo **texto** o ***texto***
    texto = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", texto)

    # Quitar asteriscos sueltos
    texto = texto.replace("*", "")

    # Quitar headers tipo ### Título
    texto = re.sub(r"^#{1,6}\s*", "", texto, flags=re.MULTILINE)

    # Limpiar saltos de línea duplicados
    texto = re.sub(r"\n\s*\n", "\n\n", texto)

    return texto.strip()

def calcular_riesgo(probabilidad_txt, impacto_txt):
    prob = mapa_probabilidad.get(probabilidad_txt, 0)
    imp = mapa_impacto.get(impacto_txt, 0)
    puntaje = prob * imp

    # Clasificación por niveles
    if puntaje >= 16:
        nivel = "Extremo"
    elif puntaje >= 12:
        nivel = "Alto"
    elif puntaje >= 6:
        nivel = "Moderado"
    else:
        nivel = "Bajo"

    return nivel, puntaje


app = Flask(__name__)
# La cookie de autenticación termina con la sesión del navegador.
app.config["SESSION_PERMANENT"] = False

# ============================================================
# BARRA DE PROGRESO GLOBAL SGSI - PARA TODOS LOS PROCESOS
# CORREGIDA: NO BLOQUEA CUANDO SE CANCELA UN CONFIRM()
# ============================================================

SGSI_PROGRESS_GLOBAL = """
<style>
#sgsiProgressOverlay {
    position: fixed;
    inset: 0;
    z-index: 999999;
    background: rgba(8, 24, 48, .62);
    backdrop-filter: blur(5px);
    display: none;
    align-items: center;
    justify-content: center;
}
.sgsi-progress-card {
    width: min(460px, 92vw);
    background: rgba(255,255,255,.96);
    border-radius: 22px;
    padding: 28px 30px;
    box-shadow: 0 18px 45px rgba(0,0,0,.35);
    text-align: center;
    border: 1px solid rgba(255,255,255,.55);
}
.sgsi-progress-title {
    font-size: 1.2rem;
    font-weight: 800;
    color: #1d4f8f;
    margin-bottom: 8px;
}
.sgsi-progress-text {
    font-size: .94rem;
    color: #526173;
    margin-bottom: 18px;
}
.sgsi-progress-percent {
    font-size: 1rem;
    font-weight: 800;
    color: #1d4f8f;
    margin-bottom: 8px;
}
.sgsi-progress-bar-wrap {
    height: 16px;
    background: #e8eef7;
    border-radius: 999px;
    overflow: hidden;
    box-shadow: inset 0 2px 5px rgba(0,0,0,.10);
}
.sgsi-progress-bar {
    width: 0%;
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(135deg, #2f6fb6 0%, #3f86d6 55%, #5aa3ea 100%);
    transition: width .35s ease;
}
.sgsi-progress-footer {
    margin-top: 14px;
    font-size: .82rem;
    color: #6c7a89;
}

    /* =========================================================
       AJUSTE FINAL UI ARKYNTECH-GRAC
       - Header más delgado
       - Logo pegado a la izquierda
       - Perfil compacto
       - Menú lateral más fino y letras más pequeñas
       ========================================================= */
    .sgsi-topbar{
      min-height:58px !important;
      height:58px !important;
      overflow:visible !important;
      position:fixed !important;
      top:0 !important;
      left:0 !important;
      right:0 !important;
      z-index:10050 !important;
    }
    .sgsi-topbar-inner{
      min-height:58px !important;
      height:58px !important;
      padding:0 24px 0 14px !important;
      margin:0 !important;
      overflow:visible !important;
    }
    .sgsi-brand{
      margin-left:0 !important;
      padding-left:0 !important;
      min-width:220px !important;
      width:220px !important;
      height:58px !important;
      display:flex !important;
      align-items:center !important;
      justify-content:flex-start !important;
      overflow:hidden !important;
    }
    .sgsi-logo{
      height:44px !important;
      width:auto !important;
      max-width:205px !important;
      object-fit:contain !important;
      object-position:left center !important;
      margin:0 !important;
      filter:drop-shadow(0 4px 9px rgba(11,58,110,.14)) !important;
    }
    .sgsi-user-link{
      padding:4px 10px 4px 5px !important;
      border-radius:999px !important;
      font-size:.72rem !important;
      min-height:30px !important;
    }
    .sgsi-user-photo{
      width:26px !important;
      height:26px !important;
    }
    .sgsi-user-name{
      font-size:.72rem !important;
      max-width:118px !important;
      font-weight:600 !important;
      line-height:1 !important;
    }

    /* =========================================================
       COMPACTACIÓN GLOBAL DE TÍTULOS DE TODOS LOS MÓDULOS
       Aplica a cualquier pantalla/módulo que use h1, hero, header,
       banner, card de título o contenedor principal.
       ========================================================= */

    /* Títulos principales globales */
    h1,
    .h1,
    .page-title,
    .module-title,
    .hero-title,
    .main-title,
    .titulo-modulo,
    .titulo-principal,
    .sgsi-page-title,
    .sgsi-module-title,
    .app-title,
    .content-title,
    .section-title-main,
    .module-header-title,
    .card-title-main,
    .dashboard-title,
    .view-title {
      font-size:1.58rem !important;
      line-height:1.12 !important;
      margin-bottom:.28rem !important;
      letter-spacing:-.02em !important;
    }

    /* Títulos dentro de banners/headers de módulos */
    .hero-card h1,
    .module-hero h1,
    .page-hero h1,
    .sgsi-hero h1,
    .sgsi-module-hero h1,
    .module-header h1,
    .page-header h1,
    .header-card h1,
    .title-card h1,
    .banner h1,
    .banner-title,
    .riesgos-hero h1,
    .riesgos-header h1,
    .dashboard-header h1,
    .dashboard-hero h1,
    .bcp-hero h1,
    .cc-hero h1,
    .madurez-hero h1,
    .vulnerabilidades-hero h1,
    .incidentes-hero h1 {
      font-size:1.48rem !important;
      line-height:1.10 !important;
      margin:0 0 .20rem 0 !important;
    }

    /* Subtítulos/descripciones de encabezado */
    .hero-card p,
    .module-hero p,
    .page-hero p,
    .sgsi-hero p,
    .sgsi-module-hero p,
    .module-header p,
    .page-header p,
    .header-card p,
    .title-card p,
    .banner p,
    .subtitle,
    .page-subtitle,
    .module-subtitle,
    .hero-subtitle,
    .sgsi-page-subtitle,
    .sgsi-module-subtitle,
    .text-subtitle {
      font-size:.82rem !important;
      line-height:1.22 !important;
      margin-bottom:0 !important;
    }

    /* Banners/headers más bajos para ganar espacio vertical */
    .hero-card,
    .module-hero,
    .page-hero,
    .sgsi-hero,
    .sgsi-module-hero,
    .module-header,
    .page-header,
    .header-card,
    .title-card,
    .banner,
    .dashboard-header,
    .dashboard-hero,
    .riesgos-hero,
    .riesgos-header,
    .bcp-hero,
    .cc-hero,
    .madurez-hero,
    .vulnerabilidades-hero,
    .incidentes-hero {
      min-height:76px !important;
      padding:12px 22px !important;
      margin-bottom:12px !important;
      border-radius:18px !important;
    }

    /* Iconos decorativos dentro de encabezados */
    .hero-card .icon-box,
    .module-hero .icon-box,
    .page-hero .icon-box,
    .sgsi-hero .icon-box,
    .module-header .icon-box,
    .page-header .icon-box,
    .title-card .icon-box,
    .header-card .icon-box,
    .banner .icon-box,
    .hero-icon,
    .module-icon,
    .page-icon,
    .title-icon {
      width:48px !important;
      height:48px !important;
      min-width:48px !important;
      border-radius:14px !important;
      font-size:1.25rem !important;
    }

    /* Badges superiores tipo “SGSI · Módulo” */
    .hero-card .badge,
    .module-hero .badge,
    .page-hero .badge,
    .sgsi-hero .badge,
    .module-header .badge,
    .page-header .badge,
    .header-card .badge,
    .title-card .badge,
    .banner .badge,
    .module-badge,
    .page-badge,
    .hero-badge {
      font-size:.68rem !important;
      padding:.26rem .62rem !important;
      line-height:1 !important;
    }

    /* Menú lateral con letras más pequeñas y compacto */
    .sgsi-sidebar,
    .sgsi-sidebar *,
    .sidebar,
    .sidebar *,
    .sidebar-menu,
    .sidebar-menu *,
    .sgsi-menu,
    .sgsi-menu * {
      font-size:.82rem !important;
    }

    .sgsi-sidebar a,
    .sidebar a,
    .sidebar-menu a,
    .sgsi-menu a,
    .sgsi-sidebar .nav-link,
    .sidebar .nav-link,
    .sidebar-menu .nav-link,
    .sgsi-menu .nav-link {
      font-size:.82rem !important;
      line-height:1.12 !important;
      padding-top:8px !important;
      padding-bottom:8px !important;
    }

    /* Tarjetas KPI/resumen más compactas */
    .stat-card,
    .summary-card,
    .kpi-card,
    .metric-card,
    .dashboard-card-sm,
    .resumen-card {
      min-height:58px !important;
      padding:10px 14px !important;
    }

    .stat-card h2,
    .summary-card h2,
    .kpi-card h2,
    .metric-card h2,
    .resumen-card h2,
    .stat-value,
    .kpi-value,
    .metric-value {
      font-size:1.28rem !important;
      line-height:1.05 !important;
      margin-bottom:0 !important;
    }

    .stat-card .label,
    .summary-card .label,
    .kpi-card .label,
    .metric-card .label,
    .resumen-card .label,
    .stat-label,
    .kpi-label,
    .metric-label {
      font-size:.76rem !important;
      line-height:1.05 !important;
    }

    /* Espaciado general para aprovechar más pantalla */
    .sgsi-content,
    .sgsi-main,
    .main-content,
    .page-content,
    .content-wrapper {
      padding-top:12px !important;
    }

</style>

<div id="sgsiProgressOverlay">
    <div class="sgsi-progress-card">
        <div class="sgsi-progress-title">Procesando solicitud</div>
        <div class="sgsi-progress-text" id="sgsiProgressText">
            Por favor espera mientras el sistema ejecuta el proceso...
        </div>
        <div class="sgsi-progress-percent" id="sgsiProgressPercent">0%</div>
        <div class="sgsi-progress-bar-wrap">
            <div class="sgsi-progress-bar" id="sgsiProgressBar"></div>
        </div>
        <div class="sgsi-progress-footer">SGSI — Arkyntech GRAC</div>
    </div>
</div>

<script>
(function () {
    if (window.__SGSI_PROGRESS_READY__) return;
    window.__SGSI_PROGRESS_READY__ = true;

    let sgsiProgressValue = 0;
    let sgsiProgressTimer = null;
    let sgsiProgressVisible = false;
    let sgsiProgressManual = false;
    let sgsiAllowBeforeUnload = false;

    function getOverlay() {
        return document.getElementById("sgsiProgressOverlay");
    }

    function setSGSIProgress(percent) {
        const bar = document.getElementById("sgsiProgressBar");
        const label = document.getElementById("sgsiProgressPercent");

        sgsiProgressValue = Math.max(0, Math.min(100, Number(percent) || 0));

        if (bar) bar.style.width = sgsiProgressValue + "%";
        if (label) label.innerText = Math.round(sgsiProgressValue) + "%";
    }

    function stopSGSIProgressAuto() {
        if (sgsiProgressTimer) {
            clearInterval(sgsiProgressTimer);
            sgsiProgressTimer = null;
        }
    }

    function startSGSIProgressAuto() {
        stopSGSIProgressAuto();

        sgsiProgressTimer = setInterval(function () {
            if (!sgsiProgressVisible) {
                stopSGSIProgressAuto();
                return;
            }

            let next = sgsiProgressValue;

            if (next < 15) {
                next += 3;
            } else if (next < 35) {
                next += 2.4;
            } else if (next < 60) {
                next += 1.7;
            } else if (next < 78) {
                next += 1.1;
            } else if (next < 90) {
                next += 0.55;
            } else if (next < 96) {
                next += 0.18;
            } else {
                next = 96;
            }

            setSGSIProgress(next);
        }, 420);
    }

    function showSGSIProgress(message) {
        const overlay = getOverlay();
        const text = document.getElementById("sgsiProgressText");

        if (!overlay) return true;

        if (text && message) {
            text.innerText = message;
        }

        sgsiProgressVisible = true;
        sgsiAllowBeforeUnload = true;

        overlay.style.display = "flex";
        overlay.style.visibility = "visible";
        overlay.style.opacity = "1";
        overlay.style.pointerEvents = "auto";
        overlay.classList.remove("d-none");

        setSGSIProgress(3);
        startSGSIProgressAuto();

        return true;
    }

    // Permite a los módulos que calculan un progreso REAL en el servidor
    // compartir el mismo cuadro global sin porcentajes simulados.
    function showSGSIProgressManual(message, percent) {
        showSGSIProgress(message);
        sgsiProgressManual = true;
        stopSGSIProgressAuto();
        setSGSIProgress(percent);
        return true;
    }

    function hideSGSIProgress() {
        const overlay = getOverlay();

        sgsiProgressManual = false;
        sgsiProgressVisible = false;
        sgsiAllowBeforeUnload = false;

        stopSGSIProgressAuto();

        if (overlay) {
            overlay.style.display = "none";
            overlay.style.visibility = "hidden";
            overlay.style.opacity = "0";
            overlay.style.pointerEvents = "none";
            overlay.classList.add("d-none");
        }

        setSGSIProgress(0);
    }

    function finishSGSIProgress() {
        setSGSIProgress(100);
        setTimeout(hideSGSIProgress, 350);
    }

    function shouldIgnoreElement(el) {
        if (!el) return true;

        if (el.dataset && el.dataset.noProgress === "true") return true;

        if (
            el.classList &&
            (
                el.classList.contains("dropdown-toggle") ||
                el.classList.contains("no-progress") ||
                el.classList.contains("btn-close")
            )
        ) {
            return true;
        }

        if (
            el.getAttribute("data-bs-toggle") ||
            el.getAttribute("data-toggle")
        ) {
            return true;
        }

        return false;
    }

    function shouldIgnoreLink(link) {
        if (!link) return true;

        const href = link.getAttribute("href") || "";
        const hrefLower = href.toLowerCase();

        if (
            !href ||
            href === "#" ||
            href.startsWith("#") ||
            href.startsWith("javascript:") ||
            hrefLower.includes(".pdf") ||
            hrefLower.includes("pdf") ||
            hrefLower.includes("reporte") ||
            hrefLower.includes("descargar") ||
            // Las rutas de exportación devuelven archivos descargables (Excel/CSV),
            // no una nueva página HTML: no activar la barra de progreso.
            hrefLower.includes("/exportar/") ||
            hrefLower.includes("exportar_excel") ||
            hrefLower.includes("download") ||
            link.target === "_blank" ||
            link.hasAttribute("download") ||
            shouldIgnoreElement(link)
        ) {
            return true;
        }

        return false;
    }

    function isSubmitButton(el) {
        if (!el) return false;

        const tag = (el.tagName || "").toLowerCase();
        const type = (el.getAttribute("type") || "").toLowerCase();

        return (
            (tag === "button" && (type === "" || type === "submit")) ||
            (tag === "input" && type === "submit")
        );
    }

    function closestSubmitterFromEvent(e) {
        if (!e) return null;

        if (e.submitter) return e.submitter;

        const active = document.activeElement;
        if (active && isSubmitButton(active)) return active;

        return null;
    }

    window.showSGSIProgress = showSGSIProgress;
    window.showSGSIProgressManual = showSGSIProgressManual;
    window.hideSGSIProgress = hideSGSIProgress;
    window.finishSGSIProgress = finishSGSIProgress;
    window.setSGSIProgress = setSGSIProgress;
    window.startSGSIProgressAuto = startSGSIProgressAuto;

    window.ai42001Progress = function (mensaje) {
        return showSGSIProgress(mensaje || "Generando y procesando información...");
    };

    window.sgsiProgressStart = function (mensaje) {
        return showSGSIProgress(mensaje || "Generando y procesando información...");
    };

    document.addEventListener("submit", function (e) {
        const form = e.target;

        if (!form || shouldIgnoreElement(form)) {
            return;
        }

        const submitter = closestSubmitterFromEvent(e);

        if (submitter && shouldIgnoreElement(submitter)) {
            return;
        }

        setTimeout(function () {
            if (e.defaultPrevented) {
                hideSGSIProgress();
                return;
            }

            const msg =
                (submitter && submitter.dataset && submitter.dataset.progressText) ||
                (form.dataset && form.dataset.progressText) ||
                "Generando y procesando información...";

            showSGSIProgress(msg);
        }, 30);
    }, true);

    document.addEventListener("click", function (e) {
        const btn = e.target.closest("button, a, input[type='submit']");
        if (!btn) return;
        if (shouldIgnoreElement(btn)) return;

        const tag = (btn.tagName || "").toLowerCase();

        if (isSubmitButton(btn)) {
            return;
        }

        if (tag === "a") {
            if (shouldIgnoreLink(btn)) return;

            showSGSIProgress(
                (btn.dataset && btn.dataset.progressText) ||
                "Cargando información..."
            );
        }
    }, true);

    const originalConfirm = window.confirm;

    window.confirm = function () {
        const result = originalConfirm.apply(window, arguments);

        if (!result) {
            hideSGSIProgress();
        }

        return result;
    };

    const originalFetch = window.fetch;

    if (originalFetch) {
        window.fetch = function () {
            const shouldShow = sgsiProgressVisible === true && !sgsiProgressManual;

            return originalFetch.apply(this, arguments)
                .then(function (response) {
                    if (shouldShow) finishSGSIProgress();
                    return response;
                })
                .catch(function (error) {
                    if (shouldShow) hideSGSIProgress();
                    throw error;
                });
        };
    }

    window.addEventListener("pageshow", function () {
        hideSGSIProgress();
    });

    window.addEventListener("pagehide", function () {
        stopSGSIProgressAuto();
    });

    window.addEventListener("beforeunload", function () {
        if (sgsiAllowBeforeUnload) {
            setSGSIProgress(Math.max(sgsiProgressValue, 12));
        }
    });
})();
</script>
"""


@app.after_request
def inject_sgsi_progress_bar(response):
    try:
        content_type = response.headers.get("Content-Type", "")

        if "text/html" not in content_type:
            return response

        html_response = response.get_data(as_text=True)

        if not html_response:
            return response

        # Evita inyectar duplicado
        if "id=\"sgsiProgressOverlay\"" in html_response or "id='sgsiProgressOverlay'" in html_response:
            return response

        if "</body>" in html_response:
            html_response = html_response.replace(
                "</body>",
                SGSI_PROGRESS_GLOBAL + "\n</body>"
            )
        else:
            html_response += SGSI_PROGRESS_GLOBAL

        response.set_data(html_response)
        response.headers["Content-Length"] = str(len(response.get_data()))

    except Exception as e:
        print("No se pudo inyectar barra de progreso SGSI:", repr(e))

    return response

# ============================================================
# CIERRE DE SESIÓN AL CERRAR PESTAÑA O NAVEGADOR
# ============================================================
# pagehide también ocurre al recargar o navegar dentro del sitio. El tab_id
# identifica la pestaña y el page_id identifica cada documento cargado. Así la
# página siguiente puede cancelar el cierre pendiente de una navegación normal.

BROWSER_SESSION_DB_PATH = os.path.join(app.instance_path, "browser_sessions.db")
_BROWSER_SESSION_DB_LOCK = threading.RLock()
_BROWSER_SESSION_KEY = "_grac_browser_session_id"

try:
    BROWSER_SESSION_GRACE_SECONDS = min(
        15.0,
        max(2.0, float(os.getenv("GRAC_TAB_CLOSE_GRACE_SECONDS", "5")))
    )
except (TypeError, ValueError):
    BROWSER_SESSION_GRACE_SECONDS = 5.0


def _browser_session_connect():
    os.makedirs(app.instance_path, exist_ok=True)
    conn = sqlite3.connect(BROWSER_SESSION_DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=10000")
    return conn


def _browser_session_init_db():
    with _BROWSER_SESSION_DB_LOCK:
        conn = _browser_session_connect()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS browser_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    revoked_at REAL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS browser_tabs (
                    session_id TEXT NOT NULL,
                    tab_id TEXT NOT NULL,
                    current_page_id TEXT,
                    close_requested_at REAL,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY (session_id, tab_id)
                );

                CREATE INDEX IF NOT EXISTS ix_browser_tabs_pending
                ON browser_tabs (session_id, close_requested_at);
                """
            )
            cutoff = time.time() - (30 * 24 * 60 * 60)
            conn.execute(
                "DELETE FROM browser_tabs WHERE updated_at < ?",
                (cutoff,)
            )
            conn.execute(
                "DELETE FROM browser_sessions WHERE updated_at < ?",
                (cutoff,)
            )
            conn.commit()
        finally:
            conn.close()


def _browser_lifecycle_id(value):
    value = str(value or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{8,180}", value):
        return None
    return value


def _browser_session_id(create=True):
    session_id = _browser_lifecycle_id(session.get(_BROWSER_SESSION_KEY))

    if not session_id and create:
        session_id = secrets.token_urlsafe(32)
        session[_BROWSER_SESSION_KEY] = session_id

    return session_id


def _browser_session_upsert(conn, session_id, now):
    conn.execute(
        """
        INSERT INTO browser_sessions
            (session_id, user_id, revoked_at, created_at, updated_at)
        VALUES (?, ?, NULL, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            user_id = excluded.user_id,
            updated_at = excluded.updated_at
        """,
        (session_id, session.get("user_id"), now, now)
    )

    state = conn.execute(
        "SELECT revoked_at FROM browser_sessions WHERE session_id = ?",
        (session_id,)
    ).fetchone()
    return not state or state["revoked_at"] is None


def _browser_session_expire_pending(conn, session_id, now):
    pending = conn.execute(
        """
        SELECT MIN(close_requested_at) AS requested_at
        FROM browser_tabs
        WHERE session_id = ? AND close_requested_at IS NOT NULL
        """,
        (session_id,)
    ).fetchone()

    requested_at = pending["requested_at"] if pending else None
    if requested_at is None:
        return False

    if (now - float(requested_at)) < BROWSER_SESSION_GRACE_SECONDS:
        return False

    conn.execute(
        """
        UPDATE browser_sessions
        SET revoked_at = ?, updated_at = ?
        WHERE session_id = ?
        """,
        (now, now, session_id)
    )
    return True


def _browser_session_touch_and_validate():
    session_id = _browser_session_id(create=True)
    now = time.time()

    with _BROWSER_SESSION_DB_LOCK:
        conn = _browser_session_connect()
        try:
            if not _browser_session_upsert(conn, session_id, now):
                conn.commit()
                return False

            expired = _browser_session_expire_pending(
                conn, session_id, now
            )
            conn.commit()
            return not expired
        finally:
            conn.close()


def _browser_session_resume_tab(tab_id, page_id):
    session_id = _browser_session_id(create=True)
    now = time.time()

    with _BROWSER_SESSION_DB_LOCK:
        conn = _browser_session_connect()
        try:
            if not _browser_session_upsert(conn, session_id, now):
                conn.commit()
                return False

            current_tab = conn.execute(
                """
                SELECT current_page_id, close_requested_at
                FROM browser_tabs
                WHERE session_id = ? AND tab_id = ?
                """,
                (session_id, tab_id)
            ).fetchone()

            # El mismo page_id con cierre pendiente puede ser un aviso que llegó
            # después del fetch inicial. Un page_id distinto es navegación o
            # recarga y sí cancela el cierre de la página anterior.
            same_page_pending = bool(
                current_tab
                and current_tab["close_requested_at"] is not None
                and current_tab["current_page_id"] == page_id
            )

            if same_page_pending:
                conn.execute(
                    """
                    UPDATE browser_tabs
                    SET updated_at = ?
                    WHERE session_id = ? AND tab_id = ?
                    """,
                    (now, session_id, tab_id)
                )
            else:
                conn.execute(
                    """
                    INSERT INTO browser_tabs
                        (session_id, tab_id, current_page_id,
                         close_requested_at, updated_at)
                    VALUES (?, ?, ?, NULL, ?)
                    ON CONFLICT(session_id, tab_id) DO UPDATE SET
                        current_page_id = excluded.current_page_id,
                        close_requested_at = NULL,
                        updated_at = excluded.updated_at
                    """,
                    (session_id, tab_id, page_id, now)
                )

            expired = _browser_session_expire_pending(
                conn, session_id, now
            )
            conn.commit()
            return not expired
        finally:
            conn.close()


def _browser_session_mark_tab_closed(tab_id, page_id):
    session_id = _browser_session_id(create=False)
    if not session_id:
        return

    now = time.time()

    with _BROWSER_SESSION_DB_LOCK:
        conn = _browser_session_connect()
        try:
            current_tab = conn.execute(
                """
                SELECT current_page_id
                FROM browser_tabs
                WHERE session_id = ? AND tab_id = ?
                """,
                (session_id, tab_id)
            ).fetchone()

            if current_tab is None:
                conn.execute(
                    """
                    INSERT INTO browser_tabs
                        (session_id, tab_id, current_page_id,
                         close_requested_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (session_id, tab_id, page_id, now, now)
                )
            elif current_tab["current_page_id"] == page_id:
                # Ignora un beacon tardío de una página anterior.
                conn.execute(
                    """
                    UPDATE browser_tabs
                    SET close_requested_at = ?, updated_at = ?
                    WHERE session_id = ? AND tab_id = ?
                    """,
                    (now, now, session_id, tab_id)
                )

            conn.commit()
        finally:
            conn.close()


def _browser_session_revoke(session_id=None):
    session_id = _browser_lifecycle_id(
        session_id or session.get(_BROWSER_SESSION_KEY)
    )
    if not session_id:
        return

    now = time.time()

    with _BROWSER_SESSION_DB_LOCK:
        conn = _browser_session_connect()
        try:
            conn.execute(
                """
                UPDATE browser_sessions
                SET revoked_at = ?, updated_at = ?
                WHERE session_id = ?
                """,
                (now, now, session_id)
            )
            conn.commit()
        finally:
            conn.close()


try:
    _browser_session_init_db()
except Exception as exc:
    # No impide arrancar GRAC; la validación se reintentará en cada acceso.
    print("No se pudo inicializar el control de pestañas:", repr(exc))


@app.before_request
def enforce_browser_session_lifecycle():
    endpoint = request.endpoint or ""

    if endpoint in {
        "static",
        "grac_browser_tab_resume",
        "grac_browser_tab_close",
        "logout"
    }:
        return None

    if not session.get("user_id"):
        return None

    try:
        valid = _browser_session_touch_and_validate()
    except Exception as exc:
        print("No se pudo validar la sesión del navegador:", repr(exc))
        return None

    if valid:
        return None

    session.clear()

    if endpoint == "login":
        return None

    if request.path.startswith("/api/") or request.is_json:
        return jsonify({
            "ok": False,
            "error": "La sesión finalizó al cerrarse la pestaña o el navegador."
        }), 401

    flash(
        "La sesión se cerró porque se cerró la pestaña o el navegador.",
        "info"
    )
    return redirect(url_for("login"))


@app.route("/session/lifecycle/resume", methods=["POST"])
def grac_browser_tab_resume():
    if not session.get("user_id"):
        return jsonify({"ok": False}), 401

    payload = request.get_json(silent=True) or request.form
    tab_id = _browser_lifecycle_id(payload.get("tab_id"))
    page_id = _browser_lifecycle_id(payload.get("page_id"))

    if not tab_id or not page_id:
        return jsonify({"ok": False, "error": "Identificador inválido."}), 400

    try:
        valid = _browser_session_resume_tab(tab_id, page_id)
    except Exception as exc:
        print("No se pudo reanudar la sesión de pestaña:", repr(exc))
        return jsonify({
            "ok": False,
            "error": "Control de sesión no disponible."
        }), 503

    if not valid:
        session.clear()
        flash(
            "La sesión se cerró porque se cerró la pestaña o el navegador.",
            "info"
        )
        return jsonify({
            "ok": False,
            "login_url": url_for("login")
        }), 401

    return jsonify({"ok": True})


@app.route("/session/lifecycle/close", methods=["POST"])
def grac_browser_tab_close():
    if not session.get("user_id"):
        return "", 204

    payload = request.get_json(silent=True) or request.form
    tab_id = _browser_lifecycle_id(payload.get("tab_id"))
    page_id = _browser_lifecycle_id(payload.get("page_id"))

    if tab_id and page_id:
        try:
            _browser_session_mark_tab_closed(tab_id, page_id)
        except Exception as exc:
            print("No se pudo registrar el cierre de pestaña:", repr(exc))

    return "", 204


BROWSER_SESSION_LIFECYCLE_HTML = r"""
<script id="gracBrowserSessionLifecycle">
(function () {
  "use strict";

  if (window.__gracBrowserSessionLifecycleInstalled) return;
  window.__gracBrowserSessionLifecycleInstalled = true;

  function newId() {
    try {
      if (window.crypto && typeof window.crypto.randomUUID === "function") {
        return window.crypto.randomUUID();
      }
      if (window.crypto && typeof window.crypto.getRandomValues === "function") {
        const bytes = new Uint8Array(16);
        window.crypto.getRandomValues(bytes);
        return Array.from(bytes, function (b) {
          return b.toString(16).padStart(2, "0");
        }).join("");
      }
    } catch (_) {}

    return Date.now().toString(36) + "-" +
      Math.random().toString(36).slice(2) +
      Math.random().toString(36).slice(2);
  }

  let tabId;
  try {
    tabId = window.sessionStorage.getItem("gracBrowserTabId");
    if (!tabId) {
      tabId = newId();
      window.sessionStorage.setItem("gracBrowserTabId", tabId);
    }
  } catch (_) {
    tabId = newId();
  }

  const pageId = newId();
  const resumeUrl = "/session/lifecycle/resume";
  const closeUrl = "/session/lifecycle/close";

  function resumeSession() {
    const body = new URLSearchParams({tab_id: tabId, page_id: pageId});

    fetch(resumeUrl, {
      method: "POST",
      credentials: "same-origin",
      cache: "no-store",
      keepalive: true,
      headers: {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"
      },
      body: body.toString()
    }).then(function (response) {
      if (response.status === 401) {
        window.location.replace("/login");
      }
    }).catch(function () {
      // Un corte puntual de red no debe interrumpir la página actual.
    });
  }

  function notifyClose(event) {
    // Una página guardada en bfcache no está cerrada y puede restaurarse.
    if (event && event.persisted) return;

    const form = new FormData();
    form.append("tab_id", tabId);
    form.append("page_id", pageId);

    let queued = false;
    try {
      queued = !!(
        navigator.sendBeacon &&
        navigator.sendBeacon(closeUrl, form)
      );
    } catch (_) {}

    if (!queued) {
      const body = new URLSearchParams({tab_id: tabId, page_id: pageId});
      fetch(closeUrl, {
        method: "POST",
        credentials: "same-origin",
        keepalive: true,
        headers: {
          "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"
        },
        body: body.toString()
      }).catch(function () {});
    }
  }

  resumeSession();

  window.addEventListener("pageshow", function (event) {
    if (event.persisted) resumeSession();
  });

  window.addEventListener("pagehide", notifyClose, {capture: true});
})();
</script>
"""


@app.after_request
def inject_browser_session_lifecycle(response):
    try:
        if response.status_code != 200 or response.is_streamed:
            return response

        if not session.get("user_id"):
            return response

        if "text/html" not in response.headers.get("Content-Type", ""):
            return response

        html_response = response.get_data(as_text=True)

        if (
            not html_response
            or "gracBrowserSessionLifecycle" in html_response
            or "</body>" not in html_response
        ):
            return response

        html_response = html_response.replace(
            "</body>",
            BROWSER_SESSION_LIFECYCLE_HTML + "\n</body>",
            1
        )
        response.set_data(html_response)
        response.headers["Content-Length"] = str(len(response.get_data()))
    except Exception as exc:
        print("No se pudo inyectar el control de sesión:", repr(exc))

    return response


# ============================================================================================================================================
#                                                               LOGS DE AUDITORÍA - DB INDEPENDIENTE
# ============================================================================================================================================

os.makedirs(app.instance_path, exist_ok=True)
LOG_DB_PATH = os.path.join(app.instance_path, "Log.db")

def get_log_db_connection():
    conn = sqlite3.connect(LOG_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_log_db():
    conn = get_log_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS auditoria_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_hora TEXT NOT NULL,
            usuario_transaccion TEXT NOT NULL,
            novedad TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()

# ============================================================================================================================================
#                                                     DB INDEPENDIENTE LISTAS RESTRICTIVAS
# ============================================================================================================================================

LISTAS_DB_PATH = os.path.join(app.instance_path, "listas_restrictivas.db")

def get_listas_db_connection():
    conn = sqlite3.connect(LISTAS_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_listas_db():
    conn = get_listas_db_connection()
    cur = conn.cursor()

    # ------------------------------------------------------------
    # Base de registros / fuentes
    # ------------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS listas_restrictivas_fuente (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fuente TEXT NOT NULL,
            nombre TEXT NOT NULL,
            alias TEXT,
            tipo_documento TEXT,
            numero_documento TEXT,
            pais TEXT,
            categoria TEXT,
            observaciones TEXT,
            activo TEXT NOT NULL DEFAULT 'Sí',
            fecha_actualizacion TEXT
        )
    """)

    # ------------------------------------------------------------
    # Historial de consultas del módulo exclusivo
    # ------------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS listas_restrictivas_consultas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            origen TEXT NOT NULL,
            proveedor_id INTEGER,
            nombre_consultado TEXT NOT NULL,
            tipo_documento TEXT,
            numero_documento TEXT,
            pais TEXT,
            fuente TEXT NOT NULL,
            resultado TEXT NOT NULL,
            nivel_riesgo TEXT NOT NULL,
            score_coincidencia REAL DEFAULT 0,
            detalle_json TEXT,
            observaciones TEXT,
            usuario TEXT,
            fecha_consulta TEXT NOT NULL
        )
    """)

    # ------------------------------------------------------------
    # Estado resumido por proveedor
    # ------------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS listas_restrictivas_estado_proveedor (
            proveedor_id INTEGER PRIMARY KEY,
            resultado TEXT,
            riesgo TEXT,
            score REAL DEFAULT 0,
            fecha_consulta TEXT,
            fuente TEXT
        )
    """)

    conn.commit()
    conn.close()


def registrar_log(usuario_transaccion, novedad):
    """
    Guarda un log en Log.db
    Campos:
    - fecha_hora
    - usuario_transaccion
    - novedad
    """
    try:
        fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        usuario_transaccion = (usuario_transaccion or "Sistema").strip()
        novedad = (novedad or "").strip()

        conn = get_log_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO auditoria_logs (fecha_hora, usuario_transaccion, novedad)
            VALUES (?, ?, ?)
        """, (fecha_hora, usuario_transaccion, novedad))
        conn.commit()
        conn.close()
    except Exception as e:
        print("Error registrando log:", repr(e))


# Inicializar la base apenas arranque la app
init_log_db()

# ============================================================================================================================================
#                                                               FIN LOGS DE AUDITORÍA - DB INDEPENDIENTE
# ============================================================================================================================================

# =========================
# CONFIG Nivel de Madurez - SOC 2
# =========================
os.makedirs(app.instance_path, exist_ok=True)

SOC2_DB_PATH = os.path.join(app.instance_path, "soc2_madurez.db")

if not app.config.get("SQLALCHEMY_BINDS"):
    app.config["SQLALCHEMY_BINDS"] = {}

app.config["SQLALCHEMY_BINDS"]["soc2_madurez"] = "sqlite:///" + SOC2_DB_PATH

# CONFIG Nivel de Madurez ISO 22301 - DB independiente
ISO22301_DB_PATH = os.path.join(app.instance_path, "iso22301_madurez.db")
app.config["SQLALCHEMY_BINDS"]["iso22301_madurez"] = "sqlite:///" + ISO22301_DB_PATH

# =========================
# CONFIG Gobierno de Firewall - DB independiente
# =========================
FIREWALL_GOV_DB_PATH = os.path.join(app.instance_path, "firewall_governance.db")
app.config["SQLALCHEMY_BINDS"]["firewall_governance"] = "sqlite:///" + FIREWALL_GOV_DB_PATH

# =========================
# CONFIG Planes de Acción - DB independiente
# =========================
PLANES_ACCION_DB_PATH = os.path.join(app.instance_path, "planes_accion.db")
app.config["SQLALCHEMY_BINDS"]["planes_accion"] = "sqlite:///" + PLANES_ACCION_DB_PATH

# =========================
# CONFIG Superficie de Ataque y Escenarios - DB independiente
# =========================
ATTACK_SURFACE_DB_PATH = os.path.join(app.instance_path, "superficie_amenazas.db")
app.config["SQLALCHEMY_BINDS"]["attack_surface"] = "sqlite:///" + ATTACK_SURFACE_DB_PATH

madurez_bp = Blueprint("madurez", __name__, url_prefix="/madurez")

# =========================
# CONFIG Nivel de Madurez - NIST CSF 2.0
# =========================

nist_madurez_bp = Blueprint("madurez_nist", __name__, url_prefix="/madurez_nist")

NIST_INSTRUMENTO_TEMPLATE_XLSX = os.path.join(
    app.root_path, "static", "templates", "Nivel de madurez NIST.xlsx"
)

NIST_TRADUCIR_EN_IMPORTACION = False  # ✅ CARGA RÁPIDA (SIN IA)
NIST_COL_ES = 2  # ✅ Columna donde está la pregunta en ESPAÑOL (B=2). Si no existe, deja 2 igual.
NIST_COL_EN = 1  # ✅ Columna donde está la pregunta en INGLÉS (A=1)

# Orden sugerido de funciones (para UI)
NIST_FUNC_ORDER = ["GOVERN", "IDENTIFY", "PROTECT", "DETECT", "RESPOND", "RECOVER"]

# Scoring (similar a ISO: SI/Parcial/No, excluye NA)
NIST_STATUS_SCORE = {
    "SI": 100,
    "PARCIAL": 50,
    "NO": 0,
    "NA": None,  # no aplica (se excluye del denominador)
}

def _nist_norm(s: str) -> str:
    s = (s or "").strip()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = s.upper()
    s = re.sub(r"\s+", " ", s).strip()
    return s

def parse_date_safe(value):
    value = (value or '').strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except Exception:
        return None

# ==========================
# ORDEN DE HOJAS / CAPÍTULOS (Madurez)
# ==========================
# Deben coincidir con los nombres que tú usas en tu análisis (xls/xlsx) y en reportes.
CHAPTER_SHEETS = [
    "4 CONTEXTO",
    "5 LIDERAZGO",
    "6 PLANIFICACIÓN",
    "7 SOPORTE",
    "8 OPERACIÓN",
    "9 EVALUACIÓN DESEMPEÑO",
    "10 MEJORA",
    "ANEXO A",
]

SHEET_ORDER = {name: i for i, name in enumerate(CHAPTER_SHEETS)}

# =========================
# CONFIG Nivel de Madurez
# =========================

APP_TITLE = "Centro de Control SGSI"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INSTRUMENTO_TEMPLATE_XLSX = os.path.join(
    BASE_DIR, "static", "templates", "instrumento_iso27001_2022.xlsx"
)

UPLOAD_DIR = "uploads"
UPLOAD_PATH = os.path.join(BASE_DIR, UPLOAD_DIR)
os.makedirs(UPLOAD_PATH, exist_ok=True)

# =========================
# Filtros
# =========================

# -- Filtro para obtener un atributo por nombre (o None si no existe)
@app.template_filter('get_attr')
def jinja_get_attr(obj, name):
    try:
        return getattr(obj, name)
    except Exception:
        return None

# -- Filtro para mostrar '—' solo cuando el valor es None (no oculta ceros)
@app.template_filter('none_dash')
def none_dash(v):
    return '—' if v is None else v

BASEDIR = os.path.abspath(os.path.dirname(__file__))

# =========================================
# Carpeta de evidencias Matriz Competencias
# =========================================

# =========================
# Carpeta donde se guardan las evidencias
# =========================
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'evidencias')
CONVERTED_FOLDER = os.path.join(app.root_path, 'static', 'evidencias_pdf')
os.makedirs(CONVERTED_FOLDER, exist_ok=True)

# ========================================
# Carpeta de evidencias (planes de mejora)
# =======================================
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app.config['UPLOAD_MEJORA_DIR'] = os.path.join(BASE_DIR, 'uploads', 'mejora')
os.makedirs(app.config['UPLOAD_MEJORA_DIR'], exist_ok=True)

def get_upload_mejora_dir():
    base_dir = os.path.abspath(os.path.dirname(__file__))
    upload_dir = os.path.join(base_dir, 'uploads', 'mejora')
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir

# =========================
# UTILIDAD: archivos PDF RFC
# =========================
def is_allowed_pdf_rfc(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'


# =========================
# Extensiones permitidas
# =========================
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx'}

ALLOWED_PDF = {'pdf'}

def allowed_pdf(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_PDF

def is_allowed_pdf(filename):
    """
    Verifica que el archivo tenga extensión .pdf (insensible a mayúsculas)
    """
    return '.' in filename and filename.lower().endswith('.pdf')

def unique_store_name(filename: str) -> str:
    """
    Genera un nombre único para guardar archivos (evidencias)
    """
    ext = os.path.splitext(filename)[1].lower()
    return f"{uuid.uuid4().hex}{ext}"

def allowed_file(filename: str) -> bool:
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower().strip()
    return ext in ALLOWED_EXTENSIONS


# =========================
# Carpeta de evidencias (proveedores)
# =========================
UPLOAD_PROV_DIR = os.path.join(app.root_path, 'uploads', 'proveedores')
os.makedirs(UPLOAD_PROV_DIR, exist_ok=True)

app.config['UPLOAD_PROVEEDORES_DIR'] = UPLOAD_PROV_DIR
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20MB total por request
ALLOWED_PDF_EXT = {'.pdf'}

# =========================
# Carpeta de evidencias (Plan de Concientización y Formación)
# =========================
UPLOAD_PLAN_DISENO_DIR = os.path.join(app.root_path, 'uploads', 'plan_diseno')
os.makedirs(UPLOAD_PLAN_DISENO_DIR, exist_ok=True)

app.config['UPLOAD_PLAN_DISENO_DIR'] = UPLOAD_PLAN_DISENO_DIR

# =========================
# Carpeta Listado Maestro de Documentos
# =========================
UPLOAD_DOCS_DIR = os.path.join(app.root_path, 'uploads', 'docs_maestro')
os.makedirs(UPLOAD_DOCS_DIR, exist_ok=True)
app.config['UPLOAD_DOCS_DIR'] = UPLOAD_DOCS_DIR
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB


# =========================
# Configuración final del upload folder
# =========================
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY','dev-secret-key')
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///soa_iso27001.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
#db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

def ensure_min_meses_revision_column():
    con = sqlite3.connect(app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", ""))
    cur = con.cursor()
    cur.execute("PRAGMA table_info(doc_tipos_documento)")
    cols = [r[1] for r in cur.fetchall()]

    if "min_meses_revision" not in cols:
        cur.execute("ALTER TABLE doc_tipos_documento ADD COLUMN min_meses_revision INTEGER DEFAULT 0")
        con.commit()

    cur.execute("UPDATE doc_tipos_documento SET min_meses_revision = 0 WHERE min_meses_revision IS NULL")
    con.commit()
    con.close()


# =========================
# Migración DB
# =========================

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sgsi.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy()
db.init_app(app)
migrate = Migrate(app, db)


# ========================================
# Carpeta de evidencias Partes Interesadas
# ========================================

UPLOAD_PARTES_INTERESADAS_DIR = os.path.join(BASE_DIR, 'uploads', 'partes_interesadas')
app.config['UPLOAD_PARTES_INTERESADAS_DIR'] = UPLOAD_PARTES_INTERESADAS_DIR
os.makedirs(app.config['UPLOAD_PARTES_INTERESADAS_DIR'], exist_ok=True)

# ======================================
# Carpeta de evidencias Vulnerabilidades
# ======================================

UPLOAD_VULNERABILIDADES_DIR = os.path.join(BASEDIR, "uploads", "vulnerabilidades")
os.makedirs(UPLOAD_VULNERABILIDADES_DIR, exist_ok=True)
app.config["UPLOAD_VULNERABILIDADES_DIR"] = UPLOAD_VULNERABILIDADES_DIR


# =========================================
# Carpeta de evidencias Matriz Competencias
# =========================================

UPLOAD_PLAN_REMEDIACION_COMP_DIR = os.path.join(
    BASEDIR, "uploads", "plan_remediacion_competencias"
)
os.makedirs(UPLOAD_PLAN_REMEDIACION_COMP_DIR, exist_ok=True)

app.config["UPLOAD_PLAN_REMEDIACION_COMP_DIR"] = UPLOAD_PLAN_REMEDIACION_COMP_DIR


# ============================================================
# AGRUPACIÓN POR CONTROL (Cláusulas 4–10) y Control ID
# + Anexo A: A.5.1, A.5.2, ...
# ============================================================
CONTROL_GROUPS = {
    "Contexto": ["4.1", "4.2", "4.3", "4.4"],
    "Liderazgo": ["5.1", "5.2", "5.3"],
    "Planificación": ["6.1", "6.2", "6.3"],
    "Soporte": ["7.1", "7.2", "7.3", "7.4", "7.5"],
    "Operación": ["8.1", "8.2", "8.3"],
    "Evaluación de desempeño": ["9.1", "9.2", "9.3"],
    "Mejora": ["10.1", "10.2"],
    "Anexo A": ["A."],  # macro; el control real será A.x.y
}

CONTROL_ORDER = [
    "4.1", "4.2", "4.3", "4.4",
    "5.1", "5.2", "5.3",
    "6.1", "6.2", "6.3",
    "7.1", "7.2", "7.3", "7.4", "7.5",
    "8.1", "8.2", "8.3",
    "9.1", "9.2", "9.3",
    "10.1", "10.2",
    # Anexo A es dinámico
]

# Hojas del instrumento (orden oficial)
CHAPTER_SHEETS = [
    "4 CONTEXTO",
    "5 LIDERAZGO",
    "6 PLANIFICACIÓN",
    "7 SOPORTE",
    "8 OPERACIÓN",
    "9 EVALUACIÓN DESEMPEÑO",
    "10 MEJORA",
    "ANEXO A",
]

# ============================================================
# TÍTULOS DE CONTROLES (Cláusulas 4–10) para UI/PDF
# ============================================================
CONTROL_TITLES = {
    "4.1": "CONOCIMIENTO DE LA ORGANIZACIÓN Y DE SU CONTEXTO",
    "4.2": "COMPRENSIÓN DE LAS NECESIDADES Y EXPECTATIVAS DE LAS PARTES INTERESADAS",
    "4.3": "DETERMINACIÓN DEL ALCANCE DEL SISTEMA DE GESTIÓN DE LA SEGURIDAD DE LA INFORMACIÓN",
    "4.4": "SISTEMA DE GESTIÓN DE LA SEGURIDAD DE LA INFORMACIÓN",

    "5.1": "LIDERAZGO Y COMPROMISO",
    "5.2": "POLÍTICA",
    "5.3": "ROLES, RESPONSABILIDADES Y AUTORIDADES EN LA ORGANIZACIÓN",

    "6.1": "ACCIONES PARA ABORDAR RIESGOS Y OPORTUNIDADES (6.1.1–6.1.3)",
    "6.2": "OBJETIVOS DE SEGURIDAD DE LA INFORMACIÓN Y PLANIFICACIÓN PARA ALCANZARLOS",
    "6.3": "PLANIFICACIÓN DE CAMBIOS",

    "7.1": "RECURSOS",
    "7.2": "COMPETENCIA",
    "7.3": "TOMA DE CONCIENCIA",
    "7.4": "COMUNICACIÓN",
    "7.5": "INFORMACIÓN DOCUMENTADA (7.5.1–7.5.3)",

    "8.1": "PLANIFICACIÓN Y CONTROL OPERACIONAL",
    "8.2": "VALORACIÓN DE RIESGOS DE LA SEGURIDAD DE LA INFORMACIÓN",
    "8.3": "TRATAMIENTO DE RIESGOS DE LA SEGURIDAD DE LA INFORMACIÓN",

    "9.1": "MONITOREO, MEDICIÓN, ANÁLISIS Y EVALUACIÓN",
    "9.2": "AUDITORÍA INTERNA (9.2.1–9.2.2)",
    "9.3": "REVISIÓN POR LA DIRECCIÓN (9.3.1–9.3.3)",

    "10.1": "MEJORA CONTINUA",
    "10.2": "NO CONFORMIDAD Y ACCIÓN CORRECTIVA",
}


def control_title(cid: str) -> str:
    cid = (cid or "").strip().upper()
    if cid.startswith("A."):
        return "Anexo A – Control " + cid
    return CONTROL_TITLES.get(cid, cid)


# ============================================================
# CONTROL_STRATEGY (para build_control_strategic_text)
# (Si no existe un cid, se usa fallback genérico)
# ============================================================
CONTROL_STRATEGY = {
    "4.1": {
        "intent": "Entender contexto interno/externo y factores que afectan el SGSI.",
        "must_have": [
            "Análisis de contexto interno y externo",
            "Registro de factores relevantes y actualización periódica",
            "Relación con riesgos/objetivos del SGSI",
        ],
        "evidence": [
            "Documento/acta de análisis de contexto (PESTEL/DOFA/otros)",
            "Matriz de factores y evaluación",
            "Revisiones y actualizaciones con fechas",
        ],
        "roles": ["Alta dirección", "Líder SGSI", "Dueños de proceso"],
        "cadence": "Revisión al menos anual y ante cambios relevantes.",
        "kpis": ["% factores revisados", "Cambios relevantes gestionados", "Hallazgos de auditoría sobre contexto"],
    },
    "4.2": {
        "intent": "Identificar y gestionar necesidades/expectativas de partes interesadas.",
        "must_have": ["Lista de partes interesadas", "Necesidades/expectativas", "Requisitos legales/contractuales"],
        "evidence": ["Matriz de partes interesadas", "Mapeo de requisitos", "Actualizaciones/versionado"],
        "roles": ["Líder SGSI", "Legal/Compliance", "Compras/Ventas"],
        "cadence": "Revisión semestral/anual y ante nuevos contratos o cambios regulatorios.",
        "kpis": ["% requisitos vigentes", "Incumplimientos contractuales", "Cambios regulatorios atendidos"],
    },
    "4.3": {
        "intent": "Definir el alcance del SGSI de forma clara y defendible.",
        "must_have": ["Declaración de alcance", "Límites y aplicabilidad", "Interfaces y dependencias"],
        "evidence": ["Documento de alcance aprobado", "Mapa de procesos/servicios en alcance", "Exclusiones justificadas"],
        "roles": ["Alta dirección", "Líder SGSI", "Dueños de proceso"],
        "cadence": "Revisión anual y ante cambios organizacionales o tecnológicos.",
        "kpis": ["Cambios de alcance controlados", "No conformidades por alcance", "Cobertura de activos/procesos"],
    },
    "4.4": {
        "intent": "Operar, mantener y mejorar el SGSI como sistema.",
        "must_have": ["Procesos del SGSI definidos", "Interacción de procesos", "Mejora continua"],
        "evidence": ["Mapa del SGSI", "Procedimientos/formatos", "Registros de operación y mejora"],
        "roles": ["Líder SGSI", "Dueños de proceso", "Auditor interno"],
        "cadence": "Gestión continua + revisión periódica en comité SGSI.",
        "kpis": ["Acciones cerradas", "Hallazgos recurrentes", "Cumplimiento de planes"],
    },

    "5.1": {"intent": "Demostrar liderazgo y compromiso con el SGSI.", "must_have": ["Patrocinio", "Recursos", "Dirección y soporte"]},
    "5.2": {"intent": "Definir y comunicar la política de seguridad de la información.", "must_have": ["Política aprobada", "Comunicación", "Revisión periódica"]},
    "5.3": {"intent": "Asignar roles, responsabilidades y autoridades para el SGSI.", "must_have": ["RACI/roles SGSI", "Responsables por control", "Autoridades definidas"]},

    "6.1": {"intent": "Gestionar riesgos y oportunidades del SGSI.", "must_have": ["Metodología de riesgos", "Criterios", "Evaluación y tratamiento"]},
    "6.2": {"intent": "Definir objetivos de SI medibles y planificar su logro.", "must_have": ["Objetivos SMART", "Planes", "Indicadores"]},
    "6.3": {"intent": "Planificar cambios del SGSI de forma controlada.", "must_have": ["Gestión de cambios", "Evaluación de impacto", "Aprobación"]},

    "7.1": {"intent": "Asegurar recursos para implementar y operar el SGSI.", "must_have": ["Presupuesto/recursos", "Herramientas", "Capacidad"]},
    "7.2": {"intent": "Asegurar competencias necesarias para SGSI.", "must_have": ["Matriz de competencias", "Planes de formación", "Evaluación"]},
    "7.3": {"intent": "Asegurar conciencia sobre seguridad de la información.", "must_have": ["Programa de awareness", "Evidencia de campañas", "Medición"]},
    "7.4": {"intent": "Gestionar comunicación interna/externa relevante al SGSI.", "must_have": ["Plan de comunicaciones", "Canales", "Registros"]},
    "7.5": {"intent": "Gestionar información documentada del SGSI.", "must_have": ["Control documental", "Versionado", "Accesos/retención"]},

    "8.1": {"intent": "Planificar y controlar operación del SGSI.", "must_have": ["Operación controlada", "Criterios operativos", "Evidencia"]},
    "8.2": {"intent": "Realizar valoraciones de riesgos de SI.", "must_have": ["Ejecución de valoraciones", "Registros", "Revisión"]},
    "8.3": {"intent": "Implementar tratamiento de riesgos.", "must_have": ["Plan de tratamiento", "Aceptación/transferencia", "Seguimiento"]},

    "9.1": {"intent": "Monitorear, medir, analizar y evaluar desempeño del SGSI.", "must_have": ["KPIs", "Medición", "Análisis y acciones"]},
    "9.2": {"intent": "Ejecutar auditorías internas del SGSI.", "must_have": ["Programa de auditoría", "Auditores", "Hallazgos/acciones"]},
    "9.3": {"intent": "Realizar revisión por la dirección del SGSI.", "must_have": ["Entradas/Salidas", "Decisiones", "Acciones"]},

    "10.1": {"intent": "Mejorar continuamente el SGSI.", "must_have": ["Backlog de mejora", "Priorización", "Ejecución"]},
    "10.2": {"intent": "Gestionar no conformidades y acciones correctivas.", "must_have": ["Registro NC", "Causa raíz", "Verificación de eficacia"]},
}



BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
UPLOAD_DIR = os.path.join(INSTANCE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

LOGOS_DIR = os.path.join(INSTANCE_DIR, "logos_empresas")
os.makedirs(LOGOS_DIR, exist_ok=True)

ALLOWED_LOGO_EXT = {"png", "jpg", "jpeg"}

def _allowed_logo(filename: str) -> bool:
    ext = (filename.rsplit(".", 1)[-1] or "").lower()
    return ext in ALLOWED_LOGO_EXT

def get_company_logo_path(company_name: str) -> str | None:
    """
    Retorna ruta absoluta del logo de la empresa si existe.
    """
    if not company_name:
        return None
    cfg = EmpresaConfig.query.filter_by(company_name=company_name).first()
    if not cfg or not cfg.logo_filename:
        return None
    p = os.path.join(LOGOS_DIR, cfg.logo_filename)
    return p if os.path.exists(p) else None

#app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(INSTANCE_DIR, "madurez_iso27001.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
#db = SQLAlchemy(app)

@event.listens_for(Engine, "connect")
def set_sqlite_pragmas(dbapi_connection, connection_record):
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")      # clave
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA busy_timeout=30000;")    # 30s
        cursor.close()
    except Exception:
        pass


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_DOCS_DIR = os.path.join(BASE_DIR, "uploads_docs")  # puedes cambiar el nombre
app.config['UPLOAD_DOCS_DIR'] = UPLOAD_DOCS_DIR
# ✅ Crear carpeta si no existe
os.makedirs(app.config['UPLOAD_DOCS_DIR'], exist_ok=True)

# =========================
# Carpeta evidencias Gestión de Accesos
# =========================
UPLOAD_GESTION_ACCESOS_DIR = os.path.join(app.root_path, 'static', 'uploads', 'gestion_accesos')
os.makedirs(UPLOAD_GESTION_ACCESOS_DIR, exist_ok=True)
app.config['UPLOAD_GESTION_ACCESOS_DIR'] = UPLOAD_GESTION_ACCESOS_DIR

#============================================
# Carpeta de evidencias de Partes Interesadas
#============================================

UPLOAD_PARTES_INTERESADAS_DIR = os.path.join(BASEDIR, "uploads", "partes_interesadas")
os.makedirs(UPLOAD_PARTES_INTERESADAS_DIR, exist_ok=True)
app.config["UPLOAD_PARTES_INTERESADAS_DIR"] = UPLOAD_PARTES_INTERESADAS_DIR

#============================================
# Carpeta de evidencias de Capacitaciones
#============================================

app.config['UPLOAD_PLAN_DISENO_DIR'] = os.path.join(app.root_path, 'uploads', 'plan_diseno')
os.makedirs(app.config['UPLOAD_PLAN_DISENO_DIR'], exist_ok=True)

#============================================
# Carpeta de evidencias de Competencias
#============================================

app.config['UPLOAD_PLAN_REMEDIACION_COMP_DIR'] = os.path.join(
    app.root_path, 'uploads', 'plan_remediacion_competencias'
)
os.makedirs(app.config['UPLOAD_PLAN_REMEDIACION_COMP_DIR'], exist_ok=True)

#============================================
# Carpeta de evidencias de Evaluación de Proveedores
#============================================

app.config['UPLOAD_PROVEEDORES_DIR'] = os.path.join(
    app.root_path, 'uploads', 'proveedores'
)
os.makedirs(app.config['UPLOAD_PROVEEDORES_DIR'], exist_ok=True)

# =========================
# Carpeta de evidencias - Vulnerabilidades
# =========================
UPLOAD_VULNERABILIDADES_DIR = os.path.join(app.root_path, 'static', 'uploads', 'vulnerabilidades')
os.makedirs(UPLOAD_VULNERABILIDADES_DIR, exist_ok=True)
app.config['UPLOAD_VULNERABILIDADES_DIR'] = UPLOAD_VULNERABILIDADES_DIR

# =========================
# Directorio de evidencias RFC
# =========================
UPLOAD_RFC_DIR = os.path.join(app.root_path, 'uploads_rfc')

# crear carpeta si no existe
os.makedirs(UPLOAD_RFC_DIR, exist_ok=True)

app.config['UPLOAD_RFC_DIR'] = UPLOAD_RFC_DIR

# ============================================================
# Utilidades FUNCIÓN DE CÁLCULO NIST
# ============================================================


def _norm_col(s: str) -> str:
    """normaliza encabezados: sin tildes, minúsculas, espacios->_, limpio"""
    s = str(s or "").strip()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = s.lower().replace(" ", "_").replace("-", "_")
    s = re.sub(r"[^a-z0-9_]+", "", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s

def _pick_col(df, candidates):
    cols_norm = {_norm_col(c): c for c in df.columns}
    for cand in candidates:
        key = _norm_col(cand)
        if key in cols_norm:
            return cols_norm[key]
    return None

def calcular_nist_desde_iso(iso_analysis_id):
    """
    Toma un AnalysisRun ISO (ISO 27001) y genera resultados NIST CSF 2.0
    usando el mapeo CSF→ISO del Excel.
    Retorna:
      {
        "detalle": { "GOVERN": {"GV.OC": 3.2, ...}, ... },
        "nivel_general": 3.1,
        "error": ""
      }
    """
    iso_run = AnalysisRun.query.get(iso_analysis_id)
    if not iso_run:
        return {"detalle": {}, "nivel_general": 0, "error": "Run ISO no encontrado."}

    # ✅ 1) ISO REAL: sale de control_results_json (no de resultados_json)
    try:
        control_results = json.loads(iso_run.control_results_json or "{}")
        if not isinstance(control_results, dict):
            control_results = {}
    except Exception as e:
        return {"detalle": {}, "nivel_general": 0, "error": f"No se pudo leer control_results_json: {e}"}

    # Construye score ISO por id de control/cláusula:
    # - Cláusulas: "4.1", "5.2", ...
    # - Anexo A: "A.5.16", ...
    # Convertimos % (0..100) a escala 0..5 (NIST-like)
    iso_score_0_5 = {}
    for cid, v in control_results.items():
        try:
            pct = float((v or {}).get("pct", 0) or 0)
        except Exception:
            pct = 0.0
        key = (str(cid) or "").strip().upper()
        iso_score_0_5[key] = round(pct / 20.0, 2)  # 100% => 5.0

    iso_pct_0_100 = {}
    for cid, v in control_results.items():
        try:
            pct = float((v or {}).get("pct", 0) or 0)
        except Exception:
            pct = 0.0
        key = (str(cid) or "").strip().upper()
        iso_pct_0_100[key] = round(pct, 2)

    # ✅ 2) Carga Excel de mapeo
    mapping_path = os.path.join(BASE_DIR, "static/templates/CSF20_to_ISO27001_Mapping_Categorias.xlsx")
    if not os.path.exists(mapping_path):
        return {"detalle": {}, "nivel_general": 0, "error": f"No se encontró el Excel de mapeo en: {mapping_path}"}

    try:
        df_map = pd.read_excel(mapping_path)
    except Exception as e:
        return {"detalle": {}, "nivel_general": 0, "error": f"No se pudo leer el Excel de mapeo: {e}"}

    cols = list(df_map.columns)

    def pick_col(*candidates):
        for c in candidates:
            if c in cols:
                return c
        return None

    col_func = pick_col("NIST_Function", "Función (CSF 2.0)")
    col_cat  = pick_col("NIST_Category", "Código de Categoría")
    col_iso_clause = pick_col("ISO_Clause", "ISO/IEC 27001:2022 (Cláusulas)")
    col_iso_anexo  = pick_col("ISO/IEC 27001:2022 (Anexo A - controles)")
    col_w = pick_col("Peso", "Weight", "PESO")

    required = [col_func, col_cat, col_iso_clause, col_iso_anexo]
    if any(x is None for x in required):
        return {
            "detalle": {},
            "nivel_general": 0,
            "error": f"Columnas requeridas no encontradas en el mapeo. Encontradas: {cols}"
        }

    def split_refs(x):
        s = ("" if pd.isna(x) else str(x)).strip()
        if not s:
            return []
        parts = re.split(r"[,\n;/]+", s)
        return [p.strip() for p in parts if p.strip()]

    # Normaliza tokens para poder matchear tus keys ("4.1", "A.5.16", etc.)
    def norm_iso_token(t):
        tt = (t or "").strip().upper()

        # si viene con texto adicional, extrae primer match válido:
        m = re.search(r"(A\.\d+\.\d+|\d+\.\d+)", tt)
        if m:
            return m.group(1)

        return tt

    # ✅ 3) Calcula NIST por Función + Categoría (ponderado si hay Peso)
    acc = {}  # func -> cat -> {"sum":..., "w":..., "items_map":{ref: {...}}}
    overall_sum, overall_w = 0.0, 0.0

    def ref_tipo(ref: str) -> str:
        r = (ref or "").strip().upper()
        return "Annex A" if r.startswith("A.") else "ISO Clause"

    for _, row in df_map.iterrows():
        f = ("" if pd.isna(row[col_func]) else str(row[col_func])).strip()
        c = ("" if pd.isna(row[col_cat]) else str(row[col_cat])).strip()
        if not f or not c:
            continue

        refs = []
        refs += split_refs(row[col_iso_clause])
        refs += split_refs(row[col_iso_anexo])

        refs = [norm_iso_token(r) for r in refs]
        refs = [r for r in refs if r]

        # Tomamos SOLO refs que existan en el run ISO
        matched = [r for r in refs if r in iso_score_0_5]

        if not matched:
            continue

        # Score NIST-like (0..5) para promediar la categoría
        scores_0_5 = [iso_score_0_5[r] for r in matched]
        row_score = sum(scores_0_5) / len(scores_0_5)

        # Peso opcional
        w = 1.0
        if col_w:
            try:
                w = float(row[col_w] or 1.0)
                if w <= 0:
                    w = 1.0
            except Exception:
                w = 1.0

        fu = f.strip()
        cu = c.strip()

        acc.setdefault(fu, {}).setdefault(cu, {"sum": 0.0, "w": 0.0, "items_map": {}})

        # Acumula promedio ponderado para score final de categoría
        acc[fu][cu]["sum"] += row_score * w
        acc[fu][cu]["w"] += w

        overall_sum += row_score * w
        overall_w += w

        # ✅ Guarda detalle por cada ref ISO asociada a esta categoría
        for r in matched:
            pct = float(iso_pct_0_100.get(r, 0) or 0)
            item = {
                "ref": r,
                "tipo": ref_tipo(r),
                "pct": round(pct, 2),
                "gap": round(100.0 - pct, 2),
            }

            # Si un ref aparece varias veces, nos quedamos con el PEOR (menor pct / mayor gap)
            prev = acc[fu][cu]["items_map"].get(r)
            if (prev is None) or (item["pct"] < prev["pct"]):
                acc[fu][cu]["items_map"][r] = item

    # ✅ Construye salida final (con items/faltantes)
    detalle = {}
    for fu, cats in acc.items():
        detalle[fu] = {}
        for cu, d in cats.items():
            score = round(d["sum"] / d["w"], 2) if d["w"] else 0.0
            items = list(d["items_map"].values())
            items.sort(key=lambda x: (x.get("gap", 0)), reverse=True)

            faltantes = [x for x in items if float(x.get("pct", 0) or 0) < 100.0]

            refs_esp = sorted(list(d.get("refs_esperadas", set())))
            refs_mat = set([x["ref"] for x in items])
            no_evaluadas = [{"ref": r, "tipo": ref_tipo(r), "pct": None, "gap": None}
                            for r in refs_esp if r not in refs_mat]

            detalle[fu][cu] = {
                "score": score,                  # score solo si hubo w>0 (si no, queda 0.0)
                "items": items,
                "faltantes": faltantes,
                "no_evaluadas": no_evaluadas,    # <-- NUEVO
            }

    nivel_general = round(overall_sum / overall_w, 2) if overall_w else 0.0

    if not detalle:
        return {
            "detalle": {},
            "nivel_general": 0,
            "error": "No se logró mapear nada desde ISO. Revisa que control_results_json tenga claves como '4.1' y 'A.5.16' y que el Excel tenga esas referencias."
        }

    return {"detalle": detalle, "nivel_general": nivel_general, "error": ""}


#---------------------------------------------------------------------------------------------------------------
#                                                  Modelos
#---------------------------------------------------------------------------------------------------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password_hash = db.Column(db.String(200))
    role = db.Column(db.String(20), default="user")
    otp_secret = db.Column(db.String(32))
    email = db.Column(db.String(255), unique=True, nullable=True)
    photo_filename = db.Column(db.String(255), nullable=True)

    def set_password(self, password):
        self.password_hash = ssha.hash(password)

    def check_password(self, password):
        return ssha.verify(password, self.password_hash)

class Control(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nr = db.Column(db.String(10), index=True)
    chapter = db.Column(db.String(100))
    topic = db.Column(db.String(300))
    control_text = db.Column(db.Text)
    applicable = db.Column(db.String(10))
    justification = db.Column(db.Text)
    motivation = db.Column(db.Text)
    implemented = db.Column(db.String(10))


class MetricConfigRiesgos(db.Model):
    __tablename__ = "metric_config_riesgos"
    id = db.Column(db.Integer, primary_key=True)

    # Campo texto (apetito residual definido)
    apetito_residual_definido = db.Column(db.String(255), nullable=False)

    # Tendencia en el tiempo
    # Valores permitidos: mensual, trimestral, cuatrimestral, semestral, anual
    tendencia_tiempo = db.Column(db.String(20), nullable=False, default="mensual")
    tendencia_ai_text = db.Column(db.Text, nullable=True)
    tendencia_ai_updated_at = db.Column(db.DateTime, nullable=True)

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UserPermission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    module_name = db.Column(db.String(100))
    has_access = db.Column(db.Boolean, default=False)

class DashboardPreference(db.Model):
    """Configuración personal de los elementos visibles en el Centro de Control."""
    __tablename__ = "dashboard_preferences"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    widget_keys_json = db.Column(db.Text, nullable=False, default="[]")
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )



class DashboardCustomWidget(db.Model):
    """Visualización creada por un usuario a partir de una fuente segura de GRAC."""
    __tablename__ = "dashboard_custom_widgets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False,
        index=True,
    )
    title = db.Column(db.String(140), nullable=False)
    subtitle = db.Column(db.String(220), nullable=True)
    source_key = db.Column(db.String(90), nullable=False, index=True)
    # Compatibilidad: kpi / gauge (versiones anteriores).
    # Nuevos valores: radar / gauge / donut / line / pie /
    # bar_vertical / bar_horizontal.
    widget_type = db.Column(db.String(20), nullable=False, default="gauge")
    icon = db.Column(db.String(80), nullable=False, default="bi-speedometer2")
    color = db.Column(db.String(20), nullable=False, default="blue")
    target_value = db.Column(db.Float, nullable=True)
    suffix = db.Column(db.String(20), nullable=True)
    decimals = db.Column(db.Integer, nullable=False, default=2)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

class OpenRouterKey(db.Model):
    __tablename__ = "openrouter_keys"
    id = db.Column(db.Integer, primary_key=True)
    api_key_enc = db.Column(db.Text, nullable=True)  # key cifrada (Fernet)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AreaEmpresa(db.Model):
    __tablename__ = 'areas_empresa'
    id = db.Column(db.Integer, primary_key=True)
    area = db.Column(db.String(200), nullable=False)  # Área
    responsable_nombre = db.Column(db.String(200), nullable=False)  # Nombre Responsable del área
    responsable_cargo = db.Column(db.String(200), nullable=False)   # Cargo (del responsable del área)
    division = db.Column(db.String(200), nullable=True)            # División
    division_encargado = db.Column(db.String(200), nullable=True)  # Nombre del encargado de la División
    division_cargo = db.Column(db.String(200), nullable=True)      # Cargo (del encargado de la división)

class DivisionEmpresa(db.Model):
    __tablename__ = 'divisiones_empresa'

    id = db.Column(db.Integer, primary_key=True)

    # Relación con Área
    area_id = db.Column(
        db.Integer,
        db.ForeignKey('areas_empresa.id', ondelete='CASCADE'),
        nullable=False
    )

    nombre_division = db.Column(db.String(200), nullable=False)        # Nombre de la división
    encargado_nombre = db.Column(db.String(200), nullable=False)       # Nombre encargado de la división
    encargado_cargo = db.Column(db.String(200), nullable=False)        # Cargo (Encargado de la división)

    area = db.relationship(
        'AreaEmpresa',
        backref=db.backref('divisiones', lazy=True)
    )



class ValoracionConfidencialidad(db.Model):
    __tablename__ = 'valoracion_confidencialidad'
    id = db.Column(db.Integer, primary_key=True)
    nivel_confidencialidad = db.Column(db.String(200), nullable=False)  # texto (Alto/Medio/Bajo o lo que uses)
    descripcion = db.Column(db.Text, nullable=False)                     # texto
    impacto = db.Column(db.String(200), nullable=False)                  # texto
    clasificacion = db.Column(db.String(200), nullable=False)            # texto
    nivel_num = db.Column(db.Integer, nullable=False, default=3)         # NUEVO: 1..5

class ValoracionIntegridad(db.Model):
    __tablename__ = 'valoracion_integridad'
    id = db.Column(db.Integer, primary_key=True)
    # si tu modelo tiene estos nombres, déjalos:
    nivel = db.Column(db.String(200), nullable=False)          # texto
    descripcion = db.Column(db.Text, nullable=False)           # texto
    impacto = db.Column(db.String(200), nullable=False)        # texto
    clasificacion = db.Column(db.String(200), nullable=False)  # texto
    # NUEVO:
    nivel_num = db.Column(db.Integer, nullable=False, default=3)

class ValoracionDisponibilidad(db.Model):
    __tablename__ = 'valoracion_disponibilidad'
    id = db.Column(db.Integer, primary_key=True)
    nivel = db.Column(db.String(200), nullable=False)          # texto
    descripcion = db.Column(db.Text, nullable=False)           # texto
    impacto = db.Column(db.String(200), nullable=False)        # texto
    clasificacion = db.Column(db.String(200), nullable=False)  # texto
    # NUEVO:
    nivel_num = db.Column(db.Integer, nullable=False, default=3)

class ValoracionCriticidadActivo(db.Model):
    __tablename__ = 'valoracion_criticidad_activo'
    id = db.Column(db.Integer, primary_key=True)
    nivel_num = db.Column(db.Integer, nullable=False, default=3)      # 1..5 (configurable)
    nivel_texto = db.Column(db.String(200), nullable=False)           # texto libre

class InventarioInformacion(db.Model):
    __tablename__ = 'inventario_informacion'
    id = db.Column(db.Integer, primary_key=True)

    area_id = db.Column(db.Integer, db.ForeignKey('areas_empresa.id', ondelete='SET NULL'), nullable=True)
    area = db.relationship('AreaEmpresa', backref='inventarios_info')

    division = db.Column(db.String(200), nullable=True)
    area = db.relationship('AreaEmpresa', backref=db.backref('inventarios_informacion', lazy=True))

    division = db.Column(db.String(120), nullable=True, index=True)
    area = db.relationship('AreaEmpresa', lazy='joined')

    #area = db.Column(db.String(200), nullable=False)
    proceso = db.Column(db.String(200), nullable=False)
    nombre_activo = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)

    formato = db.Column(db.String(20), nullable=False)           # "Digital" / "Físico"
    ubicacion_digital = db.Column(db.String(255))                # texto
    accesos_autorizados = db.Column(db.String(255))              # texto

    lectura = db.Column(db.String(2), nullable=False)            # "Sí"/"No"
    escritura = db.Column(db.String(2), nullable=False)          # "Sí"/"No"
    eliminacion = db.Column(db.String(2), nullable=False)        # "Sí"/"No"

    propietario = db.Column(db.String(200), nullable=False)

    c_nivel = db.Column(db.Integer, nullable=False)              # 1..5 (desde valor_confidencialidad)
    i_nivel = db.Column(db.Integer, nullable=False)              # 1..5
    d_nivel = db.Column(db.Integer, nullable=False)              # 1..5
    valor_activo = db.Column(db.Integer, nullable=False)         # ROUND(avg)

    criticidad_num = db.Column(db.Integer, nullable=False)       # 1..5 (desde valor_criticidad_activo)
    criticidad_texto = db.Column(db.String(200), nullable=False) # texto tomado de la tabla

    etiqueta_conf_num = db.Column(db.Integer, nullable=False)    # igual a valor_activo
    etiqueta_conf_texto = db.Column(db.String(200), nullable=False) # clasif. de confidencialidad para ese nivel

    info_personal = db.Column(db.String(2), nullable=False)      # "Sí"/"No"
    info_regulada = db.Column(db.String(2), nullable=False)      # "Sí"/"No"
    info_sensible = db.Column(db.String(2), nullable=False)      # "Sí"/"No"
    info_sensible_clientes = db.Column(db.String(2), nullable=False) # "Sí"/"No"

    observaciones = db.Column(db.Text)

class InventarioSoftware(db.Model):
    __tablename__ = 'inventario_software'
    id = db.Column(db.Integer, primary_key=True)

    # ... ya existentes ...
    area = db.Column(db.String(200), nullable=False)
    nombre_activo = db.Column(db.String(200), nullable=False)
    administrador = db.Column(db.String(200), nullable=False)
    dueno_tecnico = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)

    # NUEVO
    proceso = db.Column(db.String(200), nullable=False)  # <— NUEVO campo
    division = db.Column(db.String(120))

    # Medio / ubicación
    medio = db.Column(db.String(100))                    # 'Aplicación Web', etc.
    ubicacion_tipo = db.Column(db.String(100))           # 'Área', 'Servidor', 'Dominio/URL'
    ubicacion_nombre = db.Column(db.String(200))         # nombre de la ubicación

    # CAMBIO: antes era Sí/No; ahora texto con áreas/divisiones
    accesos_autorizados = db.Column(db.String(300))      # <— TEXTO “Áreas o Divisiones”

    propietario = db.Column(db.String(200), nullable=False)

    # Niveles
    c_nivel = db.Column(db.Integer)
    i_nivel = db.Column(db.Integer)
    d_nivel = db.Column(db.Integer)
    valor_activo = db.Column(db.Integer)

    # Etiquetado y criticidad
    etiqueta_conf_num = db.Column(db.Integer)
    etiqueta_conf_texto = db.Column(db.String(200))
    criticidad_num = db.Column(db.Integer)
    criticidad_texto = db.Column(db.String(200))

    # NUEVOS: desplegables Sí/No
    info_personal = db.Column(db.String(2), default='No')            # 'Sí'/'No'
    info_regulada = db.Column(db.String(2), default='No')            # 'Sí'/'No'
    info_sensible_compania = db.Column(db.String(2), default='No')   # 'Sí'/'No'
    info_sensible_clientes = db.Column(db.String(2), default='No')   # 'Sí'/'No'

    observaciones = db.Column(db.Text)
    
class InventarioFisico(db.Model):
    __tablename__ = "inventario_fisico"  # si ya lo tienes, déjalo igual

    id = db.Column(db.Integer, primary_key=True)

    # 🔧 CLAVE FORÁNEA CORRECTA
    area_id = db.Column(
        db.Integer,
        db.ForeignKey("areas_empresa.id"),     # <-- OJO: coincide con __tablename__ arriba
        nullable=False
    )

    # 🔗 RELACIÓN
    area = db.relationship(
        "AreaEmpresa",
        backref=db.backref("inventarios_fisicos", lazy="dynamic"),
        foreign_keys=[area_id],
        lazy="joined"
    )
    
    division = db.Column(db.String(120))

    # Nuevos campos solicitados
    asignado_a = db.Column(db.String(120))
    cargo = db.Column(db.String(120))
    ciudad = db.Column(db.String(120))
    clase_activo = db.Column(db.String(50))                # Laptop, Servidor, Equipo de comunicación, Desktop
    marca = db.Column(db.String(120))
    mouse = db.Column(db.String(2))                        # 'Sí' / 'No'
    teclado = db.Column(db.String(2))                      # 'Sí' / 'No'
    base_portatil = db.Column(db.String(2))                # 'Sí' / 'No'
    monitor = db.Column(db.String(2))                      # 'Sí' / 'No'
    numero_serial = db.Column(db.String(120))
    nombre_dispositivo = db.Column(db.String(120))
    procesador = db.Column(db.String(120))
    ram_instalada = db.Column(db.String(120))
    id_dispositivo = db.Column(db.String(120))
    id_producto = db.Column(db.String(120))
    tipo_sistema = db.Column(db.String(120))
    edicion_so = db.Column(db.String(120))
    version_so = db.Column(db.String(120))
    pais = db.Column(db.String(120))
    fecha_compra = db.Column(db.Date)
    fecha_asignacion = db.Column(db.Date)

    # C / I / D y derivados
    c_nivel = db.Column(db.Integer)
    i_nivel = db.Column(db.Integer)
    d_nivel = db.Column(db.Integer)
    valor_activo = db.Column(db.Integer)                   # ROUND((C+I+D)/3)
    criticidad_num = db.Column(db.Integer)
    criticidad_texto = db.Column(db.String(120))
    etiqueta_conf_num = db.Column(db.Integer)
    etiqueta_conf_texto = db.Column(db.String(120))

    # Flags sí/no
    info_personal = db.Column(db.String(2))                # 'Sí' / 'No'
    info_regulada = db.Column(db.String(2))                # 'Sí' / 'No'
    info_sensible = db.Column(db.String(2))                # 'Sí' / 'No'
    info_sensible_clientes = db.Column(db.String(2))       # 'Sí' / 'No'

    observaciones = db.Column(db.Text)


class DuenoInformacion(db.Model):
    __tablename__ = 'duenos_informacion'
    id = db.Column(db.Integer, primary_key=True)

    # Relación con el módulo de Áreas
    area_id = db.Column(
        db.Integer,
        db.ForeignKey('areas_empresa.id', ondelete='SET NULL'),
        nullable=True
    )

    area = db.relationship('AreaEmpresa', backref=db.backref('duenos_info', lazy=True))

    # Campos de negocio
    dueno_nombre = db.Column(db.String(200), nullable=False)
    dueno_cargo  = db.Column(db.String(200), nullable=False)
    custodio_nombre = db.Column(db.String(200), nullable=False)
    custodio_cargo  = db.Column(db.String(200), nullable=False)

    # Lista de archivos PDF (separados por coma, igual que SoA)
    acuerdos_pdf = db.Column(db.Text)  # "owner_3_Acuerdo1.pdf,owner_3_Acuerdo2.pdf"


class PlanCFRegistro(db.Model):
    __tablename__ = 'plan_cf_registros'
    id = db.Column(db.Integer, primary_key=True)

    total_empleados_contratados = db.Column(db.Integer)     # numérico
    tipo_capacitacion = db.Column(db.String(80))            # "Inducción,Reinducción" (multi-select)

    # Contenido de la capacitación
    nombre_capacitacion   = db.Column(db.String(255))
    objetivo_capacitacion = db.Column(db.Text)
    temario               = db.Column(db.Text)

    # Cronograma
    fecha_programada  = db.Column(db.String(10))   # 'YYYY-MM-DD'
    fecha_realizacion = db.Column(db.String(10))   # 'YYYY-MM-DD'
    cumplimiento_pct  = db.Column(db.Integer)      # % Cumplimiento Programa

    # Participantes / Entrenador
    area_participantes = db.Column(db.String(255), default='')
    division_participantes = db.Column(db.String(255), default='')
    competencia_entrenador   = db.Column(db.String(10))     # 'interno' / 'externo'
    quien_realizo            = db.Column(db.String(255))    # texto
    horas_duracion           = db.Column(db.Integer)        # número de horas

    # Indicadores de realización
    indicador_realizacion = db.Column(db.Integer)  # 100 o 0

    # Cobertura
    num_asistentes   = db.Column(db.Integer)
    num_programados  = db.Column(db.Integer)
    cobertura_pct    = db.Column(db.Integer)       # % Cobertura

    # Eficacia
    num_evaluados    = db.Column(db.Integer)
    num_eficaces     = db.Column(db.Integer)
    eficaces_pct     = db.Column(db.Integer)       # % de evaluaciones eficaces

    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def recalcular_indicadores(self):
        """Calcula %Cobertura y %Eficaces si hay base."""
        try:
            if (self.num_programados or 0) > 0:
                self.cobertura_pct = round((self.num_asistentes or 0) * 100 / self.num_programados)
            else:
                self.cobertura_pct = 0
        except Exception:
            self.cobertura_pct = 0

        try:
            if (self.num_evaluados or 0) > 0:
                self.eficaces_pct = round((self.num_eficaces or 0) * 100 / self.num_evaluados)
            else:
                self.eficaces_pct = 0
        except Exception:
            self.eficaces_pct = 0

class PlanDisenoRegistro(db.Model):
    __tablename__ = 'plan_diseno_registros'

    id = db.Column(db.Integer, primary_key=True)

    tema_capacitacion = db.Column(db.String(255))   # TEMA DE LA CAPACITACIÓN
    descripcion       = db.Column(db.Text)          # DESCRIPCIÓN
    horas             = db.Column(db.Integer)       # # HORAS
    dirigida_area = db.Column(db.String(200), nullable=True)
    dirigida_division = db.Column(db.String(200), nullable=True)
    fecha_programada  = db.Column(db.String(10))    # FECHA PROGRAMADA (o Date si ya usas Date)
    fecha_ejecucion   = db.Column(db.String(10))    # FECHA EJECUCIÓN
    responsable       = db.Column(db.String(255))   # RESPONSABLE
    metodologia       = db.Column(db.Text)          # METODOLOGÍA MEDICIÓN, EVALUACIÓN Y EFICACIA
    evidencia         = db.Column(db.Text)          # EVIDENCIA (texto / referencia)
    observaciones     = db.Column(db.Text)          # OBSERVACIONES

    evidencias = db.relationship(
        'PlanDisenoEvidencia',
        back_populates='registro',
        cascade='all, delete-orphan'
    )

class PlanDisenoEvidencia(db.Model):
    __tablename__ = 'plan_diseno_evidencias'

    id = db.Column(db.Integer, primary_key=True)

    plan_id = db.Column(
        db.Integer,
        db.ForeignKey('plan_diseno_registros.id'),
        nullable=False
    )

    filename      = db.Column(db.String(255), nullable=False)  # nombre guardado
    original_name = db.Column(db.String(255), nullable=False)  # nombre original
    mime          = db.Column(db.String(100), default='application/pdf')
    size          = db.Column(db.Integer)  # bytes

    registro = db.relationship('PlanDisenoRegistro', back_populates='evidencias')


class MejoraPlanRegistro(db.Model):
    __tablename__ = 'mejora_planes'

    id = db.Column(db.Integer, primary_key=True)

    # PLANEAR
    fecha = db.Column(db.String(10))                 # Fecha (planear)
    descripcion_incumplimiento = db.Column(db.Text)  # Descripción o incumplimiento
    causa = db.Column(db.Text)                       # Causa
    tipo_accion = db.Column(db.String(20))           # "Correctiva" / "Mejora"
    plan_accion = db.Column(db.Text)                 # Plan de acción

    # HACER
    termino_ejecucion = db.Column(db.String(20))     # Corto / Mediano / Largo plazo
    fecha_ejecucion_propuesta = db.Column(db.String(10))  # Fecha ejecución propuesta
    responsable = db.Column(db.String(255))          # Responsable
    estado_actividad = db.Column(db.String(20))      # Abierto / Cerrado

    # VERIFICAR
    fecha_cierre = db.Column(db.String(10))          # Fecha de cierre
    eficacia = db.Column(db.String(10))              # "Sí" / "No"
    observacion_eficacia = db.Column(db.Text)        # Observación de eficacia

    # Evidencias (archivos)
    evidencias = db.relationship(
        'MejoraPlanEvidencia',
        back_populates='plan',
        cascade='all, delete-orphan'
    )
    
class MejoraPlanEvidencia(db.Model):
    __tablename__ = 'mejora_evidencias'

    id = db.Column(db.Integer, primary_key=True)

    plan_id = db.Column(
        db.Integer,
        db.ForeignKey('mejora_planes.id'),
        nullable=False
    )

    filename      = db.Column(db.String(255), nullable=False)  # nombre guardado
    original_name = db.Column(db.String(255), nullable=False)  # nombre original
    mime          = db.Column(db.String(100), default='application/pdf')
    size          = db.Column(db.Integer)  # bytes

    plan = db.relationship('MejoraPlanRegistro', back_populates='evidencias')

class DocTipoDocumento(db.Model):
    __tablename__ = 'doc_tipos_documento'

    id          = db.Column(db.Integer, primary_key=True)
    nombre      = db.Column(db.String(150), nullable=False)   # Tipo de documento
    descripcion = db.Column(db.Text)                          # Descripción
    min_meses_revision = db.Column(db.Integer, default=0)


class DocMaestroDocumento(db.Model):
    __tablename__ = 'doc_maestro_documentos'

    id         = db.Column(db.Integer, primary_key=True)
    item       = db.Column(db.Integer, nullable=False)  # consecutivo

    # Relación con tipo de documento
    tipo_id    = db.Column(db.Integer, db.ForeignKey('doc_tipos_documento.id'), nullable=False)
    tipo       = db.relationship('DocTipoDocumento', backref='documentos')

    codigo     = db.Column(db.String(100))   # Código
    inicial    = db.Column(db.String(20))    # Inicial
    tipo_texto = db.Column(db.String(50))    # Campo "Tipo" (texto libre)

    num1       = db.Column(db.Integer)       # #1
    num2       = db.Column(db.Integer)       # #2
    num3       = db.Column(db.Integer)       # #3

    nombre_documento = db.Column(db.String(255))  # Nombre del documento

    # Archivo físico
    filename      = db.Column(db.String(255))   # nombre guardado
    original_name = db.Column(db.String(255))   # nombre original
    mime          = db.Column(db.String(100))   # mimetype
    size          = db.Column(db.Integer)       # bytes

    version    = db.Column(db.Integer)          # Versión (número)
    fecha_creacion = db.Column(db.String(10))   # YYYY-MM-DD (si quieres luego la pasas a Date)
    estado     = db.Column(db.String(30))       # Vigente / Versión obsoleta

    control_cambios = db.Column(db.Text)
    observaciones   = db.Column(db.Text)

    fecha_ultima_revision = db.Column(db.String(10))

    tipo = db.relationship('DocTipoDocumento', backref='documentos')

    evidencias = db.relationship(
        'DocEvidencia',
        back_populates='documento',
        cascade='all, delete-orphan'
    )

class DocEvidencia(db.Model):
    __tablename__ = 'docs_evidencias'

    id = db.Column(db.Integer, primary_key=True)

    doc_id = db.Column(
        db.Integer,
        db.ForeignKey('doc_maestro_documentos.id'),  # 👈 IGUAL al __tablename__
        nullable=False
    )

    filename      = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    mime          = db.Column(db.String(100), default='application/pdf')
    size          = db.Column(db.Integer)

    documento = db.relationship('DocMaestroDocumento', back_populates='evidencias')


class MatrizComunicacionRegistro(db.Model):
    __tablename__ = 'matriz_comunicaciones'

    id = db.Column(db.Integer, primary_key=True)

    # Campos del formato
    proceso           = db.Column(db.String(255), nullable=False)   # PROCESO
    informacion       = db.Column(db.Text, nullable=False)          # ¿Qué comunica?
    remitente         = db.Column(db.String(255), nullable=False)   # ¿Quién comunica?
    medio             = db.Column(db.String(255), nullable=False)   # ¿Cómo comunica?
    frecuencia        = db.Column(db.String(255), nullable=False)   # ¿Cuándo comunica?
    destinatario      = db.Column(db.String(255), nullable=False)   # ¿A quién comunica?
    tipo_comunicacion = db.Column(db.String(20),  nullable=False)   # Interna / Externa

class RequisitoLegal(db.Model):
    __tablename__ = 'requisitos_legales'

    id = db.Column(db.Integer, primary_key=True)  # interno
    # ID alfanumérico que verás en la matriz
    codigo = db.Column(db.String(50), nullable=False)

    requisito = db.Column(db.String(300), nullable=False)             # Requisito Legal / Contractual
    tipo_ley = db.Column(db.String(200), nullable=False)              # Tipo de Ley / Norma
    entidad_emisora = db.Column(db.String(200), nullable=False)       # Entidad Emisora
    descripcion_alcance = db.Column(db.Text, nullable=False)          # Descripción / Alcance
    responsable = db.Column(db.String(200), nullable=False)           # Responsable
    evidencia_cumplimiento = db.Column(db.Text, nullable=True)        # Evidencia de Cumplimiento
    estado = db.Column(db.String(100), nullable=False)                # Estado
    fecha_revision = db.Column(db.Date, nullable=True)                # Fecha de Revisión

class EmpresaConfig(db.Model):
    __tablename__ = "empresa_config"
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(255), unique=True, nullable=False, index=True)

    logo_filename = db.Column(db.String(255), nullable=True)  # ej: "logo_ACME.png"
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class VulnerabilidadRegistro(db.Model):
    __tablename__ = "vulnerabilidades_registro"

    id = db.Column(db.Integer, primary_key=True)

    # Campos de la matriz
    clasificacion = db.Column(db.String(50), nullable=True)
    codigo = db.Column(db.String(50), nullable=False)              # ID alfanumérico
    activo = db.Column(db.String(200), nullable=False)
    descripcion_vulnerabilidad = db.Column(db.Text, nullable=False)
    cve = db.Column(db.String(50), nullable=True)
    cvss = db.Column(db.String(20), nullable=True)
    fecha_identificacion = db.Column(db.Date, nullable=True)
    fecha_cierre = db.Column(db.Date, nullable=True)
    estado = db.Column(db.String(20), nullable=False)              # 'Abierto'/'Cerrado'
    responsable = db.Column(db.String(200), nullable=False)
    riesgo_residual = db.Column(db.Text, nullable=True)

    evidencias = db.relationship(
        "VulnerabilidadEvidencia",
        backref="vulnerabilidad",
        cascade="all, delete-orphan",
        lazy="selectin"
    )


class VulnerabilidadEvidencia(db.Model):
    __tablename__ = "vulnerabilidades_evidencias"

    id = db.Column(db.Integer, primary_key=True)
    vulnerabilidad_id = db.Column(
        db.Integer,
        db.ForeignKey("vulnerabilidades_registro.id", ondelete="CASCADE"),
        nullable=False
    )
    filename = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    mime = db.Column(db.String(100), nullable=False)
    size = db.Column(db.Integer, nullable=False)

class PlanRemediacion(db.Model):
    __tablename__ = 'planes_remediacion'

    id = db.Column(db.Integer, primary_key=True)

    # Relación con la vulnerabilidad registrada
    vulnerabilidad_id = db.Column(
        db.Integer,
        db.ForeignKey('vulnerabilidades_registro.id'),  # <-- ajusta si tu tabla tiene otro nombre
        nullable=False
    )

    accion_correctiva   = db.Column(db.Text, nullable=False)
    responsable         = db.Column(db.String(200), nullable=False)
    prioridad           = db.Column(db.String(20), nullable=False)   # Alta / Media / Baja
    fecha_objetivo      = db.Column(db.Date, nullable=True)
    fecha_remediacion   = db.Column(db.Date, nullable=True)
    recursos_necesarios = db.Column(db.Text, nullable=True)
    estado              = db.Column(db.String(20), nullable=False)   # Abierto / Cerrado
    jira_issue_key = db.Column(db.String(50), nullable=True)
    jira_issue_url = db.Column(db.String(500), nullable=True)
    jira_status = db.Column(db.String(100), nullable=True)
    jira_account_id = db.Column(db.String(255), nullable=True)
    jira_assignee_name = db.Column(db.String(255), nullable=True)
    jira_synced_at = db.Column(db.DateTime, nullable=True)

    vulnerabilidad = db.relationship(
        'VulnerabilidadRegistro',    # <-- ajusta al nombre real de tu modelo de vulnerabilidades
        backref=db.backref('planes_remediacion', lazy=True)
    )

class JiraConfig(db.Model):
    __tablename__ = 'jira_config'

    id = db.Column(db.Integer, primary_key=True)
    enabled = db.Column(db.Boolean, default=False, nullable=False)

    base_url = db.Column(db.String(255), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    project_key = db.Column(db.String(50), nullable=True)
    issue_type = db.Column(db.String(100), nullable=True, default="Task")

    api_token_enc = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PlanRemediacionCompetenciaRegistro(db.Model):
    __tablename__ = "plan_remediacion_competencias"

    id = db.Column(db.Integer, primary_key=True)

    rol_cargo = db.Column(db.String(200), nullable=False)
    responsable = db.Column(db.String(200), nullable=False)
    competencias_requeridas = db.Column(db.Text, nullable=False)
    brechas_detectadas = db.Column(db.Text, nullable=True)
    plan_capacitacion = db.Column(db.Text, nullable=True)
    fecha_cumplimiento = db.Column(db.Date, nullable=True)

    evidencias = db.relationship(
        "PlanRemediacionCompetenciaEvidencia",
        backref="plan",
        cascade="all, delete-orphan",
        lazy=True,
    )


class PlanRemediacionCompetenciaEvidencia(db.Model):
    __tablename__ = "plan_remediacion_competencias_evidencias"

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(
        db.Integer,
        db.ForeignKey("plan_remediacion_competencias.id", ondelete="CASCADE"),
        nullable=False,
    )
    filename = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    mime = db.Column(db.String(100), nullable=False, default="application/pdf")
    size = db.Column(db.Integer, nullable=True)


class EstadoUsuarioAcceso(db.Model):
    __tablename__ = 'estado_usuario_acceso'
    id   = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), unique=True, nullable=False)

    def __repr__(self):
        return f"<EstadoAcceso {self.nombre}>"

class GestionAcceso(db.Model):
    __tablename__ = 'gestion_acceso'
    
    id = db.Column(db.Integer, primary_key=True)

    # ✅ UNA sola FK, bien escrita y con el nombre correcto de la tabla
    area_id = db.Column(
        db.Integer,
        db.ForeignKey('areas_empresa.id'),
        nullable=False
    )
    
    id_acceso        = db.Column(db.String(50), nullable=False)  # ID alfanumérico
    rol_usuario      = db.Column(db.String(100))
    usuario          = db.Column(db.String(100))
    aplicacion       = db.Column(db.String(150))
    tipo_acceso      = db.Column(db.String(100))
    rol_tecnico_app  = db.Column(db.String(100))
    nivel_privilegio = db.Column(db.String(10))  # "Alto, Medio, Bajo"
    justificacion    = db.Column(db.Text)
    aprobado_por     = db.Column(db.String(100))
    gestionado_por   = db.Column(db.String(100))
    fecha_alta       = db.Column(db.String(10))   # "YYYY-MM-DD"
    fecha_baja       = db.Column(db.String(10))   # "YYYY-MM-DD"
    estado_id        = db.Column(db.Integer, db.ForeignKey('estado_usuario_acceso.id'))
    evidencia        = db.Column(db.Text)

    # 🔗 Relaciones
    area = db.relationship('AreaEmpresa', backref='gestiones_acceso')
    estado = db.relationship('EstadoUsuarioAcceso')
    evidencias = db.relationship(
        'GestionAccesoEvidencia',
        back_populates='registro',
        cascade='all, delete-orphan'
    )

class GestionAccesoEvidencia(db.Model):
    __tablename__ = 'gestion_acceso_evidencia'
    id = db.Column(db.Integer, primary_key=True)

    registro_id = db.Column(db.Integer, db.ForeignKey('gestion_acceso.id'), nullable=False)
    filename     = db.Column(db.String(255), nullable=False)
    original_name= db.Column(db.String(255), nullable=False)
    mime         = db.Column(db.String(100), default='application/pdf')
    size         = db.Column(db.Integer)

    registro = db.relationship('GestionAcceso', back_populates='evidencias')


class RevisionAccesoRegistro(db.Model):
    __tablename__ = 'revision_accesos'

    id = db.Column(db.Integer, primary_key=True)

    # Campos de la tabla
    usuario_rol      = db.Column(db.String(150), nullable=False)  # Usuario / Rol
    aplicacion       = db.Column(db.String(150), nullable=False)  # Aplicación
    tipo_acceso      = db.Column(db.String(20),  nullable=False)  # Escritura / Lectura / Escritura y Lectura
    revisado_por     = db.Column(db.String(150), nullable=False)  # Revisado por
    fecha_revision   = db.Column(db.String(10),  nullable=False)  # YYYY-MM-DD (caja de fecha)
    sigue_necesario  = db.Column(db.String(2),   nullable=False)  # "Si" / "No"
    observaciones    = db.Column(db.Text,        nullable=True)   # Observaciones

class CuestionarioProveedor(db.Model):
    __tablename__ = "cuestionario_proveedor"

    id = db.Column(db.Integer, primary_key=True)

    # 🔹 QUITAMOS proveedor_id Y EL FOREIGN KEY
    # proveedor_id = db.Column(db.Integer, db.ForeignKey('proveedor.id'), nullable=True)

    nombre_proveedor = db.Column(db.String(255), nullable=False)
    sitio_web = db.Column(db.String(255), nullable=True)

    nombre_archivo = db.Column(db.String(255), nullable=False)
    contenido_archivo = db.Column(db.LargeBinary, nullable=False)
    texto_normalizado = db.Column(db.Text, nullable=True)

    fecha_carga = db.Column(db.DateTime, default=datetime.utcnow)

    evaluacion = db.relationship(
        "EvaluacionCuestionario",
        backref="cuestionario",
        uselist=False,
        cascade="all, delete-orphan"
    )


class EvaluacionCuestionario(db.Model):
    __tablename__ = "evaluacion_cuestionario"

    id = db.Column(db.Integer, primary_key=True)
    cuestionario_id = db.Column(db.Integer, db.ForeignKey('cuestionario_proveedor.id'), nullable=False)

    puntaje_cuestionario = db.Column(db.Float, nullable=False)
    explicacion_cuestionario = db.Column(db.Text, nullable=False)

    puntaje_reputacion = db.Column(db.Float, nullable=False)
    explicacion_reputacion = db.Column(db.Text, nullable=False)

    puntaje_total = db.Column(db.Float, nullable=False)

    fecha_evaluacion = db.Column(db.DateTime, default=datetime.utcnow)

class EvaluacionCuestionarioLog(db.Model):
    __tablename__ = "evaluacion_cuestionario_log"

    id = db.Column(db.Integer, primary_key=True)
    cuestionario_id = db.Column(db.Integer, db.ForeignKey('cuestionario_proveedor.id'), nullable=False)

    puntaje_cuestionario = db.Column(db.Float, nullable=False)
    explicacion_cuestionario = db.Column(db.Text, nullable=False)

    puntaje_reputacion = db.Column(db.Float, nullable=False)
    explicacion_reputacion = db.Column(db.Text, nullable=False)

    puntaje_total = db.Column(db.Float, nullable=False)

    fecha_evaluacion = db.Column(db.DateTime, default=datetime.utcnow)


class EvaluacionGrupo(db.Model):
    __tablename__ = "evaluacion_grupo"

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    fecha_evaluacion = db.Column(db.DateTime, default=datetime.utcnow)

    detalles = db.relationship(
        "EvaluacionGrupoDetalle",
        backref="grupo",
        cascade="all, delete-orphan"
    )


class EvaluacionGrupoDetalle(db.Model):
    __tablename__ = "evaluacion_grupo_detalle"

    id = db.Column(db.Integer, primary_key=True)
    grupo_id = db.Column(db.Integer, db.ForeignKey('evaluacion_grupo.id'), nullable=False)

    cuestionario_id = db.Column(db.Integer, db.ForeignKey('cuestionario_proveedor.id'), nullable=False)
    cuestionario = db.relationship("CuestionarioProveedor")

    # snapshot de los datos del proponente en el momento de la evaluación
    nombre_proveedor = db.Column(db.String(255), nullable=False)
    sitio_web = db.Column(db.String(255), nullable=True)

    puntaje_cuestionario = db.Column(db.Float, nullable=False)
    explicacion_cuestionario = db.Column(db.Text, nullable=False)

    puntaje_reputacion = db.Column(db.Float, nullable=False)
    explicacion_reputacion = db.Column(db.Text, nullable=False)

    puntaje_total = db.Column(db.Float, nullable=False)

    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)



class Vulnerabilidad(db.Model):
    __tablename__ = "vulnerabilidades"

    id = db.Column(db.Integer, primary_key=True)

    # Ejemplo: Crítica, Alta, Media, Baja
    clasificacion = db.Column(db.String(50), nullable=False)

    # Estado: Activa / Cerrada
    estado = db.Column(db.String(20), nullable=False, default="Activa")

    # Fecha en la que se registró
    fecha_registro = db.Column(db.Date, nullable=False)

    # Opcionales: puedes agregar si quieres mayor detalle
    descripcion = db.Column(db.Text, nullable=True)
    recurso_afectado = db.Column(db.String(255), nullable=True)
    criticidad = db.Column(db.String(50), nullable=True)  # si quieres replicar más campos
    
class VulnerabilidadAnalisis(db.Model):
    __tablename__ = "vulnerabilidades_analisis"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(100), unique=True, nullable=False, index=True)
    analisis = db.Column(db.Text, nullable=True)

    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    actualizado_en = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class EmailConfig(db.Model):
    __tablename__ = "email_config"
    id = db.Column(db.Integer, primary_key=True)
    smtp_host = db.Column(db.String(255), nullable=False, default="smtp.gmail.com")
    smtp_port = db.Column(db.Integer, nullable=False, default=587)
    smtp_user = db.Column(db.String(255), nullable=True)
    smtp_pass = db.Column(db.String(255), nullable=True)   # ⚠️ queda en BD (ideal: encriptar)
    smtp_from = db.Column(db.String(255), nullable=True)
    app_name  = db.Column(db.String(120), nullable=False, default="SGSI")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================================
# CENTRO DE ALERTAS ARKYNTECH GRAC
# ============================================================================

class AlertConfig(db.Model):
    """Configuración global del Centro de Alertas.

    La conexión y las credenciales SMTP NO se duplican aquí: siempre se leen
    desde EmailConfig, administrado en Parámetros Generales.
    """
    __tablename__ = "alert_config"

    id = db.Column(db.Integer, primary_key=True)
    recipients = db.Column(db.Text, nullable=True, default="")
    email_enabled = db.Column(db.Boolean, nullable=False, default=True)
    in_app_enabled = db.Column(db.Boolean, nullable=False, default=True)
    subject_prefix = db.Column(db.String(120), nullable=False, default="[Arkyntech GRAC]")
    evaluation_minutes = db.Column(db.Integer, nullable=False, default=15)
    base_url = db.Column(db.String(500), nullable=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class AlertRule(db.Model):
    __tablename__ = "alert_rules"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(100), nullable=False, unique=True, index=True)
    name = db.Column(db.String(255), nullable=False)
    module = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    metric_key = db.Column(db.String(120), nullable=False)
    operator = db.Column(db.String(5), nullable=False, default=">")
    threshold = db.Column(db.Float, nullable=False, default=0)
    severity = db.Column(db.String(20), nullable=False, default="alta")
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    email_enabled = db.Column(db.Boolean, nullable=False, default=True)
    repeat_minutes = db.Column(db.Integer, nullable=False, default=1440)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class AlertEvent(db.Model):
    __tablename__ = "alert_events"

    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.Integer, db.ForeignKey("alert_rules.id"), nullable=False, index=True)
    fingerprint = db.Column(db.String(180), nullable=False, unique=True, index=True)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    module = db.Column(db.String(120), nullable=False)
    severity = db.Column(db.String(20), nullable=False, default="alta")
    status = db.Column(db.String(30), nullable=False, default="nueva", index=True)
    value = db.Column(db.Float, nullable=True)
    threshold = db.Column(db.Float, nullable=True)
    reference_url = db.Column(db.String(500), nullable=True)
    occurrence_count = db.Column(db.Integer, nullable=False, default=1)
    first_seen_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_seen_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    acknowledged_at = db.Column(db.DateTime, nullable=True)
    acknowledged_by = db.Column(db.String(160), nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolved_by = db.Column(db.String(160), nullable=True)
    last_email_at = db.Column(db.DateTime, nullable=True)
    last_email_status = db.Column(db.String(30), nullable=True)
    last_email_error = db.Column(db.Text, nullable=True)

    rule = db.relationship("AlertRule", lazy="joined")


class AlertDelivery(db.Model):
    __tablename__ = "alert_deliveries"

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("alert_events.id"), nullable=False, index=True)
    recipients = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), nullable=False, default="pendiente")
    error = db.Column(db.Text, nullable=True)
    sent_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    event = db.relationship("AlertEvent", lazy="joined")

# ==========================
# DB MODELS
# ==========================

class AnalysisRun(db.Model):
    __tablename__ = "analysis_runs"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    company_name = db.Column(db.String(255), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    excel_path = db.Column(db.String(1024), nullable=False)

    chapter_results_json = db.Column(db.Text, nullable=False, default="{}")
    chapter_ai_json = db.Column(db.Text, nullable=False, default="{}")
    gaps_json = db.Column(db.Text, nullable=False, default="[]")

    control_results_json = db.Column(db.Text, nullable=False, default="{}")
    gaps_by_control_json = db.Column(db.Text, nullable=False, default="{}")
    control_items_json = db.Column(db.Text, nullable=False, default="{}")

    # ✅ NUEVO: resultados por ítem (estructura calculada) y salidas IA por ítem
    item_results_json = db.Column(db.Text, nullable=False, default="{}")
    item_ai_json = db.Column(db.Text, nullable=False, default="{}")

    radar_overall_b64 = db.Column(db.Text, nullable=True)
    radar_by_sheet_json = db.Column(db.Text, nullable=False, default="{}")

    executive_summary = db.Column(db.Text, nullable=True)
    ai_report_text = db.Column(db.Text, nullable=True)
    action_plan_json = db.Column(db.Text, nullable=True)

    control_ai_json = db.Column(db.Text, nullable=False, default="{}")

    ai_methodology_text = db.Column(db.Text, nullable=False, default="")

class MadurezPregunta(db.Model):
    __tablename__ = "madurez_pregunta"
    id = db.Column(db.Integer, primary_key=True)

    # Origen del instrumento
    sheet = db.Column(db.String(80), nullable=False)     # "4 CONTEXTO", ... , "ANEXO A"
    orden = db.Column(db.Integer, nullable=False, default=0)

    # Para ANEXO A
    control = db.Column(db.String(20))                   # "5.1"
    tema = db.Column(db.String(255))                     # "Políticas..."
    control_desc = db.Column(db.Text)                    # texto largo del control

    # Para capítulos 4-10
    seccion = db.Column(db.String(255))                  # "4.1 CONOCIMIENTO..." (título)

    # Pregunta
    pregunta = db.Column(db.Text, nullable=False)

    # tipo: "q" pregunta, "h" header (título)
    tipo = db.Column(db.String(1), nullable=False, default="q")


class MadurezRun(db.Model):
    __tablename__ = "madurez_run"

    id = db.Column(db.Integer, primary_key=True)

    # consecutivo / nombre de la revisión
    company_name = db.Column(db.String(255), nullable=False)

    # usuario dueño del borrador/formulario
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True, index=True)

    # estado del formulario
    # BORRADOR = guardado parcial
    # FINALIZADO = formulario completo y ya listo para análisis
    estado = db.Column(db.String(20), nullable=False, default="BORRADOR", index=True)

    # porcentaje de avance del diligenciamiento
    progreso_pct = db.Column(db.Integer, nullable=False, default=0)

    # fechas
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # relación con respuestas
    respuestas = db.relationship(
        "MadurezRespuesta",
        backref="run",
        lazy=True,
        cascade="all, delete-orphan"
    )


class MadurezRespuesta(db.Model):
    __tablename__ = "madurez_respuesta"
    id = db.Column(db.Integer, primary_key=True)

    run_id = db.Column(db.Integer, db.ForeignKey("madurez_run.id"), nullable=False, index=True)
    pregunta_id = db.Column(db.Integer, db.ForeignKey("madurez_pregunta.id"), nullable=False, index=True)

    # NA / SI / PAR / NO
    opcion = db.Column(db.String(5), nullable=False)

    comentario = db.Column(db.Text)

    __table_args__ = (
        db.UniqueConstraint("run_id", "pregunta_id", name="uq_madurez_run_pregunta"),
    )

# ==========================
# PARAMETROS / CATALOGOS
# ==========================
class MaturityLevel(db.Model):
    __tablename__ = "cfg_maturity_levels"
    id = db.Column(db.Integer, primary_key=True)
    nivel = db.Column(db.Integer, nullable=False, unique=True, index=True)
    madurez = db.Column(db.String(80), nullable=False, unique=True, index=True)
    descripcion = db.Column(db.Text, nullable=True)


class ComplianceMaturityMap(db.Model):
    __tablename__ = "cfg_compliance_maturity_map"
    id = db.Column(db.Integer, primary_key=True)
    pct_min = db.Column(db.Float, nullable=False)
    pct_max = db.Column(db.Float, nullable=False)
    maturity_id = db.Column(db.Integer, db.ForeignKey("cfg_maturity_levels.id"), nullable=False)
    maturity = db.relationship("MaturityLevel", backref=db.backref("compliance_ranges", lazy=True))

    __table_args__ = (
        db.CheckConstraint("pct_min >= 0 AND pct_min <= 100", name="ck_cmm_pctmin_0_100"),
        db.CheckConstraint("pct_max >= 0 AND pct_max <= 100", name="ck_cmm_pctmax_0_100"),
        db.CheckConstraint("pct_min <= pct_max", name="ck_cmm_pctmin_le_pctmax"),
    )


class GapLevelConfig(db.Model):
    __tablename__ = "cfg_gap_levels"
    id = db.Column(db.Integer, primary_key=True)
    pct_min = db.Column(db.Float, nullable=False)
    pct_max = db.Column(db.Float, nullable=False)
    nivel_brecha = db.Column(db.String(20), nullable=False)
    interpretacion = db.Column(db.Text, nullable=True)

    __table_args__ = (
        db.CheckConstraint("pct_min >= 0 AND pct_min <= 100", name="ck_gap_pctmin_0_100"),
        db.CheckConstraint("pct_max >= 0 AND pct_max <= 100", name="ck_gap_pctmax_0_100"),
        db.CheckConstraint("pct_min <= pct_max", name="ck_gap_pctmin_le_pctmax"),
    )


    #with app.app_context():
        #db.create_all()

#---------------------------------------------------------------------------------------------------------------
#                                         Catálogo de columnas disponibles
#---------------------------------------------------------------------------------------------------------------
#                                   -----------  Matriz de Riesgos ------------

# key: nombre del atributo en el modelo Riesgo
# label: texto del encabezado
# td_class: clase CSS opcional para ancho
# colorize: si True, usa la función color_por_valor(valor) para colorear la celda
RISK_COLUMNS = [
    {"key": "codigo_riesgo",            "label": "Cód. Riesgo",                         "td_class": "texto-corto"},
    {"key": "riesgo",                   "label": "Riesgo",                               "td_class": "texto-largo"},
    {"key": "tipo_riesgo",              "label": "Tipo de Riesgo",                       "td_class": "texto-corto"},
    {"key": "fecha_identificacion",     "label": "Fecha Ident.",                         "td_class": "texto-corto"},
    {"key": "propietario_riesgo",       "label": "Propietario del Riesgo",               "td_class": "texto-medio"},
    {"key": "codigo_amenaza",           "label": "Código Amenaza",                       "td_class": "texto-corto"},
    {"key": "amenaza",                  "label": "Amenazas",                             "td_class": "texto-largo"},
    {"key": "codigo_vulnerabilidad",    "label": "Código Vulnerabilidad",                "td_class": "texto-corto"},
    {"key": "vulnerabilidad",           "label": "Vulnerabilidades",                     "td_class": "texto-largo"},
    {"key": "tipo_activo",              "label": "Tipo de Activo",                       "td_class": "texto-corto"},
    {"key": "nombre_activo",            "label": "Nombre de Activo(s)",                  "td_class": "texto-medio"},
    {"key": "dimension_seguridad",      "label": "Principio de Seguridad",               "td_class": "texto-corto"},
    {"key": "prob_inh",                 "label": "Prob. Inherente",                      "td_class": "texto-corto"},
    {"key": "imp_inh",                  "label": "Impacto Inherente",                    "td_class": "texto-corto"},
    {"key": "riesgo_inherente",         "label": "Riesgo Inherente",                     "td_class": "texto-corto", "colorize": True},

    {"key": "control_codigo",           "label": "Código del Control",                   "td_class": "texto-corto"},
    {"key": "codigo_anexo",             "label": "Código Control Anexo ISO 27002",       "td_class": "texto-corto"},
    {"key": "codigo_control_pci_dss",  "label": "Código Control PCI DSS",                 "td_class": "texto-corto"},
    {"key": "codigo_control_nist_csf", "label": "Código Control NIST CSF 2.0",            "td_class": "texto-corto"},
    {"key": "codigo_control_soc2",     "label": "Código Control SOC 2",                   "td_class": "texto-corto"},
    {"key": "descripcion_control",      "label": "Descripción del Control",              "td_class": "texto-largo"},
    {"key": "plan_accion",              "label": "Plan de Acción",                       "td_class": "texto-largo"},
    {"key": "asignacion",               "label": "Asignación",                           "td_class": "texto-medio"},
    {"key": "cargo",                    "label": "Cargo",                                "td_class": "texto-medio"},
    {"key": "calificacion_asignacion",  "label": "Calif. Asignación (%)",                "td_class": "texto-corto"},
    {"key": "tipo_control",             "label": "Tipo de Control",                      "td_class": "texto-medio"},
    {"key": "calificacion_tipo_control","label": "Calif. Tipo Control (%)",              "td_class": "texto-corto"},
    {"key": "forma_control",            "label": "Forma de Control",                     "td_class": "texto-medio"},
    {"key": "calificacion_forma_control","label":"Calif. Forma Control (%)",             "td_class": "texto-corto"},
    {"key": "frecuencia",               "label": "Frecuencia",                           "td_class": "texto-corto"},
    {"key": "funcionalidad",            "label": "Funcionalidad",                        "td_class": "texto-corto"},
    {"key": "calificacion_funcionalidad","label":"Calif. Funcionalidad (%)",            "td_class": "texto-corto"},
    {"key": "estado_control",           "label": "Estado del Control",                   "td_class": "texto-corto"},
    {"key": "referencia_documental",    "label": "Referencia Documental",                "td_class": "texto-medio"},
    {"key": "calificacion_estado_control","label":"Calif. Estado Control (%)",           "td_class": "texto-corto"},
    {"key": "evidencia_control",        "label": "Evidencia del Control",                "td_class": "texto-largo"},
    {"key": "soporte_evidencia",        "label": "Soporte Evidencia",                    "td_class": "texto-medio"},
    {"key": "calificacion_soporte_evidencia","label":"Calif. Soporte Evidencia (%)",     "td_class": "texto-corto"},
    {"key": "diseno_control",           "label": "Diseño del Control",                   "td_class": "texto-corto"},
    {"key": "ejecucion_control",        "label": "Ejecución del Control",                "td_class": "texto-corto"},
    {"key": "valor_ejecucion_control",  "label": "Valor Ejecución Control (%)",          "td_class": "texto-corto"},
    {"key": "solidez_individual",       "label": "Solidez Individual (%)",               "td_class": "texto-corto"},
    {"key": "solidez_grupal",           "label": "Solidez Grupal (%)",                   "td_class": "texto-corto"},
    {"key": "cuadrante_prob",           "label": "Probabilidad Residual.",                      "td_class": "texto-corto"},
    {"key": "cuadrante_imp",            "label": "Impacto Residual.",                       "td_class": "texto-corto"},

    #{"key": "prob_res",                 "label": "Prob. Residual",                       "td_class": "texto-corto"},
    #{"key": "imp_res",                  "label": "Impacto Residual",                     "td_class": "texto-corto"},
    {"key": "riesgo_residual",          "label": "Riesgo Residual",                      "td_class": "texto-corto", "colorize": True},
    {"key": "fecha_revision",           "label": "Fecha de Revisión",                    "td_class": "texto-corto"},

    {"key": "tratamiento_riesgo",       "label": "Tratamiento del Riesgo",               "td_class": "texto-corto"},
    {"key": "observaciones",            "label": "Observaciones",                        "td_class": "texto-largo"},
    {"key": "planes_accion",            "label": "Planes de Acción",                     "td_class": "texto-largo"},
    {"key": "responsable",              "label": "Responsable",                          "td_class": "texto-medio"},
    {"key": "fecha_implementacion",     "label": "Fecha de Implementación",              "td_class": "texto-corto"},

    {"key": "archivado",                "label": "Estatus del Riesgo",                   "td_class": "texto-corto"},
]

# Campos que se muestran por defecto si el usuario no ha elegido nada

RISK_DEFAULT_FIELDS = [
    "codigo_riesgo", "riesgo", "propietario_riesgo",
    "tipo_activo", "nombre_activo", "dimension_seguridad",
    "tipo_riesgo", "prob_inh", "imp_inh", "riesgo_inherente",
    "control_codigo", "codigo_anexo",
    "codigo_control_pci_dss", "codigo_control_nist_csf", "codigo_control_soc2",
    "descripcion_control",
    "prob_res", "imp_res", "riesgo_residual",
    "tratamiento_riesgo", "responsable", "archivado"
]

# ============================================================
# CATÁLOGOS DE CONTROLES PARA GESTIÓN DE RIESGOS
# Fuentes incorporadas:
# - ISO/IEC 27002:2022 (catálogo integrado en la aplicación)
# - PCI DSS (instrumento PCI requerimientos)
# - NIST CSF 2.0 (subcategorías/controles GV.OC-01 ... RC.CO-04)
# - SOC 2 (instrumento de preguntas SOC 2)
#
# Los textos se incluyen completos para que la aplicación sea
# autocontenida y la descripción multimarco pueda generarse sin
# depender de los archivos Excel en producción.
# ============================================================
ISO_27002_CONTROLES = [('5.1',
  'Controles organizacionales\n'
  'Políticas de seguridad de la información\n'
  'La política de seguridad de la información y las políticas específicas deberán definirse, aprobarse por la '
  'dirección, publicarse, comunicarse y reconocerse por el personal y las partes interesadas, y revisarse a '
  'intervalos planificados o cuando se produzcan cambios significativos.'),
 ('5.2',
  'Controles organizacionales\n'
  'Roles y responsabilidades de seguridad de la información\n'
  'Los roles y responsabilidades de seguridad de la información deberán definirse y asignarse según las necesidades '
  'de la organización.'),
 ('5.3',
  'Controles organizacionales\n'
  'Separación de funciones\n'
  'Las funciones conflictivas y las áreas de responsabilidad en conflicto deberán separarse.'),
 ('5.4',
  'Controles organizacionales\n'
  'Responsabilidades de la dirección\n'
  'La dirección deberá exigir que todo el personal aplique la seguridad de la información de acuerdo con la política '
  'y los procedimientos específicos aplicables.'),
 ('5.5',
  'Controles organizacionales\n'
  'Contacto con autoridades\n'
  'La organización deberá establecer y mantener contacto con las autoridades relevantes.'),
 ('5.6',
  'Controles organizacionales\n'
  'Contacto con grupos de interés especial\n'
  'La organización deberá establecer y mantener contacto con grupos de especial interés, foros especializados y '
  'asociaciones profesionales.'),
 ('5.7',
  'Controles organizacionales\n'
  'Inteligencia de amenazas\n'
  'Se deberá recopilar y analizar información relacionada con las amenazas para producir inteligencia sobre '
  'amenazas.'),
 ('5.8',
  'Controles organizacionales\n'
  'Seguridad de la información en la gestión de proyectos\n'
  'La seguridad de la información deberá integrarse en la gestión de proyectos.'),
 ('5.9',
  'Controles organizacionales\n'
  'Inventario de información y activos asociados\n'
  'Se deberá desarrollar y mantener un inventario de la información y otros activos asociados, incluidos los '
  'propietarios.'),
 ('5.10',
  'Controles organizacionales\n'
  'Uso aceptable de la información y activos asociados\n'
  'Se deberán identificar, documentar e implantar reglas y procedimientos para el uso aceptable y el manejo de la '
  'información y otros activos asociados.'),
 ('5.11',
  'Controles organizacionales\n'
  'Devolución de activos\n'
  'El personal y otras partes interesadas deberán devolver los activos de la organización en su posesión al cambiar '
  'o terminar su relación contractual o laboral.'),
 ('5.12',
  'Controles organizacionales\n'
  'Clasificación de la información\n'
  'La información deberá clasificarse según las necesidades de seguridad de la organización (confidencialidad, '
  'integridad, disponibilidad) y requisitos de las partes interesadas.'),
 ('5.13',
  'Controles organizacionales\n'
  'Etiquetado de la información\n'
  'Se deberán desarrollar e implantar procedimientos apropiados para etiquetar la información según el esquema de '
  'clasificación adoptado.'),
 ('5.14',
  'Controles organizacionales\n'
  'Transferencia de información\n'
  'Deben existir reglas, procedimientos o acuerdos para todo tipo de transferencia dentro de la organización y con '
  'terceros.'),
 ('5.15',
  'Controles organizacionales\n'
  'Control de accesos\n'
  'Se deberán establecer e implementar reglas para controlar el acceso físico y lógico a la información y activos '
  'asociados según requisitos de negocio y seguridad.'),
 ('5.16',
  'Controles organizacionales\n'
  'Gestión de identidades\n'
  'Deberá gestionarse el ciclo de vida completo de las identidades.'),
 ('5.17',
  'Controles organizacionales\n'
  'Información de autenticación\n'
  'La asignación y gestión de la información de autenticación deberá controlarse mediante procesos de gestión y '
  'orientación al personal.'),
 ('5.18',
  'Controles organizacionales\n'
  'Derechos de acceso\n'
  'Los derechos de acceso deberán ser provisionados, revisados, modificados y eliminados conforme a políticas y '
  'reglas de control de acceso.'),
 ('5.19',
  'Controles organizacionales\n'
  'Seguridad de la información en relaciones con proveedores\n'
  'Se deberán definir e implantar procesos para gestionar los riesgos de seguridad asociados al uso de productos o '
  'servicios de proveedores.'),
 ('5.20',
  'Controles organizacionales\n'
  'Seguridad en acuerdos con proveedores\n'
  'Se establecerán y acordarán requisitos de seguridad de la información con cada proveedor según el tipo de '
  'relación.'),
 ('5.21',
  'Controles organizacionales\n'
  'Gestión de la seguridad en la cadena de suministro TIC\n'
  'Se deberán definir e implantar procesos para gestionar los riesgos asociados con productos y servicios TIC de la '
  'cadena de suministro.'),
 ('5.22',
  'Controles organizacionales\n'
  'Monitoreo y gestión del cambio de servicios de proveedor\n'
  'La organización deberá supervisar, revisar y gestionar cambios en prácticas de seguridad y entrega de servicios '
  'de proveedores.'),
 ('5.23',
  'Controles organizacionales\n'
  'Seguridad para uso de servicios en la nube\n'
  'Se deberán establecer procesos para adquisición, uso, gestión y salida de servicios en la nube según requisitos '
  'de seguridad organizacionales.'),
 ('5.24',
  'Controles organizacionales\n'
  'Planificación y preparación para la gestión de incidentes\n'
  'La organización deberá planear y prepararse para gestionar incidentes de seguridad definiendo procesos, roles y '
  'responsabilidades.'),
 ('5.25',
  'Controles organizacionales\n'
  'Evaluación y decisión sobre eventos de seguridad\n'
  'La organización deberá evaluar los eventos de seguridad y decidir si deben categorizarse como incidentes.'),
 ('5.26',
  'Controles organizacionales\n'
  'Respuesta a incidentes de seguridad\n'
  'Los incidentes de seguridad deben responderse de acuerdo con procedimientos documentados.'),
 ('5.27',
  'Controles organizacionales\n'
  'Aprendizaje de incidentes de seguridad\n'
  'El conocimiento obtenido de incidentes debe usarse para fortalecer y mejorar los controles de seguridad.'),
 ('5.28',
  'Controles organizacionales\n'
  'Recopilación de evidencias\n'
  'Se deberán establecer procedimientos para la identificación, recolección y preservación de evidencias '
  'relacionadas con eventos de seguridad.'),
 ('5.29',
  'Controles organizacionales\n'
  'Seguridad durante la interrupción\n'
  'La organización deberá planear cómo mantener la seguridad de la información en un nivel apropiado durante una '
  'interrupción.'),
 ('5.30',
  'Controles organizacionales\n'
  'Preparación TIC para continuidad del negocio\n'
  'La preparación TIC para continuidad debe planearse, implementarse, mantenerse y probarse según objetivos de '
  'continuidad.'),
 ('5.31',
  'Controles organizacionales\n'
  'Requisitos legales, reglamentarios y contractuales\n'
  'Se deberán identificar, documentar y mantener actualizados los requisitos legales y contractuales relevantes para '
  'la seguridad de la información.'),
 ('5.32',
  'Controles organizacionales\n'
  'Derechos de propiedad intelectual\n'
  'La organización deberá implantar procedimientos apropiados para proteger la propiedad intelectual.'),
 ('5.33',
  'Controles organizacionales\n'
  'Protección de registros\n'
  'Los registros deberán protegerse contra pérdida, destrucción, falsificación, acceso no autorizado y divulgación '
  'no autorizada.'),
 ('5.34',
  'Controles organizacionales\n'
  'Privacidad y protección de datos personales (PII)\n'
  'La organización deberá identificar y cumplir los requisitos de preservación de la privacidad y protección de PII '
  'conforme a leyes y contratos aplicables.'),
 ('5.35',
  'Controles organizacionales\n'
  'Revisión independiente de seguridad de la información\n'
  'El enfoque de la organización para gestionar la seguridad deberá revisarse de forma independiente a intervalos '
  'planificados o tras cambios significativos.'),
 ('5.36',
  'Controles organizacionales\n'
  'Cumplimiento con políticas, reglas y estándares\n'
  'El cumplimiento con la política de seguridad, políticas específicas, reglas y estándares deberá revisarse '
  'regularmente.'),
 ('5.37',
  'Controles organizacionales\n'
  'Procedimientos operativos documentados\n'
  'Se deberán documentar los procedimientos operativos para las instalaciones de procesamiento de información y '
  'ponerlos a disposición del personal que los necesite.'),
 ('6.1',
  'Controles de personas\n'
  'Verificación de antecedentes (screening)\n'
  'Se deberán efectuar verificaciones previas de antecedentes para candidatos al personal y de forma continua según '
  'leyes, regulaciones y riesgos.'),
 ('6.2',
  'Controles de personas\n'
  'Términos y condiciones de empleo\n'
  'Los contratos de empleo deberán expresar las responsabilidades del personal y de la organización respecto a la '
  'seguridad de la información.'),
 ('6.3',
  'Controles de personas\n'
  'Concienciación, educación y formación en seguridad\n'
  'El personal y partes interesadas relevantes deberán recibir formación y actualizaciones sobre políticas y '
  'procedimientos de seguridad.'),
 ('6.4',
  'Controles de personas\n'
  'Proceso disciplinario\n'
  'Se deberá formalizar y comunicar un proceso disciplinario para acciones contra incumplimientos de la política de '
  'seguridad.'),
 ('6.5',
  'Controles de personas\n'
  'Responsabilidades tras terminación o cambio de empleo\n'
  'Se deberán definir y comunicar responsabilidades de seguridad que se mantienen tras la terminación o cambio de '
  'empleo.'),
 ('6.6',
  'Controles de personas\n'
  'Acuerdos de confidencialidad (NDA)\n'
  'Se deberán identificar, documentar, revisar y firmar acuerdos de confidencialidad según las necesidades de la '
  'organización.'),
 ('6.7',
  'Controles de personas\n'
  'Trabajo remoto\n'
  'Se deberán implantar medidas de seguridad cuando el personal trabaje de forma remota para proteger la información '
  'fuera de las instalaciones.'),
 ('6.8',
  'Controles de personas\n'
  'Reportes de eventos de seguridad\n'
  'La organización deberá proporcionar mecanismos para que el personal reporte incidentes observados o sospechados '
  'de forma oportuna.'),
 ('7.1',
  'Controles físicos\n'
  'Perímetros de seguridad física\n'
  'Se deberán definir perímetros de seguridad para proteger áreas que contengan información y activos asociados.'),
 ('7.2',
  'Controles físicos\n'
  'Entrada física\n'
  'Las áreas seguras deberán protegerse mediante controles de acceso y puntos de entrada apropiados.'),
 ('7.3',
  'Controles físicos\n'
  'Aseguramiento de oficinas, salas e instalaciones\n'
  'La seguridad física de oficinas, salas e instalaciones deberá diseñarse e implementarse.'),
 ('7.4',
  'Controles físicos\n'
  'Monitorización de seguridad física\n'
  'Las instalaciones deberán ser monitorizadas para detectar accesos físicos no autorizados.'),
 ('7.5',
  'Controles físicos\n'
  'Protección contra amenazas físicas y ambientales\n'
  'Se deberán diseñar e implementar medidas contra amenazas físicas y ambientales (desastres naturales, etc.).'),
 ('7.6',
  'Controles físicos\n'
  'Trabajo en áreas seguras\n'
  'Se deberán implantar medidas de seguridad para el trabajo en áreas seguras.'),
 ('7.7',
  'Controles físicos\n'
  'Escritorio y pantalla limpios\n'
  'Se deberán definir y aplicar reglas de escritorio y pantalla limpia para proteger la información.'),
 ('7.8', 'Controles físicos\nUbicación y protección del equipo\nEl equipo deberá ubicarse y protegerse físicamente.'),
 ('7.9',
  'Controles físicos\n'
  'Seguridad de activos fuera de las instalaciones\n'
  'Los activos fuera de las instalaciones deberán protegerse adecuadamente.'),
 ('7.10',
  'Controles físicos\n'
  'Medios de almacenamiento\n'
  'Los medios de almacenamiento deberán gestionarse durante todo su ciclo (adquisición, uso, transporte, '
  'eliminación) conforme al esquema de clasificación.'),
 ('7.11',
  'Controles físicos\n'
  'Servicios de apoyo\n'
  'Las instalaciones de procesamiento de información deberán protegerse de fallos de servicios públicos y otras '
  'interrupciones.'),
 ('7.12',
  'Controles físicos\n'
  'Seguridad del cableado\n'
  'Los cables que transporten energía o datos deberán protegerse contra intercepción, interferencia o daño.'),
 ('7.13',
  'Controles físicos\n'
  'Mantenimiento de equipos\n'
  'El equipo deberá mantenerse para asegurar disponibilidad, integridad y confidencialidad.'),
 ('7.14',
  'Controles físicos\n'
  'Disposición segura o reutilización de equipos\n'
  'Los equipos con medios de almacenamiento deberán verificarse para asegurar que los datos sensibles se han '
  'eliminado o sobrescrito antes de su eliminación o reutilización.'),
 ('8.1',
  'Controles tecnológicos\n'
  'Dispositivos endpoint de usuario\n'
  'La información almacenada, procesada o accesible mediante dispositivos endpoint deberá protegerse.'),
 ('8.2',
  'Controles tecnológicos\n'
  'Derechos privilegiados de acceso\n'
  'La asignación y uso de derechos privilegiados deberá restringirse y gestionarse.'),
 ('8.3',
  'Controles tecnológicos\n'
  'Restricción de acceso a la información\n'
  'El acceso a la información y activos asociados deberá restringirse conforme a la política de control de acceso.'),
 ('8.4',
  'Controles tecnológicos\n'
  'Acceso al código fuente\n'
  'El acceso de lectura/escritura al código fuente, herramientas de desarrollo y bibliotecas deberá gestionarse '
  'adecuadamente.'),
 ('8.5',
  'Controles tecnológicos\n'
  'Autenticación segura\n'
  'Deben implementarse tecnologías y procedimientos de autenticación segura basados en la política de control de '
  'acceso.'),
 ('8.6',
  'Controles tecnológicos\n'
  'Gestión de capacidad\n'
  'Se deberán monitorizar y ajustar los recursos conforme a los requisitos actuales y esperados.'),
 ('8.7',
  'Controles tecnológicos\n'
  'Protección contra malware\n'
  'Deben implementarse medidas de protección contra malware y concienciación del usuario.'),
 ('8.8',
  'Controles tecnológicos\n'
  'Gestión de vulnerabilidades técnicas\n'
  'Se deberá obtener información sobre vulnerabilidades técnicas y evaluar la exposición de la organización, tomando '
  'medidas apropiadas.'),
 ('8.9',
  'Controles tecnológicos\n'
  'Gestión de configuración\n'
  'Se deberán establecer, documentar, implementar y revisar configuraciones, incluidas las de seguridad.'),
 ('8.10',
  'Controles tecnológicos\n'
  'Eliminación de información\n'
  'La información almacenada en sistemas o medios deberá eliminarse cuando ya no sea necesaria.'),
 ('8.11',
  'Controles tecnológicos\n'
  'Enmascaramiento de datos\n'
  'Se deberá aplicar enmascaramiento de datos conforme a políticas y requisitos legales y de negocio.'),
 ('8.12',
  'Controles tecnológicos\n'
  'Prevención de pérdida de datos\n'
  'Se deberán aplicar medidas de prevención de fuga de datos a sistemas, redes y dispositivos que procesen '
  'información sensible.'),
 ('8.13',
  'Controles tecnológicos\n'
  'Copia de seguridad de la información\n'
  'Se deberán mantener y probar regularmente copias de seguridad de información, software y sistemas conforme a la '
  'política de backups.'),
 ('8.14',
  'Controles tecnológicos\n'
  'Redundancia de instalaciones de procesamiento\n'
  'Las instalaciones de procesamiento deberán contar con redundancia suficiente para cumplir requisitos de '
  'disponibilidad.'),
 ('8.15',
  'Controles tecnológicos\n'
  'Registro y trazabilidad (logging)\n'
  'Deben generarse, almacenar, proteger y analizar registros que reflejen actividades, excepciones y fallos '
  'relevantes.'),
 ('8.16',
  'Controles tecnológicos\n'
  'Actividades de monitorización\n'
  'Redes, sistemas y aplicaciones deberán monitorizarse para detectar comportamientos anómalos y evaluar posibles '
  'incidentes.'),
 ('8.17',
  'Controles tecnológicos\n'
  'Sincronización de relojes\n'
  'Los relojes de los sistemas deberán sincronizarse con fuentes de tiempo aprobadas.'),
 ('8.18',
  'Controles tecnológicos\n'
  'Uso de utilidades privilegiadas\n'
  'El uso de programas utilitarios capaces de anular controles del sistema deberá restringirse y controlarse '
  'estrictamente.'),
 ('8.19',
  'Controles tecnológicos\n'
  'Instalación de software en sistemas operativos\n'
  'Deben implementarse procedimientos para gestionar la instalación de software en sistemas operativos de manera '
  'segura.'),
 ('8.20',
  'Controles tecnológicos\n'
  'Seguridad de redes\n'
  'Redes y dispositivos de red deberán protegerse, gestionarse y controlarse para salvaguardar la información.'),
 ('8.21',
  'Controles tecnológicos\n'
  'Seguridad de servicios de red\n'
  'Se deberán identificar, implementar y monitorizar mecanismos y niveles de servicio de los servicios de red.'),
 ('8.22',
  'Controles tecnológicos\n'
  'Segregación en redes\n'
  'Se deberán segregar grupos de servicios, usuarios y sistemas en las redes de la organización.'),
 ('8.23',
  'Controles tecnológicos\n'
  'Filtrado web\n'
  'El acceso a sitios externos deberá gestionarse para reducir exposición a contenido malicioso.'),
 ('8.24',
  'Controles tecnológicos\n'
  'Uso de criptografía\n'
  'Deben definirse e implantar reglas para el uso efectivo de criptografía y gestión de claves.'),
 ('8.25',
  'Controles tecnológicos\n'
  'Ciclo de vida de desarrollo seguro\n'
  'Deben establecerse y aplicarse reglas para el desarrollo seguro de software y sistemas.'),
 ('8.26',
  'Controles tecnológicos\n'
  'Requisitos de seguridad de aplicaciones\n'
  'Se deberán identificar, especificar y aprobar requisitos de seguridad al desarrollar o adquirir aplicaciones.'),
 ('8.27',
  'Controles tecnológicos\n'
  'Arquitectura y principios de ingeniería seguros\n'
  'Deben establecerse principios documentados para ingeniería de sistemas seguros en actividades de desarrollo.'),
 ('8.28',
  'Controles tecnológicos\n'
  'Codificación segura\n'
  'Deben aplicarse principios de codificación segura durante el desarrollo de software.'),
 ('8.29',
  'Controles tecnológicos\n'
  'Pruebas de seguridad en desarrollo y aceptación\n'
  'Deben definirse e implantar procesos de pruebas de seguridad dentro del ciclo de desarrollo.'),
 ('8.30',
  'Controles tecnológicos\n'
  'Desarrollo externalizado\n'
  'La organización deberá dirigir, supervisar y revisar actividades relacionadas con el desarrollo externalizado.'),
 ('8.31',
  'Controles tecnológicos\n'
  'Separación de entornos (desarrollo, prueba, producción)\n'
  'Los entornos de desarrollo, prueba y producción deberán separarse y asegurarse.'),
 ('8.32',
  'Controles tecnológicos\n'
  'Gestión de cambios\n'
  'Los cambios en instalaciones y sistemas deberán sujetarse a procedimientos de gestión de cambios.'),
 ('8.33',
  'Controles tecnológicos\n'
  'Información de prueba\n'
  'La información de prueba deberá seleccionarse, protegerse y gestionarse apropiadamente.'),
 ('8.34',
  'Controles tecnológicos\n'
  'Protección de sistemas durante pruebas de auditoría\n'
  'Las pruebas de auditoría y actividades de aseguramiento en sistemas operativos deberán planificarse y acordarse '
  'con la dirección apropiada.')]

PCI_DSS_CONTROLES = [('1.1',
  'Los procesos y mecanismos para instalar y mantener controles de seguridad de red están definidos y comprendidos.'),
 ('1.1.1',
  'Todas las políticas de seguridad y procedimientos operativos identificados en el Requisito 1 son:\n'
  '\n'
  '- Documentados.\n'
  '- Mantenidos actualizados.\n'
  '- En uso.\n'
  '- Conocidos por todas las partes afectadas.'),
 ('1.1.2',
  'Los roles y responsabilidades para realizar las actividades del Requisito 1 están documentados, asignados y '
  'comprendidos.'),
 ('1.2', 'Los controles de seguridad de red (NSC) están configurados y mantenidos.'),
 ('1.2.1',
  'Los estándares de configuración para los conjuntos de reglas de los NSC son:\n'
  '\n'
  '- Definidos.\n'
  '- Implementados.\n'
  '- Mantenidos.'),
 ('1.2.2',
  'Todos los cambios en las conexiones de red y en las configuraciones de los NSC son aprobados y gestionados '
  'conforme al proceso de control de cambios definido en el Requisito 6.5.1.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Los cambios en conexiones de red incluyen la adición, eliminación o modificación de una conexión.\n'
  'Los cambios en configuraciones de NSC incluyen tanto los relacionados con el componente como aquellos que afectan '
  'cómo desempeña su función de seguridad.'),
 ('1.2.3',
  'Se mantiene uno o más diagramas de red precisos que muestran todas las conexiones entre el entorno de datos de '
  'titulares de tarjeta (CDE) y otras redes, incluyendo redes inalámbricas.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Se puede utilizar un diagrama de red actualizado u otra solución técnica o topológica que identifique conexiones '
  'y dispositivos de red.'),
 ('1.2.4',
  'Se mantiene uno o más diagramas precisos de flujo de datos que:\n'
  '\n'
  'Muestran todos los flujos de datos de cuentas a través de sistemas y redes.\n'
  'Se actualizan según cambios en el entorno.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Se puede usar un diagrama de flujo de datos u otra solución técnica o topológica que identifique dichos flujos.'),
 ('1.2.5',
  'Todos los servicios, protocolos y puertos permitidos están identificados, aprobados y tienen una necesidad de '
  'negocio definida.'),
 ('1.2.6',
  'Se definen e implementan controles de seguridad para todos los servicios, protocolos y puertos en uso '
  'considerados inseguros, de modo que el riesgo sea mitigado.'),
 ('1.2.7',
  'Las configuraciones de los NSC se revisan al menos cada seis meses para confirmar que son relevantes y '
  'efectivas.'),
 ('1.2.8',
  'Los archivos de configuración de los NSC:\n'
  '\n'
  '- Están protegidos contra accesos no autorizados.\n'
  '- Se mantienen consistentes con las configuraciones activas de red.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Se considera archivo de configuración cualquier archivo o ajuste utilizado para configurar o sincronizar NSC, '
  'incluyendo scripts, controles automatizados, infraestructura como código, parámetros respaldados o almacenados '
  'remotamente.'),
 ('1.3', 'El acceso de red hacia y desde el entorno de datos de titulares de tarjeta (CDE) está restringido.'),
 ('1.3.1',
  'El tráfico entrante al CDE se restringe de la siguiente forma:\n'
  '\n'
  '- Solo se permite el tráfico necesario.\n'
  '- Todo otro tráfico se deniega explícitamente.'),
 ('1.3.2',
  'El tráfico saliente del CDE se restringe de la siguiente forma:\n'
  '\n'
  '- Solo se permite el tráfico necesario.\n'
  '- Todo otro tráfico se deniega explícitamente.'),
 ('1.3.3',
  'Los NSC se implementan entre redes inalámbricas y el CDE, de manera que:\n'
  '\n'
  '- Todo el tráfico inalámbrico hacia el CDE se deniega por defecto.\n'
  '- Solo se permite tráfico inalámbrico con un propósito de negocio autorizado.'),
 ('1.4', 'Las conexiones entre redes confiables y no confiables están controladas.'),
 ('1.4.1', 'Se implementan NSC entre redes confiables y no confiables.'),
 ('1.4.2',
  'El tráfico entrante desde redes no confiables a redes confiables se restringe a:\n'
  '\n'
  '- Comunicaciones con componentes autorizados para servicios públicos.\n'
  '- Respuestas con estado a comunicaciones iniciadas desde redes confiables.\n'
  '- Todo otro tráfico es denegado.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'El objetivo es controlar sesiones de comunicación, no protocolos específicos.\n'
  'No limita el uso de UDP u otros protocolos sin conexión si el estado es gestionado por el NSC.'),
 ('1.4.3',
  'Se implementan medidas anti-suplantación (anti-spoofing) para detectar y bloquear direcciones IP de origen '
  'falsificadas.'),
 ('1.4.4',
  'Los componentes que almacenan datos de titulares de tarjeta no son accesibles directamente desde redes no '
  'confiables.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'No aplica a almacenamiento en memoria volátil, salvo cuando esta se usa como almacenamiento persistente (ej. RAM '
  'disk).'),
 ('1.4.5',
  'La divulgación de direcciones IP internas e información de enrutamiento se limita únicamente a partes '
  'autorizadas.'),
 ('1.5', 'Los riesgos al CDE desde dispositivos que pueden conectarse a redes no confiables y al CDE son mitigados.'),
 ('1.5.1',
  'Se implementan controles de seguridad en dispositivos que se conectan tanto a redes no confiables (incluido '
  'Internet) como al CDE:\n'
  '\n'
  'Se definen configuraciones específicas para prevenir amenazas.\n'
  'Los controles de seguridad están activos.\n'
  'No pueden ser modificados por usuarios, salvo autorización documentada y temporal.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Los controles solo pueden deshabilitarse temporalmente por necesidad técnica legítima y con autorización formal.\n'
  'Pueden requerirse controles adicionales durante ese periodo.\n'
  'Aplica a dispositivos corporativos y personales.'),
 ('2.1',
  'Los procesos y mecanismos para aplicar configuraciones seguras a todos los componentes del sistema están '
  'definidos y comprendidos.'),
 ('2.1.1',
  'Todas las políticas de seguridad y procedimientos operativos identificados en el Requisito 2 son:\n'
  '\n'
  '- Documentados.\n'
  '- Mantenidos actualizados.\n'
  '- En uso.\n'
  '- Conocidos por todas las partes afectadas.'),
 ('2.1.2',
  'Los roles y responsabilidades para realizar las actividades del Requisito 2 están documentados, asignados y '
  'comprendidos.'),
 ('2.2', 'Los componentes del sistema están configurados y gestionados de forma segura.'),
 ('2.2.1',
  'Los estándares de configuración se desarrollan, implementan y mantienen para:\n'
  '\n'
  '- Cubrir todos los componentes del sistema.\n'
  '- Abordar todas las vulnerabilidades de seguridad conocidas.\n'
  '- Ser consistentes con estándares de endurecimiento (hardening) aceptados por la industria o recomendaciones del '
  'proveedor.\n'
  '- Actualizarse cuando se identifiquen nuevas vulnerabilidades, según el Requisito 6.3.1.\n'
  '- Aplicarse cuando se configuren nuevos sistemas y verificarse antes o inmediatamente después de que un '
  'componente del sistema se conecte a un entorno de producción.'),
 ('2.2.2',
  'Las cuentas predeterminadas del proveedor se gestionan de la siguiente manera:\n'
  '\n'
  '- Si se utilizan, la contraseña predeterminada se cambia conforme al Requisito 8.3.6.\n'
  '- Si no se utilizan, la cuenta se elimina o deshabilita.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Esto aplica a TODAS las cuentas y contraseñas predeterminadas de proveedores, incluyendo, entre otros:\n'
  '\n'
  '- Sistemas operativos\n'
  '- Software de seguridad\n'
  '- Cuentas de aplicaciones y sistemas\n'
  '- Terminales POS\n'
  '- Aplicaciones de pago\n'
  '- Valores predeterminados de SNMP\n'
  '\n'
  'También aplica cuando el componente no está instalado localmente, por ejemplo, soluciones en la nube dentro del '
  'CDE.'),
 ('2.2.3',
  'Las funciones principales que requieren diferentes niveles de seguridad se gestionan así:\n'
  '\n'
  '- Existe una sola función principal por componente del sistema,\n'
  'O\n'
  '- Las funciones con diferentes niveles de seguridad en el mismo componente están aisladas entre sí,\n'
  'O\n'
  '- Todas las funciones se aseguran al nivel requerido por la función con mayor necesidad de seguridad.'),
 ('2.2.4',
  'Solo se habilitan servicios, protocolos, demonios y funciones necesarios; toda funcionalidad innecesaria se '
  'elimina o deshabilita.'),
 ('2.2.5',
  'Si existen servicios, protocolos o demonios inseguros:\n'
  '\n'
  '- Se documenta la justificación de negocio.\n'
  '- Se implementan controles de seguridad adicionales que reduzcan el riesgo.'),
 ('2.2.6', 'Los parámetros de seguridad del sistema se configuran para prevenir el uso indebido.'),
 ('2.2.7',
  'Todo acceso administrativo remoto (no por consola) está cifrado mediante criptografía fuerte.\n'
  'Notas de aplicabilidad:\n'
  'Incluye accesos administrativos mediante:\n'
  '\n'
  '- Interfaces web\n'
  '- APIs (interfaces de programación de aplicaciones)'),
 ('2.3', 'Los entornos inalámbricos están configurados y gestionados de forma segura.'),
 ('2.3.1',
  'Para entornos inalámbricos conectados al CDE o que transmiten datos de cuentas, todos los valores predeterminados '
  'del proveedor se cambian al momento de la instalación o se verifica que sean seguros, incluyendo:\n'
  '\n'
  '- Claves de cifrado inalámbricas por defecto.\n'
  '- Contraseñas de puntos de acceso inalámbricos.\n'
  '- Valores predeterminados de SNMP.\n'
  '- Cualquier otro valor predeterminado de seguridad inalámbrica.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Incluye, entre otros, claves, contraseñas, SNMP y configuraciones de seguridad por defecto.'),
 ('2.3.2',
  'Las claves de cifrado inalámbricas se cambian:\n'
  '\n'
  '- Cuando el personal con conocimiento de la clave deja la organización o cambia de rol.\n'
  '- Cuando una clave se sospecha o se confirma comprometida.'),
 ('3.1', 'Los procesos y mecanismos para realizar las actividades del Requisito 3 están definidos y comprendidos.'),
 ('3.1.1',
  'Todas las políticas de seguridad y procedimientos operativos identificados en el Requisito 3 son:\n'
  '\n'
  '- Documentados.\n'
  '- Mantenidos actualizados.\n'
  '- En uso.\n'
  '- Conocidos por todas las partes afectadas.'),
 ('3.1.2', 'Los roles y responsabilidades están documentados, asignados y comprendidos.'),
 ('3.2', 'El almacenamiento de datos de cuentas se mantiene al mínimo'),
 ('3.2.1',
  'Se minimiza el almacenamiento mediante políticas y procesos que incluyen:\n'
  '\n'
  '- Cobertura de todas las ubicaciones donde se almacenan datos.\n'
  '- Cobertura de datos de autenticación sensibles (SAD) antes de autorización.\n'
  '- Limitación del almacenamiento y retención según requisitos legales o de negocio.\n'
  '- Definición de periodos de retención con justificación documentada.\n'
  '- Eliminación segura o irrecuperabilidad cuando ya no se necesiten.\n'
  '- Verificación al menos trimestral de eliminación de datos fuera del periodo de retención.\n'
  '\n'
  'Notas:\n'
  'Aplica también a proveedores (ej. nube).\n'
  'El control de SAD previo a autorización será obligatorio desde 31 marzo 2025.'),
 ('3.3', 'Los datos de autenticación sensibles (SAD) no se almacenan después de la autorización'),
 ('3.3.1',
  'El SAD no se almacena después de la autorización, incluso si está cifrado. Todos los datos de autenticación '
  'sensibles recibidos se vuelven irrecuperables una vez finalizado el proceso de autorización.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  '\n'
  'Los emisores y entidades que apoyan servicios de emisión, cuando exista una necesidad legítima y documentada, '
  'pueden estar exentos.\n'
  'Ver Requisito 3.3.3.\n'
  'SAD incluye los datos definidos en 3.3.1.1 a 3.3.1.3.'),
 ('3.3.1.1',
  'El contenido completo de cualquier track no se almacena después de la autorización.\n'
  '\n'
  'Notas:\n'
  'Se pueden conservar únicamente:\n'
  '\n'
  '- Nombre del titular\n'
  '- PAN\n'
  '- Fecha de expiración\n'
  '- Código de servicio'),
 ('3.3.1.2', 'El código de verificación (CVV) no se almacena.'),
 ('3.3.1.3', 'El PIN ni el bloque PIN se almacenan.'),
 ('3.3.2',
  'Si el SAD se almacena antes de la autorización:\n'
  '\n'
  'Debe cifrarse con criptografía fuerte.\n'
  '\n'
  'Notas:\n'
  '\n'
  '- Aplica incluso si no hay PAN.\n'
  '- Será obligatorio desde 31 marzo 2025.'),
 ('3.3.3',
  '(Solo emisores)\n'
  'El almacenamiento de SAD:\n'
  '\n'
  '- Debe limitarse a lo necesario.\n'
  '- Debe estar protegido.\n'
  '- Debe cifrarse con criptografía fuerte.'),
 ('3.4', 'El acceso al PAN completo y su copia están restringidos'),
 ('3.4.1', 'El PAN se muestra enmascarado:\n\nMáximo BIN + últimos 4 dígitos'),
 ('3.4.2', 'Tecnologías de acceso remoto impiden copiar o mover PAN sin autorización.'),
 ('3.5', 'El PAN está protegido donde sea almacenado'),
 ('3.5.1',
  'El PAN se vuelve ilegible mediante:\n\n- Hash criptográfico\n- Truncamiento\n- Tokenización\n- Cifrado fuerte'),
 ('3.5.1.1',
  'Los hashes utilizados para hacer ilegible el PAN (según el primer punto del Requisito 3.5.1) son hashes '
  'criptográficos con clave (keyed hashes) de todo el PAN, con procesos y procedimientos de gestión de claves '
  'asociados de acuerdo con los Requisitos 3.6 y 3.7.'),
 ('3.5.1.2',
  'Si se utiliza cifrado a nivel de disco o de partición (en lugar de cifrado a nivel de archivo, columna o campo en '
  'base de datos) para hacer ilegible el PAN, se implementa únicamente de la siguiente manera:\n'
  '\n'
  '- En medios electrónicos removibles,\n'
  'O\n'
  '- Si se utiliza en medios electrónicos no removibles, el PAN también se hace ilegible mediante otro mecanismo que '
  'cumpla con el Requisito 3.5.1.\n'
  '\n'
  'Nota: Las implementaciones de cifrado a nivel de disco o partición también deben cumplir con todos los demás '
  'requisitos de cifrado y gestión de claves de PCI DSS. and key-management requirements. \n'
  'For issuers and companies that support issuing services: This requirement does not apply to PANs being accessed '
  'for real-time transaction processing. However, it does apply to PANs stored for other purposes.\n'
  'This requirement is a best practice until 31 March 2025, after which it will be required and must be fully '
  'considered during a PCI DSS assessment.'),
 ('3.5.1.3',
  'Si se utiliza cifrado a nivel de disco o de partición (en lugar de cifrado a nivel de archivo, columna o campo de '
  'base de datos) para hacer ilegible el PAN, se gestiona de la siguiente manera:\n'
  '\n'
  '- El acceso lógico se gestiona de forma separada e independiente de los mecanismos nativos de autenticación y '
  'control de acceso del sistema operativo.\n'
  '- Las claves de descifrado no están asociadas a cuentas de usuario.\n'
  '- Los factores de autenticación (contraseñas, frases de paso o claves criptográficas) que permiten el acceso a '
  'datos no cifrados se almacenan de forma segura.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Las implementaciones de cifrado a nivel de disco o partición también deben cumplir con todos los demás requisitos '
  'de cifrado y gestión de claves de PCI DSS.'),
 ('3.6', 'Las claves criptográficas utilizadas para proteger los datos de cuentas almacenados están protegidas'),
 ('3.6.1',
  'Se definen e implementan procedimientos para proteger las claves criptográficas utilizadas para proteger los '
  'datos de cuentas almacenados contra divulgación y uso indebido, que incluyen:\n'
  '\n'
  '- El acceso a las claves está restringido al menor número de custodios necesario.\n'
  '- Las claves de cifrado de claves (key-encrypting keys) son al menos tan fuertes como las claves de cifrado de '
  'datos que protegen.\n'
  '- Las claves de cifrado de claves se almacenan separadas de las claves de cifrado de datos.\n'
  '- Las claves se almacenan de forma segura en el menor número posible de ubicaciones y formatos.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito aplica a:\n'
  '\n'
  '- Claves utilizadas para proteger datos almacenados\n'
  '- Claves que protegen otras claves\n'
  '\n'
  'Debido a que una clave de cifrado de claves puede dar acceso a múltiples claves de datos, estas requieren '
  'controles de protección más fuertes.'),
 ('3.6.1.1',
  '(Solo proveedores de servicio)\n'
  '\n'
  'Se mantiene una descripción documentada de la arquitectura criptográfica que incluye:\n'
  '\n'
  '- Detalles de algoritmos, protocolos y claves, incluyendo fuerza y expiración.\n'
  '- Prevención del uso de las mismas claves en producción y pruebas (buena práctica hasta 31 marzo 2025).\n'
  '- Uso de cada clave.\n'
  '- Inventario de HSM, KMS y dispositivos criptográficos seguros (SCD), incluyendo tipo y ubicación.\n'
  '\n'
  'Notas:\n'
  '\n'
  '- Aplica solo a proveedores de servicio.\n'
  '- En nube, la responsabilidad es compartida proveedor/cliente.'),
 ('3.6.1.2',
  'Las claves secretas y privadas se almacenan en una o más de las siguientes formas:\n'
  '\n'
  '- Cifradas con una clave de cifrado de claves igual o más fuerte.\n'
  '- Dentro de un dispositivo criptográfico seguro (HSM o equivalente).\n'
  '- Como componentes o fragmentos completos según estándar reconocido.\n'
  '\n'
  'Notas:\n'
  '\n'
  '- No aplica a claves públicas.\n'
  '- Claves en KMS con HSM son válidas.\n'
  '- Dividir una clave en dos partes simples NO cumple.\n'
  '- Generación debe hacerse mediante:\n'
  '- Generador aleatorio aprobado + SCD,\n'
  'O\n'
  '- ISO 19592 o equivalente.'),
 ('3.6.1.3', 'El acceso a componentes de claves en texto claro se restringe al menor número de custodios necesario.'),
 ('3.6.1.4', 'Las claves criptográficas se almacenan en el menor número posible de ubicaciones.'),
 ('3.7',
  'Cuando se utiliza criptografía para proteger los datos de cuentas almacenados, se definen e implementan procesos '
  'y procedimientos de gestión de claves que cubren todos los aspectos del ciclo de vida de las claves.'),
 ('3.7.1',
  'Se implementan políticas y procedimientos de gestión de claves para incluir la generación de claves '
  'criptográficas fuertes utilizadas para proteger los datos de cuentas almacenados.'),
 ('3.7.2',
  'Se implementan políticas y procedimientos de gestión de claves para incluir la distribución segura de claves '
  'criptográficas utilizadas para proteger los datos de cuentas almacenados.'),
 ('3.7.3',
  'Se implementan políticas y procedimientos de gestión de claves para incluir el almacenamiento seguro de claves '
  'criptográficas utilizadas para proteger los datos de cuentas almacenados.'),
 ('3.7.4',
  'Se implementan políticas y procedimientos de gestión de claves para los cambios de claves criptográficas que han '
  'alcanzado el final de su criptoperiodo, según lo definido por el proveedor de la aplicación o el propietario de '
  'la clave correspondiente, y con base en las mejores prácticas y lineamientos de la industria, incluyendo lo '
  'siguiente:\n'
  '\n'
  '- Un criptoperiodo definido para cada tipo de clave en uso.\n'
  '- Un proceso para el cambio de claves al final del criptoperiodo definido.'),
 ('3.7.5',
  'Se implementan políticas y procedimientos de gestión de claves para incluir el retiro, reemplazo o destrucción de '
  'las claves utilizadas para proteger los datos de cuentas almacenados, según corresponda cuando:\n'
  '\n'
  '- La clave ha alcanzado el final de su criptoperiodo definido.\n'
  '- La integridad de la clave se ha debilitado, incluyendo cuando el personal con conocimiento de un componente de '
  'clave en texto claro deja la organización o cambia el rol para el cual conocía dicho componente.\n'
  '- Se sospecha o se confirma que la clave ha sido comprometida.\n'
  '\n'
  '- Las claves retiradas o reemplazadas no se utilizan para operaciones de cifrado.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Si las claves criptográficas retiradas o reemplazadas necesitan conservarse, deben archivarse de forma segura '
  '(por ejemplo, utilizando una clave de cifrado de claves).'),
 ('3.7.6',
  'Cuando las operaciones manuales de gestión de claves criptográficas en texto claro son realizadas por personal, '
  'se implementan políticas y procedimientos de gestión de claves que incluyen la gestión de estas operaciones '
  'mediante conocimiento dividido (split knowledge) y control dual.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este control aplica a operaciones manuales de gestión de claves.\n'
  '\n'
  '- Una clave criptográfica que simplemente se divide en dos partes no cumple con este requisito. Las claves '
  'secretas o privadas almacenadas como componentes o fragmentos deben generarse mediante uno de los siguientes '
  'métodos:\n'
  '\n'
  '- Utilizando un generador de números aleatorios aprobado y dentro de un dispositivo criptográfico seguro (SCD), '
  'como un módulo de seguridad hardware (HSM) o un dispositivo de interacción aprobado por PTS,\n'
  'O\n'
  '- De acuerdo con ISO 19592 o un estándar equivalente de la industria para la generación de fragmentos de claves '
  'secretas.'),
 ('3.7.7',
  'Se implementan políticas y procedimientos de gestión de claves para incluir la prevención de la sustitución no '
  'autorizada de claves criptográficas.'),
 ('3.7.8',
  'Se implementan políticas y procedimientos de gestión de claves para incluir que los custodios de claves '
  'criptográficas reconozcan formalmente (por escrito o electrónicamente) que entienden y aceptan sus '
  'responsabilidades como custodios de claves.'),
 ('3.7.9',
  '(Requisito adicional solo para proveedores de servicios):\n'
  'Cuando un proveedor de servicios comparte claves criptográficas con sus clientes para la transmisión o '
  'almacenamiento de datos de cuentas, se documenta y distribuye a los clientes del proveedor una guía sobre la '
  'transmisión, almacenamiento y actualización segura de dichas claves.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito aplica únicamente cuando la entidad evaluada es un proveedor de servicios.'),
 ('4.1', 'Los procesos y mecanismos para realizar las actividades del Requisito 4 están definidos y comprendidos.'),
 ('4.1.1',
  'Todas las políticas de seguridad y procedimientos operativos identificados en el Requisito 4 son:\n'
  '\n'
  '- Documentados\n'
  '- Mantenidos actualizados\n'
  '- En uso\n'
  '- Conocidos por todas las partes afectadas'),
 ('4.1.2',
  'Los roles y responsabilidades para realizar las actividades del Requisito 4 están documentados, asignados y '
  'comprendidos.'),
 ('4.2', 'El PAN está protegido con criptografía fuerte durante la transmisión.'),
 ('4.2.1',
  'Se implementan criptografía fuerte y protocolos de seguridad de la siguiente manera para proteger el PAN durante '
  'su transmisión a través de redes públicas abiertas:\n'
  '\n'
  'Solo se aceptan claves y certificados confiables.\n'
  'Los certificados utilizados para proteger el PAN durante la transmisión a través de redes públicas abiertas se '
  'confirman como válidos y no están expirados ni revocados. Este punto es una buena práctica hasta su fecha de '
  'entrada en vigor; consulte las notas de aplicabilidad a continuación para más detalles.\n'
  'El protocolo en uso solo admite versiones o configuraciones seguras y no permite retrocesos (fallback) ni el uso '
  'de versiones, algoritmos, tamaños de clave o implementaciones inseguras.\n'
  'La fortaleza del cifrado es adecuada para la metodología de cifrado utilizada.\n'
  '\n'
  'Notas de aplicabilidad\n'
  '\n'
  'Un certificado autofirmado puede ser aceptable si:\n'
  '\n'
  '- Es emitido por una autoridad certificadora interna de la organización,\n'
  '- Se confirma la autoría del certificado,\n'
  '- El certificado es verificado (por ejemplo, mediante hash o firma),\n'
  'Y no ha expirado.\n'
  '\n'
  'El punto anterior (validación de certificados) es una buena práctica hasta el 31 de marzo de 2025, después de lo '
  'cual será obligatorio como parte del Requisito 4.2.1 y deberá considerarse completamente en una evaluación PCI '
  'DSS.'),
 ('4.2.1.1',
  'Se mantiene un inventario de las claves y certificados confiables de la entidad.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025, después de lo cual será obligatorio y deberá '
  'considerarse completamente en una evaluación PCI DSS.'),
 ('4.2.1.2',
  'Las redes inalámbricas que transmiten PAN o están conectadas al CDE utilizan las mejores prácticas de la '
  'industria para implementar criptografía fuerte en la autenticación y transmisión.'),
 ('4.2.2',
  'El PAN se protege con criptografía fuerte siempre que se envía mediante tecnologías de mensajería de usuario '
  'final.\n'
  '\n'
  'Notas de aplicabilidad\n'
  '\n'
  'Este requisito también aplica cuando:\n'
  '\n'
  '- Un cliente u otro tercero solicita que el PAN sea enviado mediante tecnologías de mensajería de usuario final.\n'
  '\n'
  'Puede haber casos en los que una entidad reciba datos de tarjeta de forma no solicitada a través de un canal de '
  'comunicación inseguro que no fue diseñado para transmitir datos sensibles. En esta situación, la entidad puede:\n'
  '\n'
  '- Incluir el canal dentro del alcance de su CDE y asegurarlo conforme a PCI DSS,\n'
  'O\n'
  '- Eliminar los datos del titular de tarjeta e implementar controles para evitar que el canal vuelva a utilizarse '
  'para este propósito.'),
 ('5.1',
  'Los procesos y mecanismos para proteger todos los sistemas y redes contra software malicioso están definidos y '
  'comprendidos.'),
 ('5.1.1',
  'Todas las políticas de seguridad y procedimientos operativos identificados en el Requisito 5 son:\n'
  '\n'
  '- Documentados\n'
  '- Mantenidos actualizados\n'
  '- En uso\n'
  '- Conocidos por todas las partes afectadas'),
 ('5.1.2',
  'Los roles y responsabilidades para realizar las actividades del Requisito 5 están documentados, asignados y '
  'comprendidos.'),
 ('5.2', 'El software malicioso (malware) es prevenido, o detectado y gestionado.'),
 ('5.2.1',
  'Se implementa una o más soluciones anti-malware en todos los componentes del sistema, excepto en aquellos '
  'identificados mediante evaluaciones periódicas según el Requisito 5.2.3 que concluyan que dichos componentes no '
  'están en riesgo de malware.'),
 ('5.2.2',
  'Las soluciones anti-malware implementadas:\n'
  '\n'
  '- Detectan todos los tipos conocidos de malware.\n'
  '- Eliminan, bloquean o contienen todos los tipos conocidos de malware.'),
 ('5.2.3',
  'Los componentes del sistema que no están en riesgo de malware se evalúan periódicamente para incluir lo '
  'siguiente:\n'
  '\n'
  '- Una lista documentada de todos los componentes que no están en riesgo de malware.\n'
  '- Identificación y evaluación de amenazas de malware emergentes para dichos componentes.\n'
  '- Confirmación de que estos componentes continúan sin requerir protección anti-malware.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Aplica a componentes donde no se implementa anti-malware según 5.2.1.'),
 ('5.2.3.1',
  'La frecuencia de estas evaluaciones periódicas se define en el análisis de riesgos dirigido de la entidad, '
  'conforme al Requisito 12.3.1.\n'
  '\n'
  'Notas:\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025, después será obligatorio.'),
 ('5.3', 'Los mecanismos y procesos anti-malware están activos, mantenidos y monitoreados.'),
 ('5.3.1', 'Las soluciones anti-malware se mantienen actualizadas mediante actualizaciones automáticas.'),
 ('5.3.2',
  'Las soluciones anti-malware:\n'
  '\n'
  '- Realizan análisis periódicos y análisis activos o en tiempo real,\n'
  'O\n'
  '- Realizan análisis continuo del comportamiento de sistemas o procesos.'),
 ('5.3.2.1',
  'Si se realizan análisis periódicos, su frecuencia se define en el análisis de riesgos dirigido conforme al '
  'Requisito 12.3.1.\n'
  '\n'
  'Notas:\n'
  'Aplica a entidades que usan escaneos periódicos.\n'
  'Será obligatorio después del 31 de marzo de 2025.'),
 ('5.3.3',
  'Para medios electrónicos removibles, las soluciones anti-malware:\n'
  '\n'
  '- Realizan análisis automáticos cuando el medio es insertado, conectado o montado lógicamente,\n'
  'O\n'
  '- Realizan análisis continuo del comportamiento cuando el medio es insertado, conectado o montado.\n'
  '\n'
  'Notas:\n'
  'Este requisito será obligatorio después del 31 de marzo de 2025.'),
 ('5.3.4',
  'Los registros de auditoría de las soluciones anti-malware están habilitados y se conservan conforme al Requisito '
  '10.5.1.'),
 ('5.3.5',
  'Los mecanismos anti-malware no pueden ser deshabilitados o modificados por usuarios, salvo que esté documentado y '
  'autorizado por la gerencia de forma puntual y por un periodo limitado.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  '\n'
  '- Solo se permite deshabilitar temporalmente por necesidad técnica legítima.\n'
  '- Debe existir autorización formal.\n'
  '- Deben implementarse controles compensatorios durante ese periodo.'),
 ('5.4', 'Los mecanismos anti-phishing protegen a los usuarios contra ataques de phishing.'),
 ('5.4.1',
  'Se implementan procesos y mecanismos automatizados para detectar y proteger al personal contra ataques de '
  'phishing.\n'
  '\n'
  'Notas de aplicabilidad\n'
  '- Este requisito se enfoca en proteger al personal con acceso a sistemas dentro del alcance PCI DSS.\n'
  '- No reemplaza los requisitos de capacitación en concienciación de seguridad (Requisito 12.6.3.1).\n'
  '- Son controles complementarios, no equivalentes.\n'
  '\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025, después de lo cual será obligatorio y deberá '
  'ser considerado completamente en una evaluación PCI DSS.'),
 ('6.1',
  'Los procesos y mecanismos para desarrollar y mantener sistemas y software seguros están definidos y '
  'comprendidos.'),
 ('6.1.1',
  'Todas las políticas de seguridad y procedimientos operativos identificados en el Requisito 6 son:\n'
  '\n'
  '- Documentados.\n'
  '- Mantenidos actualizados.\n'
  '- En uso.\n'
  '- Conocidos por todas las partes afectadas.'),
 ('6.1.2',
  'Los roles y responsabilidades para realizar las actividades del Requisito 6 están documentados, asignados y '
  'comprendidos.\n'
  '\n'
  'Nuevo requisito – vigente inmediatamente'),
 ('6.2', 'El software propio y personalizado se desarrolla de forma segura.'),
 ('6.2.1',
  'El software propio y personalizado se desarrolla de forma segura, de la siguiente manera:\n'
  '\n'
  '- Basado en estándares de la industria y/o mejores prácticas de desarrollo seguro.\n'
  '- De acuerdo con PCI DSS (por ejemplo, autenticación segura y registros).\n'
  '- Incorporando la consideración de aspectos de seguridad de la información en cada etapa del ciclo de vida del '
  'desarrollo de software.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Aplica a todo software desarrollado por o para la entidad para su propio uso. No aplica a software de terceros.'),
 ('6.2.2',
  'El personal de desarrollo recibe capacitación al menos una vez cada 12 meses en:\n'
  '\n'
  '- Seguridad de software relevante a su función.\n'
  '- Diseño seguro y codificación segura.\n'
  '- Uso de herramientas de pruebas de seguridad (si aplica).\n'
  '\n'
  'Notas:\n'
  '\n'
  '- Aplica a revisiones de código.\n'
  '- Incluye aplicaciones internas y públicas.\n'
  '- Puede ser manual o automatizado.'),
 ('6.2.3',
  'El software se revisa antes de producción para identificar vulnerabilidades:\n'
  '\n'
  '- Cumplimiento de codificación segura.\n'
  '- Identificación de vulnerabilidades existentes y emergentes.\n'
  '- Correcciones aplicadas antes del despliegue.'),
 ('6.2.3.1',
  'Si se realizan revisiones manuales de código para software propio y personalizado antes de su liberación a '
  'producción, los cambios de código:\n'
  '\n'
  '- Son revisados por personas distintas al autor original del código y que poseen conocimientos en técnicas de '
  'revisión de código y prácticas de codificación segura.\n'
  '- Son revisados y aprobados por la gerencia antes de su liberación.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Las revisiones manuales de código pueden ser realizadas por personal interno con conocimientos o por terceros '
  'especializados.\n'
  'Una persona a la que se le haya asignado formalmente la responsabilidad del control de liberación y que no sea ni '
  'el autor original del código ni el revisor, cumple con el criterio de ser la gerencia.'),
 ('6.2.4',
  'Se definen y utilizan técnicas de ingeniería de software u otros métodos por parte del personal de desarrollo '
  'para prevenir o mitigar ataques comunes de software y vulnerabilidades relacionadas para software propio y '
  'personalizado, incluyendo, entre otros, los siguientes:\n'
  '\n'
  '- Ataques de inyección, incluyendo SQL, LDAP, XPath u otros comandos, parámetros, objetos, fallas o '
  'vulnerabilidades de tipo inyección.\n'
  '- Ataques sobre datos y estructuras de datos, incluyendo intentos de manipular buffers, punteros, datos de '
  'entrada o datos compartidos.\n'
  '- Ataques al uso de criptografía, incluyendo intentos de explotar implementaciones criptográficas débiles, '
  'inseguras o inapropiadas, algoritmos, suites de cifrado o modos de operación.\n'
  '- Ataques a la lógica de negocio, incluyendo intentos de abusar o eludir funcionalidades de la aplicación '
  'mediante la manipulación de APIs, protocolos y canales de comunicación, funcionalidades del lado del cliente u '
  'otras funciones y recursos del sistema/aplicación. Esto incluye cross-site scripting (XSS) y cross-site request '
  'forgery (CSRF).\n'
  '- Ataques a mecanismos de control de acceso, incluyendo intentos de evadir o abusar de mecanismos de '
  'identificación, autenticación o autorización, o de explotar debilidades en su implementación.\n'
  '- Ataques mediante cualquier vulnerabilidad de “alto riesgo” identificada en el proceso de identificación de '
  'vulnerabilidades, según lo definido en el Requisito 6.3.1.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Aplica a todo software desarrollado por o para la entidad para su propio uso. Incluye software propio y '
  'personalizado. No aplica a software de terceros.'),
 ('6.3', 'Las vulnerabilidades de seguridad son identificadas y gestionadas.'),
 ('6.3.1',
  'Las vulnerabilidades de seguridad se identifican y gestionan de la siguiente manera:\n'
  '\n'
  '- Las nuevas vulnerabilidades se identifican utilizando fuentes reconocidas por la industria, incluyendo alertas '
  'de equipos de respuesta a emergencias informáticas (CERT).\n'
  '- Las vulnerabilidades se clasifican según un nivel de riesgo basado en mejores prácticas de la industria y su '
  'impacto potencial.\n'
  '- Las clasificaciones de riesgo identifican, como mínimo, todas las vulnerabilidades consideradas de alto riesgo '
  'o críticas para el entorno.\n'
  '- Se cubren vulnerabilidades en software propio, personalizado y de terceros (por ejemplo, sistemas operativos y '
  'bases de datos).\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito es adicional a los escaneos de vulnerabilidades (Requisitos 11.3.1 y 11.3.2).\n'
  'Requiere monitoreo continuo de fuentes de vulnerabilidades y evaluación de riesgos por parte de la entidad.'),
 ('6.3.2',
  'Se mantiene un inventario de software propio, personalizado y de componentes de terceros integrados, para '
  'facilitar la gestión de vulnerabilidades y parches.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025, después de lo cual será obligatorio y deberá '
  'ser completamente considerado durante una evaluación PCI DSS.'),
 ('6.3.3',
  'Todos los componentes del sistema están protegidos contra vulnerabilidades conocidas mediante la instalación de '
  'parches o actualizaciones de seguridad, de la siguiente manera:\n'
  '\n'
  '- Los parches para vulnerabilidades críticas se instalan dentro de un mes desde su liberación.\n'
  '- Los demás parches se instalan dentro de un plazo apropiado según la evaluación de criticidad del riesgo '
  'realizada por la entidad conforme al Requisito 6.3.1.'),
 ('6.4', 'Las aplicaciones web públicas están protegidas contra ataques.'),
 ('6.4.1',
  'Para aplicaciones web públicas, se gestionan continuamente nuevas amenazas y vulnerabilidades, y se protegen '
  'contra ataques conocidos mediante:\n'
  '\n'
  '- Revisión mediante herramientas o métodos manuales o automatizados de evaluación de seguridad:\n'
  '   - Al menos una vez cada 12 meses y después de cambios significativos.\n'
  '   - Por una entidad especializada en seguridad de aplicaciones.\n'
  '   - Incluyendo, como mínimo, los ataques definidos en el Requisito 6.2.4.\n'
  '   - Todas las vulnerabilidades se clasifican según el Requisito 6.3.1.\n'
  '   - Todas las vulnerabilidades se corrigen.\n'
  '   - La aplicación se reevalúa después de las correcciones.\n'
  '\n'
  'O\n'
  '\n'
  '- Implementación de una solución técnica automatizada que:\n'
  '   - Se ubica frente a las aplicaciones web públicas.\n'
  '   - Detecta y previene ataques web.\n'
  '   - Está activa y actualizada.\n'
  '   - Genera registros de auditoría.\n'
  '   - Bloquea ataques o genera alertas para investigación inmediata.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'No equivale a escaneos de vulnerabilidades (Req. 11.3).\n'
  'Será reemplazado por el Requisito 6.4.2 después del 31 de marzo de 2025.'),
 ('6.4.2',
  'Para aplicaciones web de cara al público, se implementa una solución técnica automatizada que detecta y previene '
  'continuamente ataques basados en web, con al menos lo siguiente:\n'
  '\n'
  '- Está instalada frente a las aplicaciones web de cara al público y está configurada para detectar y prevenir '
  'ataques basados en web.\n'
  '- Está en ejecución activa y actualizada según corresponda.\n'
  '- Genera registros de auditoría.\n'
  '- Está configurada para bloquear ataques basados en web o generar una alerta que sea investigada de inmediato.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este nuevo requisito reemplazará al Requisito 6.4.1 una vez que entre en vigor su fecha efectiva.\n'
  '\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025, después de lo cual será obligatorio y deberá '
  'ser completamente considerado durante una evaluación PCI DSS.'),
 ('6.4.3',
  'Todos los scripts de páginas de pago que se cargan y ejecutan en el navegador del consumidor se gestionan de la '
  'siguiente manera:\n'
  '\n'
  '- Se implementa un método para confirmar que cada script está autorizado.\n'
  '- Se implementa un método para garantizar la integridad de cada script.\n'
  '- Se mantiene un inventario de todos los scripts con una justificación de negocio o técnica por escrito que '
  'explique por qué cada uno es necesario.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito aplica a todos los scripts cargados desde el entorno de la entidad y a los scripts cargados desde '
  'terceros y cuartos proveedores.\n'
  '\n'
  'Este requisito también aplica a scripts en las páginas web de la entidad que incluyen una página/formulario de '
  'pago embebido de un TPSP/procesador de pagos (por ejemplo, uno o más marcos en línea o iframes).\n'
  '\n'
  'Este requisito no aplica a una entidad para scripts en una página/formulario de pago embebido de un '
  'TPSP/procesador de pagos (por ejemplo, uno o más iframes), cuando la entidad incluye una página/formulario de '
  'pago de un TPSP/procesador de pagos en su sitio web.\n'
  '\n'
  'Los scripts en la página/formulario de pago embebido del TPSP/procesador de pagos son responsabilidad del '
  'TPSP/procesador de pagos para gestionarlos de acuerdo con este requisito.\n'
  '\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025, después de lo cual será obligatorio y deberá '
  'ser completamente considerado durante una evaluación PCI DSS.'),
 ('6.5', 'Los cambios a todos los componentes del sistema se gestionan de forma segura.'),
 ('6.5.1',
  'Los cambios a todos los componentes del sistema en el entorno de producción se realizan de acuerdo con '
  'procedimientos establecidos que incluyen:\n'
  '\n'
  '- Razón y descripción del cambio.\n'
  '- Documentación del impacto en la seguridad.\n'
  '- Aprobación documentada del cambio por partes autorizadas.\n'
  '- Pruebas para verificar que el cambio no afecte negativamente la seguridad del sistema.\n'
  '- Para cambios en software propio y personalizado, todas las actualizaciones se prueban para verificar el '
  'cumplimiento con el Requisito 6.2.4 antes de ser desplegadas en producción.\n'
  '- Procedimientos para abordar fallos y retornar a un estado seguro.'),
 ('6.5.2',
  'Tras la finalización de un cambio significativo, se confirma que todos los requisitos PCI DSS aplicables están '
  'implementados en todos los sistemas y redes nuevos o modificados, y la documentación se actualiza según '
  'corresponda.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Estos cambios significativos también deben ser capturados y reflejados en la actividad anual de confirmación del '
  'alcance PCI DSS de la entidad conforme al Requisito 12.5.2.'),
 ('6.5.3',
  'Los entornos de preproducción están separados de los entornos de producción y la separación se aplica mediante '
  'controles de acceso.'),
 ('6.5.4',
  'Los roles y funciones están separados entre los entornos de producción y preproducción para proporcionar '
  'responsabilidad, de modo que solo se desplieguen cambios revisados y aprobados?\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'En entornos con personal limitado donde los individuos desempeñan múltiples roles o funciones, este mismo '
  'objetivo puede lograrse mediante controles procedimentales adicionales que proporcionen responsabilidad. Por '
  'ejemplo, un desarrollador también puede ser un administrador que utiliza una cuenta de nivel administrador con '
  'privilegios elevados en el entorno de desarrollo y, para su rol de desarrollador, utiliza una cuenta separada con '
  'acceso a nivel de usuario en el entorno de producción.'),
 ('6.5.5',
  'Los PAN reales no se utilizan en entornos de preproducción, excepto cuando dichos entornos están incluidos dentro '
  'del CDE y protegidos de acuerdo con todos los requisitos PCI DSS aplicables?'),
 ('6.5.6',
  'Los datos de prueba y las cuentas de prueba se eliminan de los componentes del sistema antes de que el sistema '
  'pase a producción?'),
 ('7.1',
  'Los procesos y mecanismos para restringir el acceso a los componentes del sistema y a los datos de titulares de '
  'tarjeta según la necesidad de conocimiento del negocio están definidos y comprendidos.'),
 ('7.1.1',
  'Todas las políticas de seguridad y procedimientos operativos identificados en el Requisito 7 son:\n'
  '\n'
  '- Documentados,\n'
  '- Mantenidos actualizados,\n'
  '- En uso,\n'
  '- Conocidos por todas las partes afectadas.'),
 ('7.1.2',
  'Los roles y responsabilidades para realizar las actividades del Requisito 7 están documentados, asignados y '
  'comprendidos?'),
 ('7.2', 'El acceso a los componentes del sistema y a los datos está apropiadamente definido y asignado.'),
 ('7.2.1',
  'Se define un modelo de control de acceso que incluye la concesión de acceso de la siguiente manera:\n'
  '\n'
  '- Acceso apropiado según las necesidades del negocio y de acceso de la entidad.\n'
  '- Acceso a componentes del sistema y recursos de datos basado en la clasificación y funciones laborales de los '
  'usuarios.\n'
  '- Los privilegios mínimos necesarios (por ejemplo, usuario, administrador) para realizar una función laboral.'),
 ('7.2.2',
  'El acceso se asigna a los usuarios, incluyendo usuarios privilegiados, con base en:\n'
  '\n'
  '- Clasificación y función laboral.\n'
  '- Los privilegios mínimos necesarios para realizar sus responsabilidades.'),
 ('7.2.3', 'Los privilegios requeridos son aprobados por personal autorizado?'),
 ('7.2.4',
  'Todas las cuentas de usuario y privilegios de acceso asociados, incluyendo cuentas de terceros/proveedores, se '
  'revisan de la siguiente manera:\n'
  '\n'
  '- Al menos una vez cada seis meses\n'
  '- Para asegurar que las cuentas y accesos siguen siendo apropiados según la función laboral\n'
  '- Cualquier acceso inapropiado es corregido\n'
  '- La gerencia reconoce que el acceso sigue siendo apropiado\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito aplica a todas las cuentas de usuario y privilegios de acceso asociados, incluyendo:\n'
  '\n'
  '- Personal interno\n'
  '- Terceros/proveedores\n'
  '- Cuentas utilizadas para acceder a servicios en la nube de terceros\n'
  '\n'
  'Ver Requisitos 7.2.5, 7.2.5.1 y 8.6.1 a 8.6.3 para controles de cuentas de aplicaciones y sistemas.\n'
  '\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025, después de lo cual será obligatorio y deberá '
  'ser completamente considerado durante una evaluación PCI DSS.'),
 ('7.2.5',
  'Todas las cuentas de aplicaciones y sistemas y sus privilegios asociados se asignan y gestionan de la siguiente '
  'manera:\n'
  '\n'
  '- Basados en los privilegios mínimos necesarios para la operatividad del sistema o aplicación.\n'
  '- El acceso se limita a los sistemas, aplicaciones o procesos que específicamente requieren su uso.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025, después de lo cual será obligatorio.'),
 ('7.2.5.1',
  'Todo el acceso de cuentas de aplicaciones y sistemas y sus privilegios asociados se revisa de la siguiente '
  'manera:\n'
  '\n'
  '- Periódicamente (según la frecuencia definida en el análisis de riesgo dirigido de la entidad conforme al '
  'Requisito 12.3.1)\n'
  '- El acceso de la aplicación/sistema sigue siendo apropiado para la función que se realiza\n'
  '- Cualquier acceso inapropiado es corregido\n'
  'La gerencia reconoce que el acceso sigue siendo apropiado\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025, después de lo cual será obligatorio.'),
 ('7.2.6',
  'Todo el acceso de usuarios a repositorios de consulta de datos de titulares de tarjeta almacenados se restringe '
  'de la siguiente manera:\n'
  '\n'
  '- A través de aplicaciones u otros métodos programáticos, con acceso y acciones permitidas basadas en roles de '
  'usuario y privilegios mínimos\n'
  '- Solo los administradores responsables pueden acceder o consultar directamente los repositorios de datos de '
  'titulares de tarjeta almacenados (CHD)\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito aplica a controles de acceso para consultas de repositorios de datos de titulares de tarjeta '
  'almacenados.\n'
  '\n'
  'Ver Requisitos 7.2.5, 7.2.5.1 y 8.6.1 a 8.6.3 para controles de cuentas de aplicaciones y sistemas.'),
 ('7.3',
  'El acceso lógico a los componentes del sistema y a los datos se gestiona mediante sistemas de control de acceso.'),
 ('7.3.1',
  'Se implementa un sistema de control de acceso que restringe el acceso según la necesidad de conocimiento del '
  'usuario y cubre todos los componentes del sistema?'),
 ('7.3.2',
  'El sistema de control de acceso está configurado para aplicar los privilegios asignados a individuos, '
  'aplicaciones y sistemas según la clasificación y función laboral?'),
 ('7.3.3', 'El sistema de control de acceso está configurado con un enfoque de “denegar todo” por defecto?'),
 ('8.1', 'Los procesos y mecanismos para realizar las actividades del Requisito 8 están definidos y comprendidos.'),
 ('8.1.1',
  'Todas las políticas de seguridad y procedimientos operativos identificados en el Requisito 8 son:\n'
  '\n'
  '- Documentados.\n'
  '- Mantenidos actualizados.\n'
  '- En uso.\n'
  '- Conocidos por todas las partes afectadas.'),
 ('8.1.2',
  'Los roles y responsabilidades para realizar las actividades del Requisito 8 están documentados, asignados y '
  'comprendidos?'),
 ('8.2',
  'La identificación de usuarios y las cuentas relacionadas para usuarios y administradores se gestionan '
  'estrictamente a lo largo del ciclo de vida de la cuenta'),
 ('8.2.1',
  'A todos los usuarios se les asigna un identificador único (ID) antes de que se permita el acceso a los '
  'componentes del sistema o a los datos de titulares de tarjeta.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito no está destinado a aplicarse a cuentas de usuario en terminales de punto de venta (POS) que '
  'tienen acceso a un solo número de tarjeta a la vez para facilitar una única transacción.'),
 ('8.2.2',
  'Los identificadores de grupo, compartidos o genéricos, u otras credenciales de autenticación compartidas, solo se '
  'utilizan cuando sea necesario de manera excepcional, y se gestionan de la siguiente forma:\n'
  '\n'
  '- Se evita el uso del ID a menos que sea necesario para una circunstancia excepcional.\n'
  '- Su uso se limita al tiempo necesario para dicha circunstancia.\n'
  '- Se documenta la justificación de negocio para su uso.\n'
  '- Su uso es aprobado explícitamente por la gerencia.\n'
  '- La identidad del usuario individual se confirma antes de otorgar acceso a la cuenta.\n'
  '- Cada acción realizada es atribuible a un usuario individual.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito no está destinado a aplicarse a cuentas de usuario en terminales POS con acceso a un solo número '
  'de tarjeta por transacción.'),
 ('8.2.3',
  '(Requisito adicional solo para proveedores de servicios):\n'
  'Los proveedores de servicios con acceso remoto a instalaciones de clientes utilizan factores de autenticación '
  'únicos para cada instalación de cliente?\n'
  '\n'
  'Notas de aplicabilidad:\n'
  '\n'
  'Aplica solo cuando la entidad evaluada es un proveedor de servicios.\n'
  'No aplica a proveedores accediendo a sus propios entornos compartidos.\n'
  'Si empleados del proveedor usan factores compartidos, estos deben ser únicos por cliente y gestionados conforme '
  'al Requisito 8.2.2.'),
 ('8.2.4',
  'La adición, eliminación y modificación de IDs de usuario, factores de autenticación y otros objetos de '
  'identificación se gestionan de la siguiente manera:\n'
  '\n'
  '- Autorizados con la aprobación correspondiente.\n'
  '- Implementados únicamente con los privilegios especificados en la aprobación documentada.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Aplica a todas las cuentas de usuario, incluyendo empleados, contratistas, consultores, trabajadores temporales y '
  'proveedores externos.'),
 ('8.2.5', 'El acceso de usuarios terminados es revocado inmediatamente?'),
 ('8.2.6', 'Las cuentas de usuario inactivas se eliminan o deshabilitan dentro de los 90 días de inactividad?'),
 ('8.2.7',
  'Las cuentas utilizadas por terceros para acceder, dar soporte o mantener componentes del sistema mediante acceso '
  'remoto se gestionan de la siguiente manera:\n'
  '\n'
  '- Se habilitan únicamente durante el periodo necesario y se deshabilitan cuando no están en uso.\n'
  '- Su uso es monitoreado para detectar actividad inesperada.'),
 ('8.2.8',
  'Si una sesión de usuario ha estado inactiva durante más de 15 minutos, se requiere que el usuario vuelva a '
  'autenticarse para reactivar el terminal o la sesión?\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito no está destinado a aplicarse a cuentas en terminales POS que acceden a un solo número de tarjeta '
  'por transacción.\n'
  '\n'
  'Este requisito no pretende impedir actividades legítimas cuando la consola o el PC estén desatendidos.'),
 ('8.3', 'La autenticación fuerte para usuarios y administradores está establecida y gestionada.'),
 ('8.3.1',
  'Todo el acceso de usuarios a los componentes del sistema para usuarios y administradores se autentica mediante al '
  'menos uno de los siguientes factores de autenticación:\n'
  '\n'
  '- Algo que conoces, como una contraseña o frase de paso.\n'
  '- Algo que tienes, como un dispositivo token o una tarjeta inteligente.\n'
  '- Algo que eres, como un elemento biométrico.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito no está destinado a aplicarse a cuentas de usuario en terminales de punto de venta que tienen '
  'acceso a un solo número de tarjeta a la vez para facilitar una única transacción.\n'
  'Este requisito no reemplaza los requisitos de autenticación multifactor (MFA), sino que aplica a aquellos '
  'sistemas dentro del alcance que no están sujetos a MFA.\n'
  'Un certificado digital es una opción válida para “algo que tienes” si es único para un usuario en particular.'),
 ('8.3.2',
  'Se utiliza criptografía fuerte para hacer ilegibles todos los factores de autenticación durante la transmisión y '
  'el almacenamiento en todos los componentes del sistema.'),
 ('8.3.3', 'La identidad del usuario se verifica antes de modificar cualquier factor de autenticación.'),
 ('8.3.4',
  'Los intentos de autenticación inválidos se limitan mediante:\n'
  '\n'
  '- Bloqueo del ID de usuario después de no más de 10 intentos.\n'
  '- Establecer la duración del bloqueo en un mínimo de 30 minutos o hasta que se confirme la identidad del '
  'usuario.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito no está destinado a aplicarse a cuentas de usuario en terminales POS que tienen acceso a un solo '
  'número de tarjeta por transacción.'),
 ('8.3.5',
  'Si las contraseñas/frases de paso se utilizan como factores de autenticación para cumplir con el Requisito 8.3.1, '
  'se establecen y restablecen para cada usuario de la siguiente manera:\n'
  '\n'
  '- Se configuran con un valor único para el primer uso y al restablecerse.\n'
  '- Se obliga a cambiarlas inmediatamente después del primer uso.'),
 ('8.3.6',
  'Si las contraseñas/frases de paso se utilizan como factores de autenticación, deben cumplir el siguiente nivel '
  'mínimo de complejidad:\n'
  '\n'
  '- Longitud mínima de 12 caracteres (o, si el sistema no lo soporta, mínimo 8 caracteres).\n'
  '- Contener caracteres numéricos y alfabéticos.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito no aplica a:\n'
  '\n'
  '- Cuentas POS con acceso a un solo número de tarjeta por transacción.\n'
  '- Cuentas de aplicación o sistema (ver sección 8.6).\n'
  '\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025, después será obligatorio.\n'
  'Hasta esa fecha, las contraseñas deben tener mínimo 7 caracteres según PCI DSS v3.2.1.'),
 ('8.3.7',
  'No se permite reutilizar una contraseña/frase de paso igual a cualquiera de las últimas cuatro utilizadas?\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'No aplica a cuentas POS de un solo uso por transacción.'),
 ('8.3.8',
  'Las políticas y procedimientos de autenticación se documentan y comunican a todos los usuarios, incluyendo:\n'
  '\n'
  '- Guía para seleccionar factores de autenticación fuertes.\n'
  '- Guía para protegerlos.\n'
  '- Instrucciones de no reutilizar contraseñas.\n'
  '- Instrucciones para cambiar contraseñas en caso de compromiso y cómo reportarlo.'),
 ('8.3.9',
  'Si las contraseñas/frases de paso se utilizan como el único factor de autenticación para el acceso de usuarios '
  '(es decir, en cualquier implementación de autenticación de un solo factor), entonces:\n'
  '\n'
  '- Las contraseñas/frases de paso se cambian al menos una vez cada 90 días,\n'
  'O\n'
  '- La postura de seguridad de las cuentas se analiza dinámicamente y el acceso en tiempo real a los recursos se '
  'determina automáticamente en consecuencia.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito no aplica a componentes del sistema dentro del alcance donde se utiliza MFA.\n'
  'Este requisito no está destinado a aplicarse a cuentas de usuario en terminales de punto de venta que tienen '
  'acceso a un solo número de tarjeta a la vez para facilitar una única transacción.\n'
  'Este requisito no aplica a cuentas de clientes de proveedores de servicios, pero sí aplica a cuentas del personal '
  'del proveedor de servicios.'),
 ('8.3.10',
  'Requisito adicional solo para proveedores de servicios:\n'
  '\n'
  '- Si las contraseñas/frases de paso se utilizan como el único factor de autenticación para el acceso de usuarios '
  'clientes a datos de titulares de tarjeta (es decir, en cualquier implementación de autenticación de un solo '
  'factor), entonces se proporciona orientación a los usuarios clientes incluyendo:\n'
  '\n'
  '- Orientación para que los clientes cambien periódicamente sus contraseñas/frases de paso.\n'
  '- Orientación sobre cuándo y bajo qué circunstancias deben cambiarse las contraseñas/frases de paso.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito aplica solo cuando la entidad evaluada es un proveedor de servicios.\n'
  'Este requisito no aplica a cuentas de usuarios consumidores que acceden a su propia información de tarjeta de '
  'pago.\n'
  'Este requisito para proveedores de servicios será reemplazado por el Requisito 8.3.10.1 una vez que el 8.3.10.1 '
  'entre en vigor.'),
 ('8.3.10.1',
  'Requisito adicional solo para proveedores de servicios:\n'
  '\n'
  'Si las contraseñas/frases de paso se utilizan como el único factor de autenticación para el acceso de usuarios '
  'clientes (es decir, en cualquier implementación de autenticación de un solo factor), entonces:\n'
  '\n'
  '- Las contraseñas/frases de paso se cambian al menos una vez cada 90 días,\n'
  'O\n'
  '- La postura de seguridad de las cuentas se analiza dinámicamente y el acceso en tiempo real a los recursos se '
  'determina automáticamente en consecuencia.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito aplica solo cuando la entidad evaluada es un proveedor de servicios.\n'
  'Este requisito no aplica a cuentas de usuarios consumidores que acceden a su propia información de tarjeta de '
  'pago.\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025, después de lo cual será obligatorio y deberá '
  'ser completamente considerado durante una evaluación PCI DSS.\n'
  'Hasta que este requisito entre en vigor el 31 de marzo de 2025, los proveedores de servicios pueden cumplir ya '
  'sea el Requisito 8.3.10 o el 8.3.10.1.'),
 ('8.3.11',
  'Cuando se utilizan factores de autenticación como tokens de seguridad físicos o lógicos, tarjetas inteligentes o '
  'certificados:\n'
  '\n'
  '- Los factores se asignan a un usuario individual y no se comparten entre múltiples usuarios.\n'
  '- Los controles físicos y/o lógicos garantizan que solo el usuario previsto pueda usar ese factor para obtener '
  'acceso.'),
 ('8.4', 'Los sistemas de autenticación multifactor (MFA) están configurados para prevenir el uso indebido.'),
 ('8.4.1',
  'Se implementa MFA para todo acceso no por consola al CDE para el personal con acceso administrativo?\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'El requisito de MFA para acceso administrativo no por consola aplica a todo el personal con privilegios elevados '
  'o aumentados que accede al CDE mediante una conexión no por consola, es decir, mediante acceso lógico que ocurre '
  'a través de una interfaz de red en lugar de una conexión física directa.'),
 ('8.4.2',
  'Se implementa MFA para todo acceso no por consola al CDE?\n'
  '\n'
  'Notas de aplicabilidad:\n'
  '\n'
  'Este requisito no aplica a:\n'
  '\n'
  'Cuentas de aplicaciones o sistemas que realizan funciones automatizadas.\n'
  'Cuentas de usuario en terminales de punto de venta que tienen acceso a un solo número de tarjeta a la vez para '
  'facilitar una única transacción.\n'
  'Cuentas de usuario que solo están autenticadas con factores de autenticación resistentes a phishing.\n'
  '\n'
  'Se requiere MFA para ambos tipos de acceso especificados en los Requisitos 8.4.2 y 8.4.3. Por lo tanto, aplicar '
  'MFA a un tipo de acceso no reemplaza la necesidad de aplicar otra instancia de MFA al otro tipo de acceso. Si un '
  'individuo primero se conecta a la red de la entidad mediante acceso remoto y luego inicia una conexión al CDE '
  'desde dentro de la red, según este requisito el individuo deberá autenticarse usando MFA dos veces, una al '
  'conectarse remotamente a la red de la entidad y otra al conectarse desde la red de la entidad al CDE.\n'
  '\n'
  'Los requisitos de MFA aplican a todos los tipos de componentes del sistema, incluyendo nube, sistemas alojados, '
  'aplicaciones on-premise, dispositivos de seguridad de red, estaciones de trabajo, servidores y endpoints, e '
  'incluyen acceso directo a las redes o sistemas de una entidad, así como acceso basado en web a una aplicación o '
  'función.\n'
  '\n'
  'MFA para el acceso al CDE puede implementarse a nivel de red o de sistema/aplicación; no tiene que aplicarse en '
  'ambos niveles. Por ejemplo, si se utiliza MFA cuando un usuario se conecta a la red del CDE, no tiene que '
  'utilizarse cuando el usuario inicia sesión en cada sistema o aplicación dentro del CDE.\n'
  '\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025, después de lo cual será obligatorio y deberá '
  'ser completamente considerado durante una evaluación PCI DSS.'),
 ('8.4.3',
  'Se implementa MFA para todo acceso remoto de red originado desde fuera de la red de la entidad que pueda acceder '
  'o impactar el CDE?\n'
  '\n'
  'Notas de aplicabilidad:\n'
  '\n'
  'El requisito de MFA para acceso remoto desde fuera de la red de la entidad aplica a todas las cuentas de usuario '
  'que pueden acceder remotamente a la red, cuando dicho acceso remoto conduce o puede conducir a acceso al CDE. '
  'Esto incluye todo acceso remoto por parte de personal (usuarios y administradores) y terceros (incluyendo, pero '
  'no limitado a, proveedores, suministradores, prestadores de servicios y clientes).\n'
  '\n'
  'Si el acceso remoto es a una parte de la red de la entidad que está correctamente segmentada del CDE, de manera '
  'que los usuarios remotos no pueden acceder ni impactar el CDE, no se requiere MFA para ese acceso remoto. Sin '
  'embargo, MFA es requerido para cualquier acceso remoto a redes con acceso al CDE y se recomienda para todo acceso '
  'remoto a las redes de la entidad.\n'
  '\n'
  'Los requisitos de MFA aplican a todos los tipos de componentes del sistema, incluyendo nube, sistemas alojados, '
  'aplicaciones on-premise, dispositivos de seguridad de red, estaciones de trabajo, servidores y endpoints, e '
  'incluyen acceso directo a las redes o sistemas de una entidad así como acceso basado en web a una aplicación o '
  'función.'),
 ('8.5', 'La autenticación multifactor se implementa para asegurar el acceso al CDE.'),
 ('8.5.1',
  'Los sistemas MFA se implementan de la siguiente manera:\n'
  '\n'
  '- El sistema MFA no es susceptible a ataques de repetición (replay attacks).\n'
  '- Los sistemas MFA no pueden ser eludidos por ningún usuario, incluyendo usuarios administrativos, a menos que '
  'esté específicamente documentado y autorizado por la gerencia en base a excepciones y por un periodo limitado.\n'
  '- Se utilizan al menos dos tipos diferentes de factores de autenticación.\n'
  '- Se requiere el éxito de todos los factores de autenticación antes de otorgar acceso.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025, después de lo cual será obligatorio y deberá '
  'ser completamente considerado durante una evaluación PCI DSS.'),
 ('8.6',
  'El uso de cuentas de aplicaciones y sistemas y los factores de autenticación asociados se gestionan '
  'estrictamente.'),
 ('8.6.1',
  'Si las cuentas utilizadas por sistemas o aplicaciones pueden ser usadas para inicio de sesión interactivo, se '
  'gestionan de la siguiente manera:\n'
  '\n'
  '- El uso interactivo se evita salvo que sea necesario para una circunstancia excepcional.\n'
  '- El uso interactivo se limita al tiempo necesario para dicha circunstancia.\n'
  '- Se documenta la justificación de negocio.\n'
  '- El uso interactivo es aprobado explícitamente por la gerencia.\n'
  '- La identidad del usuario individual se confirma antes de otorgar acceso a la cuenta.\n'
  '- Cada acción realizada es atribuible a un usuario individual.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025, después de lo cual será obligatorio y deberá '
  'ser completamente considerado durante una evaluación PCI DSS.'),
 ('8.6.2',
  'Las contraseñas/frases de paso para cualquier cuenta de aplicación o sistema que pueda ser utilizada para inicio '
  'de sesión interactivo no están codificadas de forma rígida (hardcoded) en scripts, archivos de '
  'configuración/propiedades o código fuente propio o personalizado?\n'
  '\n'
  'Nota: Las contraseñas almacenadas deben estar cifradas conforme al Requisito 8.3.2.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Las contraseñas almacenadas deben estar cifradas conforme al Requisito 8.3.2.\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025, después de lo cual será obligatorio y deberá '
  'ser completamente considerado durante una evaluación PCI DSS.'),
 ('8.6.3',
  'Las contraseñas/frases de paso para cuentas de aplicaciones y sistemas están protegidas contra uso indebido de la '
  'siguiente manera:\n'
  '\n'
  '- Se cambian periódicamente (según el análisis de riesgo dirigido conforme al Requisito 12.3.1) y cuando exista '
  'sospecha o confirmación de compromiso.\n'
  '- Se construyen con complejidad suficiente acorde a la frecuencia de cambio.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025, después de lo cual será obligatorio y deberá '
  'ser completamente considerado durante una evaluación PCI DSS.'),
 ('9.1', 'Los procesos y mecanismos para realizar las actividades del Requisito 9 están definidos y comprendidos.'),
 ('9.1.1',
  'Todas las políticas de seguridad y procedimientos operativos identificados en el Requisito 9 son:\n'
  '\n'
  '- Documentados.\n'
  '- Mantenidos actualizados.\n'
  '- En uso.\n'
  '- Conocidos por todas las partes afectadas.'),
 ('9.1.2',
  'Los roles y responsabilidades para realizar las actividades del Requisito 9 están documentados, asignados y '
  'comprendidos?'),
 ('9.2', 'Los controles de acceso físico gestionan la entrada al entorno de datos de titulares de tarjeta (CDE).'),
 ('9.2.1',
  'Se implementan controles adecuados de acceso a instalaciones para restringir el acceso físico a los sistemas '
  'dentro del CDE?\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito no aplica a ubicaciones que sean accesibles públicamente por consumidores (titulares de tarjeta).'),
 ('9.2.1.1',
  'El acceso físico individual a áreas sensibles dentro del CDE es monitoreado mediante cámaras de video o '
  'mecanismos de control de acceso físico (o ambos) de la siguiente manera:\n'
  '\n'
  '- Los puntos de entrada y salida hacia/desde áreas sensibles dentro del CDE son monitoreados.\n'
  '- Los dispositivos o mecanismos de monitoreo están protegidos contra manipulación o desactivación.\n'
  '- Los datos recopilados son revisados y correlacionados con otros registros.\n'
  '- Los datos recopilados se almacenan durante al menos tres meses, salvo restricción legal.'),
 ('9.2.2',
  'Se implementan controles físicos y/o lógicos para restringir el uso de puntos de red accesibles públicamente '
  'dentro de la instalación?'),
 ('9.2.3',
  'El acceso físico a puntos de acceso inalámbricos, gateways, hardware de red/comunicaciones y líneas de '
  'telecomunicaciones dentro de la instalación está restringido?'),
 ('9.2.4', 'El acceso a consolas en áreas sensibles está restringido mediante bloqueo cuando no están en uso?'),
 ('9.3', 'El acceso físico al CDE para personal y visitantes es autorizado y gestionado.'),
 ('9.3.1',
  'Se implementan procedimientos para autorizar y gestionar el acceso físico del personal al CDE, incluyendo:\n'
  '\n'
  '- Identificación del personal.\n'
  '- Gestión de cambios en los requisitos de acceso físico individual.\n'
  '- Revocación o terminación de identificaciones de personal.\n'
  '- Limitación del acceso al proceso o sistema de identificación solo a personal autorizado.'),
 ('9.3.1.1',
  'El acceso físico a áreas sensibles dentro del CDE para el personal se controla de la siguiente manera:\n'
  '\n'
  '- El acceso es autorizado y basado en la función laboral individual.\n'
  '- El acceso es revocado inmediatamente tras la terminación.\n'
  '- Todos los mecanismos de acceso físico (llaves, tarjetas, etc.) son devueltos o deshabilitados tras la '
  'terminación.'),
 ('9.3.2',
  'Se implementan procedimientos para autorizar y gestionar el acceso de visitantes al CDE, incluyendo:\n'
  '\n'
  '- Los visitantes son autorizados antes de ingresar.\n'
  '- Los visitantes son acompañados en todo momento.\n'
  '- Los visitantes son claramente identificados y reciben una credencial o identificación con expiración.\n'
  '- Las credenciales de visitantes distinguen visualmente a los visitantes del personal.'),
 ('9.3.3',
  'Las credenciales de visitantes son devueltas o desactivadas antes de que los visitantes abandonen la instalación '
  'o en la fecha de expiración?'),
 ('9.3.4',
  'Se utilizan registros de visitantes para mantener un registro físico de la actividad, incluyendo:\n'
  '\n'
  '- Nombre del visitante y organización representada.\n'
  '- Fecha y hora de la visita.\n'
  '- Nombre del personal que autorizó el acceso.\n'
  '- Retención del registro por al menos tres meses, salvo restricción legal.'),
 ('9.4',
  'Los medios con datos de titulares de tarjeta se almacenan, acceden, distribuyen y destruyen de forma segura.'),
 ('9.4.1', 'Todos los medios con datos de titulares de tarjeta están físicamente protegidos?'),
 ('9.4.1.1',
  'Las copias de respaldo fuera de línea con datos de titulares de tarjeta se almacenan en ubicaciones seguras?'),
 ('9.4.1.2', 'La seguridad de las ubicaciones de respaldo fuera de línea se revisa al menos una vez cada 12 meses?'),
 ('9.4.2', 'Todos los medios con datos de titulares de tarjeta se clasifican según la sensibilidad de los datos?'),
 ('9.4.3',
  'Los medios enviados fuera de la instalación se protegen de la siguiente manera:\n'
  '\n'
  '- Se registra el envío.\n'
  '- Se utiliza mensajería segura o métodos rastreables.\n'
  '- Se mantiene registro de ubicación del medio.'),
 ('9.4.4',
  'La gerencia aprueba todos los medios con datos de titulares de tarjeta que se trasladan fuera de la instalación?\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'La aprobación debe ser realizada por personal con autoridad adecuada, sin necesidad de que el cargo sea “gerente” '
  'formalmente.'),
 ('9.4.5', 'Se mantienen inventarios de todos los medios electrónicos con datos de titulares de tarjeta?'),
 ('9.4.5.1',
  'Se realizan inventarios de los medios electrónicos con datos de titulares de tarjeta al menos una vez cada 12 '
  'meses?'),
 ('9.4.6',
  'Los materiales en formato físico (hard-copy) con datos de titulares de tarjeta se destruyen cuando ya no son '
  'necesarios por razones de negocio o legales, de la siguiente manera:\n'
  '\n'
  '- Los materiales se trituran con corte cruzado, se incineran o se convierten en pulpa, de forma que los datos de '
  'titulares de tarjeta no puedan ser reconstruidos.\n'
  '- Los materiales se almacenan en contenedores de almacenamiento seguros antes de su destrucción.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Estos requisitos para la destrucción de medios cuando dichos medios ya no son necesarios por razones de negocio o '
  'legales son separados y distintos del Requisito 3.2.1 de PCI DSS, el cual trata sobre la eliminación segura de '
  'datos de titulares de tarjeta cuando ya no son necesarios según las políticas de retención de datos de la '
  'entidad.'),
 ('9.4.7',
  'Los medios electrónicos con datos de titulares de tarjeta se destruyen cuando ya no son necesarios por razones de '
  'negocio o legales mediante uno de los siguientes métodos:\n'
  '\n'
  '- El medio electrónico es destruido.\n'
  '- Los datos de titulares de tarjeta se vuelven irrecuperables de modo que no puedan ser reconstruidos.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Estos requisitos para la destrucción de medios cuando dichos medios ya no son necesarios por razones de negocio o '
  'legales son separados y distintos del Requisito 3.2.1 de PCI DSS, el cual trata sobre la eliminación segura de '
  'datos de titulares de tarjeta cuando ya no son necesarios según las políticas de retención de datos de la '
  'entidad.'),
 ('9.5',
  'Los dispositivos de punto de interacción (POI) están protegidos contra manipulación y sustitución no autorizada.'),
 ('9.5.1',
  'Los dispositivos POI que capturan datos de tarjetas de pago mediante interacción física directa con el factor de '
  'forma de la tarjeta están protegidos contra manipulación y sustitución no autorizada, incluyendo lo siguiente:\n'
  '\n'
  '- Mantener una lista de dispositivos POI.\n'
  '- Inspeccionar periódicamente los dispositivos POI para detectar manipulación o sustitución no autorizada.\n'
  '- Capacitar al personal para que esté atento a comportamientos sospechosos y para reportar la manipulación o '
  'sustitución no autorizada de dispositivos.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Estos requisitos aplican a dispositivos POI desplegados utilizados en transacciones con tarjeta presente (es '
  'decir, cuando el factor de forma de la tarjeta es una tarjeta que se desliza, se aproxima o se inserta).\n'
  '\n'
  'Estos requisitos no aplican a:\n'
  '\n'
  '- Componentes utilizados únicamente para la entrada manual del PAN.\n'
  '- Dispositivos comerciales estándar (COTS), por ejemplo, teléfonos inteligentes o tabletas, que son dispositivos '
  'móviles propiedad del comerciante diseñados para distribución masiva.'),
 ('9.5.1.1',
  'Se mantiene una lista actualizada de dispositivos POI, que incluye:\n'
  '\n'
  '- Marca y modelo del dispositivo.\n'
  '- Ubicación del dispositivo.\n'
  '- Número de serie del dispositivo u otros métodos de identificación única.'),
 ('9.5.1.2',
  'Las superficies de los dispositivos POI se inspeccionan periódicamente para detectar manipulación y sustitución '
  'no autorizada?'),
 ('9.5.1.2.1',
  'La frecuencia de las inspecciones periódicas de los dispositivos POI y el tipo de inspecciones realizadas se '
  'define en el análisis de riesgo dirigido de la entidad, el cual se realiza conforme a todos los elementos '
  'especificados en el Requisito 12.3.1.?\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025, después de lo cual será obligatorio y deberá '
  'ser completamente considerado durante una evaluación PCI DSS.'),
 ('9.5.1.3',
  'Se proporciona capacitación al personal en entornos POI para que esté atento a intentos de manipulación o '
  'sustitución de dispositivos POI, e incluye:\n'
  '\n'
  '- Verificar la identidad de cualquier persona externa que afirme ser personal de reparación o mantenimiento antes '
  'de otorgarle acceso para modificar o solucionar problemas en los dispositivos.\n'
  '- Procedimientos para asegurar que los dispositivos no sean instalados, reemplazados o devueltos sin '
  'verificación.\n'
  '- Estar atento a comportamientos sospechosos alrededor de los dispositivos.\n'
  '- Reportar comportamientos sospechosos e indicaciones de manipulación o sustitución de dispositivos al personal '
  'correspondiente.'),
 ('10.1', 'Los procesos y mecanismos para realizar las actividades del Requisito 10 están definidos y comprendidos.'),
 ('10.1.1',
  'Todas las políticas de seguridad y procedimientos operativos identificados en el Requisito 10 son:\n'
  '\n'
  '- Documentados.\n'
  '- Mantenidos actualizados.\n'
  'En uso.\n'
  '- Conocidos por todas las partes afectadas.'),
 ('10.1.2',
  'Los roles y responsabilidades para realizar las actividades del Requisito 10 están documentados, asignados y '
  'comprendidos?'),
 ('10.2',
  'Los registros de auditoría se implementan para apoyar la detección de anomalías y actividad sospechosa, y el '
  'análisis forense de eventos.'),
 ('10.2.1',
  'Los registros de auditoría están habilitados y activos para todos los componentes del sistema y los datos de '
  'titulares de tarjeta?'),
 ('10.2.1.1',
  'Los registros de auditoría capturan todo acceso individual de usuario a los datos de titulares de tarjeta?'),
 ('10.2.1.2',
  'Los registros de auditoría capturan todas las acciones realizadas por cualquier individuo con acceso '
  'administrativo, incluyendo cualquier uso interactivo de cuentas de aplicación o sistema?'),
 ('10.2.1.3', 'Los registros de auditoría capturan todo acceso a los registros de auditoría?'),
 ('10.2.1.4', 'Los registros de auditoría capturan todos los intentos inválidos de acceso lógico?'),
 ('10.2.1.5',
  'Los registros de auditoría capturan todos los cambios en credenciales de identificación y autenticación '
  'incluyendo, pero no limitados a:\n'
  '\n'
  '- Creación de nuevas cuentas.\n'
  '- Elevación de privilegios.\n'
  '- Todos los cambios, adiciones o eliminaciones en cuentas con acceso administrativo.'),
 ('10.2.1.6',
  'Los registros de auditoría capturan lo siguiente:\n'
  '\n'
  '- Toda inicialización de nuevos registros de auditoría, y\n'
  '- Todo inicio, detención o pausa de los registros de auditoría existentes.'),
 ('10.2.1.7', 'Los registros de auditoría capturan toda creación y eliminación de objetos a nivel de sistema?'),
 ('10.2.2',
  'Los registros de auditoría registran los siguientes detalles para cada evento auditable:\n'
  '\n'
  '- Identificación del usuario.\n'
  '- Tipo de evento.\n'
  '- Fecha y hora.\n'
  '- Indicación de éxito o fallo.\n'
  '- Origen del evento.\n'
  '- Identidad o nombre de los datos, componente del sistema, recurso o servicio afectado (por ejemplo, nombre y '
  'protocolo).'),
 ('10.3', 'Los registros de auditoría están protegidos contra destrucción y modificaciones no autorizadas.'),
 ('10.3.1',
  'El acceso de lectura a los archivos de registros de auditoría está limitado a aquellos con una necesidad '
  'relacionada con su función laboral?'),
 ('10.3.2',
  'Los archivos de registros de auditoría están protegidos para prevenir modificaciones por parte de individuos?'),
 ('10.3.3',
  'Los archivos de registros de auditoría, incluyendo aquellos de tecnologías expuestas externamente, se respaldan '
  'oportunamente en un servidor central interno seguro de registros u otros medios que sean difíciles de modificar?'),
 ('10.3.4',
  'Se utilizan mecanismos de monitoreo de integridad de archivos o detección de cambios sobre los registros de '
  'auditoría para asegurar que los datos existentes no puedan ser modificados sin generar alertas?'),
 ('10.4', 'Los registros de auditoría son revisados para identificar anomalías o actividad sospechosa.'),
 ('10.4.1',
  'Los siguientes registros de auditoría se revisan al menos una vez al día:\n'
  '\n'
  '- Todos los eventos de seguridad.\n'
  '- Registros de todos los componentes del sistema que almacenan, procesan o transmiten CHD y/o SAD.\n'
  '- Registros de todos los componentes críticos del sistema.\n'
  '- Registros de todos los servidores y componentes que realizan funciones de seguridad (por ejemplo, controles de '
  'seguridad de red, sistemas IDS/IPS, servidores de autenticación).'),
 ('10.4.1.1',
  'Se utilizan mecanismos automatizados para realizar la revisión de los registros de auditoría?\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025, después de lo cual será obligatorio y deberá '
  'ser completamente considerado durante una evaluación PCI DSS.'),
 ('10.4.2',
  'Los registros de todos los demás componentes del sistema (no especificados en el Requisito 10.4.1) se revisan '
  'periódicamente?\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Aplica a todos los demás componentes dentro del alcance no incluidos en 10.4.1.'),
 ('10.4.2.1',
  'La frecuencia de revisión periódica de estos registros se define en el análisis de riesgo dirigido de la entidad, '
  'conforme al Requisito 12.3.1.?\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025, después de lo cual será obligatorio y deberá '
  'ser completamente considerado durante una evaluación PCI DSS.'),
 ('10.4.3', 'Las excepciones y anomalías identificadas durante el proceso de revisión son abordadas?'),
 ('10.5', 'El historial de registros de auditoría se conserva y está disponible para análisis.'),
 ('10.5.1',
  'Se conserva el historial de registros de auditoría por al menos 12 meses, con al menos los últimos tres meses '
  'disponibles inmediatamente para análisis?'),
 ('10.6',
  'Los mecanismos de sincronización de tiempo soportan configuraciones de tiempo consistentes en todos los '
  'sistemas.'),
 ('10.6.1',
  'Los relojes del sistema y el tiempo se sincronizan utilizando tecnología de sincronización de tiempo?\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Mantener esta tecnología actualizada incluye la gestión de vulnerabilidades y parches conforme a los Requisitos '
  '6.3.1 y 6.3.3.'),
 ('10.6.2',
  'Los sistemas están configurados con hora correcta y consistente de la siguiente manera:\n'
  '\n'
  '- Se utilizan uno o más servidores de tiempo designados.\n'
  '- Solo los servidores centrales designados reciben tiempo de fuentes externas.\n'
  '- El tiempo recibido se basa en Tiempo Atómico Internacional o UTC.\n'
  '- Los servidores de tiempo solo aceptan actualizaciones de fuentes externas aprobadas.\n'
  '- Si hay más de un servidor, estos se sincronizan entre sí.\n'
  '- Los sistemas internos reciben tiempo solo de servidores centrales designados.'),
 ('10.6.3',
  'La configuración y datos de sincronización de tiempo están protegidos de la siguiente manera:\n'
  '\n'
  '- El acceso está restringido solo a personal con necesidad de negocio.\n'
  '- Los cambios en sistemas críticos son registrados, monitoreados y revisados- .'),
 ('10.7',
  'Las fallas de los sistemas de control de seguridad críticos son detectadas, reportadas y atendidas '
  'oportunamente.'),
 ('10.7.1',
  '(Solo proveedores de servicios)\n'
  '\n'
  'Las fallas de los controles críticos son detectadas, alertadas y atendidas rápidamente, incluyendo:\n'
  '\n'
  '- Controles de seguridad de red\n'
  '- IDS/IPS\n'
  '- FIM\n'
  '- Anti-malware\n'
  '- Controles de acceso físico\n'
  '- Controles de acceso lógico\n'
  '- Registros de auditoría\n'
  '- Controles de segmentación\n'
  '\n'
  'Notas:\n'
  'Aplica solo a proveedores de servicio.\n'
  'Será reemplazado por 10.7.2.'),
 ('10.7.2',
  'Las fallas de los sistemas de control de seguridad críticos son detectadas, alertadas y atendidas rápidamente, '
  'incluyendo:\n'
  '\n'
  '- Controles de seguridad de red\n'
  '- IDS/IPS\n'
  '- Mecanismos de detección de cambios\n'
  '- Anti-malware\n'
  '- Controles físicos\n'
  '- Controles lógicos\n'
  '- Logs\n'
  '- Segmentación\n'
  '- Revisión de logs\n'
  '- Herramientas automáticas de seguridad\n'
  '\n'
  'Notas:\n'
  'Aplica a todas las entidades.\n'
  'Reemplaza 10.7.1.\n'
  'Es buena práctica hasta el 31 de marzo de 2025.'),
 ('10.7.3',
  'Las fallas de los sistemas críticos se gestionan incluyendo:\n'
  '\n'
  '- Restaurar funciones de seguridad\n'
  '- Documentar duración del incidente\n'
  '- Identificar causa\n'
  '- Aplicar remediación\n'
  '- Evaluar impactos\n'
  '- Implementar controles preventivos\n'
  '- Reanudar monitoreo\n'
  '\n'
  'Notas:\n'
  'Actualmente aplica solo a proveedores (v3.2.1), pero será obligatorio para todos.'),
 ('11.1', 'Los procesos y mecanismos para realizar las actividades del Requisito 11 están definidos y comprendidos.'),
 ('11.1.1',
  'Todas las políticas de seguridad y procedimientos operativos identificados en el Requisito 11 son:\n'
  '\n'
  '- Documentados.\n'
  '- Mantenidos actualizados.\n'
  '- En uso.\n'
  '- Conocidos por todas las partes afectadas.'),
 ('11.1.2',
  'Los roles y responsabilidades para realizar las actividades del Requisito 11 están documentados, asignados y '
  'comprendidos?'),
 ('11.2',
  'Los puntos de acceso inalámbricos son identificados y monitoreados, y los accesos inalámbricos no autorizados son '
  'gestionados.'),
 ('11.2.1',
  'Los puntos de acceso inalámbricos autorizados y no autorizados se gestionan de la siguiente manera:\n'
  '\n'
  '- Se prueba la presencia de puntos de acceso inalámbricos (Wi-Fi).\n'
  '- Se detectan e identifican todos los puntos de acceso inalámbricos autorizados y no autorizados.\n'
  '- Las pruebas, detección e identificación se realizan al menos una vez cada tres meses.\n'
  '- Si se utiliza monitoreo automatizado, el personal es notificado mediante alertas generadas.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito aplica incluso cuando existe una política que prohíbe el uso de tecnología inalámbrica.\n'
  'Los métodos utilizados deben ser suficientes para detectar e identificar tanto dispositivos autorizados como no '
  'autorizados, incluyendo dispositivos no autorizados conectados a dispositivos autorizados.'),
 ('11.2.2',
  'Se mantiene un inventario de puntos de acceso inalámbricos autorizados, incluyendo una justificación de negocio '
  'documentada?'),
 ('11.3', 'Las vulnerabilidades internas y externas son identificadas, priorizadas y gestionadas regularmente.'),
 ('11.3.1',
  'Los escaneos internos de vulnerabilidades se realizan de la siguiente manera:\n'
  '\n'
  '- Al menos una vez cada tres meses.\n'
  '- Las vulnerabilidades que sean de alto riesgo o críticas (según la clasificación de riesgos de vulnerabilidades '
  'de la entidad definida en el Requisito 6.3.1) se corrigen.\n'
  '- Se realizan reescaneos que confirman que todas las vulnerabilidades de alto riesgo y - todas las críticas (como '
  'se indicó anteriormente) han sido corregidas.\n'
  '- La herramienta de escaneo se mantiene actualizada con la información más reciente de vulnerabilidades.\n'
  '- Los escaneos son realizados por personal calificado y existe independencia organizacional del evaluador.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'No es obligatorio utilizar un QSA o ASV para realizar escaneos internos de vulnerabilidades.\n'
  'Los escaneos internos de vulnerabilidades pueden ser realizados por personal interno calificado que sea '
  'razonablemente independiente de los componentes del sistema que se están escaneando (por ejemplo, un '
  'administrador de red no debería ser responsable de escanear la red), o la entidad puede optar por que los '
  'escaneos internos sean realizados por una empresa especializada en escaneo de vulnerabilidades.'),
 ('11.3.1.1',
  'Todas las demás vulnerabilidades aplicables (aquellas que no están clasificadas como de alto riesgo o críticas '
  'según la clasificación de riesgos de vulnerabilidades de la entidad definida en el Requisito 6.3.1) se gestionan '
  'de la siguiente manera:\n'
  '\n'
  '- Se abordan con base en el riesgo definido en el análisis de riesgo dirigido de la entidad, el cual se realiza '
  'conforme a todos los elementos especificados en el Requisito 12.3.1.\n'
  '- Se realizan reescaneos según sea necesario.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'El plazo para abordar vulnerabilidades de menor riesgo está sujeto a los resultados de un análisis de riesgo '
  'según el Requisito 12.3.1 que incluye (como mínimo) la identificación de los activos protegidos, las amenazas y '
  'la probabilidad y/o impacto de que una amenaza se materialice.\n'
  '\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025, después de lo cual será obligatorio y deberá '
  'ser completamente considerado durante una evaluación PCI DSS.'),
 ('11.3.1.2',
  'Los escaneos internos de vulnerabilidades se realizan mediante escaneo autenticado de la siguiente manera:\n'
  '\n'
  '- Los sistemas que no pueden aceptar credenciales para escaneo autenticado están documentados.\n'
  '- Se utilizan privilegios suficientes para aquellos sistemas que aceptan credenciales para escaneo.\n'
  '- Si las cuentas utilizadas para escaneo autenticado pueden usarse para inicio de sesión interactivo, se '
  'gestionan de acuerdo con el Requisito 8.2.2.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Las herramientas de escaneo autenticado pueden ser basadas en host o en red.\n'
  '“Privilegios suficientes” son aquellos necesarios para acceder a los recursos del sistema de manera que se pueda '
  'realizar un escaneo completo que detecte vulnerabilidades conocidas.\n'
  '\n'
  'Este requisito no aplica a componentes del sistema que no pueden aceptar credenciales para escaneo. Ejemplos '
  'incluyen algunos dispositivos de red y seguridad, mainframes y contenedores.\n'
  '\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025, después de lo cual será obligatorio y deberá '
  'ser completamente considerado durante una evaluación PCI DSS.'),
 ('11.3.1.3',
  'Los escaneos internos de vulnerabilidades se realizan después de cualquier cambio significativo de la siguiente '
  'manera:\n'
  '\n'
  '- Las vulnerabilidades que sean de alto riesgo o críticas (según la clasificación de riesgos de vulnerabilidades '
  'de la entidad definida en el Requisito 6.3.1) se corrigen.\n'
  '- Se realizan reescaneos según sea necesario.\n'
  '- Los escaneos son realizados por personal calificado y existe independencia organizacional del evaluador (no es '
  'obligatorio que sea un QSA o ASV).\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'El escaneo interno autenticado de vulnerabilidades según el Requisito 11.3.1.2 no es obligatorio para escaneos '
  'realizados después de cambios significativos..'),
 ('11.3.2',
  'Los escaneos externos de vulnerabilidades se realizan de la siguiente manera:\n'
  '\n'
  '- Al menos una vez cada tres meses.\n'
  '- Por un proveedor de escaneo aprobado por PCI SSC (ASV).\n'
  '- Las vulnerabilidades se corrigen y se cumplen los requisitos de la Guía del Programa ASV para un escaneo '
  'aprobado.\n'
  '- Se realizan reescaneos según sea necesario para confirmar que las vulnerabilidades se han corregido conforme a '
  'la Guía del Programa ASV.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Para la evaluación inicial PCI DSS de este requisito, no es obligatorio que se hayan completado cuatro escaneos '
  'aprobados dentro de 12 meses si el evaluador verifica:\n'
  '\n'
  'que el resultado del escaneo más reciente fue aprobado,\n'
  'que la entidad tiene políticas y procedimientos documentados que requieren escaneos al menos cada tres meses, y\n'
  'que las vulnerabilidades detectadas en los resultados de escaneo han sido corregidas como se demuestra en '
  'reescaneos.\n'
  '\n'
  'Sin embargo, para años posteriores a la evaluación inicial PCI DSS, deben haberse realizado escaneos aprobados al '
  'menos cada tres meses.\n'
  '\n'
  'Las herramientas ASV pueden escanear una amplia variedad de redes y topologías. Cualquier especificidad del '
  'entorno objetivo (por ejemplo, balanceadores de carga, proveedores terceros, ISPs, configuraciones específicas, '
  'protocolos en uso, interferencias de escaneo) debe acordarse entre el ASV y el cliente.\n'
  '\n'
  'Consultar la Guía del Programa ASV publicada en el sitio web del PCI SSC para responsabilidades del cliente, '
  'preparación del escaneo, etc.'),
 ('11.3.2.1',
  'Los escaneos externos de vulnerabilidades se realizan después de cualquier cambio significativo de la siguiente '
  'manera:\n'
  '\n'
  '- Las vulnerabilidades con puntuación de 4.0 o superior según CVSS se corrigen.\n'
  '- Se realizan reescaneos según sea necesario.\n'
  '- Los escaneos son realizados por personal calificado y existe independencia organizacional del evaluador (no es '
  'obligatorio que sea un QSA o ASV).'),
 ('11.4',
  'Se realizan pruebas de penetración internas y externas regularmente, y las vulnerabilidades explotables y '
  'debilidades de seguridad se corrigen.'),
 ('11.4.1',
  'Se define, documenta e implementa una metodología de pruebas de penetración que incluye:\n'
  '\n'
  '- Enfoques de pruebas de penetración aceptados por la industria.\n'
  '- Cobertura de todo el perímetro del CDE y sistemas críticos.\n'
  '- Pruebas desde dentro y fuera de la red.\n'
  '- Pruebas para validar controles de segmentación y reducción de alcance.\n'
  '- Pruebas a nivel de aplicación para identificar, como mínimo, las vulnerabilidades del Requisito 6.2.4.\n'
  '- Pruebas a nivel de red que abarquen todos los componentes que soportan funciones de red y sistemas operativos.\n'
  '- Revisión de amenazas y vulnerabilidades de los últimos 12 meses.\n'
  '- Enfoque documentado para evaluar y gestionar riesgos.\n'
  '- Retención de resultados por al menos 12 meses.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Las pruebas internas implican evaluar desde dentro del CDE y redes internas.\n'
  'Las pruebas externas implican evaluar el perímetro expuesto y sistemas accesibles públicamente.'),
 ('11.4.2',
  'Las pruebas de penetración internas se realizan:\n'
  '\n'
  '- Según la metodología definida por la entidad.\n'
  '- Al menos una vez cada 12 meses.\n'
  '- Después de cualquier actualización o cambio significativo en la infraestructura o aplicación.\n'
  '- Por un recurso interno calificado o un tercero externo calificado.\n'
  '- Existe independencia organizacional del evaluador (no es obligatorio que sea un QSA o ASV).'),
 ('11.4.3',
  'Las pruebas de penetración externas se realizan:\n'
  '\n'
  '- Según la metodología definida por la entidad.\n'
  '- Al menos una vez cada 12 meses.\n'
  '- Después de cualquier actualización o cambio significativo en la infraestructura o aplicación.\n'
  '- Por un recurso interno calificado o un tercero externo calificado.\n'
  '- Existe independencia organizacional del evaluador (no es obligatorio que sea un QSA o ASV).'),
 ('11.4.4',
  'Las vulnerabilidades explotables y debilidades de seguridad encontradas durante las pruebas de penetración se '
  'corrigen de la siguiente manera:\n'
  '\n'
  '- De acuerdo con la evaluación de la entidad sobre el riesgo planteado por el problema de seguridad según lo '
  'definido en el Requisito 6.3.1.\n'
  '- Las pruebas de penetración se repiten para verificar las correcciones.'),
 ('11.4.5',
  'Si se utiliza segmentación para aislar el CDE de otras redes, se realizan pruebas de penetración sobre los '
  'controles de segmentación de la siguiente manera:\n'
  '\n'
  '- Al menos una vez cada 12 meses y después de cualquier cambio en los controles/métodos de segmentación.\n'
  '- Cubriendo todos los controles/métodos de segmentación en uso.\n'
  '- De acuerdo con la metodología de pruebas de penetración definida por la entidad.\n'
  '- Confirmando que los controles/métodos de segmentación son operacionales y efectivos, y aíslan el CDE de todos '
  'los sistemas fuera de alcance.\n'
  '- Confirmando la efectividad de cualquier uso de aislamiento para separar sistemas con diferentes niveles de '
  'seguridad (ver Requisito 2.2.3).\n'
  '- Realizadas por un recurso interno calificado o un tercero externo calificado.\n'
  '- Existe independencia organizacional del evaluador (no es obligatorio que sea un QSA o ASV).'),
 ('11.4.6',
  'Requisito adicional solo para proveedores de servicios:\n'
  '\n'
  'Si se utiliza segmentación para aislar el CDE de otras redes, se realizan pruebas de penetración sobre los '
  'controles de segmentación de la siguiente manera:\n'
  '\n'
  '- Al menos una vez cada seis meses y después de cualquier cambio en los controles/métodos de segmentación.\n'
  '- Cubriendo todos los controles/métodos de segmentación en uso.\n'
  '- De acuerdo con la metodología de pruebas de penetración definida por la entidad.\n'
  '- Confirmando que los controles/métodos de segmentación son operacionales y efectivos, y aíslan el CDE de todos '
  'los sistemas fuera de alcance.\n'
  '- Confirmando la efectividad de cualquier uso de aislamiento para separar sistemas con diferentes niveles de '
  'seguridad (ver Requisito 2.2.3).\n'
  '- Realizadas por un recurso interno calificado o un tercero externo calificado.\n'
  '- Existe independencia organizacional del evaluador (no es obligatorio que sea un QSA o ASV).\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito aplica únicamente cuando la entidad evaluada es un proveedor de servicios.'),
 ('11.4.7',
  'Requisito adicional solo para proveedores de servicios de hosting/cloud de terceros:\n'
  '\n'
  '- Los proveedores de servicios de hosting/cloud de terceros brindan soporte a sus clientes para pruebas de '
  'penetración externas según los Requisitos 11.4.3 y 11.4.4.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito aplica únicamente cuando la entidad evaluada es un proveedor de servicios multi-tenant.\n'
  '\n'
  'Para cumplir con este requisito, los proveedores multi-tenant pueden:\n'
  '\n'
  'Proporcionar evidencia a sus clientes que demuestre que las pruebas de penetración se han realizado conforme a '
  'los Requisitos 11.4.3 y 11.4.4 en la infraestructura suscrita por los clientes,\n'
  'O\n'
  'Proporcionar acceso oportuno a cada uno de sus clientes para que puedan realizar sus propias pruebas de '
  'penetración.\n'
  '\n'
  'La evidencia proporcionada a los clientes puede incluir resultados de pruebas de penetración redactados, pero '
  'debe incluir información suficiente para demostrar que todos los elementos de los Requisitos 11.4.3 y 11.4.4 se '
  'han cumplido en nombre del cliente.\n'
  '\n'
  'Consultar también el Apéndice A1: Requisitos adicionales de PCI DSS para proveedores de servicios multi-tenant.\n'
  '\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025, después de lo cual será obligatorio y deberá '
  'ser completamente considerado durante una evaluación PCI DSS.'),
 ('11.5', 'Las intrusiones de red y los cambios inesperados en archivos son detectados y respondidos.'),
 ('11.5.1',
  'Se utilizan técnicas de detección y/o prevención de intrusiones para detectar y/o prevenir intrusiones en la red '
  'de la siguiente manera:\n'
  '\n'
  '- Todo el tráfico es monitoreado en el perímetro del CDE.\n'
  '- Todo el tráfico es monitoreado en puntos críticos dentro del CDE.\n'
  '- El personal es alertado sobre posibles compromisos.\n'
  '- Todos los motores, líneas base y firmas de detección y prevención de intrusiones se mantienen actualizados.'),
 ('11.5.1.1',
  'Requisito adicional solo para proveedores de servicios:\n'
  '\n'
  '- Las técnicas de detección y/o prevención de intrusiones detectan, alertan sobre, previenen y gestionan canales '
  'encubiertos de comunicación de malware.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito aplica únicamente cuando la entidad evaluada es un proveedor de servicios.\n'
  '\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025, después de lo cual será obligatorio y deberá '
  'ser completamente considerado durante una evaluación PCI DSS.'),
 ('11.5.2',
  'Se implementa un mecanismo de detección de cambios (por ejemplo, herramientas de monitoreo de integridad de '
  'archivos) de la siguiente manera:\n'
  '\n'
  '- Para alertar al personal sobre modificaciones no autorizadas (incluyendo cambios, adiciones y eliminaciones) de '
  'archivos críticos.\n'
  '- Para realizar comparaciones de archivos críticos al menos una vez por semana.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Para propósitos de detección de cambios, los archivos críticos suelen ser aquellos que no cambian regularmente, '
  'pero cuya modificación podría indicar un compromiso del sistema o riesgo de compromiso.\n'
  '\n'
  'Los mecanismos de detección de cambios, como las herramientas de monitoreo de integridad de archivos, '
  'generalmente vienen preconfigurados con archivos críticos para el sistema operativo correspondiente.\n'
  '\n'
  'Otros archivos críticos, como los de aplicaciones personalizadas, deben ser evaluados y definidos por la entidad '
  '(es decir, el comerciante o proveedor de servicios).'),
 ('11.6', 'Los cambios no autorizados en páginas de pago son detectados y respondidos.'),
 ('11.6.1',
  'Se implementa un mecanismo de detección de cambios y manipulación de la siguiente manera:\n'
  '\n'
  '- Para alertar al personal sobre modificaciones no autorizadas (incluyendo indicadores de compromiso, cambios, '
  'adiciones y eliminaciones) en los encabezados HTTP que impactan la seguridad y en el contenido de los scripts de '
  'las páginas de pago tal como son recibidos por el navegador del consumidor.\n'
  '- El mecanismo está configurado para evaluar los encabezados HTTP y las páginas de pago recibidas.\n'
  '- Las funciones del mecanismo se realizan de la siguiente manera:\n'
  '- Al menos una vez por semana,\n'
  'O\n'
  '- Periódicamente (según la frecuencia definida en el análisis de riesgo dirigido de la entidad, realizado '
  'conforme al Requisito 12.3.1).\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito también aplica a entidades con páginas web que incluyen formularios/páginas de pago embebidas de '
  'un TPSP/procesador de pagos (por ejemplo, uno o más iframes).\n'
  '\n'
  'Este requisito no aplica a una entidad para scripts dentro de un formulario/página de pago embebida de un '
  'TPSP/procesador de pagos (por ejemplo, iframes), donde la entidad incluye el formulario/página de pago del TPSP '
  'en su sitio web.\n'
  '\n'
  'Los scripts en el formulario/página de pago embebida del TPSP/procesador de pagos son responsabilidad del '
  'TPSP/procesador de pagos de gestionar conforme a este requisito.\n'
  '\n'
  'La intención de este requisito no es que la entidad instale software en los sistemas o navegadores de sus '
  'consumidores, sino que la entidad utilice técnicas como las descritas en los Ejemplos de la Guía PCI DSS para '
  'prevenir y detectar actividades inesperadas de scripts.\n'
  '\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025, después de lo cual será obligatorio y deberá '
  'ser completamente considerado durante una evaluación PCI DSS.'),
 ('12.1',
  'Una política integral de seguridad de la información que gobierna y proporciona dirección para la protección de '
  'los activos de información de la entidad es conocida y está vigente.'),
 ('12.1.1',
  'Una política general de seguridad de la información es:\n'
  '\n'
  '- Establecida.\n'
  '- Publicada.\n'
  '- Mantenida.\n'
  '- Difundida a todo el personal relevante, así como a proveedores y socios comerciales relevantes.'),
 ('12.1.2',
  'La política de seguridad de la información es:\n'
  '\n'
  '- Revisada al menos una vez cada 12 meses.\n'
  '- Actualizada según sea necesario para reflejar cambios en los objetivos del negocio o riesgos del entorno.'),
 ('12.1.3',
  'La política de seguridad define claramente los roles y responsabilidades de seguridad de la información para todo '
  'el personal, y todo el personal está consciente y reconoce sus responsabilidades en materia de seguridad de la '
  'información?'),
 ('12.1.4',
  'La responsabilidad de la seguridad de la información se asigna formalmente a un Director de Seguridad de la '
  'Información (CISO) u otro miembro de la alta dirección con conocimiento en seguridad de la información?'),
 ('12.2', 'Las políticas de uso aceptable para tecnologías de usuario final están definidas e implementadas.'),
 ('12.2.1',
  'Las políticas de uso aceptable para tecnologías de usuario final están documentadas e implementadas, incluyendo:\n'
  '\n'
  '- Aprobación explícita por partes autorizadas.\n'
  '- Usos aceptables de la tecnología.\n'
  '- Lista de productos aprobados por la empresa para uso de los empleados, incluyendo hardware y software.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Ejemplos de tecnologías de usuario final para las cuales se esperan políticas de uso aceptable incluyen, pero no '
  'se limitan a, acceso remoto y tecnologías inalámbricas, portátiles, tabletas, teléfonos móviles y medios '
  'electrónicos removibles, uso de correo electrónico y uso de Internet.'),
 ('12.3',
  'Los riesgos dirigidos al entorno de datos de titulares de tarjeta son identificados, evaluados y gestionados '
  'formalmente.'),
 ('12.3.1',
  'Para cada requisito PCI DSS que especifica la realización de un análisis de riesgo dirigido, el análisis se '
  'documenta e incluye:\n'
  '\n'
  '- Identificación de los activos que se están protegiendo.\n'
  '- Identificación de las amenazas contra las cuales el requisito protege.\n'
  '- Identificación de los factores que contribuyen a la probabilidad y/o impacto de que una amenaza se '
  'materialice.\n'
  '- Análisis resultante que determina, e incluye justificación, de cómo la frecuencia o procesos definidos por la '
  'entidad para cumplir el requisito minimizan la probabilidad y/o impacto de que la amenaza se materialice.\n'
  '- Revisión de cada análisis de riesgo dirigido al menos una vez cada 12 meses para determinar si los resultados '
  'siguen siendo válidos o si se requiere una actualización.\n'
  '- Realización de análisis de riesgo actualizados cuando sea necesario, según lo determine la revisión anual.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025, después de lo cual será obligatorio y deberá '
  'ser completamente considerado durante una evaluación PCI DSS.'),
 ('12.3.2',
  'Se realiza un análisis de riesgo dirigido para cada requisito PCI DSS que la entidad cumple mediante el enfoque '
  'personalizado, incluyendo:\n'
  '\n'
  '- Evidencia documentada que detalle cada elemento especificado en el Apéndice B: Guía e instrucciones para el uso '
  'del enfoque personalizado (incluyendo, como mínimo, una matriz de controles y análisis de riesgo).\n'
  '- Aprobación de la evidencia documentada por la alta dirección.\n'
  '- Realización del análisis de riesgo dirigido al menos una vez cada 12 meses.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Esto aplica únicamente a entidades que utilizan un Enfoque Personalizado.'),
 ('12.3.3',
  'Las suites de cifrado criptográfico y protocolos en uso están documentados y se revisan al menos una vez cada 12 '
  'meses, incluyendo al menos lo siguiente:\n'
  '\n'
  '- Un inventario actualizado de todas las suites de cifrado y protocolos criptográficos en uso, incluyendo su '
  'propósito y dónde se utilizan.\n'
  '- Monitoreo activo de tendencias de la industria respecto a la viabilidad continua de todas las suites de cifrado '
  'y protocolos criptográficos en uso.\n'
  '- Documentación de un plan para responder a cambios anticipados en vulnerabilidades criptográficas.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito aplica a todas las suites de cifrado y protocolos utilizados para cumplir con PCI DSS, incluyendo, '
  'pero no limitado a, aquellos usados para hacer ilegible el PAN en almacenamiento y transmisión, para proteger '
  'contraseñas y como parte de la autenticación de acceso.\n'
  '\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025, después de lo cual será obligatorio y deberá '
  'ser completamente considerado durante una evaluación PCI DSS.'),
 ('12.3.4',
  'Las tecnologías de hardware y software en uso se revisan al menos una vez cada 12 meses, incluyendo al menos lo '
  'siguiente:\n'
  '\n'
  '- Análisis que verifique que las tecnologías continúan recibiendo correcciones de seguridad de los proveedores de '
  'manera oportuna.\n'
  '- Análisis que verifique que las tecnologías continúan soportando (y no impiden) el cumplimiento de PCI DSS de la '
  'entidad.\n'
  '- Documentación de cualquier anuncio o tendencia de la industria relacionada con una tecnología, como cuando un '
  'proveedor ha anunciado planes de “fin de vida” para una tecnología.\n'
  '- Documentación de un plan, aprobado por la alta dirección, para remediar tecnologías obsoletas, incluyendo '
  'aquellas para las cuales los proveedores han anunciado planes de “fin de vida”.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025, después de lo cual será obligatorio y deberá '
  'ser completamente considerado durante una evaluación PCI DSS.'),
 ('12.4', 'El cumplimiento de PCI DSS es gestionado.'),
 ('12.4.1',
  'Requisito adicional solo para proveedores de servicios:\n'
  '\n'
  '- La responsabilidad es establecida por la alta dirección para la protección de los datos de titulares de tarjeta '
  'y un programa de cumplimiento PCI DSS que incluye:\n'
  '- Responsabilidad general por mantener el cumplimiento de PCI DSS.\n'
  'Definir un marco (charter) para un programa de cumplimiento PCI DSS y su comunicación a la alta dirección.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito aplica únicamente cuando la entidad evaluada es un proveedor de servicios.\n'
  '\n'
  'La alta dirección puede incluir cargos de nivel C, junta directiva o equivalente. Los títulos específicos '
  'dependerán de la estructura organizacional.\n'
  '\n'
  'La responsabilidad del programa de cumplimiento PCI DSS puede asignarse a roles individuales y/o a unidades de '
  'negocio dentro de la organización.'),
 ('12.4.2',
  'Requisito adicional solo para proveedores de servicios:\n'
  '\n'
  '- Se realizan revisiones al menos una vez cada tres meses para confirmar que el personal está desempeñando sus '
  'tareas conforme a todas las políticas de seguridad y procedimientos operativos.\n'
  '- Las revisiones son realizadas por personal distinto al responsable de ejecutar las tareas e incluyen, pero no '
  'se limitan a, lo siguiente:\n'
  '- Revisiones diarias de logs.\n'
  '- Revisiones de configuración de controles de seguridad de red.\n'
  '- Aplicación de estándares de configuración a nuevos sistemas.\n'
  '- Respuesta a alertas de seguridad.\n'
  '- Procesos de gestión de cambios.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito aplica únicamente cuando la entidad evaluada es un proveedor de servicios.'),
 ('12.4.2.1',
  'Requisito adicional solo para proveedores de servicios:\n'
  '\n'
  '- Las revisiones realizadas conforme al Requisito 12.4.2 se documentan e incluyen:- \n'
  '- Resultados de las revisiones.\n'
  '- Acciones de remediación documentadas para tareas que no se realizaron conforme al Requisito 12.4.2.\n'
  '- Revisión y aprobación (firma) de los resultados por personal responsable del programa de cumplimiento PCI DSS.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito aplica únicamente cuando la entidad evaluada es un proveedor de servicios.'),
 ('12.5', 'El alcance de PCI DSS está documentado y validado.'),
 ('12.5.1',
  'Se mantiene y actualiza un inventario de los componentes del sistema dentro del alcance de PCI DSS, incluyendo '
  'una descripción de su función/uso?'),
 ('12.5.2',
  'El alcance de PCI DSS es documentado y confirmado por la entidad al menos una vez cada 12 meses y tras cambios '
  'significativos en el entorno dentro del alcance.\n'
  '\n'
  'Como mínimo, la validación del alcance incluye:\n'
  '\n'
  '- Identificar todos los flujos de datos en las distintas etapas del pago (por ejemplo, autorización, captura, '
  'liquidación, contracargos y reembolsos) y canales de aceptación (por ejemplo, tarjeta presente, tarjeta no '
  'presente y comercio electrónico).\n'
  '- Actualizar todos los diagramas de flujo de datos conforme al Requisito 1.2.4.\n'
  '- Identificar todas las ubicaciones donde los datos de cuenta se almacenan, procesan y transmiten, incluyendo '
  'pero no limitado a:\n'
  '  - ubicaciones fuera del CDE definido,\n'
  '  - aplicaciones que procesan CHD,\n'
  '  - transmisiones entre sistemas y redes,\n'
  '  - copias de respaldo.\n'
  '- Identificar todos los componentes del sistema en el CDE, conectados al CDE o que puedan afectar su seguridad.\n'
  '- Identificar todos los controles de segmentación y los entornos desde los cuales el CDE está segmentado, '
  'incluyendo justificación de entornos fuera de alcance.\n'
  '- Identificar todas las conexiones de terceros con acceso al CDE.\n'
  '- Confirmar que todos los flujos de datos, datos de cuenta, componentes, controles de segmentación y conexiones '
  'de terceros están incluidos en el alcance.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Esta confirmación anual del alcance PCI DSS es responsabilidad de la entidad evaluada y no sustituye la '
  'validación realizada por el evaluador.'),
 ('12.5.2.1',
  'Requisito adicional solo para proveedores de servicios:\n'
  '\n'
  'El alcance PCI DSS es documentado y confirmado al menos cada seis meses y tras cambios significativos.\n'
  'Incluye todos los elementos del Requisito 12.5.2.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Aplica solo a proveedores de servicios.\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025, después será obligatorio.'),
 ('12.5.3',
  'Requisito adicional solo para proveedores de servicios:\n'
  '\n'
  '- Cambios significativos en la estructura organizacional generan una revisión documentada del impacto sobre el '
  'alcance PCI DSS y la aplicabilidad de controles, comunicando resultados a la alta dirección.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Aplica solo a proveedores de servicios.\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025.'),
 ('12.6', 'La concienciación en seguridad es una actividad continua.'),
 ('12.6.1',
  'Se implementa un programa formal de concienciación en seguridad para que todo el personal conozca la política de '
  'seguridad de la información y su rol en la protección de los datos de titulares de tarjeta?'),
 ('12.6.2',
  'El programa de concienciación en seguridad es:\n'
  '\n'
  '- Revisado al menos una vez cada 12 meses.\n'
  '- Actualizado según sea necesario para abordar nuevas amenazas y vulnerabilidades que puedan afectar la seguridad '
  'de los datos de titulares de tarjeta y/o datos de autenticación sensibles, o la información proporcionada al '
  'personal.\n'
  '\n'
  'Notas de aplicabilidad:\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025.'),
 ('12.6.3',
  'El personal recibe capacitación en concienciación de seguridad de la siguiente manera:\n'
  '\n'
  '- Al momento de contratación y al menos una vez cada 12 meses.\n'
  '- Se utilizan múltiples métodos de comunicación.\n'
  '- El personal reconoce al menos una vez cada 12 meses que ha leído y entendido la política y procedimientos de '
  'seguridad de la información.'),
 ('12.6.3.1',
  'La capacitación en concienciación de seguridad incluye concienciación sobre amenazas y vulnerabilidades que '
  'podrían impactar la seguridad de los datos de titulares de tarjeta y/o datos de autenticación sensibles, '
  'incluyendo pero no limitado a:\n'
  '\n'
  '- Phishing y ataques relacionados.\n'
  '- Ingeniería social.\n'
  '\n'
  'Notas de aplicabilidad\n'
  'Ver el Requisito 5.4.1 para orientación sobre la diferencia entre controles técnicos y automatizados para '
  'detectar y proteger a los usuarios contra ataques de phishing, y este requisito para proporcionar capacitación de '
  'concienciación en seguridad a los usuarios sobre phishing e ingeniería social. Estos son dos requisitos separados '
  'y distintos, y uno no se cumple implementando los controles requeridos por el otro.\n'
  '\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025, después de lo cual será obligatorio y deberá '
  'ser completamente considerado durante una evaluación PCI DSS.'),
 ('12.6.3.2',
  'La capacitación en concienciación de seguridad incluye concienciación sobre el uso aceptable de tecnologías de '
  'usuario final de acuerdo con el Requisito 12.2.1?\n'
  '\n'
  'Notas de aplicabilidad\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025, después de lo cual será obligatorio y deberá '
  'ser completamente considerado durante una evaluación PCI DSS.'),
 ('12.7', 'El personal es evaluado para reducir los riesgos derivados de amenazas internas.'),
 ('12.7.1',
  'El personal potencial que tendrá acceso al CDE es evaluado, dentro de las restricciones de las leyes locales, '
  'antes de la contratación para minimizar el riesgo de ataques provenientes de fuentes internas?\n'
  '\n'
  'Notas de aplicabilidad\n'
  'Para el personal potencial que será contratado para posiciones como cajeros de tienda, que solo tienen acceso a '
  'un número de tarjeta a la vez al facilitar una transacción, este requisito es solo una recomendación.'),
 ('12.8',
  'El riesgo para los activos de información asociado con relaciones con proveedores de servicios de terceros (TPSP) '
  'es gestionado.'),
 ('12.8.2',
  'Se mantienen acuerdos escritos con los TPSP de la siguiente manera:\n'
  '\n'
  '- Se mantienen acuerdos escritos con todos los TPSP con los cuales se comparten datos de cuenta o que podrían '
  'afectar la seguridad del CDE.\n'
  '- Los acuerdos escritos incluyen reconocimientos por parte de los TPSP de que los TPSP son responsables de la '
  'seguridad de los datos de cuenta que poseen o que almacenan, procesan o transmiten en nombre de la entidad, o en '
  'la medida en que el TPSP pueda impactar la seguridad de los datos de titulares de tarjeta de la entidad y/o datos '
  'de autenticación sensibles.\n'
  '\n'
  'Notas de aplicabilidad\n'
  'La redacción exacta de un acuerdo dependerá de los detalles del servicio proporcionado y de las responsabilidades '
  'asignadas a cada parte. El acuerdo no tiene que incluir exactamente la redacción proporcionada en este '
  'requisito.\n'
  '\n'
  'El reconocimiento escrito del TPSP es una confirmación que establece que el TPSP es responsable de la seguridad '
  'de los datos de cuenta que pueda almacenar, procesar o transmitir en nombre del cliente o en la medida en que el '
  'TPSP pueda impactar la seguridad de los datos de titulares de tarjeta de un cliente y/o datos de autenticación '
  'sensibles.\n'
  '\n'
  'La evidencia de que un TPSP cumple con los requisitos PCI DSS no es lo mismo que el reconocimiento escrito '
  'especificado en este requisito. Por ejemplo, una Attestation of Compliance (AOC) de PCI DSS, una declaración en '
  'el sitio web de una empresa, una política, una matriz de responsabilidades u otra evidencia que no esté incluida '
  'en un acuerdo escrito no constituye un reconocimiento escrito.'),
 ('12.8.3',
  'Se implementa un proceso establecido para la contratación de TPSP, incluyendo la debida diligencia adecuada antes '
  'de la contratación?'),
 ('12.8.4',
  'Se implementa un programa para monitorear el estado de cumplimiento PCI DSS de los TPSP al menos una vez cada 12 '
  'meses?\n'
  '\n'
  'Notas de aplicabilidad\n'
  'Cuando una entidad tiene un acuerdo con un TPSP para cumplir requisitos PCI DSS en nombre de la entidad (por '
  'ejemplo, mediante un servicio de firewall), la entidad debe trabajar con el TPSP para asegurarse de que se '
  'cumplan los requisitos PCI DSS aplicables. Si el TPSP no cumple con esos requisitos aplicables, entonces dichos '
  'requisitos también se consideran “no implementados” para la entidad.'),
 ('12.8.5',
  'Se mantiene información sobre qué requisitos PCI DSS son gestionados por cada TPSP, cuáles son gestionados por la '
  'entidad y cuáles son compartidos entre el TPSP y la entidad?'),
 ('12.9', 'Los proveedores de servicios de terceros (TPSP) apoyan el cumplimiento PCI DSS de sus clientes.'),
 ('12.9.1',
  'Requisito adicional solo para proveedores de servicios:\n'
  '\n'
  'Los TPSP proporcionan acuerdos escritos a los clientes que incluyen reconocimientos de que los TPSP son '
  'responsables de la seguridad de los datos de cuenta que el TPSP posee o de otra manera almacena, procesa o '
  'transmite en nombre del cliente, o en la medida en que el TPSP pueda impactar la seguridad de los datos de '
  'titulares de tarjeta del cliente y/o datos de autenticación sensibles.\n'
  '\n'
  'Notas de aplicabilidad\n'
  'Este requisito aplica únicamente cuando la entidad evaluada es un proveedor de servicios.\n'
  '\n'
  'La redacción exacta de un acuerdo dependerá de los detalles del servicio que se esté proporcionando y de las '
  'responsabilidades asignadas a cada parte. El acuerdo no tiene que incluir exactamente la redacción proporcionada '
  'en este requisito.\n'
  '\n'
  'El reconocimiento escrito del TPSP es una confirmación que establece que el TPSP es responsable de la seguridad '
  'de los datos de cuenta que pueda almacenar, procesar o transmitir en nombre del cliente o en la medida en que el '
  'TPSP pueda impactar la seguridad de los datos de titulares de tarjeta de un cliente y/o datos de autenticación '
  'sensibles.\n'
  '\n'
  'La evidencia de que un TPSP cumple con los requisitos PCI DSS no es lo mismo que un acuerdo escrito especificado '
  'en este requisito. Por ejemplo, una Attestation of Compliance (AOC) de PCI DSS, una declaración en el sitio web '
  'de una empresa, una política, una matriz de responsabilidades u otra evidencia que no esté incluida en un acuerdo '
  'escrito no constituye un reconocimiento escrito.'),
 ('12.9.2',
  'Requisito adicional solo para proveedores de servicios:\n'
  '\n'
  'Los TPSP apoyan las solicitudes de información de sus clientes para cumplir con los Requisitos 12.8.4 y 12.8.5 '
  'proporcionando lo siguiente cuando el cliente lo solicite:\n'
  '\n'
  '- Información sobre el estado de cumplimiento PCI DSS (Requisito 12.8.4).\n'
  '- Información sobre qué requisitos PCI DSS son responsabilidad del TPSP y cuáles son responsabilidad del cliente, '
  'incluyendo cualquier responsabilidad compartida (Requisito 12.8.5), para cualquier servicio que el TPSP '
  'proporcione que cumpla un requisito PCI DSS en nombre de los clientes o que pueda impactar la seguridad de los '
  'datos de titulares de tarjeta de los clientes y/o datos de autenticación sensibles.\n'
  '\n'
  'Notas de aplicabilidad\n'
  'Este requisito aplica únicamente cuando la entidad evaluada es un proveedor de servicios.'),
 ('12.10',
  'Los incidentes de seguridad sospechosos y confirmados que podrían impactar el CDE son respondidos '
  'inmediatamente.'),
 ('12.10.1',
  'Existe un plan de respuesta a incidentes y está listo para activarse en caso de un incidente de seguridad '
  'sospechoso o confirmado. El plan incluye, pero no se limita a:\n'
  '\n'
  '- Roles, responsabilidades y estrategias de comunicación y contacto en caso de un incidente de seguridad '
  'sospechoso o confirmado, incluyendo notificación a las marcas de pago y adquirentes, como mínimo.\n'
  '- Procedimientos de respuesta a incidentes con actividades específicas de contención y mitigación para diferentes '
  'tipos de incidentes.\n'
  '- Procedimientos de recuperación y continuidad del negocio.\n'
  '- Procesos de respaldo de datos.\n'
  '- Análisis de requisitos legales para reportar compromisos de seguridad.\n'
  '- Cobertura y respuesta de todos los componentes críticos del sistema.\n'
  '- Referencia o inclusión de procedimientos de respuesta a incidentes de las marcas de pago.'),
 ('12.10.2',
  'Al menos una vez cada 12 meses, el plan de respuesta a incidentes de seguridad es:\n'
  '- Revisado y su contenido actualizado según sea necesario.\n'
  '- Probado, incluyendo todos los elementos listados en el Requisito 12.10.1.'),
 ('12.10.3',
  'Se designa personal específico para estar disponible las 24 horas del día, los 7 días de la semana, para '
  'responder a incidentes de seguridad sospechosos o confirmados?'),
 ('12.10.4',
  'El personal responsable de responder a incidentes de seguridad sospechosos y confirmados está capacitado de '
  'manera adecuada y periódica en sus responsabilidades de respuesta a incidentes?'),
 ('12.10.4.1',
  'La frecuencia de la capacitación periódica para el personal de respuesta a incidentes se define en el análisis de '
  'riesgo dirigido de la entidad, el cual se realiza conforme a todos los elementos especificados en el Requisito '
  '12.3.1.?\n'
  '\n'
  'Notas de aplicabilidad\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025, después de lo cual será obligatorio y deberá '
  'ser completamente considerado durante una evaluación PCI DSS.'),
 ('12.10.5',
  'El plan de respuesta a incidentes de seguridad incluye monitoreo y respuesta a alertas de sistemas de monitoreo '
  'de seguridad, incluyendo pero no limitado a:\n'
  '\n'
  '- Sistemas de detección y prevención de intrusiones.\n'
  '- Controles de seguridad de red.\n'
  '- Mecanismos de detección de cambios para archivos críticos.\n'
  '- El mecanismo de detección de cambios y manipulación para páginas de pago. Este punto es una buena práctica '
  'hasta su fecha de entrada en vigor; consultar las Notas de Aplicabilidad a continuación para más detalles.\n'
  '- Detección de puntos de acceso inalámbricos no autorizados.\n'
  '\n'
  'Notas de aplicabilidad\n'
  'El punto anterior (para el monitoreo y respuesta a alertas de un mecanismo de detección de cambios y manipulación '
  'para páginas de pago) es una buena práctica hasta el 31 de marzo de 2025, después de lo cual será obligatorio '
  'como parte del Requisito 12.10.5 y deberá ser completamente considerado durante una evaluación PCI DSS.'),
 ('12.10.6',
  'El plan de respuesta a incidentes de seguridad se modifica y evoluciona de acuerdo con las lecciones aprendidas y '
  'para incorporar desarrollos de la industria?'),
 ('12.10.7',
  'Existen procedimientos de respuesta a incidentes que se inician ante la detección de PAN almacenado en cualquier '
  'lugar donde no se espera, e incluyen:\n'
  '\n'
  '- Determinar qué hacer si se descubre PAN fuera del CDE, incluyendo su recuperación, eliminación segura y/o '
  'migración al CDE actualmente definido, según corresponda.\n'
  '- Identificar si los datos de autenticación sensibles están almacenados junto con el PAN.\n'
  '- Determinar de dónde provienen los datos de cuenta y cómo terminaron en un lugar donde no se esperaban.\n'
  '- Remediar fugas de datos o fallas de procesos que resultaron en que los datos de cuenta estuvieran donde no se '
  'esperaban.\n'
  '\n'
  'Notas de aplicabilidad\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025, después de lo cual será obligatorio y deberá '
  'ser completamente considerado durante una evaluación PCI DSS.'),
 ('A1.1',
  'Los proveedores de servicios multi-tenant protegen y segregan todos los entornos y datos de los clientes.'),
 ('A1.1.1',
  'La separación lógica se implementa de la siguiente manera:\n'
  '\n'
  '- El proveedor no puede acceder a los entornos de sus clientes sin autorización.\n'
  '- Los clientes no pueden acceder al entorno del proveedor sin autorización.\n'
  '\n'
  'Notas de aplicabilidad\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025, después de lo cual será obligatorio y deberá '
  'ser completamente considerado durante una evaluación PCI DSS.'),
 ('A1.1.2',
  'Se implementan controles de tal manera que cada cliente solo tenga permiso para acceder a sus propios datos de '
  'titulares de tarjeta y al CDE?'),
 ('A1.1.3',
  'Se implementan controles de tal manera que cada cliente solo pueda acceder a los recursos asignados a ellos?'),
 ('A1.1.4',
  'La efectividad de los controles de separación lógica utilizados para separar los entornos de los clientes se '
  'confirma al menos una vez cada seis meses mediante pruebas de penetración?\n'
  '\n'
  'Notas de aplicabilidad\n'
  'Las pruebas de separación adecuada entre clientes en un entorno de proveedor de servicios multi-tenant son '
  'adicionales a las pruebas de penetración especificadas en el Requisito 11.4.6.\n'
  '\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025, después de lo cual será obligatorio y deberá '
  'ser completamente considerado durante una evaluación PCI DSS.'),
 ('A1.2',
  'Los proveedores de servicios multi-tenant facilitan el registro y la respuesta a incidentes para todos los '
  'clientes.'),
 ('A1.2.1',
  'La capacidad de registros de auditoría está habilitada para el entorno de cada cliente de manera consistente con '
  'el Requisito 10 de PCI DSS, incluyendo:\n'
  '\n'
  '- Los registros están habilitados para aplicaciones comunes de terceros.\n'
  '- Los registros están activos por defecto.\n'
  '- Los registros están disponibles para revisión únicamente por el cliente propietario.\n'
  '- Las ubicaciones de los registros se comunican claramente al cliente propietario.\n'
  '- Los datos de registro y su disponibilidad son consistentes con el Requisito 10 de PCI DSS.'),
 ('A1.2.2',
  'Se implementan procesos o mecanismos para apoyar y/o facilitar investigaciones forenses oportunas en caso de un '
  'incidente de seguridad sospechoso o confirmado para cualquier cliente?'),
 ('A1.2.3',
  'Se implementan procesos o mecanismos para reportar y abordar incidentes de seguridad sospechosos o confirmados y '
  'vulnerabilidades, incluyendo:\n'
  '\n'
  '- Los clientes pueden reportar de manera segura incidentes de seguridad y vulnerabilidades al proveedor.\n'
  '- El proveedor aborda y remedia los incidentes de seguridad sospechosos o confirmados y las vulnerabilidades de '
  'acuerdo con el Requisito 6.3.1.\n'
  '\n'
  'Notas de aplicabilidad\n'
  'Este requisito es una buena práctica hasta el 31 de marzo de 2025, después de lo cual será obligatorio y deberá '
  'ser completamente considerado durante una evaluación PCI DSS.'),
 ('A2.1.1',
  'Cuando los terminales POS POI en el comercio o en la ubicación de aceptación de pagos utilizan SSL y/o TLS '
  'temprano, la entidad confirma que los dispositivos no son susceptibles a ningún exploit conocido para esos '
  'protocolos?\n'
  '\n'
  'Notas de aplicabilidad\n'
  'Este requisito está destinado a aplicarse a la entidad que posee el terminal POS POI, como un comerciante. Este '
  'requisito no está destinado a proveedores de servicios que actúan como punto de terminación o conexión para esos '
  'terminales POS POI. Los Requisitos A2.1.2 y A2.1.3 aplican a los proveedores de servicios de POS POI.\n'
  '\n'
  'La autorización para terminales POS POI que actualmente no son susceptibles a exploits se basa en los riesgos '
  'conocidos actualmente. Si se introducen nuevos exploits a los cuales los terminales POS POI sean susceptibles, '
  'los terminales POS POI deberán ser actualizados inmediatamente.'),
 ('A2.1.2',
  'Requisito adicional solo para proveedores de servicios:\n'
  '\n'
  'Todos los proveedores de servicios con puntos de conexión existentes a terminales POS POI que utilizan SSL y/o '
  'TLS temprano según lo definido en A2.1 deben contar con un Plan formal de Mitigación de Riesgos y Migración que '
  'incluya:\n'
  '\n'
  '- Descripción del uso, incluyendo qué datos se están transmitiendo, tipos y número de sistemas que utilizan y/o '
  'soportan SSL/TLS temprano, y tipo de entorno.\n'
  '- Resultados de la evaluación de riesgos y controles de reducción de riesgos implementados.\n'
  '- Descripción de los procesos para monitorear nuevas vulnerabilidades asociadas con SSL/TLS temprano.\n'
  '- Descripción de los procesos de control de cambios que se implementan para asegurar que SSL/TLS temprano no se '
  'implemente en nuevos entornos.\n'
  '- Resumen del plan del proyecto de migración para reemplazar SSL/TLS temprano en una fecha futura.\n'
  '\n'
  'Notas de aplicabilidad\n'
  'Este requisito aplica únicamente cuando la entidad evaluada es un proveedor de servicios.'),
 ('A2.1.3',
  'Requisito adicional solo para proveedores de servicios:\n'
  'Todos los proveedores de servicios ofrecen un servicio seguro?\n'
  '\n'
  'Notas de aplicabilidad\n'
  'Este requisito aplica únicamente cuando la entidad evaluada es un proveedor de servicios.')]

# Catálogo oficial utilizado en Gestión de Riesgos.
# Respaldo autocontenido de 106 subcategorías. En Cumplimiento Continuo, la fuente principal es static/templates/NIST.CSF 2.0.docx.
NIST_CSF_20_CONTROLES = [('GV.OC-01',
  'Se comprende la misión de la organización y se informa sobre la gestión de riesgos de seguridad cibernética.'),
 ('GV.OC-02',
  'Las partes interesadas internas y externas son comprendidas, y sus necesidades y expectativas con respecto a la '
  'gestión de riesgos de seguridad cibernética son comprendidas y consideradas.'),
 ('GV.OC-03',
  'Se comprenden y gestionan los requisitos legales, normativos y contractuales relativos a la seguridad cibernética, '
  'incluidas las obligaciones en materia de privacidad y libertades civiles.'),
 ('GV.OC-04',
  'Se comprenden y comunican los objetivos, las capacidades y los servicios críticos de los que dependen las partes '
  'interesadas externas o que esperan de la organización'),
 ('GV.OC-05', 'Se comprenden y comunican los resultados, capacidades y servicios de los que depende la organización'),
 ('GV.RM-01',
  'Los objetivos de la gestión de riesgos son establecidos y acordados por las partes interesadas de la organización'),
 ('GV.RM-02',
  'Se establecen, se comunican y se mantienen las declaraciones sobre el apetito de riesgo y la tolerancia al riesgo'),
 ('GV.RM-03',
  'Las actividades y los resultados de la gestión de riesgos de seguridad cibernética se incluyen en los procesos de '
  'gestión de riesgos de la empresa'),
 ('GV.RM-04',
  'Se establece y comunica una dirección estratégica que describa las opciones adecuadas de respuesta al riesgo.'),
 ('GV.RM-05',
  'Se establecen líneas de comunicación en toda la organización para los riesgos de seguridad cibernética, lo que '
  'incluye a los riesgos de proveedores y otros terceros.'),
 ('GV.RM-06',
  'Se establece y comunica un método estandarizado para calcular, documentar, categorizar y priorizar los riesgos de '
  'seguridad cibernética.'),
 ('GV.RM-07',
  'Se caracterizan las oportunidades estratégicas (es decir, los riesgos positivos) y se incluyen en las discusiones '
  'sobre riesgos de seguridad cibernética de la organización.'),
 ('GV.RR-01',
  'El liderazgo organizativo es responsable de los riesgos de seguridad cibernética y fomenta una cultura consciente '
  'de los riesgos, ética y de mejora continua.'),
 ('GV.RR-02',
  'Se establecen, comunican, comprenden y aplican las funciones, responsabilidades y autoridades relacionadas con la '
  'gestión de riesgos de seguridad cibernética.'),
 ('GV.RR-03',
  'Se asignan recursos adecuados de acuerdo con la estrategia de riesgos de seguridad cibernética, las funciones, las '
  'responsabilidades y las políticas.'),
 ('GV.RR-04', 'La seguridad cibernética se incluye en las prácticas de recursos humanos'),
 ('GV.PO-01',
  'La política de gestión de riesgos de seguridad cibernética se establece en base al contexto organizativo, la '
  'estrategia de seguridad cibernética y las prioridades, y es comunicada y aplicada'),
 ('GV.PO-02',
  'La política de gestión de riesgos de seguridad cibernética se revisa, actualiza, comunica y aplica para reflejar '
  'los cambios en los requisitos, las amenazas, la tecnología y la misión de la organización'),
 ('GV.OV-01',
  'Los resultados de la estrategia de gestión de riesgos de seguridad cibernética se revisan para informar y ajustar '
  'la estrategia y la dirección'),
 ('GV.OV-02',
  'La estrategia de gestión de riesgos de seguridad cibernética se revisa y ajusta para garantizar la cobertura de los '
  'requisitos y riesgos de la organización'),
 ('GV.OV-03',
  'El rendimiento de la gestión de riesgos de seguridad cibernética de la organización se evalúa y revisa para '
  'realizar los ajustes necesarios'),
 ('GV.SC-01',
  'Las partes interesadas de la organización establecen y acuerdan un programa, estrategia, objetivos, políticas y '
  'procesos de gestión de riesgos de seguridad cibernética en la cadena de suministro'),
 ('GV.SC-02',
  'Se establecen, comunican y coordinan interna y externamente las funciones y responsabilidades de seguridad '
  'cibernética para proveedores, clientes y colaboradores'),
 ('GV.SC-03',
  'La gestión de riesgos de la cadena de suministro de seguridad cibernética está integrada en la seguridad '
  'cibernética y la gestión de riesgos empresariales, la evaluación de riesgos y los procesos de mejora'),
 ('GV.SC-04', 'Los proveedores son conocidos y priorizados por criticidad'),
 ('GV.SC-05',
  'Los requisitos para abordar los riesgos de seguridad cibernética en las cadenas de suministro se establecen, '
  'priorizan e integran en contratos y otros tipos de acuerdos con proveedores y otras terceras partes pertinentes'),
 ('GV.SC-06',
  'Se llevan a cabo la planificación y la diligencia debida para reducir los riesgos antes de entablar relaciones '
  'formales con proveedores u otros terceros'),
 ('GV.SC-07',
  'Los riesgos planteados por un proveedor, sus productos y servicios y otros terceros se comprenden, registran, '
  'priorizan, evalúan, responden y monitorean a lo largo de la relación'),
 ('GV.SC-08',
  'Los proveedores pertinentes y otros terceros se incluyen en las actividades de planificación, respuesta y '
  'recuperación de incidentes'),
 ('GV.SC-09',
  'Las prácticas de seguridad de la cadena de suministro se integran en los programas de seguridad cibernética y de '
  'gestión de riesgos empresariales, y su rendimiento se monitorea a lo largo del ciclo de vida de los productos y '
  'servicios tecnológicos'),
 ('GV.SC-10',
  'Los planes de gestión de riesgos de la cadena de suministro de seguridad cibernética incluyen disposiciones para '
  'las actividades que ocurren después de la conclusión de un acuerdo de colaboración o servicio'),
 ('ID.AM-01', 'Se mantienen inventarios del hardware gestionado por la organización'),
 ('ID.AM-02', 'Se mantienen inventarios de software, servicios y sistemas gestionados por la organización'),
 ('ID.AM-03',
  'Se mantienen representaciones de la comunicación de red autorizada de la organización y de los flujos de datos de '
  'red internos y externos'),
 ('ID.AM-04', 'Se mantienen inventarios de los servicios prestados por los proveedores'),
 ('ID.AM-05', 'Se priorizan los activos en función de su clasificación, criticidad, recursos e impacto en la misión'),
 ('ID.AM-07', 'Se mantienen inventarios de datos y los metadatos correspondientes para los tipos de datos designados'),
 ('ID.AM-08',
  'Los sistemas, el hardware, el software, los servicios y los datos se gestionan durante todo su ciclo de vida'),
 ('ID.RA-01', 'Se identifican, validan y registran las vulnerabilidades de los activos'),
 ('ID.RA-02', 'Se recibe información sobre amenazas cibernéticas de foros y fuentes de intercambio de información'),
 ('ID.RA-03', 'Se identifican y registran las amenazas internas y externas a la organización'),
 ('ID.RA-04',
  'Se identifican y registran los impactos potenciales y las probabilidades de que las amenazas exploten las '
  'vulnerabilidades'),
 ('ID.RA-05',
  'Las amenazas, las vulnerabilidades, las probabilidades y los impactos se utilizan para comprender el riesgo '
  'inherente e informar sobre la priorización de la respuesta al riesgo'),
 ('ID.RA-06', 'Se eligen, priorizan, planifican, controlan y comunican las respuestas al riesgo'),
 ('ID.RA-07',
  'Se gestionan los cambios y las excepciones, se evalúa su impacto en el riesgo, se registran y se realiza su '
  'seguimiento'),
 ('ID.RA-08', 'Se establecen procesos para recibir, analizar y responder a las divulgaciones de vulnerabilidades'),
 ('ID.RA-09', 'Se evalúa la autenticidad e integridad del hardware y software antes de su adquisición y uso'),
 ('ID.RA-10', 'Se evalúan los proveedores críticos antes de su adquisición'),
 ('ID.IM-01', 'Las mejoras se identifican a partir de evaluaciones'),
 ('ID.IM-02',
  'Las mejoras se identifican a partir de pruebas y ejercicios de seguridad, lo que incluye a los realizados en '
  'coordinación con proveedores y terceros pertinentes'),
 ('ID.IM-03',
  'Las mejoras se identifican a partir de la ejecución de procesos, procedimientos y actividades operativos'),
 ('ID.IM-04',
  'Se establecen, comunican, mantienen y mejoran los planes de respuesta a incidentes y otros planes de seguridad '
  'cibernética que afectan a las operaciones.'),
 ('PR.AA-01',
  'La organización gestiona las identidades y credenciales de los usuarios, servicios y equipos autorizados'),
 ('PR.AA-02',
  'Las identidades están comprobadas y vinculadas a credenciales basadas en el contexto de las interacciones'),
 ('PR.AA-03', 'Los usuarios, servicios y hardware están autenticados'),
 ('PR.AA-04', 'Las afirmaciones de identidad se protegen, transmiten y verifican'),
 ('PR.AA-05',
  'Los permisos de acceso, los derechos y las autorizaciones se definen en una política, se gestionan, se aplican y se '
  'revisan, e incorporan los principios de privilegio mínimo y separación de funciones'),
 ('PR.AA-06', 'El acceso físico a los activos se gestiona, supervisa y aplica de forma proporcional al riesgo'),
 ('PR.AT-01',
  'Se sensibiliza y capacita al personal para que disponga de los conocimientos y habilidades necesarios para realizar '
  'tareas generales teniendo en cuenta los riesgos de seguridad cibernética'),
 ('PR.AT-02',
  'Se sensibiliza y capacita a las personas que desempeñan funciones especializadas para que posean los conocimientos '
  'y aptitudes necesarios para realizar las tareas pertinentes teniendo en cuenta los riesgos de seguridad '
  'cibernética'),
 ('PR.DS-01', 'La confidencialidad, la integridad y la disponibilidad de los datos en reposo están protegidas'),
 ('PR.DS-02', 'La confidencialidad, la integridad y la disponibilidad de los datos en tránsito están protegidas'),
 ('PR.DS-10', 'La confidencialidad, la integridad y la disponibilidad de los datos en uso están protegidas'),
 ('PR.DS-11', 'Se crean, protegen, mantienen y comprueban copias de seguridad de los datos'),
 ('PR.PS-01', 'Se establecen y aplican prácticas de gestión de la configuración'),
 ('PR.PS-02', 'Se mantiene, sustituye y elimina el software en función del riesgo'),
 ('PR.PS-03', 'Se mantiene, sustituye y elimina el hardware en función del riesgo'),
 ('PR.PS-04', 'Se generen registros y se pongan a disposición para una supervisión continua'),
 ('PR.PS-05', 'Se impide la instalación y la ejecución de software no autorizado'),
 ('PR.PS-06',
  'Se integran prácticas seguras de desarrollo de software y se supervisa su rendimiento durante todo el ciclo de vida '
  'de desarrollo del software'),
 ('PR.IR-01', 'Las redes y los entornos están protegidos contra el acceso lógico y el uso no autorizados'),
 ('PR.IR-02', 'Los activos tecnológicos de la organización están protegidos de las amenazas del entorno'),
 ('PR.IR-03', 'Se implementan mecanismos para lograr los requisitos de resiliencia en situaciones normales y adversas'),
 ('PR.IR-04', 'Se mantiene una capacidad de recursos adecuada para garantizar la disponibilidad'),
 ('DE.CM-01', 'Las redes y los servicios de red se monitorean para detectar acontecimientos potencialmente adversos'),
 ('DE.CM-02', 'Se monitorea el entorno físico para detectar posibles acontecimientos adversos'),
 ('DE.CM-03',
  'Se monitorea la actividad del personal y el uso de la tecnología para detectar posibles acontecimientos adversos'),
 ('DE.CM-06',
  'Se monitorean las actividades y los servicios de los proveedores de servicios externos para detectar '
  'acontecimientos potencialmente adversos.'),
 ('DE.CM-09',
  'Se monitorean el hardware y el software informáticos, los entornos de ejecución y sus datos para detectar posibles '
  'acontecimientos adversos'),
 ('DE.AE-02',
  'Los acontecimientos potencialmente adversos se analizan para comprender mejor las actividades asociadas'),
 ('DE.AE-03', 'Se correlaciona la información procedente de diversas fuentes'),
 ('DE.AE-04', 'Se comprende el impacto estimado y el alcance de los acontecimientos adversos'),
 ('DE.AE-06',
  'La información sobre acontecimientos adversos se proporciona al personal y a las herramientas autorizadas'),
 ('DE.AE-07', 'La inteligencia sobre amenazas cibernéticas y otra información contextual se integran en el análisis'),
 ('DE.AE-08',
  'Se declaran incidentes cuando los acontecimientos adversos cumplen con los criterios de incidente definidos'),
 ('RS.MA-01',
  'Se ejecuta el plan de respuesta a incidentes en coordinación con los terceros pertinentes una vez que se declara un '
  'incidente'),
 ('RS.MA-02', 'Se clasifican y validan los informes de incidentes'),
 ('RS.MA-03', 'Se clasifican y priorizan los incidentes'),
 ('RS.MA-04', 'Se escalan o elevan los incidentes según sea necesario'),
 ('RS.MA-05', 'Se aplican los criterios para iniciar la recuperación de incidentes'),
 ('RS.AN-03', 'Se realizan análisis para determinar lo que ocurrió durante un incidente y la causa raíz del mismo'),
 ('RS.AN-06',
  'Se registran las acciones realizadas durante una investigación y se preservan la integridad y la procedencia de los '
  'registros'),
 ('RS.AN-07', 'Se recopilan los datos y metadatos del incidente y se preservan su integridad y su procedencia'),
 ('RS.AN-08', 'Se estima y valida la magnitud de un incidente.'),
 ('RS.CO-02', 'Se notifican los incidentes a las partes interesadas internas y externas'),
 ('RS.CO-03', 'La información se comparte con las partes interesadas internas y externas designadas'),
 ('RS.MI-01', 'Se contienen los incidentes'),
 ('RS.MI-02', 'Se erradican los incidentes'),
 ('RC.RP-01',
  'La parte de recuperación del plan de respuesta a incidentes se ejecuta una vez que se inicia desde el proceso de '
  'respuesta a incidentes'),
 ('RC.RP-02', 'Se seleccionan, delimitan, priorizan y llevan a cabo las acciones de recuperación'),
 ('RC.RP-03',
  'Se verifica la integridad de las copias de seguridad y otros activos de restauración antes de usarlos para la '
  'restauración'),
 ('RC.RP-04',
  'Se tienen en cuenta las funciones críticas de la misión y la gestión de riesgos de seguridad cibernética para '
  'establecer normas operativas posteriores al incidente'),
 ('RC.RP-05',
  'Se verifica la integridad de los activos restaurados, se restauran los sistemas y servicios y se confirma el estado '
  'operativo normal'),
 ('RC.RP-06',
  'Se declara el fin de la recuperación del incidente sobre la base de criterios y se completa la documentación '
  'relacionada con el incidente'),
 ('RC.CO-03',
  'Las actividades de recuperación y los progresos en el restablecimiento de las capacidades operativas se comunican a '
  'las partes interesadas internas y externas designadas'),
 ('RC.CO-04',
  'Las actualizaciones públicas sobre la recuperación del incidente se comparten mediante el uso de métodos y mensajes '
  'aprobados')]

SOC2_CONTROLES = [('CC1.0', 'CRITERIOS COMUNES RELACIONADOS CON EL ENTORNO DE CONTROL'),
 ('CC1.1', 'Principio 1 de COSO: La entidad demuestra un compromiso con la integridad y los valores éticos'),
 ('CC1.2',
  'Principio 2 de COSO: La junta directiva demuestra independencia de la administración y ejerce la supervisión del '
  'desarrollo y el desempeño del control interno.'),
 ('CC1.3',
  'Principio 3 de COSO: La gerencia establece, con supervisión de la junta directiva, estructuras, líneas de reporte '
  'y autoridades y responsabilidades apropiadas en la búsqueda de objetivos.'),
 ('CC1.4',
  'Principio 4 de COSO: La entidad demuestra un compromiso para atraer, desarrollar y retener a individuos '
  'competentes en alineación con los objetivos'),
 ('CC2.0', 'Criterios comunes relacionados con la comunicación y la información .'),
 ('CC2.1',
  'Principio 13 de COSO: La entidad obtiene o genera y utiliza información relevante y de calidad para respaldar el '
  'funcionamiento del control interno.'),
 ('CC2.2',
  'Principio 14 de COSO: La entidad comunica internamente la información, incluidos los objetivos y '
  'responsabilidades de control interno, necesarios para respaldar el funcionamiento del control interno.'),
 ('CC2.3',
  'Principio 15 de COSO: La entidad se comunica con partes externas con respecto a asuntos que afectan el '
  'funcionamiento del control interno.'),
 ('CC3.0', 'Criterios comunes relacionados con la evaluación de riesgos'),
 ('CC3.1',
  'Principio 6 de COSO: La entidad especifica objetivos con suficiente claridad para permitir la identificación y '
  'evaluación de los riesgos relacionados con los objetivos.'),
 ('CC3.2',
  'Principio 7 de COSO: la entidad identifica los riesgos para el logro de sus objetivos en toda la entidad y '
  'analiza los riesgos como una base para determinar cómo deben gestionarse los riesgos?'),
 ('CC3.3',
  'Principio 8 de COSO: La entidad considera el potencial de fraude al evaluar los riesgos para el logro de los '
  'objetivos.'),
 ('CC3.4',
  'Principio 9 de COSO: La entidad identifica y evalúa los cambios que podrían afectar significativamente el sistema '
  'de control interno'),
 ('CC4.0', 'Criterios comunes relacionados con los controles de monitoreo'),
 ('CC4.1',
  'Principio 16 de COSO: La entidad selecciona, desarrolla y realiza evaluaciones continuas y / o separadas para '
  'determinar si los componentes del control interno están presentes y en funcionamiento.'),
 ('CC4.2',
  'Principio 17 de COSO: La entidad evalúa y comunica las deficiencias de control interno de manera oportuna a las '
  'partes responsables de tomar medidas correctivas, incluida la administración superior y el consejo de '
  'administración, según corresponda.'),
 ('CC5.0', 'Criterios comunes relacionados con las actividades de control.'),
 ('CC5.1',
  'Principio 11 de COSO: La entidad selecciona y desarrolla actividades de control que contribuyan a la mitigación '
  'de riesgos para el logro de los objetivos a niveles aceptables.'),
 ('CC5.2',
  'Principio 11 de COSO: La entidad también selecciona y desarrolla actividades de control general sobre la '
  'tecnología para apoyar el logro de los objetivos.'),
 ('CC5.3',
  'Principio 12 de COSO: La entidad implementa actividades de control a través de políticas que establecen lo que se '
  'espera y en procedimientos que las ponen en acción.'),
 ('CC6.0', 'Criterios comunes relacionados con los controles de acceso lógico y físico'),
 ('CC6.1',
  'La entidad implementa software de seguridad de acceso lógico, infraestructura y arquitecturas sobre activos de '
  'información protegidos para protegerlos de eventos de seguridad para cumplir con los objetivos de la entidad.'),
 ('CC6.2',
  'Antes de emitir las credenciales del sistema y otorgar acceso al sistema, la entidad registra y autoriza a los '
  'nuevos usuarios internos y externos cuyo acceso es administrado por la entidad. Para aquellos usuarios cuyo '
  'acceso es administrado por la entidad, las credenciales del sistema de usuario se eliminan cuando el acceso de '
  'usuario ya no está autorizado.'),
 ('CC6.3',
  'La entidad autoriza, modifica o elimina el acceso a datos, software, funciones y otros activos de información '
  'protegidos en función de los roles, responsabilidades o el diseño y los cambios del sistema, teniendo en cuenta '
  'los conceptos de privilegio mínimo y la separación de funciones, para cumplir con los requisitos y objetivos de '
  'la entidad.'),
 ('CC6.4',
  'La entidad descontinúa las protecciones lógicas y físicas sobre los activos físicos solo después de que la '
  'capacidad de leer o recuperar datos y software de esos activos haya disminuido y ya no sea necesario cumplir con '
  'los objetivos de la entidad.'),
 ('CC6.5',
  'La entidad implementa medidas de seguridad de acceso lógico para protegerse contra amenazas de fuentes fuera de '
  'los límites de su sistema.'),
 ('CC6.6',
  'La entidad restringe la transmisión, el movimiento y la eliminación de información a usuarios y procesos internos '
  'y externos autorizados, y la protege durante la transmisión, el movimiento o la eliminación para cumplir con los '
  'objetivos de la entidad.'),
 ('CC6.7',
  'La entidad implementa controles para prevenir o detectar y actuar sobre la introducción de software no autorizado '
  'o malicioso para cumplir con los objetivos de la entidad. .'),
 ('CC7.0', 'Criterios comunes relacionados con las operaciones del sistema.'),
 ('CC7.1',
  'Para cumplir con sus objetivos, la entidad utiliza procedimientos de detección y monitoreo para identificar (1) '
  'cambios en las configuraciones que resultan en la introducción de nuevas vulnerabilidades, y (2) '
  'susceptibilidades a las vulnerabilidades recién descubiertas.'),
 ('CC7.2',
  'La entidad supervisa los componentes del sistema y el funcionamiento de dichos componentes en busca de anomalías '
  'que sean indicativas de actos maliciosos, desastres naturales y errores que afecten la capacidad de la entidad '
  'para cumplir sus objetivos; Se analizan las anomalías para determinar si representan eventos de seguridad.'),
 ('CC7.3',
  'La entidad evalúa los eventos de seguridad para determinar si podrían o han resultado en una falla de la entidad '
  'para cumplir con sus objetivos (incidentes de seguridad) y, de ser así, toma medidas para prevenir o abordar '
  'dichos fallos.'),
 ('CC7.4',
  'La entidad responde a los incidentes de seguridad identificados mediante la ejecución de un programa de respuesta '
  'a incidentes definido para comprender, contener, remediar y comunicar los incidentes de seguridad, según '
  'corresponda'),
 ('CC8.0', 'Criterios comunes relacionados con la gestión del cambio'),
 ('CC8.1',
  'La entidad autoriza, diseña, desarrolla o adquiere, configura, documenta, prueba, aprueba e implementa cambios en '
  'infraestructura, datos, software y procedimientos para cumplir con sus objetivos.'),
 ('CC9.0', 'Criterios comunes relacionados con la mitigación de riesgos'),
 ('CC9.1',
  'La entidad identifica, selecciona y desarrolla actividades de mitigación de riesgos para los riesgos que surgen '
  'de posibles interrupciones del negocio'),
 ('CC9.2', 'La entidad evalúa y gestiona los riesgos asociados con vendedores y socios comerciales'),
 ('A1.0', 'Criterios relacionados con la disponibilidad'),
 ('A1.1',
  'La entidad mantiene, monitorea y evalúa la capacidad de procesamiento actual y el uso de los componentes del '
  'sistema (infraestructura, datos y software) para administrar la demanda de capacidad y permitir la implementación '
  'de capacidad adicional para ayudar a cumplir sus objetivos.ponentes del sistema (infraestructura, datos y '
  'software) para administrar la demanda de capacidad y permitir la implementación de capacidad adicional para '
  'ayudar a cumplir sus objetivos.'),
 ('A1.2',
  'La entidad autoriza, diseña, desarrolla o adquiere, implementa, opera, aprueba, mantiene y monitorea protecciones '
  'ambientales, software, procesos de respaldo de datos e infraestructura de recuperación para cumplir con sus '
  'objetivos.'),
 ('A1.3',
  'La entidad prueba los procedimientos del plan de recuperación que respaldan la recuperación del sistema para '
  'cumplir sus objetivos.'),
 ('C1.0', 'Criterios relacionados con la confidencialidad'),
 ('C1.1',
  'La entidad identifica y mantiene información confidencial para cumplir con los objetivos de la entidad '
  'relacionados con la confidencialidad'),
 ('C1.2',
  'La entidad dispone de información confidencial para cumplir con los objetivos de la entidad relacionados con la '
  'confidencialidad'),
 ('C1.3',
  'La entidad se comunica con partes externas sobre asuntos que afectan el funcionamiento del control interno.'),
 ('C1.14',
  'La entidad autoriza, diseña, desarrolla o adquiere, configura, documenta, prueba, aprueba e implementa cambios a '
  'la infraestructura, datos, software y procedimientos para cumplir con sus objetivos.'),
 ('P1.0', 'Criterios de Privacidad Relatados al Aviso y Comunicación de Objetivos Relacionados con la Privacidad'),
 ('P1.1', 'Revisar y mantener actualizado el aviso de privacidad.'),
 ('P1.2', 'Versionamiento de los documentos del sistema de protección de datos personales.'),
 ('P2.0', 'Criterios de privacidad relacionados con la elección y el consentimiento'),
 ('P3.0', 'Criterios de privacidad relacionados con la recopilación'),
 ('P3.3',
  'Para la información que requiere consentimiento explícito, la entidad comunica la necesidad de dicho '
  'consentimiento, así como las consecuencias de la falta de consentimiento para la solicitud de información '
  'personal, y obtiene el consentimiento antes de la recopilación de la información para cumplir con los requisitos. '
  'los objetivos de la entidad relacionados con la privacidad.'),
 ('P4.0', 'Criterios de privacidad relacionados con el uso, la retención y la eliminación.'),
 ('P4.1', 'Atención de requerimientos quejas, reclamos – Protección de Datos, Usuarios & Clientes'),
 ('P4.2',
  'La entidad retiene información personal consistente con los objetivos de la entidad relacionados con la '
  'privacidad.'),
 ('P5.0', 'Criterios de privacidad relacionados con el acceso'),
 ('P6.0', 'Criterios de privacidad relacionados con la divulgación y notificación'),
 ('P6.1', 'Procedimientos para registro de Incidentes y PQRs.')]
def construir_opciones_control(catalogo, valor_actual=""):
    """
    Construye opciones HTML para los catálogos de controles.
    Guarda solo el código, muestra código + descripción e incorpora
    el texto completo en data-descripcion para el formulario.
    """
    actual = str(valor_actual or "").strip()
    opciones = ['<option value="">Seleccione un control...</option>']
    codigos_catalogo = set()

    for codigo, descripcion in catalogo:
        codigo_txt = str(codigo or "").strip()
        descripcion_txt = str(descripcion or "").strip()
        if not codigo_txt:
            continue

        codigos_catalogo.add(codigo_txt)
        etiqueta = f"{codigo_txt} - {descripcion_txt}" if descripcion_txt else codigo_txt
        seleccionado = " selected" if codigo_txt == actual else ""
        descripcion_attr = html.escape(descripcion_txt, quote=True).replace("\n", "&#10;")

        opciones.append(
            f'<option value="{html.escape(codigo_txt, quote=True)}" '
            f'data-descripcion="{descripcion_attr}"{seleccionado}>'
            f'{html.escape(etiqueta)}</option>'
        )

    if actual and actual not in codigos_catalogo:
        opciones.insert(
            1,
            f'<option value="{html.escape(actual, quote=True)}" selected '
            f'data-descripcion="">'
            f'{html.escape(actual)} - Código conservado de un catálogo anterior</option>'
        )

    return Markup("\n".join(opciones))


def _descripcion_de_catalogo(catalogo, codigo):
    codigo_txt = str(codigo or "").strip()
    if not codigo_txt:
        return ""

    for codigo_item, descripcion in catalogo:
        if str(codigo_item or "").strip() == codigo_txt:
            return str(descripcion or "").strip()

    return ""


def construir_descripcion_controles_multimarco(
    codigo_iso="",
    codigo_pci="",
    codigo_nist="",
    codigo_soc2=""
):
    """
    Consolida en un único campo la descripción completa de cada control
    seleccionado de ISO/IEC 27002, PCI DSS, NIST CSF 2.0 y SOC 2.

    El contenido se reconstruye desde los catálogos del servidor para
    impedir que un marco sobrescriba la descripción de los demás.
    """
    seleccionados = [
        ("ISO/IEC 27002:2022", codigo_iso, ISO_27002_CONTROLES),
        ("PCI DSS", codigo_pci, PCI_DSS_CONTROLES),
        ("NIST CSF 2.0", codigo_nist, NIST_CSF_20_CONTROLES),
        ("SOC 2", codigo_soc2, SOC2_CONTROLES),
    ]

    bloques = []

    for marco, codigo, catalogo in seleccionados:
        codigo_txt = str(codigo or "").strip()
        if not codigo_txt:
            continue

        descripcion = _descripcion_de_catalogo(catalogo, codigo_txt)
        encabezado = f"{marco} — {codigo_txt}"

        if descripcion:
            bloques.append(f"{encabezado}\n{descripcion}")
        else:
            bloques.append(encabezado)

    return "\n\n".join(bloques).strip()

#                               -----------  Matriz de Proveedores ------------ 

# Campos disponibles en la matriz de Proveedores (clave -> etiqueta)
PROV_COLS = [
    # --- Info Proveedor
    ('fecha_eval_seguridad', 'Fecha Eval.'),
    ('nombre_proveedor', 'Proveedor'),
    ('estatus_proveedor', 'Estatus'),
    ('area', 'Área responsable'),                 # relación a AreaEmpresa
    ('responsable_area_nombre', 'Resp. área'),
    ('responsable_area_cargo', 'Cargo Resp. área'),
    ('nombre_cargo_evaluador', 'Evaluador'),
    ('pais_origen', 'País Origen'),
    ('pais_servicio', 'País Servicio'),
    ('desc_producto_servicio', 'Descripción'),
    ('estado_avance', 'Avance'),
    ('estado_evaluacion', 'Estado Eval.'),

    # --- Calificación (banderas y valores)
    ('es_transversal', 'Transversal (Sí/No)'),
    ('valor_alcance', 'Val. Alcance'),
    ('es_esencial', 'Esencial (Sí/No)'),
    ('valor_esencial', 'Val. Esencial'),
    ('tiene_plan_cont', 'Plan Cont. (Sí/No)'),
    ('valor_plan_cont', 'Val. Plan Cont.'),
    ('existen_alternativas', 'Alternativas (Sí/No)'),
    ('valor_alternativas', 'Val. Alternativas'),
    ('existe_plan_migracion', 'Plan Migración (Sí/No)'),
    ('valor_plan_migracion', 'Val. Migración'),
    ('procesa_info_sensible', 'Info. Sensible (Sí/No)'),
    ('valor_info_sensible', 'Val. Info Sens.'),

    # --- Criticidad calculada
    ('criticidad_pct', 'Criticidad %'),
    ('criticidad_texto', 'Criticidad'),

    # --- Evaluación (certificación / formulario)
    ('tiene_certificacion', 'Certificación (Sí/No)'),
    ('num_certificaciones', 'N° Certificaciones'),      
    ('nombre_certificaciones', 'Nombre certificaciones'),
    ('requiere_formulario', 'Req. Formulario'),
    ('puntos_certificacion', 'Pts Cert.'),
    ('puntos_formulario', 'Pts Formulario'),
    ('calificacion_total', 'Calif. total'),
    ('resultado_evaluacion', 'Resultado'),

    # --- Adjuntos / otros
    ('evidencias', 'Evidencias'),
    ('observaciones', 'Observaciones'),
]

# Sugerencia de set por defecto (puedes ajustarlo a gusto)
DEFAULT_PROV_COLS = [
    'fecha_eval_seguridad','nombre_proveedor','estatus_proveedor','area',
    'responsable_area_nombre','responsable_area_cargo',
    'estado_avance','estado_evaluacion',
    'criticidad_pct','criticidad_texto',
    'tiene_certificacion','puntos_formulario',
    'calificacion_total','resultado_evaluacion',
    'evidencias'
]

#                               -----------  Matriz de Capacitaciones ------------ 

#  Plan de capacitaciones

PLAN_DIS_COLS = [
    ("tema_capacitacion", "Tema de la capacitación"),
    ("descripcion", "Descripción"),
    ("horas", "# Horas"),
    ('dirigida_area', 'Dirigida a (área)'),
    ('dirigida_division', 'Dirigida a (división)'),
    ("fecha_programada", "Fecha programada"),
    ("fecha_ejecucion", "Fecha ejecución"),
    ("responsable", "Responsable"),
    ("metodologia", "Metodología medición, evaluación y eficacia"),
    ("evidencia", "Evidencia"),
    ("observaciones", "Observaciones"),
]

DEFAULT_PLAN_DIS_COLS = [
    "tema_capacitacion",
    "descripcion",
    "horas",
    'dirigida_area',
    'dirigida_division',
    "fecha_programada",
    "fecha_ejecucion",
    "responsable",
    'evidencia',          # 👈 importante
    'observaciones',
]

# Seguimiento al plan de capacitaciones

PLANCF_COLS = [
    ("nombre_capacitacion", "Nombre de la capacitación"),
    ("objetivo_capacitacion", "Objetivo de la capacitación"),
    ("temario", "Temario"),
    ("fecha_programada", "Fecha Programada"),
    ("fecha_realizacion", "Fecha de realización"),
    ("cumplimiento_pct", "% Cumplimiento Programa Capacitación"),
    ('area_participantes', 'Área de colaboradores participantes'),
    ('division_participantes', 'División de colaboradores participantes'),
    ("cargo_participantes", "Cargo de colaboradores participantes"),
    ("competencia_entrenador", "Competencia del entrenador (interno o externo)"),
    ("quien_realizo", "Quién realizó la Capacitación y/o Entrenamiento (Interno o Externo)"),
    ("horas_duracion", "Horas de duración de la capacitación"),
    ("indicador_realizacion", "Indicador de realización de la Capacitación y/o Entrenamiento (100% Realizada / 0% No realizada)"),
    ("num_asistentes", "Número de asistentes a capacitación"),
    ("num_programados", "Número total de trabajadores programados"),
    ("cobertura_pct", "% Cobertura"),
    ("num_evaluados", "Número trabajadores evaluados"),
    ("num_eficaces", "Número de evaluaciones eficaces"),
    ("eficaces_pct", "% de evaluaciones eficaces"),
]

DEFAULT_PLANCF_COLS = [
    'nombre_capacitacion','fecha_programada','fecha_realizacion',
    'cumplimiento_pct','area_participantes',
    'division_participantes','horas_duracion',
    'num_asistentes','num_programados','cobertura_pct',
    'num_evaluados','num_eficaces','eficaces_pct',
]

PLANCF_GROUPS = {
    "Contenido de la capacitación": [
        "nombre_capacitacion", "objetivo_capacitacion", "temario"
    ],
    "Cronograma Capacitación": [
        "fecha_programada", "fecha_realizacion"
    ],
    "Indicador Cumplimiento": [
        "cumplimiento_pct"
    ],
    "Participantes": [
        'area_participantes',
        'division_participantes',
    ],
    "Instructor": [
        "competencia_entrenador"
    ],
    "Nombre Instructor": [
        "quien_realizo"
    ],
    "No. Horas": [
        "horas_duracion"
    ],
    "%": [
        "indicador_realizacion"
    ],
    "Indicador Cobertura": [
        "num_asistentes", "num_programados", "cobertura_pct"
    ],
    "Indicador Eficacia": [
        "num_evaluados", "num_eficaces", "eficaces_pct"
    ],
}



# Objetivo del sistema de gestión de seguridad

OBJETIVOS_MATRIZ_COLS_MIN = [
    'objetivo',
    'indicador',
    'meta_pct',
    'responsable_del_indicador',
    'frecuencia_calculo',
    'fecha_meta'
]


# =========================
# Columnas — Planes de mejora SGSI
# =========================
MEJORA_PLAN_COLS = [
    ('fecha', 'Fecha'),
    ('descripcion_incumplimiento', 'Descripción o incumplimiento'),
    ('causa', 'Causa'),
    ('tipo_accion', 'Tipo de acción (correctiva/mejora)'),
    ('plan_accion', 'Plan de acción'),
    ('termino_ejecucion', 'Término de ejecución'),
    ('fecha_ejecucion_propuesta', 'Fecha de ejecución propuesta'),
    ('responsable', 'Responsable'),
    ('estado_actividad', 'Estado de la actividad'),
    ('fecha_cierre', 'Fecha de cierre'),
    ('evidencias', 'Evidencia'),
    ('eficacia', 'Eficacia (Sí / No)'),
    ('observacion_eficacia', 'Observación de eficacia'),
]

DEFAULT_MEJORA_PLAN_COLS = [c[0] for c in MEJORA_PLAN_COLS]

# =========================
# Columnas — Listado Maestro de Documentos
# =========================

DOCS_MATRIZ_MIN_COLS = [
    'item',
    'tipo_doc',
    'codigo',
    'nombre_documento',
    'version',
    'fecha_ultima_revision',
    'estado_revision',
    'estado',
]

# =============================
# Columnas — Control de Cambios
# =============================

RFC_COLS = [
    ('ticket', 'Ticket'),
    ('fecha_solicitud', 'Fecha solicitud'),
    ('responsable_solicitud_nombre', 'Responsable solicitud'),
    ('responsable_solicitud_cargo', 'Cargo responsable'),
    ('descripcion', 'Descripción'),
    ('antecedentes', 'Antecedentes'),
    ('objetivo', 'Objetivo'),
    ('alcance', 'Alcance'),
    ('ambiente', 'Ambiente'),
    ('partes_interesadas', 'Partes interesadas'),
    ('recursos_necesarios', 'Recursos necesarios'),
    ('tipo_cambio', 'Tipo de cambio'),
    ('prioridad', 'Prioridad'),

    ('total_riesgos', 'Total riesgos'),
    ('total_planes_pruebas', 'Total planes pruebas'),
    ('total_rollbacks', 'Total rollbacks'),
    ('total_implementaciones', 'Total implementaciones'),

    ('ajustes_requeridos', 'Ajustes requeridos'),
    ('cambios_requeridos', 'Cambios requeridos'),

    ('revisa_nombre', 'Revisa'),
    ('revisa_cargo', 'Cargo revisa'),
    ('revisa_observaciones', 'Obs. revisa'),
    ('revisa_fecha', 'Fecha revisa'),

    ('aprueba_nombre', 'Aprueba'),
    ('aprueba_cargo', 'Cargo aprueba'),
    ('aprueba_observaciones', 'Obs. aprueba'),
    ('aprueba_fecha', 'Fecha aprueba'),

    ('implementa_nombre', 'Implementa'),
    ('implementa_cargo', 'Cargo implementa'),
    ('implementa_observaciones', 'Obs. implementa'),
    ('implementa_fecha', 'Fecha implementa'),

    ('cambio_eficaz', 'Cambio eficaz'),
    ('descripcion_seguimiento', 'Descripción seguimiento'),
]

DEFAULT_RFC_COLS = [
    'ticket',
    'fecha_solicitud',
    'responsable_solicitud_nombre',
    'tipo_cambio',
    'prioridad',
    'total_riesgos',
    'total_planes_pruebas',
    'total_rollbacks',
    'total_implementaciones',
    'cambio_eficaz'
]

# columnas disponibles en la matriz de aspectos legales

REQ_LEGAL_COLS = [
    ('codigo', 'ID'),
    ('requisito', 'Requisito Legal / Contractual'),
    ('tipo_ley', 'Tipo de Ley / Norma'),
    ('entidad_emisora', 'Entidad Emisora'),
    ('descripcion_alcance', 'Descripción / Alcance'),
    ('responsable', 'Responsable'),
    ('evidencia_cumplimiento', 'Evidencia de Cumplimiento'),
    ('estado', 'Estado'),
    ('fecha_revision', 'Fecha de Revisión'),
]

DEFAULT_REQ_LEGAL_COLS = [c[0] for c in REQ_LEGAL_COLS]

# columnas disponibles en la matriz partes interesadas

PARTES_INTERESADAS_MATRIZ_MIN_COLS = [
    "parte_interesada",
    "necesidades_expectativas",
    "fecha_revision",
    "evidencias",
]

# columnas disponibles en la matriz vulnerabilidades

VULNERABILIDAD_COLS = [
    ('codigo', 'ID'),
    ('activo', 'Activo'),
    ('descripcion_vulnerabilidad', 'Descripción'),
    ('cve', 'CVE'),
    ('clasificacion', 'Clasificación'),          # 👈 NUEVO/IMPORTANTE
    ('estado', 'Estado'),
    ('fecha_identificacion', 'Fecha identificación'),
    ('fecha_cierre', 'Fecha cierre'), 
    ('responsable', 'Responsable'),
    ('cvss', 'CVSS'),
    ('riesgo_residual', 'Riesgo residual'),
    ('evidencias', 'Evidencias'),                # 👈 para la columna de archivos
]

DEFAULT_VULNERABILIDAD_COLS = [
    'codigo',
    'activo',
    'descripcion_vulnerabilidad',
    'cve',
    'clasificacion',       # 👈 que esté incluida
    'estado',
    'fecha_identificacion',
    'fecha_cierre', 
    'responsable',
    'cvss',
    'evidencias',          # 👈 si quieres ver la lista de PDFs en la matriz
]

# columnas disponibles en el plan de remediación

PLAN_REMED_COLS = [
    ("vuln_codigo", "ID de Vulnerabilidad"),
    ("accion_correctiva", "Acción Correctiva"),
    ("responsable", "Responsable"),
    ("prioridad", "Prioridad"),
    ("fecha_objetivo", "Fecha Objetivo"),
    ("fecha_remediacion", "Fecha de Remediación"),   # <-- NUEVO
    ("recursos_necesarios", "Recursos Necesarios"),
    ("estado", "Estado"),
    ('jira_issue_key', 'Jira Key'),
    ('jira_status', 'Estado Jira'),
    ('jira_assignee_name', 'Responsable Jira'),
]

DEFAULT_PLAN_REMED_COLS = [c[0] for c in PLAN_REMED_COLS]

# columnas disponibles en el plan de competencias

PLAN_REMEDIACION_COMP_COLS = [
    ("rol_cargo", "Rol / Cargo"),
    ("responsable", "Responsable / Persona"),
    ("competencias_requeridas", "Competencias Requeridas"),
    ("brechas_detectadas", "Brechas Detectadas"),
    ("plan_capacitacion", "Plan de Capacitación / Acción"),
    ("fecha_cumplimiento", "Fecha de Cumplimiento"),
    ("evidencias", "Evidencias de Competencia"),
]

DEFAULT_PLAN_REMEDIACION_COMP_COLS = [key for key, _ in PLAN_REMEDIACION_COMP_COLS]

# columnas disponibles en Contexto Interno

CONTEXTO_INTERNO_MATRIZ_MIN_COLS = [
    "factor_interno",
    "descripcion",
    "impacto_sgsi",
    "fecha_revision",
]

# columnas disponibles en Contexto Externo

CONTEXTO_EXTERNO_MATRIZ_MIN_COLS = [
    "categoria",
    "descripcion_factor",
    "impacto_sgsi",
    "fecha_revision",
]

# columnas disponibles en Gestión de Accesos

GESTION_ACCESO_COLS = [
    ("id_acceso",        "ID"),
    ("rol_usuario",      "Rol del Usuario"),
    ("usuario",          "Usuario"),
    ("area_nombre",      "Área"),
    ("aplicacion",       "Aplicación/Sistema"),
    ("tipo_acceso",      "Tipo de Acceso"),
    ("rol_tecnico_app",  "Rol Técnico en App"),
    ("nivel_privilegio", "Nivel de Privilegio"),
    ("justificacion",    "Justificación del Acceso"),
    ("aprobado_por",     "Aprobado por"),
    ("gestionado_por",   "Gestionado por"),
    ("fecha_alta",       "Fecha de Alta"),
    ("fecha_baja",       "Fecha de Baja"),
    ("estado_nombre",    "Estado"),
    ("evidencia",        "Evidencia (texto / PDFs)"),
]

DEFAULT_GESTION_ACCESO_COLS = [
    "id_acceso",
    "usuario",
    "area_nombre",
    "aplicacion",
    "tipo_acceso",
    "nivel_privilegio",
    "fecha_alta",
    "estado_nombre",
]


# columnas disponibles en Revisión de Accesos

REVISION_ACCESO_COLS = [
    ("usuario_rol",     "Usuario / Rol"),
    ("aplicacion",      "Aplicación"),
    ("tipo_acceso",     "Tipo de Acceso"),
    ("revisado_por",    "Revisado por"),
    ("fecha_revision",  "Fecha de Revisión"),
    ("sigue_necesario", "¿Sigue Siendo Necesario?"),
    ("observaciones",   "Observaciones"),
]

DEFAULT_REVISION_ACCESO_COLS = [
    "usuario_rol",
    "aplicacion",
    "tipo_acceso",
    "revisado_por",
    "fecha_revision",
    "sigue_necesario",
    "observaciones",
]

REVISION_TIPOS_ACCESO = ["Escritura", "Lectura", "Escritura y Lectura"]
REVISION_SI_NO = ["Si", "No"]   # si prefieres con tilde: ["Sí", "No"]

# columnas disponibles en Metricas de Incidentes

INCIDENTE_METRICA_COLS = [
    ("fecha_registro", "Fecha y hora de registro"),
    ("descripcion_incidente", "Descripción del incidente"),
    ("cargo_responsable", "Cargo responsable de la gestión del incidente"),
    ("clasificacion", "Clasificación del incidente"),
    ("requiere_contencion", "Se requiere CONTENCIÓN"),
    ("tiempo_mtcd_horas", "Tiempo ejecutado en la eficacia de la MTDC (h)"),
    ("cumplimiento_mtcd", "Cumplimiento meta final de la CONTENCIÓN (%)"),
    ("requiere_recuperacion", "Se requiere RECUPERACIÓN"),
    ("tiempo_mtir_horas", "Tiempo ejecutado en la eficacia de la MTIR (h)"),
    ("cumplimiento_mtir", "Cumplimiento meta final de la RECUPERACIÓN (%)"),
    ("cumplimiento_global", "Cumplimiento (%)"),
    ("analisis", "Análisis"),
]

DEFAULT_INCIDENTE_METRICA_COLS = [k for k, _ in INCIDENTE_METRICA_COLS]


#                                        ---------- Lista completa de controles (Anexo A) en español ---------

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



#================================================================================================================================
#                                                      Helpers
#================================================================================================================================

# ==========================================================================================================================================
#                                                       Helpers Jira - Plan Remediación
# ==========================================================================================================================================

def jira_is_enabled():
    return all([
        JIRA_ENABLED,
        (JIRA_BASE_URL or "").strip(),
        (JIRA_EMAIL or "").strip(),
        (JIRA_API_TOKEN or "").strip(),
        (JIRA_PROJECT_KEY or "").strip()
    ])


def jira_auth():
    return HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)


def jira_headers():
    return {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }


def jira_priority_name(prioridad_local: str) -> str:
    p = (prioridad_local or "").strip().lower()
    if p == "alta":
        return "High"
    if p == "media":
        return "Medium"
    if p == "baja":
        return "Low"
    return "Medium"


def limpiar_texto_jira(txt, max_len=None):
    valor = (txt or "").strip()
    if max_len:
        valor = valor[:max_len]
    return valor


def descripcion_plan_para_jira(plan, vuln):
    fecha_obj = plan.fecha_objetivo.strftime("%Y-%m-%d") if plan.fecha_objetivo else "No definida"

    return f"""
Plan de remediación generado desde el SGSI.

Vulnerabilidad asociada:
- Código: {vuln.codigo or 'N/A'}
- Activo: {vuln.activo or 'N/A'}
- Descripción: {vuln.descripcion_vulnerabilidad or 'N/A'}
- CVE: {vuln.cve or 'N/A'}
- CVSS: {vuln.cvss or 'N/A'}
- Clasificación: {vuln.clasificacion or 'N/A'}
- Estado vulnerabilidad: {vuln.estado or 'N/A'}

Plan de remediación:
- ID interno: {plan.id}
- Responsable SGSI: {plan.responsable or 'N/A'}
- Prioridad: {plan.prioridad or 'N/A'}
- Estado: {plan.estado or 'N/A'}
- Fecha objetivo: {fecha_obj}

Acción correctiva:
{plan.accion_correctiva or 'N/A'}

Recursos necesarios:
{plan.recursos_necesarios or 'N/A'}
""".strip()

def jira_adf_parrafo(texto: str, bold=False):
    if not texto:
        return {
            "type": "paragraph",
            "content": []
        }

    nodo = {
        "type": "text",
        "text": texto[:5000]
    }

    if bold:
        nodo["marks"] = [{"type": "strong"}]

    return {
        "type": "paragraph",
        "content": [nodo]
    }


def jira_adf_descripcion_plan(vuln, plan):
    contenido = []

    contenido.append(jira_adf_parrafo(f"Remediación de vulnerabilidad {vuln.codigo or '—'}", bold=True))
    contenido.append(jira_adf_parrafo(f"Activo: {vuln.activo or '—'}"))
    contenido.append(jira_adf_parrafo(f"Descripción vulnerabilidad: {vuln.descripcion_vulnerabilidad or '—'}"))
    contenido.append(jira_adf_parrafo(f"Acción correctiva: {plan.accion_correctiva or '—'}"))
    contenido.append(jira_adf_parrafo(f"Responsable SGSI: {plan.responsable or '—'}"))
    contenido.append(jira_adf_parrafo(f"Prioridad: {plan.prioridad or '—'}"))
    contenido.append(jira_adf_parrafo(f"Fecha objetivo: {plan.fecha_objetivo or '—'}"))
    contenido.append(jira_adf_parrafo(f"Recursos necesarios: {plan.recursos_necesarios or '—'}"))
    contenido.append(jira_adf_parrafo(f"Estado interno: {plan.estado or '—'}"))

    return {
        "type": "doc",
        "version": 1,
        "content": contenido
    }


def jira_consultar_issue(issue_key: str):
    if not jira_is_enabled():
        raise RuntimeError("Jira no está configurado correctamente.")

    url = f"{JIRA_BASE_URL.rstrip('/')}/rest/api/3/issue/{issue_key}"
    resp = requests.get(
        url,
        headers=jira_headers(),
        auth=jira_auth(),
        timeout=30
    )

    if resp.status_code != 200:
        raise RuntimeError(f"Error consultando issue Jira: {resp.status_code} - {resp.text}")

    return resp.json()

def _month_range(anio: int, mes: int):
    last_day = calendar.monthrange(anio, mes)[1]
    start = f"{anio:04d}-{mes:02d}-01"
    end   = f"{anio:04d}-{mes:02d}-{last_day:02d}"
    return start, end


# ==========================
# HELPERS Nivel de Madurez
# ==========================
def to_text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, list):
        return "\n".join([to_text(x) for x in v if x is not None])
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False, indent=2)
    return str(v)

def load_instrument_structure(xlsx_path: str):
    xls = pd.ExcelFile(xlsx_path)
    sheets = []
    for sheet_name in xls.sheet_names:
        df = xls.parse(sheet_name, header=None)

        # Detectar si es "ANEXO A" por encabezado "Preguntas" en col 4
        is_anexo_a = False
        if df.shape[0] > 2:
            v = str(df.iloc[1, 4]) if df.shape[1] > 4 else ""
            if "preguntas" in v.lower():
                is_anexo_a = True

        items = []

        if is_anexo_a:
            # Header suele estar en fila 1, preguntas desde fila 3 aprox.
            # Columnas:
            # 0: idx, 1: control, 2: tema, 3: descripcion, 4: pregunta,
            # 5: no aplica, 6: si, 7: parcialmente, 8: no, 9: comentarios
            start_row = 3
            for r in range(start_row, len(df)):
                pregunta = df.iloc[r, 4] if df.shape[1] > 4 else None
                if pd.isna(pregunta) or not str(pregunta).strip():
                    continue

                control = df.iloc[r, 1] if df.shape[1] > 1 else ""
                tema = df.iloc[r, 2] if df.shape[1] > 2 else ""
                items.append({
                    "row": r,
                    "tipo": "q",
                    "control": "" if pd.isna(control) else str(control).strip(),
                    "tema": "" if pd.isna(tema) else str(tema).strip(),
                    "pregunta": str(pregunta).strip(),
                    "layout": "anexo_a"
                })

        else:
            # Capítulos (4-10): encabezado suele estar en fila 0
            # Columnas:
            # 1: pregunta/texto, 2..5 opciones, 6 comentarios
            start_row = 1
            for r in range(start_row, len(df)):
                texto = df.iloc[r, 1] if df.shape[1] > 1 else None
                if pd.isna(texto) or not str(texto).strip():
                    continue

                txt = str(texto).strip()

                # Si parece ser un título de cláusula (ej: "4.1 ...", "5.2 ...") lo marcamos como header
                is_header = bool(
                    (len(txt) < 120) and (
                        txt.startswith(("4.", "5.", "6.", "7.", "8.", "9.", "10.")) and
                        ("¿" not in txt)
                    )
                )

                items.append({
                    "row": r,
                    "tipo": "h" if is_header else "q",
                    "pregunta": txt,
                    "layout": "capitulo"
                })

        sheets.append({
            "name": sheet_name,
            "items": items
        })

    return sheets

def render_action_plan_table(plan: list) -> str:
    if not plan:
        return "<div class='text-muted small'>Aún no se ha generado el plan de acción general.</div>"

    tr = ""
    for row in plan[:250]:
        if not isinstance(row, dict):
            continue
        tr += f"""
        <tr class="cell-small">
          <td class="wrap" style="min-width:260px;">{xml_escape(to_text(row.get("accion")) )}</td>
          <td class="wrap" style="min-width:220px;">{xml_escape(to_text(row.get("proposito")) )}</td>
          <td class="wrap" style="min-width:240px;">{xml_escape(to_text(row.get("evidencia")) )}</td>
          <td class="text-muted" style="min-width:90px;">{xml_escape(to_text(row.get("prioridad")) )}</td>
          <td class="text-muted" style="min-width:90px;">{xml_escape(to_text(row.get("horizonte")) )}</td>
          <td class="wrap" style="min-width:220px;">{xml_escape(to_text(row.get("dependencia")) )}</td>
        </tr>
        """

    return f"""
    <div class="table-responsive mt-2" style="max-height: 460px; overflow:auto;">
      <table class="table table-sm table-striped align-middle table-tight">
        <thead>
          <tr>
            <th>Acción</th>
            <th>Propósito</th>
            <th>Evidencia</th>
            <th>Prioridad</th>
            <th>Horizonte</th>
            <th>Dependencia</th>
          </tr>
        </thead>
        <tbody>
          {tr if tr else "<tr><td colspan='6' class='text-muted'>Sin datos.</td></tr>"}
        </tbody>
      </table>
    </div>
    """

def normalize_action_plan_payload(parsed):
    """
    Acepta respuesta IA como:
      A) {"action_plan":[{...}]}
      B) {"plan":[{...}]}
      C) [{...}, {...}]   <-- lista directa (tu caso)
    Retorna SIEMPRE: {"action_plan":[{...}]}  (dict)
    Además normaliza llaves con acentos: acción->accion, propósito->proposito.
    """
    def _strip_accents_keys(d: dict) -> dict:
        if not isinstance(d, dict):
            return {}
        # mapa de llaves esperadas (acentos -> sin acentos)
        key_map = {
            "acción": "accion",
            "propósito": "proposito",
            "evidéncia": "evidencia",
            "responsáble": "responsable",
            "capítulo": "capitulo",
            "fase": "fase",
            "requisito": "requisito",
            "prioridad": "prioridad",
            "horizonte": "horizonte",
            "dependencia": "dependencia",
        }
        out = {}
        for k, v in d.items():
            kk = (k or "").strip()
            kk_low = kk.lower()
            kk_norm = key_map.get(kk_low, kk_low)

            # también soporta variantes comunes
            if kk_norm == "accion" or kk_norm == "acción":
                kk_norm = "accion"
            elif kk_norm == "proposito" or kk_norm == "propósito":
                kk_norm = "proposito"

            out[kk_norm] = v
        return out

    # 1) determinar lista de filas
    rows = None
    if isinstance(parsed, list):
        rows = parsed
    elif isinstance(parsed, dict):
        # varias llaves posibles
        rows = parsed.get("action_plan") or parsed.get("plan") or parsed.get("acciones")
        if rows is None:
            # a veces viene {"action_plan": {...}} malformado
            rows = []
    else:
        rows = []

    if not isinstance(rows, list):
        rows = []

    # 2) normalizar filas
    cleaned_rows = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        rr = _strip_accents_keys(r)

        cleaned_rows.append({
            # usa tus nombres esperados en UI
            "accion": harden_no_conditionals(to_text(rr.get("accion"))).strip(),
            "proposito": harden_no_conditionals(to_text(rr.get("proposito"))).strip(),
            "evidencia": harden_no_conditionals(to_text(rr.get("evidencia"))).strip(),
            "prioridad": (to_text(rr.get("prioridad")) or "").strip(),
            "horizonte": (to_text(rr.get("horizonte")) or "").strip(),
            "dependencia": harden_no_conditionals(to_text(rr.get("dependencia"))).strip(),
            "responsable": harden_no_conditionals(to_text(rr.get("responsable"))).strip(),
            "capitulo": (to_text(rr.get("capitulo")) or "").strip(),
            "fase": (to_text(rr.get("fase")) or "").strip(),
            "requisito": harden_no_conditionals(to_text(rr.get("requisito"))).strip(),
        })

    return {"action_plan": cleaned_rows}


 
# =========================
# Helper Evidencias SOA
# =========================

EVIDENCE_EXTENSIONS = {"pdf", "doc", "docx", "xls", "xlsx"}

def allowed_evidence_file(filename: str) -> bool:
    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower() in EVIDENCE_EXTENSIONS
    )


# configuración del correo

def get_email_config():
    """
    Obtiene la configuración SMTP desde la base de datos (EmailConfig)
    o como fallback desde variables de entorno.
    """

    # 1️⃣ Intentar desde BD
    try:
        cfg = EmailConfig.query.first()
    except Exception:
        cfg = None

    if cfg:
        return {
            "SMTP_HOST": cfg.smtp_host,
            "SMTP_PORT": int(cfg.smtp_port or 587),
            "SMTP_USER": cfg.smtp_user,
            "SMTP_PASS": cfg.smtp_pass,
            "SMTP_FROM": cfg.smtp_from or cfg.smtp_user,
            "APP_NAME":  cfg.app_name or "SGSI",
        }

    # 2️⃣ Fallback a variables de entorno
    return {
        "SMTP_HOST": os.getenv("SMTP_HOST"),
        "SMTP_PORT": int(os.getenv("SMTP_PORT", "587")),
        "SMTP_USER": os.getenv("SMTP_USER"),
        "SMTP_PASS": os.getenv("SMTP_PASS"),
        "SMTP_FROM": os.getenv("SMTP_FROM"),
        "APP_NAME":  os.getenv("APP_NAME", "SGSI"),
    }

# Tipo de Riesgos

def gattr(obj, name):
    if name == "tipo_riesgo_nombre":
        tr = getattr(obj, "tipo_riesgo", None)
        return tr.nombre if tr else ""
    return getattr(obj, name, None)

# Metricas de Riesgos

RISK_ORDER = ["Bajo", "Moderado", "Alto", "Extremo"]  # orden oficial

def normalize_level(s: str) -> str:
    if s is None:
        return ""
    x = str(s).strip().lower()

    # quitar acentos simples
    x = (x.replace("á","a").replace("é","e").replace("í","i")
           .replace("ó","o").replace("ú","u"))

    # 1) si viene numérico (ej: "16", "20") interpreta como matriz prob*impacto
    if x.isdigit():
        v = int(x)
        if v <= 4:
            return "Bajo"
        elif v <= 9:
            return "Moderado"
        elif v <= 15:
            return "Alto"
        else:
            return "Extremo"

    # 2) sinónimos / variantes comunes
    if x in ["bajo", "low"]:
        return "Bajo"
    if x in ["medio", "moderado", "moderate", "medium"]:
        return "Moderado"
    if x in ["alto", "high"]:
        return "Alto"
    if x in ["Extremo", "extreme ", "severo", "several"]:
        return "Extremo"

    # 3) detección por contains
    if "crit" in x:
        return "Extremo"
    if "alt" in x:
        return "Alto"
    if "mod" in x or "med" in x:
        return "Moderado"
    if "baj" in x:
        return "Bajo"
    return ""

def safe_appetite_level(raw: str, default="Moderado") -> str:
    lvl = normalize_level(raw)
    return lvl if lvl in RISK_ORDER else default

def dominant_level(level_counts: dict) -> str:
    """
    Retorna el nivel dominante (el más frecuente).
    Si hay empate, gana el nivel MÁS alto (Extremo > Crítico > ...).
    """
    best_lvl = ""
    best_count = -1
    for lvl in RISK_ORDER:
        c = int(level_counts.get(lvl, 0) or 0)
        if c > best_count:
            best_count = c
            best_lvl = lvl
        elif c == best_count and c > 0:
            # empate: el más alto según RISK_ORDER
            if level_rank(lvl) > level_rank(best_lvl):
                best_lvl = lvl
    return best_lvl if best_count > 0 else ""

def build_trend_text_dominant(trend_rows):
    if not trend_rows:
        return {
            "inherente": "No hay datos con fecha para analizar tendencia.",
            "residual": "No hay datos con fecha para analizar tendencia.",
        }

    first = trend_rows[0]
    last = trend_rows[-1]

    inh_ini, inh_fin = first["inh_dominante"], last["inh_dominante"]
    res_ini, res_fin = first["res_dominante"], last["res_dominante"]

    def describe(start, end, label):
        if start == "Sin dato" or end == "Sin dato":
            return f"No hay suficiente información para determinar tendencia {label}."
        if start == end:
            return f"La criticidad dominante {label} se mantiene en **{start}**."
        # sube o baja según ranking
        if level_rank(end) > level_rank(start):
            return f"La criticidad dominante {label} **aumenta** de **{start}** a **{end}**."
        else:
            return f"La criticidad dominante {label} **disminuye** de **{start}** a **{end}**."

    return {
        "inherente": describe(inh_ini, inh_fin, "INHERENTE"),
        "residual": describe(res_ini, res_fin, "RESIDUAL"),
    }


def level_rank(level: str) -> int:
    lvl = normalize_level(level)
    if lvl in RISK_ORDER:
        return RISK_ORDER.index(lvl)
    return -1

def is_outside_appetite(residual_level: str, appetite_level: str) -> bool:
    """True si residual >= apetito (umbral)."""
    r = level_rank(residual_level)
    a = level_rank(appetite_level)
    if r < 0 or a < 0:
        return False
    return r >= a

def build_trend_text(trend_rows, order_levels):
    """
    Genera análisis en texto para Inherente y Residual por criticidad.
    Usa la primera y última fila disponible como comparación (inicio vs fin).
    """
    if not trend_rows:
        return {
            "inherente": "No hay datos con fecha para analizar tendencia.",
            "residual": "No hay datos con fecha para analizar tendencia.",
        }

    first = trend_rows[0]
    last = trend_rows[-1]

    def one_side(prefix: str) -> str:
        # prefix: "inh_" o "res_"
        lines = []
        total_first = 0
        total_last = 0

        deltas = []
        for lvl in order_levels:
            a = int(first.get(f"{prefix}{lvl}", 0) or 0)
            b = int(last.get(f"{prefix}{lvl}", 0) or 0)
            d = b - a
            total_first += a
            total_last += b
            deltas.append((lvl, a, b, d))

        # Resumen general
        if total_last > total_first:
            general = f"Aumenta el total ({total_first} → {total_last})."
        elif total_last < total_first:
            general = f"Disminuye el total ({total_first} → {total_last})."
        else:
            general = f"Se mantiene el total ({total_first} → {total_last})."

        # Cambios por criticidad
        changes = []
        for (lvl, a, b, d) in deltas:
            if d > 0:
                changes.append(f"{lvl}: +{d} ({a}→{b})")
            elif d < 0:
                changes.append(f"{lvl}: {d} ({a}→{b})")
            else:
                changes.append(f"{lvl}: 0 ({a}→{b})")

        # Encontrar mayor subida y mayor bajada
        max_up = max(deltas, key=lambda x: x[3])
        max_down = min(deltas, key=lambda x: x[3])

        extra = []
        if max_up[3] > 0:
            extra.append(f"Mayor aumento: {max_up[0]} (+{max_up[3]}).")
        if max_down[3] < 0:
            extra.append(f"Mayor reducción: {max_down[0]} ({max_down[3]}).")

        lines.append(general)
        lines.append("Cambios por criticidad: " + " · ".join(changes) + ".")
        if extra:
            lines.append(" ".join(extra))

        return " ".join(lines)

    return {
        "inherente": one_side("inh_"),
        "residual": one_side("res_"),
    }


def parse_any_date(s: str):
    """Parsea fechas típicas: YYYY-MM-DD, DD/MM/YYYY, etc. Retorna datetime o None."""
    if not s:
        return None
    s = str(s).strip()
    fmts = [
        "%Y-%m-%d", "%Y/%m/%d",
        "%d/%m/%Y", "%d-%m-%Y",
        "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S", "%d-%m-%Y %H:%M:%S",
    ]
    # intento ISO
    try:
        return datetime.fromisoformat(s)
    except Exception:
        pass
    for f in fmts:
        try:
            return datetime.strptime(s, f)
        except Exception:
            continue
    return None

def period_key(dt: datetime, tendencia: str) -> str:
    """Genera llave de periodo según tendencia."""
    y = dt.year
    m = dt.month
    tendencia = (tendencia or "mensual").lower()

    if tendencia == "mensual":
        return f"{y}-{m:02d}"
    if tendencia == "trimestral":
        q = (m - 1) // 3 + 1
        return f"{y}-T{q}"
    if tendencia == "cuatrimestral":
        c = (m - 1) // 4 + 1  # 1..3
        return f"{y}-C{c}"
    if tendencia == "semestral":
        s = 1 if m <= 6 else 2
        return f"{y}-S{s}"
    if tendencia == "anual":
        return f"{y}"

    # fallback
    return f"{y}-{m:02d}"

# mapa de divisiones por área

def divisiones_por_area():
    out = {}
    for a in AreaEmpresa.query.order_by(AreaEmpresa.area.asc(), AreaEmpresa.division.asc()).all():
        if not a.division:
            continue
        out.setdefault(a.id, [])
        if a.division not in out[a.id]:
            out[a.id].append(a.division)
    return out

def get_area_divisiones_map():
    """
    Devuelve un dict: { nombre_area: [división1, división2, ...] } (ordenadas)
    """
    filas = AreaEmpresa.query.order_by(AreaEmpresa.area.asc(),
                                       AreaEmpresa.division.asc()).all()
    m = {}
    for f in filas:
        area = (f.area or "").strip()
        div  = (f.division or "").strip()
        if not area:
            continue
        m.setdefault(area, set())
        if div:
            m[area].add(div)
    # sets -> listas ordenadas
    return {k: sorted(v) for k, v in m.items()}


def get_areaid_divisiones_map():
    """
    Devuelve un dict: { area_id: [división1, división2, ...] } (ordenadas)
    Útil si tus selects usan area_id en lugar del nombre.
    """
    filas = AreaEmpresa.query.order_by(AreaEmpresa.area.asc(),
                                       AreaEmpresa.division.asc()).all()
    m = {}
    for f in filas:
        div = (f.division or "").strip()
        m.setdefault(f.id, set())
        if div:
            m[f.id].add(div)
    return {k: sorted(v) for k, v in m.items()}

# para setear cálculos en servidor

    def calcular_criticidad(self):
        total = (self.valor_alcance or 0) + (self.valor_esencial or 0) + \
                (self.valor_plan_cont or 0) + (self.valor_alternativas or 0) + \
                (self.valor_plan_migracion or 0) + (self.valor_info_sensible or 0)
        self.criticidad_pct = total
        # Reglas pedidas:
        # >61 alta (rojo), >41 media (amarillo), >26 baja (verde oscuro), >1 muy baja (verde claro), si 0 -> muy baja
        if total > 61:
            self.criticidad_texto = "Criticidad alta"
            self.criticidad_color = "badge-rojo"
        elif total > 41:
            self.criticidad_texto = "Criticidad media"
            self.criticidad_color = "badge-amarillo"
        elif total > 26:
            self.criticidad_texto = "Criticidad baja"
            self.criticidad_color = "badge-verde-oscuro"
        elif total > 1:
            self.criticidad_texto = "Criticidad muy baja"
            self.criticidad_color = "badge-verde-claro"
        else:
            self.criticidad_texto = "Criticidad muy baja"
            self.criticidad_color = "badge-verde-claro"

    def calcular_certificados(self):
        # requiere_formulario: No si hay certificación, Sí si no hay
        self.requiere_formulario = "No" if (self.tiene_certificacion == "Sí") else "Sí"
        self.puntos_certificacion = 100 if (self.tiene_certificacion == "Sí") else 0
        if self.puntos_certificacion > 0:
            self.puntos_formulario = 0
        # total + resultado
        total = (self.puntos_certificacion or 0) + (self.puntos_formulario or 0)
        self.calificacion_total = total
        if total > 80:
            self.resultado_evaluacion = "Aprobado"
            self.resultado_color = "badge-aprobado"
        elif total > 60:
            self.resultado_evaluacion = "En revisión"
            self.resultado_color = "badge-revision"
        elif total > 0:
            self.resultado_evaluacion = "No Aprobado"
            self.resultado_color = "badge-noaprob"
        else:
            self.resultado_evaluacion = "No Aprobado"
            self.resultado_color = "badge-noaprob"
            
    def is_allowed_pdf(filename: str) -> bool:
        ext = os.path.splitext(filename.lower())[1]
    return ext in ALLOWED_PDF_EXT

    def unique_store_name(original: str) -> str:
        # evita colisiones y oculta nombres reales
        ext = os.path.splitext(original)[1].lower()
        return f"{uuid4().hex}{ext}"

    def obtener_cargos_desde_areas():
        cargos = set()
        for a in AreaEmpresa.query.all():
            # ajusta los nombres a tu modelo de Áreas
            if getattr(a, 'responsable_cargo', None):
                cargos.add(a.responsable_cargo)
            if getattr(a, 'division_cargo', None):
                cargos.add(a.division_cargo)
        lst = sorted(c for c in cargos if c)
        return lst or ['Analista','Coordinador','Jefe','Gerente']  # fallback

    def attribute(obj, name):
        return getattr(obj, name, None)


    
def extraer_respuestas_desde_excel(path_xlsx):
    """
    Lee el archivo Excel del cuestionario de proveedores y
    devuelve una lista de dicts con:
    - codigo
    - pregunta
    - cumplimiento
    - notas
    """
    xls = pd.ExcelFile(path_xlsx)

    # En tu plantilla el cuestionario está en la hoja "Requerimientos Aplicativos"
    df = xls.parse("Requerimientos Aplicativos", header=None)

    respuestas = []

    # A partir de la fila 36 empiezan las preguntas (según el archivo que subiste)
    # Columna B -> código (1.1, 1.2, etc.)
    # Columna C -> texto de la pregunta
    # Columna I -> Evidencias/Notas
    # Columna J -> Cumplimiento (lo que llenará el proveedor)
    for i in range(36, len(df)):
        cod = df.iloc[i, 1]
        txt = df.iloc[i, 2]

        # Si no hay código ni texto, saltamos
        if (pd.isna(cod) and pd.isna(txt)):
            continue

        # Saltar filas de títulos tipo "Sección 1", "Referencia", etc.
        cod_str = "" if pd.isna(cod) else str(cod).strip()
        txt_str = "" if pd.isna(txt) else str(txt).strip()

        if not txt_str:
            continue

        # Tomamos cumplimiento y notas
        notas = df.iloc[i, 8] if df.shape[1] > 8 else None
        cumpl = df.iloc[i, 9] if df.shape[1] > 9 else None

        notas_str = "" if pd.isna(notas) else str(notas).strip()
        cumpl_str = "" if pd.isna(cumpl) else str(cumpl).strip().upper()

        respuestas.append({
            "codigo": cod_str,
            "pregunta": txt_str,
            "cumplimiento": cumpl_str,
            "notas": notas_str
        })

    return respuestas

def chat_ai(prompt: str, model: str = None) -> str:
    """
    Mantiene la misma firma para no romper módulos existentes,
    pero usa el proveedor activo configurado en Administración.
    """
    ai_cfg = get_openrouter_client()
    provider = ai_cfg.get("provider")

    if provider == "ollama":
        base_url = ai_cfg.get("base_url", "").rstrip("/")
        ollama_model = ai_cfg.get("model") or get_ollama_model() or "llama3.1"

        if not base_url:
            raise RuntimeError("No existe OLLAMA_BASE_URL configurada en Administración.")
        if not ollama_model:
            raise RuntimeError("No existe OLLAMA_MODEL configurado en Administración.")

        resp = requests.post(
            f"{base_url}/api/generate",
            json={
                "model": ollama_model,
                "prompt": f"Responde en español, claro y accionable.\n\n{prompt}",
                "stream": False,
                "options": {
                    "temperature": 0.2
                }
            },
            timeout=300
        )
        resp.raise_for_status()

        data = resp.json() or {}
        return (data.get("response") or "").strip()

    # OpenRouter
    client = ai_cfg["client"]
    model_name = model or ai_cfg.get("model") or OPENROUTER_MODEL or "deepseek/deepseek-chat"

    resp = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "Responde en español, claro y accionable."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    return (resp.choices[0].message.content or "").strip()


# =========================
# Inserta todos los controles si la tabla está vacía
# =========================

def populate_if_needed():
    # Insertar controles iniciales si la tabla está vacía
    if Control.query.first() is None:
        for item in FULL_SOA:
            db.session.add(Control(**item))
        db.session.commit()

    # Crear la tabla de registro de incidentes directamente en SQLite
    conn = sqlite3.connect('sgsi.db')
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS registro_incidentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descripcion_corta TEXT,
            causa TEXT,
            fecha_inicio TEXT,
            fecha_fin TEXT,
            estado_actual TEXT,
            datos_personales_involucrados TEXT,
            violacion_datos_personales TEXT,
            medidas_tomadas TEXT,
            enlace_informe_interno TEXT,
            medidas_prevencion TEXT
        )
    """)
    conn.commit()
    conn.close()


def create_admin():
    if not User.query.filter_by(username='Administrador').first():
        admin = User(username='Administrador', role='admin')
        admin.set_password('Abcd12345%')
        db.session.add(admin)
        db.session.commit()


# =========================
# Inicialización de BD al arrancar (compatible con Flask 3.x)
# =========================

with app.app_context():
    db.create_all()
    populate_if_needed()
    create_admin()


# =========================
# Export CSV (descargar todo)
# =========================

@app.route('/export')
def export_csv():
    controls = Control.query.order_by(Control.nr).all()
    si = io.StringIO()
    fieldnames = ['nr','chapter','topic','control_text','applicable','justification','motivation','implemented']
    writer = csv.DictWriter(si, fieldnames=fieldnames)
    writer.writeheader()
    for c in controls:
        writer.writerow(c.to_dict())
    mem = io.BytesIO()
    mem.write(si.getvalue().encode('utf-8'))
    mem.seek(0)
    return send_file(mem, as_attachment=True, download_name='soa_iso27001_export.csv', mimetype='text/csv')

# =========================
# Ruta para descargar via send_file necesita BytesIO importado
# =========================

from io import BytesIO as _BytesIO
def io_BytesIO(b): return _BytesIO(b)

# =========================
# Ajuste para send_file con BytesIO: re-definimos send_file wrapper
# =========================
from flask import Response
@app.route('/export_alt')
def export_csv_alt():
    controls = Control.query.order_by(Control.nr).all()
    si = io.StringIO()
    fieldnames = ['nr','chapter','topic','control_text','applicable','justification','motivation','implemented']
    writer = csv.DictWriter(si, fieldnames=fieldnames)
    writer.writeheader()
    for c in controls:
        writer.writerow(c.to_dict())
    data = si.getvalue().encode('utf-8')
    return Response(data, mimetype='text/csv', headers={'Content-Disposition':'attachment;filename=soa_iso27001_export.csv'})

# =========================
# Atajo: /export redirige a /export_alt si send_file falla
# =========================
@app.route('/export')
def export_csv_redirect():
    return export_csv_alt()

# =========================
# Manejador de errores simple
# =========================
@app.errorhandler(Exception)
def handle_all_errors(e):
    # si es un error HTTP normal (404, 403, etc.), respétalo
    if isinstance(e, HTTPException):
        return e

    tb = traceback.format_exc()
    html = f"""
    <div class="alert alert-danger">
      <h5 class="mb-2">Error interno real (traceback)</h5>
      <pre style="white-space:pre-wrap; font-size:12px; max-height:520px; overflow:auto;">{tb}</pre>
    </div>
    """
    return render_template_string(BASE, content=html), 500

# =========================
# Persona Empresas
# =========================
def get_personas_empresa():
    try:
        return EmpresaPersona.query.order_by(EmpresaPersona.nombre.asc()).all()
    except Exception:
        return []


# ============================================================================================================================================
#                                                               Autenticación de Usuarios
# ============================================================================================================================================

from functools import wraps
from flask import (
    render_template_string,
    request,
    redirect,
    url_for,
    flash,
    session,
    send_file
)

import pyotp
import qrcode
import io
import base64

from io import BytesIO


# =========================
# DECORADOR DE LOGIN
# =========================
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash("Por favor, inicia sesión.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = User.query.get(session.get('user_id'))

        if not user or user.role != 'admin':
            flash("Acceso solo permitido a administradores.", "danger")
            return redirect(url_for('menu'))

        return f(*args, **kwargs)

    return wrapper


def admin_or_access_manager_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = User.query.get(session.get('user_id'))

        if not user or user.role not in ('admin', 'gestor_accesos'):
            flash(
                "Acceso solo permitido a administradores o gestores de accesos.",
                "danger"
            )
            return redirect(url_for('menu'))

        return f(*args, **kwargs)

    return wrapper


def verify_otp(user, otp_code):
    if not user or not user.otp_secret:
        return False

    totp = pyotp.TOTP(user.otp_secret)
    return totp.verify(otp_code)


# ============================================================================================================================================
#                                                           RENDER QR OTP
# ============================================================================================================================================
def _render_qr_otp_setup(user, secret):

    otp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=user.username,
        issuer_name="SGSI"
    )

    qr = qrcode.make(otp_uri)

    buffer = io.BytesIO()

    qr.save(buffer, format="PNG")

    qr_data = base64.b64encode(buffer.getvalue()).decode()

    content = f"""
    <div class="col-md-6 offset-md-3 text-center">

        <h3>Configuración de Autenticación en Dos Pasos</h3>

        <div class="alert alert-info">
            Escanea este código QR con Google Authenticator,
            Microsoft Authenticator o Authy.
            Luego ingresa el código de 6 dígitos para activar el token.
        </div>

        <img src="data:image/png;base64,{qr_data}"
             class="img-fluid mb-3"
             alt="QR Code"
             style="max-width:260px;">

        <form method="post"
              action="{url_for('verificar_otp')}"
              autocomplete="off"
              autocorrect="off"
              autocapitalize="none"
              spellcheck="false">

            <input type="hidden" name="username" value="{user.username}">
            <input type="hidden" name="modo" value="setup">

            <div class="mt-3 mb-3">
                <label class="form-label fw-bold">
                    Código de Verificación
                </label>

                <input class="form-control text-center"
                       name="otp"
                       type="password"
                       inputmode="numeric"
                       pattern="[0-9]{{6}}"
                       maxlength="6"
                       placeholder="••••••"
                       required
                       autocomplete="off"
                       autocorrect="off"
                       autocapitalize="none"
                       spellcheck="false">
            </div>

            <button class="btn btn-success rounded-pill px-4">
                Activar token
            </button>

            <a href="{url_for('login')}"
               class="btn btn-secondary rounded-pill px-4">
                Cancelar
            </a>

        </form>
    </div>
    """

    return render_template_string(BASE, content=content)


# ============================================================================================================================================
#                                                               LOGIN
# ============================================================================================================================================
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username_ingresado = (
            request.form.get('sgsi_user_secure') or
            ""
        ).strip()

        password_ingresado = (
            request.form.get('sgsi_password_secure') or
            ""
        )

        user = User.query.filter_by(
            username=username_ingresado
        ).first()

        # ============================================================
        # LOGIN CORRECTO
        # ============================================================
        if user and user.check_password(password_ingresado):

            # =====================================================
            # USUARIO SIN OTP CONFIGURADO
            # =====================================================
            if not user.otp_secret:

                secret_temporal = pyotp.random_base32()

                session['temp_user'] = user.username
                session['pending_otp_secret'] = secret_temporal

                return _render_qr_otp_setup(
                    user,
                    secret_temporal
                )

            # =====================================================
            # USUARIO YA TIENE OTP
            # =====================================================
            session['temp_user'] = user.username

            session.pop(
                'pending_otp_secret',
                None
            )

            return redirect(
                url_for('verificar_otp')
            )

        # ============================================================
        # LOGIN FALLIDO
        # ============================================================
        registrar_log(
            username_ingresado or "Desconocido",
            (
                "Acceso fallido al sistema. "
                f"Usuario o contraseña inválida: "
                f"{username_ingresado or 'Desconocido'}"
            )
        )

        flash(
            "Usuario o contraseña incorrectos.",
            "danger"
        )

    # ====================================================================
    # HTML LOGIN
    # ====================================================================
    content = """
    <style>

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

      .login-card{
        background:#ffffff;
        border-radius:24px;
        padding:32px;
        box-shadow:0 10px 30px rgba(15,23,42,.08);
      }

      .login-title{
        font-size:2rem;
        font-weight:900;
        text-align:center;
        margin-bottom:24px;
        color:#1e293b;
      }

      .login-label{
        font-weight:800;
        margin-bottom:8px;
        color:#334155;
      }

      .login-input{
        height:52px;
        border-radius:14px;
        border:1px solid #dbe2ea;
        font-size:1rem;
        padding-left:14px;
        transition:.2s ease;
      }

      .login-input:focus{
        border-color:#3f86d6;
        box-shadow:0 0 0 .18rem rgba(63,134,214,.15);
      }

      .login-btn{
        height:52px;
        border-radius:14px;
        font-weight:900;
        font-size:1rem;
        background:#3f86d6;
        border:none;
      }

      .login-btn:hover{
        background:#2f6fb6;
      }

    </style>

    <div class="col-md-4 offset-md-4">

      <div class="login-card">

        <div class="login-title">
          Iniciar sesión
        </div>

        <form method="post"
              id="sgsiLoginForm"
              autocomplete="off"
              autocorrect="off"
              autocapitalize="none"
              spellcheck="false">

            <!-- CAMPOS TRAMPA -->
            <input type="text"
                   style="display:none"
                   tabindex="-1"
                   autocomplete="off">

            <input type="password"
                   style="display:none"
                   tabindex="-1"
                   autocomplete="new-password">

            <!-- USUARIO -->
            <div class="mb-3">

              <label class="login-label">
                Usuario
              </label>

              <input class="form-control login-input"
                     id="sgsi_user_secure"
                     name="sgsi_user_secure"
                     type="text"
                     required

                     autocomplete="off"
                     autocorrect="off"
                     autocapitalize="none"
                     spellcheck="false"

                     data-form-type="other"

                     readonly
                     onfocus="this.removeAttribute('readonly');"

                     placeholder="Digite su usuario">

            </div>

            <!-- PASSWORD -->
            <div class="mb-4">

              <label class="login-label">
                Contraseña
              </label>

              <input class="form-control login-input"
                     id="sgsi_password_secure"
                     name="sgsi_password_secure"
                     type="password"
                     required

                     autocomplete="off"
                     autocorrect="off"
                     autocapitalize="none"
                     spellcheck="false"

                     data-form-type="other"
                     data-lpignore="true"

                     readonly
                     onfocus="this.removeAttribute('readonly');"

                     placeholder="••••••••">

            </div>

            <button class="btn btn-primary w-100 login-btn">
              Ingresar
            </button>

        </form>

      </div>

    </div>

    <script>

    document.addEventListener('DOMContentLoaded', function(){

        const form = document.getElementById('sgsiLoginForm');

        const user = document.getElementById('sgsi_user_secure');

        const pass = document.getElementById('sgsi_password_secure');

        // LIMPIAR AUTOFILL
        if(user){
            user.value = '';

            setTimeout(function(){
                user.value = '';
            }, 100);
        }

        if(pass){
            pass.value = '';

            setTimeout(function(){
                pass.value = '';
            }, 100);
        }

        // BLOQUEAR DETECCIÓN DE LOGIN
        if(form){

            form.setAttribute(
                'autocomplete',
                'off'
            );

            form.addEventListener(
                'submit',
                function(){

                    user.setAttribute(
                        'autocomplete',
                        'off'
                    );

                    pass.setAttribute(
                        'autocomplete',
                        'new-password'
                    );

                }
            );

        }

        // DESBLOQUEAR READONLY AL HACER FOCUS
        [user, pass].forEach(function(el){

            if(!el) return;

            el.addEventListener('focus', function(){

                this.removeAttribute(
                    'readonly'
                );

                this.setAttribute(
                    'autocomplete',
                    'off'
                );

            });

        });

    });

    </script>
    """

    return render_template_string(
        BASE,
        content=content
    )


# ============================================================================================================================================
#                                                               OTP
# ============================================================================================================================================
@app.route('/verificar_otp', methods=['GET', 'POST'])
def verificar_otp():

    username = session.get('temp_user')

    if not username:
        flash(
            "Primero inicia sesión.",
            "warning"
        )

        return redirect(
            url_for('login')
        )

    user = User.query.filter_by(
        username=username
    ).first()

    if not user:

        session.pop('temp_user', None)

        session.pop(
            'pending_otp_secret',
            None
        )

        registrar_log(
            username or "Desconocido",
            (
                "Acceso fallido al sistema. "
                "Usuario no encontrado "
                f"en verificación OTP: "
                f"{username or 'Desconocido'}"
            )
        )

        flash(
            "Usuario no encontrado.",
            "danger"
        )

        return redirect(
            url_for('login')
        )

    if request.method == 'POST':

        otp = (
            request.form.get('otp') or ""
        ).strip()

        modo = (
            request.form.get('modo') or ""
        ).strip()

        # =====================================================
        # CONFIGURACIÓN INICIAL OTP
        # =====================================================
        if modo == "setup":

            secret_temporal = session.get(
                'pending_otp_secret'
            )

            if not secret_temporal:

                flash(
                    "La configuración del token expiró. "
                    "Inicia sesión nuevamente.",
                    "warning"
                )

                return redirect(
                    url_for('login')
                )

            totp = pyotp.TOTP(
                secret_temporal
            )

            if totp.verify(otp):

                user.otp_secret = secret_temporal

                db.session.commit()

                session['user_id'] = user.id
                session['username'] = user.username
                session['role'] = user.role

                session.pop(
                    'temp_user',
                    None
                )

                session.pop(
                    'pending_otp_secret',
                    None
                )

                registrar_log(
                    user.username,
                    (
                        "Acceso exitoso al sistema. "
                        "Token OTP configurado "
                        f"y usuario autenticado "
                        f"con perfil: {user.role}"
                    )
                )

                flash(
                    f"Token configurado correctamente. "
                    f"Bienvenido {user.username}",
                    "success"
                )

                return redirect(
                    url_for('menu')
                )

            registrar_log(
                user.username,
                (
                    "Configuración OTP fallida. "
                    f"Código inválido para "
                    f"el usuario: {user.username}"
                )
            )

            flash(
                "Código OTP inválido. "
                "Escanea el QR e intenta nuevamente.",
                "danger"
            )

            return _render_qr_otp_setup(
                user,
                secret_temporal
            )

        # =====================================================
        # LOGIN NORMAL OTP
        # =====================================================
        if not user.otp_secret:

            flash(
                "Este usuario aún no tiene "
                "token configurado. "
                "Inicia sesión nuevamente.",
                "warning"
            )

            return redirect(
                url_for('login')
            )

        totp = pyotp.TOTP(
            user.otp_secret
        )

        if totp.verify(otp):

            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role

            session.pop(
                'temp_user',
                None
            )

            session.pop(
                'pending_otp_secret',
                None
            )

            registrar_log(
                user.username,
                (
                    "Acceso exitoso al sistema. "
                    "Usuario autenticado "
                    f"correctamente con perfil: "
                    f"{user.role}"
                )
            )

            flash(
                f"Bienvenido {user.username}",
                "success"
            )

            return redirect(
                url_for('menu')
            )

        registrar_log(
            user.username,
            (
                "Acceso fallido al sistema. "
                f"OTP inválido para el usuario: "
                f"{user.username}"
            )
        )

        flash(
            "Código OTP inválido, intente de nuevo.",
            "danger"
        )

    # ====================================================================
    # HTML OTP
    # ====================================================================
    content = f"""
    <div class="col-md-4 offset-md-4 text-center">

      <h3>Verificación de Código OTP</h3>

      <form method="post"
            autocomplete="off"
            autocorrect="off"
            autocapitalize="none"
            spellcheck="false">

        <input type="hidden"
               name="username"
               value="{user.username}">

        <div class="mb-3">

          <label>
            Código OTP
          </label>

          <input class="form-control text-center"
                 name="otp"
                 type="password"
                 inputmode="numeric"
                 pattern="[0-9]{{6}}"
                 maxlength="6"
                 placeholder="••••••"
                 required
                 autocomplete="off"
                 autocorrect="off"
                 autocapitalize="none"
                 spellcheck="false">

        </div>

        <button class="btn btn-success rounded-pill px-4">
          Verificar
        </button>

        <a href="{url_for('login')}"
           class="btn btn-secondary rounded-pill px-4">
          Cancelar
        </a>

      </form>

    </div>
    """

    return render_template_string(
        BASE,
        content=content
    )


# ============================================================================================================================================
#                                                           GENERAR OTP
# ============================================================================================================================================
@app.route('/generar_otp/<username>')
def generar_otp(username):

    user = User.query.filter_by(
        username=username
    ).first()

    if not user:
        return "Usuario no encontrado", 404

    secret = (
        user.otp_secret or
        session.get('pending_otp_secret') or
        pyotp.random_base32()
    )

    session['temp_user'] = user.username

    session['pending_otp_secret'] = secret

    otp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=username,
        issuer_name="Sistema ISO27001"
    )

    img = qrcode.make(otp_uri)

    buffer = BytesIO()

    img.save(buffer, format="PNG")

    buffer.seek(0)

    return send_file(
        buffer,
        mimetype='image/png'
    )


# ============================================================================================================================================
#                                                               LOGOUT
# ============================================================================================================================================
@app.route('/logout')
def logout():

    try:
        _browser_session_revoke()
    except Exception as exc:
        print("No se pudo revocar la sesión al cerrar manualmente:", repr(exc))

    session.clear()

    flash(
        "Sesión finalizada",
        "info"
    )

    return redirect(
        url_for('login')
    )


# ============================================================================================================================================
#                                                   Fin módulo de Autenticación
# ============================================================================================================================================

# ============================================================================================================================================
#                                                                   Módulo de Perfil
# ============================================================================================================================================

@app.context_processor
def inject_user():
    u = None
    if 'user_id' in session:
        u = User.query.get(session.get('user_id'))
    return dict(current_user=u)

@app.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    user = User.query.get(session.get("user_id"))

    if request.method == "POST":
        accion = request.form.get("accion")

        # ============================
        # A) Subir foto
        # ============================
        if accion == "subir_foto":
            f = request.files.get("foto")
            if not f or f.filename == "":
                flash("Selecciona una imagen.", "warning")
                return redirect(url_for("perfil"))

            if not allowed_file(f.filename):
                flash("Formato no permitido. Usa PNG/JPG/JPEG/WEBP.", "danger")
                return redirect(url_for("perfil"))

            ext = f.filename.rsplit(".", 1)[1].lower()
            filename = secure_filename(f"{uuid4().hex}.{ext}")
            path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            f.save(path)

            # (Opcional) borrar foto anterior
            if user.photo_filename:
                old_path = os.path.join(app.config["UPLOAD_FOLDER"], user.photo_filename)
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except:
                        pass

            user.photo_filename = filename
            db.session.commit()
            flash("Foto actualizada.", "success")
            return redirect(url_for("perfil"))

        # ============================
        # B) Cambiar contraseña
        # ============================
        if accion == "cambiar_password":
            actual = request.form.get("password_actual") or ""
            nueva = request.form.get("password_nueva") or ""
            confirma = request.form.get("password_confirma") or ""

            if not user.check_password(actual):
                flash("La contraseña actual no es correcta.", "danger")
                return redirect(url_for("perfil"))

            if len(nueva) < 10:
                flash("La nueva contraseña debe tener mínimo 10 caracteres.", "warning")
                return redirect(url_for("perfil"))

            # regla mínima: 1 mayúscula + 1 especial
            especiales = set("!@#$%^&*()-_=+[]{};:,.?/\\|`~")
            if not any(c.isupper() for c in nueva):
                flash("La nueva contraseña debe incluir al menos 1 mayúscula.", "warning")
                return redirect(url_for("perfil"))
            if not any(c in especiales for c in nueva):
                flash("La nueva contraseña debe incluir al menos 1 caracter especial.", "warning")
                return redirect(url_for("perfil"))

            if nueva != confirma:
                flash("La confirmación no coincide.", "warning")
                return redirect(url_for("perfil"))

            user.set_password(nueva)
            db.session.commit()
            flash("Contraseña cambiada correctamente.", "success")
            return redirect(url_for("perfil"))

    # URL de avatar
    avatar_url = (
        url_for("static", filename=f"uploads/profiles/{user.photo_filename}")
        if user.photo_filename
        else url_for("static", filename="img/default_user.png")  # crea esta imagen
    )

    inner = render_template_string("""
    <div class="perfil-shell">

      <!-- HEADER SGSI -->
      <div class="perfil-header-card">
        <div class="perfil-header-overlay">
          <div class="perfil-header-text">
            <h3 class="perfil-title m-0">Perfil de usuario</h3>
            <div class="perfil-subtitle">
              Administra tu foto de perfil y actualiza tu contraseña de acceso
            </div>
          </div>
        </div>
      </div>

      <div class="perfil-card">
        <div class="card-body">

          <!-- DATOS USUARIO -->
          <div class="perfil-section-title">Información del usuario</div>

          <div class="perfil-user-box mb-4">
            <img src="{{ avatar_url }}" alt="Foto" class="perfil-avatar">

            <div class="perfil-user-info">
              <div class="perfil-user-name">👤 {{ user.username }}</div>
              <div class="perfil-user-meta">Rol: <b>{{ user.role }}</b></div>
              {% if user.email %}
                <div class="perfil-user-meta">Correo: <b>{{ user.email }}</b></div>
              {% endif %}
            </div>
          </div>

          <!-- FOTO -->
          <div class="perfil-section-title">🖼️ Cambiar foto</div>

          <form method="POST" enctype="multipart/form-data" class="mb-4">
            <input type="hidden" name="accion" value="subir_foto">

            <div class="row g-3 align-items-end">
              <div class="col-md-8">
                <label class="form-label fw-semibold">Seleccionar imagen</label>
                <input type="file" name="foto" class="form-control" accept="image/*" required>
              </div>
              <div class="col-md-4 text-md-end">
                <button class="btn btn-primary rounded-pill px-4 fw-semibold">Subir foto</button>
              </div>
            </div>
          </form>

          <!-- CONTRASEÑA -->
          <div class="perfil-section-title">🔑 Cambiar contraseña</div>

          <form method="POST">
            <input type="hidden" name="accion" value="cambiar_password">

            <div class="row g-3">
              <div class="col-md-4">
                <label class="form-label fw-semibold">Contraseña actual</label>
                <input type="password" name="password_actual" class="form-control" required>
              </div>

              <div class="col-md-4">
                <label class="form-label fw-semibold">Nueva contraseña</label>
                <input type="password" name="password_nueva" class="form-control" required>
                <div class="text-muted small mt-1">Mínimo 10 caracteres, 1 mayúscula y 1 carácter especial</div>
              </div>

              <div class="col-md-4">
                <label class="form-label fw-semibold">Confirmar contraseña</label>
                <input type="password" name="password_confirma" class="form-control" required>
              </div>
            </div>

            <div class="text-center text-md-start">
              <button class="btn btn-success rounded-pill px-4 fw-semibold mt-4">Guardar contraseña</button>
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

      .perfil-shell{
        width:96%;
        max-width:1200px;
        margin:26px auto 24px auto;
      }

      .perfil-header-card{
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

      .perfil-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .perfil-header-overlay{
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

      .perfil-header-overlay::before{
        content:"👤";
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

      .perfil-header-text{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
      }

      .perfil-header-text::before{
        content:"SGSI · Perfil de Usuario";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .perfil-title{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .perfil-subtitle{
        color:rgba(255,255,255,.95);
        font-size:.78rem;
        margin-top:4px;
        line-height:1.25;
        font-weight:800;
      }

      .perfil-header-actions{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .perfil-header-actions .btn,
      .perfil-btn-main,
      .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 22px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      .perfil-btn-main{
        background:#ffffff;
        color:#0f172a !important;
        border:1px solid #cfd8e3 !important;
      }

      .perfil-btn-main:hover{
        background:#edf5ff;
        color:#0b65d8 !important;
        border-color:#9ec5fe !important;
      }

      .perfil-card,
      .card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }

      .perfil-card .card-body{
        padding:22px;
      }

      .perfil-section-title,
      .card h5,
      .card h6{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        padding-bottom:8px;
        border-bottom:2px solid rgba(59,130,246,.18);
        margin-bottom:16px;
      }

      .perfil-user-box{
        display:flex;
        align-items:center;
        gap:18px;
        background:#f8fbff;
        border:1px solid #dbe6f4;
        border-radius:16px;
        padding:16px;
        box-shadow:0 8px 18px rgba(15,23,42,.08);
      }

      .perfil-avatar{
        width:78px;
        height:78px;
        border-radius:50%;
        object-fit:cover;
        border:3px solid #0b4a8f;
        box-shadow:0 6px 16px rgba(0,0,0,.12);
        flex:0 0 auto;
      }

      .perfil-user-info{
        min-width:0;
      }

      .perfil-user-name{
        font-size:1.05rem;
        font-weight:950;
        color:#101827;
        line-height:1.2;
        margin-bottom:4px;
      }

      .perfil-user-meta{
        color:#607086;
        font-size:.90rem;
        line-height:1.35;
        font-weight:700;
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

      @media (max-width:992px){
        .perfil-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .perfil-header-card{
          min-height:88px;
        }

        .perfil-title{
          font-size:1.20rem;
        }

        .perfil-subtitle{
          font-size:.68rem;
        }

        .perfil-card .card-body{
          padding:16px;
        }

        .perfil-user-box{
          flex-direction:column;
          align-items:flex-start;
          text-align:left;
        }
      }

      @media (max-width:768px){
        .perfil-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .perfil-header-overlay::before{
          margin:0;
        }

        .perfil-header-text::before{
          margin-left:auto;
          margin-right:auto;
        }

        .perfil-title,
        .perfil-subtitle{
          text-align:center;
        }

        .perfil-header-actions .btn{
          width:100%;
        }
      }
    </style>
    """, user=user, avatar_url=avatar_url)

    return render_template_string(BASE, content=Markup(inner))


# ============================================================================================================================================
#                                                                   Fin del módulo de Perfil
# ============================================================================================================================================

# ============================================================================================================================================
#                                                               Módulo de envio del password
# ============================================================================================================================================

