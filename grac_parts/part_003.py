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
          <td><div class="d-flex flex-wrap gap-1">{% if event.status not in ['resuelta','descartada'] %}<form method="post"><input type="hidden" name="event_id" value="{{ event.id }}"><input type="hidden" name="action" value="acknowledge"><button class="btn btn-sm btn-outline-warning" title="Reconocer"><i class="bi bi-eye"></i></button></form><form method="post"><input type="hidden" name="event_id" value="{{ event.id }}"><input type="hidden" name="action" value="resolve"><button class="btn btn-sm btn-outline-success" title="Resolver"><i class="bi bi-check2-circle"></i></button></form><form method="post"><input type="hidden" name="event_id" value="{{ event.id }}"><input type="hidden" name="action" value="discard"><button class="btn btn-sm btn-outline-secondary" title="Descartar"><i class="bi bi-x-circle"></i></button></form>{% endif %}</div></td></tr>
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
                            <button type="button"
                                    title="Eliminar archivo"
                                    onclick="deleteEvidence({{ r.id }}, '{{ file }}', 'file-{{ r.id }}-{{ loop.index }}')">
                              🗑️
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
              eliminarBtn.textContent = "❌";
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
