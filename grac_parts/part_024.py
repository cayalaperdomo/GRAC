@app.route("/planes_accion/<int:plan_id>/eliminar", methods=["POST"])
@login_required
def planes_accion_delete(plan_id):
    user, response = pa_require_write()
    if response:
        return response

    plan = ContinuousActionPlan.query.get_or_404(plan_id)
    deleted_title = plan.title or "Plan de acción"
    source_ref = (plan.source_ref or "").strip()
    suppression_refs = set()

    if pa_source_is_automatic(source_ref):
        suppression_refs.add(source_ref)

    # Un plan manual de un riesgo también puede provenir de la sincronización.
    try:
        raw_data = json.loads(plan.raw_json or "{}")
        risk_source_id = raw_data.get("riesgo_id") if isinstance(raw_data, dict) else None
        if risk_source_id:
            suppression_refs.add(f"riesgo-existente:{risk_source_id}")
    except (TypeError, ValueError, json.JSONDecodeError):
        pass

    for suppressed_ref in suppression_refs:
        suppression = ContinuousActionPlanSuppression.query.filter_by(
            source_ref=suppressed_ref
        ).first()
        if suppression is None:
            suppression = ContinuousActionPlanSuppression(source_ref=suppressed_ref)
            db.session.add(suppression)
        suppression.deleted_plan_id = plan.id
        suppression.deleted_title = deleted_title[:500]
        suppression.deleted_by = pa_username(user)
        suppression.deleted_at = datetime.utcnow()

    db.session.delete(plan)
    db.session.commit()
    registrar_log(
        pa_username(user),
        f"Eliminó el plan de acción {plan_id}: {deleted_title}.",
    )
    flash("Plan de acción eliminado correctamente.", "success")
    return redirect(url_for("planes_accion_dashboard"))

# ============================================================================================================================================
#                         FIN CAPÍTULO INDEPENDIENTE: PLAN DE ACCIÓN
# ============================================================================================================================================


# ============================================================================================================================================
#                         MÓDULO GOBIERNO DE FIREWALL - CUMPLIMIENTO CONTINUO
#                         Conector OPNsense API + análisis + DB independiente firewall_governance.db
# ============================================================================================================================================

from sqlalchemy import or_

FIREWALL_GOV_VENDOR_OPNSENSE = "OPNsense"
FIREWALL_GOV_DEFAULT_URL = "https://192.168.100.10"
FIREWALL_GOV_SEVERITY_ORDER = {"Crítica": 4, "Alta": 3, "Media": 2, "Baja": 1, "Informativa": 0}
FIREWALL_GOV_SEVERITY_SCORE = {"Crítica": 25, "Alta": 15, "Media": 8, "Baja": 3, "Informativa": 0}


class FirewallGovDevice(db.Model):
    __tablename__ = "firewall_gov_devices"
    __bind_key__ = "firewall_governance"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    vendor = db.Column(db.String(80), nullable=False, default=FIREWALL_GOV_VENDOR_OPNSENSE)
    base_url = db.Column(db.String(500), nullable=False, default=FIREWALL_GOV_DEFAULT_URL)
    api_key_encrypted = db.Column(db.Text, nullable=True)
    api_secret_encrypted = db.Column(db.Text, nullable=True)
    verify_ssl = db.Column(db.Boolean, nullable=False, default=False)
    timeout_seconds = db.Column(db.Integer, nullable=False, default=30)
    search_phrase = db.Column(db.String(255), nullable=True, default="GRAC-")
    category_filter = db.Column(db.String(255), nullable=True, default="GRAC_LAB")
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    last_status = db.Column(db.String(50), nullable=True, default="No probado")
    last_message = db.Column(db.Text, nullable=True)
    last_test_at = db.Column(db.DateTime, nullable=True)
    last_sync_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FirewallGovRule(db.Model):
    __tablename__ = "firewall_gov_rules"
    __bind_key__ = "firewall_governance"

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey("firewall_gov_devices.id"), nullable=False, index=True)
    external_id = db.Column(db.String(255), nullable=False, index=True)
    name = db.Column(db.String(500), nullable=True)
    description = db.Column(db.Text, nullable=True)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    action = db.Column(db.String(50), nullable=True)
    quick = db.Column(db.Boolean, nullable=False, default=True)
    interface = db.Column(db.String(255), nullable=True)
    direction = db.Column(db.String(50), nullable=True)
    ip_version = db.Column(db.String(50), nullable=True)
    protocol = db.Column(db.String(100), nullable=True)
    source = db.Column(db.Text, nullable=True)
    source_port = db.Column(db.String(255), nullable=True)
    destination = db.Column(db.Text, nullable=True)
    destination_port = db.Column(db.String(255), nullable=True)
    gateway = db.Column(db.String(255), nullable=True)
    schedule = db.Column(db.String(255), nullable=True)
    logging_enabled = db.Column(db.Boolean, nullable=False, default=False)
    category = db.Column(db.String(255), nullable=True)
    sequence = db.Column(db.Integer, nullable=True)
    sort_order = db.Column(db.Float, nullable=True)
    owner = db.Column(db.String(255), nullable=True)
    ticket = db.Column(db.String(255), nullable=True)
    review_date = db.Column(db.String(20), nullable=True)
    expiration_date = db.Column(db.String(20), nullable=True)
    justification = db.Column(db.Text, nullable=True)
    fingerprint = db.Column(db.String(64), nullable=True, index=True)
    raw_json = db.Column(db.Text, nullable=True)
    active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    first_seen_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("device_id", "external_id", name="uq_firewall_gov_rule_device_external"),
    )


class FirewallGovFinding(db.Model):
    __tablename__ = "firewall_gov_findings"
    __bind_key__ = "firewall_governance"

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey("firewall_gov_devices.id"), nullable=False, index=True)
    rule_id = db.Column(db.Integer, db.ForeignKey("firewall_gov_rules.id"), nullable=True, index=True)
    finding_key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    finding_code = db.Column(db.String(120), nullable=False, index=True)
    severity = db.Column(db.String(30), nullable=False, default="Media", index=True)
    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text, nullable=True)
    recommendation = db.Column(db.Text, nullable=True)
    control_mapping = db.Column(db.Text, nullable=True)
    rule_external_id = db.Column(db.String(255), nullable=True)
    rule_name = db.Column(db.String(500), nullable=True)
    related_rule_external_id = db.Column(db.String(255), nullable=True)
    technical_detail = db.Column(db.Text, nullable=True)
    risk_score = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(50), nullable=False, default="Abierto", index=True)
    assigned_to = db.Column(db.String(255), nullable=True)
    management_comment = db.Column(db.Text, nullable=True)
    active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    first_detected_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_detected_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FirewallGovSyncLog(db.Model):
    __tablename__ = "firewall_gov_sync_logs"
    __bind_key__ = "firewall_governance"

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey("firewall_gov_devices.id"), nullable=False, index=True)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    finished_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), nullable=False, default="En proceso")
    message = db.Column(db.Text, nullable=True)
    endpoint_used = db.Column(db.String(500), nullable=True)
    rules_received = db.Column(db.Integer, default=0)
    rules_active = db.Column(db.Integer, default=0)
    findings_active = db.Column(db.Integer, default=0)
    critical_findings = db.Column(db.Integer, default=0)
    compliance_score = db.Column(db.Float, default=100)
    executed_by = db.Column(db.String(255), nullable=True)


def fwgov_init_db():
    """
    Inicializa exclusivamente las tablas del módulo Gobierno de Firewall
    dentro de instance/firewall_governance.db.

    No crea ni modifica estas tablas en la base principal sgsi.db.
    """
    try:
        os.makedirs(app.instance_path, exist_ok=True)
        with app.app_context():
            try:
                # Flask-SQLAlchemy 3.x
                db.create_all(bind_key="firewall_governance")
            except TypeError:
                # Compatibilidad con Flask-SQLAlchemy 2.x
                db.create_all(bind="firewall_governance")
    except Exception as exc:
        print("No se pudo inicializar Gobierno de Firewall en", FIREWALL_GOV_DB_PATH, ":", repr(exc))


fwgov_init_db()


def fwgov_current_username(user=None):
    return (
        getattr(user, "username", None)
        or session.get("username")
        or "Sistema"
    )


def fwgov_get_fernet():
    env_key = (os.getenv("FIREWALL_GOV_FERNET_KEY") or "").strip()
    if env_key:
        try:
            return Fernet(env_key.encode("utf-8"))
        except Exception as exc:
            raise RuntimeError("FIREWALL_GOV_FERNET_KEY no contiene una clave Fernet válida.") from exc

    os.makedirs(app.instance_path, exist_ok=True)
    key_path = os.path.join(app.instance_path, "firewall_governance.key")

    if os.path.exists(key_path):
        with open(key_path, "rb") as fh:
            key = fh.read().strip()
    else:
        key = Fernet.generate_key()
        with open(key_path, "wb") as fh:
            fh.write(key)
        try:
            os.chmod(key_path, 0o600)
        except Exception:
            pass

    return Fernet(key)


def fwgov_encrypt(value):
    value = (value or "").strip()
    if not value:
        return None
    return fwgov_get_fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def fwgov_decrypt(value):
    value = (value or "").strip()
    if not value:
        return ""
    try:
        return fwgov_get_fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError, TypeError):
        return ""


def fwgov_bool(value):
    return str(value or "").strip().lower() in ("1", "true", "yes", "si", "sí", "on", "enabled", "enable")


def fwgov_clean_url(value):
    url = (value or "").strip().rstrip("/")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("La URL del firewall debe iniciar con http:// o https:// e incluir un host válido.")
    return url


def fwgov_safe_int(value, default=0, minimum=None, maximum=None):
    try:
        number = int(float(value))
    except Exception:
        number = default
    if minimum is not None:
        number = max(minimum, number)
    if maximum is not None:
        number = min(maximum, number)
    return number


def fwgov_safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def fwgov_parse_date(value):
    text_value = (value or "").strip()
    if not text_value or text_value.upper() in ("NONE", "N/A", "NA", "NO APLICA", "SIN VENCIMIENTO"):
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(text_value, fmt).date()
        except Exception:
            continue
    return "INVALID"


def fwgov_parse_metadata(description):
    description = (description or "").strip()
    result = {
        "name": "",
        "owner": "",
        "ticket": "",
        "review": "",
        "expires": "",
        "justification": "",
    }
    if not description:
        return result

    parts = [p.strip() for p in description.split("|")]
    result["name"] = parts[0].strip()

    patterns = {
        "owner": r"^OWNER\s*=\s*(.+)$",
        "ticket": r"^TICKET\s*=\s*(.+)$",
        "review": r"^REVIEW\s*=\s*(.+)$",
        "expires": r"^EXPIRES\s*=\s*(.+)$",
        "justification": r"^JUSTIFICATION\s*=\s*(.+)$",
    }

    for part in parts[1:]:
        for key, pattern in patterns.items():
            match = re.match(pattern, part, flags=re.IGNORECASE)
            if match:
                result[key] = match.group(1).strip()
                break

    return result


def fwgov_is_any(value):
    text_value = (value or "").strip().lower()
    return text_value in ("", "any", "*", "all", "0.0.0.0/0", "::/0")


def fwgov_normalize_port(value):
    text_value = str(value or "").strip().lower().replace(" ", "")
    if text_value in ("", "any", "*", "all"):
        return "any"
    named = {
        "ssh": "22",
        "telnet": "23",
        "http": "80",
        "https": "443",
        "rdp": "3389",
        "ms-rdp": "3389",
        "microsoft-ds": "445",
        "smb": "445",
        "mysql": "3306",
        "postgresql": "5432",
        "domain": "53",
    }
    return named.get(text_value, text_value)


def fwgov_port_interval(value):
    text_value = fwgov_normalize_port(value)
    if text_value == "any":
        return (1, 65535)

    if "," in text_value:
        return None

    match = re.match(r"^(\d+)(?:-|:)(\d+)$", text_value)
    if match:
        start = int(match.group(1))
        end = int(match.group(2))
        if start > end:
            start, end = end, start
        return (max(0, start), min(65535, end))

    if text_value.isdigit():
        port = int(text_value)
        return (port, port)

    return None


def fwgov_port_contains(value, port):
    interval = fwgov_port_interval(value)
    return bool(interval and interval[0] <= int(port) <= interval[1])


def fwgov_port_covers(earlier, later):
    earlier_interval = fwgov_port_interval(earlier)
    later_interval = fwgov_port_interval(later)
    if earlier_interval and later_interval:
        return earlier_interval[0] <= later_interval[0] and earlier_interval[1] >= later_interval[1]
    return fwgov_normalize_port(earlier) == fwgov_normalize_port(later)


def fwgov_net_covers(earlier, later):
    if fwgov_is_any(earlier):
        return True
    if (earlier or "").strip().lower() == (later or "").strip().lower():
        return True

    try:
        earlier_net = ipaddress.ip_network(str(earlier).strip(), strict=False)
        later_net = ipaddress.ip_network(str(later).strip(), strict=False)
        return later_net.subnet_of(earlier_net)
    except Exception:
        return False


def fwgov_protocol_covers(earlier, later):
    earlier_value = (earlier or "any").strip().lower()
    later_value = (later or "any").strip().lower()
    return earlier_value in ("", "any", "*") or earlier_value == later_value


def fwgov_action_is_allow(action):
    return (action or "").strip().lower() in ("pass", "allow", "permit", "accept")


def fwgov_rule_fingerprint(rule_data):
    technical = {
        "enabled": bool(rule_data.get("enabled")),
        "action": (rule_data.get("action") or "").lower(),
        "quick": bool(rule_data.get("quick")),
        "interface": (rule_data.get("interface") or "").lower(),
        "direction": (rule_data.get("direction") or "").lower(),
        "ip_version": (rule_data.get("ip_version") or "").lower(),
        "protocol": (rule_data.get("protocol") or "").lower(),
        "source": (rule_data.get("source") or "").lower(),
        "source_port": fwgov_normalize_port(rule_data.get("source_port")),
        "destination": (rule_data.get("destination") or "").lower(),
        "destination_port": fwgov_normalize_port(rule_data.get("destination_port")),
        "gateway": (rule_data.get("gateway") or "").lower(),
        "schedule": (rule_data.get("schedule") or "").lower(),
        "logging_enabled": bool(rule_data.get("logging_enabled")),
    }
    payload = json.dumps(technical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def fwgov_normalize_opnsense_rule(raw_rule):
    raw_rule = raw_rule or {}
    description = (raw_rule.get("description") or "").strip()
    metadata = fwgov_parse_metadata(description)
    external_id = (
        raw_rule.get("uuid")
        or raw_rule.get("id")
        or hashlib.sha256(json.dumps(raw_rule, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:32]
    )

    normalized = {
        "external_id": str(external_id),
        "name": metadata.get("name") or description or f"Regla {external_id}",
        "description": description,
        "enabled": fwgov_bool(raw_rule.get("enabled", "1")),
        "action": str(raw_rule.get("action") or raw_rule.get("%action") or "").strip(),
        "quick": fwgov_bool(raw_rule.get("quick", "1")),
        "interface": str(raw_rule.get("%interface") or raw_rule.get("interface") or "").strip(),
        "direction": str(raw_rule.get("%direction") or raw_rule.get("direction") or "").strip(),
        "ip_version": str(raw_rule.get("%ipprotocol") or raw_rule.get("ipprotocol") or "").strip(),
        "protocol": str(raw_rule.get("protocol") or "any").strip(),
        "source": str(raw_rule.get("%source_net") or raw_rule.get("source_net") or "any").strip(),
        "source_port": fwgov_normalize_port(raw_rule.get("source_port")),
        "destination": str(raw_rule.get("%destination_net") or raw_rule.get("destination_net") or "any").strip(),
        "destination_port": fwgov_normalize_port(raw_rule.get("destination_port")),
        "gateway": str(raw_rule.get("gateway") or "").strip(),
        "schedule": str(raw_rule.get("sched") or raw_rule.get("schedule") or "").strip(),
        "logging_enabled": fwgov_bool(raw_rule.get("log", "0")),
        "category": str(raw_rule.get("%categories") or raw_rule.get("categories") or "").strip(),
        "sequence": fwgov_safe_int(raw_rule.get("sequence"), default=0),
        "sort_order": fwgov_safe_float(raw_rule.get("sort_order"), default=0.0),
        "owner": metadata.get("owner") or "",
        "ticket": metadata.get("ticket") or "",
        "review_date": metadata.get("review") or "",
        "expiration_date": metadata.get("expires") or "",
        "justification": metadata.get("justification") or "",
        "raw_json": json.dumps(raw_rule, ensure_ascii=False, default=str),
    }
    normalized["fingerprint"] = fwgov_rule_fingerprint(normalized)
    return normalized


def fwgov_api_credentials(device):
    api_key = fwgov_decrypt(device.api_key_encrypted)
    api_secret = fwgov_decrypt(device.api_secret_encrypted)
    if not api_key or not api_secret:
        raise RuntimeError("El dispositivo no tiene una API key/secret válida configurada.")
    return api_key, api_secret


def fwgov_api_get(device, endpoint, params=None):
    if (device.vendor or "").strip().lower() != FIREWALL_GOV_VENDOR_OPNSENSE.lower():
        raise RuntimeError(f"El conector para {device.vendor} todavía no está implementado.")

    api_key, api_secret = fwgov_api_credentials(device)
    url = fwgov_clean_url(device.base_url) + endpoint
    response = requests.get(
        url,
        auth=HTTPBasicAuth(api_key, api_secret),
        params=params or {},
        verify=bool(device.verify_ssl),
        timeout=fwgov_safe_int(device.timeout_seconds, 30, 5, 120),
        headers={"Accept": "application/json"},
    )
    response.raise_for_status()
    try:
        return response.json() or {}, url
    except ValueError as exc:
        raise RuntimeError("La API respondió, pero el contenido no es JSON válido.") from exc


def fwgov_fetch_opnsense_rules(device, only_test=False):
    endpoints = (
        "/api/firewall/filter/searchRule",
        "/api/firewall/filter/search_rule",
    )
    last_error = None
    row_count = 1 if only_test else 500

    for endpoint in endpoints:
        try:
            all_rows = []
            current_page = 1
            endpoint_url = ""

            while True:
                data, endpoint_url = fwgov_api_get(
                    device,
                    endpoint,
                    params={
                        "current": current_page,
                        "rowCount": row_count,
                        "searchPhrase": (device.search_phrase or "").strip(),
                    },
                )

                rows = data.get("rows") if isinstance(data, dict) else None
                if rows is None and isinstance(data, dict):
                    rows = data.get("data", {}).get("rows") if isinstance(data.get("data"), dict) else None
                rows = rows if isinstance(rows, list) else []

                if only_test:
                    total = fwgov_safe_int(data.get("total"), len(rows)) if isinstance(data, dict) else len(rows)
                    return rows, total, endpoint_url

                all_rows.extend(rows)
                total = fwgov_safe_int(data.get("total"), len(all_rows)) if isinstance(data, dict) else len(all_rows)

                if not rows or len(all_rows) >= total or current_page >= 20:
                    break
                current_page += 1

            category_filter = (device.category_filter or "").strip().lower()
            if category_filter:
                filtered = []
                for row in all_rows:
                    category_text = str(row.get("%categories") or row.get("categories") or "").lower()
                    if category_filter in category_text:
                        filtered.append(row)
                all_rows = filtered

            return all_rows, len(all_rows), endpoint_url

        except requests.HTTPError as exc:
            last_error = exc
            if getattr(exc.response, "status_code", None) == 404:
                continue
            raise
        except Exception as exc:
            last_error = exc
            break

    if last_error:
        raise last_error
    raise RuntimeError("No se encontró un endpoint compatible para consultar reglas.")


def fwgov_test_device(device):
    try:
        rows, total, endpoint = fwgov_fetch_opnsense_rules(device, only_test=True)
        device.last_status = "Online"
        device.last_message = f"Conexión exitosa. La API reportó {total} regla(s)."
        device.last_test_at = datetime.utcnow()
        db.session.commit()
        return True, device.last_message, endpoint
    except Exception as exc:
        db.session.rollback()
        device = FirewallGovDevice.query.get(device.id)
        device.last_status = "Error"
        device.last_message = str(exc)[:1000]
        device.last_test_at = datetime.utcnow()
        db.session.commit()
        return False, device.last_message, ""


def fwgov_sync_rule_rows(device, raw_rows):
    now = datetime.utcnow()
    FirewallGovRule.query.filter_by(device_id=device.id).update({"active": False}, synchronize_session=False)

    active_rule_ids = []
    for raw_row in raw_rows:
        normalized = fwgov_normalize_opnsense_rule(raw_row)
        rule = FirewallGovRule.query.filter_by(
            device_id=device.id,
            external_id=normalized["external_id"],
        ).first()

        if not rule:
            rule = FirewallGovRule(
                device_id=device.id,
                external_id=normalized["external_id"],
                first_seen_at=now,
            )
            db.session.add(rule)

        for field in (
            "name", "description", "enabled", "action", "quick", "interface", "direction",
            "ip_version", "protocol", "source", "source_port", "destination", "destination_port",
            "gateway", "schedule", "logging_enabled", "category", "sequence", "sort_order",
            "owner", "ticket", "review_date", "expiration_date", "justification", "fingerprint",
            "raw_json",
        ):
            setattr(rule, field, normalized.get(field))

        rule.active = True
        rule.last_seen_at = now
        db.session.flush()
        active_rule_ids.append(rule.id)

    db.session.commit()
    return active_rule_ids


def fwgov_finding_key(device_id, rule_external_id, finding_code, related_external_id=""):
    raw = f"{device_id}|{rule_external_id or ''}|{finding_code or ''}|{related_external_id or ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def fwgov_add_finding(device, rule, code, severity, title, description, recommendation, control_mapping, related_rule=None, technical_detail=""):
    now = datetime.utcnow()
    related_external_id = related_rule.external_id if related_rule else ""
    key = fwgov_finding_key(device.id, rule.external_id if rule else "", code, related_external_id)
    finding = FirewallGovFinding.query.filter_by(finding_key=key).first()

    if not finding:
        finding = FirewallGovFinding(
            device_id=device.id,
            rule_id=rule.id if rule else None,
            finding_key=key,
            finding_code=code,
            first_detected_at=now,
            status="Abierto",
        )
        db.session.add(finding)
    elif finding.status in ("Resuelto automáticamente", "Resuelto"):
        finding.status = "Abierto"
        finding.resolved_at = None

    finding.rule_id = rule.id if rule else None
    finding.severity = severity
    finding.title = title
    finding.description = description
    finding.recommendation = recommendation
    finding.control_mapping = control_mapping
    finding.rule_external_id = rule.external_id if rule else ""
    finding.rule_name = rule.name if rule else ""
    finding.related_rule_external_id = related_external_id
    finding.technical_detail = technical_detail
    finding.risk_score = FIREWALL_GOV_SEVERITY_SCORE.get(severity, 0)
    finding.active = True
    finding.last_detected_at = now
    finding.updated_at = now
    return finding


def fwgov_rule_subsumes(earlier, later):
    if not earlier.quick or not earlier.enabled:
        return False
    if (earlier.interface or "").lower() != (later.interface or "").lower():
        return False
    if (earlier.direction or "").lower() != (later.direction or "").lower():
        return False
    if not fwgov_protocol_covers(earlier.protocol, later.protocol):
        return False
    if not fwgov_net_covers(earlier.source, later.source):
        return False
    if not fwgov_net_covers(earlier.destination, later.destination):
        return False
    if not fwgov_port_covers(earlier.source_port, later.source_port):
        return False
    if not fwgov_port_covers(earlier.destination_port, later.destination_port):
        return False
    return True


def fwgov_analyze_device(device):
    now = datetime.utcnow()
    today = date.today()

    FirewallGovFinding.query.filter_by(device_id=device.id).update(
        {"active": False}, synchronize_session=False
    )

    rules = FirewallGovRule.query.filter_by(device_id=device.id, active=True).order_by(
        FirewallGovRule.sort_order.asc(),
        FirewallGovRule.sequence.asc(),
        FirewallGovRule.id.asc(),
    ).all()

    for rule in rules:
        allow = fwgov_action_is_allow(rule.action)
        source_any = fwgov_is_any(rule.source)
        destination_any = fwgov_is_any(rule.destination)
        protocol_any = (rule.protocol or "").strip().lower() in ("", "any", "*")
        destination_port_any = fwgov_normalize_port(rule.destination_port) == "any"
        port_interval = fwgov_port_interval(rule.destination_port)

        if not (rule.description or "").strip():
            fwgov_add_finding(
                device, rule, "MISSING_DESCRIPTION", "Baja",
                "Regla sin nombre o descripción",
                "La regla no contiene una descripción que permita identificar su propósito.",
                "Asignar un nombre, propósito, propietario y referencia de cambio.",
                "ISO 27001 A.5.2, NIST CSF GV.PO",
            )

        if allow and source_any and destination_any and protocol_any and destination_port_any:
            fwgov_add_finding(
                device, rule, "ANY_ANY_ALLOW", "Crítica",
                "Regla completamente permisiva ANY-ANY",
                "La regla permite tráfico desde cualquier origen hacia cualquier destino, sin restringir protocolo ni servicio.",
                "Eliminar la regla o limitar origen, destino, protocolo y puertos al mínimo necesario.",
                "ISO 27001 A.8.20; NIST CSF PR.PS; PCI DSS 1.2.1",
                technical_detail=f"{rule.source} -> {rule.destination} | {rule.protocol} | {rule.destination_port}",
            )
        elif allow and ((source_any and destination_any) or (destination_any and destination_port_any)):
            fwgov_add_finding(
                device, rule, "BROAD_ALLOW", "Alta",
                "Regla de acceso excesivamente amplia",
                "La combinación de origen, destino o servicio permite un alcance mayor al necesario.",
                "Aplicar mínimo privilegio y sustituir valores Any por redes, hosts y servicios específicos.",
                "ISO 27001 A.8.20; NIST CSF PR.AA; PCI DSS 1.2",
                technical_detail=f"Origen={rule.source}; Destino={rule.destination}; Puerto={rule.destination_port}",
            )

        if allow and not rule.logging_enabled:
            fwgov_add_finding(
                device, rule, "LOGGING_DISABLED", "Media",
                "Logging desactivado en regla permisiva",
                "La regla permite tráfico, pero no registra los eventos asociados.",
                "Habilitar logging y definir retención, revisión y alertamiento de eventos.",
                "ISO 27001 A.8.15; NIST CSF DE.CM; PCI DSS 10.2",
            )

        if allow and port_interval and not destination_port_any:
            width = port_interval[1] - port_interval[0] + 1
            if width > 20 or port_interval[0] <= 1:
                fwgov_add_finding(
                    device, rule, "EXCESSIVE_PORT_RANGE", "Alta",
                    "Rango de puertos excesivamente amplio",
                    f"La regla permite el rango {rule.destination_port}, equivalente a {width} puertos.",
                    "Definir únicamente los puertos requeridos. Verificar si el rango fue creado por error.",
                    "ISO 27001 A.8.20; NIST CSF PR.PS; PCI DSS 1.2.5",
                    technical_detail=f"Rango detectado: {rule.destination_port}",
                )

        if allow and (fwgov_port_contains(rule.destination_port, 21) or fwgov_port_contains(rule.destination_port, 23)):
            fwgov_add_finding(
                device, rule, "INSECURE_CLEAR_TEXT_SERVICE", "Alta",
                "Servicio inseguro en texto claro permitido",
                "La regla permite FTP o Telnet, protocolos que pueden exponer credenciales y datos sin cifrado.",
                "Reemplazar por SFTP/SSH o protocolos cifrados y limitar estrictamente el origen.",
                "ISO 27001 A.8.24; NIST CSF PR.DS; PCI DSS 4.2",
            )

        if allow and source_any and any(fwgov_port_contains(rule.destination_port, p) for p in (22, 443, 8443, 3389, 5900)):
            fwgov_add_finding(
                device, rule, "ADMIN_SERVICE_ANY_SOURCE", "Alta",
                "Servicio administrativo expuesto desde cualquier origen",
                "La regla permite acceso a un puerto administrativo desde un origen no restringido.",
                "Restringir a una red de administración, VPN o bastión y aplicar MFA cuando corresponda.",
                "ISO 27001 A.5.15/A.8.20; NIST CSF PR.AA; PCI DSS 8.2",
            )

        if allow and source_any and fwgov_port_contains(rule.destination_port, 445):
            fwgov_add_finding(
                device, rule, "SMB_ANY_SOURCE", "Alta",
                "SMB permitido desde cualquier origen",
                "El puerto 445 está accesible desde un origen amplio, incrementando el riesgo de movimiento lateral y explotación remota.",
                "Limitar SMB a segmentos autorizados y bloquearlo desde redes no confiables.",
                "ISO 27001 A.8.20; NIST CSF PR.PS; CIS Control 12",
            )

        if allow and source_any and any(fwgov_port_contains(rule.destination_port, p) for p in (1433, 1521, 3306, 5432, 6379, 9200, 27017)):
            fwgov_add_finding(
                device, rule, "DATABASE_ANY_SOURCE", "Alta",
                "Servicio de base de datos accesible desde cualquier origen",
                "La regla permite conectividad hacia un servicio de datos sin restringir el origen.",
                "Autorizar únicamente servidores de aplicación o administración definidos y registrar las conexiones.",
                "ISO 27001 A.8.20/A.8.21; NIST CSF PR.DS; PCI DSS 1.3",
            )

        if not rule.owner:
            fwgov_add_finding(
                device, rule, "MISSING_OWNER", "Media",
                "Regla sin propietario definido",
                "No se identificó OWNER en la descripción de la regla.",
                "Asignar un propietario responsable de revisar, justificar y retirar la regla.",
                "ISO 27001 A.5.2; NIST CSF GV.RR",
            )

        if not rule.ticket:
            fwgov_add_finding(
                device, rule, "MISSING_CHANGE_TICKET", "Media",
                "Regla sin ticket de cambio",
                "No se identificó TICKET en la descripción de la regla.",
                "Relacionar la regla con una solicitud de cambio aprobada y evidencia de autorización.",
                "ISO 27001 A.8.32; NIST CSF PR.PS; PCI DSS 6.5",
            )

        if not rule.justification:
            fwgov_add_finding(
                device, rule, "MISSING_JUSTIFICATION", "Media",
                "Regla sin justificación",
                "La descripción no documenta la necesidad de negocio o seguridad de la regla.",
                "Registrar una justificación verificable y el alcance autorizado.",
                "ISO 27001 A.5.2/A.8.20; PCI DSS 1.2.7",
            )

        parsed_review = fwgov_parse_date(rule.review_date)
        if not rule.review_date:
            fwgov_add_finding(
                device, rule, "MISSING_REVIEW_DATE", "Media",
                "Regla sin fecha de revisión",
                "No se identificó REVIEW en la descripción.",
                "Definir una fecha de última revisión y establecer revisiones periódicas.",
                "ISO 27001 A.8.20; NIST CSF GV.OV; PCI DSS 1.2.7",
            )
        elif parsed_review == "INVALID":
            fwgov_add_finding(
                device, rule, "INVALID_REVIEW_DATE", "Media",
                "Fecha de revisión inválida",
                f"El valor REVIEW={rule.review_date} no tiene un formato de fecha reconocido.",
                "Usar el formato YYYY-MM-DD.",
                "ISO 27001 A.8.20; NIST CSF GV.OV",
            )
        elif isinstance(parsed_review, date) and (today - parsed_review).days > 365:
            fwgov_add_finding(
                device, rule, "STALE_REVIEW", "Media",
                "Revisión de regla vencida",
                f"La última revisión registrada fue hace {(today - parsed_review).days} días.",
                "Revalidar necesidad, alcance, propietario y servicios autorizados.",
                "ISO 27001 A.8.20; NIST CSF GV.OV; PCI DSS 1.2.7",
            )

        parsed_expiration = fwgov_parse_date(rule.expiration_date)
        if parsed_expiration == "INVALID":
            fwgov_add_finding(
                device, rule, "INVALID_EXPIRATION_DATE", "Media",
                "Fecha de expiración inválida",
                f"El valor EXPIRES={rule.expiration_date} no tiene un formato de fecha reconocido.",
                "Usar YYYY-MM-DD o EXPIRES=NONE cuando la regla no sea temporal.",
                "ISO 27001 A.8.20; NIST CSF GV.OV",
            )
        elif rule.enabled and isinstance(parsed_expiration, date) and parsed_expiration < today:
            fwgov_add_finding(
                device, rule, "EXPIRED_ENABLED_RULE", "Alta",
                "Regla vencida todavía habilitada",
                f"La regla expiró el {parsed_expiration.isoformat()} y continúa activa.",
                "Deshabilitarla, eliminarla o tramitar una renovación formal antes de reactivarla.",
                "ISO 27001 A.5.15/A.8.20; NIST CSF PR.AA; PCI DSS 1.2.7",
            )

        if not rule.enabled:
            fwgov_add_finding(
                device, rule, "DISABLED_RULE", "Baja",
                "Regla deshabilitada pendiente de depuración",
                "La regla continúa en la configuración aunque está deshabilitada.",
                "Validar su retención y eliminarla si ya no es necesaria.",
                "ISO 27001 A.8.9/A.8.20; NIST CSF PR.PS",
            )

    fingerprint_groups = defaultdict(list)
    for rule in rules:
        fingerprint_groups[rule.fingerprint or ""].append(rule)

    for fingerprint, duplicated_rules in fingerprint_groups.items():
        if not fingerprint or len(duplicated_rules) < 2:
            continue
        canonical = duplicated_rules[0]
        for duplicate in duplicated_rules[1:]:
            fwgov_add_finding(
                device, duplicate, "DUPLICATE_RULE", "Media",
                "Regla duplicada",
                f"La regla es técnicamente equivalente a {canonical.name}.",
                "Consolidar las reglas y conservar una única entrada autorizada y trazable.",
                "ISO 27001 A.8.9/A.8.20; NIST CSF PR.PS",
                related_rule=canonical,
                technical_detail=f"Fingerprint: {fingerprint}",
            )

    for later_index, later in enumerate(rules):
        if not later.enabled:
            continue
        for earlier in rules[:later_index]:
            if earlier.fingerprint == later.fingerprint:
                continue
            if not fwgov_rule_subsumes(earlier, later):
                continue

            if (earlier.action or "").lower() != (later.action or "").lower():
                fwgov_add_finding(
                    device, later, "SHADOWED_RULE", "Alta",
                    "Regla potencialmente ocultada por una regla anterior",
                    f"La regla {earlier.name} aparece antes, cubre el mismo tráfico y aplica una acción diferente.",
                    "Reordenar o restringir la regla anterior para que la política específica pueda evaluarse.",
                    "ISO 27001 A.8.20; NIST CSF PR.PS; PCI DSS 1.2",
                    related_rule=earlier,
                    technical_detail=f"Regla anterior: {earlier.external_id}; orden={earlier.sort_order}",
                )
            else:
                fwgov_add_finding(
                    device, later, "REDUNDANT_RULE", "Media",
                    "Regla redundante cubierta por una regla anterior",
                    f"La regla {earlier.name} cubre el tráfico de esta regla con la misma acción.",
                    "Consolidar reglas para reducir complejidad y riesgo operativo.",
                    "ISO 27001 A.8.9/A.8.20; NIST CSF PR.PS",
                    related_rule=earlier,
                )
            break

    stale_findings = FirewallGovFinding.query.filter_by(device_id=device.id, active=False).all()
    for finding in stale_findings:
        if finding.status not in ("Falso positivo", "Riesgo aceptado"):
            finding.status = "Resuelto automáticamente"
            finding.resolved_at = now
        finding.updated_at = now

    db.session.commit()

    active_findings = FirewallGovFinding.query.filter_by(device_id=device.id, active=True).all()
    effective_findings = [f for f in active_findings if f.status not in ("Falso positivo", "Resuelto", "Resuelto automáticamente")]
    total_penalty = sum(FIREWALL_GOV_SEVERITY_SCORE.get(f.severity, 0) for f in effective_findings)
    compliance_score = max(0, round(100 - min(100, total_penalty), 1))
    critical = len([f for f in effective_findings if f.severity == "Crítica"])

    return {
        "rules": len(rules),
        "findings": len(active_findings),
        "critical": critical,
        "score": compliance_score,
    }


def fwgov_sync_device(device, executed_by):
    sync_log = FirewallGovSyncLog(
        device_id=device.id,
        status="En proceso",
        message="Sincronización iniciada.",
        executed_by=executed_by,
    )
    db.session.add(sync_log)
    db.session.commit()
    log_id = sync_log.id

    try:
        raw_rows, total, endpoint = fwgov_fetch_opnsense_rules(device, only_test=False)
        fwgov_sync_rule_rows(device, raw_rows)
        analysis = fwgov_analyze_device(device)

        device = FirewallGovDevice.query.get(device.id)
        device.last_status = "Online"
        device.last_message = f"Sincronización completada: {analysis['rules']} reglas y {analysis['findings']} hallazgos."
        device.last_sync_at = datetime.utcnow()
        device.last_test_at = datetime.utcnow()

        sync_log = FirewallGovSyncLog.query.get(log_id)
        sync_log.finished_at = datetime.utcnow()
        sync_log.status = "Completado"
        sync_log.message = device.last_message
        sync_log.endpoint_used = endpoint
        sync_log.rules_received = total
        sync_log.rules_active = analysis["rules"]
        sync_log.findings_active = analysis["findings"]
        sync_log.critical_findings = analysis["critical"]
        sync_log.compliance_score = analysis["score"]
        db.session.commit()
        return analysis

    except Exception as exc:
        db.session.rollback()
        device = FirewallGovDevice.query.get(device.id)
        if device:
            device.last_status = "Error"
            device.last_message = str(exc)[:1500]
            device.last_test_at = datetime.utcnow()

        sync_log = FirewallGovSyncLog.query.get(log_id)
        if sync_log:
            sync_log.finished_at = datetime.utcnow()
            sync_log.status = "Error"
            sync_log.message = str(exc)[:2000]
        db.session.commit()
        raise


def fwgov_severity_badge(severity):
    classes = {
        "Crítica": "danger",
        "Alta": "warning text-dark",
        "Media": "primary",
        "Baja": "secondary",
        "Informativa": "info text-dark",
    }
    css = classes.get(severity or "", "secondary")
    return Markup(f'<span class="badge bg-{css}">{escape(severity or "N/A")}</span>')


def fwgov_status_badge(status):
    classes = {
        "Abierto": "danger",
        "En tratamiento": "warning text-dark",
        "Riesgo aceptado": "info text-dark",
        "Falso positivo": "secondary",
        "Resuelto": "success",
        "Resuelto automáticamente": "success",
    }
    css = classes.get(status or "", "secondary")
    return Markup(f'<span class="badge bg-{css}">{escape(status or "N/A")}</span>')


def fwgov_device_status_badge(status):
    status = status or "No probado"
    css = "success" if status == "Online" else ("danger" if status == "Error" else "secondary")
    return Markup(f'<span class="badge bg-{css}">{escape(status)}</span>')


def fwgov_dashboard_metrics(device_id=None):
    rule_query = FirewallGovRule.query.filter_by(active=True)
    finding_query = FirewallGovFinding.query.filter_by(active=True)
    if device_id:
        rule_query = rule_query.filter_by(device_id=device_id)
        finding_query = finding_query.filter_by(device_id=device_id)

    rules = rule_query.all()
    findings = finding_query.all()
    effective = [
        f for f in findings
        if f.status not in ("Falso positivo", "Resuelto", "Resuelto automáticamente")
    ]
    penalty = sum(FIREWALL_GOV_SEVERITY_SCORE.get(f.severity, 0) for f in effective)

    return {
        "rules": len(rules),
        "enabled_rules": len([r for r in rules if r.enabled]),
        "findings": len(effective),
        "critical": len([f for f in effective if f.severity == "Crítica"]),
        "high": len([f for f in effective if f.severity == "Alta"]),
        "medium": len([f for f in effective if f.severity == "Media"]),
        "low": len([f for f in effective if f.severity == "Baja"]),
        "score": max(0, round(100 - min(100, penalty), 1)),
    }


FIREWALL_GOV_EXTRA_CSS = """
<style>
  .fwgov-grid{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:14px}
  .fwgov-device-card{border:1px solid #d8e3f3;border-radius:16px;padding:14px;background:#fff;height:100%}
  .fwgov-device-card.active{border:2px solid #1d5fae;box-shadow:0 8px 18px rgba(29,95,174,.14)}
  .fwgov-small{font-size:.76rem;color:#64748b}
  .fwgov-code{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;font-size:.74rem}
  .fwgov-truncate{max-width:300px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .fwgov-scroll{max-height:580px;overflow:auto}
  .fwgov-score{font-size:2rem;font-weight:950;color:#0b4a8f;line-height:1}
  .fwgov-secret-state{font-size:.75rem;font-weight:800;color:#166534}

  .fwgov-action-grid{
    display:grid;
    grid-template-columns:repeat(2,minmax(0,1fr));
    gap:14px;
    margin:14px 0;
  }
  .fwgov-action-card{
    display:flex;
    align-items:center;
    gap:14px;
    min-height:92px;
    padding:16px 18px;
    border:1px solid #d7e4f5;
    border-radius:18px;
    background:linear-gradient(145deg,#ffffff 0%,#f4f8fe 100%);
    box-shadow:0 8px 22px rgba(15,67,125,.08);
    color:#173a63;
    text-decoration:none!important;
    transition:transform .18s ease,box-shadow .18s ease,border-color .18s ease;
  }
  .fwgov-action-card:hover{
    transform:translateY(-2px);
    box-shadow:0 13px 28px rgba(15,67,125,.14);
    border-color:#8eb6e8;
    color:#0b4a8f;
  }
  .fwgov-action-icon{
    width:52px;
    height:52px;
    min-width:52px;
    display:flex;
    align-items:center;
    justify-content:center;
    border-radius:15px;
    background:linear-gradient(135deg,#154f91,#2f7ac5);
    color:#fff;
    font-size:1.35rem;
    box-shadow:0 8px 18px rgba(21,79,145,.24);
  }
  .fwgov-action-copy{min-width:0;flex:1}
  .fwgov-action-title{font-size:.94rem;font-weight:900;line-height:1.18;margin-bottom:4px}
  .fwgov-action-text{font-size:.76rem;color:#64748b;line-height:1.25}
  .fwgov-action-arrow{font-size:1.1rem;color:#2f6fae}

  .fwgov-back-row{display:flex;align-items:center;margin:0 0 12px 0}
  .fwgov-back-button{
    display:inline-flex;
    align-items:center;
    gap:8px;
    padding:9px 14px;
    border:1px solid #cadcf1;
    border-radius:12px;
    background:#fff;
    color:#174f8f;
    text-decoration:none!important;
    font-size:.82rem;
    font-weight:850;
    box-shadow:0 5px 14px rgba(15,67,125,.07);
    transition:all .18s ease;
  }
  .fwgov-back-button:hover{background:#edf5ff;border-color:#8eb6e8;color:#0b4a8f;transform:translateX(-2px)}

  .fwgov-config-shortcuts{margin:14px 0 4px 0}
  .fwgov-config-shortcuts .fwgov-action-card{min-height:80px;padding:13px 16px}
  .fwgov-config-shortcuts .fwgov-action-icon{width:44px;height:44px;min-width:44px;font-size:1.1rem}

  .fwgov-kpi-grid{
    display:grid;
    grid-template-columns:repeat(4,minmax(0,1fr));
    gap:12px;
    margin-top:14px;
  }
  .fwgov-kpi-card{
    position:relative;
    overflow:hidden;
    display:flex;
    align-items:center;
    gap:12px;
    min-height:82px;
    padding:14px 15px;
    border:1px solid #dce7f4;
    border-radius:17px;
    background:#fff;
    box-shadow:0 7px 18px rgba(15,67,125,.07);
  }
  .fwgov-kpi-card:before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:#2f6fae}
  .fwgov-kpi-icon{width:42px;height:42px;min-width:42px;border-radius:13px;display:flex;align-items:center;justify-content:center;background:#edf5ff;color:#1b5b9f;font-size:1.15rem}
  .fwgov-kpi-number{font-size:1.45rem;font-weight:950;line-height:1;color:#123e70}
  .fwgov-kpi-label{font-size:.75rem;color:#64748b;font-weight:760;margin-top:5px;line-height:1.15}
  .fwgov-kpi-critical:before{background:#b42318}.fwgov-kpi-critical .fwgov-kpi-icon{background:#fff0ef;color:#b42318}
  .fwgov-kpi-high:before{background:#d97706}.fwgov-kpi-high .fwgov-kpi-icon{background:#fff7e8;color:#b45309}
  .fwgov-kpi-medium:before{background:#ca8a04}.fwgov-kpi-medium .fwgov-kpi-icon{background:#fffbea;color:#a16207}
  .fwgov-kpi-low:before{background:#15803d}.fwgov-kpi-low .fwgov-kpi-icon{background:#edfdf3;color:#15803d}
  .fwgov-kpi-score:before{background:#6d28d9}.fwgov-kpi-score .fwgov-kpi-icon{background:#f4efff;color:#6d28d9}

  @media(max-width:1100px){.fwgov-kpi-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
  @media(max-width:768px){.fwgov-action-grid{grid-template-columns:1fr}.fwgov-kpi-grid{grid-template-columns:1fr}}
  @media(max-width:992px){.fwgov-grid{display:block}.fwgov-device-card{margin-bottom:12px}}
</style>
"""


def fwgov_page_selection(allow_new=False):
    """Obtiene los firewalls y conserva el dispositivo seleccionado entre pantallas."""
    devices = FirewallGovDevice.query.order_by(FirewallGovDevice.name.asc()).all()
    selected_device_id = request.args.get("device_id", type=int)
    new_mode = bool(allow_new and request.args.get("new") == "1")
    selected_device = FirewallGovDevice.query.get(selected_device_id) if selected_device_id else None

    if not selected_device and devices and not new_mode:
        selected_device = devices[0]

    return devices, selected_device, new_mode


def fwgov_main_actions(selected_device=None):
    """Accesos principales visibles únicamente en la pantalla de hallazgos."""
    params = {"device_id": selected_device.id} if selected_device else {}
    actions = [
        (
            "bi-gear-wide-connected",
            "Configuración del conector",
            "Administre credenciales, URL, filtros y parámetros de conexión.",
            url_for("fwgov_connector_config", **params),
        ),
        (
            "bi-list-check",
            "Inventario normalizado de reglas",
            "Consulte la vista técnica estandarizada de las reglas sincronizadas.",
            url_for("fwgov_rules_inventory", **params),
        ),
        (
            "bi-diagram-3-fill",
            "Modelamiento de Amenazas",
            "Consulte los hallazgos del firewall mapeados con tácticas y técnicas MITRE ATT&CK.",
            url_for("threat_model_dashboard", herramienta=THREAT_MODEL_FIREWALL_SOURCE),
        ),
    ]
    return Markup(render_template_string("""
    <div class="fwgov-action-grid" data-keep-cumplimiento-nav="true">
      {% for icon, title, text, href in actions %}
      <a class="fwgov-action-card" href="{{ href }}">
        <span class="fwgov-action-icon"><i class="bi {{ icon }}"></i></span>
        <span class="fwgov-action-copy">
          <span class="fwgov-action-title d-block">{{ title }}</span>
          <span class="fwgov-action-text d-block">{{ text }}</span>
        </span>
        <i class="bi bi-arrow-right fwgov-action-arrow"></i>
      </a>
      {% endfor %}
    </div>
    """, actions=actions))


def fwgov_back_button(selected_device=None, destination="findings"):
    """Botón único de regreso para las pantallas secundarias."""
    params = {"device_id": selected_device.id} if selected_device else {}
    destinations = {
        "findings": (
            "Volver a Hallazgos de Gobierno de Firewall",
            url_for("cumplimiento_continuo_firewall", **params),
        ),
        "config": (
            "Volver a Configuración del conector",
            url_for("fwgov_connector_config", **params),
        ),
    }
    label, href = destinations.get(destination, destinations["findings"])
    return Markup(render_template_string("""
    <div class="fwgov-back-row" data-keep-cumplimiento-nav="true">
      <a class="fwgov-back-button" href="{{ href }}">
        <i class="bi bi-arrow-left"></i> {{ label }}
      </a>
    </div>
    """, label=label, href=href))


def fwgov_config_shortcuts(selected_device=None):
    """Accesos subordinados disponibles dentro de Configuración del conector."""
    params = {"device_id": selected_device.id} if selected_device else {}
    actions = [
        (
            "bi-hdd-network",
            "Firewalls registrados",
            "Revise conectores, estado de conexión y acciones de sincronización.",
            url_for("fwgov_firewalls_registered", **params),
        ),
        (
            "bi-clock-history",
            "Historial de sincronización",
            "Consulte la trazabilidad de ejecuciones, resultados y puntajes.",
            url_for("fwgov_sync_history", **params),
        ),
    ]
    return Markup(render_template_string("""
    <div class="fwgov-action-grid fwgov-config-shortcuts" data-keep-cumplimiento-nav="true">
      {% for icon, title, text, href in actions %}
      <a class="fwgov-action-card" href="{{ href }}">
        <span class="fwgov-action-icon"><i class="bi {{ icon }}"></i></span>
        <span class="fwgov-action-copy">
          <span class="fwgov-action-title d-block">{{ title }}</span>
          <span class="fwgov-action-text d-block">{{ text }}</span>
        </span>
        <i class="bi bi-arrow-right fwgov-action-arrow"></i>
      </a>
      {% endfor %}
    </div>
    """, actions=actions))


@app.route("/cumplimiento_continuo/firewall")
@login_required
def cumplimiento_continuo_firewall():
    """Pantalla principal: indicadores y hallazgos de Gobierno de Firewall."""
    user, resp = cont_comp_require_read()
    if resp:
        return resp

    devices, selected_device, _ = fwgov_page_selection()
    q = (request.args.get("q") or "").strip()
    severity_filter = (request.args.get("severity") or "").strip()
    status_filter = (request.args.get("status") or "").strip()

    findings_query = FirewallGovFinding.query.filter_by(active=True)
    if selected_device:
        findings_query = findings_query.filter_by(device_id=selected_device.id)

    if q:
        like = f"%{q}%"
        findings_query = findings_query.filter(or_(
            FirewallGovFinding.rule_name.ilike(like),
            FirewallGovFinding.rule_external_id.ilike(like),
            FirewallGovFinding.title.ilike(like),
            FirewallGovFinding.description.ilike(like),
            FirewallGovFinding.finding_code.ilike(like),
        ))
    if severity_filter:
        findings_query = findings_query.filter_by(severity=severity_filter)
    if status_filter:
        findings_query = findings_query.filter_by(status=status_filter)

    findings = findings_query.all()
    findings.sort(key=lambda f: (
        -FIREWALL_GOV_SEVERITY_ORDER.get(f.severity, 0),
        -(f.last_detected_at.timestamp() if f.last_detected_at else 0),
    ))
    findings = findings[:500]

    # Vincula cada hallazgo con su plan existente sin modificar el esquema
    # de firewall_governance.db. El vínculo se resuelve por source_ref.
    plan_refs = [f"firewall-finding:{finding.id}" for finding in findings]
    plan_by_ref = {}
    if plan_refs:
        existing_plans = ContinuousActionPlan.query.filter(
            ContinuousActionPlan.source_ref.in_(plan_refs)
        ).all()
        plan_by_ref = {
            (plan.source_ref or ""): plan.id
            for plan in existing_plans
            if plan.source_ref
        }
    for finding in findings:
        finding.action_plan_id = plan_by_ref.get(f"firewall-finding:{finding.id}")

    metrics = fwgov_dashboard_metrics(selected_device.id if selected_device else None)
    read_only = not cont_comp_can_write(user)
    selected_device_id = selected_device.id if selected_device else None

    content = render_template_string("""
    {{ extra_css|safe }}

    <div class="cc-card">
      <div class="d-flex flex-wrap justify-content-between align-items-center gap-3">
        <div>
          <h5 class="cc-section-title mb-1">Hallazgos de Gobierno de Firewall</h5>
          <div class="cc-muted">Vista principal para priorizar riesgos, responsables, tratamientos y planes de acción.</div>
        </div>
        {% if devices %}
        <form method="get" class="d-flex gap-2 align-items-end">
          <div>
            <label class="fwgov-small d-block mb-1">Firewall</label>
            <select class="form-select form-select-sm" name="device_id" onchange="this.form.submit()">
              {% for d in devices %}
              <option value="{{ d.id }}" {% if selected_device and selected_device.id == d.id %}selected{% endif %}>{{ d.name }}</option>
              {% endfor %}
            </select>
          </div>
          <noscript><button class="btn btn-sm btn-outline-primary">Aplicar</button></noscript>
        </form>
        {% endif %}
      </div>
    </div>

    {{ main_actions|safe }}

    <style>
      .fwgov-validation-details > summary {
        list-style: none;
        cursor: pointer;
        user-select: none;
      }
      .fwgov-validation-details > summary::-webkit-details-marker { display: none; }
      .fwgov-validation-summary {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
      }
      .fwgov-validation-toggle {
        display: inline-flex;
        align-items: center;
        gap: 7px;
        padding: 7px 12px;
        border: 1px solid #2f6fb6;
        border-radius: 10px;
        color: #1d4f8f;
        background: #fff;
        font-size: .82rem;
        font-weight: 700;
        white-space: nowrap;
      }
      .fwgov-validation-details[open] .fwgov-validation-toggle {
        background: #eef5ff;
      }
      .fwgov-validation-details .fwgov-toggle-hide { display: none; }
      .fwgov-validation-details[open] .fwgov-toggle-show { display: none; }
      .fwgov-validation-details[open] .fwgov-toggle-hide { display: inline; }
      .fwgov-validation-chevron { transition: transform .2s ease; }
      .fwgov-validation-details[open] .fwgov-validation-chevron { transform: rotate(180deg); }
      @media (max-width: 700px) {
        .fwgov-validation-summary { align-items: flex-start; }
        .fwgov-validation-summary-actions { width: 100%; justify-content: space-between; }
      }
    </style>

    <details class="cc-card mt-3 fwgov-validation-details">
      <summary class="fwgov-validation-summary" aria-label="Mostrar u ocultar validaciones de Gobierno de Firewall">
        <div>
          <h5 class="cc-section-title mb-1"><i class="bi bi-clipboard2-check me-1"></i> ¿Qué valida Gobierno de Firewall?</h5>
          <div class="cc-muted">Haz clic para consultar los puntos técnicos y de gobierno evaluados.</div>
        </div>
        <div class="d-flex flex-wrap align-items-center gap-2 fwgov-validation-summary-actions">
          <span class="badge rounded-pill text-bg-primary">21 validaciones automáticas</span>
          <span class="fwgov-validation-toggle">
            <span class="fwgov-toggle-show">Ver puntos evaluados</span>
            <span class="fwgov-toggle-hide">Ocultar puntos evaluados</span>
            <i class="bi bi-chevron-down fwgov-validation-chevron"></i>
          </span>
        </div>
      </summary>

      <div class="pt-3 mt-3 border-top">
        <div class="cc-muted mb-3">La evaluación analiza automáticamente 21 condiciones técnicas y de gobierno sobre las reglas sincronizadas. Cada hallazgo indica la regla afectada, el riesgo detectado, la recomendación y su mapeo con ISO 27001, NIST CSF y PCI DSS cuando corresponde.</div>

      <div class="row g-3 mt-1">
        <div class="col-xl-3 col-md-6">
          <div class="border rounded-3 p-3 h-100 bg-light">
            <div class="fw-bold text-primary mb-2"><i class="bi bi-shield-exclamation me-1"></i> Exposición y mínimo privilegio</div>
            <ul class="mb-0 ps-3 fwgov-small">
              <li>Reglas permisivas ANY-ANY sin restricción de origen, destino, protocolo o puerto.</li>
              <li>Reglas de acceso excesivamente amplias.</li>
              <li>Rangos de puertos demasiado extensos o iniciados en puertos reservados.</li>
              <li>Servicios administrativos expuestos desde cualquier origen.</li>
              <li>SMB —puerto 445— accesible desde orígenes amplios.</li>
              <li>Bases de datos accesibles desde cualquier origen.</li>
              <li>FTP o Telnet permitidos sin cifrado.</li>
            </ul>
          </div>
        </div>

        <div class="col-xl-3 col-md-6">
          <div class="border rounded-3 p-3 h-100 bg-light">
            <div class="fw-bold text-primary mb-2"><i class="bi bi-journal-check me-1"></i> Monitoreo y trazabilidad</div>
            <ul class="mb-0 ps-3 fwgov-small">
              <li>Logging desactivado en reglas que permiten tráfico.</li>
              <li>Reglas sin nombre o descripción que explique su propósito.</li>
              <li>Ausencia de propietario responsable.</li>
              <li>Ausencia de ticket o solicitud de cambio aprobada.</li>
              <li>Ausencia de justificación de negocio o seguridad.</li>
            </ul>
          </div>
        </div>

        <div class="col-xl-3 col-md-6">
          <div class="border rounded-3 p-3 h-100 bg-light">
            <div class="fw-bold text-primary mb-2"><i class="bi bi-calendar2-check me-1"></i> Vigencia y revisión</div>
            <ul class="mb-0 ps-3 fwgov-small">
              <li>Reglas sin fecha de revisión.</li>
              <li>Fechas de revisión con formato inválido.</li>
              <li>Revisiones con antigüedad superior a 365 días.</li>
              <li>Fechas de expiración inválidas.</li>
              <li>Reglas vencidas que continúan habilitadas.</li>
            </ul>
          </div>
        </div>

        <div class="col-xl-3 col-md-6">
          <div class="border rounded-3 p-3 h-100 bg-light">
            <div class="fw-bold text-primary mb-2"><i class="bi bi-diagram-3 me-1"></i> Calidad y orden de la política</div>
            <ul class="mb-0 ps-3 fwgov-small">
              <li>Reglas deshabilitadas pendientes de depuración.</li>
              <li>Reglas técnicamente duplicadas.</li>
              <li>Reglas ocultadas por una regla anterior con acción diferente.</li>
              <li>Reglas redundantes cubiertas por una regla anterior.</li>
            </ul>
          </div>
        </div>
      </div>
      <div class="fwgov-small mt-3"><i class="bi bi-info-circle me-1"></i> La validación se ejecuta sobre el inventario sincronizado del firewall. Los resultados dependen de los campos realmente entregados por el conector y de la calidad de la documentación de cada regla.</div>
      </div>
    </details>

    <div class="fwgov-kpi-grid">
      <div class="fwgov-kpi-card"><div class="fwgov-kpi-icon"><i class="bi bi-list-check"></i></div><div><div class="fwgov-kpi-number">{{ metrics.rules }}</div><div class="fwgov-kpi-label">Reglas sincronizadas</div></div></div>
      <div class="fwgov-kpi-card"><div class="fwgov-kpi-icon"><i class="bi bi-toggle-on"></i></div><div><div class="fwgov-kpi-number">{{ metrics.enabled_rules }}</div><div class="fwgov-kpi-label">Reglas habilitadas</div></div></div>
      <div class="fwgov-kpi-card"><div class="fwgov-kpi-icon"><i class="bi bi-exclamation-triangle"></i></div><div><div class="fwgov-kpi-number">{{ metrics.findings }}</div><div class="fwgov-kpi-label">Hallazgos activos</div></div></div>
      <div class="fwgov-kpi-card fwgov-kpi-critical"><div class="fwgov-kpi-icon"><i class="bi bi-x-octagon"></i></div><div><div class="fwgov-kpi-number">{{ metrics.critical }}</div><div class="fwgov-kpi-label">Críticos</div></div></div>
      <div class="fwgov-kpi-card fwgov-kpi-high"><div class="fwgov-kpi-icon"><i class="bi bi-shield-exclamation"></i></div><div><div class="fwgov-kpi-number">{{ metrics.high }}</div><div class="fwgov-kpi-label">Altos</div></div></div>
      <div class="fwgov-kpi-card fwgov-kpi-medium"><div class="fwgov-kpi-icon"><i class="bi bi-exclamation-circle"></i></div><div><div class="fwgov-kpi-number">{{ metrics.medium }}</div><div class="fwgov-kpi-label">Medios</div></div></div>
      <div class="fwgov-kpi-card fwgov-kpi-low"><div class="fwgov-kpi-icon"><i class="bi bi-info-circle"></i></div><div><div class="fwgov-kpi-number">{{ metrics.low }}</div><div class="fwgov-kpi-label">Bajos</div></div></div>
      <div class="fwgov-kpi-card fwgov-kpi-score"><div class="fwgov-kpi-icon"><i class="bi bi-speedometer2"></i></div><div><div class="fwgov-kpi-number">{{ metrics.score }}%</div><div class="fwgov-kpi-label">Score de gobierno</div></div></div>
    </div>

    <div class="cc-card mt-3">
      <div class="d-flex flex-wrap justify-content-between align-items-center gap-2">
        <div>
          <h5 class="cc-section-title mb-1">Matriz de hallazgos</h5>
          <div class="cc-muted">Mínimo privilegio, puertos de riesgo, logging, trazabilidad, vencimiento, duplicidad, redundancia y sombreado.</div>
        </div>
        <div class="d-flex flex-wrap gap-2">
          <form method="get" class="d-flex flex-wrap gap-2">
            {% if selected_device_id %}<input type="hidden" name="device_id" value="{{ selected_device_id }}">{% endif %}
            <input class="form-control form-control-sm" name="q" value="{{ q }}" placeholder="Buscar regla o hallazgo">
            <select class="form-select form-select-sm" name="severity">
              <option value="">Todas las severidades</option>
              {% for sev in ['Crítica','Alta','Media','Baja'] %}<option value="{{ sev }}" {% if severity_filter == sev %}selected{% endif %}>{{ sev }}</option>{% endfor %}
            </select>
            <select class="form-select form-select-sm" name="status">
              <option value="">Todos los estados</option>
              {% for st in ['Abierto','En tratamiento','Riesgo aceptado','Falso positivo','Resuelto','Resuelto automáticamente'] %}<option value="{{ st }}" {% if status_filter == st %}selected{% endif %}>{{ st }}</option>{% endfor %}
            </select>
            <button class="btn btn-sm btn-outline-primary" data-no-progress="true">Filtrar</button>
          </form>
          <a class="btn btn-sm btn-outline-success" href="{{ url_for('fwgov_export_csv', device_id=selected_device_id) }}" data-no-progress="true"><i class="bi bi-file-earmark-spreadsheet"></i> Exportar CSV</a>
        </div>
      </div>

      <div class="table-responsive fwgov-scroll mt-3">
        <table class="table cc-table table-hover align-middle">
          <thead><tr><th>Severidad</th><th>Regla</th><th>Hallazgo</th><th>Detalle</th><th>Control</th><th>Estado</th><th>Gestión</th></tr></thead>
          <tbody>
          {% for f in findings %}
            <tr>
              <td>{{ severity_badge(f.severity) }}</td>
              <td><div class="fw-bold">{{ f.rule_name or f.rule_external_id }}</div><div class="fwgov-code">{{ f.rule_external_id }}</div></td>
              <td><div class="fw-bold">{{ f.title }}</div><div class="fwgov-code">{{ f.finding_code }}</div></td>
              <td style="min-width:280px"><div>{{ f.description }}</div><div class="fwgov-small mt-1"><strong>Recomendación:</strong> {{ f.recommendation }}</div>{% if f.related_rule_external_id %}<div class="fwgov-small"><strong>Relacionada:</strong> {{ f.related_rule_external_id }}</div>{% endif %}</td>
              <td class="fwgov-small">{{ f.control_mapping }}</td>
              <td>{{ status_badge(f.status) }}<div class="fwgov-small mt-1">{{ f.assigned_to or 'Sin responsable' }}</div></td>
              <td style="min-width:250px">
                {% if not read_only %}
                <form method="post" action="{{ url_for('fwgov_update_finding', finding_id=f.id) }}" class="d-grid gap-1">
                  <select class="form-select form-select-sm" name="status">
                    {% for st in ['Abierto','En tratamiento','Riesgo aceptado','Falso positivo','Resuelto'] %}<option value="{{ st }}" {% if f.status == st %}selected{% endif %}>{{ st }}</option>{% endfor %}
                  </select>
                  <input class="form-control form-control-sm" name="assigned_to" value="{{ f.assigned_to or '' }}" placeholder="Responsable">
                  <input class="form-control form-control-sm" name="management_comment" value="{{ f.management_comment or '' }}" placeholder="Comentario de gestión">
                  <button class="btn btn-sm btn-outline-primary">Actualizar</button>
                </form>
                {% if f.action_plan_id %}
                <a class="btn btn-sm btn-success w-100 mt-1"
                   href="{{ url_for('planes_accion_dashboard', plan_id=f.action_plan_id) }}">
                  <i class="bi bi-box-arrow-up-right"></i> Ir al plan de acción
                </a>
                {% else %}
                <form method="post" action="{{ url_for('fwgov_create_plan', finding_id=f.id) }}" class="mt-1">
                  <button class="btn btn-sm btn-outline-danger w-100">
                    <i class="bi bi-clipboard2-plus"></i> Crear plan de acción
                  </button>
                </form>
                {% endif %}
                {% else %}
                <span class="fwgov-small">Solo lectura</span>
                {% endif %}
              </td>
            </tr>
          {% else %}
            <tr><td colspan="7" class="cc-empty">No hay hallazgos. Sincronice un firewall o ajuste los filtros.</td></tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
    """,
    extra_css=Markup(FIREWALL_GOV_EXTRA_CSS),
    main_actions=fwgov_main_actions(selected_device),
    devices=devices,
    selected_device=selected_device,
    selected_device_id=selected_device_id,
    metrics=metrics,
    findings=findings,
    q=q,
    severity_filter=severity_filter,
    status_filter=status_filter,
    read_only=read_only,
    severity_badge=fwgov_severity_badge,
    status_badge=fwgov_status_badge,
    )

    return cont_comp_render(
        content,
        "firewall",
        "Hallazgos de Gobierno de Firewall",
        "Indicadores ejecutivos, priorización de hallazgos y gestión de planes de acción.",
    )


@app.route("/cumplimiento_continuo/firewall/registrados")
@login_required
def fwgov_firewalls_registered():
    """Pantalla exclusiva para administrar los firewalls registrados."""
    user, resp = cont_comp_require_read()
    if resp:
        return resp

    devices, selected_device, _ = fwgov_page_selection()
    read_only = not cont_comp_can_write(user)

    content = render_template_string("""
    {{ extra_css|safe }}
    {{ back_button|safe }}

    <div class="cc-card">
      <div class="d-flex flex-wrap justify-content-between align-items-center gap-2">
        <div>
          <h5 class="cc-section-title mb-1">Firewalls registrados</h5>
          <div class="cc-muted">Conectores registrados para inventariar reglas y ejecutar evaluaciones de gobierno.</div>
        </div>
        {% if not read_only %}
        <a class="btn btn-primary" href="{{ url_for('fwgov_connector_config', new=1) }}"><i class="bi bi-plus-circle"></i> Registrar firewall</a>
        {% endif %}
      </div>

      {% if devices %}
      <div class="row g-3 mt-1">
        {% for d in devices %}
        <div class="col-xl-4 col-md-6">
          <div class="fwgov-device-card {% if selected_device and selected_device.id == d.id %}active{% endif %}">
            <div class="d-flex justify-content-between align-items-start gap-2">
              <div>
                <div class="fw-bold text-primary">{{ d.name }}</div>
                <div class="fwgov-small">{{ d.vendor }} · {{ d.base_url }}</div>
              </div>
              {{ device_status_badge(d.last_status) }}
            </div>
            <div class="fwgov-small mt-2"><strong>Última prueba:</strong> {{ d.last_test_at or 'Sin prueba' }}</div>
            <div class="fwgov-small"><strong>Última sincronización:</strong> {{ d.last_sync_at or 'Sin sincronización' }}</div>
            {% if d.last_message %}<div class="fwgov-small mt-2">{{ d.last_message }}</div>{% endif %}
            <div class="d-flex flex-wrap gap-2 mt-3">
              <a class="btn btn-sm btn-outline-secondary" href="{{ url_for('fwgov_connector_config', device_id=d.id) }}">Configurar</a>
              {% if not read_only %}
              <form method="post" action="{{ url_for('fwgov_test_device_route', device_id=d.id) }}">
                <button class="btn btn-sm btn-outline-success" data-progress-text="Probando conexión con el firewall...">Probar</button>
              </form>
              <form method="post" action="{{ url_for('fwgov_sync_device_route', device_id=d.id) }}">
                <button class="btn btn-sm btn-warning" data-progress-text="Sincronizando y evaluando reglas...">Sincronizar</button>
              </form>
              {% endif %}
            </div>
          </div>
        </div>
        {% endfor %}
      </div>
      {% else %}
      <div class="cc-empty mt-3">No hay firewalls registrados.</div>
      {% endif %}
    </div>
    """,
    extra_css=Markup(FIREWALL_GOV_EXTRA_CSS),
    back_button=fwgov_back_button(selected_device, "config"),
    devices=devices,
    selected_device=selected_device,
    read_only=read_only,
    device_status_badge=fwgov_device_status_badge,
    )

    return cont_comp_render(
        content,
        "firewall",
        "Firewalls registrados",
        "Inventario de conectores, estado de conexión y acciones de sincronización.",
    )


@app.route("/cumplimiento_continuo/firewall/configuracion")
@login_required
def fwgov_connector_config():
    """Pantalla exclusiva para crear o editar la configuración del conector."""
    user, resp = cont_comp_require_read()
    if resp:
        return resp

    devices, selected_device, new_mode = fwgov_page_selection(allow_new=True)
    read_only = not cont_comp_can_write(user)
    secret_configured = bool(selected_device and fwgov_decrypt(selected_device.api_secret_encrypted))
    key_configured = bool(selected_device and fwgov_decrypt(selected_device.api_key_encrypted))

    content = render_template_string("""
    {{ extra_css|safe }}
    {{ back_button|safe }}

    <div class="cc-card">
      <div class="d-flex flex-wrap justify-content-between align-items-center gap-2">
        <div>
          <h5 class="cc-section-title mb-1">Configuración del conector</h5>
          <div class="cc-muted">Credenciales, URL, filtros y parámetros de comunicación con OPNsense.</div>
        </div>
        <div class="d-flex flex-wrap gap-2">
          {% if devices %}
          <form method="get">
            <select class="form-select form-select-sm" name="device_id" onchange="this.form.submit()">
              <option value="">Seleccionar firewall</option>
              {% for d in devices %}<option value="{{ d.id }}" {% if selected_device and selected_device.id == d.id %}selected{% endif %}>{{ d.name }}</option>{% endfor %}
            </select>
          </form>
          {% endif %}
          {% if not read_only %}<a class="btn btn-sm btn-outline-primary" href="{{ url_for('fwgov_connector_config', new=1) }}">Nuevo registro</a>{% endif %}
        </div>
      </div>

      {{ config_shortcuts|safe }}

      <div class="alert alert-info py-2 small mt-3">
        La versión local/One-Premise puede conectarse directamente a una IP privada. Una versión alojada en nube requiere VPN, túnel o una API alcanzable y restringida.
      </div>

      {% if read_only %}
      <div class="alert alert-secondary">El rol actual tiene acceso de solo lectura.</div>
      {% else %}
      <form method="post" action="{{ url_for('fwgov_save_device') }}" class="cc-form">
        <input type="hidden" name="device_id" value="{{ selected_device.id if selected_device else '' }}">
        <div class="row g-3">
          <div class="col-md-3">
            <label>Nombre del firewall</label>
            <input class="form-control" name="name" required value="{{ selected_device.name if selected_device else 'OPNsense Laboratorio GRAC' }}">
          </div>
          <div class="col-md-2">
            <label>Fabricante</label>
            <select class="form-select" name="vendor"><option value="OPNsense" selected>OPNsense</option></select>
          </div>
          <div class="col-md-4">
            <label>URL base API</label>
            <input class="form-control" name="base_url" required value="{{ selected_device.base_url if selected_device else default_url }}" placeholder="https://192.168.100.10">
          </div>
          <div class="col-md-3">
            <label>Timeout (segundos)</label>
            <input class="form-control" type="number" min="5" max="120" name="timeout_seconds" value="{{ selected_device.timeout_seconds if selected_device else 30 }}">
          </div>

          <div class="col-md-6">
            <label>API key {% if key_configured %}<span class="fwgov-secret-state">· configurada</span>{% endif %}</label>
            <input class="form-control" type="password" name="api_key" autocomplete="new-password" placeholder="Dejar vacío para conservar la actual">
          </div>
          <div class="col-md-6">
            <label>API secret {% if secret_configured %}<span class="fwgov-secret-state">· configurado</span>{% endif %}</label>
            <input class="form-control" type="password" name="api_secret" autocomplete="new-password" placeholder="Dejar vacío para conservar el actual">
          </div>

          <div class="col-md-4">
            <label>Texto de búsqueda API</label>
            <input class="form-control" name="search_phrase" value="{{ selected_device.search_phrase if selected_device else 'GRAC-' }}" placeholder="Vacío para todas las reglas">
          </div>
          <div class="col-md-4">
            <label>Filtro local de categoría</label>
            <input class="form-control" name="category_filter" value="{{ selected_device.category_filter if selected_device else 'GRAC_LAB' }}" placeholder="Vacío para todas las categorías">
          </div>
          <div class="col-md-2 d-flex align-items-end">
            <div class="form-check mb-2">
              <input class="form-check-input" type="checkbox" name="verify_ssl" value="1" id="fwVerifySsl" {% if selected_device and selected_device.verify_ssl %}checked{% endif %}>
              <label class="form-check-label" for="fwVerifySsl">Validar certificado TLS</label>
            </div>
          </div>
          <div class="col-md-2 d-flex align-items-end">
            <div class="form-check mb-2">
              <input class="form-check-input" type="checkbox" name="enabled" value="1" id="fwEnabled" {% if not selected_device or selected_device.enabled %}checked{% endif %}>
              <label class="form-check-label" for="fwEnabled">Conector habilitado</label>
            </div>
          </div>
        </div>
        <div class="d-flex gap-2 mt-3">
          <button class="btn btn-primary" data-progress-text="Guardando configuración del firewall..."><i class="bi bi-save"></i> Guardar configuración</button>
        </div>
      </form>
      {% endif %}
    </div>
    """,
    extra_css=Markup(FIREWALL_GOV_EXTRA_CSS),
    back_button=fwgov_back_button(selected_device, "findings"),
    config_shortcuts=fwgov_config_shortcuts(selected_device),
    devices=devices,
    selected_device=selected_device,
    new_mode=new_mode,
    read_only=read_only,
    key_configured=key_configured,
    secret_configured=secret_configured,
    default_url=FIREWALL_GOV_DEFAULT_URL,
    )

    return cont_comp_render(
        content,
        "firewall",
        "Configuración del conector",
        "Administración segura de la conexión API con el firewall.",
    )


@app.route("/cumplimiento_continuo/firewall/inventario")
@login_required
def fwgov_rules_inventory():
    """Pantalla exclusiva para el inventario normalizado de reglas."""
    user, resp = cont_comp_require_read()
    if resp:
        return resp

    devices, selected_device, _ = fwgov_page_selection()
    q = (request.args.get("q") or "").strip()

    rules_query = FirewallGovRule.query.filter_by(active=True)
    if selected_device:
        rules_query = rules_query.filter_by(device_id=selected_device.id)
    if q:
        like = f"%{q}%"
        rules_query = rules_query.filter(or_(
            FirewallGovRule.name.ilike(like),
            FirewallGovRule.description.ilike(like),
            FirewallGovRule.source.ilike(like),
            FirewallGovRule.destination.ilike(like),
            FirewallGovRule.protocol.ilike(like),
            FirewallGovRule.destination_port.ilike(like),
        ))

    rules = rules_query.order_by(
        FirewallGovRule.sort_order.asc(), FirewallGovRule.sequence.asc(), FirewallGovRule.id.asc()
    ).limit(1000).all()

    finding_counts = defaultdict(int)
    max_severity = {}
    findings_query = FirewallGovFinding.query.filter_by(active=True)
    if selected_device:
        findings_query = findings_query.filter_by(device_id=selected_device.id)
    for finding in findings_query.all():
        if finding.rule_id:
            finding_counts[finding.rule_id] += 1
            current = max_severity.get(finding.rule_id)
            if FIREWALL_GOV_SEVERITY_ORDER.get(finding.severity, 0) > FIREWALL_GOV_SEVERITY_ORDER.get(current, -1):
                max_severity[finding.rule_id] = finding.severity

    content = render_template_string("""
    {{ extra_css|safe }}
    {{ back_button|safe }}

    <div class="cc-card">
      <div class="d-flex flex-wrap justify-content-between align-items-center gap-2">
        <div>
          <h5 class="cc-section-title mb-1">Inventario normalizado de reglas</h5>
          <div class="cc-muted">Vista técnica estandarizada de las reglas sincronizadas desde el firewall.</div>
        </div>
        <form method="get" class="d-flex flex-wrap gap-2">
          {% if devices %}
          <select class="form-select form-select-sm" name="device_id">
            {% for d in devices %}<option value="{{ d.id }}" {% if selected_device and selected_device.id == d.id %}selected{% endif %}>{{ d.name }}</option>{% endfor %}
          </select>
          {% endif %}
          <input class="form-control form-control-sm" name="q" value="{{ q }}" placeholder="Buscar regla, origen, destino o puerto">
          <button class="btn btn-sm btn-outline-primary" data-no-progress="true">Filtrar</button>
        </form>
      </div>

      <div class="table-responsive fwgov-scroll mt-3">
        <table class="table cc-table table-hover align-middle">
          <thead><tr><th>Orden</th><th>Estado</th><th>Nombre</th><th>Acción</th><th>Interfaz</th><th>Protocolo</th><th>Origen</th><th>Destino</th><th>Puerto</th><th>Log</th><th>Gobierno</th><th>Hallazgos</th></tr></thead>
          <tbody>
          {% for r in rules %}
            <tr>
              <td>{{ r.sequence or '-' }}</td>
              <td>{% if r.enabled %}<span class="badge bg-success">Habilitada</span>{% else %}<span class="badge bg-secondary">Deshabilitada</span>{% endif %}</td>
              <td><div class="fw-bold fwgov-truncate" title="{{ r.description }}">{{ r.name }}</div><div class="fwgov-code">{{ r.external_id }}</div></td>
              <td><span class="badge {% if r.action|lower in ['pass','allow','permit'] %}bg-success{% else %}bg-danger{% endif %}">{{ r.action }}</span></td>
              <td>{{ r.interface }} / {{ r.direction }}</td>
              <td>{{ r.ip_version }} · {{ r.protocol }}</td>
              <td>{{ r.source }}{% if r.source_port and r.source_port != 'any' %}:{{ r.source_port }}{% endif %}</td>
              <td>{{ r.destination }}</td>
              <td><span class="fwgov-code">{{ r.destination_port or 'any' }}</span></td>
              <td>{% if r.logging_enabled %}<span class="badge bg-success">Sí</span>{% else %}<span class="badge bg-warning text-dark">No</span>{% endif %}</td>
              <td class="fwgov-small">OWNER={{ r.owner or '—' }}<br>TICKET={{ r.ticket or '—' }}<br>REVIEW={{ r.review_date or '—' }}<br>EXPIRES={{ r.expiration_date or '—' }}</td>
              <td>{% if finding_counts.get(r.id) %}{{ severity_badge(max_severity.get(r.id)) }} <strong>{{ finding_counts.get(r.id) }}</strong>{% else %}<span class="badge bg-success">0</span>{% endif %}</td>
            </tr>
          {% else %}
            <tr><td colspan="12" class="cc-empty">No hay reglas sincronizadas.</td></tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
    """,
    extra_css=Markup(FIREWALL_GOV_EXTRA_CSS),
    back_button=fwgov_back_button(selected_device, "findings"),
    devices=devices,
    selected_device=selected_device,
    rules=rules,
    q=q,
    finding_counts=finding_counts,
    max_severity=max_severity,
    severity_badge=fwgov_severity_badge,
    )

    return cont_comp_render(
        content,
        "firewall",
        "Inventario normalizado de reglas",
        "Reglas normalizadas, metadatos de gobierno y relación con hallazgos.",
    )


@app.route("/cumplimiento_continuo/firewall/historial")
@login_required
def fwgov_sync_history():
    """Pantalla exclusiva para el historial de sincronización."""
    user, resp = cont_comp_require_read()
    if resp:
        return resp

    devices, selected_device, _ = fwgov_page_selection()
    logs_query = FirewallGovSyncLog.query
    if selected_device:
        logs_query = logs_query.filter_by(device_id=selected_device.id)
    recent_logs = logs_query.order_by(FirewallGovSyncLog.id.desc()).limit(500).all()
    device_names = {d.id: d.name for d in devices}

    content = render_template_string("""
    {{ extra_css|safe }}
    {{ back_button|safe }}

    <div class="cc-card">
      <div class="d-flex flex-wrap justify-content-between align-items-center gap-2">
        <div>
          <h5 class="cc-section-title mb-1">Historial de sincronización</h5>
          <div class="cc-muted">Trazabilidad de pruebas, sincronizaciones, reglas recibidas, hallazgos y score obtenido.</div>
        </div>
        {% if devices %}
        <form method="get">
          <select class="form-select form-select-sm" name="device_id" onchange="this.form.submit()">
            {% for d in devices %}<option value="{{ d.id }}" {% if selected_device and selected_device.id == d.id %}selected{% endif %}>{{ d.name }}</option>{% endfor %}
          </select>
        </form>
        {% endif %}
      </div>

      <div class="table-responsive mt-3">
        <table class="table cc-table align-middle">
          <thead><tr><th>Firewall</th><th>Inicio</th><th>Fin</th><th>Estado</th><th>Reglas recibidas</th><th>Reglas activas</th><th>Hallazgos</th><th>Críticos</th><th>Score</th><th>Ejecutado por</th><th>Mensaje</th></tr></thead>
          <tbody>
          {% for log in recent_logs %}
            <tr>
              <td>{{ device_names.get(log.device_id, log.device_id) }}</td>
              <td>{{ log.started_at }}</td>
              <td>{{ log.finished_at or '—' }}</td>
              <td><span class="badge {% if log.status == 'Completado' %}bg-success{% elif log.status == 'Error' %}bg-danger{% else %}bg-warning text-dark{% endif %}">{{ log.status }}</span></td>
              <td>{{ log.rules_received }}</td>
              <td>{{ log.rules_active }}</td>
              <td>{{ log.findings_active }}</td>
              <td>{{ log.critical_findings }}</td>
              <td>{{ log.compliance_score }}%</td>
              <td>{{ log.executed_by or 'Sistema' }}</td>
              <td style="min-width:260px">{{ log.message }}</td>
            </tr>
          {% else %}
            <tr><td colspan="11" class="cc-empty">Sin historial de sincronización.</td></tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
    """,
    extra_css=Markup(FIREWALL_GOV_EXTRA_CSS),
    back_button=fwgov_back_button(selected_device, "config"),
    devices=devices,
    selected_device=selected_device,
    recent_logs=recent_logs,
    device_names=device_names,
    )

    return cont_comp_render(
        content,
        "firewall",
        "Historial de sincronización",
        "Registro cronológico de ejecuciones y resultados del conector.",
    )


@app.route("/cumplimiento_continuo/firewall/dispositivo/guardar", methods=["POST"])
@login_required
def fwgov_save_device():
    user, resp = cont_comp_require_write()
    if resp:
        return resp

    device_id = request.form.get("device_id", type=int)
    device = FirewallGovDevice.query.get(device_id) if device_id else None
    creating = device is None
    if creating:
        device = FirewallGovDevice()
        db.session.add(device)

    try:
        device.name = (request.form.get("name") or "").strip()
        if not device.name:
            raise ValueError("Debe indicar un nombre para el firewall.")
        device.vendor = (request.form.get("vendor") or FIREWALL_GOV_VENDOR_OPNSENSE).strip()
        device.base_url = fwgov_clean_url(request.form.get("base_url"))
        device.timeout_seconds = fwgov_safe_int(request.form.get("timeout_seconds"), 30, 5, 120)
        device.search_phrase = (request.form.get("search_phrase") or "").strip()
        device.category_filter = (request.form.get("category_filter") or "").strip()
        device.verify_ssl = request.form.get("verify_ssl") == "1"
        device.enabled = request.form.get("enabled") == "1"

        api_key = (request.form.get("api_key") or "").strip()
        api_secret = (request.form.get("api_secret") or "").strip()
        if api_key:
            device.api_key_encrypted = fwgov_encrypt(api_key)
        if api_secret:
            device.api_secret_encrypted = fwgov_encrypt(api_secret)

        if creating and (not device.api_key_encrypted or not device.api_secret_encrypted):
            raise ValueError("Para registrar un firewall nuevo debe ingresar API key y API secret.")

        db.session.commit()
        registrar_log(fwgov_current_username(user), f"Configuración de Gobierno de Firewall guardada para {device.name}.")
        flash("Configuración del firewall guardada correctamente.", "success")
        return redirect(url_for("fwgov_connector_config", device_id=device.id))

    except Exception as exc:
        db.session.rollback()
        flash(f"No fue posible guardar la configuración: {exc}", "danger")
        return redirect(url_for("fwgov_connector_config", device_id=device_id) if device_id else url_for("fwgov_connector_config", new=1))


@app.route("/cumplimiento_continuo/firewall/dispositivo/<int:device_id>/probar", methods=["POST"])
@login_required
def fwgov_test_device_route(device_id):
    user, resp = cont_comp_require_write()
    if resp:
        return resp

    device = FirewallGovDevice.query.get_or_404(device_id)
    ok, message, endpoint = fwgov_test_device(device)
    registrar_log(fwgov_current_username(user), f"Prueba de conexión Firewall Governance ({device.name}): {message}")
    flash(message, "success" if ok else "danger")
    return redirect(url_for("fwgov_firewalls_registered", device_id=device.id))


@app.route("/cumplimiento_continuo/firewall/dispositivo/<int:device_id>/sincronizar", methods=["POST"])
@login_required
def fwgov_sync_device_route(device_id):
    user, resp = cont_comp_require_write()
    if resp:
        return resp

    device = FirewallGovDevice.query.get_or_404(device_id)
    if not device.enabled:
        flash("El conector está deshabilitado. Habilítelo antes de sincronizar.", "warning")
        return redirect(url_for("fwgov_firewalls_registered", device_id=device.id))

    try:
        result = fwgov_sync_device(device, fwgov_current_username(user))
        registrar_log(
            fwgov_current_username(user),
            f"Gobierno de Firewall sincronizado para {device.name}: {result['rules']} reglas, {result['findings']} hallazgos, score {result['score']}%.",
        )
        flash(
            f"Sincronización completada: {result['rules']} reglas, {result['findings']} hallazgos y score {result['score']}%.",
            "success",
        )
    except Exception as exc:
        registrar_log(fwgov_current_username(user), f"Error sincronizando Gobierno de Firewall ({device.name}): {exc}")
        flash(f"No fue posible sincronizar el firewall: {exc}", "danger")

    return redirect(url_for("fwgov_firewalls_registered", device_id=device.id))


@app.route("/cumplimiento_continuo/firewall/hallazgo/<int:finding_id>/actualizar", methods=["POST"])
@login_required
def fwgov_update_finding(finding_id):
    user, resp = cont_comp_require_write()
    if resp:
        return resp

    finding = FirewallGovFinding.query.get_or_404(finding_id)
    allowed_statuses = {"Abierto", "En tratamiento", "Riesgo aceptado", "Falso positivo", "Resuelto"}
    new_status = (request.form.get("status") or "Abierto").strip()
    if new_status not in allowed_statuses:
        new_status = "Abierto"

    finding.status = new_status
    finding.assigned_to = (request.form.get("assigned_to") or "").strip()
    finding.management_comment = (request.form.get("management_comment") or "").strip()
    finding.updated_at = datetime.utcnow()
    if new_status == "Resuelto":
        finding.resolved_at = datetime.utcnow()
    elif new_status not in ("Resuelto", "Resuelto automáticamente"):
        finding.resolved_at = None
    db.session.commit()

    registrar_log(
        fwgov_current_username(user),
        f"Hallazgo de firewall {finding.finding_code} actualizado a {finding.status}.",
    )
    flash("Hallazgo actualizado correctamente.", "success")
    return redirect(url_for("cumplimiento_continuo_firewall", device_id=finding.device_id))


@app.route("/cumplimiento_continuo/firewall/hallazgo/<int:finding_id>/crear_plan", methods=["POST"])
@login_required
def fwgov_create_plan(finding_id):
    user, resp = cont_comp_require_write()
    if resp:
        return resp

    finding = FirewallGovFinding.query.get_or_404(finding_id)
    source_ref = f"firewall-finding:{finding.id}"
    existing = ContinuousActionPlan.query.filter_by(source_ref=source_ref).first()
    if existing:
        if finding.status not in ("Resuelto", "Resuelto automáticamente", "Falso positivo"):
            finding.status = "En tratamiento"
            finding.updated_at = datetime.utcnow()
            db.session.commit()
        flash("Este hallazgo ya tiene un plan de acción asociado.", "warning")
        return redirect(url_for("planes_accion_dashboard", plan_id=existing.id))

    plan = ContinuousActionPlan(
        origin="Firewall Governance",
        standard="MULTI",
        control_code=finding.finding_code,
        title=f"Remediar: {finding.title}",
        description=f"Regla: {finding.rule_name or finding.rule_external_id}\n\n{finding.description}\n\nRecomendación: {finding.recommendation}",
        asset=finding.rule_name or finding.rule_external_id,
        severity=finding.severity,
        action_type="Remediación",
        responsible=finding.assigned_to or fwgov_current_username(user),
        status="Abierto",
        source_ref=source_ref,
        raw_json=json.dumps({
            "finding_id": finding.id,
            "rule_external_id": finding.rule_external_id,
            "finding_code": finding.finding_code,
            "control_mapping": finding.control_mapping,
        }, ensure_ascii=False),
    )
    db.session.add(plan)
    if finding.status not in ("Resuelto", "Resuelto automáticamente", "Falso positivo"):
        finding.status = "En tratamiento"
        finding.updated_at = datetime.utcnow()
    db.session.commit()

    registrar_log(fwgov_current_username(user), f"Plan de acción creado desde hallazgo de firewall {finding.finding_code}.")
    flash("Plan de acción creado correctamente.", "success")
    return redirect(url_for("planes_accion_dashboard", plan_id=plan.id))


@app.route("/cumplimiento_continuo/firewall/exportar.csv")
@login_required
def fwgov_export_csv():
    user, resp = cont_comp_require_read()
    if resp:
        return resp

    device_id = request.args.get("device_id", type=int)
    query = FirewallGovFinding.query.filter_by(active=True)
    if device_id:
        query = query.filter_by(device_id=device_id)
    findings = query.order_by(FirewallGovFinding.id.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Dispositivo", "Regla", "UUID regla", "Código", "Severidad", "Título", "Descripción",
        "Recomendación", "Mapeo de control", "Estado", "Responsable", "Comentario", "Primera detección", "Última detección",
    ])

    device_names = {d.id: d.name for d in FirewallGovDevice.query.all()}
    for finding in findings:
        writer.writerow([
            device_names.get(finding.device_id, finding.device_id),
            finding.rule_name,
            finding.rule_external_id,
            finding.finding_code,
            finding.severity,
            finding.title,
            finding.description,
            finding.recommendation,
            finding.control_mapping,
            finding.status,
            finding.assigned_to,
            finding.management_comment,
            finding.first_detected_at,
            finding.last_detected_at,
        ])

    response = make_response("\ufeff" + output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=hallazgos_gobierno_firewall.csv"
    return response


# ============================================================================================================================================
#                                      FIN MÓDULO GOBIERNO DE FIREWALL
# ============================================================================================================================================


# ============================================================================================================================================
#                                            FIN MÓDULO CUMPLIMIENTO CONTINUO - WAZUH + GRAC
# ============================================================================================================================================




# ============================================================================================================================================
#                                                       MÓDULO PRUEBAS SAST - OLLAMA LOCAL
# ============================================================================================================================================
# Integración directa al SGSI:
# - Menú: Gestión de Eventos -> Pruebas SAST
# - Motor IA: Ollama local (/api/tags y /api/chat)
# - Salidas: PDF + JSON en reports/sast
# - No usa llaves externas ni OpenRouter/Azure para este módulo.

try:
    app.json.ensure_ascii = False
except Exception:
    pass

SAST_APP_TITLE = "Pruebas SAST con IA Local – OWASP / CERT / SANS"
SAST_MODULE_NAME = "Pruebas SAST"
SAST_BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SAST_UPLOAD_DIR = os.path.join(SAST_BASE_DIR, "uploads", "sast")
SAST_REPORT_DIR = os.path.join(SAST_BASE_DIR, "reports", "sast")
SAST_CONFIG_FILE = os.path.join(SAST_BASE_DIR, "sast_ollama_config.json")
SAST_HISTORY_FILE = os.path.join(SAST_REPORT_DIR, "sast_scan_history.json")
SAST_MAX_CODE_CHARS = int(os.getenv("SAST_MAX_CODE_CHARS", "22000"))

SAST_ALLOWED_EXT = {
    ".py", ".js", ".ts", ".java", ".cs", ".go", ".php", ".rb", ".c", ".cpp", ".h",
    ".json", ".yml", ".yaml", ".xml", ".html", ".sql", ".txt", ".md", ".css", ".sh"
}

os.makedirs(SAST_UPLOAD_DIR, exist_ok=True)
os.makedirs(SAST_REPORT_DIR, exist_ok=True)

SAST_DEFAULT_OLLAMA_CONFIG = {
    "base_url": os.getenv("SAST_OLLAMA_BASE_URL", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")),
    "default_model": os.getenv("SAST_OLLAMA_MODEL", os.getenv("OLLAMA_MODEL", "")),
    "temperature": float(os.getenv("SAST_OLLAMA_TEMPERATURE", "0.2")),
    "timeout": int(os.getenv("SAST_OLLAMA_TIMEOUT", "240")),
    "summary_max_tokens": int(os.getenv("SAST_OLLAMA_SUMMARY_MAX_TOKENS", "1100")),
    "findings_max_tokens": int(os.getenv("SAST_OLLAMA_FINDINGS_MAX_TOKENS", "4000")),
}

SAST_JOBS = {}
SAST_MAX_CONCURRENT_JOBS = int(os.getenv("SAST_MAX_CONCURRENT_JOBS", "1"))
_sast_job_sem = threading.Semaphore(SAST_MAX_CONCURRENT_JOBS)
_sast_ollama_lock = threading.Lock()

_sast_history_lock = threading.Lock()


def sast_safe_int(value, default=0):
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def sast_safe_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def sast_history_report_id_from_json_name(json_name):
    base = os.path.basename(json_name or "")
    if base.startswith("analysis_") and base.endswith(".json"):
        return base[len("analysis_"):-len(".json")]
    return ""


def sast_counts_from_analysis(analysis):
    analysis = analysis or {}
    metrics = analysis.get("metrics", {}) or {}
    findings = analysis.get("findings", []) or []
    by_sev = dict(metrics.get("by_severity", {}) or {})

    if not by_sev and isinstance(findings, list):
        by_sev = {"Crítico": 0, "Alto": 0, "Medio": 0, "Bajo": 0}
        for finding in findings:
            if not isinstance(finding, dict):
                continue
            sev = (finding.get("severity") or "Bajo").strip()
            if sev in ("Critico", "Critical", "critical"):
                sev = "Crítico"
            if sev == "Alta":
                sev = "Alto"
            if sev == "Media":
                sev = "Medio"
            if sev == "Baja":
                sev = "Bajo"
            by_sev[sev] = by_sev.get(sev, 0) + 1

    total = metrics.get("total_findings")
    if total is None:
        total = len(findings) if isinstance(findings, list) else 0

    return {
        "total_findings": sast_safe_int(total, 0),
        "critical_count": sast_safe_int(by_sev.get("Crítico", by_sev.get("Critica", by_sev.get("Critical", 0))), 0),
        "high_count": sast_safe_int(by_sev.get("Alto", by_sev.get("Alta", by_sev.get("High", 0))), 0),
        "medium_count": sast_safe_int(by_sev.get("Medio", by_sev.get("Media", by_sev.get("Medium", 0))), 0),
        "low_count": sast_safe_int(by_sev.get("Bajo", by_sev.get("Baja", by_sev.get("Low", 0))), 0),
    }


def sast_record_sort_key(record):
    date_txt = (record.get("date_str") or record.get("created_at") or "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_txt[:19], fmt).timestamp()
        except Exception:
            pass
    return sast_safe_float(record.get("mtime"), 0.0)


def sast_build_scan_history_record(report_id, analysis, meta, pdf_name, json_name, registration_summary=None, payload=None):
    analysis = analysis or {}
    meta = meta or {}
    registration_summary = registration_summary or {}
    payload = payload or {}
    ex = analysis.get("executive_summary", {}) or {}
    counts = sast_counts_from_analysis(analysis)

    return {
        "report_id": str(report_id or "").strip(),
        "date_str": meta.get("date_str") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "project_name": meta.get("project_name") or "Proyecto sin nombre",
        "artifact_type": meta.get("artifact_type") or "N/A",
        "filename": meta.get("filename") or "N/A",
        "language": meta.get("language") or "N/A",
        "model": meta.get("model") or "Ollama local",
        "overall_risk_level": ex.get("overall_risk_level") or "N/A",
        "overall_risk_score": ex.get("overall_risk_score", "N/A"),
        "total_findings": counts["total_findings"],
        "critical_count": counts["critical_count"],
        "high_count": counts["high_count"],
        "medium_count": counts["medium_count"],
        "low_count": counts["low_count"],
        "pdf_name": pdf_name or "",
        "json_name": json_name or "",
        "requested_register_vulnerabilities": bool(registration_summary.get("requested_register_vulnerabilities", payload.get("register_vulnerabilities"))),
        "requested_create_remediation_plans": bool(registration_summary.get("requested_create_remediation_plans", payload.get("create_remediation_plans"))),
        "requested_ai_remediation": bool(registration_summary.get("requested_ai_remediation", payload.get("generate_ai_remediation"))),
        "vulnerabilities_created": sast_safe_int(registration_summary.get("vulnerabilities_created"), 0),
        "remediation_plans_created": sast_safe_int(registration_summary.get("remediation_plans_created"), 0),
        "registration_error": registration_summary.get("error") or "",
        "executed_by": payload.get("username") or payload.get("responsable") or session.get("username") or "N/A",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }


def sast_load_history_file_records():
    if not os.path.exists(SAST_HISTORY_FILE):
        return []
    try:
        with open(SAST_HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
    except Exception as e:
        print("No se pudo leer historial SAST:", repr(e))
    return []


def sast_write_history_file_records(records):
    try:
        os.makedirs(SAST_REPORT_DIR, exist_ok=True)
        tmp = SAST_HISTORY_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        os.replace(tmp, SAST_HISTORY_FILE)
    except Exception as e:
        print("No se pudo escribir historial SAST:", repr(e))


def sast_save_scan_history_record(record):
    if not isinstance(record, dict):
        return
    report_id = (record.get("report_id") or "").strip()
    if not report_id:
        return

    with _sast_history_lock:
        records = sast_load_history_file_records()
        updated = False
        for idx, item in enumerate(records):
            if (item.get("report_id") or "").strip() == report_id:
                current = dict(item)
                current.update(record)
                records[idx] = current
                updated = True
                break
        if not updated:
            records.append(record)
        records.sort(key=sast_record_sort_key, reverse=True)
        sast_write_history_file_records(records)


def sast_discover_scan_history_from_reports(existing_ids=None):
    existing_ids = set(existing_ids or [])
    discovered = []
    try:
        if not os.path.isdir(SAST_REPORT_DIR):
            return discovered
        for name in os.listdir(SAST_REPORT_DIR):
            if not (name.startswith("analysis_") and name.endswith(".json")):
                continue
            report_id = sast_history_report_id_from_json_name(name)
            if not report_id or report_id in existing_ids:
                continue
            json_path = os.path.join(SAST_REPORT_DIR, name)
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    analysis = json.load(f)
                if not isinstance(analysis, dict):
                    continue
            except Exception:
                continue

            meta = analysis.get("sast_meta", {}) or {}
            reg = analysis.get("sgsi_registration", {}) or {}
            report = analysis.get("sast_report", {}) or {}
            pdf_name = report.get("pdf_name") or f"Informe_SAST_{report_id}.pdf"
            stat = os.stat(json_path)

            if not meta.get("date_str"):
                try:
                    meta["date_str"] = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    meta["date_str"] = ""
            if not meta.get("project_name"):
                meta["project_name"] = "Análisis SAST"
            if not meta.get("filename"):
                meta["filename"] = "N/A"
            if not meta.get("model"):
                meta["model"] = "Ollama local"

            record = sast_build_scan_history_record(report_id, analysis, meta, pdf_name, name, reg, {})
            record["mtime"] = stat.st_mtime
            discovered.append(record)
    except Exception as e:
        print("No se pudo reconstruir historial SAST desde reportes:", repr(e))
    return discovered


def sast_get_scan_history():
    with _sast_history_lock:
        records = sast_load_history_file_records()
        existing_ids = {(r.get("report_id") or "").strip() for r in records if isinstance(r, dict)}
        discovered = sast_discover_scan_history_from_reports(existing_ids)
        if discovered:
            records.extend(discovered)
            records.sort(key=sast_record_sort_key, reverse=True)
            sast_write_history_file_records(records)
        else:
            records.sort(key=sast_record_sort_key, reverse=True)
        return records


def sast_get_scan_history_record(report_id):
    report_id = (report_id or "").strip()
    if not report_id:
        return None
    for record in sast_get_scan_history():
        if (record.get("report_id") or "").strip() == report_id:
            return record
    return None


def sast_delete_scan_history_record(report_id):
    """
    Elimina un registro del historial SAST sin tocar vulnerabilidades ni planes de remediación.
    Retorna True si el registro existía en el archivo de historial.
    """
    report_id = (report_id or "").strip()
    if not report_id:
        return False

    with _sast_history_lock:
        records = sast_load_history_file_records()
        new_records = [
            r for r in records
            if (r.get("report_id") or "").strip() != report_id
        ]

        changed = len(new_records) != len(records)
        sast_write_history_file_records(new_records)
        return changed


def sast_require_access(write=False, config=False):
    user = User.query.get(session.get("user_id"))

    if not user:
        flash("Debe iniciar sesión.", "danger")
        return None, redirect(url_for("login")), True

    if getattr(user, "role", "") == "admin":
        return user, None, False

    if config:
        flash("Solo el administrador puede modificar la configuración SAST/Ollama.", "danger")
        return user, redirect(url_for("menu")), True

    if getattr(user, "role", "") == "auditor":
        if write:
            flash("El rol Auditor solo puede consultar este módulo.", "danger")
            return user, redirect(url_for("sast_index")), True
        return user, None, True

    if not verificar_permiso(user, SAST_MODULE_NAME):
        flash("No tiene permiso para acceder al módulo Pruebas SAST.", "danger")
        return user, redirect(url_for("menu")), True

    return user, None, False


def sast_normalize_ollama_base_url(base_url):
    base_url = (base_url or SAST_DEFAULT_OLLAMA_CONFIG["base_url"]).strip()
    if not base_url.startswith(("http://", "https://")):
        base_url = "http://" + base_url
    return base_url.rstrip("/")


def sast_coerce_float(value, default):
    try:
        return float(value)
    except Exception:
        return float(default)


def sast_coerce_int(value, default):
    try:
        return int(value)
    except Exception:
        return int(default)


def sast_load_ollama_config():
    cfg = dict(SAST_DEFAULT_OLLAMA_CONFIG)

    if os.path.exists(SAST_CONFIG_FILE):
        try:
            with open(SAST_CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            if isinstance(saved, dict):
                cfg.update(saved)
        except Exception:
            pass

    cfg["base_url"] = sast_normalize_ollama_base_url(cfg.get("base_url"))
    cfg["default_model"] = (cfg.get("default_model") or "").strip()
    cfg["temperature"] = sast_coerce_float(cfg.get("temperature"), SAST_DEFAULT_OLLAMA_CONFIG["temperature"])
    cfg["timeout"] = sast_coerce_int(cfg.get("timeout"), SAST_DEFAULT_OLLAMA_CONFIG["timeout"])
    cfg["summary_max_tokens"] = sast_coerce_int(cfg.get("summary_max_tokens"), SAST_DEFAULT_OLLAMA_CONFIG["summary_max_tokens"])
    cfg["findings_max_tokens"] = sast_coerce_int(cfg.get("findings_max_tokens"), SAST_DEFAULT_OLLAMA_CONFIG["findings_max_tokens"])
    return cfg


def sast_save_ollama_config(config):
    cfg = sast_load_ollama_config()
    cfg.update(config or {})
    cfg["base_url"] = sast_normalize_ollama_base_url(cfg.get("base_url"))
    cfg["default_model"] = (cfg.get("default_model") or "").strip()
    cfg["temperature"] = sast_coerce_float(cfg.get("temperature"), SAST_DEFAULT_OLLAMA_CONFIG["temperature"])
    cfg["timeout"] = sast_coerce_int(cfg.get("timeout"), SAST_DEFAULT_OLLAMA_CONFIG["timeout"])
    cfg["summary_max_tokens"] = sast_coerce_int(cfg.get("summary_max_tokens"), SAST_DEFAULT_OLLAMA_CONFIG["summary_max_tokens"])
    cfg["findings_max_tokens"] = sast_coerce_int(cfg.get("findings_max_tokens"), SAST_DEFAULT_OLLAMA_CONFIG["findings_max_tokens"])

    with open(SAST_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

    return cfg


def sast_ollama_api_url(base_url, path):
    return sast_normalize_ollama_base_url(base_url) + "/" + path.lstrip("/")


def sast_list_ollama_models(base_url=None, timeout=8):
    cfg = sast_load_ollama_config()
    base_url = sast_normalize_ollama_base_url(base_url or cfg.get("base_url"))

    try:
        resp = requests.get(sast_ollama_api_url(base_url, "/api/tags"), timeout=timeout)
        resp.raise_for_status()
        data = resp.json() or {}
        models = []
        for item in data.get("models", []) or []:
            name = item.get("name") or item.get("model")
            if name:
                models.append(name)
        return sorted(set(models)), None
    except Exception as e:
        return [], str(e)


def sast_resolve_ollama_model(requested_model=None):
    cfg = sast_load_ollama_config()
    model = (requested_model or cfg.get("default_model") or "").strip()

    if model:
        return model

    models, _ = sast_list_ollama_models(cfg.get("base_url"), timeout=5)
    if models:
        return models[0]

    raise RuntimeError(
        "No hay modelo configurado en Ollama. Instale un modelo con 'ollama pull <modelo>' "
        "y selecciónelo en Pruebas SAST > Configuración Ollama."
    )


def sast_test_ollama_connection(base_url=None):
    cfg = sast_load_ollama_config()
    base_url = sast_normalize_ollama_base_url(base_url or cfg.get("base_url"))
    models, err = sast_list_ollama_models(base_url, timeout=8)

    if err:
        return False, f"No fue posible conectar con Ollama en {base_url}. Detalle: {err}", []

    if not models:
        return True, "Conexión exitosa, pero no se encontraron modelos instalados.", []

    return True, f"Conexión exitosa. Modelos disponibles: {len(models)}.", models


def sast_strip_json_fences(raw):
    raw = (raw or "").strip()

    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw).strip()

    if raw and not raw.startswith("{"):
        first = raw.find("{")
        last = raw.rfind("}")
        if first >= 0 and last > first:
            raw = raw[first:last + 1]

    return raw


def sast_call_ollama_json(prompt, model=None, max_tokens=1200, temperature=None, timeout=None):
    cfg = sast_load_ollama_config()
    base_url = cfg.get("base_url")
    model = sast_resolve_ollama_model(model)
    temperature = cfg.get("temperature") if temperature is None else temperature
    timeout = cfg.get("timeout") if timeout is None else timeout

    payload = {
        "model": model,
        "stream": False,
        "format": "json",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Responde únicamente con un objeto JSON válido. "
                    "No incluyas markdown, comentarios ni texto fuera del JSON."
                )
            },
            {"role": "user", "content": prompt},
        ],
        "options": {
            "temperature": float(temperature),
            "num_predict": int(max_tokens),
        }
    }

    try:
        with _sast_ollama_lock:
            resp = requests.post(
                sast_ollama_api_url(base_url, "/api/chat"),
                json=payload,
                timeout=int(timeout)
            )
        resp.raise_for_status()
        data = resp.json() or {}

    except requests.exceptions.ConnectionError as e:
        raise RuntimeError(
            f"No fue posible conectar con Ollama en {base_url}. "
            "Verifique que Ollama esté ejecutándose localmente. Detalle: " + str(e)
        )
    except requests.exceptions.Timeout:
        raise RuntimeError(
            f"Tiempo de espera agotado consultando Ollama en {base_url}. "
            "Aumente el timeout o use un modelo más liviano."
        )
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"Ollama respondió con error HTTP: {e}. Respuesta: {getattr(resp, 'text', '')[:600]}")
    except Exception as e:
        raise RuntimeError(f"Error llamando a Ollama local: {e}")

    content = ((data.get("message") or {}).get("content") or data.get("response") or "").strip()
    if not content:
        raise RuntimeError(f"Ollama no devolvió contenido. Respuesta: {json.dumps(data, ensure_ascii=False)[:800]}")

    return sast_strip_json_fences(content)


def sast_safe_filename(name):
    name = re.sub(r"[^a-zA-Z0-9._-]+", "_", (name or "").strip())
    if not name:
        name = "archivo.txt"
    return name[:140]


def sast_ext_ok(filename):
    _, ext = os.path.splitext((filename or "").lower())
    return ext in SAST_ALLOWED_EXT


def sast_read_text_file(path, max_bytes=2_000_000):
    with open(path, "rb") as f:
        data = f.read(max_bytes)

    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1", errors="replace")


def sast_detect_language_from_filename(filename):
    ext = os.path.splitext((filename or "").lower())[1]
    return {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".java": "java",
        ".cs": "csharp",
        ".go": "go",
        ".php": "php",
        ".rb": "ruby",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "c/cpp",
        ".html": "html",
        ".css": "css",
        ".sql": "sql",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".json": "json",
        ".xml": "xml",
        ".md": "markdown",
        ".txt": "text",
        ".sh": "shell",
    }.get(ext, "unknown")


def sast_trim_code_for_ai(code, max_chars=SAST_MAX_CODE_CHARS):
    if not code:
        return ""

    if len(code) <= max_chars:
        return code

    head = code[: max_chars // 2]
    tail = code[-max_chars // 2:]
    return head + "\n\n/* --- CÓDIGO RECORTADO PARA ANÁLISIS IA --- */\n\n" + tail


def sast_escape_pdf(value):
    if value is None:
        return ""
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\t", "    ")
    )


def sast_severity_color(sev):
    sev = (sev or "").strip().lower()
    if sev in ("crítico", "critico"):
        return colors.HexColor("#7A0019")
    if sev == "alto":
        return colors.HexColor("#B71C1C")
    if sev == "medio":
        return colors.HexColor("#E65100")
    if sev == "bajo":
        return colors.HexColor("#1B5E20")
    return colors.black


def sast_loads_json_object(raw, where=""):
    raw = sast_strip_json_fences(raw)

    if not raw:
        raise RuntimeError(f"{where}: respuesta vacía del modelo.")

    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"{where}: JSON inválido. Error: {e}. Respuesta: {raw[:900]}")

    if not isinstance(obj, dict):
        raise RuntimeError(f"{where}: se esperaba un objeto JSON y llegó {type(obj).__name__}")

    return obj


def sast_build_prompt_summary(code_text, artifact_type, language, filename):
    return f"""
Eres un analista senior de AppSec. Realiza un análisis SAST asistido sobre el código provisto.
Basado en OWASP Top 10, CERT Secure Coding y SANS Top 25 / CWE.

Devuelve ÚNICAMENTE un JSON válido, sin texto adicional.

OBJETIVO:
Genera un resumen ejecutivo, alcance, métricas y conclusiones. No generes todavía la lista completa de findings.

REGLAS:
- No devuelvas null.
- Usa español profesional.
- Si no hay evidencia suficiente, indícalo como limitación.
- El puntaje debe estar entre 0 y 100.

ESQUEMA:
{{
  "executive_summary": {{
    "overall_risk_level": "Bajo|Medio|Alto|Crítico",
    "overall_risk_score": 0,
    "key_risks": ["..."],
    "management_overview": "..."
  }},
  "scope_context": {{
    "artifact_type": "{artifact_type}",
    "language": "{language}",
    "files_analyzed": ["{filename}"],
    "sast_notes": "Análisis estático asistido por IA local con Ollama."
  }},
  "metrics": {{
    "total_findings": 0,
    "by_severity": {{"Crítico":0,"Alto":0,"Medio":0,"Bajo":0}},
    "by_category": {{}},
    "top_cwe": ["CWE-..."],
    "compliance_snapshot": {{
      "owasp_alignment": "Bajo|Medio|Alto",
      "cert_alignment": "Bajo|Medio|Alto",
      "sans_top25_alignment": "Bajo|Medio|Alto"
    }}
  }},
  "conclusions": {{
    "summary": "...",
    "next_steps": ["..."]
  }}
}}

CONTEXTO:
- Tipo de artefacto: {artifact_type}
- Lenguaje: {language}
- Archivo: {filename}

CÓDIGO:
\"\"\"
{code_text}
\"\"\"
""".strip()


def sast_build_prompt_findings(code_text, artifact_type, language, filename, summary_json):
    ex = summary_json.get("executive_summary", {}) or {}
    risk_level = ex.get("overall_risk_level", "N/A")
    risk_score = ex.get("overall_risk_score", "N/A")

    return f"""
Eres un analista senior de AppSec. Genera SOLO la lista de hallazgos SAST en JSON válido.
Basado en OWASP Top 10, CERT Secure Coding y SANS Top 25 / CWE.

Devuelve ÚNICAMENTE:
{{ "findings": [ ... ] }}

REGLAS:
- Máximo 20 hallazgos, priorizando severidad y explotabilidad.
- Usa español profesional.
- No inventes CVE; usa "N/A" si no hay una dependencia/version concreta.
- Para inyección SQL usa CWE-89 si aplica.
- Para XSS usa CWE-79 si aplica.
- Para command injection usa CWE-78 si aplica.
- Si no puedes determinar línea exacta, usa line_start=1 y line_end=1 e indícalo en remediation_notes.
- evidence_snippet y secure_code_example deben ser cortos.

CONTEXTO:
- Riesgo general del paso 1: {risk_level}
- Puntaje general del paso 1: {risk_score}
- Tipo de artefacto: {artifact_type}
- Lenguaje: {language}
- Archivo: {filename}

ESQUEMA:
{{
  "findings": [
    {{
      "id": "F-001",
      "title": "...",
      "category": "Injection|XSS|Auth|Crypto|Secrets|AccessControl|InputValidation|MemorySafety|Dependency|Logging|Other",
      "description": "...",
      "location": {{
        "file": "{filename}",
        "line_start": 1,
        "line_end": 1
      }},
      "evidence_snippet": "...",
      "cwe": "CWE-xxx",
      "cve": "CVE-YYYY-NNNN o N/A",
      "cvss_score": 0.0,
      "severity": "Bajo|Medio|Alto|Crítico",
      "risk_rationale": {{
        "impact": "Bajo|Medio|Alto",
        "likelihood": "Bajo|Medio|Alto",
        "notes": "..."
      }},
      "remediation": {{
        "recommendation": "...",
        "secure_code_example": "...",
        "remediation_notes": "..."
      }},
      "references": ["OWASP ...", "CERT ...", "SANS/CWE ..."]
    }}
  ]
}}

CÓDIGO:
\"\"\"
{code_text}
\"\"\"
""".strip()


def sast_analyze_code_with_ai(code_text, artifact_type, language, filename, model=None):
    cfg = sast_load_ollama_config()
    safe_code = sast_trim_code_for_ai(code_text)

    prompt1 = sast_build_prompt_summary(safe_code, artifact_type, language, filename)
    raw1 = sast_call_ollama_json(
        prompt1,
        model=model,
        max_tokens=cfg.get("summary_max_tokens", 1100),
        temperature=cfg.get("temperature", 0.2),
        timeout=cfg.get("timeout", 240)
    )
    data1 = sast_loads_json_object(raw1, where="Paso 1 SAST")

    prompt2 = sast_build_prompt_findings(safe_code, artifact_type, language, filename, data1)
    raw2 = sast_call_ollama_json(
        prompt2,
        model=model,
        max_tokens=cfg.get("findings_max_tokens", 4000),
        temperature=cfg.get("temperature", 0.2),
        timeout=cfg.get("timeout", 240)
    )
    data2 = sast_loads_json_object(raw2, where="Paso 2 SAST")

    findings = data2.get("findings", []) or []
    if not isinstance(findings, list):
        findings = []

    final = {
        "executive_summary": data1.get("executive_summary", {}) or {},
        "scope_context": data1.get("scope_context", {}) or {},
        "findings": findings,
        "metrics": data1.get("metrics", {}) or {},
        "conclusions": data1.get("conclusions", {}) or {},
    }

    if not isinstance(final["metrics"], dict):
        final["metrics"] = {}

    final["metrics"]["total_findings"] = len(findings)

    by_sev = {"Crítico": 0, "Alto": 0, "Medio": 0, "Bajo": 0}
    by_cat = {}
    top_cwe = []

    for f in findings:
        if not isinstance(f, dict):
            continue
        sev = (f.get("severity") or "Bajo").strip()
        if sev == "Critico":
            sev = "Crítico"
        if sev not in by_sev:
            by_sev[sev] = 0
        by_sev[sev] += 1

        cat = (f.get("category") or "Other").strip()
        by_cat[cat] = by_cat.get(cat, 0) + 1

        cwe = (f.get("cwe") or "").strip()
        if cwe and cwe.upper() != "N/A":
            top_cwe.append(cwe)

    final["metrics"]["by_severity"] = by_sev
    final["metrics"]["by_category"] = by_cat
    final["metrics"]["top_cwe"] = list(dict.fromkeys(top_cwe))[:10]

    return final


def sast_bool_form(value):
    return str(value or "").strip().lower() in ("1", "true", "on", "yes", "si", "sí")


def sast_text_limit(value, limit=500):
    value = (value or "").strip()
    if len(value) > limit:
        return value[: limit - 3].rstrip() + "..."
    return value


def sast_severity_to_clasificacion(severity):
    sev = (severity or "").strip().lower()
    if sev in ("crítico", "critico", "critical"):
        return "Crítica"
    if sev in ("alto", "alta", "high"):
        return "Alta"
    if sev in ("medio", "media", "medium"):
        return "Media"
    if sev in ("bajo", "baja", "low"):
        return "Baja"
    return "Media"


def sast_severity_to_priority(severity):
    return sast_severity_to_clasificacion(severity)


def sast_priority_due_date(prioridad):
    prioridad = (prioridad or "").strip().lower()
    if prioridad in ("crítica", "critica"):
        days = 15
    elif prioridad == "alta":
        days = 30
    elif prioridad == "media":
        days = 60
    else:
        days = 90
    try:
        return datetime.now().date() + timedelta(days=days)
    except Exception:
        return None


def sast_finding_location_text(finding):
    loc = finding.get("location", {}) or {}
    file_ = loc.get("file") or ""
    ls = loc.get("line_start") or ""
    le = loc.get("line_end") or ""
    if file_ or ls or le:
        return f"{file_}:{ls}-{le}".strip(":-")
    return "N/A"


def sast_finding_to_vulnerability_description(finding, meta):
    rem = finding.get("remediation", {}) or {}
    rr = finding.get("risk_rationale", {}) or {}
    parts = [
        f"Hallazgo SAST: {finding.get('title', 'Sin título')}",
        f"Descripción: {finding.get('description', 'N/A')}",
        f"Categoría: {finding.get('category', 'N/A')}",
        f"CWE: {finding.get('cwe', 'N/A')} | CVE: {finding.get('cve', 'N/A')} | CVSS: {finding.get('cvss_score', 'N/A')}",
        f"Ubicación: {sast_finding_location_text(finding)}",
        f"Impacto: {rr.get('impact', 'N/A')} | Probabilidad: {rr.get('likelihood', 'N/A')}",
        f"Evidencia: {finding.get('evidence_snippet', 'N/A')}",
        f"Recomendación / acción correctiva: {rem.get('recommendation', 'N/A')}",
        f"Origen: Pruebas SAST con Ollama local. Proyecto: {meta.get('project_name', 'N/A')} | Archivo: {meta.get('filename', 'N/A')} | Modelo: {meta.get('model', 'N/A')}",
    ]
    return "\n".join([str(p) for p in parts if p])


def sast_finding_to_hallazgo_for_remediation(finding, meta):
    loc = finding.get("location", {}) or {}
    rem = finding.get("remediation", {}) or {}
    return {
        "titulo": finding.get("title") or "Hallazgo SAST",
        "descripcion": finding.get("description") or "",
        "fuente": "Pruebas SAST con Ollama local",
        "severidad": sast_severity_to_clasificacion(finding.get("severity")),
        "cve": "" if (finding.get("cve") or "").strip().upper() == "N/A" else (finding.get("cve") or ""),
        "cvss": str(finding.get("cvss_score") or ""),
        "puerto": "",
        "servicio": meta.get("artifact_type") or "",
        "evidencia": f"{finding.get('evidence_snippet','')} | Ubicación: {loc.get('file','')}:{loc.get('line_start','')}",
        "recomendacion_base": rem.get("recommendation") or "",
    }


def sast_build_congruent_corrective_action(hallazgo):
    """
    Construye una acción correctiva que pueda usarse tanto en el informe SAST como en
    el Plan de Remediación. Así se evita que el PDF muestre una recomendación técnica
    y la matriz de remediación registre una acción genérica distinta.
    """
    titulo = (hallazgo.get("titulo") or "hallazgo detectado").strip()
    recomendacion_base = (hallazgo.get("recomendacion_base") or "").strip()

    if recomendacion_base:
        return (
            f"Validar técnicamente el hallazgo '{titulo}', confirmar su impacto real y aplicar la corrección específica: "
            f"{recomendacion_base} Posteriormente, ejecutar pruebas de regresión, repetir el análisis SAST, validar que el hallazgo no se reproduzca "
            "y documentar evidencia técnica de cierre."
        )

    return (
        f"Validar técnicamente el hallazgo '{titulo}', identificar y corregir la causa raíz en el código, dependencias o configuración afectada, "
        "aplicar controles seguros, ejecutar pruebas de regresión, repetir el análisis SAST y documentar evidencia técnica de cierre."
    )


def sast_generic_remediation(hallazgo):
    severidad = (hallazgo.get("severidad") or "").strip()
    prioridad = sast_severity_to_priority(severidad)

    try:
        data = _fallback_remediacion_segura(hallazgo)
        if not isinstance(data, dict):
            raise RuntimeError("Fallback de remediación no devolvió dict.")

        # Garantiza congruencia con la recomendación técnica del informe SAST.
        data["accion_correctiva"] = sast_build_congruent_corrective_action(hallazgo)
        data["prioridad"] = data.get("prioridad") or prioridad
        data["recursos_necesarios"] = data.get("recursos_necesarios") or (
            "Equipo de desarrollo responsable, apoyo de seguridad de aplicaciones, ambiente de pruebas, "
            "repositorio de código, herramienta SAST y evidencia técnica de validación."
        )
        return data
    except Exception:
        return {
            "accion_correctiva": sast_build_congruent_corrective_action(hallazgo),
            "prioridad": prioridad,
            "recursos_necesarios": (
                "Equipo de desarrollo responsable, apoyo de seguridad de aplicaciones, ambiente de pruebas, "
                "repositorio de código, herramienta SAST y evidencia técnica de validación."
            )
        }


def sast_apply_remediation_data_to_finding(finding, rem_data, plan_id=None):
    """
    Sincroniza la recomendación visible en el informe SAST con la acción correctiva
    realmente registrada en Plan de Remediación.
    """
    if not isinstance(finding, dict):
        return finding

    if not isinstance(rem_data, dict):
        rem_data = {}

    rem = finding.get("remediation")
    if not isinstance(rem, dict):
        rem = {}
        finding["remediation"] = rem

    accion = (rem_data.get("accion_correctiva") or rem.get("recommendation") or "").strip()
    recursos = (rem_data.get("recursos_necesarios") or "").strip()
    origen = (rem_data.get("origen") or "genérica").strip()

    original_recommendation = (rem.get("recommendation") or "").strip()
    if original_recommendation and original_recommendation != accion:
        rem.setdefault("original_recommendation", original_recommendation)

    if accion:
        rem["recommendation"] = accion
        rem["corrective_action"] = accion
        finding["sgsi_remediation_action"] = accion

    if recursos:
        rem["resources_required"] = recursos
        finding["sgsi_remediation_resources"] = recursos

    rem["remediation_source"] = origen
    finding["sgsi_remediation_source"] = origen

    if plan_id is not None:
        rem["plan_remediacion_id"] = plan_id
        finding["sgsi_plan_remediacion_id"] = plan_id

    notes = (rem.get("remediation_notes") or "").strip()
    congruence_note = "La recomendación del informe corresponde a la acción correctiva registrada en el Plan de Remediación."
    if notes:
        if congruence_note not in notes:
            rem["remediation_notes"] = notes + " " + congruence_note
    else:
        rem["remediation_notes"] = congruence_note

    return finding


def sast_generate_remediation_data(finding, meta, use_ai=True):
    hallazgo = sast_finding_to_hallazgo_for_remediation(finding, meta)

    if not use_ai:
        data = sast_generic_remediation(hallazgo)
        data["origen"] = "genérica"
        return data

    try:
        data = sugerir_remediacion_ai(hallazgo)
        if not isinstance(data, dict):
            raise RuntimeError("La sugerencia IA no devolvió un objeto válido.")
        data.setdefault("accion_correctiva", "")
        data.setdefault("prioridad", sast_severity_to_priority(finding.get("severity")))
        data.setdefault("recursos_necesarios", "")
        data["origen"] = "IA/fallback"
        if not data.get("accion_correctiva"):
            raise RuntimeError("La sugerencia IA no incluyó acción correctiva.")

        # Si la IA responde demasiado genérica, reforzamos con la recomendación técnica del SAST.
        base = (hallazgo.get("recomendacion_base") or "").strip()
        accion = (data.get("accion_correctiva") or "").strip()
        if base and base.lower() not in accion.lower():
            data["accion_correctiva"] = (
                f"{accion} Recomendación técnica específica del análisis SAST: {base}"
            ).strip()

        return data
    except Exception:
        data = sast_generic_remediation(hallazgo)
        data["origen"] = "genérica"
        return data


def sast_register_findings_in_sgsi(analysis, meta, payload):
    """
    Registra automáticamente hallazgos SAST en:
    - Matriz de Vulnerabilidades
    - Plan de Remediación

    Si se solicita crear plan de remediación, se registra la vulnerabilidad aunque el switch de
    vulnerabilidades no venga activo, porque el plan requiere FK obligatoria a vulnerabilidades_registro.
    """
    findings = analysis.get("findings", []) or []
    register_vulns = bool(payload.get("register_vulnerabilities"))
    create_plans = bool(payload.get("create_remediation_plans"))
    use_ai_remediation = bool(payload.get("generate_ai_remediation"))

    if create_plans:
        register_vulns = True

    summary = {
        "requested_register_vulnerabilities": register_vulns,
        "requested_create_remediation_plans": create_plans,
        "requested_ai_remediation": use_ai_remediation,
        "vulnerabilities_created": 0,
        "remediation_plans_created": 0,
        "vulnerability_ids": [],
        "plan_ids": [],
        "error": "",
    }

    if not findings or not register_vulns:
        return summary

    responsable = (
        payload.get("responsable")
        or payload.get("username")
        or "Seguridad de la Información"
    )

    report_id = (payload.get("report_id") or uuid.uuid4().hex[:12]).upper()
    project_name = meta.get("project_name") or "Proyecto SAST"
    filename = meta.get("filename") or "archivo"
    activo_base = f"{project_name} · {filename}".strip(" ·")
    activo_base = activo_base[:200]

    try:
        for idx, finding in enumerate(findings, start=1):
            if not isinstance(finding, dict):
                continue

            codigo = f"SAST-{report_id}-{idx:03d}"[:50]
            severity = finding.get("severity") or "Media"
            clasificacion = sast_severity_to_clasificacion(severity)
            cve = (finding.get("cve") or "").strip()
            if cve.upper() == "N/A":
                cve = ""

            cvss = str(finding.get("cvss_score") or "").strip()

            # Si se creará Plan de Remediación, se genera primero la acción correctiva
            # y se sincroniza con el hallazgo antes de armar la descripción de la vulnerabilidad.
            # Así el informe, el JSON, la matriz de vulnerabilidades y el plan quedan congruentes.
            rem_data = None
            if create_plans:
                rem_data = sast_generate_remediation_data(finding, meta, use_ai=use_ai_remediation)
                accion_sync = (rem_data.get("accion_correctiva") or "").strip()
                if not accion_sync:
                    accion_sync = sast_generic_remediation(sast_finding_to_hallazgo_for_remediation(finding, meta))["accion_correctiva"]
                    rem_data["accion_correctiva"] = accion_sync
                sast_apply_remediation_data_to_finding(finding, rem_data)

            descripcion = sast_finding_to_vulnerability_description(finding, meta)

            vuln = VulnerabilidadRegistro(
                codigo=codigo,
                activo=activo_base,
                descripcion_vulnerabilidad=descripcion,
                cve=cve,
                cvss=cvss,
                clasificacion=clasificacion,
                fecha_identificacion=datetime.now().date(),
                fecha_cierre=None,
                estado="Abierto",
                responsable=responsable,
                riesgo_residual=(
                    f"Riesgo residual inicial estimado por SAST: {clasificacion}. "
                    f"CVSS: {cvss or 'N/A'}. Requiere validación técnica y seguimiento."
                )
            )
            db.session.add(vuln)
            db.session.flush()

            summary["vulnerabilities_created"] += 1
            summary["vulnerability_ids"].append(vuln.id)

            if create_plans:
                if rem_data is None:
                    rem_data = sast_generate_remediation_data(finding, meta, use_ai=use_ai_remediation)

                accion_plan = (rem_data.get("accion_correctiva") or "").strip()
                if not accion_plan:
                    accion_plan = sast_generic_remediation(sast_finding_to_hallazgo_for_remediation(finding, meta))["accion_correctiva"]
                    rem_data["accion_correctiva"] = accion_plan

                # Se vuelve a sincronizar justo antes de crear el plan para garantizar que
                # el texto del informe sea exactamente el mismo texto de acción correctiva.
                sast_apply_remediation_data_to_finding(finding, rem_data)

                prioridad = (rem_data.get("prioridad") or clasificacion or "Media").strip()
                if prioridad == "Critica":
                    prioridad = "Crítica"
                if prioridad not in ("Crítica", "Alta", "Media", "Baja"):
                    prioridad = clasificacion if clasificacion in ("Crítica", "Alta", "Media", "Baja") else "Media"

                plan = PlanRemediacion(
                    vulnerabilidad_id=vuln.id,
                    accion_correctiva=accion_plan,
                    responsable=responsable,
                    prioridad=prioridad,
                    fecha_objetivo=sast_priority_due_date(prioridad),
                    fecha_remediacion=None,
                    recursos_necesarios=rem_data.get("recursos_necesarios") or "Equipo técnico responsable, AppSec y evidencia de cierre.",
                    estado="Abierto"
                )
                db.session.add(plan)
                db.session.flush()

                # Guarda el ID del plan también dentro del JSON del informe SAST.
                sast_apply_remediation_data_to_finding(finding, rem_data, plan_id=plan.id)

                summary["remediation_plans_created"] += 1
                summary["plan_ids"].append(plan.id)

        db.session.commit()

        try:
            registrar_log(
                responsable,
                (
                    f"Pruebas SAST registró {summary['vulnerabilities_created']} vulnerabilidad(es) "
                    f"y {summary['remediation_plans_created']} plan(es) de remediación. Reporte: {report_id}"
                )
            )
        except Exception:
            pass

    except Exception as e:
        db.session.rollback()
        summary["error"] = str(e)

    return summary


def sast_build_pdf(report_path, analysis, meta):
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SAST_H1", fontSize=16, leading=19, spaceAfter=10))
    styles.add(ParagraphStyle(name="SAST_H2", fontSize=13, leading=16, spaceAfter=8))
    styles.add(ParagraphStyle(name="SAST_Body", fontSize=10.5, leading=13.5))
    styles.add(ParagraphStyle(name="SAST_Small", fontSize=9, leading=11))
    styles.add(ParagraphStyle(name="SAST_Mono", fontName="Courier", fontSize=8.2, leading=10.2))

    doc = SimpleDocTemplate(
        report_path,
        pagesize=letter,
        leftMargin=0.72 * inch,
        rightMargin=0.72 * inch,
        topMargin=0.72 * inch,
        bottomMargin=0.72 * inch,
        title="Informe de Pruebas SAST",
    )

    story = []

    story.append(Paragraph("Informe de Pruebas SAST con IA Local", styles["SAST_H1"]))
    story.append(Paragraph(f"<b>Proyecto:</b> {sast_escape_pdf(meta.get('project_name'))}", styles["SAST_Body"]))
    story.append(Paragraph(f"<b>Tipo de artefacto:</b> {sast_escape_pdf(meta.get('artifact_type'))}", styles["SAST_Body"]))
    story.append(Paragraph(f"<b>Archivo:</b> {sast_escape_pdf(meta.get('filename'))}", styles["SAST_Body"]))
    story.append(Paragraph(f"<b>Lenguaje:</b> {sast_escape_pdf(meta.get('language'))}", styles["SAST_Body"]))
    story.append(Paragraph(f"<b>Motor:</b> Ollama local · {sast_escape_pdf(meta.get('model'))}", styles["SAST_Body"]))
    story.append(Paragraph(f"<b>Fecha:</b> {sast_escape_pdf(meta.get('date_str'))}", styles["SAST_Body"]))
    story.append(Spacer(1, 12))

    ex = analysis.get("executive_summary", {}) or {}
    story.append(Paragraph("1. Resumen Ejecutivo", styles["SAST_H2"]))
    story.append(Paragraph(f"<b>Nivel de riesgo general:</b> {sast_escape_pdf(ex.get('overall_risk_level','N/A'))}", styles["SAST_Body"]))
    story.append(Paragraph(f"<b>Puntaje global:</b> {sast_escape_pdf(ex.get('overall_risk_score','N/A'))}/100", styles["SAST_Body"]))

    if ex.get("management_overview"):
        story.append(Paragraph(f"<b>Visión para dirección:</b> {sast_escape_pdf(ex.get('management_overview'))}", styles["SAST_Body"]))

    key_risks = ex.get("key_risks", []) or []
    if key_risks:
        story.append(Spacer(1, 5))
        story.append(Paragraph("<b>Riesgos clave:</b><br/>" + "<br/>".join([f"• {sast_escape_pdf(x)}" for x in key_risks[:10]]), styles["SAST_Body"]))

    story.append(Spacer(1, 10))

    metrics = analysis.get("metrics", {}) or {}
    by_sev = metrics.get("by_severity", {}) or {}
    compliance = metrics.get("compliance_snapshot", {}) or {}
    story.append(Paragraph("2. Métricas", styles["SAST_H2"]))
    story.append(Paragraph(f"<b>Total de hallazgos:</b> {sast_escape_pdf(metrics.get('total_findings', 0))}", styles["SAST_Body"]))
    story.append(Paragraph(
        "<b>Distribución por severidad:</b> " +
        f"Crítico: {by_sev.get('Crítico',0)} | Alto: {by_sev.get('Alto',0)} | Medio: {by_sev.get('Medio',0)} | Bajo: {by_sev.get('Bajo',0)}",
        styles["SAST_Body"]
    ))
    story.append(Paragraph(
        "<b>Alineación:</b> " +
        f"OWASP={sast_escape_pdf(compliance.get('owasp_alignment','N/A'))}, " +
        f"CERT={sast_escape_pdf(compliance.get('cert_alignment','N/A'))}, " +
        f"SANS Top 25={sast_escape_pdf(compliance.get('sans_top25_alignment','N/A'))}",
        styles["SAST_Body"]
    ))
    story.append(Spacer(1, 10))

    findings = analysis.get("findings", []) or []
    story.append(Paragraph("3. Hallazgos", styles["SAST_H2"]))

    if not findings:
        story.append(Paragraph("No se identificaron hallazgos en el código analizado.", styles["SAST_Body"]))
    else:
        table_data = [["ID", "Título", "Severidad", "CVSS", "CWE", "CVE", "Ubicación"]]
        for f in findings[:200]:
            loc = f.get("location", {}) or {}
            table_data.append([
                str(f.get("id", "N/A")),
                (f.get("title", "") or "")[:60],
                str(f.get("severity", "N/A")),
                str(f.get("cvss_score", "N/A")),
                str(f.get("cwe", "N/A")),
                str(f.get("cve", "N/A")),
                f"{loc.get('file', meta.get('filename'))}:{loc.get('line_start','N/A')}",
            ])

        tbl = Table(
            table_data,
            colWidths=[0.55*inch, 2.15*inch, 0.78*inch, 0.55*inch, 0.72*inch, 1.02*inch, 1.25*inch]
        )
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1459A6")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
            ("FONTSIZE", (0,0), (-1,0), 8.2),
            ("FONTSIZE", (0,1), (-1,-1), 7.8),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
        ]))
        story.append(tbl)
        story.append(PageBreak())

        for f in findings[:200]:
            loc = f.get("location", {}) or {}
            story.append(Paragraph(f"{sast_escape_pdf(f.get('id','N/A'))} – {sast_escape_pdf(f.get('title','Sin título'))}", styles["SAST_H2"]))
            story.append(Paragraph(
                f"<b>Severidad:</b> {sast_escape_pdf(f.get('severity','N/A'))} | "
                f"<b>CVSS:</b> {sast_escape_pdf(f.get('cvss_score','N/A'))} | "
                f"<b>CWE:</b> {sast_escape_pdf(f.get('cwe','N/A'))} | "
                f"<b>CVE:</b> {sast_escape_pdf(f.get('cve','N/A'))}",
                styles["SAST_Body"]
            ))
            story.append(Paragraph(
                f"<b>Ubicación:</b> {sast_escape_pdf(loc.get('file', meta.get('filename')))} "
                f"líneas {sast_escape_pdf(loc.get('line_start','N/A'))}–{sast_escape_pdf(loc.get('line_end','N/A'))}",
                styles["SAST_Body"]
            ))
            if f.get("description"):
                story.append(Paragraph(f"<b>Descripción:</b> {sast_escape_pdf(f.get('description'))}", styles["SAST_Body"]))

            rr = f.get("risk_rationale", {}) or {}
            if rr:
                story.append(Paragraph(
                    f"<b>Racional de riesgo:</b> Impacto={sast_escape_pdf(rr.get('impact','N/A'))}, "
                    f"Probabilidad={sast_escape_pdf(rr.get('likelihood','N/A'))}. "
                    f"{sast_escape_pdf(rr.get('notes',''))}",
                    styles["SAST_Body"]
                ))

            if f.get("evidence_snippet"):
                story.append(Spacer(1, 4))
                story.append(Paragraph("<b>Evidencia:</b>", styles["SAST_Body"]))
                story.append(Paragraph(f"<font name='Courier'>{sast_escape_pdf(f.get('evidence_snippet'))}</font>", styles["SAST_Mono"]))

            rem = f.get("remediation", {}) or {}
            if rem.get("recommendation"):
                story.append(Spacer(1, 4))
                story.append(Paragraph(f"<b>Recomendación / acción correctiva:</b> {sast_escape_pdf(rem.get('recommendation'))}", styles["SAST_Body"]))
            if rem.get("secure_code_example"):
                story.append(Paragraph("<b>Ejemplo seguro:</b>", styles["SAST_Body"]))
                story.append(Paragraph(f"<font name='Courier'>{sast_escape_pdf(rem.get('secure_code_example'))}</font>", styles["SAST_Mono"]))
            if rem.get("remediation_notes"):
                story.append(Paragraph(f"<b>Notas:</b> {sast_escape_pdf(rem.get('remediation_notes'))}", styles["SAST_Small"]))

            refs = f.get("references", []) or []
            if refs:
                story.append(Paragraph("<b>Referencias:</b> " + "; ".join([sast_escape_pdf(x) for x in refs[:8]]), styles["SAST_Small"]))

            story.append(Spacer(1, 12))

    concl = analysis.get("conclusions", {}) or {}
    story.append(Paragraph("4. Conclusiones", styles["SAST_H2"]))
    story.append(Paragraph(sast_escape_pdf(concl.get("summary", "N/A")), styles["SAST_Body"]))

    next_steps = concl.get("next_steps", []) or []
    if next_steps:
        story.append(Paragraph("<b>Próximos pasos:</b><br/>" + "<br/>".join([f"• {sast_escape_pdf(x)}" for x in next_steps[:12]]), styles["SAST_Body"]))

    doc.build(story)


def sast_job_update(job_id, percent, message, status="running"):
    job = SAST_JOBS.get(job_id)
    if not job:
        return
    job["percent"] = int(percent)
    job["message"] = message
    job["status"] = status


def sast_run_analysis_job(job_id, payload):
    with _sast_job_sem:
        with app.app_context():
            try:
                sast_job_update(job_id, 5, "Preparando entrada…")

                project_name = payload["project_name"]
                artifact_type = payload["artifact_type"]
                filename = payload["filename"]
                language = payload["language"]
                code_text = payload["code_text"]
                model = payload["model"]

                report_id = payload["report_id"]
                date_str = payload["date_str"]

                meta = {
                    "project_name": project_name,
                    "artifact_type": artifact_type,
                    "filename": filename,
                    "language": language,
                    "date_str": date_str,
                    "model": model,
                }

                sast_job_update(job_id, 20, f"Ejecutando análisis SAST con Ollama ({model})…")

                analysis = sast_analyze_code_with_ai(code_text, artifact_type, language, filename, model=model)
                if not isinstance(analysis, dict):
                    raise RuntimeError("El análisis no devolvió un objeto válido.")

                registration_summary = {
                    "requested_register_vulnerabilities": bool(payload.get("register_vulnerabilities")),
                    "requested_create_remediation_plans": bool(payload.get("create_remediation_plans")),
                    "requested_ai_remediation": bool(payload.get("generate_ai_remediation")),
                    "vulnerabilities_created": 0,
                    "remediation_plans_created": 0,
                    "vulnerability_ids": [],
                    "plan_ids": [],
                    "error": "",
                }

                if payload.get("register_vulnerabilities") or payload.get("create_remediation_plans"):
                    if payload.get("create_remediation_plans") and payload.get("generate_ai_remediation"):
                        sast_job_update(job_id, 60, "Registrando vulnerabilidades y generando remediaciones con IA…")
                    elif payload.get("create_remediation_plans"):
                        sast_job_update(job_id, 60, "Registrando vulnerabilidades y creando planes con texto genérico…")
                    else:
                        sast_job_update(job_id, 60, "Registrando hallazgos en la matriz de vulnerabilidades…")

                    registration_summary = sast_register_findings_in_sgsi(analysis, meta, payload)

                analysis["sgsi_registration"] = registration_summary

                if registration_summary.get("error"):
                    sast_job_update(job_id, 72, "Generando PDF… El registro SGSI presentó advertencia.")
                else:
                    sast_job_update(job_id, 72, "Generando PDF…")

                pdf_name = f"Informe_SAST_{report_id}.pdf"
                pdf_path = os.path.join(SAST_REPORT_DIR, pdf_name)

                sast_build_pdf(pdf_path, analysis, meta)

                sast_job_update(job_id, 88, "Guardando JSON…")

                json_name = f"analysis_{report_id}.json"
                json_path = os.path.join(SAST_REPORT_DIR, json_name)

                analysis["sast_meta"] = meta
                analysis["sast_report"] = {
                    "report_id": report_id,
                    "pdf_name": pdf_name,
                    "json_name": json_name,
                }

                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(analysis, f, ensure_ascii=False, indent=2)

                history_record = sast_build_scan_history_record(
                    report_id,
                    analysis,
                    meta,
                    pdf_name,
                    json_name,
                    registration_summary,
                    payload
                )
                sast_save_scan_history_record(history_record)

                SAST_JOBS[job_id]["result"] = {
                    "analysis": analysis,
                    "pdf_name": pdf_name,
                    "json_name": json_name,
                    "meta": meta,
                    "registration_summary": registration_summary,
                    "history_record": history_record,
                }

                sast_job_update(job_id, 100, "Listo ✅", status="done")
                SAST_JOBS[job_id]["done"] = True

            except Exception as e:
                try:
                    db.session.rollback()
                except Exception:
                    pass
                SAST_JOBS[job_id]["error"] = str(e)
                SAST_JOBS[job_id]["done"] = True
                sast_job_update(job_id, 100, "Error en análisis SAST", status="error")


SAST_INDEX_HTML = """
<div class="sast-shell">

  <div class="sast-hero">
    <div class="sast-hero-icon">🧪</div>
    <div>
      <div class="sast-badge">SGSI · Gestión de Eventos · Pruebas SAST</div>
      <h2 class="sast-title">Pruebas SAST con IA Local</h2>
      <div class="sast-subtitle">
        Revisión de seguridad de código fuente con Ollama local, orientada a OWASP, CERT Secure Coding y SANS Top 25.
      </div>
    </div>
  </div>

  <div class="sast-actions">
    <a href="{{ url_for('vulnerabilidades_matriz') }}" class="btn btn-light rounded-pill px-4 fw-bold">
      ⬅ Volver a Vulnerabilidades
    </a>

    <div class="dropdown">
      <button class="btn btn-primary rounded-pill px-4 fw-bold dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false">
        Ejecución de pruebas
      </button>
      <ul class="dropdown-menu shadow-sm rounded-4">
        <li>
          <a class="dropdown-item fw-semibold" href="{{ url_for('sast_index') }}">
            🧪 Nueva prueba SAST
          </a>
        </li>
        <li>
          <a class="dropdown-item fw-semibold" href="{{ url_for('sast_reports') }}">
            📊 Ver informes
          </a>
        </li>
        <li><hr class="dropdown-divider"></li>
        <li>
          <a class="dropdown-item fw-semibold" href="{{ url_for('sast_config') }}">
            ⚙️ Configuración Ollama
          </a>
        </li>
      </ul>
    </div>
  </div>

  <div class="sast-card">
    <div class="sast-card-body">

      <div class="sast-status-grid mb-3">
        <div class="sast-status-box">
          <div class="sast-status-label">URL Ollama</div>
          <div class="sast-status-value">{{ cfg.base_url }}</div>
        </div>
        <div class="sast-status-box">
          <div class="sast-status-label">Modelo por defecto</div>
          <div class="sast-status-value">{{ cfg.default_model or 'No configurado' }}</div>
        </div>
        <div class="sast-status-box">
          <div class="sast-status-label">Estado</div>
          <div class="sast-status-value {{ 'text-success' if conn_ok else 'text-danger' }}">
            {{ conn_msg }}
          </div>
        </div>
      </div>

      {% if read_only %}
        <div class="alert alert-warning rounded-4">
          El rol Auditor puede consultar el módulo, pero no puede ejecutar nuevos análisis.
        </div>
      {% endif %}

      <form id="sastAnalyzeForm" method="POST" action="{{ url_for('sast_start') }}" enctype="multipart/form-data" data-no-progress="true">
        <div class="row g-3">
          <div class="col-md-6">
            <label class="form-label">Nombre del proyecto</label>
            <input class="form-control" name="project_name" placeholder="Ej: API Clientes v2">
          </div>

          <div class="col-md-3">
            <label class="form-label">Tipo de artefacto</label>
            <select class="form-select" name="artifact_type" id="sastArtifactType" required>
              <option>API</option>
              <option>Librería</option>
              <option>Script</option>
              <option>Parte de Código</option>
              <option selected>Programa completo</option>
            </select>
          </div>

          <div class="col-md-3">
            <label class="form-label">Lenguaje</label>
            <select class="form-select" name="language">
              <option value="">Auto / No especificar</option>
              <option>python</option>
              <option>javascript</option>
              <option>typescript</option>
              <option>java</option>
              <option>csharp</option>
              <option>go</option>
              <option>php</option>
              <option>ruby</option>
              <option>c</option>
              <option>cpp</option>
              <option>sql</option>
            </select>
          </div>

          <div class="col-md-6">
            <label class="form-label">Modelo / algoritmo Ollama</label>
            <select class="form-select" name="ollama_model" required>
              {% if models %}
                {% for m in models %}
                  <option value="{{ m }}" {% if m == cfg.default_model %}selected{% endif %}>{{ m }}</option>
                {% endfor %}
              {% else %}
                <option value="">No se encontraron modelos</option>
              {% endif %}
            </select>
            <div class="sast-help">Instala modelos con: <code>ollama pull qwen2.5-coder</code></div>
          </div>

          <div class="col-md-6">
            <label class="form-label">Extensiones permitidas</label>
            <div class="sast-ext-box">{{ allowed_ext }}</div>
          </div>

          <div class="col-12">
            <div class="sast-register-box">
              <div class="sast-register-title">Registro automático en SGSI</div>
              <div class="row g-3">
                <div class="col-md-4">
                  <label class="sast-switch-card">
                    <input type="checkbox" name="register_vulnerabilities" id="sastRegisterVulnerabilities" value="1">
                    <span>
                      <b>Registrar en Vulnerabilidades</b>
                      <small>Guarda cada hallazgo SAST en la matriz de vulnerabilidades.</small>
                    </span>
                  </label>
                </div>

                <div class="col-md-4">
                  <label class="sast-switch-card">
                    <input type="checkbox" name="create_remediation_plans" id="sastCreateRemediationPlans" value="1">
                    <span>
                      <b>Crear Plan de Remediación</b>
                      <small>Crea una acción correctiva por cada hallazgo registrado.</small>
                    </span>
                  </label>
                </div>

                <div class="col-md-4">
                  <label class="sast-switch-card">
                    <input type="checkbox" name="generate_ai_remediation" id="sastGenerateAiRemediation" value="1" checked>
                    <span>
                      <b>Remediación con IA</b>
                      <small>Si IA no responde o no está habilitada, se usa texto genérico seguro.</small>
                    </span>
                  </label>
                </div>
              </div>
              <div class="sast-help mt-2">
                Nota: si activa el plan de remediación, el sistema también registrará la vulnerabilidad porque el plan queda asociado a ese ID.
              </div>
            </div>
          </div>

          <div class="col-12">
            <div class="sast-source-tabs">
              <button type="button" class="sast-tab active" id="sastFileTab" onclick="sastShowPane('file')">📤 Subir archivo</button>
              <button type="button" class="sast-tab" id="sastPasteTab" onclick="sastShowPane('paste')">💻 Pegar código</button>
            </div>

            <div id="sastFilePane" class="sast-pane">
              <label class="form-label">Archivo de código</label>
              <input class="form-control" type="file" name="file" id="sastFileInput">
              <div class="sast-help mt-1">Para DVWA puedes probar: <code>vulnerabilities/sqli/source/low.php</code></div>
            </div>

            <div id="sastPastePane" class="sast-pane d-none">
              <label class="form-label">Código</label>
              <textarea class="form-control" name="pasted_code" rows="12" placeholder="Pega aquí el fragmento o programa completo..."></textarea>
            </div>
          </div>

          <div class="col-12 d-flex justify-content-center gap-2 flex-wrap mt-3">
            {% if read_only %}
              <button type="button" class="btn btn-secondary rounded-pill px-5 fw-bold" disabled>
                Analizar y generar PDF
              </button>
            {% else %}
              <button id="sastSubmitBtn" class="btn btn-primary rounded-pill px-5 fw-bold" type="submit" {% if not models %}disabled{% endif %}>
                🛡️ Analizar y generar PDF
              </button>
            {% endif %}
          </div>

          <div class="col-12">
            <div class="sast-progress d-none" id="sastProgressBox">
              <div class="sast-progress-label" id="sastProgressText">Enviando código al servidor…</div>
              <div class="progress">
                <div class="progress-bar" id="sastProgressBar" role="progressbar" style="width:20%;"></div>
              </div>
            </div>
          </div>
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

  .sast-shell{
    width:96%;
    max-width:1320px;
    margin:26px auto 24px auto;
  }

  .sast-hero{
    background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
    border-radius:18px;
    padding:18px 26px;
    min-height:94px;
    display:flex;
    align-items:center;
    gap:16px;
    box-shadow:0 12px 24px rgba(15,23,42,.25);
    position:relative;
    overflow:hidden;
    color:#fff;
  }

  .sast-hero::before{
    content:"";
    position:absolute;
    inset:0;
    background:
      radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
      repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
    pointer-events:none;
  }

  .sast-hero > *{ position:relative; z-index:1; }

  .sast-hero-icon{
    width:58px;
    height:58px;
    min-width:58px;
    border-radius:16px;
    background:#fff;
    color:#0b4a8f;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:1.55rem;
    box-shadow:0 8px 18px rgba(0,0,0,.25);
  }

  .sast-badge{
    width:fit-content;
    background:rgba(255,255,255,.18);
    border-radius:999px;
    padding:4px 11px;
    font-size:.68rem;
    font-weight:900;
    margin-bottom:4px;
  }

  .sast-title{
    font-size:1.42rem;
    font-weight:950;
    margin:0;
    text-shadow:0 4px 14px rgba(0,0,0,.42);
  }

  .sast-subtitle{
    font-size:.84rem;
    color:rgba(255,255,255,.88);
    margin-top:3px;
  }

  .sast-actions{
    display:flex;
    justify-content:center;
    flex-wrap:wrap;
    gap:10px;
    margin:12px 0 14px;
  }

  .sast-actions .btn{
    min-height:34px;
    padding:8px 22px !important;
    font-size:.82rem;
    font-weight:900;
    box-shadow:0 8px 16px rgba(15,23,42,.15);
  }

  .sast-card{
    background:rgba(255,255,255,.96);
    backdrop-filter:blur(8px);
    border:1px solid rgba(219,230,244,.9);
    border-radius:18px;
    box-shadow:0 12px 24px rgba(15,23,42,.18);
    overflow:hidden;
  }

  .sast-card-body{
    padding:20px;
  }

  .sast-status-grid{
    display:grid;
    grid-template-columns:repeat(3, minmax(0, 1fr));
    gap:12px;
  }

  .sast-status-box{
    background:#f8fbff;
    border:1px solid #dbe6f4;
    border-radius:16px;
    padding:12px 14px;
  }

  .sast-status-label{
    font-size:.70rem;
    font-weight:950;
    color:#5f6f86;
    text-transform:uppercase;
    letter-spacing:.04em;
  }

  .sast-status-value{
    font-size:.82rem;
    font-weight:900;
    color:#172033;
    word-break:break-word;
  }

  .sast-source-tabs{
    display:flex;
    gap:8px;
    flex-wrap:wrap;
    margin:8px 0 12px;
  }

  .sast-tab{
    border:1px solid #d9e3f0;
    background:#ffffff;
    color:#102a4b;
    border-radius:999px;
    padding:8px 18px;
    font-weight:900;
    font-size:.82rem;
  }

  .sast-tab.active{
    background:linear-gradient(135deg,#0b4a8f,#1d5fae);
    color:#fff;
    border-color:#0b4a8f;
  }

  .sast-pane{
    background:#f8fbff;
    border:1px dashed #cfe0f4;
    border-radius:16px;
    padding:15px;
  }

  .sast-ext-box{
    min-height:40px;
    border:1px solid #d9e3f0;
    background:#f8fafc;
    border-radius:10px;
    display:flex;
    align-items:center;
    padding:8px 12px;
    font-size:.80rem;
    color:#334155;
    word-break:break-word;
  }

  .sast-help{
    color:#475569;
    font-size:.76rem;
    margin-top:6px;
  }

  .sast-help code{
    background:#eef5ff;
    border:1px solid #d8e8fb;
    border-radius:7px;
    padding:2px 6px;
    color:#062b55;
  }

  .sast-register-box{
    background:#f8fbff;
    border:1px solid #dbe6f4;
    border-radius:16px;
    padding:14px;
    box-shadow:0 6px 14px rgba(15,23,42,.06);
  }

  .sast-register-title{
    font-size:.78rem;
    font-weight:950;
    color:#0b4a8f;
    margin-bottom:10px;
    text-transform:uppercase;
    letter-spacing:.04em;
  }

  .sast-switch-card{
    display:flex;
    gap:10px;
    align-items:flex-start;
    min-height:86px;
    padding:12px;
    border:1px solid #d9e3f0;
    background:#ffffff;
    border-radius:14px;
    cursor:pointer;
    transition:.18s ease;
  }

  .sast-switch-card:hover{
    border-color:#3f86d6;
    box-shadow:0 8px 16px rgba(63,134,214,.12);
  }

  .sast-switch-card input{
    margin-top:4px;
    width:18px;
    height:18px;
    accent-color:#0b4a8f;
  }

  .sast-switch-card b{
    display:block;
    font-size:.82rem;
    color:#172033;
  }

  .sast-switch-card small{
    display:block;
    color:#475569;
    font-size:.72rem;
    line-height:1.25;
    margin-top:3px;
  }

  .sast-progress{
    margin-top:10px;
    background:#f8fbff;
    border:1px solid #dbe6f4;
    border-radius:16px;
    padding:14px;
  }

  .sast-progress-label{
    font-size:.82rem;
    font-weight:900;
    color:#0b4a8f;
    margin-bottom:8px;
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
  }

  .form-control:focus,
  .form-select:focus{
    border-color:#3f86d6;
    box-shadow:0 0 0 .15rem rgba(63,134,214,.18);
    background:#ffffff;
  }

  @media(max-width:992px){
    .sast-status-grid{
      grid-template-columns:1fr;
    }
  }

  @media(max-width:768px){
    .sast-hero{
      flex-direction:column;
      text-align:center;
    }
    .sast-badge{
      margin-left:auto;
      margin-right:auto;
    }
  }
</style>

<script>
  function sastShowPane(kind){
    const filePane = document.getElementById("sastFilePane");
    const pastePane = document.getElementById("sastPastePane");
    const fileTab = document.getElementById("sastFileTab");
    const pasteTab = document.getElementById("sastPasteTab");

    if(kind === "paste"){
      filePane.classList.add("d-none");
      pastePane.classList.remove("d-none");
      fileTab.classList.remove("active");
      pasteTab.classList.add("active");
    }else{
      pastePane.classList.add("d-none");
      filePane.classList.remove("d-none");
      pasteTab.classList.remove("active");
      fileTab.classList.add("active");
    }
  }

  const artifactType = document.getElementById("sastArtifactType");
  if(artifactType){
    artifactType.addEventListener("change", function(){
      const v = (artifactType.value || "").toLowerCase();
      if(v === "parte de código" || v === "parte de codigo"){
        sastShowPane("paste");
      }
    });
  }

  const createPlansToggle = document.getElementById("sastCreateRemediationPlans");
  const registerVulnToggle = document.getElementById("sastRegisterVulnerabilities");
  if(createPlansToggle && registerVulnToggle){
    createPlansToggle.addEventListener("change", function(){
      if(createPlansToggle.checked){
        registerVulnToggle.checked = true;
      }
    });
    registerVulnToggle.addEventListener("change", function(){
      if(!registerVulnToggle.checked && createPlansToggle.checked){
        createPlansToggle.checked = false;
      }
    });
  }

  const form = document.getElementById("sastAnalyzeForm");
  if(form){
    form.addEventListener("submit", async function(e){
      e.preventDefault();

      const progressBox = document.getElementById("sastProgressBox");
      const progressText = document.getElementById("sastProgressText");
      const progressBar = document.getElementById("sastProgressBar");
      const submitBtn = document.getElementById("sastSubmitBtn");

      if(progressBox) progressBox.classList.remove("d-none");
      if(progressText) progressText.textContent = "Enviando código al servidor…";
      if(progressBar) progressBar.style.width = "20%";
      if(submitBtn) submitBtn.disabled = true;

      try{
        const fd = new FormData(form);
        const resp = await fetch(form.action, {
          method: "POST",
          body: fd,
          headers: {
            "Accept": "application/json",
            "X-Requested-With": "fetch"
          }
        });

        const data = await resp.json().catch(() => null);

        if(!resp.ok){
          throw new Error((data && data.error) ? data.error : "Error HTTP " + resp.status);
        }

        if(!data || !data.ok || !data.job_id){
          throw new Error("Respuesta inválida del servidor.");
        }

        window.location.href = "{{ url_for('sast_track', job_id='__JOB__') }}".replace("__JOB__", data.job_id);

      }catch(err){
        if(progressText) progressText.textContent = "Error: " + (err.message || err);
        if(submitBtn) submitBtn.disabled = false;
      }
    });
  }
</script>
"""


SAST_CONFIG_HTML = """
<div class="sast-shell">

  <div class="sast-hero">
    <div class="sast-hero-icon">⚙️</div>
    <div>
      <div class="sast-badge">SGSI · Pruebas SAST · Ollama Local</div>
      <h2 class="sast-title">Configuración Ollama</h2>
      <div class="sast-subtitle">
        Configure la URL local y seleccione el modelo/algoritmo instalado en Ollama.
      </div>
    </div>
  </div>

  <div class="sast-actions">
    <a href="{{ url_for('sast_index') }}" class="btn btn-light rounded-pill px-4 fw-bold">
      ⬅ Volver a Pruebas SAST
    </a>
    <a href="{{ url_for('vulnerabilidades_matriz') }}" class="btn btn-outline-secondary rounded-pill px-4 fw-bold">
      Matriz de Vulnerabilidades
    </a>
  </div>

  <div class="sast-card">
    <div class="sast-card-body">
      <div class="alert {{ 'alert-success' if conn_ok else 'alert-danger' }} rounded-4">
        <b>Estado de conexión:</b> {{ conn_msg }}
      </div>

      <form method="post">
        <div class="row g-3">
          <div class="col-md-6">
            <label class="form-label">URL base de Ollama</label>
            <input class="form-control" name="base_url" value="{{ cfg.base_url }}" placeholder="http://localhost:11434" required>
          </div>

          <div class="col-md-6">
            <label class="form-label">Modelo por defecto</label>
            <select class="form-select" name="default_model">
              <option value="">Seleccione un modelo</option>
              {% for m in models %}
                <option value="{{ m }}" {% if m == cfg.default_model %}selected{% endif %}>{{ m }}</option>
              {% endfor %}
            </select>
            {% if not models %}
              <div class="sast-help text-danger">No se encontraron modelos. Ejecute: <code>ollama pull qwen2.5-coder</code></div>
            {% endif %}
          </div>

          <div class="col-md-3">
            <label class="form-label">Temperatura</label>
            <input class="form-control" name="temperature" value="{{ cfg.temperature }}" type="number" min="0" max="1" step="0.1">
          </div>

          <div class="col-md-3">
            <label class="form-label">Timeout segundos</label>
            <input class="form-control" name="timeout" value="{{ cfg.timeout }}" type="number" min="30" max="1200" step="10">
          </div>

          <div class="col-md-3">
            <label class="form-label">Tokens resumen</label>
            <input class="form-control" name="summary_max_tokens" value="{{ cfg.summary_max_tokens }}" type="number" min="300" max="5000" step="100">
          </div>

          <div class="col-md-3">
            <label class="form-label">Tokens hallazgos</label>
            <input class="form-control" name="findings_max_tokens" value="{{ cfg.findings_max_tokens }}" type="number" min="800" max="12000" step="100">
          </div>

          <div class="col-12 d-flex justify-content-center gap-2 flex-wrap mt-3">
            <button class="btn btn-primary rounded-pill px-5 fw-bold" type="submit">
              Guardar configuración
            </button>
            <a class="btn btn-outline-primary rounded-pill px-5 fw-bold" href="{{ url_for('sast_config') }}">
              Probar conexión
            </a>
          </div>
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
  .sast-shell{width:96%; max-width:1180px; margin:26px auto 24px auto;}
  .sast-hero{
    background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);
    border-radius:18px;
    padding:18px 26px;
    min-height:94px;
    display:flex;
    align-items:center;
    gap:16px;
    box-shadow:0 12px 24px rgba(15,23,42,.25);
    color:#fff;
    position:relative;
    overflow:hidden;
  }
  .sast-hero::before{
    content:"";
    position:absolute;
    inset:0;
    background:
      radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
      repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
    pointer-events:none;
  }
  .sast-hero > *{position:relative; z-index:1;}
  .sast-hero-icon{
    width:58px;height:58px;min-width:58px;border-radius:16px;background:#fff;color:#0b4a8f;
    display:flex;align-items:center;justify-content:center;font-size:1.55rem;box-shadow:0 8px 18px rgba(0,0,0,.25);
  }
  .sast-badge{width:fit-content;background:rgba(255,255,255,.18);border-radius:999px;padding:4px 11px;font-size:.68rem;font-weight:900;margin-bottom:4px;}
  .sast-title{font-size:1.42rem;font-weight:950;margin:0;text-shadow:0 4px 14px rgba(0,0,0,.42);}
  .sast-subtitle{font-size:.84rem;color:rgba(255,255,255,.88);margin-top:3px;}
  .sast-actions{display:flex;justify-content:center;flex-wrap:wrap;gap:10px;margin:12px 0 14px;}
  .sast-actions .btn{min-height:34px;padding:8px 22px!important;font-size:.82rem;font-weight:900;box-shadow:0 8px 16px rgba(15,23,42,.15);}
  .sast-card{background:rgba(255,255,255,.96);backdrop-filter:blur(8px);border:1px solid rgba(219,230,244,.9);border-radius:18px;box-shadow:0 12px 24px rgba(15,23,42,.18);overflow:hidden;}
  .sast-card-body{padding:20px;}
  .form-label{color:#25324a;margin-bottom:4px;font-weight:900;font-size:.78rem;}
  .form-control,.form-select{border-radius:10px;min-height:40px;border:1px solid #d9e3f0;font-size:.86rem;background:#f8fafc;}
  .form-control:focus,.form-select:focus{border-color:#3f86d6;box-shadow:0 0 0 .15rem rgba(63,134,214,.18);background:#ffffff;}
  .sast-help{color:#475569;font-size:.76rem;margin-top:6px;}
  .sast-help code{background:#eef5ff;border:1px solid #d8e8fb;border-radius:7px;padding:2px 6px;color:#062b55;}
</style>
"""


SAST_TRACK_HTML = """
<div class="sast-shell">
  <div class="sast-card">
    <div class="sast-card-body text-center">
      <h4 class="fw-bold text-primary mb-2">Procesando análisis SAST…</h4>
      <div class="text-muted mb-3">No cierre esta ventana mientras Ollama analiza el código.</div>
      <div class="progress" style="height:16px; border-radius:999px;">
        <div id="sastTrackBar" class="progress-bar" role="progressbar" style="width:5%;"></div>
      </div>
      <div class="mt-3 fw-bold text-primary" id="sastTrackMsg">Iniciando…</div>
      <div class="mt-4">
        <a href="{{ url_for('sast_index') }}" class="btn btn-outline-secondary rounded-pill px-4">Cancelar / volver</a>
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
  .sast-shell{width:96%; max-width:760px; margin:70px auto 24px auto;}
  .sast-card{background:rgba(255,255,255,.96);backdrop-filter:blur(8px);border:1px solid rgba(219,230,244,.9);border-radius:18px;box-shadow:0 12px 24px rgba(15,23,42,.18);overflow:hidden;}
  .sast-card-body{padding:30px;}
</style>

<script>
  const jobId = "{{ job_id }}";
  const bar = document.getElementById("sastTrackBar");
  const msg = document.getElementById("sastTrackMsg");

  const es = new EventSource("{{ url_for('sast_progress', job_id=job_id) }}");

  es.onmessage = function(evt){
    const p = JSON.parse(evt.data);
    const pct = Math.max(0, Math.min(100, p.percent || 0));
    if(bar) bar.style.width = pct + "%";
    if(msg) msg.textContent = p.message || "Procesando…";

    if(p.status === "error"){
      es.close();
      if(msg) msg.textContent = "Error: " + (p.error || "desconocido");
    }

    if(p.done && p.status === "done"){
      es.close();
      window.location.href = "{{ url_for('sast_result', job_id=job_id) }}";
    }
  };

  es.onerror = function(){
    es.close();
    if(msg) msg.textContent = "Error recibiendo progreso del servidor.";
  };
</script>
"""


SAST_RESULT_HTML = """
<div class="sast-shell">

  <div class="sast-hero">
    <div class="sast-hero-icon">📄</div>
    <div>
      <div class="sast-badge">SGSI · Resultado Pruebas SAST</div>
      <h2 class="sast-title">Resultado del análisis SAST</h2>
      <div class="sast-subtitle">
        Informe generado con Ollama local y clasificado por severidad, CWE/CVE y recomendación de remediación.
      </div>
    </div>
  </div>

  <div class="sast-actions">
    <a class="btn btn-primary rounded-pill px-4 fw-bold" href="{{ url_for('sast_download_pdf', name=pdf_name) }}">
      Descargar PDF
    </a>
    <a class="btn btn-outline-primary rounded-pill px-4 fw-bold" href="{{ url_for('sast_download_json', name=json_name) }}">
      Descargar JSON
    </a>
    <a class="btn btn-light rounded-pill px-4 fw-bold" href="{{ url_for('sast_index') }}">
      Nuevo análisis
    </a>
    <a class="btn btn-outline-primary rounded-pill px-4 fw-bold" href="{{ url_for('sast_reports') }}">
      Ver informes
    </a>
    <a class="btn btn-outline-secondary rounded-pill px-4 fw-bold" href="{{ url_for('vulnerabilidades_matriz') }}">
      Matriz de Vulnerabilidades
    </a>
  </div>

  {% set reg = registration_summary or analysis.get('sgsi_registration', {}) or {} %}
  {% if reg.get('requested_register_vulnerabilities') or reg.get('requested_create_remediation_plans') %}
    <div class="sast-card mb-3">
      <div class="sast-card-body">
        <div class="sast-section-title">Registro automático SGSI</div>

        {% if reg.get('error') %}
          <div class="alert alert-warning rounded-4 mb-3">
            El análisis SAST se generó correctamente, pero el registro automático presentó una advertencia:
            <b>{{ reg.get('error') }}</b>
          </div>
        {% endif %}

        <div class="row g-3">
          <div class="col-md-4">
            <div class="sast-kpi">
              <div class="sast-kpi-label">Vulnerabilidades creadas</div>
              <div class="sast-kpi-value">{{ reg.get('vulnerabilities_created', 0) }}</div>
            </div>
          </div>
          <div class="col-md-4">
            <div class="sast-kpi">
              <div class="sast-kpi-label">Planes creados</div>
              <div class="sast-kpi-value">{{ reg.get('remediation_plans_created', 0) }}</div>
            </div>
          </div>
          <div class="col-md-4">
            <div class="sast-kpi">
              <div class="sast-kpi-label">Remediación</div>
              <div class="sast-kpi-value small">
                {{ 'IA / fallback seguro' if reg.get('requested_ai_remediation') else 'Texto genérico' }}
              </div>
            </div>
          </div>
          <div class="col-12 d-flex gap-2 flex-wrap justify-content-center">
            <a class="btn btn-outline-primary rounded-pill px-4 fw-bold" href="{{ url_for('vulnerabilidades_matriz') }}">
              Ver Matriz de Vulnerabilidades
            </a>
            <a class="btn btn-outline-primary rounded-pill px-4 fw-bold" href="{{ url_for('plan_remediacion_matriz') }}">
              Ver Plan de Remediación
            </a>
          </div>
        </div>
      </div>
    </div>
  {% endif %}

  <div class="sast-card mb-3">
    <div class="sast-card-body">
      {% set ex = analysis.get('executive_summary', {}) or {} %}
      <div class="row g-3">
        <div class="col-md-4">
          <div class="sast-kpi">
            <div class="sast-kpi-label">Riesgo general</div>
            <div class="sast-kpi-value">{{ ex.get('overall_risk_level', 'N/A') }}</div>
          </div>
        </div>
        <div class="col-md-4">
          <div class="sast-kpi">
            <div class="sast-kpi-label">Puntaje</div>
            <div class="sast-kpi-value">{{ ex.get('overall_risk_score', 'N/A') }}/100</div>
          </div>
        </div>
        <div class="col-md-4">
          <div class="sast-kpi">
            <div class="sast-kpi-label">Modelo</div>
            <div class="sast-kpi-value small">{{ meta.get('model', 'Ollama') }}</div>
          </div>
        </div>
        <div class="col-12">
          <div class="sast-summary">{{ ex.get('management_overview', 'Sin resumen ejecutivo.') }}</div>
        </div>
      </div>
    </div>
  </div>

  <div class="sast-card mb-3">
    <div class="sast-card-body">
      <div class="sast-section-title">Métricas</div>
      <pre class="sast-pre">{{ analysis.get('metrics', {}) | tojson(indent=2) }}</pre>
    </div>
  </div>

  <div class="sast-card">
    <div class="sast-card-body">
      <div class="sast-section-title">Hallazgos</div>

      {% set findings = analysis.get('findings', []) or [] %}
      {% if findings|length == 0 %}
        <div class="alert alert-success rounded-4 mb-0">No se identificaron hallazgos.</div>
      {% else %}
        <div class="table-responsive">
          <table class="table table-hover align-middle sast-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Título</th>
                <th>Severidad</th>
                <th>CVSS</th>
                <th>CWE</th>
                <th>CVE</th>
                <th>Ubicación</th>
              </tr>
            </thead>
            <tbody>
              {% for f in findings %}
                {% set loc = f.get('location', {}) or {} %}
                <tr>
                  <td class="fw-bold">{{ f.get('id','N/A') }}</td>
                  <td>
                    <div class="fw-bold">{{ f.get('title','') }}</div>
                    <div class="text-muted small">{{ f.get('description','') }}</div>
                  </td>
                  <td class="fw-bold">{{ f.get('severity','N/A') }}</td>
                  <td>{{ f.get('cvss_score','N/A') }}</td>
                  <td>{{ f.get('cwe','N/A') }}</td>
                  <td>{{ f.get('cve','N/A') }}</td>
                  <td class="small">{{ loc.get('file','') }}:{{ loc.get('line_start','') }}</td>
                </tr>
                <tr>
                  <td></td>
                  <td colspan="6">
                    <div class="sast-detail-grid">
                      <div>
                        <b>Evidencia:</b>
                        <pre class="sast-pre">{{ f.get('evidence_snippet','') }}</pre>
                      </div>
                      <div>
                        {% set rem = f.get('remediation', {}) or {} %}
                        <b>Recomendación / acción correctiva:</b>
                        <div class="sast-summary">{{ rem.get('recommendation','') }}</div>
                        {% if rem.get('secure_code_example') %}
                          <b class="mt-2 d-block">Ejemplo seguro:</b>
                          <pre class="sast-pre">{{ rem.get('secure_code_example','') }}</pre>
                        {% endif %}
                      </div>
                    </div>
                  </td>
                </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      {% endif %}
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
  .sast-shell{width:96%; max-width:1320px; margin:26px auto 24px auto;}
  .sast-hero{background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);border-radius:18px;padding:18px 26px;min-height:94px;display:flex;align-items:center;gap:16px;box-shadow:0 12px 24px rgba(15,23,42,.25);color:#fff;position:relative;overflow:hidden;}
  .sast-hero::before{content:"";position:absolute;inset:0;background:radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);pointer-events:none;}
  .sast-hero > *{position:relative;z-index:1;}
  .sast-hero-icon{width:58px;height:58px;min-width:58px;border-radius:16px;background:#fff;color:#0b4a8f;display:flex;align-items:center;justify-content:center;font-size:1.55rem;box-shadow:0 8px 18px rgba(0,0,0,.25);}
  .sast-badge{width:fit-content;background:rgba(255,255,255,.18);border-radius:999px;padding:4px 11px;font-size:.68rem;font-weight:900;margin-bottom:4px;}
  .sast-title{font-size:1.42rem;font-weight:950;margin:0;text-shadow:0 4px 14px rgba(0,0,0,.42);}
  .sast-subtitle{font-size:.84rem;color:rgba(255,255,255,.88);margin-top:3px;}
  .sast-actions{display:flex;justify-content:center;flex-wrap:wrap;gap:10px;margin:12px 0 14px;}
  .sast-actions .btn{min-height:34px;padding:8px 22px!important;font-size:.82rem;font-weight:900;box-shadow:0 8px 16px rgba(15,23,42,.15);}
  .sast-card{background:rgba(255,255,255,.96);backdrop-filter:blur(8px);border:1px solid rgba(219,230,244,.9);border-radius:18px;box-shadow:0 12px 24px rgba(15,23,42,.18);overflow:hidden;}
  .sast-card-body{padding:20px;}
  .sast-kpi{background:#f8fbff;border:1px solid #dbe6f4;border-radius:16px;padding:14px;}
  .sast-kpi-label{font-size:.70rem;font-weight:950;color:#475569;text-transform:uppercase;letter-spacing:.04em;}
  .sast-kpi-value{font-size:1.2rem;font-weight:950;color:#0b4a8f;word-break:break-word;}
  .sast-summary{background:#f8fbff;border:1px solid #dbe6f4;border-radius:14px;padding:12px;color:#101827;font-size:.86rem;}
  .sast-section-title{font-size:.95rem;font-weight:950;color:#0b4a8f;margin-bottom:10px;}
  .sast-pre{white-space:pre-wrap;background:#f8fbff;border:1px solid #dbe6f4;border-radius:14px;padding:10px;font-size:.78rem;margin:4px 0;color:#101827;}
  .sast-table thead th{background:linear-gradient(135deg,#1d5fa9,#2f7fd1)!important;color:#fff!important;font-weight:900;font-size:.78rem;}
  .sast-table td{font-size:.78rem;vertical-align:top;}
  .sast-detail-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;}
  @media(max-width:992px){.sast-detail-grid{grid-template-columns:1fr;}}
</style>
"""


SAST_REPORTS_HTML = """
<div class="sast-shell">

  <div class="sast-hero">
    <div class="sast-hero-icon">📊</div>
    <div>
      <div class="sast-badge">SGSI · Pruebas SAST · Informes</div>
      <h2 class="sast-title">Informes de Pruebas SAST</h2>
      <div class="sast-subtitle">
        Matriz histórica de ejecuciones SAST efectuadas con Ollama local, con acceso a PDF, JSON y detalle del análisis.
      </div>
    </div>
  </div>

  <div class="sast-actions">
    <a href="{{ url_for('sast_index') }}" class="btn btn-light rounded-pill px-4 fw-bold">
      ⬅ Volver a Pruebas SAST
    </a>

    <div class="dropdown">
      <button class="btn btn-primary rounded-pill px-4 fw-bold dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false">
        Ejecución de pruebas
      </button>
      <ul class="dropdown-menu shadow-sm rounded-4">
        <li><a class="dropdown-item fw-semibold" href="{{ url_for('sast_index') }}">🧪 Nueva prueba SAST</a></li>
        <li><a class="dropdown-item fw-semibold active" href="{{ url_for('sast_reports') }}">📊 Ver informes</a></li>
        <li><hr class="dropdown-divider"></li>
        <li><a class="dropdown-item fw-semibold" href="{{ url_for('sast_config') }}">⚙️ Configuración Ollama</a></li>
      </ul>
    </div>

    <a href="{{ url_for('vulnerabilidades_matriz') }}" class="btn btn-outline-primary rounded-pill px-4 fw-bold">
      Matriz de Vulnerabilidades
    </a>
  </div>

  <div class="sast-card mb-3">
    <div class="sast-card-body">
      <form method="get" action="{{ url_for('sast_reports') }}" class="row g-3 align-items-end">
        <div class="col-md-8">
          <label class="form-label">Buscar ejecución</label>
          <input class="form-control" name="q" value="{{ q }}" placeholder="Proyecto, archivo, modelo, riesgo o usuario...">
        </div>
        <div class="col-md-4 d-flex gap-2 flex-wrap">
          <button class="btn btn-primary rounded-pill px-4 fw-bold" type="submit">Filtrar</button>
          <a class="btn btn-outline-secondary rounded-pill px-4 fw-bold" href="{{ url_for('sast_reports') }}">Limpiar</a>
        </div>
      </form>
    </div>
  </div>

  <div class="sast-card">
    <div class="sast-card-body">
      <div class="d-flex justify-content-between flex-wrap gap-2 align-items-center mb-3">
        <div>
          <div class="sast-section-title mb-1">Matriz de ejecuciones</div>
          <div class="text-muted small">Total mostrado: {{ reports|length }}</div>
        </div>
      </div>

      {% if reports|length == 0 %}
        <div class="alert alert-info rounded-4 mb-0">
          No hay informes SAST registrados todavía. Ejecuta una prueba desde <b>Pruebas SAST con IA Local</b> para alimentar esta matriz.
        </div>
      {% else %}
        <div class="table-responsive">
          <table class="table table-hover align-middle sast-table">
            <thead>
              <tr>
                <th style="width:120px;">Fecha</th>
                <th>Proyecto</th>
                <th>Archivo</th>
                <th style="width:110px;">Lenguaje</th>
                <th>Modelo</th>
                <th style="width:100px;">Riesgo</th>
                <th style="width:95px;">Score</th>
                <th style="width:130px;">Hallazgos</th>
                <th style="width:150px;">Registro SGSI</th>
                <th style="width:260px;">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {% for r in reports %}
                <tr>
                  <td class="small fw-semibold">{{ r.get('date_str','') }}</td>
                  <td>
                    <div class="fw-bold">{{ r.get('project_name','N/A') }}</div>
                    <div class="text-muted small">{{ r.get('artifact_type','N/A') }} · Ejecutado por: {{ r.get('executed_by','N/A') }}</div>
                  </td>
                  <td class="small">{{ r.get('filename','N/A') }}</td>
                  <td>{{ r.get('language','N/A') }}</td>
                  <td class="small">{{ r.get('model','N/A') }}</td>
                  <td>
                    <span class="badge rounded-pill bg-primary-subtle text-primary border border-primary-subtle">
                      {{ r.get('overall_risk_level','N/A') }}
                    </span>
                  </td>
                  <td class="fw-bold">{{ r.get('overall_risk_score','N/A') }}</td>
                  <td class="small">
                    <b>{{ r.get('total_findings',0) }}</b>
                    <div class="text-muted">
                      C:{{ r.get('critical_count',0) }} · A:{{ r.get('high_count',0) }} · M:{{ r.get('medium_count',0) }} · B:{{ r.get('low_count',0) }}
                    </div>
                  </td>
                  <td class="small">
                    <div>Vuln: <b>{{ r.get('vulnerabilities_created',0) }}</b></div>
                    <div>Planes: <b>{{ r.get('remediation_plans_created',0) }}</b></div>
                    {% if r.get('registration_error') %}
                      <div class="text-warning fw-bold">Advertencia</div>
                    {% endif %}
                  </td>
                  <td>
                    <div class="d-flex gap-1 flex-wrap">
                      <a class="btn btn-sm btn-outline-primary rounded-pill fw-bold"
                         href="{{ url_for('sast_report_detail', report_id=r.get('report_id')) }}">
                        Abrir
                      </a>

                      {% if r.get('pdf_name') %}
                        <a class="btn btn-sm btn-primary rounded-pill fw-bold"
                           href="{{ url_for('sast_download_pdf', name=r.get('pdf_name')) }}">
                          PDF
                        </a>
                      {% endif %}

                      {% if r.get('json_name') %}
                        <a class="btn btn-sm btn-outline-secondary rounded-pill fw-bold"
                           href="{{ url_for('sast_download_json', name=r.get('json_name')) }}">
                          JSON
                        </a>
                      {% endif %}

                      {% if not read_only %}
                        <form method="POST"
                              action="{{ url_for('sast_report_delete', report_id=r.get('report_id')) }}"
                              class="d-inline"
                              data-no-progress="true"
                              onsubmit="return confirm('¿Seguro que deseas eliminar este informe SAST? Se eliminarán el PDF y el JSON del informe, pero no las vulnerabilidades ni los planes de remediación ya registrados.');">
                          <button type="submit"
                                  class="btn btn-sm btn-outline-danger rounded-pill fw-bold">
                            Eliminar
                          </button>
                        </form>
                      {% endif %}
                    </div>
                  </td>
                </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      {% endif %}
    </div>
  </div>
</div>

<style>
  body{background-image:url('/static/img/ccsgsi.jpg');background-size:cover;background-position:center;background-attachment:fixed;background-repeat:no-repeat;}
  .sast-shell{width:96%;max-width:1360px;margin:26px auto 24px auto;}
  .sast-hero{background:linear-gradient(135deg,#062b55,#0b4a8f,#1d5fae);border-radius:18px;padding:18px 26px;min-height:94px;display:flex;align-items:center;gap:16px;box-shadow:0 12px 24px rgba(15,23,42,.25);color:#fff;position:relative;overflow:hidden;}
  .sast-hero::before{content:"";position:absolute;inset:0;background:radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);pointer-events:none;}
  .sast-hero>*{position:relative;z-index:1;}
  .sast-hero-icon{width:58px;height:58px;min-width:58px;border-radius:16px;background:#fff;color:#0b4a8f;display:flex;align-items:center;justify-content:center;font-size:1.55rem;box-shadow:0 8px 18px rgba(0,0,0,.25);}
  .sast-badge{width:fit-content;background:rgba(255,255,255,.18);border-radius:999px;padding:4px 11px;font-size:.68rem;font-weight:900;margin-bottom:4px;}
  .sast-title{font-size:1.42rem;font-weight:950;margin:0;text-shadow:0 4px 14px rgba(0,0,0,.42);}
  .sast-subtitle{font-size:.84rem;color:rgba(255,255,255,.88);margin-top:3px;}
  .sast-actions{display:flex;justify-content:center;flex-wrap:wrap;gap:10px;margin:12px 0 14px;}
  .sast-actions .btn{min-height:34px;padding:8px 22px!important;font-size:.82rem;font-weight:900;box-shadow:0 8px 16px rgba(15,23,42,.15);}
  .sast-card{background:rgba(255,255,255,.96);backdrop-filter:blur(8px);border:1px solid rgba(219,230,244,.9);border-radius:18px;box-shadow:0 12px 24px rgba(15,23,42,.18);overflow:hidden;}
  .sast-card-body{padding:20px;}
  .form-label{color:#25324a;margin-bottom:4px;font-weight:900;font-size:.78rem;}
  .form-control,.form-select{border-radius:10px;min-height:40px;border:1px solid #d9e3f0;font-size:.86rem;background:#f8fafc;}
  .sast-section-title{font-size:.95rem;font-weight:950;color:#0b4a8f;margin-bottom:10px;}
  .sast-table thead th{background:linear-gradient(135deg,#1d5fa9,#2f7fd1)!important;color:#fff!important;font-weight:900;font-size:.75rem;white-space:nowrap;}
  .sast-table td{font-size:.76rem;vertical-align:top;}
  .dropdown-menu .dropdown-item{font-size:.82rem;}
</style>
"""


@app.route("/pruebas_sast", methods=["GET"])
@login_required
def sast_index():
    user, resp, read_only = sast_require_access(write=False)
    if resp:
        return resp

    cfg = sast_load_ollama_config()
    conn_ok, conn_msg, models = sast_test_ollama_connection(cfg.get("base_url"))

    if cfg.get("default_model") and cfg.get("default_model") not in models:
        models = [cfg.get("default_model")] + models

    inner = render_template_string(
        SAST_INDEX_HTML,
        cfg=cfg,
        models=models,
        conn_ok=conn_ok,
        conn_msg=conn_msg,
        allowed_ext=", ".join(sorted(SAST_ALLOWED_EXT)),
        read_only=read_only,
    )
    return render_template_string(BASE, content=Markup(inner))


@app.route("/pruebas_sast/informes", methods=["GET"])
@login_required
def sast_reports():
    user, resp, read_only = sast_require_access(write=False)
    if resp:
        return resp

    q = (request.args.get("q") or "").strip()
    q_norm = q.lower()
    reports = sast_get_scan_history()

    if q_norm:
        def match_record(r):
            haystack = " ".join([
                str(r.get("report_id", "")),
                str(r.get("date_str", "")),
                str(r.get("project_name", "")),
                str(r.get("artifact_type", "")),
                str(r.get("filename", "")),
                str(r.get("language", "")),
                str(r.get("model", "")),
                str(r.get("overall_risk_level", "")),
                str(r.get("executed_by", "")),
            ]).lower()
            return q_norm in haystack
        reports = [r for r in reports if match_record(r)]

    inner = render_template_string(
        SAST_REPORTS_HTML,
        reports=reports,
        q=q,
        read_only=read_only,
    )
    return render_template_string(BASE, content=Markup(inner))


@app.route("/pruebas_sast/informes/<report_id>", methods=["GET"])
@login_required
def sast_report_detail(report_id):
    user, resp, read_only = sast_require_access(write=False)
    if resp:
        return resp

    report_id = (report_id or "").strip()
    record = sast_get_scan_history_record(report_id)
    if not record:
        flash("Informe SAST no encontrado en el historial.", "warning")
        return redirect(url_for("sast_reports"))

    json_name = record.get("json_name") or f"analysis_{report_id}.json"
    json_path = os.path.join(SAST_REPORT_DIR, sast_safe_filename(json_name))

    if not os.path.exists(json_path):
        flash("El archivo JSON del informe SAST no existe en reports/sast.", "warning")
        return redirect(url_for("sast_reports"))

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            analysis = json.load(f)
        if not isinstance(analysis, dict):
            analysis = {}
    except Exception as e:
        flash(f"No fue posible abrir el JSON del informe SAST: {e}", "danger")
        return redirect(url_for("sast_reports"))

    meta = analysis.get("sast_meta", {}) or {
        "project_name": record.get("project_name"),
        "artifact_type": record.get("artifact_type"),
        "filename": record.get("filename"),
        "language": record.get("language"),
        "date_str": record.get("date_str"),
        "model": record.get("model"),
    }

    inner = render_template_string(
        SAST_RESULT_HTML,
        analysis=analysis,
        pdf_name=record.get("pdf_name") or f"Informe_SAST_{report_id}.pdf",
        json_name=json_name,
        meta=meta,
        registration_summary=(analysis.get("sgsi_registration", {}) or {}),
    )
    return render_template_string(BASE, content=Markup(inner))


@app.route("/pruebas_sast/informes/<report_id>/eliminar", methods=["POST"])
@login_required
def sast_report_delete(report_id):
    user, resp, read_only = sast_require_access(write=True)
    if resp:
        return resp

    report_id = (report_id or "").strip()
    if not report_id:
        flash("ID de informe SAST inválido.", "warning")
        return redirect(url_for("sast_reports"))

    record = sast_get_scan_history_record(report_id)
    if not record:
        flash("Informe SAST no encontrado en el historial.", "warning")
        return redirect(url_for("sast_reports"))

    deleted_files = []
    file_errors = []
    base_dir = os.path.abspath(SAST_REPORT_DIR)

    for field in ("pdf_name", "json_name"):
        name = (record.get(field) or "").strip()
        if not name:
            continue

        safe_name = sast_safe_filename(name)
        path = os.path.abspath(os.path.join(SAST_REPORT_DIR, safe_name))

        # Evita traversal fuera de reports/sast
        if not path.startswith(base_dir + os.sep):
            file_errors.append(f"{safe_name}: ruta no permitida")
            continue

        if os.path.exists(path):
            try:
                os.remove(path)
                deleted_files.append(os.path.basename(path))
            except Exception as e:
                file_errors.append(f"{safe_name}: {e}")

    sast_delete_scan_history_record(report_id)

    try:
        username = getattr(user, "username", None) or session.get("username") or "Sistema"
        registrar_log(
            username,
            (
                f"Eliminó informe SAST {report_id}. "
                f"Archivos eliminados: {', '.join(deleted_files) if deleted_files else 'ninguno'}."
            )
        )
    except Exception:
        pass

    if file_errors:
        flash(
            "El informe fue retirado del historial, pero algunos archivos no pudieron eliminarse: "
            + " | ".join(file_errors),
            "warning"
        )
    else:
        flash(
            "Informe SAST eliminado correctamente. "
            "No se eliminaron vulnerabilidades ni planes de remediación asociados.",
            "success"
        )

    return redirect(url_for("sast_reports"))


@app.route("/pruebas_sast/config", methods=["GET", "POST"])
@login_required
def sast_config():
    user, resp, read_only = sast_require_access(write=True, config=True)
    if resp:
        return resp

    if request.method == "POST":
        cfg = sast_save_ollama_config({
            "base_url": request.form.get("base_url"),
            "default_model": request.form.get("default_model"),
            "temperature": request.form.get("temperature"),
            "timeout": request.form.get("timeout"),
            "summary_max_tokens": request.form.get("summary_max_tokens"),
            "findings_max_tokens": request.form.get("findings_max_tokens"),
        })
        flash("Configuración SAST/Ollama guardada correctamente.", "success")
        return redirect(url_for("sast_config"))

    cfg = sast_load_ollama_config()
    conn_ok, conn_msg, models = sast_test_ollama_connection(cfg.get("base_url"))

    if cfg.get("default_model") and cfg.get("default_model") not in models:
        models = [cfg.get("default_model")] + models

    inner = render_template_string(
        SAST_CONFIG_HTML,
        cfg=cfg,
        models=models,
        conn_ok=conn_ok,
        conn_msg=conn_msg,
    )
    return render_template_string(BASE, content=Markup(inner))


@app.route("/pruebas_sast/models", methods=["GET"])
@login_required
def sast_models():
    user, resp, read_only = sast_require_access(write=False)
    if resp:
        return resp

    base_url = request.args.get("base_url") or None
    models, err = sast_list_ollama_models(base_url)
    return jsonify({"ok": err is None, "models": models, "error": err})


@app.route("/pruebas_sast/start", methods=["POST"])
@login_required
def sast_start():
    user, resp, read_only = sast_require_access(write=True)
    if resp:
        return jsonify({"ok": False, "error": "No tiene permiso para ejecutar pruebas SAST."}), 403

    register_vulnerabilities = sast_bool_form(request.form.get("register_vulnerabilities"))
    create_remediation_plans = sast_bool_form(request.form.get("create_remediation_plans"))
    generate_ai_remediation = sast_bool_form(request.form.get("generate_ai_remediation"))

    # Si se crea plan de remediación, se requiere vulnerabilidad porque PlanRemediacion
    # tiene FK obligatoria contra VulnerabilidadRegistro.
    if create_remediation_plans:
        register_vulnerabilities = True

    if register_vulnerabilities:
        if user.role != "admin" and not verificar_permiso(user, "Registro de Vulnerabilidades"):
            return jsonify({
                "ok": False,
                "error": "No tiene permiso para registrar hallazgos en Registro de Vulnerabilidades."
            }), 403

    if create_remediation_plans:
        if user.role != "admin" and not verificar_permiso(user, "Plan de Remediación"):
            return jsonify({
                "ok": False,
                "error": "No tiene permiso para crear planes de remediación."
            }), 403

    project_name = (request.form.get("project_name") or "Proyecto sin nombre").strip()
    artifact_type = (request.form.get("artifact_type") or "Programa completo").strip()
    requested_model = (request.form.get("ollama_model") or "").strip()
    pasted_code = (request.form.get("pasted_code") or "").strip()
    uploaded = request.files.get("file")

    artifact_norm = artifact_type.strip().lower()
    is_partial = artifact_norm in ("parte de código", "parte de codigo")

    if is_partial:
        if not pasted_code:
            return jsonify({"ok": False, "error": 'Para "Parte de Código" debe pegar el fragmento en la caja de texto.'}), 400
        uploaded = None

    if not pasted_code and (not uploaded or not uploaded.filename or uploaded.filename.strip() == ""):
        return jsonify({"ok": False, "error": "Debe pegar código o cargar un archivo."}), 400

    filename = "codigo_pegado.txt"
    code_text = ""
    language = (request.form.get("language") or "").strip()

    if uploaded and uploaded.filename and not pasted_code:
        original_name = uploaded.filename
        if not sast_ext_ok(original_name):
            return jsonify({"ok": False, "error": f"Extensión no permitida: {os.path.splitext(original_name)[1]}"}), 400

        filename = sast_safe_filename(original_name)
        stored_name = f"{uuid.uuid4().hex}_{filename}"
        path = os.path.join(SAST_UPLOAD_DIR, stored_name)
        uploaded.save(path)
        code_text = sast_read_text_file(path)

        if not language:
            language = sast_detect_language_from_filename(filename)
    else:
        code_text = pasted_code
        if not language:
            language = "unknown"

    if not code_text.strip():
        return jsonify({"ok": False, "error": "El código está vacío."}), 400

    try:
        model = sast_resolve_ollama_model(requested_model)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400

    report_id = uuid.uuid4().hex[:12]
    job_id = uuid.uuid4().hex

    SAST_JOBS[job_id] = {
        "status": "queued",
        "percent": 0,
        "message": "En cola…",
        "done": False,
        "error": None,
        "result": None,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }

    username = getattr(user, "username", None) or session.get("username") or "Seguridad de la Información"

    payload = {
        "project_name": project_name,
        "artifact_type": artifact_type,
        "filename": filename,
        "language": language,
        "code_text": code_text,
        "model": model,
        "report_id": report_id,
        "date_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "register_vulnerabilities": register_vulnerabilities,
        "create_remediation_plans": create_remediation_plans,
        "generate_ai_remediation": generate_ai_remediation,
        "username": username,
        "responsable": username,
    }

    t = threading.Thread(target=sast_run_analysis_job, args=(job_id, payload), daemon=True)
    t.start()

    return jsonify({"ok": True, "job_id": job_id})


@app.route("/pruebas_sast/track/<job_id>", methods=["GET"])
@login_required
def sast_track(job_id):
    user, resp, read_only = sast_require_access(write=False)
    if resp:
        return resp

    if job_id not in SAST_JOBS:
        flash("Job SAST no encontrado.", "warning")
        return redirect(url_for("sast_index"))

    inner = render_template_string(SAST_TRACK_HTML, job_id=job_id)
    return render_template_string(BASE, content=Markup(inner))


@app.route("/pruebas_sast/progress/<job_id>", methods=["GET"])
@login_required
def sast_progress(job_id):
    user, resp, read_only = sast_require_access(write=False)
    if resp:
        return resp

    def event_stream():
        last = None
        while True:
            job = SAST_JOBS.get(job_id)
            if not job:
                yield 'event: error\ndata: {"error":"Job no encontrado"}\n\n'
                break

            snapshot = json.dumps({
                "status": job.get("status"),
                "percent": job.get("percent"),
                "message": job.get("message"),
                "done": job.get("done"),
                "error": job.get("error"),
            }, ensure_ascii=False)

            if snapshot != last:
                yield f"data: {snapshot}\n\n"
                last = snapshot

            if job.get("done"):
                break

            time.sleep(0.4)

    return Response(event_stream(), mimetype="text/event-stream")


@app.route("/pruebas_sast/result/<job_id>", methods=["GET"])
@login_required
def sast_result(job_id):
    user, resp, read_only = sast_require_access(write=False)
    if resp:
        return resp

    job = SAST_JOBS.get(job_id)
    if not job:
        flash("Job SAST no encontrado.", "warning")
        return redirect(url_for("sast_index"))

    if job.get("status") == "error":
        flash(f"Error en análisis SAST: {job.get('error')}", "danger")
        return redirect(url_for("sast_index"))

    if not job.get("done") or not job.get("result"):
        flash("El análisis SAST aún no termina.", "warning")
        return redirect(url_for("sast_index"))

    res = job["result"]
    inner = render_template_string(
        SAST_RESULT_HTML,
        analysis=(res.get("analysis") or {}),
        pdf_name=res["pdf_name"],
        json_name=res["json_name"],
        meta=(res.get("meta") or {}),
        registration_summary=(res.get("registration_summary") or {}),
    )
    return render_template_string(BASE, content=Markup(inner))


@app.route("/pruebas_sast/download/pdf/<name>", methods=["GET"])
@login_required
def sast_download_pdf(name):
    user, resp, read_only = sast_require_access(write=False)
    if resp:
        return resp

    path = os.path.join(SAST_REPORT_DIR, sast_safe_filename(name))
    if not os.path.exists(path):
        flash("PDF SAST no encontrado.", "warning")
        return redirect(url_for("sast_index"))

    return send_file(path, as_attachment=True, download_name=os.path.basename(path), mimetype="application/pdf")


@app.route("/pruebas_sast/download/json/<name>", methods=["GET"])
@login_required
def sast_download_json(name):
    user, resp, read_only = sast_require_access(write=False)
    if resp:
        return resp

    path = os.path.join(SAST_REPORT_DIR, sast_safe_filename(name))
    if not os.path.exists(path):
        flash("JSON SAST no encontrado.", "warning")
        return redirect(url_for("sast_index"))

    return send_file(path, as_attachment=True, download_name=os.path.basename(path), mimetype="application/json")


# ============================================================================================================================================
#                                                   FIN MÓDULO PRUEBAS SAST - OLLAMA LOCAL
# ============================================================================
# SUPERFICIE DE ATAQUE Y ESCENARIOS
# Generación automática multi-fuente, IA opcional e histórico por períodos.
# Base independiente: instance/superficie_amenazas.db
# ============================================================================

ATTACK_AUTO_MODULE = "Superficie de Ataque y Escenarios"
ATTACK_AUTO_SOURCE_LABELS = {
    "MITRE": "MITRE ATT&CK",
    "VULNERABILIDAD": "Vulnerabilidades",
    "INCIDENTE": "Incidentes",
    "TPRM": "Cadena de suministro (TPRM)",
    "WAZUH_MITRE": "Wazuh + MITRE",
    "WAZUH_VULN": "Wazuh Vulnerabilidades",
    "FIREWALL": "Gobierno de Firewall",
    "ACTIVE_DIRECTORY": "Gobierno del Directorio Activo",
}


class AttackAutoScenario(db.Model):
    __bind_key__ = "attack_surface"
    __tablename__ = "attack_auto_scenarios"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), nullable=False, unique=True, index=True)
    source_type = db.Column(db.String(40), nullable=False, index=True)
    source_ref = db.Column(db.String(255), nullable=False)
    source_label = db.Column(db.String(255), nullable=True)
    source_date = db.Column(db.String(40), nullable=True)
    source_count = db.Column(db.Integer, nullable=False, default=1)
    source_snapshot = db.Column(db.Text, nullable=True)

    name = db.Column(db.String(500), nullable=False)
    asset_name = db.Column(db.String(255), nullable=True)
    asset_type = db.Column(db.String(120), nullable=True)
    scope = db.Column(db.Text, nullable=True)
    description = db.Column(db.Text, nullable=True)
    exposure_channel = db.Column(db.String(255), nullable=True)
    internet_exposed = db.Column(db.Boolean, nullable=False, default=False)
    threat_actor = db.Column(db.String(255), nullable=True)
    threat_event = db.Column(db.Text, nullable=True)
    vulnerability = db.Column(db.Text, nullable=True)
    consequences = db.Column(db.Text, nullable=True)
    security_dimensions = db.Column(db.String(120), nullable=True)
    existing_controls = db.Column(db.Text, nullable=True)
    control_weaknesses = db.Column(db.Text, nullable=True)
    evidence = db.Column(db.Text, nullable=True)
    severity = db.Column(db.String(20), nullable=False, default="Media")

    exposure_level = db.Column(db.Integer, nullable=False, default=3)
    exploitability = db.Column(db.Integer, nullable=False, default=3)
    detected_activity = db.Column(db.Integer, nullable=False, default=1)
    control_weakness_level = db.Column(db.Integer, nullable=False, default=3)
    asset_criticality = db.Column(db.Integer, nullable=False, default=3)
    inherent_probability = db.Column(db.Integer, nullable=False, default=3)
    inherent_impact = db.Column(db.Integer, nullable=False, default=3)
    inherent_score = db.Column(db.Integer, nullable=False, default=9)
    inherent_level = db.Column(db.String(20), nullable=False, default="Medio")
    control_effectiveness = db.Column(db.Integer, nullable=False, default=25)
    residual_probability = db.Column(db.Integer, nullable=False, default=2)
    residual_impact = db.Column(db.Integer, nullable=False, default=3)
    residual_score = db.Column(db.Integer, nullable=False, default=6)
    residual_level = db.Column(db.String(20), nullable=False, default="Medio")

    risk_appetite = db.Column(db.String(50), nullable=True, default="Fuera de apetito")
    treatment = db.Column(db.String(80), nullable=True, default="Mitigar")
    status = db.Column(db.String(50), nullable=False, default="En análisis", index=True)
    owner = db.Column(db.String(255), nullable=True)

    supplier_id = db.Column(db.Integer, nullable=True)
    supplier_name = db.Column(db.String(255), nullable=True)
    supplier_relationship = db.Column(db.String(255), nullable=True)
    supply_chain_details = db.Column(db.Text, nullable=True)

    risk_id = db.Column(db.Integer, nullable=True, index=True)
    risk_code = db.Column(db.String(50), nullable=True)
    manually_edited = db.Column(db.Boolean, nullable=False, default=False)
    ai_status = db.Column(db.String(40), nullable=False, default="No solicitado")
    ai_provider = db.Column(db.String(40), nullable=True)
    ai_justification = db.Column(db.Text, nullable=True)
    ai_enriched_at = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.String(120), nullable=True)
    generated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    techniques = db.relationship(
        "AttackAutoTechnique",
        backref="scenario",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="AttackAutoTechnique.id",
    )
    evaluations = db.relationship(
        "AttackAutoEvaluation",
        backref="scenario",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="AttackAutoEvaluation.period_start.desc()",
    )

    __table_args__ = (
        db.UniqueConstraint("source_type", "source_ref", name="uq_attack_auto_source"),
    )


class AttackAutoTechnique(db.Model):
    __bind_key__ = "attack_surface"
    __tablename__ = "attack_auto_techniques"

    id = db.Column(db.Integer, primary_key=True)
    scenario_id = db.Column(
        db.Integer,
        db.ForeignKey("attack_auto_scenarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    technique_id = db.Column(db.String(40), nullable=False)
    technique_name = db.Column(db.String(255), nullable=False)
    tactic_id = db.Column(db.String(40), nullable=True)
    tactic_name = db.Column(db.String(120), nullable=True)
    rationale = db.Column(db.Text, nullable=True)
    confidence = db.Column(db.Integer, nullable=False, default=60)
    origin = db.Column(db.String(30), nullable=False, default="Automático")

    __table_args__ = (
        db.UniqueConstraint("scenario_id", "technique_id", "tactic_id", name="uq_attack_auto_technique"),
    )


class AttackAutoEvaluation(db.Model):
    __bind_key__ = "attack_surface"
    __tablename__ = "attack_auto_evaluations"

    id = db.Column(db.Integer, primary_key=True)
    scenario_id = db.Column(
        db.Integer,
        db.ForeignKey("attack_auto_scenarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    period_start = db.Column(db.String(10), nullable=False)
    period_end = db.Column(db.String(10), nullable=False)
    evaluation_date = db.Column(db.String(10), nullable=False)
    evaluator = db.Column(db.String(255), nullable=True)
    methodology = db.Column(db.String(120), nullable=False, default="Matriz 5x5 GRAC")
    exposure_level = db.Column(db.Integer, nullable=False, default=3)
    exploitability = db.Column(db.Integer, nullable=False, default=3)
    detected_activity = db.Column(db.Integer, nullable=False, default=1)
    control_weakness_level = db.Column(db.Integer, nullable=False, default=3)
    asset_criticality = db.Column(db.Integer, nullable=False, default=3)
    inherent_probability = db.Column(db.Integer, nullable=False, default=3)
    inherent_impact = db.Column(db.Integer, nullable=False, default=3)
    inherent_score = db.Column(db.Integer, nullable=False, default=9)
    inherent_level = db.Column(db.String(20), nullable=False, default="Medio")
    control_effectiveness = db.Column(db.Integer, nullable=False, default=25)
    residual_probability = db.Column(db.Integer, nullable=False, default=2)
    residual_impact = db.Column(db.Integer, nullable=False, default=3)
    residual_score = db.Column(db.Integer, nullable=False, default=6)
    residual_level = db.Column(db.String(20), nullable=False, default="Medio")
    risk_appetite = db.Column(db.String(50), nullable=True)
    treatment = db.Column(db.String(80), nullable=True)
    justification = db.Column(db.Text, nullable=True)
    controls_reviewed = db.Column(db.Text, nullable=True)
    observations = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), nullable=False, default="Vigente")
    origin = db.Column(db.String(30), nullable=False, default="Manual")
    risk_id = db.Column(db.Integer, nullable=True)
    risk_code = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("scenario_id", "period_start", "period_end", name="uq_attack_auto_period"),
    )


class AttackAutoGenerationLog(db.Model):
    __bind_key__ = "attack_surface"
    __tablename__ = "attack_auto_generation_logs"

    id = db.Column(db.Integer, primary_key=True)
    started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    finished_at = db.Column(db.DateTime, nullable=True)
    executed_by = db.Column(db.String(120), nullable=True)
    status = db.Column(db.String(40), nullable=False, default="En proceso")
    created_count = db.Column(db.Integer, nullable=False, default=0)
    updated_count = db.Column(db.Integer, nullable=False, default=0)
    unchanged_count = db.Column(db.Integer, nullable=False, default=0)
    ai_enriched_count = db.Column(db.Integer, nullable=False, default=0)
    error_count = db.Column(db.Integer, nullable=False, default=0)
    source_counts = db.Column(db.Text, nullable=True)
    error_detail = db.Column(db.Text, nullable=True)


def ensure_attack_auto_db():
    """Crea solamente las tablas del módulo en su base SQLite independiente."""
    os.makedirs(app.instance_path, exist_ok=True)
    db.create_all(bind_key="attack_surface")


def attack_auto_user():
    return User.query.get(session.get("user_id"))


def attack_auto_guard(write=False):
    user = attack_auto_user()
    if not user:
        flash("No fue posible identificar el usuario autenticado.", "danger")
        return None, redirect(url_for("login"))
    if not verificar_permiso(user, ATTACK_AUTO_MODULE):
        flash("No tiene permiso para acceder a Superficie de Ataque y Escenarios.", "danger")
        return user, redirect(url_for("menu"))
    if write and auditor_is_read_only(user):
        flash("El rol Auditor tiene acceso de solo lectura.", "warning")
        return user, redirect(url_for("attack_auto"))
    return user, None


def attack_auto_clamp(value, minimum=1, maximum=5, default=3):
    try:
        return max(minimum, min(maximum, int(float(value))))
    except Exception:
        return default


def attack_auto_yes(value):
    return str(value or "").strip().lower() in {"1", "true", "sí", "si", "yes", "s", "on"}


def attack_auto_clean(value, limit=None):
    text_value = re.sub(r"\s+", " ", str(value or "")).strip()
    return text_value[:limit] if limit else text_value


def attack_auto_normalize_severity(value):
    text_value = tm_normalize_text(value or "")
    if any(x in text_value for x in ("critical", "critica", "critico", "urgent")):
        return "Crítica"
    if any(x in text_value for x in ("high", "alta", "alto")):
        return "Alta"
    if any(x in text_value for x in ("low", "baja", "bajo")):
        return "Baja"
    return "Media"


def attack_auto_level(score):
    score = int(score or 0)
    if score >= 17:
        return "Crítico"
    if score >= 10:
        return "Alto"
    if score >= 5:
        return "Medio"
    return "Bajo"


def attack_auto_score_from_severity(value):
    return {"Crítica": 5, "Alta": 4, "Media": 3, "Baja": 2}.get(
        attack_auto_normalize_severity(value), 3
    )


def attack_auto_factor_values(record):
    severity_factor = attack_auto_score_from_severity(record.get("severity"))
    source_type = record.get("source_type")
    internet = bool(record.get("internet_exposed"))
    detected_default = 5 if source_type in {"INCIDENTE", "WAZUH_MITRE"} else 2
    exposure_default = 5 if internet else (4 if source_type in {"FIREWALL", "TPRM", "ACTIVE_DIRECTORY"} else 3)
    exploit_default = max(2, severity_factor)
    weakness_default = max(2, severity_factor)
    criticality_default = max(3, severity_factor)
    control_default = int(record.get("control_effectiveness") or 25)

    exposure = attack_auto_clamp(record.get("exposure_level"), default=exposure_default)
    exploitability = attack_auto_clamp(record.get("exploitability"), default=exploit_default)
    detected = attack_auto_clamp(record.get("detected_activity"), default=detected_default)
    weakness = attack_auto_clamp(record.get("control_weakness_level"), default=weakness_default)
    criticality = attack_auto_clamp(record.get("asset_criticality"), default=criticality_default)
    effectiveness = max(0, min(100, control_default))
    probability = attack_auto_clamp(round((exposure + exploitability + detected + weakness) / 4), default=3)
    impact = attack_auto_clamp(round((criticality + severity_factor) / 2), default=3)
    inherent_score = probability * impact
    residual_probability = attack_auto_clamp(round(probability * (1 - effectiveness / 125)), default=probability)
    residual_impact = attack_auto_clamp(round(impact * (1 - effectiveness / 200)), default=impact)
    residual_score = residual_probability * residual_impact

    return {
        "exposure_level": exposure,
        "exploitability": exploitability,
        "detected_activity": detected,
        "control_weakness_level": weakness,
        "asset_criticality": criticality,
        "inherent_probability": probability,
        "inherent_impact": impact,
        "inherent_score": inherent_score,
        "inherent_level": attack_auto_level(inherent_score),
        "control_effectiveness": effectiveness,
        "residual_probability": residual_probability,
        "residual_impact": residual_impact,
        "residual_score": residual_score,
        "residual_level": attack_auto_level(residual_score),
    }


def attack_auto_mitre_map(title, description, evidence, severity, cve="", service=""):
    mappings = tm_map_finding_to_mitre({
        "titulo": title or "",
        "descripcion": description or "",
        "evidencia": evidence or "",
        "recomendacion_base": "",
        "servicio": service or "",
        "severidad": severity or "",
        "cve": cve or "",
    })
    return [{
        "technique_id": item.get("technique_id") or "T1190",
        "technique_name": item.get("technique_name") or "Exploit Public-Facing Application",
        "tactic_id": item.get("tactic_id") or "TA0001",
        "tactic_name": item.get("tactic_name") or "Initial Access",
        "rationale": item.get("rationale") or "Correlación automática con MITRE ATT&CK",
        "confidence": int(item.get("confidence") or item.get("score") or 60),
    } for item in mappings]


def attack_auto_default_technique():
    return [{
        "technique_id": "T1190",
        "technique_name": "Exploit Public-Facing Application",
        "tactic_id": "TA0001",
        "tactic_name": "Initial Access",
        "rationale": "Mapeo preventivo pendiente de validación por el analista.",
        "confidence": 40,
    }]


def attack_auto_base_record(source_type, source_ref, name, asset_name, severity):
    return {
        "source_type": source_type,
        "source_ref": str(source_ref),
        "source_label": ATTACK_AUTO_SOURCE_LABELS.get(source_type, source_type),
        "source_count": 1,
        "name": attack_auto_clean(name, 500) or "Escenario de amenaza",
        "asset_name": attack_auto_clean(asset_name, 255) or "Activo no especificado",
        "asset_type": "Activo de información",
        "scope": "Alcance derivado automáticamente de la evidencia registrada.",
        "description": "",
        "exposure_channel": "Canal por validar",
        "internet_exposed": False,
        "threat_actor": "Actor de amenaza externo o interno por determinar",
        "threat_event": attack_auto_clean(name),
        "vulnerability": "Debilidad pendiente de validación",
        "consequences": "Afectación potencial de la confidencialidad, integridad o disponibilidad.",
        "security_dimensions": "Confidencialidad, Integridad, Disponibilidad",
        "existing_controls": "Controles existentes pendientes de validar",
        "control_weaknesses": "Efectividad de controles pendiente de validar",
        "evidence": "",
        "severity": attack_auto_normalize_severity(severity),
        "risk_appetite": "Fuera de apetito" if attack_auto_score_from_severity(severity) >= 4 else "Por evaluar",
        "treatment": "Mitigar",
        "status": "En análisis",
        "techniques": [],
    }


def attack_auto_collect_threat_models():
    records = []
    for entry in ThreatModelEntry.query.order_by(ThreatModelEntry.id.asc()).all():
        # Active Directory and Gobierno de Firewall have richer dedicated
        # collectors. Skipping their mirrored MITRE entries prevents duplicates.
        mirrored_sources = {THREAT_MODEL_AD_SOURCE, THREAT_MODEL_FIREWALL_SOURCE}
        if (entry.herramienta or "").strip().lower() in mirrored_sources:
            continue
        record = attack_auto_base_record(
            "MITRE", entry.id,
            "Explotación de {} en {}".format(entry.vulnerabilidad, entry.activo),
            entry.activo, entry.severidad,
        )
        record.update({
            "source_date": (entry.updated_at or entry.created_at or datetime.utcnow()).isoformat(),
            "asset_type": "Activo tecnológico",
            "description": entry.descripcion or entry.vulnerabilidad,
            "exposure_channel": entry.herramienta or "Modelamiento de amenazas",
            "internet_exposed": any(x in tm_normalize_text(entry.herramienta, entry.descripcion) for x in ("nikto", "nuclei", "web", "http", "extern")),
            "threat_event": "Uso de técnicas MITRE ATT&CK para explotar {}".format(entry.vulnerabilidad),
            "vulnerability": entry.vulnerabilidad,
            "consequences": entry.impacto or "Compromiso potencial del activo identificado.",
            "evidence": "Modelamiento MITRE #{}; herramienta {}; confianza {}%.".format(entry.id, entry.herramienta or "N/D", entry.confianza or 0),
            "source_snapshot": json.dumps({"entry_id": entry.id, "tool": entry.herramienta, "severity": entry.severidad}, ensure_ascii=False),
        })
        record["techniques"] = [{
            "technique_id": tech.mitre_technique_id,
            "technique_name": tech.mitre_technique_name,
            "tactic_id": tech.mitre_tactic_id,
            "tactic_name": tech.mitre_tactic_name,
            "rationale": tech.rationale or "Mapeo registrado en Modelamiento de Amenazas",
            "confidence": int(tech.score or entry.confianza or 60),
        } for tech in entry.tecnicas]
        if not record["techniques"]:
            record["techniques"] = attack_auto_mitre_map(entry.vulnerabilidad, entry.descripcion, "", entry.severidad)
        records.append(record)
    return records


def attack_auto_collect_vulnerabilities():
    mapped_ids = {
        row[0] for row in db.session.query(ThreatModelEntry.vulnerabilidad_registro_id).filter(
            ThreatModelEntry.vulnerabilidad_registro_id.isnot(None)
        ).all()
    }
    records = []
    for vuln in VulnerabilidadRegistro.query.order_by(VulnerabilidadRegistro.id.asc()).all():
        if vuln.id in mapped_ids:
            continue
        severity = "Media"
        try:
            cvss = float(str(vuln.cvss or "0").replace(",", "."))
            severity = "Crítica" if cvss >= 9 else "Alta" if cvss >= 7 else "Media" if cvss >= 4 else "Baja"
        except Exception:
            pass
        record = attack_auto_base_record(
            "VULNERABILIDAD", vuln.id,
            "Explotación de vulnerabilidad {} sobre {}".format(vuln.codigo, vuln.activo),
            vuln.activo, severity,
        )
        is_closed = tm_normalize_text(vuln.estado) in {"cerrado", "cerrada", "resuelto", "resuelta"}
        record.update({
            "source_date": str(vuln.fecha_identificacion or ""),
            "description": vuln.descripcion_vulnerabilidad,
            "vulnerability": "{}{}".format(vuln.descripcion_vulnerabilidad, " / " + vuln.cve if vuln.cve else ""),
            "threat_event": "Explotación de la vulnerabilidad registrada {}".format(vuln.codigo),
            "existing_controls": vuln.riesgo_residual or "Plan de remediación y controles técnicos por confirmar",
            "control_weaknesses": "Vulnerabilidad cerrada, validar eficacia" if is_closed else "Vulnerabilidad abierta o tratamiento pendiente",
            "control_effectiveness": 70 if is_closed else 20,
            "owner": vuln.responsable,
            "evidence": "Vulnerabilidad #{}; código {}; CVE {}; CVSS {}; estado {}.".format(vuln.id, vuln.codigo, vuln.cve or "N/D", vuln.cvss or "N/D", vuln.estado),
            "source_snapshot": json.dumps({"id": vuln.id, "code": vuln.codigo, "cve": vuln.cve, "state": vuln.estado}, ensure_ascii=False),
        })
        record["techniques"] = attack_auto_mitre_map(
            vuln.descripcion_vulnerabilidad, vuln.descripcion_vulnerabilidad,
            record["evidence"], severity, vuln.cve,
        ) or attack_auto_default_technique()
        records.append(record)
    return records


def attack_auto_collect_incidents():
    records = []
    conn = get_incidentes_db_connection()
    try:
        rows = conn.execute("SELECT * FROM registro_incidentes ORDER BY id ASC").fetchall()
        for row in rows:
            item = dict(row)
            priority = item.get("prioridad") or item.get("clasificacion_incidente") or "Media"
            asset = item.get("nombre_recurso_id") or "Recurso afectado no especificado"
            title = item.get("nombre_alerta") or item.get("id_incidente") or "Incidente de seguridad"
            record = attack_auto_base_record("INCIDENTE", item.get("id"), "Escenario observado: {}".format(title), asset, priority)
            closed = tm_normalize_text(item.get("estado")) in {"cerrado", "cerrada", "resuelto", "resuelta"}
            record.update({
                "source_date": item.get("fecha_alerta") or "",
                "asset_type": item.get("tipo_recurso_afectado") or "Activo afectado por incidente",
                "description": item.get("descripcion_alerta") or title,
                "exposure_channel": item.get("ubicacion_atacante") or "Canal evidenciado en incidente",
                "internet_exposed": bool(item.get("ubicacion_atacante") or item.get("atacante")),
                "threat_actor": item.get("atacante") or "Actor observado no identificado",
                "threat_event": title,
                "vulnerability": item.get("descripcion_alerta") or "Condición que permitió el incidente por determinar",
                "consequences": item.get("descripcion_cierre") or "Impacto evidenciado en el incidente y posible recurrencia.",
                "security_dimensions": item.get("principio") or "Confidencialidad, Integridad, Disponibilidad",
                "existing_controls": "; ".join(filter(None, [item.get("descripcion_contencion"), item.get("descripcion_recuperacion")])) or "Contención y recuperación pendientes de documentar",
                "control_weaknesses": "Validar causa raíz y prevención de recurrencia",
                "control_effectiveness": 65 if closed else 20,
                "detected_activity": 5,
                "owner": item.get("cargo_responsable"),
                "evidence": "Incidente interno {}; estado {}; clasificación {}; fecha {}.".format(item.get("id_incidente") or item.get("id"), item.get("estado") or "N/D", item.get("clasificacion_incidente") or "N/D", item.get("fecha_alerta") or "N/D"),
                "source_snapshot": json.dumps({"id": item.get("id"), "incident": item.get("id_incidente"), "state": item.get("estado")}, ensure_ascii=False),
            })
            record["techniques"] = attack_auto_mitre_map(title, item.get("descripcion_alerta"), record["evidence"], priority) or attack_auto_default_technique()
            records.append(record)
    finally:
        conn.close()
    return records


def attack_auto_collect_tprm():
    records = []
    for supplier in ProveedorEvaluacion.query.order_by(ProveedorEvaluacion.id.asc()).all():
        criticality = int(supplier.criticidad_pct or 0)
        severity = "Crítica" if criticality >= 76 else "Alta" if criticality >= 51 else "Media" if criticality >= 26 else "Baja"
        service = supplier.desc_producto_servicio or "servicio contratado"
        record = attack_auto_base_record(
            "TPRM", supplier.id,
            "Compromiso de cadena de suministro a través de {}".format(supplier.nombre_proveedor or "proveedor"),
            supplier.nombre_proveedor or "Proveedor no especificado", severity,
        )
        approved = tm_normalize_text(supplier.resultado_evaluacion) in {"aprobado", "aprobada"}
        gaps = []
        if not attack_auto_yes(supplier.tiene_plan_cont): gaps.append("sin plan de continuidad confirmado")
        if not attack_auto_yes(supplier.tiene_plan_rec): gaps.append("sin plan de recuperación confirmado")
        if not attack_auto_yes(supplier.existen_alternativas): gaps.append("sin proveedor alternativo confirmado")
        if not attack_auto_yes(supplier.existe_plan_migracion): gaps.append("sin plan de migración confirmado")
        record.update({
            "source_date": supplier.fecha_eval_seguridad or "",
            "asset_type": "Tercero / Cadena de suministro",
            "scope": "Servicio de tercero: {}. País origen: {}. País servicio: {}.".format(service, supplier.pais_origen or "N/D", supplier.pais_servicio or "N/D"),
            "description": "Un compromiso, indisponibilidad o acceso indebido en el proveedor puede propagarse al entorno de la organización.",
            "exposure_channel": "Relación de confianza y servicio de tercero",
            "internet_exposed": bool(attack_auto_yes(supplier.procesa_info_nube) or attack_auto_yes(supplier.procesa_info_sensible)),
            "threat_actor": "Atacante de la cadena de suministro o personal del tercero",
            "threat_event": "Compromiso del proveedor, de sus accesos o de la entrega del servicio",
            "vulnerability": "; ".join(gaps) or "Dependencia y relación de confianza con el tercero",
            "consequences": "Interrupción del servicio, exposición de información y propagación del compromiso a la organización.",
            "existing_controls": "Evaluación TPRM: {}; resultado: {}; certificaciones: {}.".format(supplier.estado_evaluacion or "N/D", supplier.resultado_evaluacion or "N/D", supplier.nombre_certificaciones or "N/D"),
            "control_weaknesses": "; ".join(gaps) or "Validar periódicamente controles contractuales, técnicos y de continuidad",
            "control_effectiveness": 70 if approved else 35,
            "asset_criticality": 5 if criticality >= 76 else 4 if criticality >= 51 else 3,
            "owner": supplier.responsable_area_nombre or supplier.nombre_cargo_evaluador,
            "supplier_id": supplier.id,
            "supplier_name": supplier.nombre_proveedor,
            "supplier_relationship": service,
            "supply_chain_details": supplier.observaciones or "Escenario TPRM generado desde la evaluación del proveedor.",
            "evidence": "TPRM #{}; criticidad {}% ({}); evaluación {}; estado {}.".format(supplier.id, criticality, supplier.criticidad_texto or "N/D", supplier.resultado_evaluacion or "N/D", supplier.estatus_proveedor or "N/D"),
            "source_snapshot": json.dumps({"id": supplier.id, "criticality": criticality, "result": supplier.resultado_evaluacion}, ensure_ascii=False),
            "techniques": [
                {"technique_id": "T1195", "technique_name": "Supply Chain Compromise", "tactic_id": "TA0001", "tactic_name": "Initial Access", "rationale": "Escenario generado desde una relación de cadena de suministro.", "confidence": 90},
                {"technique_id": "T1199", "technique_name": "Trusted Relationship", "tactic_id": "TA0001", "tactic_name": "Initial Access", "rationale": "El proveedor mantiene una relación de confianza o presta un servicio a la organización.", "confidence": 85},
            ],
        })
        records.append(record)
    return records


def attack_auto_collect_wazuh_mitre():
    grouped = {}
    for event in WazuhMitreEvent.query.order_by(WazuhMitreEvent.id.asc()).all():
        key = "{}|{}".format(event.agent_id or event.agent_name or "sin-agente", event.technique_id or event.technique or "sin-tecnica")
        group = grouped.setdefault(key, {"events": [], "max_level": 0, "last": None})
        group["events"].append(event)
        group["max_level"] = max(group["max_level"], int(event.rule_level or 0))
        group["last"] = event
    records = []
    for key, group in grouped.items():
        event = group["last"]
        severity = "Crítica" if group["max_level"] >= 13 else "Alta" if group["max_level"] >= 10 else "Media"
        record = attack_auto_base_record("WAZUH_MITRE", key, "Actividad MITRE {} detectada en {}".format(event.technique_id or event.technique or "N/D", event.agent_name or event.agent_id or "agente"), event.agent_name or event.agent_id, severity)
        record.update({
            "source_date": event.timestamp or "",
            "source_count": len(group["events"]),
            "asset_type": "Endpoint monitoreado por Wazuh",
            "description": event.description or "Actividad correlacionada con MITRE ATT&CK en Wazuh.",
            "exposure_channel": "Telemetría Wazuh",
            "threat_event": event.description or event.technique or "Actividad adversaria detectada",
            "vulnerability": "Condición de exposición o control a investigar a partir de la alerta",
            "consequences": "Posible progresión del atacante en la cadena MITRE ATT&CK.",
            "existing_controls": "Monitoreo y detección Wazuh",
            "control_weaknesses": "La actividad fue observada; validar contención, causa raíz y cobertura preventiva",
            "detected_activity": 5,
            "control_effectiveness": 35,
            "evidence": "{} evento(s) Wazuh; nivel máximo {}; última observación {}.".format(len(group["events"]), group["max_level"], event.timestamp or "N/D"),
            "source_snapshot": json.dumps({"key": key, "count": len(group["events"]), "max_level": group["max_level"]}, ensure_ascii=False),
            "techniques": [{"technique_id": event.technique_id or "MITRE-PENDIENTE", "technique_name": event.technique or "Técnica detectada por Wazuh", "tactic_id": "", "tactic_name": event.tactic or "Táctica MITRE", "rationale": "Técnica reportada directamente por la telemetría Wazuh.", "confidence": 95}],
        })
        records.append(record)
    return records


def attack_auto_collect_wazuh_vulnerabilities():
    records = []
    for vuln in WazuhVulnerability.query.order_by(WazuhVulnerability.id.asc()).all():
        severity = attack_auto_normalize_severity(vuln.severity)
        if severity not in {"Crítica", "Alta"}:
            continue
        ref = vuln.unique_key or vuln.id
        record = attack_auto_base_record("WAZUH_VULN", ref, "Explotación de {} en {}".format(vuln.cve or vuln.title or "vulnerabilidad", vuln.agent_name or vuln.agent_id or "agente"), vuln.agent_name or vuln.agent_id, severity)
        closed = tm_normalize_text(vuln.status) in {"cerrado", "cerrada", "resuelto", "resuelta", "solved"}
        record.update({
            "source_date": vuln.synced_at.isoformat() if vuln.synced_at else "",
            "asset_type": "Endpoint monitoreado por Wazuh",
            "description": vuln.title or vuln.condition or vuln.cve,
            "exposure_channel": "Paquete {} {}".format(vuln.package_name or "N/D", vuln.package_version or ""),
            "threat_event": "Explotación de vulnerabilidad crítica/alta detectada por Wazuh",
            "vulnerability": "{} - {}".format(vuln.cve or "CVE N/D", vuln.title or vuln.condition or "Vulnerabilidad"),
            "existing_controls": "Agente Wazuh y gestión de vulnerabilidades",
            "control_weaknesses": "Vulnerabilidad cerrada; verificar parche" if closed else "Parcheo o mitigación pendiente",
            "control_effectiveness": 70 if closed else 20,
            "evidence": "Wazuh vuln #{}; CVE {}; CVSS {}; paquete {}; estado {}.".format(vuln.id, vuln.cve or "N/D", vuln.cvss or "N/D", vuln.package_name or "N/D", vuln.status or "N/D"),
            "source_snapshot": json.dumps({"id": vuln.id, "cve": vuln.cve, "state": vuln.status}, ensure_ascii=False),
        })
        record["techniques"] = attack_auto_mitre_map(vuln.title, vuln.condition, record["evidence"], severity, vuln.cve, vuln.package_name) or attack_auto_default_technique()
        records.append(record)
    return records


def attack_auto_collect_firewall():
    records = []
    devices = {item.id: item for item in FirewallGovDevice.query.all()}
    for finding in FirewallGovFinding.query.filter_by(active=True).order_by(FirewallGovFinding.id.asc()).all():
        device = devices.get(finding.device_id)
        asset = device.name if device else "Firewall #{}".format(finding.device_id)
        record = attack_auto_base_record("FIREWALL", finding.id, "Explotación de exposición de firewall: {}".format(finding.title), asset, finding.severity)
        record.update({
            "source_date": (finding.last_detected_at or finding.first_detected_at or datetime.utcnow()).isoformat(),
            "asset_type": "Firewall / Perímetro",
            "description": finding.description or finding.title,
            "exposure_channel": finding.rule_name or finding.rule_external_id or "Regla de firewall",
            "internet_exposed": True,
            "threat_event": "Aprovechamiento de configuración o regla de firewall expuesta",
            "vulnerability": finding.title,
            "consequences": finding.technical_detail or "Acceso no autorizado, movimiento lateral o exposición del perímetro.",
            "existing_controls": finding.control_mapping or "Firewall y revisión de reglas",
            "control_weaknesses": finding.recommendation or "Corregir el hallazgo de gobierno de firewall",
            "control_effectiveness": 20 if tm_normalize_text(finding.status) not in {"resuelto", "cerrado"} else 70,
            "owner": finding.assigned_to,
            "evidence": "Hallazgo firewall #{}; código {}; regla {}; puntaje {}; estado {}.".format(finding.id, finding.finding_code, finding.rule_external_id or "N/D", finding.risk_score or 0, finding.status),
            "source_snapshot": json.dumps({"id": finding.id, "code": finding.finding_code, "state": finding.status}, ensure_ascii=False),
        })
        record["techniques"] = attack_auto_mitre_map(finding.title, finding.description, finding.technical_detail, finding.severity, service=finding.rule_name) or attack_auto_default_technique()
        records.append(record)
    return records


def attack_auto_collect_active_directory():
    """Convierte los hallazgos de Gobierno del Directorio Activo en escenarios trazables."""
    ad_db_path = os.path.join(app.instance_path, "ad_governance.db")
    if not os.path.exists(ad_db_path):
        return []

    conn = sqlite3.connect(ad_db_path, timeout=20)
    conn.row_factory = sqlite3.Row
    try:
        table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ad_findings'"
        ).fetchone()
        if not table_exists:
            return []
        rows = conn.execute(
            """
            SELECT f.id,f.connector_id,f.finding_key,f.finding_code,f.severity,f.title,
                   f.description,f.recommendation,f.control_mapping,f.status,f.assigned_to,
                   f.management_comment,f.first_detected_at,f.last_detected_at,f.resolved_at,
                   c.name connector_name,c.host connector_host,c.platform connector_platform,
                   u.sam_account_name,u.display_name,u.department,u.title account_title,
                   u.privilege_path,u.enabled,u.privileged,u.service_account,u.generic_account
              FROM ad_findings f
              JOIN ad_connectors c ON c.id=f.connector_id
              LEFT JOIN ad_users u ON u.id=f.user_id
             WHERE f.active=1
             ORDER BY f.id ASC
            """
        ).fetchall()
    except sqlite3.Error:
        return []
    finally:
        conn.close()

    records = []
    for row in rows:
        status_text = tm_normalize_text(row["status"])
        closed = status_text in {
            "resuelto", "resuelto automaticamente", "descartado", "falso positivo"
        }
        in_treatment = status_text in {"en tratamiento", "riesgo aceptado"}
        account = row["sam_account_name"] or row["display_name"] or row["connector_name"] or "Directorio corporativo"
        privilege_path = row["privilege_path"] or "No identificada"
        severity = attack_auto_normalize_severity(row["severity"])
        source_ref = "AD:{}".format(row["id"])
        connector_platform = str(row["connector_platform"] or "SAMBA").upper()
        connector_platform_label = (
            "Microsoft Active Directory Windows"
            if connector_platform == "WINDOWS"
            else "Active Directory Samba"
        )

        record = attack_auto_base_record(
            "ACTIVE_DIRECTORY",
            source_ref,
            "Abuso o compromiso de identidad por {}".format(row["title"]),
            account,
            severity,
        )
        record.update({
            "source_label": "Gobierno del Directorio Activo · {}".format(connector_platform_label),
            "ad_connector_id": int(row["connector_id"] or 0),
            "ad_platform": connector_platform,
            "source_date": row["last_detected_at"] or row["first_detected_at"] or "",
            "asset_type": "Identidad / {}".format(connector_platform_label),
            "scope": "Tecnología: {}. Conector: {} ({}). Área: {}. Cargo: {}. Ruta de privilegio: {}.".format(
                connector_platform_label, row["connector_name"] or "N/D", row["connector_host"] or "N/D",
                row["department"] or "N/D", row["account_title"] or "N/D", privilege_path,
            ),
            "description": row["description"] or row["title"],
            "exposure_channel": "Active Directory / LDAP / Kerberos",
            "internet_exposed": False,
            "threat_actor": "Atacante interno, cuenta comprometida o actor con credenciales válidas",
            "threat_event": "Uso indebido, compromiso o escalamiento de privilegios sobre una identidad del directorio",
            "vulnerability": "{}: {}".format(row["finding_code"], row["description"] or row["title"]),
            "consequences": "Acceso no autorizado, persistencia, escalamiento de privilegios, movimiento lateral y afectación de información o servicios corporativos.",
            "security_dimensions": "Confidencialidad, Integridad, Disponibilidad",
            "existing_controls": row["control_mapping"] or "Gobierno de identidades, autenticación y revisión de accesos",
            "control_weaknesses": row["recommendation"] or "Corregir el hallazgo de gobierno de identidad y validar la evidencia de cierre",
            "control_effectiveness": 85 if closed else 45 if in_treatment else 20,
            "asset_criticality": 5 if severity in {"Crítica", "Alta"} else 3,
            "owner": row["assigned_to"],
            "evidence": "Hallazgo AD #{}; tecnología {}; código {}; cuenta {}; conector {}; estado {}; última detección {}.".format(
                row["id"], connector_platform_label, row["finding_code"], account, row["connector_name"] or "N/D",
                row["status"] or "N/D", row["last_detected_at"] or "N/D",
            ),
            "source_snapshot": json.dumps({
                "finding_id": row["id"],
                "finding_code": row["finding_code"],
                "finding_key": row["finding_key"],
                "connector_id": row["connector_id"],
                "connector": row["connector_name"],
                "platform": connector_platform,
                "platform_label": connector_platform_label,
                "account": account,
                "status": row["status"],
                "management_comment": row["management_comment"],
            }, ensure_ascii=False),
            "status": "Cerrado" if closed else "En tratamiento" if in_treatment else "En análisis",
            "techniques": [
                {
                    "technique_id": "T1078.002",
                    "technique_name": "Valid Accounts: Domain Accounts",
                    "tactic_id": "TA0001",
                    "tactic_name": "Initial Access",
                    "rationale": "Los hallazgos de cuentas y credenciales de Active Directory pueden facilitar el uso de identidades de dominio válidas.",
                    "confidence": 92,
                },
                {
                    "technique_id": "T1098",
                    "technique_name": "Account Manipulation",
                    "tactic_id": "TA0003",
                    "tactic_name": "Persistence",
                    "rationale": "La debilidad de gobierno de identidades puede permitir persistencia mediante cambios de cuentas, grupos o privilegios.",
                    "confidence": 82,
                },
            ],
        })
        records.append(record)
    return records


def attack_auto_sync_active_directory_scenarios(username="Sistema", connector_id=None, platform=None):
    """Crea o actualiza inmediatamente escenarios desde los hallazgos AD activos."""
    ensure_attack_auto_db()
    platform = str(platform or "").strip().upper()
    if platform not in {"SAMBA", "WINDOWS"}:
        platform = ""

    selected = []
    for record in attack_auto_collect_active_directory():
        record_connector_id = int(record.get("ad_connector_id") or 0)
        record_platform = str(record.get("ad_platform") or "").strip().upper()
        if connector_id is not None and record_connector_id != int(connector_id):
            continue
        if platform and record_platform != platform:
            continue
        selected.append(record)

    counts = {"created": 0, "updated": 0, "unchanged": 0, "closed": 0, "total": len(selected)}
    active_refs = {str(record.get("source_ref")) for record in selected}

    try:
        for record in selected:
            _, result, _ = attack_auto_upsert_record(
                record,
                username or "Sistema",
                use_ai=False,
                ai_budget=[0],
            )
            counts[result] = counts.get(result, 0) + 1

        # Cierra escenarios cuya evidencia AD ya no está activa para el conector/plataforma sincronizado.
        for scenario in AttackAutoScenario.query.filter_by(source_type="ACTIVE_DIRECTORY").all():
            try:
                snapshot = json.loads(scenario.source_snapshot or "{}")
            except Exception:
                snapshot = {}
            scenario_connector = int(snapshot.get("connector_id") or 0)
            scenario_platform = str(snapshot.get("platform") or "").strip().upper()
            if connector_id is not None and scenario_connector != int(connector_id):
                continue
            if platform and scenario_platform != platform:
                continue
            if scenario.source_ref not in active_refs and scenario.status != "Cerrado":
                scenario.status = "Cerrado"
                scenario.updated_at = datetime.utcnow()
                counts["closed"] += 1

        db.session.commit()
        return counts
    except Exception:
        db.session.rollback()
        raise


ATTACK_AUTO_COLLECTORS = (
    ("MITRE", attack_auto_collect_threat_models),
    ("VULNERABILIDAD", attack_auto_collect_vulnerabilities),
    ("INCIDENTE", attack_auto_collect_incidents),
    ("TPRM", attack_auto_collect_tprm),
    ("WAZUH_MITRE", attack_auto_collect_wazuh_mitre),
    ("WAZUH_VULN", attack_auto_collect_wazuh_vulnerabilities),
    ("FIREWALL", attack_auto_collect_firewall),
    ("ACTIVE_DIRECTORY", attack_auto_collect_active_directory),
)


def attack_auto_extract_json(text_value):
    raw = str(text_value or "").strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.I)
    raw = re.sub(r"\s*```$", "", raw)
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("La IA no devolvió un objeto JSON válido")
    return json.loads(raw[start:end + 1])


def attack_auto_ai_enrich(record):
    """
    La IA enriquece la narrativa y la correlación. Nunca decide ni modifica
    los factores o puntajes de riesgo, que permanecen determinísticos.
    """
    compact = {
        "fuente": record.get("source_label"),
        "activo": record.get("asset_name"),
        "tipo_activo": record.get("asset_type"),
        "evento": record.get("threat_event"),
        "vulnerabilidad": record.get("vulnerability"),
        "evidencia_resumida": attack_auto_clean(record.get("evidence"), 1200),
        "controles": attack_auto_clean(record.get("existing_controls"), 800),
        "debilidades_control": attack_auto_clean(record.get("control_weaknesses"), 800),
        "mitre": [
            "{} {} / {}".format(t.get("technique_id"), t.get("technique_name"), t.get("tactic_name"))
            for t in (record.get("techniques") or [])[:8]
        ],
    }
    prompt = """
Analiza este resumen técnico de un escenario de amenaza para una aplicación GRAC.
Devuelve EXCLUSIVAMENTE JSON válido con estas cinco claves de texto:
description, threat_actor, consequences, control_weaknesses, justification.
No inventes activos, incidentes, CVE ni controles. Distingue evidencia de hipótesis.
La justificación debe explicar la correlación entre fuente, activo y MITRE ATT&CK.
No calcules probabilidad, impacto ni nivel de riesgo.

DATOS:
{}
""".format(json.dumps(compact, ensure_ascii=False))
    response = ai_text_general(
        prompt,
        system_prompt="Eres analista senior de ciberseguridad, MITRE ATT&CK, TPRM y gestión de riesgos ISO 27005.",
        temperature=0.1,
        max_tokens=350,
    )
    data = attack_auto_extract_json(response)
    allowed = ("description", "threat_actor", "consequences", "control_weaknesses", "justification")
    result = {key: attack_auto_clean(data.get(key), 4000) for key in allowed}
    if not any(result.values()):
        raise ValueError("La IA no entregó contenido utilizable")
    return result


def attack_auto_code_for(source_type, source_ref):
    digest = hashlib.sha1("{}:{}".format(source_type, source_ref).encode("utf-8")).hexdigest()[:8].upper()
    prefix = {
        "MITRE": "MIT", "VULNERABILIDAD": "VUL", "INCIDENTE": "INC",
        "TPRM": "TPR", "WAZUH_MITRE": "WMI", "WAZUH_VULN": "WVU",
        "FIREWALL": "FW", "ACTIVE_DIRECTORY": "AD",
    }.get(source_type, "ESC")
    return "ESC-{}-{}".format(prefix, digest)


def attack_auto_replace_techniques(scenario, techniques):
    """
    Sincroniza técnicas automáticas sin borrar y volver a insertar las que ya
    existen. Así se evita violar la restricción única:
    escenario + técnica + táctica.
    Las técnicas validadas manualmente siempre se preservan.
    """
    manual_keys = set()
    automatic_by_key = {}
    duplicate_automatic = []

    for item in list(scenario.techniques):
        key = (
            attack_auto_clean(item.technique_id, 40),
            attack_auto_clean(item.tactic_id, 40),
        )
        if not key[0]:
            db.session.delete(item)
            continue

        if item.origin == "Manual":
            manual_keys.add(key)
            continue

        if key in automatic_by_key:
            duplicate_automatic.append(item)
        else:
            automatic_by_key[key] = item

    desired_keys = set()
    for tech in techniques or attack_auto_default_technique():
        key = (
            attack_auto_clean(tech.get("technique_id"), 40),
            attack_auto_clean(tech.get("tactic_id"), 40),
        )
        if not key[0] or key in desired_keys:
            continue
        desired_keys.add(key)

        # Una validación manual tiene prioridad sobre el mapeo automático.
        if key in manual_keys:
            old_automatic = automatic_by_key.pop(key, None)
            if old_automatic is not None:
                db.session.delete(old_automatic)
            continue

        item = automatic_by_key.pop(key, None)
        if item is None:
            item = AttackAutoTechnique(
                technique_id=key[0],
                technique_name="Técnica MITRE",
                tactic_id=key[1],
                tactic_name=None,
                rationale=None,
                confidence=60,
                origin="Automático",
            )
            scenario.techniques.append(item)

        item.technique_id = key[0]
        item.technique_name = attack_auto_clean(tech.get("technique_name"), 255) or "Técnica MITRE"
        item.tactic_id = key[1]
        item.tactic_name = attack_auto_clean(tech.get("tactic_name"), 120)
        item.rationale = attack_auto_clean(tech.get("rationale"), 4000)
        item.confidence = max(0, min(100, int(tech.get("confidence") or 60)))
        item.origin = "Automático"

    # Eliminar únicamente técnicas automáticas que ya no vienen de la fuente.
    for item in automatic_by_key.values():
        db.session.delete(item)
    for item in duplicate_automatic:
        db.session.delete(item)


def attack_auto_apply_record(scenario, record, preserve_manual=True):
    source_fields = ("source_label", "source_date", "source_count", "source_snapshot", "evidence")
    editable_fields = (
        "name", "asset_name", "asset_type", "scope", "description", "exposure_channel",
        "internet_exposed", "threat_actor", "threat_event", "vulnerability", "consequences",
        "security_dimensions", "existing_controls", "control_weaknesses", "severity",
        "risk_appetite", "treatment", "status", "owner", "supplier_id", "supplier_name",
        "supplier_relationship", "supply_chain_details",
    )
    for field in source_fields:
        if field in record:
            setattr(scenario, field, record.get(field))
    if not (preserve_manual and scenario.manually_edited):
        for field in editable_fields:
            if field in record:
                setattr(scenario, field, record.get(field))
        factors = attack_auto_factor_values(record)
        for field, value in factors.items():
            setattr(scenario, field, value)
    scenario.updated_at = datetime.utcnow()


def attack_auto_period_bounds(today=None):
    today = today or date.today()
    return "{}-01-01".format(today.year), "{}-12-31".format(today.year)


def attack_auto_sync_current_evaluation(scenario, username):
    start, end = attack_auto_period_bounds()
    evaluation = AttackAutoEvaluation.query.filter_by(
        scenario_id=scenario.id, period_start=start, period_end=end
    ).first()
    if evaluation and evaluation.origin != "Automático":
        return evaluation
    if not evaluation:
        evaluation = AttackAutoEvaluation(
            scenario_id=scenario.id,
            period_start=start,
            period_end=end,
            evaluation_date=date.today().isoformat(),
            evaluator=username,
            origin="Automático",
        )
        db.session.add(evaluation)
    for field in (
        "exposure_level", "exploitability", "detected_activity", "control_weakness_level",
        "asset_criticality", "inherent_probability", "inherent_impact", "inherent_score",
        "inherent_level", "control_effectiveness", "residual_probability", "residual_impact",
        "residual_score", "residual_level", "risk_appetite", "treatment",
    ):
        setattr(evaluation, field, getattr(scenario, field))
    evaluation.controls_reviewed = scenario.existing_controls
    evaluation.justification = scenario.ai_justification or "Evaluación inicial generada con reglas trazables desde la fuente."
    evaluation.observations = "Evaluación automática del período; puede editarse y quedará preservada en futuras generaciones."
    evaluation.status = "Vigente"
    return evaluation


def attack_auto_upsert_record(record, username, use_ai=False, ai_budget=None):
    scenario = AttackAutoScenario.query.filter_by(
        source_type=record["source_type"], source_ref=str(record["source_ref"])
    ).first()
    created = scenario is None
    if created:
        scenario = AttackAutoScenario(
            code=attack_auto_code_for(record["source_type"], record["source_ref"]),
            source_type=record["source_type"],
            source_ref=str(record["source_ref"]),
            source_label=record.get("source_label"),
            name=record.get("name") or "Escenario de amenaza",
            created_by=username,
            generated_at=datetime.utcnow(),
        )
        db.session.add(scenario)
    before = json.dumps({
        "snapshot": scenario.source_snapshot,
        "name": scenario.name,
        "severity": scenario.severity,
    }, ensure_ascii=False, sort_keys=True)
    attack_auto_apply_record(scenario, record, preserve_manual=not created)
    attack_auto_replace_techniques(scenario, record.get("techniques"))
    changed_by_source = created or before != json.dumps({
        "snapshot": scenario.source_snapshot,
        "name": scenario.name,
        "severity": scenario.severity,
    }, ensure_ascii=False, sort_keys=True)

    ai_used = False
    should_enrich_ai = changed_by_source or scenario.ai_status != "Enriquecido"
    if use_ai and should_enrich_ai and ai_budget is not None and ai_budget[0] > 0 and scenario.severity in {"Crítica", "Alta"}:
        ai_budget[0] -= 1
        try:
            enriched = attack_auto_ai_enrich(record)
            if not scenario.manually_edited:
                for field in ("description", "threat_actor", "consequences", "control_weaknesses"):
                    if enriched.get(field):
                        setattr(scenario, field, enriched[field])
            scenario.ai_justification = enriched.get("justification")
            scenario.ai_status = "Enriquecido"
            try:
                scenario.ai_provider = (get_ai_provider() or "openrouter").strip().lower()
            except Exception:
                scenario.ai_provider = "configurado"
            scenario.ai_enriched_at = datetime.utcnow()
            ai_used = True
        except Exception as exc:
            scenario.ai_status = "Omitido por error"
            scenario.ai_justification = "La generación determinística se completó. IA no disponible: {}".format(attack_auto_clean(exc, 500))

    db.session.flush()
    attack_auto_sync_current_evaluation(scenario, username)
    after = json.dumps({
        "snapshot": scenario.source_snapshot,
        "name": scenario.name,
        "severity": scenario.severity,
    }, ensure_ascii=False, sort_keys=True)
    return scenario, "created" if created else "updated" if before != after else "unchanged", ai_used


def attack_auto_run_generation(username, use_ai=False):
    ensure_attack_auto_db()
    log = AttackAutoGenerationLog(executed_by=username, status="En proceso")
    db.session.add(log)
    db.session.commit()
    log_id = log.id
    counts = {"created": 0, "updated": 0, "unchanged": 0, "ai": 0}
    source_counts = {}
    errors = []
    ai_budget = [max(0, min(25, int(os.getenv("ATTACK_SURFACE_AI_MAX_PER_RUN", "5"))))]

    for source_name, collector in ATTACK_AUTO_COLLECTORS:
        try:
            records = collector()
            source_counts[source_name] = len(records)
        except Exception as exc:
            db.session.rollback()
            source_counts[source_name] = 0
            errors.append("{}: no se pudo leer la fuente ({})".format(source_name, attack_auto_clean(exc, 700)))
            continue
        for record in records:
            try:
                _, result, ai_used = attack_auto_upsert_record(record, username, use_ai=use_ai, ai_budget=ai_budget)
                db.session.commit()
                counts[result] += 1
                if ai_used:
                    counts["ai"] += 1
            except Exception as exc:
                db.session.rollback()
                errors.append("{} {}: {}".format(source_name, record.get("source_ref"), attack_auto_clean(exc, 700)))

    log = AttackAutoGenerationLog.query.get(log_id)
    log.finished_at = datetime.utcnow()
    log.created_count = counts["created"]
    log.updated_count = counts["updated"]
    log.unchanged_count = counts["unchanged"]
    log.ai_enriched_count = counts["ai"]
    log.error_count = len(errors)
    log.source_counts = json.dumps(source_counts, ensure_ascii=False)
    log.error_detail = "\n".join(errors[:100])
    log.status = "Completado" if not errors else "Completado con alertas"
    db.session.commit()
    return counts, source_counts, errors


def attack_auto_badge(level):
    return {
        "Crítico": "danger", "Crítica": "danger", "Alto": "warning", "Alta": "warning",
        "Medio": "info", "Media": "info", "Bajo": "success", "Baja": "success",
    }.get(level, "secondary")


def attack_auto_shell(title, body):
    content = render_template_string("""
    <style>
      .as-shell{width:96%;max-width:1650px;margin:10px auto 24px auto}
      .as-header-card{
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
      .as-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }
      .as-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
      }
      .as-header-overlay::before{
        content:"🎯";
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
      .as-header-text{max-width:1200px;width:100%;position:relative;z-index:1}
      .as-header-text::before{
        content:"SGSI · Gestión de Eventos";
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }
      .as-title{
        color:#ffffff!important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0!important;
      }
      .as-subtitle{color:rgba(255,255,255,.95);font-size:.78rem;margin-top:4px;line-height:1.25}
      .as-card{border:0;border-radius:18px;box-shadow:0 9px 25px rgba(15,23,42,.10);overflow:hidden}
      .as-kpi{padding:15px;border-radius:15px;background:#fff;border:1px solid #e3edf7;height:100%}
      .as-kpi small{color:#64748b;font-weight:800}.as-kpi strong{display:block;font-size:1.5rem;color:#0b4a6f}
      .as-table th{white-space:nowrap;background:#eaf5fb;color:#083b5c;font-size:.75rem}.as-table td{font-size:.78rem;vertical-align:middle}
      .as-actions{display:flex;gap:5px;flex-wrap:wrap}.as-actions form{margin:0}
      .as-section{font-weight:950;font-size:.78rem;color:#0b4a8f;padding:9px 12px;border-radius:12px;background:#eef5ff;border:1px solid #d9eaff;margin:14px 0 12px}
      .as-value{white-space:pre-wrap;overflow-wrap:anywhere;background:#f8fbfd;border:1px solid #e1edf4;border-radius:11px;padding:10px;min-height:44px}
      .as-tech{background:#eef8ff;border:1px solid #cde9fa;border-radius:12px;padding:9px;margin-bottom:7px}
      .as-note{font-size:.78rem;color:#475569}
      .as-risk-method{
        border:1px solid #cfe3f7;
        background:linear-gradient(135deg,#f8fbff 0%,#eef6ff 100%);
        border-radius:16px;
      }
      .as-risk-method .formula-box{
        background:#ffffff;
        border:1px solid #d9e8f7;
        border-radius:12px;
        padding:10px 12px;
        height:100%;
        font-size:.76rem;
        line-height:1.42;
      }
      .as-risk-details{margin-top:5px}
      .as-risk-details summary{
        cursor:pointer;
        color:#0b63ce;
        font-size:.70rem;
        font-weight:850;
        list-style:none;
        white-space:nowrap;
      }
      .as-risk-details summary::-webkit-details-marker{display:none}
      .as-risk-details summary::before{content:"ⓘ ";font-weight:900}
      .as-risk-details[open]{
        min-width:240px;
        padding:7px 8px;
        border:1px solid #d7e7f5;
        border-radius:10px;
        background:#f8fbff;
      }
      .as-risk-breakdown{
        margin-top:6px;
        font-size:.68rem;
        line-height:1.38;
        color:#334155;
        white-space:normal;
      }
      .as-risk-breakdown b{color:#0b4a6f}
      .as-form .form-label{font-weight:800;color:#24465d;font-size:.78rem}
      .as-form .form-control,.as-form .form-select{border-radius:10px;font-size:.82rem}
      @media(max-width:900px){
        .as-shell{width:98%}
        .as-header-card{min-height:88px;padding:14px 18px}
        .as-header-overlay{flex-direction:column;text-align:center;gap:8px}
        .as-header-overlay::before{margin-right:0}
        .as-title,.as-subtitle{text-align:center}
        .as-actions{min-width:210px}
      }
    </style>
    <div class="as-shell">
      <div class="as-header-card">
        <div class="as-header-overlay">
          <div class="as-header-text">
            <h3 class="as-title m-0">{{ title }}</h3>
            <div class="as-subtitle">Correlación automática, trazable y periódica de escenarios de amenaza</div>
          </div>
        </div>
      </div>
      {{ body|safe }}
    </div>
    """, title=title, body=Markup(body))
    return render_template_string(BASE, content=Markup(content))


def attack_auto_get_or_404(scenario_id):
    scenario = AttackAutoScenario.query.get(scenario_id)
    if not scenario:
        abort(404)
    return scenario


@app.route("/superficie_ataque", methods=["GET"])
@login_required
def attack_auto():
    user, response = attack_auto_guard(write=False)
    if response:
        return response
    ensure_attack_auto_db()
    query_text = (request.args.get("q") or "").strip()
    source_filter = (request.args.get("source") or "").strip()
    ad_platform_filter = (request.args.get("ad_platform") or "").strip().upper()
    if ad_platform_filter not in {"SAMBA", "WINDOWS"}:
        ad_platform_filter = ""
    severity = (request.args.get("severity") or "").strip()
    status = (request.args.get("status") or "").strip()
    query = AttackAutoScenario.query
    if query_text:
        like = "%{}%".format(query_text)
        query = query.filter(or_(
            AttackAutoScenario.code.ilike(like), AttackAutoScenario.name.ilike(like),
            AttackAutoScenario.asset_name.ilike(like), AttackAutoScenario.supplier_name.ilike(like),
            AttackAutoScenario.threat_event.ilike(like), AttackAutoScenario.source_ref.ilike(like),
            AttackAutoScenario.source_label.ilike(like),
        ))
    if source_filter:
        query = query.filter_by(source_type=source_filter)
    if source_filter == "ACTIVE_DIRECTORY" and ad_platform_filter:
        platform_label_filter = (
            "Microsoft Active Directory Windows"
            if ad_platform_filter == "WINDOWS"
            else "Active Directory Samba"
        )
        query = query.filter(or_(
            AttackAutoScenario.source_snapshot.ilike(
                '%"platform": "{}"%'.format(ad_platform_filter)
            ),
            AttackAutoScenario.source_snapshot.ilike(
                '%"platform":"{}"%'.format(ad_platform_filter)
            ),
            AttackAutoScenario.source_label.ilike("%{}%".format(platform_label_filter)),
        ))
    if severity:
        query = query.filter_by(severity=severity)
    if status:
        query = query.filter_by(status=status)
    scenarios = query.order_by(AttackAutoScenario.updated_at.desc(), AttackAutoScenario.id.desc()).all()
    all_items = AttackAutoScenario.query.all()
    total = len(all_items)
    linked = sum(1 for item in all_items if item.risk_id)
    critical_high = sum(1 for item in all_items if item.severity in {"Crítica", "Alta"})
    sources = len({item.source_type for item in all_items})
    last_log = AttackAutoGenerationLog.query.order_by(AttackAutoGenerationLog.id.desc()).first()
    read_only = auditor_is_read_only(user)

    body = render_template_string("""
    <div class="as-card card mb-3"><div class="card-body p-3">
      <div class="d-flex justify-content-between align-items-center gap-3 flex-wrap">
        <div>
          <h5 class="fw-bold text-primary mb-1"><i class="bi bi-stars"></i> Generación automática</h5>
          <div class="as-note">Lee los registros existentes de MITRE ATT&CK, vulnerabilidades, incidentes, TPRM, herramienta XDR, firewall y Gobierno del Directorio Activo.</div>
        </div>
        {% if not read_only %}
        <form method="post" action="{{ url_for('attack_auto_generate') }}" class="d-flex align-items-center gap-3 flex-wrap" onsubmit="this.querySelector('button').disabled=true;this.querySelector('button').innerHTML='<span class=&quot;spinner-border spinner-border-sm&quot;></span> Generando...';">
          <div class="form-check form-switch">
            <input class="form-check-input" type="checkbox" name="use_ai" value="1" id="use_ai" checked>
            <label class="form-check-label small fw-bold" for="use_ai">Enriquecer con IA</label>
          </div>
          <button class="btn btn-primary rounded-pill px-4"><i class="bi bi-magic"></i> Generar escenarios automáticamente</button>
        </form>
        {% endif %}
      </div>
      {% if last_log %}
      <div class="alert {{ 'alert-warning' if last_log.error_count else 'alert-success' }} py-2 mt-3 mb-0 small">
        Última ejecución: {{ last_log.finished_at or last_log.started_at }} · {{ last_log.status }} ·
        {{ last_log.created_count }} nuevos, {{ last_log.updated_count }} actualizados,
        {{ last_log.ai_enriched_count }} enriquecidos con IA, {{ last_log.error_count }} alertas.
        {% if last_log.error_detail %}<details class="mt-1"><summary>Ver alertas técnicas</summary><pre class="mb-0 small">{{ last_log.error_detail }}</pre></details>{% endif %}
      </div>
      {% endif %}
    </div></div>

    <div class="row g-3 mb-3">
      <div class="col-6 col-lg"><div class="as-kpi"><small>Escenarios</small><strong>{{ total }}</strong></div></div>
      <div class="col-6 col-lg"><div class="as-kpi"><small>Fuentes correlacionadas</small><strong>{{ sources }}</strong></div></div>
      <div class="col-6 col-lg"><div class="as-kpi"><small>Críticos / Altos</small><strong>{{ critical_high }}</strong></div></div>
      <div class="col-6 col-lg"><div class="as-kpi"><small>En matriz de riesgos</small><strong>{{ linked }}</strong></div></div>
      <div class="col-6 col-lg"><div class="as-kpi"><small>Pendientes de registrar</small><strong>{{ total-linked }}</strong></div></div>
    </div>


    <div class="as-card as-risk-method card mb-3">
      <div class="card-body p-3">
        <div class="d-flex align-items-start gap-3 flex-wrap">
          <div class="flex-grow-1">
            <h6 class="fw-bold text-primary mb-1"><i class="bi bi-calculator"></i> ¿Cómo se calcula el riesgo inherente?</h6>
            <div class="as-note">
              Es la exposición del escenario <strong>antes de considerar la efectividad de los controles</strong>.
              Se obtiene con una matriz 5×5: <strong>Probabilidad × Impacto</strong>.
              En cada fila puede desplegar <em>Ver cálculo</em> para revisar los factores utilizados.
            </div>
          </div>
        </div>
        <div class="row g-2 mt-1">
          <div class="col-lg-4">
            <div class="formula-box">
              <b>1. Probabilidad inherente</b><br>
              Redondeo de: (Exposición + Explotabilidad + Actividad detectada + Debilidad de control) ÷ 4.
            </div>
          </div>
          <div class="col-lg-4">
            <div class="formula-box">
              <b>2. Impacto inherente</b><br>
              Redondeo de: (Criticidad del activo + Severidad del hallazgo) ÷ 2.
              Severidad: Baja=2, Media=3, Alta=4, Crítica=5.
            </div>
          </div>
          <div class="col-lg-4">
            <div class="formula-box">
              <b>3. Resultado y nivel</b><br>
              Probabilidad × Impacto. Clasificación: 1–4 Bajo, 5–9 Medio, 10–16 Alto y 17–25 Crítico.
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="as-card card mb-3"><div class="card-body p-3">
      <form method="get" class="row g-2 align-items-end">
        {% if ad_platform_filter %}<input type="hidden" name="ad_platform" value="{{ ad_platform_filter }}">{% endif %}
        <div class="col-md-4"><label class="form-label small fw-bold">Buscar</label><input name="q" value="{{ query_text }}" class="form-control" placeholder="Código, escenario, activo o proveedor"></div>
        <div class="col-md-2"><label class="form-label small fw-bold">Fuente</label><select name="source" class="form-select"><option value="">Todas</option>{% for key,label in source_labels.items() %}<option value="{{ key }}" {{ 'selected' if source_filter==key else '' }}>{{ label }}</option>{% endfor %}</select></div>
        <div class="col-md-2"><label class="form-label small fw-bold">Severidad</label><select name="severity" class="form-select"><option value="">Todas</option>{% for item in ['Crítica','Alta','Media','Baja'] %}<option {{ 'selected' if severity==item else '' }}>{{ item }}</option>{% endfor %}</select></div>
        <div class="col-md-2"><label class="form-label small fw-bold">Estado</label><select name="status" class="form-select"><option value="">Todos</option>{% for item in ['En análisis','Vigente','En tratamiento','Aceptado','Cerrado'] %}<option {{ 'selected' if status==item else '' }}>{{ item }}</option>{% endfor %}</select></div>
        <div class="col-md-2 d-flex gap-2"><button class="btn btn-outline-primary flex-fill">Filtrar</button><a href="{{ url_for('attack_auto') }}" class="btn btn-outline-secondary">Limpiar</a></div>
      </form>
    </div></div>

    <div class="as-card card"><div class="table-responsive"><table class="table table-hover as-table mb-0">
      <thead><tr><th>Código</th><th>Fuente</th><th>Escenario / Activo</th><th>MITRE ATT&CK</th><th>Períodos</th><th>Riesgo inherente</th><th>Estado</th><th>Riesgo</th><th>Acciones</th></tr></thead>
      <tbody>
      {% for item in scenarios %}
      <tr>
        <td><b>{{ item.code }}</b><br><span class="text-muted">{{ item.updated_at.strftime('%Y-%m-%d') if item.updated_at else '' }}</span></td>
        <td><span class="badge bg-dark">{{ source_labels.get(item.source_type,item.source_type) }}</span>{% if item.source_count>1 %}<br><span class="text-muted">{{ item.source_count }} evidencias</span>{% endif %}</td>
        <td style="min-width:250px"><b>{{ item.name }}</b><br><span class="text-muted"><i class="bi bi-hdd"></i> {{ item.asset_name }}</span>{% if item.supplier_name %}<br><span class="text-primary"><i class="bi bi-truck"></i> {{ item.supplier_name }}</span>{% endif %}</td>
        <td style="min-width:180px">{% for tech in item.techniques[:3] %}<span class="badge bg-light text-dark border mb-1">{{ tech.technique_id }} · {{ tech.technique_name }}</span><br>{% endfor %}{% if not item.techniques %}<span class="text-muted">Pendiente</span>{% endif %}</td>
        <td class="text-center"><span class="badge bg-secondary">{{ item.evaluations|length }}</span></td>
        <td style="min-width:210px">
          <span class="badge bg-{{ badge(item.inherent_level) }}">{{ item.inherent_score }} · {{ item.inherent_level }}</span>
          <div class="text-muted mt-1" style="font-size:.69rem">
            P{{ item.inherent_probability }} × I{{ item.inherent_impact }} = {{ item.inherent_score }}
          </div>
          <details class="as-risk-details">
            <summary>Ver cálculo</summary>
            <div class="as-risk-breakdown">
              <div><b>Probabilidad:</b> redondeo de
                ({{ item.exposure_level }} exposición +
                 {{ item.exploitability }} explotabilidad +
                 {{ item.detected_activity }} actividad detectada +
                 {{ item.control_weakness_level }} debilidad de control) ÷ 4
                = <b>{{ item.inherent_probability }}</b>.
              </div>
              <div class="mt-1"><b>Impacto:</b> redondeo de
                ({{ item.asset_criticality }} criticidad del activo +
                 {{ severity_factor(item.severity) }} severidad {{ item.severity }}) ÷ 2
                = <b>{{ item.inherent_impact }}</b>.
              </div>
              <div class="mt-1"><b>Resultado:</b>
                {{ item.inherent_probability }} × {{ item.inherent_impact }}
                = <b>{{ item.inherent_score }} · {{ item.inherent_level }}</b>.
              </div>
            </div>
          </details>
        </td>
        <td>{{ item.status }}{% if item.ai_status=='Enriquecido' %}<br><span class="badge bg-info text-dark"><i class="bi bi-stars"></i> IA</span>{% endif %}</td>
        <td>{% if item.risk_code %}<span class="badge bg-success">{{ item.risk_code }}</span>{% else %}<span class="text-muted">No registrado</span>{% endif %}</td>
        <td style="min-width:310px"><div class="as-actions">
          <a class="btn btn-sm btn-outline-primary" href="{{ url_for('attack_auto_view', scenario_id=item.id) }}"><i class="bi bi-eye"></i> Ver</a>
          {% if not read_only %}
          <a class="btn btn-sm btn-outline-warning" href="{{ url_for('attack_auto_edit', scenario_id=item.id) }}"><i class="bi bi-pencil"></i> Editar</a>
          <form method="post" action="{{ url_for('attack_auto_delete', scenario_id=item.id) }}" onsubmit="return confirm('¿Eliminar este escenario y su histórico de evaluaciones? El riesgo ya registrado no será eliminado.');"><button class="btn btn-sm btn-outline-danger"><i class="bi bi-trash"></i> Eliminar</button></form>
          <form method="post" action="{{ url_for('attack_auto_register_risk', scenario_id=item.id) }}" onsubmit="return confirm('¿{{ 'Actualizar' if item.risk_id else 'Registrar' }} este escenario en la Matriz de Riesgos?');"><button class="btn btn-sm btn-success"><i class="bi bi-shield-check"></i> {{ 'Actualizar en Riesgos' if item.risk_id else 'Registrar en Matriz de Riesgos' }}</button></form>
          {% endif %}
        </div></td>
      </tr>
      {% else %}<tr><td colspan="9" class="text-center text-muted py-5">No hay escenarios. Use “Generar escenarios automáticamente” para crearlos desde los datos existentes.</td></tr>{% endfor %}
      </tbody>
    </table></div></div>
    """, scenarios=scenarios, total=total, linked=linked, critical_high=critical_high,
        sources=sources, last_log=last_log, read_only=read_only, query_text=query_text,
        source_filter=source_filter, ad_platform_filter=ad_platform_filter,
        severity=severity, status=status, source_labels=ATTACK_AUTO_SOURCE_LABELS,
        badge=attack_auto_badge, severity_factor=attack_auto_score_from_severity)
    return attack_auto_shell("Superficie de Ataque y Escenarios", body)


@app.route("/superficie_ataque/generar", methods=["POST"])
@app.route("/superficie_ataque/sincronizar/mitre", methods=["GET", "POST"])
@app.route("/superficie_ataque/sincronizar-mitre", methods=["GET", "POST"])
@app.route("/superficie_ataque/sincronizar_mitre", methods=["GET", "POST"])
@login_required
def attack_auto_generate():
    user, response = attack_auto_guard(write=True)
    if response:
        return response
    if request.method == "GET":
        flash("La sincronización MITRE fue reemplazada por la generación automática multi-fuente. Use el botón de la matriz.", "info")
        return redirect(url_for("attack_auto"))
    try:
        counts, source_counts, errors = attack_auto_run_generation(
            getattr(user, "username", None) or getattr(user, "email", None) or "usuario",
            use_ai=attack_auto_yes(request.form.get("use_ai")),
        )
        message = "Generación completada: {} nuevos, {} actualizados, {} sin cambios y {} enriquecidos con IA.".format(
            counts["created"], counts["updated"], counts["unchanged"], counts["ai"]
        )
        if errors:
            flash(message + " Se presentaron {} alertas aisladas; consulte el detalle de la última ejecución.".format(len(errors)), "warning")
        else:
            flash(message, "success")
    except Exception as exc:
        db.session.rollback()
        flash("No fue posible iniciar la generación automática: {}".format(attack_auto_clean(exc, 700)), "danger")
    return redirect(url_for("attack_auto"))


@app.route("/superficie_ataque/escenarios/<int:scenario_id>", methods=["GET"])
@login_required
def attack_auto_view(scenario_id):
    user, response = attack_auto_guard(write=False)
    if response:
        return response
    ensure_attack_auto_db()
    item = attack_auto_get_or_404(scenario_id)
    read_only = auditor_is_read_only(user)
    body = render_template_string("""
    <div class="d-flex justify-content-center gap-2 flex-wrap mb-3">
      <a href="{{ url_for('attack_auto') }}" class="btn btn-light border rounded-pill px-4"><i class="bi bi-arrow-left"></i> Volver a la matriz</a>
      {% if not read_only %}<a href="{{ url_for('attack_auto_edit', scenario_id=item.id) }}" class="btn btn-warning rounded-pill px-4"><i class="bi bi-pencil"></i> Editar</a>
      <form method="post" action="{{ url_for('attack_auto_register_risk', scenario_id=item.id) }}"><button class="btn btn-success rounded-pill px-4"><i class="bi bi-shield-check"></i> {{ 'Actualizar en Riesgos' if item.risk_id else 'Registrar en Matriz de Riesgos' }}</button></form>{% endif %}
    </div>
    <div class="as-card card"><div class="card-body p-4">
      <div class="d-flex justify-content-between gap-3 flex-wrap"><div><h4 class="fw-bold text-primary">{{ item.code }} · {{ item.name }}</h4><div class="text-muted">Fuente: {{ source_labels.get(item.source_type,item.source_type) }} · Referencia {{ item.source_ref }}</div></div><div><span class="badge bg-{{ badge(item.inherent_level) }} fs-6">Inherente {{ item.inherent_score }} · {{ item.inherent_level }}</span> <span class="badge bg-{{ badge(item.residual_level) }} fs-6">Residual {{ item.residual_score }} · {{ item.residual_level }}</span></div></div>
      <div class="as-section">Contexto del escenario</div>
      <div class="row g-3">
        <div class="col-md-4"><b>Activo</b><div class="as-value">{{ item.asset_name }}\n{{ item.asset_type or '' }}</div></div>
        <div class="col-md-4"><b>Canal de exposición</b><div class="as-value">{{ item.exposure_channel or 'N/D' }}\nExposición a Internet: {{ 'Sí' if item.internet_exposed else 'No' }}</div></div>
        <div class="col-md-4"><b>Responsable / Estado</b><div class="as-value">{{ item.owner or 'Por asignar' }}\n{{ item.status }}</div></div>
        <div class="col-md-6"><b>Descripción</b><div class="as-value">{{ item.description or 'N/D' }}</div></div>
        <div class="col-md-6"><b>Actor de amenaza</b><div class="as-value">{{ item.threat_actor or 'N/D' }}</div></div>
        <div class="col-md-6"><b>Evento de amenaza</b><div class="as-value">{{ item.threat_event or 'N/D' }}</div></div>
        <div class="col-md-6"><b>Vulnerabilidad / condición</b><div class="as-value">{{ item.vulnerability or 'N/D' }}</div></div>
        <div class="col-md-6"><b>Consecuencias</b><div class="as-value">{{ item.consequences or 'N/D' }}</div></div>
        <div class="col-md-6"><b>Dimensiones</b><div class="as-value">{{ item.security_dimensions or 'N/D' }}</div></div>
      </div>
      {% if item.source_type=='TPRM' %}<div class="as-section">Cadena de suministro (TPRM)</div><div class="row g-3"><div class="col-md-4"><b>Proveedor</b><div class="as-value">{{ item.supplier_name or 'N/D' }}</div></div><div class="col-md-4"><b>Relación / servicio</b><div class="as-value">{{ item.supplier_relationship or 'N/D' }}</div></div><div class="col-md-4"><b>Detalle</b><div class="as-value">{{ item.supply_chain_details or 'N/D' }}</div></div></div>{% endif %}
      <div class="as-section">MITRE ATT&CK</div>
      {% for tech in item.techniques %}<div class="as-tech"><b>{{ tech.technique_id }} · {{ tech.technique_name }}</b> <span class="badge bg-secondary">{{ tech.tactic_id }} · {{ tech.tactic_name }}</span><br><small>{{ tech.rationale }} · Confianza {{ tech.confidence }}% · {{ tech.origin }}</small></div>{% else %}<div class="text-muted">Sin técnica correlacionada.</div>{% endfor %}
      <div class="as-section">Controles, evidencia e IA</div>
      <div class="row g-3"><div class="col-md-4"><b>Controles existentes</b><div class="as-value">{{ item.existing_controls or 'N/D' }}</div></div><div class="col-md-4"><b>Debilidades de control</b><div class="as-value">{{ item.control_weaknesses or 'N/D' }}</div></div><div class="col-md-4"><b>Evidencia de origen</b><div class="as-value">{{ item.evidence or 'N/D' }}</div></div></div>
      <div class="alert alert-info mt-3 mb-0"><b>IA: {{ item.ai_status }}</b>{% if item.ai_provider %} · {{ item.ai_provider }}{% endif %}<br>{{ item.ai_justification or 'No se solicitó enriquecimiento. La evaluación se generó únicamente con reglas determinísticas.' }}</div>
      <div class="as-section d-flex justify-content-between align-items-center"><span>Evaluaciones por período</span>{% if not read_only %}<a href="{{ url_for('attack_auto_evaluation_new', scenario_id=item.id) }}" class="btn btn-sm btn-primary"><i class="bi bi-calendar-plus"></i> Nueva evaluación de período</a>{% endif %}</div>
      <div class="table-responsive"><table class="table table-sm as-table"><thead><tr><th>Período</th><th>Evaluador</th><th>Inherente</th><th>Controles</th><th>Residual</th><th>Tratamiento</th><th>Origen</th><th>Acciones</th></tr></thead><tbody>
      {% for ev in item.evaluations %}<tr><td>{{ ev.period_start }} a {{ ev.period_end }}<br><small>{{ ev.evaluation_date }}</small></td><td>{{ ev.evaluator or 'N/D' }}</td><td><span class="badge bg-{{ badge(ev.inherent_level) }}">{{ ev.inherent_score }} · {{ ev.inherent_level }}</span></td><td>{{ ev.control_effectiveness }}%</td><td><span class="badge bg-{{ badge(ev.residual_level) }}">{{ ev.residual_score }} · {{ ev.residual_level }}</span></td><td>{{ ev.treatment }}<br><small>{{ ev.status }}</small></td><td>{{ ev.origin }}</td><td>{% if not read_only %}<div class="as-actions"><a class="btn btn-sm btn-outline-warning" href="{{ url_for('attack_auto_evaluation_edit', scenario_id=item.id, evaluation_id=ev.id) }}"><i class="bi bi-pencil"></i> Editar</a><form method="post" action="{{ url_for('attack_auto_evaluation_delete', scenario_id=item.id, evaluation_id=ev.id) }}" onsubmit="return confirm('¿Eliminar esta evaluación del período?');"><button class="btn btn-sm btn-outline-danger"><i class="bi bi-trash"></i></button></form></div>{% endif %}</td></tr>
      {% else %}<tr><td colspan="8" class="text-center text-muted">Sin evaluaciones.</td></tr>{% endfor %}
      </tbody></table></div>
    </div></div>
    """, item=item, read_only=read_only, source_labels=ATTACK_AUTO_SOURCE_LABELS, badge=attack_auto_badge)
    return attack_auto_shell("Detalle del escenario", body)


def attack_auto_technique_lines(item):
    return "\n".join(
        "{}|{}|{}|{}".format(t.technique_id, t.technique_name, t.tactic_id or "", t.tactic_name or "")
        for t in item.techniques
    )


def attack_auto_parse_technique_lines(raw):
    """
    Convierte las líneas del formulario en técnicas MITRE y elimina
    combinaciones repetidas de técnica + táctica antes de guardar.
    """
    parsed = []
    seen = set()

    for line in str(raw or "").splitlines():
        parts = [attack_auto_clean(value) for value in line.split("|")]
        if not parts or not parts[0]:
            continue
        while len(parts) < 4:
            parts.append("")

        technique_id = parts[0][:40]
        tactic_id = parts[2][:40]
        key = (technique_id, tactic_id)

        if key in seen:
            continue
        seen.add(key)

        parsed.append({
            "technique_id": technique_id,
            "technique_name": (parts[1] or "Técnica MITRE")[:255],
            "tactic_id": tactic_id,
            "tactic_name": parts[3][:120],
        })

    return parsed


def attack_auto_apply_scenario_form(item, form):
    text_fields = (
        "name", "asset_name", "asset_type", "scope", "description", "exposure_channel",
        "threat_actor", "threat_event", "vulnerability", "consequences", "security_dimensions",
        "existing_controls", "control_weaknesses", "evidence", "risk_appetite", "treatment",
        "status", "owner", "supplier_name", "supplier_relationship", "supply_chain_details",
    )
    for field in text_fields:
        if field in form:
            setattr(item, field, attack_auto_clean(form.get(field), 4000))
    item.name = item.name or "Escenario de amenaza"
    item.asset_name = item.asset_name or "Activo no especificado"
    item.internet_exposed = attack_auto_yes(form.get("internet_exposed"))
    item.severity = attack_auto_normalize_severity(form.get("severity"))
    factor_input = {
        "severity": item.severity,
        "exposure_level": form.get("exposure_level"),
        "exploitability": form.get("exploitability"),
        "detected_activity": form.get("detected_activity"),
        "control_weakness_level": form.get("control_weakness_level"),
        "asset_criticality": form.get("asset_criticality"),
        "control_effectiveness": max(0, min(100, int(form.get("control_effectiveness") or 0))),
    }
    for field, value in attack_auto_factor_values(factor_input).items():
        setattr(item, field, value)
    if item.source_type == "TPRM":
        try:
            item.supplier_id = int(form.get("supplier_id")) if form.get("supplier_id") else item.supplier_id
        except Exception:
            pass
    # Reconciliar técnicas existentes en lugar de borrarlas y reinsertarlas.
    # Esto evita que SQLite intente insertar una combinación única antes de
    # ejecutar el DELETE del registro anterior.
    existing_by_key = {}
    duplicate_existing = []

    for current in list(item.techniques):
        key = (
            attack_auto_clean(current.technique_id, 40),
            attack_auto_clean(current.tactic_id, 40),
        )
        if key in existing_by_key:
            duplicate_existing.append(current)
        else:
            existing_by_key[key] = current

    desired_keys = set()
    for tech in attack_auto_parse_technique_lines(form.get("technique_lines")):
        key = (tech["technique_id"], tech["tactic_id"])
        desired_keys.add(key)

        current = existing_by_key.pop(key, None)
        if current is None:
            current = AttackAutoTechnique(
                technique_id=tech["technique_id"],
                technique_name=tech["technique_name"],
                tactic_id=tech["tactic_id"],
                tactic_name=tech["tactic_name"],
                rationale="Mapeo validado manualmente por el analista.",
                confidence=100,
                origin="Manual",
            )
            item.techniques.append(current)
        else:
            current.technique_name = tech["technique_name"]
            current.tactic_name = tech["tactic_name"]
            current.rationale = "Mapeo validado manualmente por el analista."
            current.confidence = 100
            current.origin = "Manual"

    # Las técnicas retiradas del formulario sí se eliminan.
    for current in existing_by_key.values():
        db.session.delete(current)
    for current in duplicate_existing:
        db.session.delete(current)

    item.manually_edited = True
    item.updated_at = datetime.utcnow()


def attack_auto_scenario_form(item):
    body = render_template_string("""
    <form method="post" class="as-form">
      <div class="d-flex justify-content-center gap-2 mb-3"><a href="{{ url_for('attack_auto_view', scenario_id=item.id) }}" class="btn btn-light border rounded-pill px-4"><i class="bi bi-arrow-left"></i> Cancelar</a><button class="btn btn-primary rounded-pill px-4"><i class="bi bi-save"></i> Guardar cambios</button></div>
      <div class="as-card card"><div class="card-body p-4">
        <div class="alert alert-info small">Los datos se pueden ajustar manualmente. Una nueva generación actualizará la evidencia de origen, pero preservará los campos editados y las técnicas validadas.</div>
        <div class="as-section">Identificación y alcance</div>
        <div class="row g-3">
          <div class="col-md-8"><label class="form-label">Nombre del escenario</label><input class="form-control" name="name" required value="{{ item.name }}"></div>
          <div class="col-md-2"><label class="form-label">Severidad</label><select class="form-select" name="severity">{% for value in ['Crítica','Alta','Media','Baja'] %}<option {{ 'selected' if item.severity==value else '' }}>{{ value }}</option>{% endfor %}</select></div>
          <div class="col-md-2"><label class="form-label">Estado</label><select class="form-select" name="status">{% for value in ['En análisis','Vigente','En tratamiento','Aceptado','Cerrado'] %}<option {{ 'selected' if item.status==value else '' }}>{{ value }}</option>{% endfor %}</select></div>
          <div class="col-md-4"><label class="form-label">Activo</label><input class="form-control" name="asset_name" value="{{ item.asset_name or '' }}"></div>
          <div class="col-md-4"><label class="form-label">Tipo de activo</label><input class="form-control" name="asset_type" value="{{ item.asset_type or '' }}"></div>
          <div class="col-md-4"><label class="form-label">Responsable</label><input class="form-control" name="owner" value="{{ item.owner or '' }}"></div>
          <div class="col-md-8"><label class="form-label">Canal de exposición</label><input class="form-control" name="exposure_channel" value="{{ item.exposure_channel or '' }}"></div>
          <div class="col-md-4 d-flex align-items-end"><div class="form-check mb-2"><input class="form-check-input" type="checkbox" name="internet_exposed" value="1" id="internet_exposed" {{ 'checked' if item.internet_exposed else '' }}><label class="form-check-label" for="internet_exposed">Expuesto a Internet</label></div></div>
          <div class="col-12"><label class="form-label">Alcance</label><textarea class="form-control" rows="2" name="scope">{{ item.scope or '' }}</textarea></div>
        </div>
        <div class="as-section">Narrativa del escenario</div>
        <div class="row g-3">
          <div class="col-md-6"><label class="form-label">Descripción</label><textarea class="form-control" rows="4" name="description">{{ item.description or '' }}</textarea></div>
          <div class="col-md-6"><label class="form-label">Actor de amenaza</label><textarea class="form-control" rows="4" name="threat_actor">{{ item.threat_actor or '' }}</textarea></div>
          <div class="col-md-6"><label class="form-label">Evento de amenaza</label><textarea class="form-control" rows="4" name="threat_event">{{ item.threat_event or '' }}</textarea></div>
          <div class="col-md-6"><label class="form-label">Vulnerabilidad / condición</label><textarea class="form-control" rows="4" name="vulnerability">{{ item.vulnerability or '' }}</textarea></div>
          <div class="col-md-6"><label class="form-label">Consecuencias</label><textarea class="form-control" rows="4" name="consequences">{{ item.consequences or '' }}</textarea></div>
          <div class="col-md-6"><label class="form-label">Dimensiones de seguridad</label><textarea class="form-control" rows="4" name="security_dimensions">{{ item.security_dimensions or '' }}</textarea></div>
        </div>
        <div class="as-section">Controles y evidencia</div>
        <div class="row g-3"><div class="col-md-4"><label class="form-label">Controles existentes</label><textarea class="form-control" rows="4" name="existing_controls">{{ item.existing_controls or '' }}</textarea></div><div class="col-md-4"><label class="form-label">Debilidades de control</label><textarea class="form-control" rows="4" name="control_weaknesses">{{ item.control_weaknesses or '' }}</textarea></div><div class="col-md-4"><label class="form-label">Evidencia</label><textarea class="form-control" rows="4" name="evidence">{{ item.evidence or '' }}</textarea></div></div>
        {% if item.source_type=='TPRM' %}<div class="as-section">Cadena de suministro (TPRM)</div><div class="row g-3"><div class="col-md-2"><label class="form-label">ID proveedor</label><input class="form-control" type="number" name="supplier_id" value="{{ item.supplier_id or '' }}"></div><div class="col-md-4"><label class="form-label">Proveedor</label><input class="form-control" name="supplier_name" value="{{ item.supplier_name or '' }}"></div><div class="col-md-6"><label class="form-label">Relación / servicio</label><input class="form-control" name="supplier_relationship" value="{{ item.supplier_relationship or '' }}"></div><div class="col-12"><label class="form-label">Detalle de cadena de suministro</label><textarea class="form-control" name="supply_chain_details">{{ item.supply_chain_details or '' }}</textarea></div></div>{% endif %}
        <div class="as-section">Factores de evaluación (1 a 5)</div>
        <div class="row g-3">
          {% for field,label,value in factors %}<div class="col-6 col-md-2"><label class="form-label">{{ label }}</label><input class="form-control" type="number" min="1" max="5" name="{{ field }}" value="{{ value }}" required></div>{% endfor %}
          <div class="col-6 col-md-2"><label class="form-label">Eficacia control %</label><input class="form-control" type="number" min="0" max="100" name="control_effectiveness" value="{{ item.control_effectiveness }}" required></div>
          <div class="col-md-4"><label class="form-label">Apetito</label><select class="form-select" name="risk_appetite">{% for value in ['Dentro de apetito','Por evaluar','Fuera de apetito'] %}<option {{ 'selected' if item.risk_appetite==value else '' }}>{{ value }}</option>{% endfor %}</select></div>
          <div class="col-md-4"><label class="form-label">Tratamiento</label><select class="form-select" name="treatment">{% for value in ['Mitigar','Evitar','Transferir','Aceptar','Monitorear'] %}<option {{ 'selected' if item.treatment==value else '' }}>{{ value }}</option>{% endfor %}</select></div>
        </div>
        <div class="as-section">MITRE ATT&CK</div><label class="form-label">Una técnica por línea: ID|Nombre|ID táctica|Nombre táctica</label><textarea class="form-control font-monospace" rows="6" name="technique_lines">{{ technique_lines }}</textarea>
        <div class="text-center mt-4"><button class="btn btn-primary rounded-pill px-5"><i class="bi bi-save"></i> Guardar cambios</button></div>
      </div></div>
    </form>
    """, item=item, technique_lines=attack_auto_technique_lines(item), factors=[
        ("exposure_level", "Exposición", item.exposure_level),
        ("exploitability", "Explotabilidad", item.exploitability),
        ("detected_activity", "Actividad detectada", item.detected_activity),
        ("control_weakness_level", "Debilidad control", item.control_weakness_level),
        ("asset_criticality", "Criticidad activo", item.asset_criticality),
    ])
    return attack_auto_shell("Editar escenario {}".format(item.code), body)


@app.route("/superficie_ataque/escenarios/<int:scenario_id>/editar", methods=["GET", "POST"])
@login_required
def attack_auto_edit(scenario_id):
    user, response = attack_auto_guard(write=True)
    if response:
        return response
    ensure_attack_auto_db()
    item = attack_auto_get_or_404(scenario_id)
    if request.method == "POST":
        try:
            attack_auto_apply_scenario_form(item, request.form)
            db.session.commit()
            flash("Escenario actualizado correctamente.", "success")
            return redirect(url_for("attack_auto_view", scenario_id=item.id))
        except Exception as exc:
            db.session.rollback()
            flash("No fue posible actualizar el escenario: {}".format(attack_auto_clean(exc, 500)), "danger")
    return attack_auto_scenario_form(item)


@app.route("/superficie_ataque/escenarios/<int:scenario_id>/eliminar", methods=["POST"])
@login_required
def attack_auto_delete(scenario_id):
    user, response = attack_auto_guard(write=True)
    if response:
        return response
    ensure_attack_auto_db()
    item = attack_auto_get_or_404(scenario_id)
    risk_code = item.risk_code
    db.session.delete(item)
    db.session.commit()
    message = "Escenario e histórico eliminados."
    if risk_code:
        message += " El riesgo {} se conservó en la Matriz de Riesgos.".format(risk_code)
    flash(message, "success")
    return redirect(url_for("attack_auto"))


def attack_auto_latest_evaluation(item):
    return sorted(item.evaluations, key=lambda ev: (ev.period_end or "", ev.id or 0), reverse=True)[0] if item.evaluations else None


def attack_auto_probability_label(value):
    return {1: "Rara vez o Muy baja", 2: "Eventualmente o baja", 3: "Puede ocurrir o Moderada", 4: "Probable o Alta", 5: "Muy frecuente o Muy Alta"}.get(int(value or 3), "Puede ocurrir o Moderada")


def attack_auto_impact_label(value):
    return {1: "Insignificante o Inferior", 2: "Menor", 3: "Moderado o Importante", 4: "Mayor", 5: "Catastrófico o Crítico"}.get(int(value or 3), "Moderado o Importante")


ATTACK_AUTO_RISK_TYPE_NAME = "Seguridad y Ciberseguridad"


def attack_auto_get_or_create_risk_type(user):
    """Obtiene o crea el Tipo de Riesgo usado por los escenarios de ataque."""
    risk_type = TipoRiesgo.query.filter(
        TipoRiesgo.owner_user_id == user.id,
        db.func.lower(TipoRiesgo.nombre) == ATTACK_AUTO_RISK_TYPE_NAME.lower(),
    ).first()

    if not risk_type:
        risk_type = TipoRiesgo(
            nombre=ATTACK_AUTO_RISK_TYPE_NAME,
            owner_user_id=user.id,
            activo=True,
            creado_por=(
                getattr(user, "username", None)
                or session.get("username")
                or "sistema"
            ),
        )
        db.session.add(risk_type)
        db.session.flush()
    elif not risk_type.activo:
        risk_type.activo = True

    return risk_type


@app.route("/superficie_ataque/escenarios/<int:scenario_id>/registrar-riesgo", methods=["POST"])
@login_required
def attack_auto_register_risk(scenario_id):
    user, response = attack_auto_guard(write=True)
    if response:
        return response
    ensure_attack_auto_db()
    item = attack_auto_get_or_404(scenario_id)
    evaluation = attack_auto_latest_evaluation(item)
    expected_risk_code = "R-{}".format(item.code)[:50]
    risk = Riesgo.query.get(item.risk_id) if item.risk_id else None
    if not risk:
        risk = Riesgo.query.filter_by(codigo_riesgo=item.risk_code or expected_risk_code).first()
    created = risk is None
    if created:
        risk = Riesgo(codigo_riesgo=expected_risk_code)
        db.session.add(risk)
    risk_type = attack_auto_get_or_create_risk_type(user)
    probability = evaluation.inherent_probability if evaluation else item.inherent_probability
    impact = evaluation.inherent_impact if evaluation else item.inherent_impact
    inherent_score = evaluation.inherent_score if evaluation else item.inherent_score
    inherent_level = evaluation.inherent_level if evaluation else item.inherent_level
    residual_probability = evaluation.residual_probability if evaluation else item.residual_probability
    residual_impact = evaluation.residual_impact if evaluation else item.residual_impact
    residual_score = evaluation.residual_score if evaluation else item.residual_score
    residual_level = evaluation.residual_level if evaluation else item.residual_level
    treatment = evaluation.treatment if evaluation else item.treatment
    tech_ids = ", ".join(dict.fromkeys(t.technique_id for t in item.techniques))
    risk.riesgo = attack_auto_clean(item.name, 255)
    risk.fecha_identificacion = date.today().isoformat()
    risk.propietario_riesgo = attack_auto_clean(item.owner or "Por asignar", 255)
    risk.codigo_amenaza = attack_auto_clean(tech_ids, 50)
    risk.amenaza = attack_auto_clean(item.threat_event, 255)
    risk.codigo_vulnerabilidad = attack_auto_clean(item.source_ref, 50)
    risk.vulnerabilidad = attack_auto_clean(item.vulnerability, 255)
    risk.tipo_activo = attack_auto_clean(item.asset_type, 100)
    risk.nombre_activo = attack_auto_clean(item.asset_name, 255)
    risk.dimension_seguridad = attack_auto_clean(item.security_dimensions, 50)
    risk.tipo_riesgo_id = risk_type.id
    risk.probabilidad = int(probability)
    risk.impacto = int(impact)
    risk.descripcion_control = item.existing_controls
    efectividad_control = riesgo_normalizar_fraccion(item.control_effectiveness, 0.0)
    risk.diseno_control = riesgo_formatear_porcentaje(efectividad_control)
    risk.ejecucion_control = "Fuerte" if efectividad_control >= 0.70 else "Débil"
    risk.valor = efectividad_control
    risk.solidez_individual = efectividad_control
    risk.solidez_grupal = efectividad_control
    risk.prob_inh = attack_auto_probability_label(probability)
    risk.imp_inh = attack_auto_impact_label(impact)
    resultado_matriz = riesgo_calcular_resultados(risk.prob_inh, risk.imp_inh, efectividad_control)
    risk.probabilidad = resultado_matriz["prob_inh_num"]
    risk.impacto = resultado_matriz["imp_inh_num"]
    risk.riesgo_inherente = resultado_matriz["riesgo_inherente"]
    risk.cuadrante_prob = resultado_matriz["prob_res_label"]
    risk.prob_res = resultado_matriz["prob_res_label"]
    risk.cuadrante_imp = resultado_matriz["imp_res_label"]
    risk.impacto_res = resultado_matriz["imp_res_num"]
    risk.impacto_res_label = resultado_matriz["imp_res_label"]
    risk.riesgo_residual = resultado_matriz["riesgo_residual"]
    risk.fecha_revision = date.today().isoformat()
    risk.tratamiento_riesgo = attack_auto_clean(treatment, 255)
    risk.plan_accion = attack_auto_clean(item.control_weaknesses, 255)
    risk.responsable = attack_auto_clean(item.owner or "Por asignar", 255)
    risk.observaciones = "Generado desde {} ({} / {}). IA: {}. {}".format(
        ATTACK_AUTO_MODULE, item.code, ATTACK_AUTO_SOURCE_LABELS.get(item.source_type, item.source_type),
        item.ai_status, item.ai_justification or "Evaluación determinística",
    )
    risk.archivado = False
    db.session.flush()
    item.risk_id = risk.id
    item.risk_code = risk.codigo_riesgo
    item.status = "Vigente" if item.status == "En análisis" else item.status
    if evaluation:
        evaluation.risk_id = risk.id
        evaluation.risk_code = risk.codigo_riesgo
    db.session.commit()

    # Mantener la trazabilidad con el hallazgo AD original. La creación o
    # actualización del riesgo continúa ocurriendo únicamente en este módulo.
    if item.source_type == "ACTIVE_DIRECTORY":
        try:
            finding_id = int(str(item.source_ref or "").split(":")[-1])
            ad_db_path = os.path.join(app.instance_path, "ad_governance.db")
            if os.path.exists(ad_db_path):
                with sqlite3.connect(ad_db_path, timeout=20) as ad_conn:
                    ad_conn.execute("UPDATE ad_findings SET risk_id=? WHERE id=?", (risk.id, finding_id))
                    ad_conn.commit()
        except Exception:
            pass

    flash("Escenario {} {} en la Matriz de Riesgos con código {}.".format(item.code, "registrado" if created else "actualizado", risk.codigo_riesgo), "success")
    return redirect(url_for("attack_auto"))


def attack_auto_validate_date(value, label):
    try:
        return datetime.strptime(str(value or ""), "%Y-%m-%d").date().isoformat()
    except Exception:
        raise ValueError("{} debe tener formato AAAA-MM-DD".format(label))


def attack_auto_apply_evaluation_form(evaluation, form, user):
    start = attack_auto_validate_date(form.get("period_start"), "Inicio del período")
    end = attack_auto_validate_date(form.get("period_end"), "Fin del período")
    if start > end:
        raise ValueError("El inicio del período no puede ser posterior al fin")
    evaluation.period_start = start
    evaluation.period_end = end
    evaluation.evaluation_date = attack_auto_validate_date(form.get("evaluation_date"), "Fecha de evaluación")
    evaluation.evaluator = attack_auto_clean(form.get("evaluator") or getattr(user, "username", None) or "usuario", 255)
    evaluation.methodology = attack_auto_clean(form.get("methodology"), 120) or "Matriz 5x5 GRAC"
    factor_input = {
        "severity": form.get("severity") or "Media",
        "exposure_level": form.get("exposure_level"),
        "exploitability": form.get("exploitability"),
        "detected_activity": form.get("detected_activity"),
        "control_weakness_level": form.get("control_weakness_level"),
        "asset_criticality": form.get("asset_criticality"),
        "control_effectiveness": max(0, min(100, int(form.get("control_effectiveness") or 0))),
    }
    for field, value in attack_auto_factor_values(factor_input).items():
        setattr(evaluation, field, value)
    evaluation.risk_appetite = attack_auto_clean(form.get("risk_appetite"), 50)
    evaluation.treatment = attack_auto_clean(form.get("treatment"), 80)
    evaluation.justification = attack_auto_clean(form.get("justification"), 4000)
    evaluation.controls_reviewed = attack_auto_clean(form.get("controls_reviewed"), 4000)
    evaluation.observations = attack_auto_clean(form.get("observations"), 4000)
    evaluation.status = attack_auto_clean(form.get("status"), 50) or "Vigente"
    evaluation.origin = "Manual"


def attack_auto_evaluation_form(item, evaluation, is_new=False):
    body = render_template_string("""
    <form method="post" class="as-form">
      <div class="d-flex justify-content-center gap-2 mb-3"><a href="{{ url_for('attack_auto_view', scenario_id=item.id) }}" class="btn btn-light border rounded-pill px-4"><i class="bi bi-arrow-left"></i> Cancelar</a><button class="btn btn-primary rounded-pill px-4"><i class="bi bi-save"></i> Guardar evaluación</button></div>
      <div class="as-card card"><div class="card-body p-4">
        <div class="alert alert-info small">Cada período conserva su propia evaluación. La generación automática futura no sobrescribirá una evaluación que haya sido guardada manualmente.</div>
        <h5 class="fw-bold text-primary">{{ item.code }} · {{ item.name }}</h5>
        <div class="as-section">Período y responsable</div>
        <div class="row g-3">
          <div class="col-md-3"><label class="form-label">Inicio del período</label><input class="form-control" type="date" name="period_start" value="{{ evaluation.period_start }}" required></div>
          <div class="col-md-3"><label class="form-label">Fin del período</label><input class="form-control" type="date" name="period_end" value="{{ evaluation.period_end }}" required></div>
          <div class="col-md-3"><label class="form-label">Fecha de evaluación</label><input class="form-control" type="date" name="evaluation_date" value="{{ evaluation.evaluation_date }}" required></div>
          <div class="col-md-3"><label class="form-label">Evaluador</label><input class="form-control" name="evaluator" value="{{ evaluation.evaluator or '' }}"></div>
          <div class="col-md-8"><label class="form-label">Metodología</label><input class="form-control" name="methodology" value="{{ evaluation.methodology or 'Matriz 5x5 GRAC' }}"></div>
          <div class="col-md-4"><label class="form-label">Estado de evaluación</label><select class="form-select" name="status">{% for value in ['Vigente','En seguimiento','Cerrada','Reemplazada'] %}<option {{ 'selected' if evaluation.status==value else '' }}>{{ value }}</option>{% endfor %}</select></div>
        </div>
        <div class="as-section">Factores del período</div>
        <div class="row g-3">
          {% for field,label,value in factors %}<div class="col-6 col-md-2"><label class="form-label">{{ label }}</label><input class="form-control" type="number" min="1" max="5" name="{{ field }}" value="{{ value }}" required></div>{% endfor %}
          <div class="col-6 col-md-2"><label class="form-label">Eficacia control %</label><input class="form-control" type="number" min="0" max="100" name="control_effectiveness" value="{{ evaluation.control_effectiveness }}" required></div>
          <input type="hidden" name="severity" value="{{ item.severity }}">
        </div>
        <div class="as-section">Decisión y soporte</div>
        <div class="row g-3">
          <div class="col-md-6"><label class="form-label">Apetito</label><select class="form-select" name="risk_appetite">{% for value in ['Dentro de apetito','Por evaluar','Fuera de apetito'] %}<option {{ 'selected' if evaluation.risk_appetite==value else '' }}>{{ value }}</option>{% endfor %}</select></div>
          <div class="col-md-6"><label class="form-label">Tratamiento</label><select class="form-select" name="treatment">{% for value in ['Mitigar','Evitar','Transferir','Aceptar','Monitorear'] %}<option {{ 'selected' if evaluation.treatment==value else '' }}>{{ value }}</option>{% endfor %}</select></div>
          <div class="col-md-6"><label class="form-label">Justificación</label><textarea class="form-control" rows="4" name="justification">{{ evaluation.justification or '' }}</textarea></div>
          <div class="col-md-6"><label class="form-label">Controles revisados</label><textarea class="form-control" rows="4" name="controls_reviewed">{{ evaluation.controls_reviewed or '' }}</textarea></div>
          <div class="col-12"><label class="form-label">Observaciones</label><textarea class="form-control" rows="3" name="observations">{{ evaluation.observations or '' }}</textarea></div>
        </div>
        <div class="text-center mt-4"><button class="btn btn-primary rounded-pill px-5"><i class="bi bi-save"></i> Guardar evaluación del período</button></div>
      </div></div>
    </form>
    """, item=item, evaluation=evaluation, is_new=is_new, factors=[
        ("exposure_level", "Exposición", evaluation.exposure_level),
        ("exploitability", "Explotabilidad", evaluation.exploitability),
        ("detected_activity", "Actividad detectada", evaluation.detected_activity),
        ("control_weakness_level", "Debilidad control", evaluation.control_weakness_level),
        ("asset_criticality", "Criticidad activo", evaluation.asset_criticality),
    ])
    return attack_auto_shell(("Nueva" if is_new else "Editar") + " evaluación por período", body)


@app.route("/superficie_ataque/escenarios/<int:scenario_id>/evaluaciones/nueva", methods=["GET", "POST"])
@login_required
def attack_auto_evaluation_new(scenario_id):
    user, response = attack_auto_guard(write=True)
    if response:
        return response
    ensure_attack_auto_db()
    item = attack_auto_get_or_404(scenario_id)
    start, end = attack_auto_period_bounds()
    evaluation = AttackAutoEvaluation(
        scenario_id=item.id, period_start=start, period_end=end,
        evaluation_date=date.today().isoformat(), evaluator=getattr(user, "username", None),
        methodology="Matriz 5x5 GRAC", exposure_level=item.exposure_level,
        exploitability=item.exploitability, detected_activity=item.detected_activity,
        control_weakness_level=item.control_weakness_level, asset_criticality=item.asset_criticality,
        inherent_probability=item.inherent_probability, inherent_impact=item.inherent_impact,
        inherent_score=item.inherent_score, inherent_level=item.inherent_level,
        control_effectiveness=item.control_effectiveness, residual_probability=item.residual_probability,
        residual_impact=item.residual_impact, residual_score=item.residual_score,
        residual_level=item.residual_level, risk_appetite=item.risk_appetite,
        treatment=item.treatment, controls_reviewed=item.existing_controls, status="Vigente", origin="Manual",
    )
    if request.method == "POST":
        try:
            attack_auto_apply_evaluation_form(evaluation, request.form, user)
            duplicate = AttackAutoEvaluation.query.filter_by(
                scenario_id=item.id, period_start=evaluation.period_start, period_end=evaluation.period_end
            ).first()
            if duplicate:
                raise ValueError("Ya existe una evaluación para ese período; edite la existente")
            db.session.add(evaluation)
            db.session.commit()
            flash("Evaluación del período registrada correctamente.", "success")
            return redirect(url_for("attack_auto_view", scenario_id=item.id))
        except Exception as exc:
            db.session.rollback()
            flash("No fue posible guardar la evaluación: {}".format(attack_auto_clean(exc, 500)), "danger")
    return attack_auto_evaluation_form(item, evaluation, is_new=True)


@app.route("/superficie_ataque/escenarios/<int:scenario_id>/evaluaciones/<int:evaluation_id>/editar", methods=["GET", "POST"])
@login_required
def attack_auto_evaluation_edit(scenario_id, evaluation_id):
    user, response = attack_auto_guard(write=True)
    if response:
        return response
    ensure_attack_auto_db()
    item = attack_auto_get_or_404(scenario_id)
    evaluation = AttackAutoEvaluation.query.filter_by(id=evaluation_id, scenario_id=item.id).first()
    if not evaluation:
        abort(404)
    if request.method == "POST":
        try:
            attack_auto_apply_evaluation_form(evaluation, request.form, user)
            duplicate = AttackAutoEvaluation.query.filter(
                AttackAutoEvaluation.scenario_id == item.id,
                AttackAutoEvaluation.period_start == evaluation.period_start,
                AttackAutoEvaluation.period_end == evaluation.period_end,
                AttackAutoEvaluation.id != evaluation.id,
            ).first()
            if duplicate:
                raise ValueError("Ya existe otra evaluación para ese período")
            db.session.commit()
            flash("Evaluación del período actualizada.", "success")
            return redirect(url_for("attack_auto_view", scenario_id=item.id))
        except Exception as exc:
            db.session.rollback()
            flash("No fue posible actualizar la evaluación: {}".format(attack_auto_clean(exc, 500)), "danger")
    return attack_auto_evaluation_form(item, evaluation, is_new=False)


@app.route("/superficie_ataque/escenarios/<int:scenario_id>/evaluaciones/<int:evaluation_id>/eliminar", methods=["POST"])
@login_required
def attack_auto_evaluation_delete(scenario_id, evaluation_id):
    user, response = attack_auto_guard(write=True)
    if response:
        return response
    ensure_attack_auto_db()
    item = attack_auto_get_or_404(scenario_id)
    evaluation = AttackAutoEvaluation.query.filter_by(id=evaluation_id, scenario_id=item.id).first()
    if not evaluation:
        abort(404)
    db.session.delete(evaluation)
    db.session.commit()
    flash("Evaluación del período eliminada.", "success")
    return redirect(url_for("attack_auto_view", scenario_id=item.id))

# ============================================================================
# FIN SUPERFICIE DE ATAQUE Y ESCENARIOS
# ============================================================================
# ============================================================================================================================================

# =========================
# INICIO
# =========================
UPLOAD_FOLDER = os.path.join("static", "uploads", "profiles")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


import csv
import hashlib
import io
import json
import os
import re
import socket
import sqlite3
import ssl
import uuid
from collections import defaultdict, deque
from datetime import date, datetime, timedelta, timezone
from functools import wraps

from cryptography.fernet import Fernet, InvalidToken
from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template_string,
    request,
    send_file,
    session,
    url_for,
)
from markupsafe import Markup, escape


AD_MODULE_NAME = "Cumplimiento Continuo"
AD_PLATFORM_SAMBA = "SAMBA"
AD_PLATFORM_WINDOWS = "WINDOWS"
AD_CONNECTION_LDAP = "LDAP"
AD_PLATFORM_LABELS = {
    AD_PLATFORM_SAMBA: "Active Directory Samba",
    AD_PLATFORM_WINDOWS: "Active Directory Windows",
}
AD_PRIVILEGED_GROUPS = {
    "administrators",
    "domain admins",
    "enterprise admins",
    "schema admins",
    "account operators",
    "server operators",
    "backup operators",
    "dnsadmins",
    "group policy creator owners",
}
AD_SEVERITY_ORDER = {"Crítica": 4, "Alta": 3, "Media": 2, "Baja": 1, "Informativa": 0}
AD_UAC_DISABLED = 0x0002
AD_UAC_LOCKOUT = 0x0010
AD_UAC_PASSWORD_NOT_REQUIRED = 0x0020
AD_UAC_PASSWORD_CANNOT_CHANGE = 0x0040
AD_UAC_NORMAL_ACCOUNT = 0x0200
AD_UAC_DONT_EXPIRE_PASSWORD = 0x10000


AD_STYLE = """
<style>
  .adg-shell{width:96%;max-width:1650px;margin:10px auto 24px auto;padding:0}
  .adg-hero{
    background:linear-gradient(135deg,rgba(11,58,110,.97),rgba(20,89,166,.95),rgba(44,123,229,.92));
    border-radius:18px;padding:16px 24px;min-height:94px;display:flex;align-items:center;
    justify-content:flex-start;gap:14px;box-shadow:0 12px 24px rgba(15,23,42,.24);
    color:#fff;position:relative;overflow:hidden;margin-bottom:12px
  }
  .adg-hero::before{
    content:"";position:absolute;inset:0;background:
      radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 26%),
      repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0,rgba(255,255,255,.05) 1px,transparent 1px,transparent 15px);
    pointer-events:none
  }
  .adg-hero-icon{
    width:54px;height:54px;min-width:54px;border-radius:14px;background:rgba(255,255,255,.96);
    color:#0b4a8f;display:flex;align-items:center;justify-content:center;font-size:1.55rem;
    box-shadow:0 8px 18px rgba(0,0,0,.20);position:relative;z-index:1
  }
  .adg-hero-text{position:relative;z-index:1;min-width:0}
  .adg-module-kicker{
    display:inline-block;background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.30);
    border-radius:999px;padding:3px 10px;font-size:.66rem;font-weight:800;letter-spacing:.35px;margin-bottom:4px
  }
  .adg-hero h2{color:#fff!important;font-weight:950;font-size:1.36rem;line-height:1.08;margin:0}
  .adg-hero p{margin:5px 0 0;color:rgba(255,255,255,.90);font-size:.82rem;font-weight:600}
  .adg-module-nav{
    background:rgba(255,255,255,.97);border:1px solid rgba(219,230,244,.98);border-radius:16px;
    box-shadow:0 8px 20px rgba(15,23,42,.10);padding:10px 12px;margin-bottom:14px
  }
  .adg-actions{display:flex;flex-wrap:wrap;gap:9px;margin-top:0}
  .adg-btn{display:inline-flex;align-items:center;justify-content:center;gap:7px;border-radius:999px;
    padding:9px 15px;text-decoration:none;font-size:.82rem;font-weight:750;border:1px solid transparent}
  .adg-btn-primary{background:#0d6efd;color:#fff}.adg-btn-primary:hover{background:#0959cb;color:#fff}
  .adg-btn-light{background:#f4f8fe;color:#0b4a8f;border-color:#d2e2f4}.adg-btn-light:hover{background:#e7f1fd;color:#062b55}
  .adg-btn-danger{background:#dc3545;color:#fff}.adg-btn-danger:hover{background:#b92d3a;color:#fff}
  .adg-btn-success{background:#198754;color:#fff}.adg-btn-success:hover{background:#146c43;color:#fff}
  .adg-btn-warning{background:#ffc107;color:#3b2c00}.adg-btn-warning:hover{background:#e5ac00;color:#231a00}
  .adg-btn-outline{background:#fff;color:#0b4a8f;border-color:#9cc5eb}.adg-btn-outline:hover{background:#e9f4ff;color:#062b55}
  .adg-grid{display:grid;grid-template-columns:repeat(6,minmax(150px,1fr));gap:14px;margin-top:14px}
  .adg-kpi,.adg-card{background:rgba(255,255,255,.96);border:1px solid rgba(169,205,235,.86);
    border-radius:18px;box-shadow:0 10px 24px rgba(16,42,75,.10)}
  .adg-kpi{padding:15px}.adg-kpi .value{font-size:1.55rem;font-weight:850;color:#0b4a8f}
  .adg-kpi .label{font-size:.76rem;color:#526d8c;font-weight:700}
  .adg-card{padding:16px;margin-top:14px}.adg-card h5{color:#0b4a8f;font-weight:800}
  .adg-table{font-size:.79rem}.adg-table th{background:#0b4a8f!important;color:#fff!important;
    white-space:nowrap;vertical-align:middle}.adg-table td{vertical-align:middle}
  .adg-table-wrap{overflow:auto;max-height:680px;border-radius:15px}
  .adg-muted{font-size:.78rem;color:#58718e}.adg-code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.73rem}
  .adg-chip{display:inline-flex;align-items:center;border-radius:999px;padding:4px 9px;font-weight:750;font-size:.7rem}
  .adg-chip-ok{background:#dff7e9;color:#12683e}.adg-chip-bad{background:#ffe3e7;color:#a51d2d}
  .adg-chip-warn{background:#fff1c9;color:#765700}.adg-chip-info{background:#dcecff;color:#0753a0}
  .adg-form label{font-size:.78rem;font-weight:750;color:#244565}
  .adg-form .form-control,.adg-form .form-select{border-radius:12px;border-color:#b8d3eb}
  .adg-actions-vertical{display:flex;flex-direction:column;align-items:stretch;gap:6px;min-width:175px}
  .adg-actions-vertical .adg-btn,.adg-actions-vertical button{width:100%;white-space:nowrap}
  .adg-detail{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
  .adg-detail-item{background:#f5f9fd;border:1px solid #d9e8f6;border-radius:13px;padding:12px}
  .adg-detail-item span{display:block;color:#58718e;font-size:.72rem;font-weight:700}
  .adg-detail-item strong{display:block;color:#173a5e;font-size:.83rem;overflow-wrap:anywhere}
  .adg-ai-panel{margin-top:16px;border:1px solid #b9d7f2;border-radius:18px;overflow:hidden;background:#f8fbff;box-shadow:0 8px 20px rgba(11,74,143,.09)}
  .adg-ai-header{display:flex;align-items:center;gap:10px;padding:13px 16px;background:linear-gradient(135deg,#e5f2ff,#f4f9ff);border-bottom:1px solid #cfe3f6;color:#0b4a8f}
  .adg-ai-header i{font-size:1.2rem}.adg-ai-header strong{font-size:.92rem}.adg-ai-header span{font-size:.72rem;color:#55718d}
  .adg-ai-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;padding:14px}
  .adg-ai-section{background:#fff;border:1px solid #d9e8f6;border-radius:14px;padding:13px 14px;min-width:0}
  .adg-ai-section h6{display:flex;align-items:center;gap:8px;color:#0b4a8f;font-weight:850;font-size:.82rem;margin:0 0 8px}
  .adg-ai-section p{font-size:.8rem;line-height:1.48;color:#294a68;margin:0;white-space:pre-line}
  .adg-ai-section ul{padding-left:18px;margin:0}.adg-ai-section li{font-size:.79rem;line-height:1.45;color:#294a68;margin-bottom:5px}
  .adg-ai-section-wide{grid-column:1/-1}
  @media(max-width:900px){.adg-ai-grid{grid-template-columns:1fr}.adg-ai-section-wide{grid-column:auto}}
  @media(max-width:1200px){.adg-grid{grid-template-columns:repeat(3,1fr)}}
  @media(max-width:720px){.adg-grid{grid-template-columns:repeat(2,1fr)}.adg-detail{grid-template-columns:1fr}.adg-shell{width:calc(100% - 20px)}.adg-hero{padding:14px 16px}.adg-hero-icon{width:48px;height:48px;min-width:48px}}
</style>
"""


def register_ad_governance(
    app,
    base_template,
    user_model,
    permission_checker=None,
    audit_logger=None,
    plan_model=None,
    orm_db=None,
    risk_model=None,
    risk_type_model=None,
    ai_helper=None,
):
    """Registra Gobierno de AD Samba y Microsoft Windows en el mismo archivo de GRAC, mediante LDAP/LDAPS directo."""

    db_path = os.path.join(app.instance_path, "ad_governance.db")
    key_path = os.path.join(app.instance_path, "ad_governance.key")
    os.makedirs(app.instance_path, exist_ok=True)

    def db_conn():
        conn = sqlite3.connect(db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def init_db():
        schema = """
        CREATE TABLE IF NOT EXISTS ad_connectors (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          platform TEXT NOT NULL DEFAULT 'SAMBA',
          connection_mode TEXT NOT NULL DEFAULT 'LDAP',
          host TEXT NOT NULL,
          port INTEGER NOT NULL DEFAULT 389,
          use_ssl INTEGER NOT NULL DEFAULT 0,
          verify_ssl INTEGER NOT NULL DEFAULT 0,
          ca_cert_path TEXT,
          base_dn TEXT NOT NULL,
          bind_user TEXT NOT NULL,
          bind_password_encrypted TEXT,
          connect_timeout INTEGER NOT NULL DEFAULT 15,
          inactive_days INTEGER NOT NULL DEFAULT 90,
          password_age_days INTEGER NOT NULL DEFAULT 90,
          enabled INTEGER NOT NULL DEFAULT 1,
          last_status TEXT DEFAULT 'No probado',
          last_message TEXT,
          last_test_at TEXT,
          last_sync_at TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS ad_users (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          connector_id INTEGER NOT NULL,
          object_guid TEXT NOT NULL,
          distinguished_name TEXT NOT NULL,
          sam_account_name TEXT,
          user_principal_name TEXT,
          display_name TEXT,
          given_name TEXT,
          surname TEXT,
          mail TEXT,
          department TEXT,
          title TEXT,
          description TEXT,
          user_account_control INTEGER DEFAULT 0,
          enabled INTEGER NOT NULL DEFAULT 1,
          locked INTEGER NOT NULL DEFAULT 0,
          password_never_expires INTEGER NOT NULL DEFAULT 0,
          password_not_required INTEGER NOT NULL DEFAULT 0,
          service_account INTEGER NOT NULL DEFAULT 0,
          generic_account INTEGER NOT NULL DEFAULT 0,
          privileged INTEGER NOT NULL DEFAULT 0,
          privilege_type TEXT,
          privilege_path TEXT,
          when_created TEXT,
          when_changed TEXT,
          pwd_last_set TEXT,
          last_logon TEXT,
          account_expires TEXT,
          direct_groups_json TEXT,
          raw_json TEXT,
          active INTEGER NOT NULL DEFAULT 1,
          first_seen_at TEXT NOT NULL,
          last_seen_at TEXT NOT NULL,
          UNIQUE(connector_id, object_guid),
          FOREIGN KEY(connector_id) REFERENCES ad_connectors(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS ad_groups (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          connector_id INTEGER NOT NULL,
          object_guid TEXT NOT NULL,
          distinguished_name TEXT NOT NULL,
          sam_account_name TEXT,
          display_name TEXT,
          description TEXT,
          group_type TEXT,
          privileged INTEGER NOT NULL DEFAULT 0,
          member_count INTEGER NOT NULL DEFAULT 0,
          members_json TEXT,
          active INTEGER NOT NULL DEFAULT 1,
          first_seen_at TEXT NOT NULL,
          last_seen_at TEXT NOT NULL,
          UNIQUE(connector_id, object_guid),
          FOREIGN KEY(connector_id) REFERENCES ad_connectors(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS ad_memberships (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          connector_id INTEGER NOT NULL,
          group_dn TEXT NOT NULL,
          member_dn TEXT NOT NULL,
          member_type TEXT,
          detected_at TEXT NOT NULL,
          UNIQUE(connector_id, group_dn, member_dn),
          FOREIGN KEY(connector_id) REFERENCES ad_connectors(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS ad_findings (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          connector_id INTEGER NOT NULL,
          user_id INTEGER,
          finding_key TEXT NOT NULL,
          finding_code TEXT NOT NULL,
          severity TEXT NOT NULL,
          title TEXT NOT NULL,
          description TEXT,
          recommendation TEXT,
          control_mapping TEXT,
          status TEXT NOT NULL DEFAULT 'Abierto',
          assigned_to TEXT,
          management_comment TEXT,
          ai_analysis TEXT,
          plan_id INTEGER,
          risk_id INTEGER,
          active INTEGER NOT NULL DEFAULT 1,
          first_detected_at TEXT NOT NULL,
          last_detected_at TEXT NOT NULL,
          resolved_at TEXT,
          UNIQUE(connector_id, finding_key),
          FOREIGN KEY(connector_id) REFERENCES ad_connectors(id) ON DELETE CASCADE,
          FOREIGN KEY(user_id) REFERENCES ad_users(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS ad_sync_logs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          connector_id INTEGER NOT NULL,
          started_at TEXT NOT NULL,
          finished_at TEXT,
          status TEXT NOT NULL,
          message TEXT,
          users_received INTEGER DEFAULT 0,
          groups_received INTEGER DEFAULT 0,
          memberships_received INTEGER DEFAULT 0,
          findings_active INTEGER DEFAULT 0,
          critical_findings INTEGER DEFAULT 0,
          high_findings INTEGER DEFAULT 0,
          compliance_score REAL DEFAULT 100,
          executed_by TEXT,
          FOREIGN KEY(connector_id) REFERENCES ad_connectors(id) ON DELETE CASCADE
        );
        """
        with db_conn() as conn:
            conn.executescript(schema)
            # Migración compatible con instalaciones existentes.
            connector_columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(ad_connectors)").fetchall()
            }
            migrations = {
                "platform": "TEXT NOT NULL DEFAULT 'SAMBA'",
                "connection_mode": "TEXT NOT NULL DEFAULT 'LDAP'",
            }
            for column_name, definition in migrations.items():
                if column_name not in connector_columns:
                    conn.execute(
                        f"ALTER TABLE ad_connectors ADD COLUMN {column_name} {definition}"
                    )
            conn.execute(
                """UPDATE ad_connectors
                   SET platform=COALESCE(NULLIF(UPPER(platform),''),'SAMBA'),
                       connection_mode='LDAP'"""
            )
            conn.commit()

    init_db()

    def now_iso():
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    def normalize_platform(value, default=AD_PLATFORM_SAMBA):
        normalized = str(value or "").strip().upper()
        aliases = {
            "SAMBA": AD_PLATFORM_SAMBA,
            "ACTIVE DIRECTORY SAMBA": AD_PLATFORM_SAMBA,
            "WINDOWS": AD_PLATFORM_WINDOWS,
            "MICROSOFT": AD_PLATFORM_WINDOWS,
            "MICROSOFT WINDOWS": AD_PLATFORM_WINDOWS,
            "ACTIVE DIRECTORY WINDOWS": AD_PLATFORM_WINDOWS,
        }
        return aliases.get(normalized, default)

    def platform_label(value):
        return AD_PLATFORM_LABELS.get(normalize_platform(value), AD_PLATFORM_LABELS[AD_PLATFORM_SAMBA])

    def request_platform(default=AD_PLATFORM_SAMBA):
        return normalize_platform(request.args.get("platform") or request.form.get("platform"), default)


    def normalize_ldap_host(raw_host):
        """Normaliza host LDAP/LDAPS sin resolverlo durante el guardado."""
        text = str(raw_host or "").strip()
        if not text:
            return ""

        # Permite que el usuario pegue ldap://host:389 o ldaps://host:636.
        if "://" in text:
            parsed = urlparse(text)
            text = parsed.hostname or ""
        else:
            text = text.split("/", 1)[0].strip()
            # Quita :puerto únicamente para host IPv4/FQDN.
            if text.count(":") == 1:
                candidate, possible_port = text.rsplit(":", 1)
                if possible_port.isdigit():
                    text = candidate
            # Conserva IPv6 entre corchetes sin los corchetes.
            if text.startswith("[") and text.endswith("]"):
                text = text[1:-1]

        return text.strip().rstrip(".")

    def validate_ldap_host(host):
        if not host:
            raise ValueError("El host o IP del controlador de dominio es obligatorio.")
        try:
            ipaddress.ip_address(host)
            return
        except ValueError:
            pass
        if len(host) > 253:
            raise ValueError("El nombre del controlador de dominio es demasiado largo.")
        labels = host.split(".")
        hostname_re = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")
        if not all(hostname_re.match(label or "") for label in labels):
            raise ValueError(
                "Host inválido. Ingrese solamente una IP o un FQDN, por ejemplo "
                "10.20.1.43 o dc1.adlab.arkyntech.com; no incluya rutas ni espacios."
            )

    def ldap_resolution_message(connector, exc):
        host = normalize_ldap_host(connector["host"] if connector else "")
        platform = normalize_platform(connector["platform"] if connector and "platform" in connector.keys() else AD_PLATFORM_SAMBA)
        base = f"No fue posible resolver el host '{host}' desde el servidor donde se ejecuta GRAC."
        if platform == AD_PLATFORM_WINDOWS:
            return (
                base + " El nombre dc1.adlab.arkyntech.com pertenece al DNS interno de Active Directory. "
                "Si GRAC está en Render, use un FQDN o una IP alcanzable desde Internet y publique únicamente "
                "LDAPS por TCP 636 con certificado y reglas de origen restringidas. Si GRAC está en la misma red "
                "o conectado por VPN, configure su DNS para resolver la zona adlab.arkyntech.com. "
                f"Detalle técnico: {exc}"
            )
        return base + f" Verifique DNS, VPN, ruta y conectividad. Detalle técnico: {exc}"

    def current_user():
        try:
            return user_model.query.get(session.get("user_id"))
        except Exception:
            return None

    def username(user=None):
        return (
            getattr(user, "username", None)
            or session.get("username")
            or "Sistema"
        )

    def can_read(user):
        if not user:
            return False
        if getattr(user, "role", "") in ("admin", "auditor"):
            return True
        if permission_checker:
            try:
                return bool(permission_checker(user, AD_MODULE_NAME))
            except Exception:
                return False
        return False

    def can_write(user):
        if not user or getattr(user, "role", "") == "auditor":
            return False
        if getattr(user, "role", "") == "admin":
            return True
        if permission_checker:
            try:
                return bool(permission_checker(user, AD_MODULE_NAME))
            except Exception:
                return False
        return False

    def audit(message, user=None):
        if audit_logger:
            try:
                audit_logger(username(user), message)
            except Exception:
                pass

    def require_access(write=False):
        def decorator(fn):
            @wraps(fn)
            def wrapped(*args, **kwargs):
                if "user_id" not in session:
                    flash("Por favor, inicia sesión.", "warning")
                    return redirect(url_for("login"))
                user = current_user()
                allowed = can_write(user) if write else can_read(user)
                if not allowed:
                    flash(
                        "No tiene permiso para modificar Gobierno del Directorio Activo."
                        if write else
                        "No tiene permiso para consultar Gobierno del Directorio Activo.",
                        "danger",
                    )
                    return redirect(url_for("menu"))
                return fn(*args, **kwargs)
            return wrapped
        return decorator

    def get_fernet():
        env_key = (os.getenv("AD_GOV_FERNET_KEY") or "").strip()
        if env_key:
            return Fernet(env_key.encode("utf-8"))
        if os.path.exists(key_path):
            with open(key_path, "rb") as fh:
                key = fh.read().strip()
        else:
            key = Fernet.generate_key()
            with open(key_path, "wb") as fh:
                fh.write(key)
            try:
                os.chmod(key_path, 0o600)
            except Exception:
                pass
        return Fernet(key)

    def encrypt_secret(value):
        value = (value or "").strip()
        return get_fernet().encrypt(value.encode()).decode() if value else None

    def decrypt_secret(value):
        if not value:
            return ""
        try:
            return get_fernet().decrypt(value.encode()).decode()
        except (InvalidToken, ValueError, TypeError):
            return ""

    def fetchone(sql, params=()):
        with db_conn() as conn:
            return conn.execute(sql, params).fetchone()

    def fetchall(sql, params=()):
        with db_conn() as conn:
            return conn.execute(sql, params).fetchall()

    def connector_or_404(connector_id):
        row = fetchone("SELECT * FROM ad_connectors WHERE id=?", (connector_id,))
        if not row:
            abort(404)
        return row

    def html_badge(value, kind="info"):
        return Markup(f'<span class="adg-chip adg-chip-{kind}">{escape(str(value))}</span>')

    def severity_badge(severity):
        kind = {
            "Crítica": "bad",
            "Alta": "warn",
            "Media": "info",
            "Baja": "ok",
        }.get(severity, "info")
        return html_badge(severity, kind)

    def ad_ai_extract_payload(value):
        raw = str(value or "").strip()
        if not raw:
            return {}
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.I)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start >= 0 and end > start:
            try:
                payload = json.loads(cleaned[start:end + 1])
                if isinstance(payload, dict):
                    return payload
            except Exception:
                pass

        # Compatibilidad con análisis anteriores en texto libre.
        headings = {
            "resumen ejecutivo": "resumen_ejecutivo",
            "causa probable": "causa_probable",
            "riesgo de negocio": "riesgo_negocio",
            "validaciones": "validaciones",
            "remediacion priorizada": "remediacion_priorizada",
            "remediación priorizada": "remediacion_priorizada",
            "evidencia de cierre": "evidencia_cierre",
            "metricas": "metricas",
            "métricas": "metricas",
            "controles relacionados": "controles_relacionados",
        }
        parsed = {}
        current = None
        for original_line in raw.splitlines():
            line = original_line.strip()
            if not line:
                continue
            line = re.sub(r"^[#*\-\s]+", "", line).strip()
            match = re.match(r"^(?:\d+[\.\)]\s*)?([^:]{3,45})\s*:\s*(.*)$", line)
            if match:
                heading = unicodedata.normalize("NFKD", match.group(1)).encode("ascii", "ignore").decode().lower().strip()
                key = headings.get(heading)
                if key:
                    current = key
                    parsed.setdefault(key, [])
                    if match.group(2).strip():
                        parsed[key].append(match.group(2).strip())
                    continue
            if current:
                parsed.setdefault(current, []).append(re.sub(r"^[•\-]\s*", "", line))
            else:
                parsed.setdefault("resumen_ejecutivo", []).append(line)

        for key, content in list(parsed.items()):
            if isinstance(content, list) and len(content) == 1:
                parsed[key] = content[0]
        return parsed or {"resumen_ejecutivo": raw}

    def ad_ai_value_items(value):
        if value is None:
            return []
        if isinstance(value, list):
            result = []
            for item in value:
                if isinstance(item, dict):
                    parts = []
                    for key in ("prioridad", "accion", "responsable", "plazo", "indicador", "meta", "validacion", "evidencia"):
                        if item.get(key):
                            label = key.replace("_", " ").capitalize()
                            parts.append(f"{label}: {item.get(key)}")
                    if not parts:
                        parts = [f"{k}: {v}" for k, v in item.items() if v not in (None, "", [], {})]
                    if parts:
                        result.append(" · ".join(str(part) for part in parts))
                elif str(item or "").strip():
                    result.append(str(item).strip())
            return result
        if isinstance(value, dict):
            return ["{}: {}".format(str(k).replace("_", " ").capitalize(), v) for k, v in value.items()]
        text_value = str(value or "").strip()
        if not text_value:
            return []
        lines = [re.sub(r"^[•\-]\s*", "", line).strip() for line in text_value.splitlines() if line.strip()]
        return lines or [text_value]

    def ad_ai_sections(value):
        payload = ad_ai_extract_payload(value)
        specs = [
            ("resumen_ejecutivo", "Resumen ejecutivo", "bi-clipboard-data", True),
            ("causa_probable", "Causa probable", "bi-search", False),
            ("riesgo_negocio", "Riesgo para el negocio", "bi-building-exclamation", False),
            ("validaciones", "Validaciones técnicas", "bi-check2-square", False),
            ("remediacion_priorizada", "Remediación priorizada", "bi-list-check", True),
            ("evidencia_cierre", "Evidencia requerida para cierre", "bi-file-earmark-check", False),
            ("metricas", "Métricas y seguimiento", "bi-graph-up-arrow", False),
            ("controles_relacionados", "Controles relacionados", "bi-shield-check", False),
        ]
        sections = []
        for key, title, icon, wide in specs:
            items = ad_ai_value_items(payload.get(key))
            if items:
                sections.append({
                    "key": key,
                    "title": title,
                    "icon": icon,
                    "items": items,
                    "wide": wide,
                })
        if not sections and str(value or "").strip():
            sections.append({
                "key": "resumen_ejecutivo",
                "title": "Análisis complementario",
                "icon": "bi-stars",
                "items": [str(value).strip()],
                "wide": True,
            })
        return sections

    def ad_ai_normalized_json(value):
        payload = ad_ai_extract_payload(value)
        allowed = {
            "resumen_ejecutivo", "causa_probable", "riesgo_negocio", "validaciones",
            "remediacion_priorizada", "evidencia_cierre", "metricas", "controles_relacionados",
        }
        normalized = {key: payload.get(key) for key in allowed if payload.get(key) not in (None, "", [], {})}
        if not normalized:
            normalized = {"resumen_ejecutivo": str(value or "").strip()}
        return json.dumps(normalized, ensure_ascii=False, indent=2)

    def page(content, title, subtitle="", platform=None):
        user = current_user()
        platform = normalize_platform(platform or request.args.get("platform"), AD_PLATFORM_SAMBA)
        header = render_template_string(
            """
            {{ style|safe }}
            <div class="adg-shell">
              <div class="adg-hero">
                <div class="adg-hero-icon"><i class="bi bi-person-lock"></i></div>
                <div class="adg-hero-text">
                  <span class="adg-module-kicker">SGSI · Gobierno de Identidades · {{ platform_label }}</span>
                  <h2>{{ title }}</h2>
                  <p>{{ subtitle }}</p>
                </div>
              </div>
              <div class="adg-module-nav" data-keep-cumplimiento-nav="true">
                <div class="adg-actions mb-2">
                  <a class="adg-btn {{ 'adg-btn-primary' if platform=='SAMBA' else 'adg-btn-light' }}" href="{{ url_for('adgov.samba_home') }}"><i class="bi bi-hdd-network"></i> Active Directory Samba</a>
                  <a class="adg-btn {{ 'adg-btn-primary' if platform=='WINDOWS' else 'adg-btn-light' }}" href="{{ url_for('adgov.windows_home') }}"><i class="bi bi-windows"></i> Active Directory Windows</a>
                </div>
                <div class="adg-actions">
                  <a class="adg-btn adg-btn-light" href="{{ url_for('adgov.dashboard', platform=platform) }}"><i class="bi bi-speedometer2"></i> Dashboard</a>
                  <a class="adg-btn adg-btn-light" href="{{ url_for('adgov.users', platform=platform) }}"><i class="bi bi-people"></i> Usuarios</a>
                  <a class="adg-btn adg-btn-light" href="{{ url_for('adgov.groups', platform=platform) }}"><i class="bi bi-diagram-3"></i> Grupos</a>
                  <a class="adg-btn adg-btn-light" href="{{ url_for('adgov.findings', platform=platform) }}"><i class="bi bi-shield-exclamation"></i> Hallazgos</a>
                  <a class="adg-btn adg-btn-light" href="{{ url_for('attack_auto', source='ACTIVE_DIRECTORY', ad_platform=platform) }}"><i class="bi bi-bullseye"></i> Superficie de Ataque</a>
                  <a class="adg-btn adg-btn-light" href="{{ url_for('threat_model_dashboard', herramienta='active_directory', ad_platform=platform) }}"><i class="bi bi-diagram-3-fill"></i> Modelamiento de Amenazas</a>
                  <a class="adg-btn adg-btn-light" href="{{ url_for('adgov.history', platform=platform) }}"><i class="bi bi-clock-history"></i> Historial</a>
                  {% if can_write %}<a class="adg-btn adg-btn-light" href="{{ url_for('adgov.config', platform=platform) }}"><i class="bi bi-gear"></i> Configuración</a>{% endif %}
                </div>
              </div>
              {{ content|safe }}
            </div>
            """,
            style=Markup(AD_STYLE),
            title=title,
            subtitle=subtitle,
            content=Markup(content),
            can_write=can_write(user),
            platform=platform,
            platform_label=platform_label(platform),
        )
        return render_template_string(base_template, content=Markup(header))

    def require_ldap3():
        try:
            from ldap3 import ALL, BASE, SUBTREE, Connection, Server, Tls
            return {
                "ALL": ALL,
                "BASE": BASE,
                "SUBTREE": SUBTREE,
                "Connection": Connection,
                "Server": Server,
                "Tls": Tls,
            }
        except ImportError as exc:
            raise RuntimeError(
                "Falta la dependencia ldap3. Instálela con: python3 -m pip install ldap3"
            ) from exc

    def ldap_connection(connector):
        ldap = require_ldap3()
        host = normalize_ldap_host(connector["host"])
        validate_ldap_host(host)
        password = decrypt_secret(connector["bind_password_encrypted"])
        if not password:
            raise ValueError("No existe una contraseña válida guardada para el conector.")
        use_ssl = bool(connector["use_ssl"])
        verify_ssl = bool(connector["verify_ssl"])
        tls = ldap["Tls"](
            validate=ssl.CERT_REQUIRED if verify_ssl else ssl.CERT_NONE,
            ca_certs_file=(connector["ca_cert_path"] or "").strip() or None,
        )
        server = ldap["Server"](
            host,
            port=int(connector["port"] or (636 if use_ssl else 389)),
            use_ssl=use_ssl,
            tls=tls,
            get_info=ldap["ALL"],
            connect_timeout=int(connector["connect_timeout"] or 15),
        )
        connection = ldap["Connection"](
            server,
            user=(connector["bind_user"] or "").strip(),
            password=password,
            auto_bind=True,
            receive_timeout=int(connector["connect_timeout"] or 15),
            raise_exceptions=True,
        )
        return connection, ldap

    def value(attrs, key, default=None):
        raw = attrs.get(key, default)
        if isinstance(raw, list):
            return raw[0] if raw else default
        return raw

    def values(attrs, key):
        raw = attrs.get(key, [])
        if raw is None:
            return []
        return raw if isinstance(raw, list) else [raw]

    def text_value(raw):
        if raw is None:
            return ""
        if isinstance(raw, bytes):
            try:
                return str(uuid.UUID(bytes_le=raw))
            except Exception:
                return raw.hex()
        return str(raw)

    def int_value(raw, default=0):
        try:
            return int(raw)
        except Exception:
            try:
                return int(str(raw))
            except Exception:
                return default

    def ad_datetime(raw):
        if raw in (None, "", 0, "0", 9223372036854775807, "9223372036854775807"):
            return ""
        if isinstance(raw, datetime):
            if raw.tzinfo is None:
                raw = raw.replace(tzinfo=timezone.utc)
            return raw.astimezone(timezone.utc).replace(microsecond=0).isoformat()
        if isinstance(raw, date):
            return datetime(raw.year, raw.month, raw.day, tzinfo=timezone.utc).isoformat()
        text = str(raw).strip()
        if re.fullmatch(r"\d{12,18}", text):
            try:
                ticks = int(text)
                if ticks <= 0 or ticks >= 9223372036854775807:
                    return ""
                unix_seconds = (ticks - 116444736000000000) / 10000000
                return datetime.fromtimestamp(unix_seconds, tz=timezone.utc).replace(microsecond=0).isoformat()
            except Exception:
                return ""
        return text

    def parse_iso(raw):
        if not raw:
            return None
        try:
            return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except Exception:
            return None

    def entry_attributes(entry):
        if isinstance(entry, dict):
            return entry.get("attributes") or {}
        return {}

    def is_service_account(sam, dn, description):
        joined = " ".join([sam or "", dn or "", description or ""]).lower()
        return (
            (sam or "").lower().startswith(("svc_", "svc-", "service.", "sa_"))
            or "ou=cuentasservicio" in joined
            or "cuenta de servicio" in joined
            or "service account" in joined
        )

    def is_generic_account(sam, display_name, description):
        joined = " ".join([sam or "", display_name or "", description or ""]).lower()
        patterns = (
            "generico", "genérico", "generic", "compartida", "compartido",
            "shared account", "usuario.generico", "operaciones@", "turno",
        )
        return any(pattern in joined for pattern in patterns)

    def finding_key(connector_id, code, object_guid):
        payload = f"{connector_id}|{code}|{object_guid}".encode()
        return hashlib.sha256(payload).hexdigest()

    def add_finding(target, connector_id, user_guid, code, severity, title, description, recommendation, controls):
        target.append({
            "finding_key": finding_key(connector_id, code, user_guid),
            "finding_code": code,
            "user_guid": user_guid,
            "severity": severity,
            "title": title,
            "description": description,
            "recommendation": recommendation,
            "control_mapping": controls,
        })

    def build_findings(connector, users):
        findings = []
        now = datetime.now(timezone.utc)
        inactive_days = int(connector["inactive_days"] or 90)
        password_age_days = int(connector["password_age_days"] or 90)
        for item in users:
            guid = item["object_guid"]
            sam = item["sam_account_name"] or item["display_name"] or guid
            if item["locked"] and item["enabled"]:
                add_finding(
                    findings, connector["id"], guid, "ACCOUNT_LOCKED", "Media",
                    f"Cuenta bloqueada: {sam}",
                    "La cuenta se encuentra bloqueada por eventos de autenticación fallida.",
                    "Confirmar la identidad del usuario, investigar los intentos fallidos y desbloquear solo después de validar el evento.",
                    "ISO 27001 A.5.15/A.8.16; NIST CSF PR.AA/DE.CM; SOC 2 CC6/CC7; PCI DSS 8.3.4",
                )
            if item["enabled"] and item["generic_account"]:
                add_finding(
                    findings, connector["id"], guid, "GENERIC_SHARED_ACCOUNT", "Alta",
                    f"Cuenta genérica o compartida activa: {sam}",
                    "El nombre o la descripción indican que la cuenta puede ser compartida y reducir la trazabilidad individual.",
                    "Sustituirla por cuentas nominativas o documentar excepción, custodio, rotación, MFA y trazabilidad de uso.",
                    "ISO 27001 A.5.16/A.5.18; NIST CSF PR.AA; SOC 2 CC6; PCI DSS 8.2.1/8.2.2",
                )
            if item["password_not_required"] and item["enabled"]:
                add_finding(
                    findings, connector["id"], guid, "PASSWORD_NOT_REQUIRED", "Crítica",
                    f"Contraseña no requerida: {sam}",
                    "La bandera de la cuenta permite que no se requiera contraseña.",
                    "Retirar inmediatamente la configuración PASSWD_NOTREQD, establecer una contraseña robusta y revisar actividad reciente.",
                    "ISO 27001 A.5.17/A.8.5; NIST CSF PR.AA; SOC 2 CC6; PCI DSS 8.3/8.3.6",
                )
            if item["password_never_expires"] and item["enabled"]:
                severity = "Media" if item["service_account"] else "Alta"
                add_finding(
                    findings, connector["id"], guid, "PASSWORD_NEVER_EXPIRES", severity,
                    f"Contraseña configurada para no expirar: {sam}",
                    "La cuenta tiene activa la bandera DONT_EXPIRE_PASSWORD.",
                    "Aplicar rotación controlada. Para cuentas técnicas, documentar propietario, bóveda, uso, alcance y periodicidad de rotación.",
                    "ISO 27001 A.5.17/A.8.5; NIST CSF PR.AA; SOC 2 CC6; PCI DSS 8.3.9",
                )
            pwd_date = parse_iso(item["pwd_last_set"])
            if item["enabled"] and pwd_date and (now - pwd_date).days > password_age_days:
                add_finding(
                    findings, connector["id"], guid, "STALE_PASSWORD", "Alta",
                    f"Contraseña con antigüedad elevada: {sam}",
                    f"La contraseña tiene aproximadamente {(now - pwd_date).days} días, superior al umbral de {password_age_days}.",
                    "Rotar la contraseña y validar que la política de credenciales se aplique a la cuenta.",
                    "ISO 27001 A.5.17/A.8.5; NIST CSF PR.AA; SOC 2 CC6; PCI DSS 8.3.9",
                )
            last_logon = parse_iso(item["last_logon"])
            created = parse_iso(item["when_created"])
            if item["enabled"] and last_logon and (now - last_logon).days > inactive_days:
                add_finding(
                    findings, connector["id"], guid, "STALE_ACTIVE_ACCOUNT", "Alta",
                    f"Cuenta activa sin uso reciente: {sam}",
                    f"El último inicio de sesión conocido supera el umbral de {inactive_days} días.",
                    "Validar vigencia con el propietario y deshabilitar o retirar la cuenta si ya no se necesita.",
                    "ISO 27001 A.5.18; NIST CSF PR.AA; SOC 2 CC6; PCI DSS 8.2.6",
                )
            elif item["enabled"] and not last_logon and created and (now - created).days > 30:
                add_finding(
                    findings, connector["id"], guid, "NEVER_USED_ACTIVE_ACCOUNT", "Media",
                    f"Cuenta activa sin inicio de sesión: {sam}",
                    "La cuenta tiene más de 30 días y no registra un inicio de sesión conocido.",
                    "Confirmar su necesidad; deshabilitarla si fue creada por error o nunca fue entregada.",
                    "ISO 27001 A.5.18; NIST CSF PR.AA; SOC 2 CC6; PCI DSS 8.2.6",
                )
            if item["service_account"] and item["privileged"] and item["enabled"]:
                add_finding(
                    findings, connector["id"], guid, "PRIVILEGED_SERVICE_ACCOUNT", "Crítica",
                    f"Cuenta de servicio con privilegios elevados: {sam}",
                    f"La cuenta técnica alcanza un grupo privilegiado por la ruta: {item['privilege_path'] or 'no documentada'}.",
                    "Retirar privilegios no indispensables, restringir inicio interactivo, rotar el secreto y usar una cuenta administrada cuando sea posible.",
                    "ISO 27001 A.5.15/A.8.2; NIST CSF PR.AA; SOC 2 CC6; PCI DSS 7.2.1/8.6.1",
                )
            elif item["privileged"] and item["privilege_type"] == "Anidado" and item["enabled"]:
                add_finding(
                    findings, connector["id"], guid, "NESTED_PRIVILEGE", "Alta",
                    f"Privilegio administrativo heredado: {sam}",
                    f"La cuenta obtiene privilegios mediante grupos anidados: {item['privilege_path']}.",
                    "Validar aprobación y necesidad del privilegio; retirar la membresía indirecta si no corresponde.",
                    "ISO 27001 A.5.15/A.8.2; NIST CSF PR.AA; SOC 2 CC6; PCI DSS 7.2.1/7.2.4",
                )
            if not item["enabled"] and item["privileged"]:
                add_finding(
                    findings, connector["id"], guid, "DISABLED_PRIVILEGED_ACCOUNT", "Alta",
                    f"Cuenta privilegiada deshabilitada aún existente: {sam}",
                    "La cuenta permanece asociada a privilegios administrativos aunque está deshabilitada.",
                    "Retirar membresías privilegiadas y eliminar la cuenta conforme a la política de retención y baja.",
                    "ISO 27001 A.5.18/A.8.2; NIST CSF PR.AA; SOC 2 CC6; PCI DSS 7.2.4/8.2.6",
                )
            if item["enabled"] and not item["service_account"] and not item["generic_account"]:
                missing = []
                if not item["mail"]:
                    missing.append("correo")
                if not item["department"]:
                    missing.append("área/departamento")
                if missing:
                    add_finding(
                        findings, connector["id"], guid, "INCOMPLETE_IDENTITY_DATA", "Baja",
                        f"Datos de identidad incompletos: {sam}",
                        "Faltan atributos de gobierno: " + ", ".join(missing) + ".",
                        "Completar los atributos para soportar recertificación, propiedad y trazabilidad.",
                        "ISO 27001 A.5.16/A.5.18; NIST CSF PR.AA; SOC 2 CC6; PCI DSS 7.2.1/8.2.1",
                    )
        return findings

    def test_connector(connector):
        started = datetime.now(timezone.utc)
        connection = None
        try:
            host = normalize_ldap_host(connector["host"])
            validate_ldap_host(host)
            try:
                socket.getaddrinfo(host, int(connector["port"]))
            except socket.gaierror as exc:
                return False, ldap_resolution_message(connector, exc)
            connection, ldap = ldap_connection(connector)
            ok = connection.search(
                search_base=connector["base_dn"],
                search_filter="(objectClass=*)",
                search_scope=ldap["BASE"],
                attributes=["distinguishedName"],
            )
            if not ok and connection.result.get("result") not in (0,):
                raise RuntimeError(connection.result.get("message") or "No se pudo consultar el Base DN.")
            elapsed = (datetime.now(timezone.utc) - started).total_seconds()
            return True, f"Conexión y autenticación LDAP correctas ({elapsed:.2f} s)."
        except Exception as exc:
            return False, str(exc)
        finally:
            if connection:
                try:
                    connection.unbind()
                except Exception:
                    pass

    def sync_connector(connector, executed_by):
        sync_started = now_iso()
        with db_conn() as sql:
            cur = sql.execute(
                """INSERT INTO ad_sync_logs
                   (connector_id,started_at,status,message,executed_by)
                   VALUES(?,?,?,?,?)""",
                (connector["id"], sync_started, "En proceso", "Conectando con Active Directory.", executed_by),
            )
            log_id = cur.lastrowid
            sql.commit()

        connection = None
        try:
            connection, ldap = ldap_connection(connector)
            user_attributes = [
                "objectGUID", "distinguishedName", "sAMAccountName", "userPrincipalName",
                "displayName", "givenName", "sn", "mail", "department", "title",
                "description", "userAccountControl", "lockoutTime", "whenCreated",
                "whenChanged", "pwdLastSet", "lastLogonTimestamp", "lastLogon",
                "accountExpires", "memberOf",
            ]
            group_attributes = [
                "objectGUID", "distinguishedName", "sAMAccountName", "displayName",
                "description", "groupType", "member",
            ]
            user_entries = connection.extend.standard.paged_search(
                search_base=connector["base_dn"],
                search_filter="(&(objectCategory=person)(objectClass=user))",
                search_scope=ldap["SUBTREE"],
                attributes=user_attributes,
                paged_size=1000,
                generator=False,
            )
            group_entries = connection.extend.standard.paged_search(
                search_base=connector["base_dn"],
                search_filter="(objectClass=group)",
                search_scope=ldap["SUBTREE"],
                attributes=group_attributes,
                paged_size=1000,
                generator=False,
            )

            raw_groups = []
            group_by_dn = {}
            parents = defaultdict(set)
            for entry in group_entries:
                attrs = entry_attributes(entry)
                dn = text_value(value(attrs, "distinguishedName") or entry.get("dn")).strip()
                if not dn:
                    continue
                sam = text_value(value(attrs, "sAMAccountName")).strip()
                members = [text_value(x).strip() for x in values(attrs, "member") if text_value(x).strip()]
                group = {
                    "object_guid": text_value(value(attrs, "objectGUID") or hashlib.sha256(dn.lower().encode()).hexdigest()),
                    "distinguished_name": dn,
                    "sam_account_name": sam,
                    "display_name": text_value(value(attrs, "displayName") or sam),
                    "description": text_value(value(attrs, "description")),
                    "group_type": text_value(value(attrs, "groupType")),
                    "privileged": int(sam.lower() in AD_PRIVILEGED_GROUPS),
                    "members": members,
                }
                raw_groups.append(group)
                group_by_dn[dn.lower()] = group
                for member_dn in members:
                    parents[member_dn.lower()].add(dn.lower())

            privileged_dns = {
                group["distinguished_name"].lower()
                for group in raw_groups if group["privileged"]
            }

            def privilege_for(user_dn):
                start = user_dn.lower()
                direct = list(parents.get(start, set()))
                queue = deque((group_dn, [group_dn]) for group_dn in direct)
                visited = set()
                while queue:
                    group_dn, path_dns = queue.popleft()
                    if group_dn in visited:
                        continue
                    visited.add(group_dn)
                    if group_dn in privileged_dns:
                        names = [
                            group_by_dn.get(dn, {}).get("sam_account_name") or dn
                            for dn in path_dns
                        ]
                        return True, "Directo" if len(path_dns) == 1 else "Anidado", " → ".join(names)
                    for parent_dn in parents.get(group_dn, set()):
                        queue.append((parent_dn, path_dns + [parent_dn]))
                return False, "", ""

            raw_users = []
            for entry in user_entries:
                attrs = entry_attributes(entry)
                dn = text_value(value(attrs, "distinguishedName") or entry.get("dn")).strip()
                if not dn:
                    continue
                sam = text_value(value(attrs, "sAMAccountName")).strip()
                display = text_value(value(attrs, "displayName") or sam)
                description = text_value(value(attrs, "description"))
                uac = int_value(value(attrs, "userAccountControl"), 0)
                locked = bool(int_value(value(attrs, "lockoutTime"), 0) or (uac & AD_UAC_LOCKOUT))
                privileged, privilege_type, privilege_path = privilege_for(dn)
                direct_groups = [
                    group_by_dn.get(group_dn, {}).get("sam_account_name") or group_dn
                    for group_dn in parents.get(dn.lower(), set())
                ]
                last_logon_raw = value(attrs, "lastLogonTimestamp") or value(attrs, "lastLogon")
                item = {
                    "object_guid": text_value(value(attrs, "objectGUID") or hashlib.sha256(dn.lower().encode()).hexdigest()),
                    "distinguished_name": dn,
                    "sam_account_name": sam,
                    "user_principal_name": text_value(value(attrs, "userPrincipalName")),
                    "display_name": display,
                    "given_name": text_value(value(attrs, "givenName")),
                    "surname": text_value(value(attrs, "sn")),
                    "mail": text_value(value(attrs, "mail")),
                    "department": text_value(value(attrs, "department")),
                    "title": text_value(value(attrs, "title")),
                    "description": description,
                    "user_account_control": uac,
                    "enabled": int(not bool(uac & AD_UAC_DISABLED)),
                    "locked": int(locked),
                    "password_never_expires": int(bool(uac & AD_UAC_DONT_EXPIRE_PASSWORD)),
                    "password_not_required": int(bool(uac & AD_UAC_PASSWORD_NOT_REQUIRED)),
                    "service_account": int(is_service_account(sam, dn, description)),
                    "generic_account": int(is_generic_account(sam, display, description)),
                    "privileged": int(privileged),
                    "privilege_type": privilege_type,
                    "privilege_path": privilege_path,
                    "when_created": ad_datetime(value(attrs, "whenCreated")),
                    "when_changed": ad_datetime(value(attrs, "whenChanged")),
                    "pwd_last_set": ad_datetime(value(attrs, "pwdLastSet")),
                    "last_logon": ad_datetime(last_logon_raw),
                    "account_expires": ad_datetime(value(attrs, "accountExpires")),
                    "direct_groups": sorted(set(direct_groups)),
                }
                raw_users.append(item)

            findings = build_findings(connector, raw_users)
            seen_at = now_iso()
            with db_conn() as sql:
                sql.execute("BEGIN")
                sql.execute("UPDATE ad_users SET active=0 WHERE connector_id=?", (connector["id"],))
                sql.execute("UPDATE ad_groups SET active=0 WHERE connector_id=?", (connector["id"],))
                sql.execute("UPDATE ad_findings SET active=0 WHERE connector_id=?", (connector["id"],))
                sql.execute("DELETE FROM ad_memberships WHERE connector_id=?", (connector["id"],))

                for group in raw_groups:
                    sql.execute(
                        """INSERT INTO ad_groups
                           (connector_id,object_guid,distinguished_name,sam_account_name,display_name,
                            description,group_type,privileged,member_count,members_json,active,first_seen_at,last_seen_at)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                           ON CONFLICT(connector_id,object_guid) DO UPDATE SET
                            distinguished_name=excluded.distinguished_name,
                            sam_account_name=excluded.sam_account_name,
                            display_name=excluded.display_name,
                            description=excluded.description,
                            group_type=excluded.group_type,
                            privileged=excluded.privileged,
                            member_count=excluded.member_count,
                            members_json=excluded.members_json,
                            active=1,last_seen_at=excluded.last_seen_at""",
                        (
                            connector["id"], group["object_guid"], group["distinguished_name"],
                            group["sam_account_name"], group["display_name"], group["description"],
                            group["group_type"], group["privileged"], len(group["members"]),
                            json.dumps(group["members"], ensure_ascii=False), 1, seen_at, seen_at,
                        ),
                    )
                    for member_dn in group["members"]:
                        member_type = "Grupo" if member_dn.lower() in group_by_dn else "Usuario/Objeto"
                        sql.execute(
                            """INSERT OR IGNORE INTO ad_memberships
                               (connector_id,group_dn,member_dn,member_type,detected_at)
                               VALUES(?,?,?,?,?)""",
                            (connector["id"], group["distinguished_name"], member_dn, member_type, seen_at),
                        )

                for item in raw_users:
                    sql.execute(
                        """INSERT INTO ad_users
                           (connector_id,object_guid,distinguished_name,sam_account_name,user_principal_name,
                            display_name,given_name,surname,mail,department,title,description,user_account_control,
                            enabled,locked,password_never_expires,password_not_required,service_account,
                            generic_account,privileged,privilege_type,privilege_path,when_created,when_changed,
                            pwd_last_set,last_logon,account_expires,direct_groups_json,raw_json,
                            active,first_seen_at,last_seen_at)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                           ON CONFLICT(connector_id,object_guid) DO UPDATE SET
                            distinguished_name=excluded.distinguished_name,sam_account_name=excluded.sam_account_name,
                            user_principal_name=excluded.user_principal_name,display_name=excluded.display_name,
                            given_name=excluded.given_name,surname=excluded.surname,mail=excluded.mail,
                            department=excluded.department,title=excluded.title,description=excluded.description,
                            user_account_control=excluded.user_account_control,enabled=excluded.enabled,
                            locked=excluded.locked,password_never_expires=excluded.password_never_expires,
                            password_not_required=excluded.password_not_required,
                            service_account=excluded.service_account,generic_account=excluded.generic_account,
                            privileged=excluded.privileged,privilege_type=excluded.privilege_type,
                            privilege_path=excluded.privilege_path,when_created=excluded.when_created,
                            when_changed=excluded.when_changed,pwd_last_set=excluded.pwd_last_set,
                            last_logon=excluded.last_logon,account_expires=excluded.account_expires,
                            direct_groups_json=excluded.direct_groups_json,raw_json=excluded.raw_json,
                            active=1,last_seen_at=excluded.last_seen_at""",
                        (
                            connector["id"], item["object_guid"], item["distinguished_name"],
                            item["sam_account_name"], item["user_principal_name"], item["display_name"],
                            item["given_name"], item["surname"], item["mail"], item["department"],
                            item["title"], item["description"], item["user_account_control"],
                            item["enabled"], item["locked"], item["password_never_expires"],
                            item["password_not_required"], item["service_account"], item["generic_account"],
                            item["privileged"], item["privilege_type"], item["privilege_path"],
                            item["when_created"], item["when_changed"], item["pwd_last_set"],
                            item["last_logon"], item["account_expires"],
                            json.dumps(item["direct_groups"], ensure_ascii=False),
                            json.dumps(item, ensure_ascii=False), 1, seen_at, seen_at,
                        ),
                    )

                user_ids = {
                    row["object_guid"]: row["id"]
                    for row in sql.execute(
                        "SELECT id,object_guid FROM ad_users WHERE connector_id=?",
                        (connector["id"],),
                    ).fetchall()
                }
                for finding in findings:
                    sql.execute(
                        """INSERT INTO ad_findings
                           (connector_id,user_id,finding_key,finding_code,severity,title,description,
                            recommendation,control_mapping,status,active,first_detected_at,last_detected_at)
                           VALUES(?,?,?,?,?,?,?,?,?,'Abierto',1,?,?)
                           ON CONFLICT(connector_id,finding_key) DO UPDATE SET
                            user_id=excluded.user_id,finding_code=excluded.finding_code,
                            severity=excluded.severity,title=excluded.title,description=excluded.description,
                            recommendation=excluded.recommendation,control_mapping=excluded.control_mapping,
                            active=1,last_detected_at=excluded.last_detected_at,
                            status=CASE WHEN ad_findings.status='Resuelto automáticamente' THEN 'Abierto' ELSE ad_findings.status END,
                            resolved_at=CASE WHEN ad_findings.status='Resuelto automáticamente' THEN NULL ELSE ad_findings.resolved_at END""",
                        (
                            connector["id"], user_ids.get(finding["user_guid"]),
                            finding["finding_key"], finding["finding_code"], finding["severity"],
                            finding["title"], finding["description"], finding["recommendation"],
                            finding["control_mapping"], seen_at, seen_at,
                        ),
                    )

                sql.execute(
                    """UPDATE ad_findings SET status='Resuelto automáticamente',resolved_at=?
                       WHERE connector_id=? AND active=0
                       AND status NOT IN ('Riesgo aceptado','Falso positivo','Descartado')""",
                    (seen_at, connector["id"]),
                )
                metrics = sql.execute(
                    """SELECT COUNT(*) total,
                       SUM(CASE WHEN severity='Crítica' THEN 1 ELSE 0 END) critical,
                       SUM(CASE WHEN severity='Alta' THEN 1 ELSE 0 END) high
                       FROM ad_findings WHERE connector_id=? AND active=1""",
                    (connector["id"],),
                ).fetchone()
                total_findings = int(metrics["total"] or 0)
                critical = int(metrics["critical"] or 0)
                high = int(metrics["high"] or 0)
                score = max(0.0, round(100 - critical * 15 - high * 8 - max(0, total_findings - critical - high) * 2, 1))
                sql.execute(
                    """UPDATE ad_connectors SET last_status='Conectado',last_message=?,
                       last_sync_at=?,updated_at=? WHERE id=?""",
                    (
                        f"{len(raw_users)} usuarios, {len(raw_groups)} grupos y {total_findings} hallazgos.",
                        seen_at, seen_at, connector["id"],
                    ),
                )
                sql.execute(
                    """UPDATE ad_sync_logs SET finished_at=?,status='Completado',message=?,
                       users_received=?,groups_received=?,memberships_received=?,findings_active=?,
                       critical_findings=?,high_findings=?,compliance_score=? WHERE id=?""",
                    (
                        seen_at, "Sincronización LDAP finalizada correctamente.", len(raw_users),
                        len(raw_groups), sum(len(g["members"]) for g in raw_groups), total_findings,
                        critical, high, score, log_id,
                    ),
                )
                sql.commit()

            # Actualiza inmediatamente los módulos que consumen los hallazgos AD.
            for hook_name in (
                "cont_comp_sync_governance_findings",
                "asegurar_sincronizacion_active_directory_modelamiento",
            ):
                hook = globals().get(hook_name)
                if callable(hook):
                    try:
                        hook()
                    except Exception as hook_exc:
                        print(f"No fue posible ejecutar {hook_name} después de sincronizar AD:", repr(hook_exc))

            surface_result = {"created": 0, "updated": 0, "unchanged": 0, "closed": 0, "total": 0}
            surface_error = ""
            surface_hook = globals().get("attack_auto_sync_active_directory_scenarios")
            if callable(surface_hook):
                try:
                    surface_result = surface_hook(
                        executed_by,
                        connector_id=connector["id"],
                        platform=connector["platform"],
                    )
                except Exception as surface_exc:
                    surface_error = str(surface_exc)
                    print("No fue posible actualizar Superficie de Ataque después de sincronizar AD:", repr(surface_exc))

            return {
                "users": len(raw_users),
                "groups": len(raw_groups),
                "memberships": sum(len(g["members"]) for g in raw_groups),
                "findings": total_findings,
                "score": score,
                "surface_created": int(surface_result.get("created", 0)),
                "surface_updated": int(surface_result.get("updated", 0)),
                "surface_unchanged": int(surface_result.get("unchanged", 0)),
                "surface_closed": int(surface_result.get("closed", 0)),
                "surface_total": int(surface_result.get("total", 0)),
                "surface_error": surface_error,
            }
        except Exception as exc:
            finished = now_iso()
            with db_conn() as sql:
                sql.execute(
                    "UPDATE ad_connectors SET last_status='Error',last_message=?,updated_at=? WHERE id=?",
                    (str(exc), finished, connector["id"]),
                )
                sql.execute(
                    "UPDATE ad_sync_logs SET finished_at=?,status='Error',message=? WHERE id=?",
                    (finished, str(exc), log_id),
                )
                sql.commit()
            raise
        finally:
            if connection:
                try:
                    connection.unbind()
                except Exception:
                    pass

    bp = Blueprint("adgov", __name__, url_prefix="/cumplimiento_continuo/active_directory")

    @bp.route("/")
    @require_access()
    def home():
        counts = {
            AD_PLATFORM_SAMBA: fetchone(
                "SELECT COUNT(*) n FROM ad_connectors WHERE platform=?", (AD_PLATFORM_SAMBA,)
            )["n"],
            AD_PLATFORM_WINDOWS: fetchone(
                "SELECT COUNT(*) n FROM ad_connectors WHERE platform=?", (AD_PLATFORM_WINDOWS,)
            )["n"],
        }
        body = render_template_string(
            """
            <div class="row g-4">
              <div class="col-lg-6">
                <div class="adg-card h-100">
                  <div class="d-flex align-items-center gap-3">
                    <div class="adg-hero-icon"><i class="bi bi-hdd-network"></i></div>
                    <div><h5 class="mb-1">Active Directory Samba</h5>
                    <div class="adg-muted">Conexión LDAP/LDAPS iniciada desde GRAC para Samba AD DC.</div></div>
                  </div>
                  <div class="mt-3"><span class="adg-chip adg-chip-info">{{ counts.SAMBA }} conector(es)</span></div>
                  <a class="adg-btn adg-btn-primary mt-3" href="{{ url_for('adgov.samba_home') }}">Abrir submódulo Samba</a>
                </div>
              </div>
              <div class="col-lg-6">
                <div class="adg-card h-100">
                  <div class="d-flex align-items-center gap-3">
                    <div class="adg-hero-icon"><i class="bi bi-windows"></i></div>
                    <div><h5 class="mb-1">Active Directory Windows</h5>
                    <div class="adg-muted">Conexión LDAP/LDAPS directa desde GRAC a Microsoft Active Directory, sin agente ni archivos adicionales.</div></div>
                  </div>
                  <div class="mt-3"><span class="adg-chip adg-chip-info">{{ counts.WINDOWS }} conector(es)</span></div>
                  <a class="adg-btn adg-btn-primary mt-3" href="{{ url_for('adgov.windows_home') }}">Abrir submódulo Windows</a>
                </div>
              </div>
            </div>
            """,
            counts=counts,
        )
        return page(
            body,
            "Gobierno del Directorio Activo",
            "Seleccione la tecnología de directorio. Ambos submódulos comparten las mismas validaciones, hallazgos, IA e integraciones.",
            platform=AD_PLATFORM_SAMBA,
        )

    @bp.route("/samba")
    @require_access()
    def samba_home():
        return redirect(url_for("adgov.dashboard", platform=AD_PLATFORM_SAMBA))

    @bp.route("/windows")
    @require_access()
    def windows_home():
        return redirect(url_for("adgov.dashboard", platform=AD_PLATFORM_WINDOWS))

    @bp.route("/dashboard")
    @require_access()
    def dashboard():
        platform = request_platform()
        connector_id = request.args.get("connector_id", type=int)
        connectors = fetchall(
            "SELECT * FROM ad_connectors WHERE platform=? ORDER BY id", (platform,)
        )
        if not connector_id and connectors:
            connector_id = connectors[0]["id"]
        selected = fetchone("SELECT * FROM ad_connectors WHERE id=? AND platform=?", (connector_id, platform)) if connector_id else None
        params = (connector_id,) if connector_id else ()
        where = " WHERE connector_id=?" if connector_id else ""
        metrics = {
            "users": fetchone(f"SELECT COUNT(*) n FROM ad_users{where}" + (" AND active=1" if where else " WHERE active=1"), params)["n"],
            "enabled": fetchone(f"SELECT COUNT(*) n FROM ad_users{where}" + (" AND active=1 AND enabled=1" if where else " WHERE active=1 AND enabled=1"), params)["n"],
            "privileged": fetchone(f"SELECT COUNT(*) n FROM ad_users{where}" + (" AND active=1 AND privileged=1" if where else " WHERE active=1 AND privileged=1"), params)["n"],
            "groups": fetchone(f"SELECT COUNT(*) n FROM ad_groups{where}" + (" AND active=1" if where else " WHERE active=1"), params)["n"],
            "findings": fetchone(f"SELECT COUNT(*) n FROM ad_findings{where}" + (" AND active=1" if where else " WHERE active=1"), params)["n"],
            "critical_high": fetchone(f"SELECT COUNT(*) n FROM ad_findings{where}" + (" AND active=1 AND severity IN ('Crítica','Alta')" if where else " WHERE active=1 AND severity IN ('Crítica','Alta')"), params)["n"],
        }
        recent = fetchall(
            f"""SELECT f.*,u.sam_account_name FROM ad_findings f
                LEFT JOIN ad_users u ON u.id=f.user_id
                {'WHERE f.connector_id=? AND f.active=1' if connector_id else 'WHERE f.active=1'}
                ORDER BY CASE f.severity WHEN 'Crítica' THEN 4 WHEN 'Alta' THEN 3 WHEN 'Media' THEN 2 ELSE 1 END DESC,
                f.id DESC LIMIT 10""",
            params,
        )
        latest_log = fetchone(
            f"SELECT * FROM ad_sync_logs {('WHERE connector_id=?' if connector_id else '')} ORDER BY id DESC LIMIT 1",
            params,
        )
        body = render_template_string(
            """
            <style>
              .adg-validation-details > summary {
                list-style: none;
                cursor: pointer;
                user-select: none;
              }
              .adg-validation-details > summary::-webkit-details-marker { display: none; }
              .adg-validation-summary {
                display: flex;
                flex-wrap: wrap;
                align-items: center;
                justify-content: space-between;
                gap: 12px;
              }
              .adg-validation-toggle {
                display: inline-flex;
                align-items: center;
                gap: 7px;
                padding: 7px 12px;
                border: 1px solid #2f6fb6;
                border-radius: 10px;
                color: #1d4f8f;
                background: #fff;
                font-size: .82rem;
                font-weight: 700;
                white-space: nowrap;
              }
              .adg-validation-details[open] .adg-validation-toggle {
                background: #eef5ff;
              }
              .adg-validation-details .adg-toggle-hide { display: none; }
              .adg-validation-details[open] .adg-toggle-show { display: none; }
              .adg-validation-details[open] .adg-toggle-hide { display: inline; }
              .adg-validation-chevron { transition: transform .2s ease; }
              .adg-validation-details[open] .adg-validation-chevron { transform: rotate(180deg); }
              @media (max-width: 700px) {
                .adg-validation-summary { align-items: flex-start; }
                .adg-validation-summary-actions { width: 100%; justify-content: space-between; }
              }
            </style>

            <details class="adg-card adg-validation-details">
              <summary class="adg-validation-summary" aria-label="Mostrar u ocultar validaciones de Gobierno de {{ platform_label }}">
                <div>
                  <h5 class="mb-1"><i class="bi bi-clipboard2-check text-primary me-1"></i> ¿Qué valida el {{ platform_label }}?</h5>
                  <div class="adg-muted">Haz clic para consultar los controles aplicados a cuentas, credenciales, privilegios y datos de identidad.</div>
                </div>
                <div class="d-flex flex-wrap align-items-center gap-2 adg-validation-summary-actions">
                  <span class="adg-chip adg-chip-info">11 validaciones automáticas</span>
                  <span class="adg-validation-toggle">
                    <span class="adg-toggle-show">Ver puntos evaluados</span>
                    <span class="adg-toggle-hide">Ocultar puntos evaluados</span>
                    <i class="bi bi-chevron-down adg-validation-chevron"></i>
                  </span>
                </div>
              </summary>

              <div class="pt-3 mt-3 border-top">
                <div class="adg-muted mb-3">El submódulo ejecuta 11 validaciones automáticas sobre cuentas, credenciales, privilegios, actividad y calidad de los datos de identidad. Los mismos criterios se aplican a Active Directory Samba y Active Directory Windows.</div>

              <div class="row g-3 mt-1">
                <div class="col-xl-3 col-md-6">
                  <div class="border rounded-3 p-3 h-100 bg-light">
                    <div class="fw-bold text-primary mb-2"><i class="bi bi-person-check me-1"></i> Estado y uso de cuentas</div>
                    <ul class="mb-0 ps-3 small">
                      <li>Cuentas habilitadas que se encuentran bloqueadas.</li>
                      <li>Cuentas activas sin uso reciente según el umbral configurado.</li>
                      <li>Cuentas habilitadas por más de 30 días que nunca han iniciado sesión.</li>
                      <li>Cuentas deshabilitadas que aún conservan privilegios administrativos.</li>
                    </ul>
                  </div>
                </div>

                <div class="col-xl-3 col-md-6">
                  <div class="border rounded-3 p-3 h-100 bg-light">
                    <div class="fw-bold text-primary mb-2"><i class="bi bi-key me-1"></i> Credenciales</div>
                    <ul class="mb-0 ps-3 small">
                      <li>Cuentas habilitadas con la opción de contraseña no requerida.</li>
                      <li>Cuentas con contraseña configurada para no expirar.</li>
                      <li>Contraseñas cuya antigüedad supera el umbral definido en el conector.</li>
                    </ul>
                  </div>
                </div>

                <div class="col-xl-3 col-md-6">
                  <div class="border rounded-3 p-3 h-100 bg-light">
                    <div class="fw-bold text-primary mb-2"><i class="bi bi-person-lock me-1"></i> Privilegios y trazabilidad</div>
                    <ul class="mb-0 ps-3 small">
                      <li>Cuentas genéricas o compartidas que reducen la trazabilidad individual.</li>
                      <li>Cuentas de servicio con privilegios elevados.</li>
                      <li>Privilegios administrativos heredados mediante grupos anidados.</li>
                    </ul>
                  </div>
                </div>

                <div class="col-xl-3 col-md-6">
                  <div class="border rounded-3 p-3 h-100 bg-light">
                    <div class="fw-bold text-primary mb-2"><i class="bi bi-person-vcard me-1"></i> Calidad de identidad</div>
                    <ul class="mb-0 ps-3 small">
                      <li>Usuarios nominativos activos sin correo electrónico registrado.</li>
                      <li>Usuarios nominativos activos sin área o departamento informado.</li>
                    </ul>
                    <div class="small text-muted mt-2">Esta validación no se aplica a cuentas técnicas ni a cuentas identificadas como genéricas.</div>
                  </div>
                </div>
              </div>
              <div class="small text-muted mt-3"><i class="bi bi-info-circle me-1"></i> Los umbrales de inactividad y antigüedad de contraseña se toman de la configuración del conector seleccionado. Cada hallazgo incluye descripción, recomendación y mapeo con ISO 27001, NIST CSF, SOC 2 y PCI DSS cuando corresponde.</div>
              </div>
            </details>

            {% if not connectors %}
              <div class="adg-card text-center py-5">
                <i class="bi bi-plug display-5 text-primary"></i>
                <h5 class="mt-3">Configure el primer conector</h5>
                <p class="adg-muted">Registre un conector para {{ platform_label }} e inicie el inventario y las evaluaciones de seguridad.</p>
                {% if can_write %}<a class="adg-btn adg-btn-primary" href="{{ url_for('adgov.config', platform=platform) }}">Configurar conector</a>{% endif %}
              </div>
            {% else %}
              <div class="adg-card">
                <div class="d-flex flex-wrap justify-content-between align-items-center gap-2">
                  <div>
                    <h5 class="mb-1">{{ selected.name if selected else 'Todos los conectores' }}</h5>
                    <div class="adg-muted">
                      {{ selected.host ~ ':' ~ selected.port if selected else '' }}
                      {% if selected %} · {{ selected.base_dn }} · Estado: {{ selected.last_status }}{% endif %}
                    </div>
                  </div>
                  <div class="d-flex flex-wrap gap-2">
                    <form method="get">
                      <input type="hidden" name="platform" value="{{ platform }}">
                      <select class="form-select form-select-sm" name="connector_id" onchange="this.form.submit()">
                        {% for c in connectors %}<option value="{{ c.id }}" {% if selected and selected.id==c.id %}selected{% endif %}>{{ c.name }}</option>{% endfor %}
                      </select>
                    </form>
                    {% if can_write and selected %}
                      <form method="post" action="{{ url_for('adgov.test', connector_id=selected.id) }}"><button class="adg-btn adg-btn-outline"><i class="bi bi-plug"></i> Probar</button></form>
                      <form method="post" action="{{ url_for('adgov.sync', connector_id=selected.id) }}"><button class="adg-btn adg-btn-primary"><i class="bi bi-arrow-repeat"></i> Sincronizar</button></form>
                    {% endif %}
                  </div>
                </div>
              </div>
              <div class="adg-grid">
                {% for value,label in [(metrics.users,'Usuarios'),(metrics.enabled,'Usuarios activos'),(metrics.privileged,'Privilegiados'),(metrics.groups,'Grupos'),(metrics.findings,'Hallazgos'),(metrics.critical_high,'Críticos y altos')] %}
                  <div class="adg-kpi"><div class="value">{{ value }}</div><div class="label">{{ label }}</div></div>
                {% endfor %}
              </div>
              {% if latest_log %}
              <div class="adg-card">
                <h5>Última sincronización</h5>
                <div class="adg-muted">{{ latest_log.started_at }} · {{ latest_log.status }} · Score {{ latest_log.compliance_score }}% · {{ latest_log.message }}</div>
              </div>
              {% endif %}
              <div class="adg-card">
                <h5>Hallazgos prioritarios</h5>
                <div class="table-responsive">
                  <table class="table adg-table table-hover">
                    <thead><tr><th>Severidad</th><th>Código</th><th>Cuenta</th><th>Hallazgo</th><th>Estado</th><th>Acción</th></tr></thead>
                    <tbody>
                    {% for f in recent %}
                      <tr><td>{{ severity_badge(f.severity) }}</td><td class="adg-code">{{ f.finding_code }}</td>
                      <td>{{ f.sam_account_name or '—' }}</td><td>{{ f.title }}</td><td>{{ f.status }}</td>
                      <td><a class="adg-btn adg-btn-outline" href="{{ url_for('adgov.finding_detail', finding_id=f.id) }}">Gestionar</a></td></tr>
                    {% else %}<tr><td colspan="6" class="text-center py-4 text-muted">No hay hallazgos activos.</td></tr>{% endfor %}
                    </tbody>
                  </table>
                </div>
              </div>
            {% endif %}
            """,
            connectors=connectors,
            selected=selected,
            metrics=metrics,
            recent=recent,
            latest_log=latest_log,
            can_write=can_write(current_user()),
            severity_badge=severity_badge,
            platform=platform,
            platform_label=platform_label(platform),
        )
        return page(
            body,
            "{}".format(platform_label(platform)),
            "Inventario, privilegios, cuentas, hallazgos y trazabilidad del directorio corporativo.",
            platform=platform,
        )

    @bp.route("/configuracion")
    @require_access(write=True)
    def config():
        platform = request_platform()
        connector_id = request.args.get("connector_id", type=int)
        selected = fetchone(
            "SELECT * FROM ad_connectors WHERE id=? AND platform=?", (connector_id, platform)
        ) if connector_id else None
        connectors = fetchall(
            "SELECT * FROM ad_connectors WHERE platform=? ORDER BY id", (platform,)
        )
        connection_mode = AD_CONNECTION_LDAP
        body = render_template_string(
            """
            <div class="adg-card">
              <div class="d-flex justify-content-between align-items-center gap-2">
                <div><h5>Configuración del conector</h5><div class="adg-muted">La contraseña se cifra localmente y nunca se muestra.</div></div>
                <a class="adg-btn adg-btn-outline" href="{{ url_for('adgov.config', platform=platform) }}"><i class="bi bi-plus-circle"></i> Nuevo</a>
              </div>
              <form class="adg-form mt-3" method="post" action="{{ url_for('adgov.save_connector') }}">
                <input type="hidden" name="connector_id" value="{{ selected.id if selected else '' }}">
                <input type="hidden" name="platform" value="{{ platform }}">
                <input type="hidden" name="connection_mode" value="LDAP">
                {% if platform == 'WINDOWS' %}
                <div class="alert alert-info">
                  <strong>Microsoft Active Directory integrado directamente.</strong> Este mismo archivo de GRAC prueba, sincroniza y evalúa Windows AD mediante LDAP/LDAPS, igual que el submódulo Samba. No requiere agente ni otro programa Python.<br>
                  <span class="small">El nombre interno <code>dc1.adlab.arkyntech.com</code> solo funciona si el servidor de GRAC puede resolver el DNS de AD y tiene ruta hacia Oracle. Desde Render debe utilizarse LDAPS 636 con un FQDN/IP públicamente alcanzable y acceso restringido.</span>
                </div>
                {% endif %}
                <div class="row g-3">
                  <div class="col-md-4"><label>Nombre</label><input class="form-control" name="name" required value="{{ selected.name if selected else ('Microsoft AD Windows - DC1' if platform=='WINDOWS' else 'Samba AD GRAC LAB') }}"></div>
                  <div class="col-md-4"><label>Host o IP del controlador</label><input class="form-control" name="host" required value="{{ selected.host if selected else ('dc1.adlab.arkyntech.com' if platform=='WINDOWS' else '10.211.55.9') }}"><div class="adg-muted">Ingrese solo el host o IP, sin ldap://, rutas ni puerto. En Render debe ser alcanzable desde Internet o mediante VPN.</div></div>
                  <div class="col-md-2"><label>Puerto</label><input class="form-control" type="number" name="port" value="{{ selected.port if selected else 389 }}"></div>
                  <div class="col-md-2"><label>Timeout (s)</label><input class="form-control" type="number" min="5" max="120" name="connect_timeout" value="{{ selected.connect_timeout if selected else 15 }}"></div>
                  <div class="col-md-6"><label>Base DN</label><input class="form-control" name="base_dn" required value="{{ selected.base_dn if selected else ('DC=adlab,DC=arkyntech,DC=com' if platform=='WINDOWS' else 'DC=ad,DC=grac,DC=test') }}"></div>
                  <div class="col-md-6"><label>Usuario de lectura</label><input class="form-control" name="bind_user" required value="{{ selected.bind_user if selected else ('svc_grac_ldap@adlab.arkyntech.com' if platform=='WINDOWS' else 'svc_grac_read@ad.grac.test') }}"></div>
                  <div class="col-md-6"><label>Contraseña LDAP {% if selected %}(dejar vacía para conservar){% endif %}</label><input class="form-control" type="password" name="bind_password" {% if not selected %}required{% endif %} autocomplete="new-password"><div class="adg-muted">Se cifra localmente en GRAC y nunca se muestra en pantalla.</div></div>
                  <div class="col-md-6"><label>Ruta CA para validar LDAPS</label><input class="form-control" name="ca_cert_path" value="{{ selected.ca_cert_path if selected else '' }}" placeholder="/ruta/ca.pem"></div>
                  <div class="col-md-3"><label>Inactividad máxima (días)</label><input class="form-control" type="number" min="1" name="inactive_days" value="{{ selected.inactive_days if selected else 90 }}"></div>
                  <div class="col-md-3"><label>Antigüedad contraseña (días)</label><input class="form-control" type="number" min="1" name="password_age_days" value="{{ selected.password_age_days if selected else 90 }}"></div>
                  <div class="col-md-2"><label>Protocolo</label><select class="form-select" name="use_ssl"><option value="0" {% if not selected or not selected.use_ssl %}selected{% endif %}>LDAP</option><option value="1" {% if selected and selected.use_ssl %}selected{% endif %}>LDAPS</option></select></div>
                  <div class="col-md-2"><label>Validar certificado</label><select class="form-select" name="verify_ssl"><option value="1" {% if selected and selected.verify_ssl %}selected{% endif %}>Sí</option><option value="0" {% if not selected or not selected.verify_ssl %}selected{% endif %}>No (solo laboratorio)</option></select></div>
                  <div class="col-md-2"><label>Estado</label><select class="form-select" name="enabled"><option value="1" {% if not selected or selected.enabled %}selected{% endif %}>Habilitado</option><option value="0" {% if selected and not selected.enabled %}selected{% endif %}>Deshabilitado</option></select></div>
                </div>
                <div class="mt-4 text-center"><button class="adg-btn adg-btn-primary"><i class="bi bi-save"></i> Guardar configuración</button></div>
              </form>
            </div>
            <div class="adg-card">
              <h5>Conectores registrados</h5>
              <div class="table-responsive"><table class="table adg-table">
                <thead><tr><th>Nombre</th><th>Tecnología</th><th>Conexión</th><th>Base DN</th><th>Estado</th><th>Última sincronización</th><th>Acciones</th></tr></thead>
                <tbody>{% for c in connectors %}<tr><td>{{ c.name }}</td><td>{{ platform_label(c.platform) }}</td><td>{{ 'LDAPS' if c.use_ssl else 'LDAP' }}://{{ c.host }}:{{ c.port }}</td><td class="adg-code">{{ c.base_dn }}</td><td>{{ c.last_status }}</td><td>{{ c.last_sync_at or '—' }}</td>
                  <td><div class="adg-actions-vertical">
                    <a class="adg-btn adg-btn-outline" href="{{ url_for('adgov.config',connector_id=c.id,platform=platform) }}">Editar</a>
                    <form method="post" action="{{ url_for('adgov.test',connector_id=c.id) }}"><button class="adg-btn adg-btn-outline">Probar conexión</button></form>
                    <form method="post" action="{{ url_for('adgov.sync',connector_id=c.id) }}"><button class="adg-btn adg-btn-primary">Sincronizar ahora</button></form>
                    <form method="post" action="{{ url_for('adgov.delete_connector',connector_id=c.id) }}" onsubmit="return confirm('¿Eliminar el conector y todo su inventario AD?');"><button class="adg-btn adg-btn-danger">Eliminar</button></form>
                  </div></td></tr>{% else %}<tr><td colspan="7" class="text-center text-muted py-4">Sin conectores registrados.</td></tr>{% endfor %}</tbody>
              </table></div>
            </div>
            """,
            selected=selected,
            connectors=connectors,
            platform=platform,
            connection_mode=connection_mode,
            platform_label=platform_label,
        )
        subtitle = "Conexión LDAP/LDAPS directa, cifrado de credenciales y umbrales de gobierno."
        return page(body, "Configuración de {}".format(platform_label(platform)), subtitle, platform=platform)

    @bp.route("/conector/guardar", methods=["POST"])
    @require_access(write=True)
    def save_connector():
        connector_id = request.form.get("connector_id", type=int)
        existing = fetchone("SELECT * FROM ad_connectors WHERE id=?", (connector_id,)) if connector_id else None
        platform = request_platform()
        connection_mode = AD_CONNECTION_LDAP
        try:
            name = (request.form.get("name") or "").strip()
            host = normalize_ldap_host(request.form.get("host"))
            validate_ldap_host(host)
            base_dn = (request.form.get("base_dn") or "").strip()
            bind_user = (request.form.get("bind_user") or "").strip()
            if not all((name, host, base_dn, bind_user)):
                raise ValueError("Nombre, host, Base DN y usuario de lectura son obligatorios.")

            port = int(request.form.get("port") or 389)
            password = (request.form.get("bind_password") or "").strip()
            encrypted = encrypt_secret(password) if password else (
                existing["bind_password_encrypted"] if existing else None
            )
            # Guardar la configuración no depende de que el DNS o la red estén disponibles.
            # La resolución y autenticación se validan en "Probar conexión".
            if not encrypted:
                raise ValueError("Debe ingresar la contraseña del usuario de enlace LDAP.")
            now = now_iso()
            values_tuple = (
                name, platform, connection_mode, host, port,
                int(request.form.get("use_ssl") or 0),
                int(request.form.get("verify_ssl") or 0),
                (request.form.get("ca_cert_path") or "").strip(),
                base_dn, bind_user, encrypted,
                max(5, min(120, int(request.form.get("connect_timeout") or 15))),
                max(1, int(request.form.get("inactive_days") or 90)),
                max(1, int(request.form.get("password_age_days") or 90)),
                int(request.form.get("enabled") or 0),
                now,
            )
            with db_conn() as sql:
                if existing:
                    sql.execute(
                        """UPDATE ad_connectors
                           SET name=?,platform=?,connection_mode=?,host=?,port=?,use_ssl=?,verify_ssl=?,
                               ca_cert_path=?,base_dn=?,bind_user=?,bind_password_encrypted=?,connect_timeout=?,
                               inactive_days=?,password_age_days=?,enabled=?,updated_at=?
                           WHERE id=?""",
                        values_tuple + (connector_id,),
                    )
                else:
                    cur = sql.execute(
                        """INSERT INTO ad_connectors
                           (name,platform,connection_mode,host,port,use_ssl,verify_ssl,ca_cert_path,
                            base_dn,bind_user,bind_password_encrypted,connect_timeout,inactive_days,
                            password_age_days,enabled,created_at,updated_at)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        values_tuple[:-1] + (now, now),
                    )
                    connector_id = cur.lastrowid
                sql.commit()
            audit(
                f"Guardó conector {platform_label(platform)} {name} en modo {connection_mode}.",
                current_user(),
            )
            flash("Conector de Active Directory guardado correctamente.", "success")
            return redirect(url_for("adgov.config", connector_id=connector_id, platform=platform))
        except Exception as exc:
            flash(f"No fue posible guardar el conector: {exc}", "warning")
            return redirect(
                url_for("adgov.config", connector_id=connector_id, platform=platform)
                if connector_id else url_for("adgov.config", platform=platform)
            )

    @bp.route("/conector/<int:connector_id>/eliminar", methods=["POST"])
    @require_access(write=True)
    def delete_connector(connector_id):
        connector = connector_or_404(connector_id)
        with db_conn() as sql:
            sql.execute("DELETE FROM ad_connectors WHERE id=?", (connector_id,))
            sql.commit()
        audit(f"Eliminó el conector Active Directory {connector['name']}.", current_user())
        flash("Conector e inventario asociado eliminados.", "success")
        return redirect(url_for("adgov.config", platform=connector["platform"]))

    @bp.route("/conector/<int:connector_id>/probar", methods=["POST"])
    @require_access(write=True)
    def test(connector_id):
        connector = connector_or_404(connector_id)
        ok, message = test_connector(connector)
        now = now_iso()
        with db_conn() as sql:
            sql.execute(
                """UPDATE ad_connectors SET last_status=?,last_message=?,last_test_at=?,updated_at=?
                   WHERE id=?""",
                ("Conectado" if ok else "Error", message, now, now, connector_id),
            )
            sql.commit()
        audit(f"Probó conexión Active Directory {connector['name']}: {message}", current_user())
        flash(message, "success" if ok else "warning")
        return redirect(url_for("adgov.config", connector_id=connector_id, platform=connector["platform"]))

    @bp.route("/conector/<int:connector_id>/sincronizar", methods=["POST"])
    @require_access(write=True)
    def sync(connector_id):
        connector = connector_or_404(connector_id)
        if not connector["enabled"]:
            flash("El conector está deshabilitado.", "warning")
            return redirect(url_for("adgov.dashboard", connector_id=connector_id, platform=connector["platform"]))
        try:
            result = sync_connector(connector, username(current_user()))
            audit(
                f"Sincronizó Active Directory {connector['name']}: "
                f"{result['users']} usuarios, {result['groups']} grupos y {result['findings']} hallazgos.",
                current_user(),
            )
            surface_message = (
                f" Superficie de Ataque: {result.get('surface_created', 0)} nuevos, "
                f"{result.get('surface_updated', 0)} actualizados y "
                f"{result.get('surface_closed', 0)} cerrados."
            )
            if result.get("surface_error"):
                surface_message += " La sincronización de escenarios presentó una alerta técnica."
            flash(
                f"Sincronización completada: {result['users']} usuarios, "
                f"{result['groups']} grupos, {result['findings']} hallazgos y score {result['score']}%."
                + surface_message,
                "success",
            )
        except Exception as exc:
            audit(f"Error sincronizando Active Directory {connector['name']}: {exc}", current_user())
            flash(f"No fue posible sincronizar Active Directory: {exc}", "danger")
        return redirect(url_for("adgov.dashboard", connector_id=connector_id, platform=connector["platform"]))

    @bp.route("/usuarios")
    @require_access()
    def users():
        platform = request_platform()
        q = (request.args.get("q") or "").strip()
        state = (request.args.get("state") or "").strip()
        connector_id = request.args.get("connector_id", type=int)
        clauses = ["u.active=1", "c.platform=?"]
        params = [platform]
        if connector_id:
            clauses.append("u.connector_id=?")
            params.append(connector_id)
        if q:
            clauses.append("(u.sam_account_name LIKE ? OR u.display_name LIKE ? OR u.mail LIKE ? OR u.department LIKE ?)")
            like = f"%{q}%"
            params.extend([like, like, like, like])
        if state == "enabled":
            clauses.append("u.enabled=1")
        elif state == "disabled":
            clauses.append("u.enabled=0")
        elif state == "privileged":
            clauses.append("u.privileged=1")
        elif state == "service":
            clauses.append("u.service_account=1")
        elif state == "generic":
            clauses.append("u.generic_account=1")
        rows = fetchall(
            f"""SELECT u.*,c.name connector_name,
                (SELECT COUNT(*) FROM ad_findings f WHERE f.user_id=u.id AND f.active=1) finding_count
                FROM ad_users u JOIN ad_connectors c ON c.id=u.connector_id
                WHERE {' AND '.join(clauses)}
                ORDER BY u.privileged DESC,u.enabled DESC,u.display_name LIMIT 3000""",
            tuple(params),
        )
        connectors = fetchall("SELECT id,name FROM ad_connectors WHERE platform=? ORDER BY name", (platform,))
        body = render_template_string(
            """
            <div class="adg-card">
              <div class="d-flex flex-wrap justify-content-between align-items-center gap-2"><div><h5>Inventario de usuarios</h5><div class="adg-muted">{{ rows|length }} registros visibles</div></div>
              <form class="d-flex flex-wrap gap-2" method="get">
                <input type="hidden" name="platform" value="{{ platform }}">
                <select class="form-select form-select-sm" name="connector_id"><option value="">Todos los conectores</option>{% for c in connectors %}<option value="{{ c.id }}" {% if connector_id==c.id %}selected{% endif %}>{{ c.name }}</option>{% endfor %}</select>
                <select class="form-select form-select-sm" name="state"><option value="">Todos</option>{% for key,label in [('enabled','Activos'),('disabled','Deshabilitados'),('privileged','Privilegiados'),('service','Servicio'),('generic','Genéricos')] %}<option value="{{ key }}" {% if state==key %}selected{% endif %}>{{ label }}</option>{% endfor %}</select>
                <input class="form-control form-control-sm" name="q" value="{{ q }}" placeholder="Cuenta, nombre, correo o área"><button class="adg-btn adg-btn-outline">Filtrar</button>
              </form></div>
              <div class="adg-table-wrap mt-3"><table class="table adg-table table-hover">
                <thead><tr><th>Cuenta</th><th>Nombre</th><th>Área / cargo</th><th>Estado</th><th>Privilegio</th><th>Último acceso</th><th>Contraseña</th><th>Grupos directos</th><th>Hallazgos</th></tr></thead>
                <tbody>{% for u in rows %}<tr>
                  <td><strong>{{ u.sam_account_name }}</strong><div class="adg-code">{{ u.user_principal_name }}</div></td>
                  <td>{{ u.display_name }}<div class="adg-muted">{{ u.mail or 'Sin correo' }}</div></td><td>{{ u.department or '—' }}<div class="adg-muted">{{ u.title or '—' }}</div></td>
                  <td>{% if u.enabled %}<span class="adg-chip adg-chip-ok">Activo</span>{% else %}<span class="adg-chip adg-chip-bad">Deshabilitado</span>{% endif %}{% if u.locked %} <span class="adg-chip adg-chip-warn">Bloqueado</span>{% endif %}</td>
                  <td>{% if u.privileged %}<span class="adg-chip adg-chip-bad">{{ u.privilege_type }}</span><div class="adg-muted">{{ u.privilege_path }}</div>{% else %}<span class="adg-chip adg-chip-ok">Estándar</span>{% endif %}</td>
                  <td>{{ u.last_logon or 'Nunca / sin dato' }}</td>
                  <td>{% if u.password_never_expires %}<span class="adg-chip adg-chip-warn">No expira</span>{% else %}{{ u.pwd_last_set or '—' }}{% endif %}</td>
                  <td class="adg-muted">{{ (u.direct_groups_json or '[]')|safe }}</td>
                  <td>{% if u.finding_count %}<a class="adg-btn adg-btn-warning" href="{{ url_for('adgov.findings',user_id=u.id,platform=platform) }}">{{ u.finding_count }} hallazgo(s)</a>{% else %}<span class="adg-chip adg-chip-ok">0</span>{% endif %}</td>
                </tr>{% else %}<tr><td colspan="9" class="text-center py-4 text-muted">Sin usuarios sincronizados.</td></tr>{% endfor %}</tbody>
              </table></div>
            </div>
            """,
            rows=rows, connectors=connectors, connector_id=connector_id, q=q, state=state, platform=platform,
        )
        return page(body, "Inventario de usuarios {}".format(platform_label(platform)), "Estado, atributos, accesos, privilegios y grupos de cada identidad.", platform=platform)

    @bp.route("/grupos")
    @require_access()
    def groups():
        platform = request_platform()
        q = (request.args.get("q") or "").strip()
        connector_id = request.args.get("connector_id", type=int)
        clauses = ["g.active=1", "c.platform=?"]
        params = [platform]
        if connector_id:
            clauses.append("g.connector_id=?")
            params.append(connector_id)
        if q:
            clauses.append("(g.sam_account_name LIKE ? OR g.display_name LIKE ? OR g.description LIKE ?)")
            like = f"%{q}%"
            params.extend([like, like, like])
        rows = fetchall(
            f"""SELECT g.*,c.name connector_name FROM ad_groups g
                JOIN ad_connectors c ON c.id=g.connector_id
                WHERE {' AND '.join(clauses)}
                ORDER BY g.privileged DESC,g.sam_account_name LIMIT 3000""",
            tuple(params),
        )
        body = render_template_string(
            """
            <div class="adg-card">
              <div class="d-flex flex-wrap justify-content-between gap-2"><div><h5>Inventario de grupos</h5><div class="adg-muted">{{ rows|length }} grupos sincronizados</div></div>
              <form class="d-flex gap-2"><input type="hidden" name="platform" value="{{ platform }}"><input class="form-control form-control-sm" name="q" value="{{ q }}" placeholder="Buscar grupo"><button class="adg-btn adg-btn-outline">Filtrar</button></form></div>
              <div class="adg-table-wrap mt-3"><table class="table adg-table table-hover">
                <thead><tr><th>Grupo</th><th>Descripción</th><th>Miembros</th><th>Clasificación</th><th>DN</th></tr></thead>
                <tbody>{% for g in rows %}<tr><td><strong>{{ g.sam_account_name }}</strong><div class="adg-muted">{{ g.connector_name }}</div></td><td>{{ g.description or '—' }}</td><td>{{ g.member_count }}</td>
                <td>{% if g.privileged %}<span class="adg-chip adg-chip-bad">Privilegiado</span>{% else %}<span class="adg-chip adg-chip-info">Estándar</span>{% endif %}</td><td class="adg-code">{{ g.distinguished_name }}</td></tr>
                {% else %}<tr><td colspan="5" class="text-center text-muted py-4">Sin grupos sincronizados.</td></tr>{% endfor %}</tbody>
              </table></div>
            </div>
            """, rows=rows, q=q, platform=platform,
        )
        return page(body, "Inventario de grupos {}".format(platform_label(platform)), "Grupos, membresías y clasificación de privilegios.", platform=platform)

    @bp.route("/hallazgos")
    @require_access()
    def findings():
        platform = request_platform()
        severity = (request.args.get("severity") or "").strip()
        status = (request.args.get("status") or "").strip()
        q = (request.args.get("q") or "").strip()
        user_id = request.args.get("user_id", type=int)
        clauses = ["f.active=1", "c.platform=?"]
        params = [platform]
        if severity:
            clauses.append("f.severity=?"); params.append(severity)
        if status:
            clauses.append("f.status=?"); params.append(status)
        if user_id:
            clauses.append("f.user_id=?"); params.append(user_id)
        if q:
            clauses.append("(f.title LIKE ? OR f.finding_code LIKE ? OR u.sam_account_name LIKE ?)")
            like = f"%{q}%"; params.extend([like, like, like])
        rows = fetchall(
            f"""SELECT f.*,u.sam_account_name,u.display_name,c.name connector_name
                FROM ad_findings f LEFT JOIN ad_users u ON u.id=f.user_id
                JOIN ad_connectors c ON c.id=f.connector_id
                WHERE {' AND '.join(clauses)}
                ORDER BY CASE f.severity WHEN 'Crítica' THEN 4 WHEN 'Alta' THEN 3 WHEN 'Media' THEN 2 ELSE 1 END DESC,f.id DESC LIMIT 3000""",
            tuple(params),
        )
        body = render_template_string(
            """
            <div class="alert alert-info border-0 shadow-sm">
              <i class="bi bi-diagram-3-fill me-1"></i>
              Estos hallazgos alimentan <strong>Modelamiento de Amenazas</strong> y <strong>Superficie de Ataque y Escenarios</strong>. La creación o actualización del riesgo se realiza únicamente desde Superficie de Ataque.
            </div>
            <div class="adg-card">
              <div class="d-flex flex-wrap justify-content-between gap-2"><div><h5>Matriz de hallazgos AD</h5><div class="adg-muted">{{ rows|length }} hallazgos activos</div></div>
              <form class="d-flex flex-wrap gap-2"><input type="hidden" name="platform" value="{{ platform }}"><select class="form-select form-select-sm" name="severity"><option value="">Severidades</option>{% for x in ['Crítica','Alta','Media','Baja'] %}<option {% if severity==x %}selected{% endif %}>{{ x }}</option>{% endfor %}</select>
              <select class="form-select form-select-sm" name="status"><option value="">Estados</option>{% for x in ['Abierto','En tratamiento','Riesgo aceptado','Falso positivo','Resuelto'] %}<option {% if status==x %}selected{% endif %}>{{ x }}</option>{% endfor %}</select>
              <input class="form-control form-control-sm" name="q" value="{{ q }}" placeholder="Código, cuenta o hallazgo"><button class="adg-btn adg-btn-outline">Filtrar</button>
              <a class="adg-btn adg-btn-success" href="{{ url_for('adgov.export_findings', platform=platform) }}">CSV</a></form>
              {% if can_write %}<form method="post" action="{{ url_for('adgov.sync_attack_surface') }}"><input type="hidden" name="platform" value="{{ platform }}"><button class="adg-btn adg-btn-primary"><i class="bi bi-bullseye"></i> Actualizar Superficie</button></form>{% endif %}</div>
              <div class="adg-table-wrap mt-3"><table class="table adg-table table-hover">
                <thead><tr><th>Severidad</th><th>Código</th><th>Cuenta</th><th>Hallazgo</th><th>Controles</th><th>Estado</th><th>Acciones</th></tr></thead>
                <tbody>{% for f in rows %}<tr><td>{{ severity_badge(f.severity) }}</td><td class="adg-code">{{ f.finding_code }}</td><td>{{ f.sam_account_name or '—' }}<div class="adg-muted">{{ f.display_name or '' }}</div></td>
                <td><strong>{{ f.title }}</strong><div class="adg-muted">{{ f.description }}</div></td><td>{{ f.control_mapping }}</td><td>{{ f.status }}</td>
                <td><div class="adg-actions-vertical"><a class="adg-btn adg-btn-outline" href="{{ url_for('adgov.finding_detail',finding_id=f.id) }}">Ver / gestionar</a>
                {% if f.plan_id %}<a class="adg-btn adg-btn-success" href="{{ url_for('planes_accion_dashboard',plan_id=f.plan_id) }}">Ir al plan</a>{% endif %}</div></td></tr>
                {% else %}<tr><td colspan="7" class="text-center text-muted py-4">Sin hallazgos.</td></tr>{% endfor %}</tbody>
              </table></div>
            </div>
            """,
            rows=rows, severity=severity, status=status, q=q, severity_badge=severity_badge,
            platform=platform, can_write=can_write(current_user()),
        )
        return page(body, "Hallazgos de {}".format(platform_label(platform)), "Evaluaciones determinísticas, mapeo de controles y tratamiento.", platform=platform)

    @bp.route("/superficie-ataque/sincronizar", methods=["POST"])
    @require_access(write=True)
    def sync_attack_surface():
        platform = request_platform()
        hook = globals().get("attack_auto_sync_active_directory_scenarios")
        if not callable(hook):
            flash("La integración con Superficie de Ataque no está disponible.", "danger")
            return redirect(url_for("adgov.findings", platform=platform))
        try:
            result = hook(username(current_user()), platform=platform)
            flash(
                "Superficie de Ataque actualizada: "
                f"{result.get('created', 0)} escenarios nuevos, "
                f"{result.get('updated', 0)} actualizados, "
                f"{result.get('unchanged', 0)} sin cambios y "
                f"{result.get('closed', 0)} cerrados.",
                "success",
            )
            return redirect(url_for("attack_auto", source="ACTIVE_DIRECTORY", ad_platform=platform))
        except Exception as exc:
            flash(f"No fue posible actualizar Superficie de Ataque: {exc}", "danger")
            return redirect(url_for("adgov.findings", platform=platform))

    @bp.route("/hallazgo/<int:finding_id>", methods=["GET", "POST"])
    @require_access()
    def finding_detail(finding_id):
        finding = fetchone(
            """SELECT f.*,u.sam_account_name,u.display_name,u.distinguished_name,u.privilege_path,
               u.department,u.title AS user_title,u.mail,c.name connector_name,c.platform
               FROM ad_findings f LEFT JOIN ad_users u ON u.id=f.user_id
               JOIN ad_connectors c ON c.id=f.connector_id WHERE f.id=?""",
            (finding_id,),
        )
        if not finding:
            abort(404)
        user = current_user()
        if request.method == "POST":
            if not can_write(user):
                flash("El perfil actual es de solo lectura.", "danger")
                return redirect(url_for("adgov.finding_detail", finding_id=finding_id))
            allowed = {"Abierto", "En tratamiento", "Riesgo aceptado", "Falso positivo", "Resuelto", "Descartado"}
            new_status = (request.form.get("status") or "Abierto").strip()
            if new_status not in allowed:
                new_status = "Abierto"
            resolved = now_iso() if new_status in ("Resuelto", "Descartado") else None
            with db_conn() as sql:
                sql.execute(
                    """UPDATE ad_findings SET status=?,assigned_to=?,management_comment=?,resolved_at=?
                       WHERE id=?""",
                    (
                        new_status, (request.form.get("assigned_to") or "").strip(),
                        (request.form.get("management_comment") or "").strip(), resolved, finding_id,
                    ),
                )
                sql.commit()
            audit(f"Actualizó hallazgo AD {finding['finding_code']} a {new_status}.", user)
            flash("Hallazgo actualizado.", "success")
            return redirect(url_for("adgov.finding_detail", finding_id=finding_id))
        body = render_template_string(
            """
            <div class="adg-card">
              <div class="d-flex justify-content-between gap-2"><div><h5>{{ finding.title }}</h5><div class="adg-muted">{{ finding.connector_name }} · {{ finding.finding_code }}</div></div>{{ severity_badge(finding.severity) }}</div>
              <div class="adg-detail mt-3">
                {% for label,val in [('Cuenta',finding.sam_account_name),('Nombre',finding.display_name),('Área',finding.department),('Cargo',finding.user_title),('Correo',finding.mail),('Ruta de privilegio',finding.privilege_path),('DN',finding.distinguished_name),('Estado',finding.status)] %}
                <div class="adg-detail-item"><span>{{ label }}</span><strong>{{ val or '—' }}</strong></div>{% endfor %}
              </div>
              <hr><h6 class="fw-bold text-primary">Descripción</h6><p>{{ finding.description }}</p>
              <h6 class="fw-bold text-primary">Recomendación determinística</h6><p>{{ finding.recommendation }}</p>
              <h6 class="fw-bold text-primary">Mapeo de controles</h6><p>{{ finding.control_mapping }}</p>
              {% if ai_sections %}
              <div class="adg-ai-panel">
                <div class="adg-ai-header"><i class="bi bi-stars"></i><div><strong>Análisis complementario de IA</strong><br><span>Organizado por secciones para facilitar validación, remediación y seguimiento.</span></div></div>
                <div class="adg-ai-grid">
                  {% for section in ai_sections %}
                  <section class="adg-ai-section {{ 'adg-ai-section-wide' if section['wide'] else '' }}">
                    <h6><i class="bi {{ section['icon'] }}"></i>{{ section['title'] }}</h6>
                    {% if section['items']|length == 1 and section['key'] in ['resumen_ejecutivo','causa_probable','riesgo_negocio'] %}
                    <p>{{ section['items'][0] }}</p>
                    {% else %}
                    <ul>{% for item in section['items'] %}<li>{{ item }}</li>{% endfor %}</ul>
                    {% endif %}
                  </section>
                  {% endfor %}
                </div>
              </div>
              {% endif %}
              {% if can_write %}
              <div class="adg-actions">
                {% if not finding.plan_id %}<form method="post" action="{{ url_for('adgov.create_plan',finding_id=finding.id) }}"><button class="adg-btn adg-btn-success"><i class="bi bi-clipboard2-plus"></i> Asignar plan de acción</button></form>{% else %}<a class="adg-btn adg-btn-success" href="{{ url_for('planes_accion_dashboard',plan_id=finding.plan_id) }}">Ir al plan de acción</a>{% endif %}
                <form method="post" action="{{ url_for('adgov.generate_ai',finding_id=finding.id) }}"><button class="adg-btn adg-btn-primary"><i class="bi bi-stars"></i> Analizar con IA</button></form>
              </div>
              <form class="adg-form mt-4" method="post">
                <div class="row g-3"><div class="col-md-4"><label>Estado</label><select class="form-select" name="status">{% for x in ['Abierto','En tratamiento','Riesgo aceptado','Falso positivo','Resuelto','Descartado'] %}<option {% if finding.status==x %}selected{% endif %}>{{ x }}</option>{% endfor %}</select></div>
                <div class="col-md-8"><label>Responsable</label><input class="form-control" name="assigned_to" value="{{ finding.assigned_to or '' }}"></div>
                <div class="col-12"><label>Comentario de gestión</label><textarea class="form-control" rows="4" name="management_comment">{{ finding.management_comment or '' }}</textarea></div></div>
                <div class="text-center mt-3"><button class="adg-btn adg-btn-primary">Guardar gestión</button></div>
              </form>{% endif %}
            </div>
            """,
            finding=finding,
            severity_badge=severity_badge,
            can_write=can_write(user),
            ai_sections=list(ad_ai_sections(finding["ai_analysis"]) or []),
        )
        return page(body, "Detalle del hallazgo {}".format(platform_label(finding["platform"])), "Análisis, gestión, escenarios de ataque y plan de acción.", platform=finding["platform"])

    @bp.route("/hallazgo/<int:finding_id>/plan", methods=["POST"])
    @require_access(write=True)
    def create_plan(finding_id):
        if not plan_model or not orm_db:
            flash("La integración con Planes de Acción no está disponible.", "danger")
            return redirect(url_for("adgov.finding_detail", finding_id=finding_id))
        finding = fetchone(
            """SELECT f.*,u.sam_account_name,u.display_name FROM ad_findings f
               LEFT JOIN ad_users u ON u.id=f.user_id WHERE f.id=?""",
            (finding_id,),
        )
        if not finding:
            abort(404)
        source_ref = f"adgov-finding:{finding['connector_id']}:{finding['finding_key']}"
        existing = plan_model.query.filter_by(source_ref=source_ref).first()
        if existing:
            plan_id = existing.id
        else:
            plan = plan_model(
                origin="Gobierno del Directorio Activo",
                standard="MULTI",
                control_code=finding["finding_code"],
                title=f"Remediar: {finding['title']}",
                description=f"{finding['description']}\n\nRecomendación: {finding['recommendation']}\n\nControles: {finding['control_mapping']}",
                asset=finding["sam_account_name"] or finding["display_name"] or "Active Directory",
                severity=finding["severity"],
                action_type="Remediación IAM",
                responsible=finding["assigned_to"] or username(current_user()),
                status="Abierto",
                source_ref=source_ref,
                raw_json=json.dumps({"ad_finding_id": finding_id}, ensure_ascii=False),
            )
            orm_db.session.add(plan)
            orm_db.session.commit()
            plan_id = plan.id
        with db_conn() as sql:
            sql.execute("UPDATE ad_findings SET plan_id=?,status='En tratamiento' WHERE id=?", (plan_id, finding_id))
            sql.commit()
        audit(f"Creó plan de acción desde hallazgo AD {finding['finding_code']}.", current_user())
        flash("Plan de acción creado correctamente.", "success")
        return redirect(url_for("planes_accion_dashboard", plan_id=plan_id))

    # El registro de riesgos de hallazgos AD se realiza exclusivamente desde
    # Superficie de Ataque y Escenarios, después de generar o actualizar el escenario.

    @bp.route("/hallazgo/<int:finding_id>/ia", methods=["POST"])
    @require_access(write=True)
    def generate_ai(finding_id):
        finding = fetchone(
            """SELECT f.*,u.sam_account_name,u.display_name,u.department,u.privilege_path
               FROM ad_findings f LEFT JOIN ad_users u ON u.id=f.user_id WHERE f.id=?""",
            (finding_id,),
        )
        if not finding:
            abort(404)
        if not ai_helper:
            flash("El servicio de IA no está disponible en esta instalación.", "warning")
            return redirect(url_for("adgov.finding_detail", finding_id=finding_id))
        prompt = f"""
Eres especialista senior en gobierno de identidades, Microsoft Active Directory, Samba AD,
ISO 27001, NIST CSF, SOC 2 y gestión de riesgos.

Analiza el hallazgo confirmado por reglas determinísticas de GRAC. No cambies su existencia,
código ni severidad. No inventes evidencia. Distingue claramente hechos, validaciones pendientes
y recomendaciones.

Devuelve EXCLUSIVAMENTE un objeto JSON válido, sin markdown, con esta estructura:
{{
  "resumen_ejecutivo": "síntesis breve y clara",
  "causa_probable": "causa técnica y de gobierno más probable",
  "riesgo_negocio": "impacto para confidencialidad, integridad, disponibilidad y operación",
  "validaciones": ["validación técnica 1", "validación técnica 2"],
  "remediacion_priorizada": [
    {{"prioridad": "Inmediata/Alta/Media", "accion": "acción concreta", "responsable": "rol sugerido", "plazo": "plazo sugerido"}}
  ],
  "evidencia_cierre": ["evidencia verificable 1", "evidencia verificable 2"],
  "metricas": [
    {{"indicador": "nombre del indicador", "meta": "meta verificable"}}
  ],
  "controles_relacionados": ["control o marco relacionado"]
}}

Mantén cada sección concisa y accionable.

Cuenta: {finding['sam_account_name'] or finding['display_name']}
Área: {finding['department'] or 'No informada'}
Código: {finding['finding_code']}
Severidad: {finding['severity']}
Hallazgo: {finding['title']}
Descripción: {finding['description']}
Recomendación base: {finding['recommendation']}
Ruta de privilegio: {finding['privilege_path'] or 'No aplica'}
Controles: {finding['control_mapping']}
"""
        try:
            analysis_raw = ai_helper(prompt, temperature=0.10, max_tokens=900)
            analysis = ad_ai_normalized_json(analysis_raw)
            with db_conn() as sql:
                sql.execute("UPDATE ad_findings SET ai_analysis=? WHERE id=?", (analysis, finding_id))
                sql.commit()
            audit(f"Generó análisis IA para hallazgo AD {finding['finding_code']}.", current_user())
            flash("Análisis complementario generado por IA.", "success")
        except Exception as exc:
            flash(f"No fue posible generar el análisis IA: {exc}", "danger")
        return redirect(url_for("adgov.finding_detail", finding_id=finding_id))



    @bp.route("/historial")
    @require_access()
    def history():
        platform = request_platform()
        rows = fetchall(
            """SELECT l.*,c.name connector_name,c.platform FROM ad_sync_logs l
               JOIN ad_connectors c ON c.id=l.connector_id
               WHERE c.platform=? ORDER BY l.id DESC LIMIT 1000""",
            (platform,),
        )
        body = render_template_string(
            """
            <div class="adg-card"><h5>Historial de sincronización</h5>
              <div class="adg-table-wrap mt-3"><table class="table adg-table">
                <thead><tr><th>Conector</th><th>Inicio</th><th>Estado</th><th>Usuarios</th><th>Grupos</th><th>Membresías</th><th>Hallazgos</th><th>Score</th><th>Ejecutado por</th><th>Mensaje</th><th>Acción</th></tr></thead>
                <tbody>{% for l in rows %}<tr><td>{{ l.connector_name }}</td><td>{{ l.started_at }}</td><td>{{ l.status }}</td><td>{{ l.users_received }}</td><td>{{ l.groups_received }}</td><td>{{ l.memberships_received }}</td><td>{{ l.findings_active }}</td><td>{{ l.compliance_score }}%</td><td>{{ l.executed_by }}</td><td>{{ l.message }}</td>
                <td>{% if can_write %}<form method="post" action="{{ url_for('adgov.delete_history',log_id=l.id) }}" onsubmit="return confirm('¿Eliminar este registro del historial?');"><button class="adg-btn adg-btn-danger">Eliminar</button></form>{% endif %}</td></tr>
                {% else %}<tr><td colspan="11" class="text-center text-muted py-4">Sin sincronizaciones.</td></tr>{% endfor %}</tbody>
              </table></div>
            </div>
            """, rows=rows, can_write=can_write(current_user()),
        )
        return page(body, "Historial de {}".format(platform_label(platform)), "Trazabilidad de conexiones, sincronizaciones y resultados.", platform=platform)

    @bp.route("/historial/<int:log_id>/eliminar", methods=["POST"])
    @require_access(write=True)
    def delete_history(log_id):
        with db_conn() as sql:
            sql.execute("DELETE FROM ad_sync_logs WHERE id=?", (log_id,))
            sql.commit()
        audit(f"Eliminó registro {log_id} del historial Active Directory.", current_user())
        flash("Registro del historial eliminado.", "success")
        return redirect(url_for("adgov.history"))

    @bp.route("/hallazgos.csv")
    @require_access()
    def export_findings():
        platform = request_platform()
        rows = fetchall(
            """SELECT c.name connector,c.platform,u.sam_account_name,u.display_name,f.*
               FROM ad_findings f JOIN ad_connectors c ON c.id=f.connector_id
               LEFT JOIN ad_users u ON u.id=f.user_id
               WHERE f.active=1 AND c.platform=?
               ORDER BY f.severity,f.id""",
            (platform,),
        )
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Conector", "Cuenta", "Nombre", "Código", "Severidad", "Título",
            "Descripción", "Recomendación", "Controles", "Estado", "Responsable",
            "Primera detección", "Última detección", "Plan ID", "Riesgo ID",
        ])
        for row in rows:
            writer.writerow([
                row["connector"], row["sam_account_name"], row["display_name"],
                row["finding_code"], row["severity"], row["title"], row["description"],
                row["recommendation"], row["control_mapping"], row["status"],
                row["assigned_to"], row["first_detected_at"], row["last_detected_at"],
                row["plan_id"], row["risk_id"],
            ])
        data = io.BytesIO(output.getvalue().encode("utf-8-sig"))
        data.seek(0)
        return send_file(
            data,
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"hallazgos_active_directory_{date.today().isoformat()}.csv",
        )

    app.register_blueprint(bp)
    app.extensions["ad_governance"] = {
        "db_path": db_path,
        "module": "Gobierno del Directorio Activo",
        "platforms": dict(AD_PLATFORM_LABELS),
        "connection_mode": "LDAP/LDAPS directo integrado en GRAC",
    }
    return bp


