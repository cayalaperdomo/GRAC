def scorecard_kali_worker(run_id, dominio):
    with app.app_context():
        try:
            ejecutar_scorecard_kali_independiente(run_id, dominio)
        except Exception as e:
            tb = traceback.format_exc()
            scorecard_set_progress(
                run_id,
                pct=100,
                stage="Error en escaneo Kali independiente",
                tool=None,
                estado="error",
                error=tb
            )

def scorecard_get_param(clave, default):
    try:
        conn = get_scorecard_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT valor
            FROM scorecard_parametros
            WHERE clave = ?
        """, (clave,))
        row = cur.fetchone()
        conn.close()

        if row:
            return float(row["valor"])

        return float(default)

    except Exception:
        return float(default)


def scorecard_risk_levels_activos():
    try:
        conn = get_scorecard_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT *
            FROM scorecard_risk_levels
            WHERE activo = 1
            ORDER BY score_min DESC, orden ASC, id ASC
        """)
        rows = cur.fetchall()
        conn.close()
        return rows
    except Exception:
        return []


def nivel_riesgo_scorecard(score):
    score = float(score or 0)
    niveles = scorecard_risk_levels_activos()

    if not niveles:
        if score >= 85:
            return "Bajo"
        if score >= 70:
            return "Medio"
        if score >= 50:
            return "Alto"
        return "Crítico"

    for nivel in niveles:
        if score >= float(nivel["score_min"] or 0):
            return nivel["nombre"]

    return niveles[-1]["nombre"]


def scorecard_badge_color(nivel_nombre):
    try:
        conn = get_scorecard_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT color_bootstrap
            FROM scorecard_risk_levels
            WHERE nombre = ?
            LIMIT 1
        """, (nivel_nombre,))
        row = cur.fetchone()
        conn.close()

        if row:
            return row["color_bootstrap"]

        return "secondary"

    except Exception:
        return "secondary"


def scorecard_calcular_total(score_dns, score_ip, score_kali, score_incidentes, score_darkweb=100, incluir_kali=True):
    """
    Calcula score total.

    Si incluir_kali=False, Kali NO participa en el score.
    Esto evita castigar cuando no se ejecutó el escaneo Kali.
    """

    peso_dns = scorecard_get_param("peso_dns", 20)
    peso_ip = scorecard_get_param("peso_ip", 15)
    peso_kali = scorecard_get_param("peso_kali", 35)
    peso_incidentes = scorecard_get_param("peso_incidentes", 15)
    peso_darkweb = scorecard_get_param("peso_darkweb", 15)

    componentes = [
        (float(score_dns or 0), peso_dns),
        (float(score_ip or 0), peso_ip),
        (float(score_incidentes or 0), peso_incidentes),
        (float(score_darkweb or 0), peso_darkweb),
    ]

    if incluir_kali:
        componentes.append((float(score_kali or 0), peso_kali))

    total_pesos = sum(peso for _, peso in componentes)

    if total_pesos <= 0:
        return 0

    total = sum(valor * peso for valor, peso in componentes) / total_pesos
    return round(max(0, min(100, total)), 2)


def scorecard_score_incidentes(incidentes):
    """
    Calcula score por severidad, no solo por cantidad.

    Reglas:
    - Sin incidentes: 100
    - Crítico: 20
    - Alto: 55
    - Medio: 75
    - Bajo: 90

    Si hay varios incidentes, toma la severidad más alta.
    """

    incidentes = incidentes or []

    if not incidentes:
        return 100, "Bajo"

    severidad_orden = {
        "Bajo": 1,
        "Medio": 2,
        "Alto": 3,
        "Crítico": 4,
        "Critico": 4
    }

    severidad_max = "Bajo"

    for item in incidentes:
        sev = item.get("severidad") or "Bajo"
        if severidad_orden.get(sev, 0) > severidad_orden.get(severidad_max, 0):
            severidad_max = sev

    if severidad_max in ["Crítico", "Critico"]:
        return 20, "Crítico"

    if severidad_max == "Alto":
        return 55, "Alto"

    if severidad_max == "Medio":
        return 75, "Medio"

    return 90, "Bajo"

def scorecard_brechas_historicas_demo(proveedor_nombre, dominio):
    """
    Catálogo mínimo de brechas históricas conocidas para pruebas/demo.

    Motivo:
    Las búsquedas OSINT tipo GDELT son dinámicas y pueden no devolver incidentes
    antiguos en cada ejecución. Por eso, para validar el funcionamiento del
    módulo, se agrega un catálogo controlado de casos conocidos.
    """

    proveedor_norm = (proveedor_nombre or "").strip().lower()
    dominio_limpio = limpiar_dominio_scorecard(dominio)
    dominio_base = obtener_dominio_base(dominio_limpio)

    incidentes = []

    # Equifax 2017
    if (
        "equifax" in proveedor_norm
        or dominio_base == "equifax.com"
        or dominio_limpio.endswith(".equifax.com")
    ):
        incidentes.append({
            "fuente": "FTC / Caso histórico conocido",
            "titulo": "Equifax Data Breach 2017",
            "url": "https://www.ftc.gov/enforcement/refunds/equifax-data-breach-settlement",
            "fecha_incidente": "2017-09",
            "severidad": "Crítico",
            "descripcion": (
                "Equifax anunció en 2017 una brecha de datos que expuso información personal "
                "de aproximadamente 147 millones de personas. Se registra como incidente histórico "
                "crítico para validar el Scorecard."
            )
        })

    # Yahoo 2013-2014
    if (
        "yahoo" in proveedor_norm
        or dominio_base == "yahoo.com"
        or dominio_limpio.endswith(".yahoo.com")
    ):
        incidentes.append({
            "fuente": "Caso histórico conocido",
            "titulo": "Yahoo Data Breaches 2013-2014",
            "url": "https://www.sec.gov/newsroom/press-releases/2018-71",
            "fecha_incidente": "2013-2014",
            "severidad": "Crítico",
            "descripcion": (
                "Yahoo tuvo brechas históricas de gran escala reportadas públicamente. "
                "Se registra como incidente histórico crítico para pruebas de Scorecard."
            )
        })

    # Marriott / Starwood 2018
    if (
        "marriott" in proveedor_norm
        or "starwood" in proveedor_norm
        or dominio_base == "marriott.com"
        or dominio_limpio.endswith(".marriott.com")
    ):
        incidentes.append({
            "fuente": "Caso histórico conocido",
            "titulo": "Marriott / Starwood Data Breach 2018",
            "url": "https://www.ftc.gov/business-guidance/blog/2024/10/ftc-says-marriott-starwood-data-breaches-resulted-poor-security-practices",
            "fecha_incidente": "2018",
            "severidad": "Crítico",
            "descripcion": (
                "Marriott/Starwood tuvo una brecha de datos ampliamente reportada. "
                "Se registra como incidente histórico crítico para pruebas de Scorecard."
            )
        })

    # Dropbox 2012
    if (
        "dropbox" in proveedor_norm
        or dominio_base == "dropbox.com"
        or dominio_limpio.endswith(".dropbox.com")
    ):
        incidentes.append({
            "fuente": "Caso histórico conocido",
            "titulo": "Dropbox Credential Exposure 2012",
            "url": "https://blogs.dropbox.com/dropbox/2016/08/resetting-passwords-to-keep-your-files-safe/",
            "fecha_incidente": "2012",
            "severidad": "Alto",
            "descripcion": (
                "Dropbox reportó un incidente histórico asociado a credenciales. "
                "Se registra como incidente alto para pruebas de Scorecard."
            )
        })

    return incidentes


def guardar_scorecard_incidente(run_id, proveedor_id, proveedor_nombre, dominio, item):
    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO scorecard_incidents
        (run_id, proveedor_id, proveedor_nombre, dominio, fuente, titulo, url,
         fecha_incidente, severidad, descripcion, detalle_json, fecha_registro)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id,
        proveedor_id,
        proveedor_nombre,
        dominio,
        item.get("fuente"),
        item.get("titulo"),
        item.get("url"),
        item.get("fecha_incidente"),
        item.get("severidad"),
        item.get("descripcion"),
        json.dumps(item, ensure_ascii=False),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def consultar_incidentes_osint_scorecard(proveedor_nombre, dominio):
    """
    Consulta incidentes de seguridad.

    1. Primero usa catálogo histórico controlado para pruebas/demo.
    2. Luego consulta GDELT para noticias públicas recientes o indexadas.
    """

    incidentes = []
    incidentes.extend(scorecard_brechas_historicas_demo(proveedor_nombre, dominio))

    try:
        terminos = []

        proveedor_nombre = (proveedor_nombre or "").strip()
        dominio_limpio = limpiar_dominio_scorecard(dominio)
        dominio_base = obtener_dominio_base(dominio_limpio)

        if proveedor_nombre and proveedor_nombre != "Proveedor no asociado":
            terminos.append(f'"{proveedor_nombre}" "data breach"')
            terminos.append(f'"{proveedor_nombre}" "cybersecurity incident"')
            terminos.append(f'"{proveedor_nombre}" "ransomware"')
            terminos.append(f'"{proveedor_nombre}" "data leak"')
            terminos.append(f'"{proveedor_nombre}" "security breach"')

        if dominio_base:
            terminos.append(f'"{dominio_base}" "data breach"')
            terminos.append(f'"{dominio_base}" "security incident"')
            terminos.append(f'"{dominio_base}" "ransomware"')
            terminos.append(f'"{dominio_base}" "leak"')
            terminos.append(f'"{dominio_base}" "breach"')

        query = " OR ".join(terminos[:10])

        if query:
            resp = requests.get(
                "https://api.gdeltproject.org/api/v2/doc/doc",
                params={
                    "query": query,
                    "mode": "ArtList",
                    "format": "json",
                    "maxrecords": 20,
                    "sort": "HybridRel"
                },
                timeout=20
            )

            if resp.status_code == 200:
                data = resp.json() or {}
                articles = data.get("articles") or []

                vistos = set((i.get("url") or "").lower() for i in incidentes if i.get("url"))

                for art in articles:
                    titulo = (art.get("title") or "").strip()
                    link = (art.get("url") or "").strip()

                    if not titulo or not link:
                        continue

                    key = link.lower()
                    if key in vistos:
                        continue

                    vistos.add(key)

                    texto = f"{titulo} {art.get('domain','')} {art.get('seendate','')} {art.get('sourceCountry','')}".lower()

                    severidad = "Medio"

                    if any(x in texto for x in ["ransomware", "breach", "data breach", "leak", "stolen", "compromised"]):
                        severidad = "Alto"

                    if any(x in texto for x in ["massive", "millions", "critical", "extortion", "class action", "settlement"]):
                        severidad = "Crítico"

                    incidentes.append({
                        "fuente": art.get("sourceCountry") or "GDELT / Noticias públicas",
                        "titulo": titulo[:500],
                        "url": link,
                        "fecha_incidente": scorecard_normalizar_fecha(art.get("seendate")),
                        "severidad": severidad,
                        "descripcion": (art.get("domain") or "")[:500]
                    })

    except Exception as e:
        print("Error consultando incidentes OSINT Scorecard:", repr(e))

    return incidentes


def evaluar_incident_history_scorecard(run_id, proveedor_id, proveedor_nombre, dominio):
    incidentes = consultar_incidentes_osint_scorecard(proveedor_nombre, dominio)

    for item in incidentes:
        guardar_scorecard_incidente(run_id, proveedor_id, proveedor_nombre, dominio, item)

    total = len(incidentes)
    score, riesgo = scorecard_score_incidentes(incidentes)

    evidencia = (
        f"Se identificaron {total} referencias públicas o históricas asociadas a incidentes, brechas, ransomware, leaks o ataques."
        if total else
        "No se identificaron referencias públicas relevantes de brechas o incidentes en la consulta OSINT básica."
    )

    guardar_scorecard_finding(run_id, {
        "categoria": "Incident History",
        "herramienta": "Catálogo histórico + OSINT Público",
        "control": "Brechas e incidentes de seguridad",
        "estado": "Con hallazgos" if total else "Sin hallazgos",
        "riesgo": riesgo,
        "severidad": riesgo,
        "score": score,
        "evidencia": evidencia,
        "recomendacion": (
            "Validar manualmente las fuentes públicas encontradas, solicitar explicación formal al proveedor "
            "y pedir evidencia de remediación, mejoras de seguridad y controles posteriores al incidente."
            if total else
            "Mantener monitoreo periódico de noticias e incidentes públicos."
        )
    })

    return score, riesgo, total

def scorecard_normalizar_fecha(valor):
    try:
        valor = str(valor or "").strip()
        if not valor:
            return ""
        if len(valor) >= 8 and valor[:8].isdigit():
            return f"{valor[:4]}-{valor[4:6]}-{valor[6:8]}"
        return valor[:30]
    except Exception:
        return ""


def scorecard_leakcheck_extraer_resultados(data):
    if data is None:
        return 0, []

    if isinstance(data, list):
        return len(data), data

    if not isinstance(data, dict):
        return 0, []

    result = data.get("result") or data.get("results") or data.get("data") or []

    if isinstance(result, dict):
        tmp = []
        for k, v in result.items():
            if isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        item["_account"] = k
                        tmp.append(item)
                    else:
                        tmp.append({"_account": k, "value": item})
            elif isinstance(v, dict):
                v["_account"] = k
                tmp.append(v)
            else:
                tmp.append({"_account": k, "value": v})
        result = tmp

    if not isinstance(result, list):
        result = []

    found = data.get("found")
    if found is None:
        found = data.get("total")
    if found is None:
        found = len(result)

    try:
        found = int(found or 0)
    except Exception:
        found = len(result)

    return found, result


def consultar_leakcheck_hibrido_scorecard(proveedor_nombre, dominio):
    hallazgos = []

    api_key = scorecard_get_enterprise_api_key("leakcheck")
    if not api_key:
        return hallazgos

    try:
        dominio_base = obtener_dominio_base(dominio)

        if not dominio_base:
            return hallazgos

        if LeakCheckAPI_v2 is not None:
            api = LeakCheckAPI_v2(api_key=api_key)
            data = api.lookup(query=dominio_base, query_type="domain", limit=100)
        else:
            resp = requests.get(
                f"https://leakcheck.io/api/v2/query/{dominio_base}",
                params={"type": "domain", "limit": 100},
                headers={"Accept": "application/json", "X-API-Key": api_key},
                timeout=25
            )

            if resp.status_code in [400, 401, 403, 422, 429]:
                return [scorecard_api_error_item("LeakCheck API", f"HTTP {resp.status_code}: {resp.text[:300]}")]

            if resp.status_code != 200:
                return []

            data = resp.json() or {}

        found, results = scorecard_leakcheck_extraer_resultados(data)

        if found <= 0:
            return hallazgos

        fuentes = []
        muestras = []

        for item in results[:25]:
            if not isinstance(item, dict):
                continue

            src = item.get("source") or item.get("sources") or item.get("breach") or item.get("database")
            if isinstance(src, dict):
                src_name = src.get("name") or src.get("breach") or src.get("title") or "Fuente no informada"
                fecha = src.get("breach_date") or src.get("date") or ""
            elif isinstance(src, list):
                src_name = ", ".join([str(x) for x in src[:3]])
                fecha = ""
            else:
                src_name = str(src or "Fuente no informada")
                fecha = item.get("breach_date") or item.get("date") or ""

            cuenta = (
                item.get("email")
                or item.get("username")
                or item.get("login")
                or item.get("_account")
                or item.get("value")
                or ""
            )

            if src_name and src_name not in fuentes:
                fuentes.append(src_name)

            muestras.append({
                "cuenta_mascarada": scorecard_mask_indicator(cuenta),
                "fuente": src_name,
                "fecha": fecha,
                "password_omitido": True
            })

        severidad = "Medio"
        if found > 2:
            severidad = "Alto"
        if found > 10:
            severidad = "Crítico"

        hallazgos.append({
            "fuente": "LeakCheck API",
            "tipo_exposicion": "Credenciales / identidades filtradas",
            "indicador": f"{dominio_base} - {found} registros encontrados",
            "severidad": severidad,
            "fecha": datetime.now().strftime("%Y-%m-%d"),
            "evidencia": (
                f"LeakCheck reportó {found} registros asociados al dominio {dominio_base}. "
                f"Fuentes detectadas: {', '.join(fuentes[:8]) if fuentes else 'No informadas'}."
            ),
            "recomendacion": (
                "Solicitar al proveedor investigación formal, rotación de credenciales, MFA obligatorio, "
                "bloqueo de password reuse y evidencia de remediación."
            ),
            "url": "https://leakcheck.io/",
            "credencial_confirmada": True,
            "detalle": {
                "found": found,
                "fuentes": fuentes[:20],
                "muestras_mascaradas": muestras,
                "raw_passwords_omitted": True
            }
        })

    except Exception as e:
        hallazgos.append(scorecard_api_error_item("LeakCheck API", repr(e)))

    return hallazgos


def consultar_hibp_hibrido_scorecard(proveedor_nombre, dominio):
    hallazgos = []

    api_key = scorecard_get_enterprise_api_key("hibp")
    if not api_key:
        return hallazgos

    try:
        dominio_base = obtener_dominio_base(dominio)

        if not dominio_base:
            return hallazgos

        headers = {
            "hibp-api-key": api_key,
            "User-Agent": "GRAC-SGSI-Scorecard/1.0",
            "Accept": "application/json"
        }

        resp = requests.get(
            f"https://haveibeenpwned.com/api/v3/breacheddomain/{dominio_base}",
            params={"truncateResponse": "false"},
            headers=headers,
            timeout=25
        )

        if resp.status_code == 404:
            return hallazgos

        if resp.status_code in [400, 401, 403, 429]:
            return [scorecard_api_error_item("Have I Been Pwned API", f"HTTP {resp.status_code}: dominio no verificado, API key inválida, cuota o rate limit.")]

        if resp.status_code != 200:
            return hallazgos

        data = resp.json() or {}

        if not isinstance(data, dict) or not data:
            return hallazgos

        total_accounts = len(data.keys())
        breach_names = {}
        muestras = []

        for account, breaches in list(data.items())[:25]:
            breach_list = breaches or []
            muestras.append({
                "account": scorecard_mask_email(account),
                "breaches": breach_list[:10]
            })
            for b in breach_list:
                breach_names[b] = breach_names.get(b, 0) + 1

        top_breaches = sorted(breach_names.items(), key=lambda x: x[1], reverse=True)[:8]

        severidad = "Medio"
        if total_accounts > 2:
            severidad = "Alto"
        if total_accounts > 10:
            severidad = "Crítico"

        hallazgos.append({
            "fuente": "Have I Been Pwned API",
            "tipo_exposicion": "Cuentas del dominio en brechas",
            "indicador": f"{dominio_base} - {total_accounts} cuentas afectadas",
            "severidad": severidad,
            "fecha": datetime.now().strftime("%Y-%m-%d"),
            "evidencia": (
                f"HIBP reportó {total_accounts} cuentas del dominio {dominio_base} asociadas a brechas. "
                f"Brechas más frecuentes: {', '.join([x[0] for x in top_breaches])}."
            ),
            "recomendacion": (
                "Exigir al proveedor revisión de cuentas afectadas, rotación de credenciales, MFA y detección de password reuse."
            ),
            "url": "https://haveibeenpwned.com/",
            "credencial_confirmada": True,
            "detalle": {
                "total_accounts": total_accounts,
                "top_breaches": top_breaches,
                "samples_masked": muestras,
                "raw_accounts_masked": True
            }
        })

    except Exception as e:
        hallazgos.append(scorecard_api_error_item("Have I Been Pwned API", repr(e)))

    return hallazgos


def consultar_shodan_hibrido_scorecard(ip, dominio):
    hallazgos = []

    api_key = scorecard_get_enterprise_api_key("shodan")
    if not api_key:
        return hallazgos

    if not ip:
        return hallazgos

    try:
        resp = requests.get(
            f"https://api.shodan.io/shodan/host/{ip}",
            params={"key": api_key},
            timeout=25
        )

        if resp.status_code == 404:
            return hallazgos

        if resp.status_code in [400, 401, 403, 429]:
            return [scorecard_api_error_item("Shodan API", f"HTTP {resp.status_code}: API key inválida, sin créditos o rate limit.")]

        if resp.status_code != 200:
            return hallazgos

        data = resp.json() or {}
        ports = data.get("ports") or []
        vulns = data.get("vulns") or {}
        hostnames = data.get("hostnames") or []

        cves = []
        if isinstance(vulns, dict):
            for cve, detail in vulns.items():
                cvss = 0
                try:
                    if isinstance(detail, dict):
                        cvss = float(detail.get("cvss") or 0)
                except Exception:
                    cvss = 0
                cves.append({"cve": cve, "cvss": cvss})

        critical_cves = [x for x in cves if x["cvss"] >= 9]
        high_cves = [x for x in cves if 7 <= x["cvss"] < 9]

        if critical_cves:
            severidad = "Crítico"
        elif high_cves or len(cves) > 0:
            severidad = "Alto"
        elif len(ports) >= 8:
            severidad = "Medio"
        else:
            severidad = "Bajo"

        if ports or cves:
            hallazgos.append({
                "fuente": "Shodan API",
                "tipo_exposicion": "Servicios expuestos / CVEs",
                "indicador": f"{ip} - puertos: {', '.join(str(p) for p in ports[:20])}",
                "severidad": severidad,
                "fecha": datetime.now().strftime("%Y-%m-%d"),
                "evidencia": (
                    f"Shodan reportó {len(ports)} puertos observados y {len(cves)} CVEs para la IP {ip}. "
                    f"Hostnames: {', '.join(hostnames[:5])}."
                ),
                "recomendacion": (
                    "Validar exposición de servicios, cerrar puertos innecesarios, aplicar hardening y corregir CVEs."
                ),
                "url": f"https://www.shodan.io/host/{ip}",
                "credencial_confirmada": False,
                "detalle": {
                    "ip": ip,
                    "ports": ports,
                    "hostnames": hostnames,
                    "cves": cves[:50],
                    "critical_cves": critical_cves[:20],
                    "high_cves": high_cves[:20],
                    "org": data.get("org"),
                    "isp": data.get("isp"),
                    "country": data.get("country_name")
                }
            })

    except Exception as e:
        hallazgos.append(scorecard_api_error_item("Shodan API", repr(e)))

    return hallazgos


def scorecard_score_hacker_chatter(total_hallazgos, credencial_confirmada=False, severidad_max="Bajo"):
    total_hallazgos = int(total_hallazgos or 0)

    if credencial_confirmada:
        return scorecard_get_param("darkweb_score_credenciales_confirmadas", 20), "Crítico"

    if total_hallazgos <= 0:
        return scorecard_get_param("darkweb_score_sin_hallazgos", 100), "Bajo"

    if total_hallazgos <= 2:
        base = scorecard_get_param("darkweb_score_1_2", 80)
        riesgo = "Medio"
    elif total_hallazgos <= 5:
        base = scorecard_get_param("darkweb_score_3_5", 60)
        riesgo = "Alto"
    else:
        base = scorecard_get_param("darkweb_score_mas_5", 40)
        riesgo = "Crítico"

    if severidad_max == "Crítico":
        base = min(base, 35)
        riesgo = "Crítico"
    elif severidad_max == "Alto":
        base = min(base, 55)
        if riesgo in ["Bajo", "Medio"]:
            riesgo = "Alto"

    return max(0, min(100, float(base))), riesgo


def guardar_scorecard_darkweb_exposure(run_id, proveedor_id, proveedor_nombre, dominio, item):
    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO scorecard_darkweb_exposures
        (run_id, proveedor_id, proveedor_nombre, dominio, fuente, tipo_exposicion,
         indicador, severidad, fecha, evidencia, recomendacion, url,
         credencial_confirmada, detalle_json, fecha_registro)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id,
        proveedor_id,
        proveedor_nombre,
        dominio,
        item.get("fuente"),
        item.get("tipo_exposicion"),
        item.get("indicador"),
        item.get("severidad"),
        item.get("fecha"),
        item.get("evidencia"),
        item.get("recomendacion"),
        item.get("url"),
        1 if item.get("credencial_confirmada") else 0,
        json.dumps(item, ensure_ascii=False),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def consultar_hacker_chatter_gdelt_scorecard(proveedor_nombre, dominio):
    hallazgos = []

    try:
        terminos = []
        proveedor_nombre = (proveedor_nombre or "").strip()
        dominio_limpio = limpiar_dominio_scorecard(dominio)
        dominio_base = obtener_dominio_base(dominio_limpio)

        palabras = [
            "leak", "leaked", "credential", "credentials", "password", "dump",
            "database dump", "paste", "breached", "compromised", "ransomware",
            "extortion", "exploit", "hacker forum", "for sale", "stealer logs", "infostealer"
        ]

        if proveedor_nombre and proveedor_nombre != "Proveedor no asociado":
            for palabra in palabras[:12]:
                terminos.append(f'"{proveedor_nombre}" "{palabra}"')

        if dominio_base:
            for palabra in palabras:
                terminos.append(f'"{dominio_base}" "{palabra}"')

        query = " OR ".join(terminos[:22])
        if not query:
            return []

        resp = requests.get(
            "https://api.gdeltproject.org/api/v2/doc/doc",
            params={"query": query, "mode": "ArtList", "format": "json", "maxrecords": 30, "sort": "HybridRel"},
            timeout=20
        )

        if resp.status_code != 200:
            return []

        data = resp.json() or {}
        articles = data.get("articles") or []
        vistos = set()

        for art in articles:
            titulo = (art.get("title") or "").strip()
            url = (art.get("url") or "").strip()
            if not titulo or not url:
                continue
            if url.lower() in vistos:
                continue
            vistos.add(url.lower())

            texto = f"{titulo} {art.get('domain','')} {art.get('seendate','')}".lower()

            severidad = "Medio"
            tipo = "Mención pública de exposición"

            if any(x in texto for x in ["credential", "credentials", "password", "dump", "database dump", "leaked database", "stealer", "infostealer"]):
                severidad = "Alto"
                tipo = "Posible fuga de credenciales o datos"

            if any(x in texto for x in ["ransomware", "extortion", "for sale", "hacker forum", "compromised"]):
                severidad = "Crítico"
                tipo = "Hacker chatter crítico / posible compromiso"

            hallazgos.append({
                "fuente": art.get("sourceCountry") or "GDELT / Noticias públicas",
                "tipo_exposicion": tipo,
                "indicador": titulo[:500],
                "severidad": severidad,
                "fecha": scorecard_normalizar_fecha(art.get("seendate")),
                "evidencia": f"Mención pública relacionada con exposición: {titulo[:700]}",
                "recomendacion": "Validar la fuente, solicitar aclaración formal al proveedor y exigir evidencias de contención si aplica.",
                "url": url,
                "credencial_confirmada": False,
                "detalle": art
            })

    except Exception as e:
        print("Error consultando Hacker Chatter GDELT Scorecard:", repr(e))

    return hallazgos


def consultar_certificados_ct_scorecard(dominio):
    """
    Fuente segura: crt.sh.
    No es dark web, pero ayuda a detectar superficie expuesta:
    subdominios publicados en Certificate Transparency.
    """
    hallazgos = []

    try:
        dominio = limpiar_dominio_scorecard(dominio)
        if not dominio:
            return []

        resp = requests.get(
            "https://crt.sh/",
            params={"q": f"%.{dominio}", "output": "json"},
            timeout=20
        )

        if resp.status_code != 200:
            return []

        try:
            data = resp.json() or []
        except Exception:
            return []

        vistos = set()
        subdominios = []

        for item in data[:100]:
            name_value = (item.get("name_value") or "").strip()
            for raw in name_value.splitlines():
                sub = raw.strip().lower().replace("*.", "")
                if sub.endswith(dominio) and sub not in vistos:
                    vistos.add(sub)
                    subdominios.append(sub)

        total = len(subdominios)

        if total >= 20:
            severidad = "Medio"
            evidencia = f"Se identificaron {total} subdominios en Certificate Transparency. Ejemplos: {', '.join(subdominios[:15])}"
            recomendacion = "Revisar si los subdominios publicados están autorizados y si exponen servicios no aprobados."
        elif total > 0:
            severidad = "Bajo"
            evidencia = f"Se identificaron {total} subdominios públicos en Certificate Transparency. Ejemplos: {', '.join(subdominios[:10])}"
            recomendacion = "Mantener inventario de subdominios públicos y monitoreo de exposición."
        else:
            return []

        hallazgos.append({
            "fuente": "crt.sh / Certificate Transparency",
            "tipo_exposicion": "Superficie pública expuesta",
            "indicador": f"Subdominios públicos detectados para {dominio}",
            "severidad": severidad,
            "fecha": datetime.now().strftime("%Y-%m-%d"),
            "evidencia": evidencia,
            "recomendacion": recomendacion,
            "url": f"https://crt.sh/?q=%25.{dominio}",
            "credencial_confirmada": False,
            "detalle": {"total_subdominios": total, "subdominios_muestra": subdominios[:50]}
        })

    except Exception as e:
        print("Error consultando crt.sh Scorecard:", repr(e))

    return hallazgos


def consultar_github_exposure_scorecard(proveedor_nombre, dominio):
    hallazgos = []

    try:
        dominio_limpio = limpiar_dominio_scorecard(dominio)
        dominio_base = obtener_dominio_base(dominio_limpio)
        proveedor_nombre = (proveedor_nombre or "").strip()

        queries = []

        if dominio_base:
            queries.append(f'"{dominio_base}" password')
            queries.append(f'"{dominio_base}" api_key')
            queries.append(f'"{dominio_base}" secret')
            queries.append(f'"{dominio_base}" token')
            queries.append(f'"{dominio_base}" private_key')

        if proveedor_nombre and proveedor_nombre != "Proveedor no asociado":
            queries.append(f'"{proveedor_nombre}" password')
            queries.append(f'"{proveedor_nombre}" api_key')
            queries.append(f'"{proveedor_nombre}" secret')

        vistos = set()

        for q in queries[:7]:
            resp = requests.get(
                "https://api.github.com/search/code",
                params={"q": q, "per_page": 5},
                headers={"Accept": "application/vnd.github+json"},
                timeout=15
            )

            if resp.status_code not in [200, 403, 422]:
                continue

            if resp.status_code in [403, 422]:
                break

            data = resp.json() or {}
            items = data.get("items") or []

            for it in items:
                html_url = (it.get("html_url") or "").strip()
                repo = ((it.get("repository") or {}).get("full_name") or "").strip()
                path = (it.get("path") or "").strip()

                if not html_url or html_url.lower() in vistos:
                    continue

                vistos.add(html_url.lower())

                hallazgos.append({
                    "fuente": "GitHub Search pública",
                    "tipo_exposicion": "Posible exposición en repositorio público",
                    "indicador": f"{repo}/{path}"[:500],
                    "severidad": "Alto",
                    "fecha": datetime.now().strftime("%Y-%m-%d"),
                    "evidencia": "Se encontró una posible mención pública asociada a secretos, tokens, API keys o contraseñas. Debe validarse manualmente.",
                    "recomendacion": "Validar repositorio, revocar secretos expuestos y solicitar remediación formal al proveedor.",
                    "url": html_url,
                    "credencial_confirmada": False,
                    "detalle": {"repository": repo, "path": path, "html_url": html_url, "raw_secret_omitted": True}
                })

    except Exception as e:
        print("Error consultando GitHub Exposure Scorecard:", repr(e))

    return hallazgos


def deduplicar_hacker_chatter_items(items):
    dedup = []
    vistos = set()

    for item in items:
        key = (
            (item.get("url") or "").strip().lower()
            or
            (item.get("fuente", "") + "|" + item.get("indicador", "")).strip().lower()
        )

        if not key or key in vistos:
            continue

        vistos.add(key)
        dedup.append(item)

    return dedup


def evaluar_darkweb_exposure_scorecard(run_id, proveedor_id, proveedor_nombre, dominio):
    scorecard_set_progress(
        run_id,
        pct=25,
        stage="Consultando Hacker Chatter / Exposure Intelligence híbrido",
        tool="Enterprise + OSINT"
    )

    dominio_limpio = limpiar_dominio_scorecard(dominio)
    ip = resolver_ip_scorecard(dominio_limpio)

    hallazgos = []

    # APIs Enterprise: solo se usan si tienen API Key activa.
    hallazgos.extend(consultar_leakcheck_hibrido_scorecard(proveedor_nombre, dominio_limpio))
    hallazgos.extend(consultar_hibp_hibrido_scorecard(proveedor_nombre, dominio_limpio))
    hallazgos.extend(consultar_shodan_hibrido_scorecard(ip, dominio_limpio))

    # OSINT público: siempre activo.
    hallazgos.extend(consultar_hacker_chatter_gdelt_scorecard(proveedor_nombre, dominio_limpio))
    hallazgos.extend(consultar_certificados_ct_scorecard(dominio_limpio))
    hallazgos.extend(consultar_github_exposure_scorecard(proveedor_nombre, dominio_limpio))

    hallazgos = deduplicar_hacker_chatter_items(hallazgos)

    severidad_orden = {"Bajo": 1, "Medio": 2, "Alto": 3, "Crítico": 4}
    severidad_max = "Bajo"
    credencial_confirmada = False
    total_cves = 0
    fuentes_activas = []
    hallazgos_riesgo = []
    hallazgos_info = []

    for item in hallazgos:
        tipo = (item.get("tipo_exposicion") or "").lower()
        es_info = "api no disponible" in tipo or "error controlado" in tipo

        if es_info:
            hallazgos_info.append(item)
        else:
            hallazgos_riesgo.append(item)

        if not es_info:
            sev = item.get("severidad") or "Bajo"
            if severidad_orden.get(sev, 0) > severidad_orden.get(severidad_max, 0):
                severidad_max = sev

            if item.get("credencial_confirmada"):
                credencial_confirmada = True

            detalle = item.get("detalle") or {}
            if isinstance(detalle, dict):
                total_cves += len(detalle.get("cves") or [])

        fuente = item.get("fuente") or ""
        if fuente and fuente not in fuentes_activas:
            fuentes_activas.append(fuente)

        guardar_scorecard_darkweb_exposure(
            run_id,
            proveedor_id,
            proveedor_nombre,
            dominio_limpio,
            item
        )

    total_riesgo = len(hallazgos_riesgo)
    total_info = len(hallazgos_info)

    score, riesgo = scorecard_score_hacker_chatter(
        total_riesgo,
        credencial_confirmada=credencial_confirmada,
        severidad_max=severidad_max
    )

    if total_cves >= 1 and score > 70:
        score = 70
        riesgo = "Medio"

    if total_cves >= 5 and score > 55:
        score = 55
        riesgo = "Alto"

    if severidad_max == "Crítico":
        score = min(score, 35)
        riesgo = "Crítico"

    if total_riesgo:
        evidencia = (
            f"Se identificaron {total_riesgo} señales de exposición/hacker chatter. "
            f"Severidad máxima: {severidad_max}. "
            f"Fuentes: {', '.join(fuentes_activas[:8])}. "
            f"Credenciales confirmadas: {'sí' if credencial_confirmada else 'no'}. "
            f"CVEs observadas: {total_cves}."
        )
        recomendacion = (
            "Validar hallazgos, solicitar descargos al proveedor, rotar credenciales, activar MFA, "
            "corregir CVEs, reducir exposición pública y exigir evidencia de remediación."
        )
        estado = "Con hallazgos"
    else:
        evidencia = (
            "No se identificaron señales de riesgo relevantes. "
            "Las APIs sin configurar fueron omitidas automáticamente y OSINT público se mantuvo activo."
        )
        if total_info:
            evidencia += f" Hay {total_info} aviso(s) informativos de API no disponible."
        recomendacion = "Mantener monitoreo periódico y configurar APIs enterprise si se requiere mayor profundidad."
        estado = "Sin hallazgos"

    api_estado = scorecard_api_status()

    guardar_scorecard_finding(run_id, {
        "categoria": "Hacker Chatter / Exposure Intelligence",
        "herramienta": "LeakCheck + HIBP + Shodan + GDELT + crt.sh + GitHub",
        "control": "Credenciales, identidades, brechas, CVEs, chatter y superficie expuesta",
        "estado": estado,
        "riesgo": riesgo,
        "severidad": riesgo,
        "score": score,
        "evidencia": evidencia,
        "recomendacion": recomendacion,
        "detalle": {
            "total_hallazgos_riesgo": total_riesgo,
            "total_hallazgos_info": total_info,
            "severidad_max": severidad_max,
            "credencial_confirmada": credencial_confirmada,
            "total_cves": total_cves,
            "fuentes_activas": fuentes_activas,
            "apis_configuradas": {
                "leakcheck": api_estado["leakcheck"]["activo"] and api_estado["leakcheck"]["configurada"],
                "hibp": api_estado["hibp"]["activo"] and api_estado["hibp"]["configurada"],
                "shodan": api_estado["shodan"]["activo"] and api_estado["shodan"]["configurada"]
            }
        }
    })

    scorecard_set_progress(
        run_id,
        pct=40,
        stage="Hacker Chatter / Exposure Intelligence híbrido finalizado",
        tool=None
    )

    return score, riesgo, total_riesgo, credencial_confirmada

def obtener_dominio_base(dominio):
    """
    Obtiene dominio base para evaluar SPF, DMARC, MX y NS.

    Ejemplos:
    - www.amazon.com      -> amazon.com
    - mail.google.com     -> google.com
    - app.empresa.com.co  -> empresa.com.co
    """
    try:
        dominio = limpiar_dominio_scorecard(dominio)

        if not dominio:
            return ""

        partes = dominio.split(".")

        if len(partes) <= 2:
            return dominio

        tlds_compuestos = {
            "com.co", "net.co", "org.co", "edu.co", "gov.co", "mil.co",
            "com.mx", "net.mx", "org.mx", "gob.mx", "edu.mx",
            "com.br", "net.br", "org.br", "gov.br",
            "com.ar", "net.ar", "org.ar", "gob.ar",
            "com.pe", "net.pe", "org.pe", "gob.pe",
            "com.ec", "net.ec", "org.ec", "gob.ec",
            "com.cl", "net.cl", "org.cl", "gob.cl",
            "co.uk", "com.au", "com.es"
        }

        ultimos_dos = ".".join(partes[-2:])
        ultimos_tres = ".".join(partes[-3:])

        if ultimos_dos in tlds_compuestos and len(partes) >= 3:
            return ultimos_tres

        return ultimos_dos

    except Exception:
        return dominio


# ===============================
# RUTA DE CONFIGURACIÓN API KEYS
# ===============================

@app.route("/proveedores/scorecard/apis", methods=["GET", "POST"])
@login_required
def proveedores_scorecard_apis():
    user, allowed, read_only = scorecard_user_permiso()

    if not allowed:
        flash("No tiene permiso para acceder a la configuración del Scorecard.", "danger")
        return redirect(url_for("menu"))

    if read_only:
        flash("El rol Auditor no puede modificar API Keys.", "danger")
        return redirect(url_for("proveedores_scorecard_dashboard"))

    if user.role != "admin":
        flash("Solo el administrador puede configurar API Keys del Scorecard.", "danger")
        return redirect(url_for("proveedores_scorecard_dashboard"))

    if request.method == "POST":
        accion = request.form.get("accion", "").strip()

        proveedores = ["leakcheck", "hibp", "shodan"]

        for proveedor in proveedores:
            if accion == f"guardar_{proveedor}":
                api_key = request.form.get(f"{proveedor}_api_key", "").strip()
                activo = bool(request.form.get(f"{proveedor}_activo"))

                if not api_key:
                    flash(f"Debe ingresar una API Key para {proveedor.upper()} o desactivar el servicio.", "warning")
                    return redirect(url_for("proveedores_scorecard_apis"))

                scorecard_guardar_api_key(
                    proveedor,
                    api_key,
                    activo,
                    getattr(user, "username", "Sistema")
                )

                registrar_log(
                    getattr(user, "username", "Sistema"),
                    f"Actualizó API Key cifrada para Scorecard: {proveedor}"
                )

                flash(f"API Key de {proveedor.upper()} guardada cifrada correctamente.", "success")
                return redirect(url_for("proveedores_scorecard_apis"))

            if accion == f"eliminar_{proveedor}":
                scorecard_guardar_api_key(
                    proveedor,
                    "",
                    False,
                    getattr(user, "username", "Sistema")
                )

                registrar_log(
                    getattr(user, "username", "Sistema"),
                    f"Eliminó API Key cifrada para Scorecard: {proveedor}"
                )

                flash(f"API Key de {proveedor.upper()} eliminada correctamente.", "success")
                return redirect(url_for("proveedores_scorecard_apis"))

        flash("Acción no reconocida.", "warning")
        return redirect(url_for("proveedores_scorecard_apis"))

    estado = scorecard_api_status()

    body = """
    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .score-shell{
        width:96%;
        max-width:1280px;
        margin:26px auto 30px auto;
      }

      .score-header-card{
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

      .score-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .score-header-overlay{
        width:100%;
        display:flex;
        align-items:center;
        justify-content:flex-start;
        text-align:left;
        position:relative;
        z-index:1;
      }

      .score-header-overlay::before{
        content:"🔐";
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

      .score-header-text{
        color:#ffffff !important;
        font-size:1.32rem;
        font-weight:950;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .score-header-text::before{
        content:"SGSI · Scorecard Enterprise";
        display:block;
        width:max-content;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
        text-shadow:none;
      }

      .api-card{
        background:rgba(255,255,255,.96);
        border:1px solid rgba(219,230,244,.9);
        border-radius:18px;
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        padding:20px;
        height:100%;
      }

      .api-title{
        font-weight:950;
        color:#0b4a8f;
        margin-bottom:4px;
      }

      .api-sub{
        color:#475569;
        font-size:.9rem;
        font-weight:700;
        margin-bottom:14px;
      }

      .api-mask{
        background:#eef5ff;
        border:1px solid #d9eaff;
        color:#0b4a8f;
        border-radius:10px;
        padding:8px 10px;
        font-weight:900;
        margin-bottom:12px;
      }

      .form-control{
        border-radius:12px;
        font-weight:700;
      }

      .btn{
        border-radius:999px !important;
        font-weight:900;
      }
    </style>

    <div class="score-shell">
      <div class="score-header-card">
        <div class="score-header-overlay">
          <h1 class="score-header-text">Configuración API Keys — Scorecard de Seguridad de Proveedores</h1>
        </div>
      </div>

      <div class="d-flex justify-content-between mb-3">
        <a href="{{ url_for('proveedores_scorecard_dashboard') }}" class="btn btn-outline-secondary px-4">
          Volver
        </a>
      </div>

      <div class="alert alert-info">
        Las API Keys se guardan <strong>cifradas</strong> en la base de datos del Scorecard.
        Si una API no está configurada o está inactiva, el módulo la omite sin generar error.
      </div>

      <div class="row g-3">
        <div class="col-md-4">
          <div class="api-card">
            <h4 class="api-title">LeakCheck</h4>
            <div class="api-sub">Credenciales, identidades y registros filtrados.</div>

            <div class="api-mask">
              Estado:
              {% if estado.leakcheck.activo and estado.leakcheck.configurada %}
                <span class="badge bg-success">Activo</span>
              {% else %}
                <span class="badge bg-secondary">Inactivo</span>
              {% endif %}
              <br>
              Key: {{ estado.leakcheck.mask }}
            </div>

            <form method="POST">
              <input type="hidden" name="accion" value="guardar_leakcheck">
              <div class="mb-2">
                <label class="form-label fw-bold">API Key LeakCheck</label>
                <input type="password" name="leakcheck_api_key" class="form-control" placeholder="Ingrese nueva API Key">
              </div>
              <div class="form-check form-switch mb-3">
                <input class="form-check-input" type="checkbox" name="leakcheck_activo" id="leakcheck_activo"
                  {% if estado.leakcheck.activo %}checked{% endif %}>
                <label class="form-check-label fw-bold" for="leakcheck_activo">Activar LeakCheck</label>
              </div>
              <button class="btn btn-primary w-100 mb-2">Guardar LeakCheck</button>
            </form>

            <form method="POST" onsubmit="return confirm('¿Eliminar API Key LeakCheck?');">
              <input type="hidden" name="accion" value="eliminar_leakcheck">
              <button class="btn btn-outline-danger w-100">Eliminar Key</button>
            </form>
          </div>
        </div>

        <div class="col-md-4">
          <div class="api-card">
            <h4 class="api-title">Have I Been Pwned</h4>
            <div class="api-sub">Brechas asociadas a dominios verificados.</div>

            <div class="api-mask">
              Estado:
              {% if estado.hibp.activo and estado.hibp.configurada %}
                <span class="badge bg-success">Activo</span>
              {% else %}
                <span class="badge bg-secondary">Inactivo</span>
              {% endif %}
              <br>
              Key: {{ estado.hibp.mask }}
            </div>

            <form method="POST">
              <input type="hidden" name="accion" value="guardar_hibp">
              <div class="mb-2">
                <label class="form-label fw-bold">API Key HIBP</label>
                <input type="password" name="hibp_api_key" class="form-control" placeholder="Ingrese nueva API Key">
              </div>
              <div class="form-check form-switch mb-3">
                <input class="form-check-input" type="checkbox" name="hibp_activo" id="hibp_activo"
                  {% if estado.hibp.activo %}checked{% endif %}>
                <label class="form-check-label fw-bold" for="hibp_activo">Activar HIBP</label>
              </div>
              <button class="btn btn-primary w-100 mb-2">Guardar HIBP</button>
            </form>

            <form method="POST" onsubmit="return confirm('¿Eliminar API Key HIBP?');">
              <input type="hidden" name="accion" value="eliminar_hibp">
              <button class="btn btn-outline-danger w-100">Eliminar Key</button>
            </form>
          </div>
        </div>

        <div class="col-md-4">
          <div class="api-card">
            <h4 class="api-title">Shodan</h4>
            <div class="api-sub">Puertos, exposición pública y CVEs por IP.</div>

            <div class="api-mask">
              Estado:
              {% if estado.shodan.activo and estado.shodan.configurada %}
                <span class="badge bg-success">Activo</span>
              {% else %}
                <span class="badge bg-secondary">Inactivo</span>
              {% endif %}
              <br>
              Key: {{ estado.shodan.mask }}
            </div>

            <form method="POST">
              <input type="hidden" name="accion" value="guardar_shodan">
              <div class="mb-2">
                <label class="form-label fw-bold">API Key Shodan</label>
                <input type="password" name="shodan_api_key" class="form-control" placeholder="Ingrese nueva API Key">
              </div>
              <div class="form-check form-switch mb-3">
                <input class="form-check-input" type="checkbox" name="shodan_activo" id="shodan_activo"
                  {% if estado.shodan.activo %}checked{% endif %}>
                <label class="form-check-label fw-bold" for="shodan_activo">Activar Shodan</label>
              </div>
              <button class="btn btn-primary w-100 mb-2">Guardar Shodan</button>
            </form>

            <form method="POST" onsubmit="return confirm('¿Eliminar API Key Shodan?');">
              <input type="hidden" name="accion" value="eliminar_shodan">
              <button class="btn btn-outline-danger w-100">Eliminar Key</button>
            </form>
          </div>
        </div>
      </div>
    </div>
    """

    return render_template_string(
        BASE,
        content=Markup(render_template_string(body, estado=estado))
    )

# ============================================================
# DASHBOARD
# ============================================================

@app.route("/proveedores/scorecard")
@login_required
def proveedores_scorecard_dashboard():
    user, allowed, read_only = scorecard_user_permiso()

    if not allowed:
        flash("No tiene permiso para acceder al Scorecard de Proveedores.", "danger")
        return redirect(url_for("menu"))

    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM scorecard_runs
        ORDER BY id DESC
        LIMIT 200
    """)
    runs = cur.fetchall()

    cur.execute("SELECT COUNT(*) total FROM scorecard_runs")
    total = cur.fetchone()["total"] or 0

    cur.execute("SELECT AVG(score_total) promedio FROM scorecard_runs WHERE estado = 'finalizado'")
    promedio = cur.fetchone()["promedio"] or 0

    niveles_riesgo_activos = scorecard_risk_levels_activos()
    niveles_malos = [
        n["nombre"] for n in niveles_riesgo_activos
        if float(n["score_min"] or 0) <= 50
    ]

    if niveles_malos:
        placeholders = ",".join(["?"] * len(niveles_malos))
        cur.execute(f"""
            SELECT COUNT(*) total
            FROM scorecard_runs
            WHERE nivel_riesgo IN ({placeholders})
        """, niveles_malos)
        alto_critico = cur.fetchone()["total"] or 0
    else:
        alto_critico = 0

    conn.close()

    api_estado = scorecard_api_status()

    body = """
    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .score-shell{
        width:96%;
        max-width:1720px;
        margin:26px auto 24px auto;
      }

      .score-header-card{
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

      .score-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(
            135deg,
            rgba(255,255,255,.05) 0px,
            rgba(255,255,255,.05) 1px,
            transparent 1px,
            transparent 14px
          );
        pointer-events:none;
      }

      .score-header-overlay{
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

      .score-header-overlay::before{
        content:"📈";
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

      .score-header-text{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
        color:#ffffff !important;
        font-size:1.32rem;
        font-weight:950;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .score-header-text::before{
        content:"SGSI · Scorecard";
        display:block;
        width:max-content;
        max-width:100%;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
        text-shadow:none;
      }

      .score-kpi{
        padding:18px;
        border-radius:18px;
        background:rgba(255,255,255,.96);
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
      }

      .score-kpi .label{
        font-size:.72rem;
        color:#0b4a8f;
        font-weight:900;
        text-transform:uppercase;
        letter-spacing:.35px;
        background:#eef5ff;
        border:1px solid #d9eaff;
        padding:6px 10px;
        border-radius:10px;
        display:inline-block;
        margin-bottom:8px;
      }

      .score-kpi .value{
        font-size:2rem;
        font-weight:950;
        color:#0b4a8f;
        line-height:1.1;
      }

      .soft-table-wrap{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        overflow:hidden;
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
      }

      .score-table-scroll{
        max-height:620px;
        overflow:auto;
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
        font-weight:900 !important;
        border:none !important;
        white-space:nowrap;
        vertical-align:middle !important;
        text-align:center;
        padding:9px 8px;
      }

      .table tbody td,
      .table td{
        vertical-align:middle !important;
        font-size:.82rem;
        padding:9px 8px;
        border-bottom:1px solid #e5edf7;
        color:#101827;
        white-space:nowrap;
      }

      .table tbody tr:nth-child(even){
        background:#f8fbff;
      }

      .table tbody tr:hover{
        background:#eef6ff;
      }

      .badge{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }

      .btn{
        border-radius:10px !important;
        font-weight:900;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }

      /* ======================================================
         BOTON API AZUL SGSI
      ====================================================== */
      .btn-api-blue{
        background:linear-gradient(135deg,#0b4a8f,#2f7fd1) !important;
        border:none !important;
        color:#ffffff !important;
        border-radius:999px !important;
        padding:10px 22px !important;
        font-size:.84rem !important;
        font-weight:900 !important;
        box-shadow:0 10px 22px rgba(20,89,166,.35) !important;
        transition:all .18s ease-in-out;
      }

      .btn-api-blue:hover{
        background:linear-gradient(135deg,#0f4f97,#266fbb) !important;
        color:#ffffff !important;
        transform:translateY(-1px);
        box-shadow:0 14px 26px rgba(20,89,166,.45) !important;
      }

      .btn-api-blue:focus,
      .btn-api-blue:active{
        background:linear-gradient(135deg,#0f4f97,#266fbb) !important;
        color:#ffffff !important;
        outline:none !important;
        box-shadow:0 0 0 .18rem rgba(47,127,209,.25) !important;
      }

      .api-mini{
        background:rgba(255,255,255,.96);
        border:1px solid rgba(219,230,244,.9);
        border-radius:16px;
        padding:12px 14px;
        box-shadow:0 8px 18px rgba(15,23,42,.12);
        margin-bottom:14px;
      }

      .api-mini-title{
        font-weight:950;
        color:#0b4a8f;
        font-size:.84rem;
        text-transform:uppercase;
      }
    </style>

    <div class="score-shell">
      <div class="score-header-card">
        <div class="score-header-overlay">
          <h1 class="score-header-text">Scorecard de Seguridad de Proveedores</h1>
        </div>
      </div>

      <div class="d-flex justify-content-end mb-3 gap-2 flex-wrap">
        {% if not read_only %}
            {% if user.role == 'admin' %}
              <a href="{{ url_for('admin_scorecard_proponentes_apis') }}" class="btn btn-api-blue">
                🔐 Configurar APIs
              </a>
            {% endif %}

            <a href="{{ url_for('proveedores_scorecard_parametros') }}" class="btn btn-secondary rounded-pill px-4">
              ⚙️ Parámetros Scorecard
            </a>

            <a href="{{ url_for('proveedores_scorecard_scan_nuevo') }}" class="btn btn-primary rounded-pill px-4">
              🚀 Ejecutar Escaneo Scorecard
            </a>
        {% endif %}
      </div>

      <div class="api-mini">
        <div class="api-mini-title mb-2">Fuentes Enterprise configuradas</div>
        <span class="badge bg-{% if api_estado.leakcheck.activo and api_estado.leakcheck.configurada %}success{% else %}secondary{% endif %}">
          LeakCheck
        </span>
        <span class="badge bg-{% if api_estado.hibp.activo and api_estado.hibp.configurada %}success{% else %}secondary{% endif %}">
          HIBP
        </span>
        <span class="badge bg-{% if api_estado.shodan.activo and api_estado.shodan.configurada %}success{% else %}secondary{% endif %}">
          Shodan
        </span>
        <span class="badge bg-info text-dark">OSINT público activo</span>
      </div>

      <div class="row g-3 mb-3">
        <div class="col-md-4">
          <div class="score-kpi">
            <div class="label">Evaluaciones ejecutadas</div>
            <div class="value">{{ total }}</div>
          </div>
        </div>
        <div class="col-md-4">
          <div class="score-kpi">
            <div class="label">Score promedio</div>
            <div class="value">{{ "%.1f"|format(promedio) }}%</div>
          </div>
        </div>
        <div class="col-md-4">
          <div class="score-kpi">
            <div class="label">Riesgos críticos / no aceptables</div>
            <div class="value">{{ alto_critico }}</div>
          </div>
        </div>
      </div>

      <div class="soft-table-wrap p-3">
        <div class="table-responsive score-table-scroll">
          <table class="table table-hover align-middle mb-0">
            <thead>
              <tr>
                <th>ID</th>
                <th>Proveedor</th>
                <th>Dominio</th>
                <th>IP</th>
                <th>DNS</th>
                <th>IP Rep.</th>
                <th>Kali</th>
                <th>Hacker Chatter</th>
                <th>Total</th>
                <th>Riesgo</th>
                <th>Estado</th>
                <th>Progreso</th>
                <th>Fecha</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {% for r in runs %}
              <tr>
                <td>#{{ r.id }}</td>
                <td>{{ r.proveedor_nombre or '—' }}</td>
                <td>{{ r.dominio }}</td>
                <td>{{ r.ip_resuelta or '—' }}</td>
                <td>{{ "%.1f"|format(r.score_dns or 0) }}%</td>
                <td>{{ "%.1f"|format(r.score_ip or 0) }}%</td>
                <td>{{ "%.1f"|format(r.score_kali or 0) }}%</td>
                <td>{{ "%.1f"|format(r.score_darkweb or 100) }}%</td>
                <td><strong>{{ "%.1f"|format(r.score_total or 0) }}%</strong></td>
                <td>
                  <span class="badge bg-{{ scorecard_badge_color(r.nivel_riesgo) }}">
                    {{ r.nivel_riesgo or 'Pendiente' }}
                  </span>
                </td>
                <td>{{ r.estado }}</td>
                <td>{{ r.progress_pct or 0 }}%</td>
                <td>{{ r.fecha_ejecucion }}</td>
                <td>
                  <div class="d-flex gap-1 flex-wrap">
                    <a class="btn btn-sm btn-outline-primary rounded-pill"
                       href="{{ url_for('proveedores_scorecard_detalle', scorecard_id=r.id) }}">
                      Ver
                    </a>

                    <a class="btn btn-sm btn-outline-success rounded-pill"
                        href="{{ url_for('proveedores_scorecard_rating', scorecard_id=r.id) }}">
                       Gráfica
                    </a>

                    {% if not read_only %}
                    <form method="POST"
                          action="{{ url_for('proveedores_scorecard_eliminar', scorecard_id=r.id) }}"
                          onsubmit="return confirm('¿Está seguro de eliminar este Scorecard? Esta acción no se puede deshacer.');"
                          style="display:inline;">
                      <button type="submit" class="btn btn-sm btn-outline-danger rounded-pill">
                        Eliminar
                      </button>
                    </form>
                    {% endif %}
                  </div>
                </td>
              </tr>
              {% else %}
              <tr>
                <td colspan="14" class="text-center text-muted py-4">
                  No hay evaluaciones de scorecard registradas.
                </td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
    </div>
    """

    return render_template_string(
        BASE,
        content=Markup(render_template_string(
            body,
            runs=runs,
            total=total,
            promedio=promedio,
            alto_critico=alto_critico,
            read_only=read_only,
            user=user,
            api_estado=api_estado,
            scorecard_badge_color=scorecard_badge_color
        ))
    )



# ============================================================
# NUEVA PANTALLA EXCLUSIVA DE ESCANEO SCORECARD
# ============================================================

@app.route("/proveedores/scorecard/scan/nuevo", methods=["GET", "POST"])
@login_required
def proveedores_scorecard_scan_nuevo():
    user, allowed, read_only = scorecard_user_permiso()

    if not allowed:
        flash("No tiene permiso para ejecutar Scorecard de Proveedores.", "danger")
        return redirect(url_for("menu"))

    if read_only:
        flash("El rol Auditor no puede ejecutar scorecards.", "danger")
        return redirect(url_for("proveedores_scorecard_dashboard"))

    proveedores = ProveedorEvaluacion.query.order_by(ProveedorEvaluacion.nombre_proveedor.asc()).all()

    if request.method == "POST":
        proveedor_id = request.form.get("proveedor_id", type=int)
        dominio = limpiar_dominio_scorecard(request.form.get("dominio"))
        ejecutar_kali = bool(request.form.get("ejecutar_kali"))

        if not dominio:
            flash("Debe indicar el dominio autorizado del proveedor.", "danger")
            return redirect(url_for("proveedores_scorecard_scan_nuevo"))

        proveedor = ProveedorEvaluacion.query.get(proveedor_id) if proveedor_id else None
        proveedor_nombre = proveedor.nombre_proveedor if proveedor else "Proveedor no asociado"

        ip = resolver_ip_scorecard(dominio)

        score_dns, findings_dns = evaluar_dns_health_scorecard(dominio)
        score_ip, findings_ip = evaluar_ip_reputation_scorecard(ip)

        score_kali = 0
        score_incidentes = 100
        score_darkweb = 100

        estado = "finalizado"
        progress = 100
        current_stage = "Scorecard finalizado sin escaneo Kali"

        if ejecutar_kali:
            estado = "pendiente"
            progress = 1
            current_stage = "Escaneo Kali pendiente"

        score_total = scorecard_calcular_total(
            score_dns,
            score_ip,
            score_kali,
            score_incidentes,
            score_darkweb,
            incluir_kali=ejecutar_kali
        )
        nivel = nivel_riesgo_scorecard(score_total)

        resumen = {
            "dns_score": score_dns,
            "ip_score": score_ip,
            "kali_score": score_kali,
            "incident_score": score_incidentes,
            "darkweb_score": score_darkweb,
            "score_total": score_total,
            "nivel_riesgo": nivel,
            "ejecutar_kali": ejecutar_kali
        }

        conn = get_scorecard_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO scorecard_runs
            (proveedor_id, proveedor_nombre, dominio, ip_resuelta,
             score_dns, score_ip, score_kali, score_incidentes, score_darkweb,
             score_total, nivel_riesgo, estado, progress_pct, current_stage,
             current_tool, resumen_json, usuario, fecha_ejecucion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            proveedor_id,
            proveedor_nombre,
            dominio,
            ip,
            score_dns,
            score_ip,
            score_kali,
            score_incidentes,
            score_darkweb,
            score_total,
            nivel,
            estado,
            progress,
            current_stage,
            None,
            json.dumps(resumen, ensure_ascii=False),
            getattr(user, "username", "Sistema"),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        scorecard_id = cur.lastrowid
        conn.commit()
        conn.close()

        for item in findings_dns + findings_ip:
            guardar_scorecard_finding(scorecard_id, item)

        score_incidentes, riesgo_incidentes, total_incidentes = evaluar_incident_history_scorecard(
            scorecard_id,
            proveedor_id,
            proveedor_nombre,
            dominio
        )

        score_darkweb, riesgo_darkweb, total_darkweb, credencial_confirmada = evaluar_darkweb_exposure_scorecard(
            scorecard_id,
            proveedor_id,
            proveedor_nombre,
            dominio
        )

        score_total = scorecard_calcular_total(
            score_dns,
            score_ip,
            score_kali,
            score_incidentes,
            score_darkweb,
            incluir_kali=ejecutar_kali
        )
        nivel = nivel_riesgo_scorecard(score_total)

        resumen = {
            "dns_score": score_dns,
            "ip_score": score_ip,
            "kali_score": score_kali,
            "incident_score": score_incidentes,
            "darkweb_score": score_darkweb,
            "total_incidentes": total_incidentes,
            "total_darkweb": total_darkweb,
            "riesgo_incidentes": riesgo_incidentes,
            "riesgo_darkweb": riesgo_darkweb,
            "credencial_confirmada": credencial_confirmada,
            "score_total": score_total,
            "nivel_riesgo": nivel,
            "ejecutar_kali": ejecutar_kali,
            "fuentes_darkweb": "GDELT + crt.sh + GitHub Search pública"
        }

        conn = get_scorecard_db_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE scorecard_runs
            SET score_incidentes = ?, score_darkweb = ?, score_total = ?,
                nivel_riesgo = ?, resumen_json = ?
            WHERE id = ?
        """, (
            score_incidentes,
            score_darkweb,
            score_total,
            nivel,
            json.dumps(resumen, ensure_ascii=False),
            scorecard_id
        ))
        conn.commit()
        conn.close()

        if ejecutar_kali:
            hilo = threading.Thread(
                target=scorecard_kali_worker,
                args=(scorecard_id, dominio),
                daemon=True
            )
            hilo.start()

        registrar_log(
            getattr(user, "username", "Sistema"),
            f"Ejecutó Scorecard proveedor con Hacker Chatter / Exposure Intelligence: {proveedor_nombre} - {dominio}"
        )

        flash("Scorecard creado correctamente. Se validó DNS, reputación IP, incidentes, Hacker Chatter / Exposure Intelligence y Kali si fue seleccionado.", "success")
        return redirect(url_for("proveedores_scorecard_detalle", scorecard_id=scorecard_id))

    body = """
    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .score-shell{
        width:96%;
        max-width:1150px;
        margin:26px auto 24px auto;
      }

      .score-header-card{
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

      .score-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      /* ✅ LOGO A LA IZQUIERDA */
      .score-header-card::after{
        content:"⚙️";
        order:-1;
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
        position:relative;
        z-index:1;
      }

      .score-header-text{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
        color:#ffffff !important;
        font-size:1.32rem;
        font-weight:950;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
        position:relative;
        z-index:1;
      }

      .score-header-text::before{
        content:"SGSI · Configuración Scorecard";
        display:block;
        width:max-content;
        max-width:100%;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
        text-shadow:none;
      }

      .score-card,
      .card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
        padding:24px;
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

      @media (max-width:992px){
        .score-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .score-header-card{
          min-height:88px;
        }

        .score-header-text{
          font-size:1.20rem;
        }

        .score-card,
        .card{
          padding:16px;
        }
      }

      @media (max-width:768px){
        .score-header-card{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .score-header-card::after{
          margin:0;
        }

        .score-header-text,
        .score-header-text::before{
          text-align:center;
          margin-left:auto;
          margin-right:auto;
        }
      }
    </style>

    <div class="score-shell">
      <div class="score-header-card">
        <h1 class="score-header-text">Nuevo Escaneo Scorecard de Proveedor</h1>
      </div>

      <div class="score-card">
        <form method="POST" data-progress-text="Creando Scorecard y ejecutando validaciones...">
          <div class="mb-3">
            <label class="form-label fw-bold">Proveedor</label>
            <select name="proveedor_id" class="form-select">
              <option value="">Proveedor no asociado</option>
              {% for p in proveedores %}
                <option value="{{ p.id }}">{{ p.nombre_proveedor }}</option>
              {% endfor %}
            </select>
          </div>

          <div class="mb-3">
            <label class="form-label fw-bold">Dominio / URL autorizada</label>
            <input name="dominio" class="form-control" placeholder="ejemplo.com" required>
          </div>

          <div class="alert alert-info">
            <strong>Validaciones incluidas:</strong><br>
            DNS Health, IP Reputation, Incidentes/Brechas,
            <strong>Hacker Chatter / Exposure Intelligence</strong>
            mediante <strong>GDELT + crt.sh + GitHub Search pública</strong>,
            y Kali Linux si se selecciona.
          </div>

          <div class="form-check form-switch mb-4">
            <input class="form-check-input" type="checkbox" name="ejecutar_kali" id="ejecutar_kali" checked>
            <label class="form-check-label fw-bold" for="ejecutar_kali">
              Ejecutar escaneo Kali independiente: Nmap, WhatWeb, Nikto, Nuclei y testssl
            </label>
          </div>

          <div class="d-flex justify-content-between">
            <a href="{{ url_for('proveedores_scorecard_dashboard') }}" class="btn btn-outline-secondary rounded-pill px-4">Volver</a>
            <button class="btn btn-primary rounded-pill px-4">🚀 Ejecutar Scorecard</button>
          </div>
        </form>
      </div>
    </div>
    """

    return render_template_string(BASE, content=Markup(render_template_string(body, proveedores=proveedores)))


# ============================================================
# DETALLE SCORECARD
# ============================================================

@app.route("/proveedores/scorecard/<int:scorecard_id>/estado")
@login_required
def proveedores_scorecard_estado(scorecard_id):
    user, allowed, read_only = scorecard_user_permiso()

    if not allowed:
        return jsonify({
            "ok": False,
            "error": "No tiene permiso para consultar el estado del Scorecard."
        }), 403

    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, estado, progress_pct, current_stage, current_tool,
               score_total, score_dns, score_ip, score_kali,
               score_incidentes, score_darkweb, nivel_riesgo, error_detalle
        FROM scorecard_runs
        WHERE id = ?
    """, (scorecard_id,))

    row = cur.fetchone()
    conn.close()

    if not row:
        return jsonify({
            "ok": False,
            "error": "Scorecard no encontrado."
        }), 404

    estado = row["estado"] or "pendiente"
    progress_pct = int(row["progress_pct"] or 0)

    return jsonify({
        "ok": True,
        "id": row["id"],
        "estado": estado,
        "progress_pct": progress_pct,
        "current_stage": row["current_stage"] or "—",
        "current_tool": row["current_tool"] or "—",
        "score_total": round(float(row["score_total"] or 0), 1),
        "score_dns": round(float(row["score_dns"] or 0), 1),
        "score_ip": round(float(row["score_ip"] or 0), 1),
        "score_kali": round(float(row["score_kali"] or 0), 1),
        "score_incidentes": round(float(row["score_incidentes"] or 100), 1),
        "score_darkweb": round(float(row["score_darkweb"] or 100), 1),
        "nivel_riesgo": row["nivel_riesgo"] or "Pendiente",
        "error_detalle": row["error_detalle"] or ""
    })


# ============================================================
# DETALLE SCORECARD - CON BARRA DE PROGRESO AUTOREFRESH
# REEMPLAZA COMPLETA TU FUNCIÓN proveedores_scorecard_detalle()
# ============================================================

@app.route("/proveedores/scorecard/<int:scorecard_id>")
@login_required
def proveedores_scorecard_detalle(scorecard_id):
    user, allowed, read_only = scorecard_user_permiso()

    if not allowed:
        flash("No tiene permiso para acceder al Scorecard de Proveedores.", "danger")
        return redirect(url_for("menu"))

    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM scorecard_runs WHERE id = ?", (scorecard_id,))
    run = cur.fetchone()

    if not run:
        conn.close()
        abort(404)

    cur.execute("""
        SELECT *
        FROM scorecard_findings
        WHERE run_id = ?
          AND categoria <> 'Kali Linux Scan'
        ORDER BY
          CASE categoria
            WHEN 'Hacker Chatter / Exposure Intelligence' THEN 1
            WHEN 'Incident History' THEN 2
            WHEN 'DNS Health' THEN 3
            WHEN 'IP Reputation' THEN 4
            ELSE 5
          END,
          id ASC
    """, (scorecard_id,))
    findings = cur.fetchall()

    cur.execute("""
        SELECT *
        FROM scorecard_incidents
        WHERE run_id = ?
        ORDER BY
          CASE severidad
            WHEN 'Crítico' THEN 1
            WHEN 'Alto' THEN 2
            WHEN 'Medio' THEN 3
            WHEN 'Bajo' THEN 4
            ELSE 5
          END,
          id ASC
    """, (scorecard_id,))
    incidentes = cur.fetchall()

    cur.execute("""
        SELECT *
        FROM scorecard_darkweb_exposures
        WHERE run_id = ?
        ORDER BY
          CASE severidad
            WHEN 'Crítico' THEN 1
            WHEN 'Alto' THEN 2
            WHEN 'Medio' THEN 3
            WHEN 'Bajo' THEN 4
            ELSE 5
          END,
          id ASC
    """, (scorecard_id,))
    hacker_chatter = cur.fetchall()

    cur.execute("""
        SELECT COUNT(*) total
        FROM scorecard_findings
        WHERE run_id = ?
          AND categoria = 'Kali Linux Scan'
    """, (scorecard_id,))
    total_kali = cur.fetchone()["total"] or 0

    conn.close()

    body = """
    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .score-shell{
        width:96%;
        max-width:1650px;
        margin:26px auto 24px auto;
      }

      .score-header-card{
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

      .score-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .score-header-card::after{
        content:"📈";
        order:-1;
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
        position:relative;
        z-index:1;
      }

      .score-header-text{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
        color:#ffffff !important;
        font-size:1.32rem;
        font-weight:950;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
        position:relative;
        z-index:1;
      }

      .score-header-text::before{
        content:"SGSI · Scorecard Hacker Chatter";
        display:block;
        width:max-content;
        max-width:100%;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
        text-shadow:none;
      }

      .score-card,
      .card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
        padding:20px;
      }

      .score-main{
        font-size:3rem;
        font-weight:950;
        color:#0b4a8f;
        line-height:1;
      }

      .score-table-scroll{
        max-height:520px;
        overflow:auto;
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
        font-weight:900 !important;
        border:none !important;
        white-space:nowrap;
        vertical-align:middle !important;
        text-align:center;
        padding:9px 8px;
      }

      .table tbody td,
      .table td{
        vertical-align:middle !important;
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

      .incident-title,
      .chatter-text{
        min-width:360px;
        white-space:normal;
        word-break:break-word;
        overflow-wrap:anywhere;
        line-height:1.45;
      }

      .score-progress-box{
        background:rgba(59,130,246,.08);
        border:1px solid rgba(59,130,246,.12);
        border-radius:14px;
        padding:12px 14px;
        margin:10px 0 12px 0;
      }

      .score-progress-head{
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:12px;
        margin-bottom:8px;
      }

      .score-progress-title{
        font-weight:950;
        color:#0b4a8f;
      }

      .score-live-dot{
        display:inline-block;
        width:9px;
        height:9px;
        border-radius:999px;
        background:#ffc107;
        margin-right:6px;
        box-shadow:0 0 0 rgba(255,193,7,.8);
        animation:scorePulse 1.4s infinite;
      }

      @keyframes scorePulse{
        0%{box-shadow:0 0 0 0 rgba(255,193,7,.8);}
        70%{box-shadow:0 0 0 9px rgba(255,193,7,0);}
        100%{box-shadow:0 0 0 0 rgba(255,193,7,0);}
      }

      .progress{
        background:rgba(0,0,0,.08);
        box-shadow:inset 0 2px 6px rgba(0,0,0,.16);
        height:22px;
        border-radius:999px;
        overflow:hidden;
      }

      .progress-bar{
        font-size:.78rem;
        font-weight:900;
        letter-spacing:.4px;
        transition:width .55s ease;
      }

      .score-autorefresh-note{
        font-size:.82rem;
        color:#607086;
        font-weight:800;
        margin-top:7px;
      }

      .score-error-box{
        display:none;
        border-radius:12px;
        padding:10px 12px;
        background:rgba(220,53,69,.08);
        border:1px solid rgba(220,53,69,.18);
        color:#842029;
        font-weight:800;
        margin-top:10px;
        white-space:pre-wrap;
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

      @media (max-width:992px){
        .score-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .score-header-card{
          min-height:88px;
        }

        .score-header-text{
          font-size:1.20rem;
        }

        .score-card,
        .card{
          padding:16px;
        }

        .score-main{
          font-size:2.35rem;
        }
      }

      @media (max-width:768px){
        .score-header-card{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .score-header-card::after{
          margin:0;
        }

        .score-header-text,
        .score-header-text::before{
          text-align:center;
          margin-left:auto;
          margin-right:auto;
        }

        .score-progress-head{
          flex-direction:column;
          align-items:flex-start;
        }
      }
    </style>

    <div class="score-shell">
      <div class="score-header-card">
        <h1 class="score-header-text">Detalle Scorecard de Proveedor</h1>
      </div>

      <div class="d-flex justify-content-between mb-3">
        <a href="{{ url_for('proveedores_scorecard_dashboard') }}" class="btn btn-outline-secondary rounded-pill px-4">Volver</a>

        <div class="d-flex gap-2 flex-wrap">
          <a href="{{ url_for('proveedores_scorecard_rating', scorecard_id=run.id) }}"
             class="btn btn-success rounded-pill px-4">
            📊 SecurityScorecard Proveedores
          </a>

          {% if read_only %}
            <button class="btn btn-warning rounded-pill px-4" disabled title="El rol Auditor no tiene acceso al detalle Kali Linux">
              🧪 Ver Detalle Kali Linux
              {% if total_kali %}
                <span class="badge bg-dark ms-1">{{ total_kali }}</span>
              {% endif %}
            </button>
          {% else %}
            <a href="{{ url_for('proveedores_scorecard_kali_detalle', scorecard_id=run.id) }}"
               class="btn btn-warning rounded-pill px-4">
              🧪 Ver Detalle Kali Linux
              {% if total_kali %}
                <span class="badge bg-dark ms-1">{{ total_kali }}</span>
              {% endif %}
            </a>
          {% endif %}

          <a href="{{ url_for('proveedores_scorecard_detalle', scorecard_id=run.id) }}"
             class="btn btn-primary rounded-pill px-4">
            🔄 Actualizar
          </a>
        </div>
      </div>

      <div class="score-card mb-3">
        <div class="row align-items-center">
          <div class="col-md-4 text-center">
            <div class="score-main" id="score-total-main">{{ "%.1f"|format(run.score_total or 0) }}%</div>
            <span id="score-risk-badge" class="badge bg-{{ scorecard_badge_color(run.nivel_riesgo) }} fs-6">
              Riesgo {{ run.nivel_riesgo or 'Pendiente' }}
            </span>
          </div>

          <div class="col-md-8">
            <h4 class="fw-bold">{{ run.proveedor_nombre or 'Proveedor no asociado' }}</h4>

            <p class="mb-1"><strong>Dominio:</strong> {{ run.dominio }}</p>
            <p class="mb-1"><strong>IP:</strong> {{ run.ip_resuelta or '—' }}</p>

            <div class="score-progress-box">
              <div class="score-progress-head">
                <div class="score-progress-title">
                  <span id="score-live-dot" class="score-live-dot"
                    style="{% if run.estado in ['finalizado', 'error'] %}display:none;{% endif %}">
                  </span>
                  Estado:
                  <span id="score-estado-badge"
                        class="badge bg-{% if run.estado == 'finalizado' %}success{% elif run.estado == 'error' %}danger{% else %}warning text-dark{% endif %}">
                    {{ run.estado|capitalize }}
                  </span>
                </div>

                <div class="fw-bold text-primary">
                  Progreso: <span id="score-progress-text">{{ run.progress_pct or 0 }}</span>%
                </div>
              </div>

              <div class="progress">
                <div id="score-progress-bar"
                  class="progress-bar progress-bar-striped
                  {% if run.estado == 'finalizado' %}bg-success
                  {% elif run.estado == 'error' %}bg-danger
                  {% else %}bg-warning text-dark progress-bar-animated{% endif %}"
                  role="progressbar"
                  style="width: {{ run.progress_pct or 0 }}%;"
                  aria-valuenow="{{ run.progress_pct or 0 }}"
                  aria-valuemin="0"
                  aria-valuemax="100">
                  {{ run.progress_pct or 0 }}%
                </div>
              </div>

              <div id="score-autorefresh-note" class="score-autorefresh-note">
                {% if run.estado in ['finalizado', 'error'] %}
                  Actualización automática detenida porque el proceso está {{ run.estado }}.
                {% else %}
                  La barra se actualiza automáticamente cada 3 segundos.
                {% endif %}
              </div>

              <div id="score-error-box" class="score-error-box"></div>
            </div>

            <p class="mb-1"><strong>Etapa:</strong> <span id="score-current-stage">{{ run.current_stage or '—' }}</span></p>
            <p class="mb-1"><strong>Herramienta actual:</strong> <span id="score-current-tool">{{ run.current_tool or '—' }}</span></p>
            <p class="mb-0"><strong>Fecha:</strong> {{ run.fecha_ejecucion }}</p>
          </div>
        </div>
      </div>

      <div class="score-card mb-3">
        <h5 class="fw-bold mb-3">🕵️ Hacker Chatter / Inteligencia de Exposición</h5>

        <div class="alert alert-info">
          Esta sección consolida señales públicas y fuentes enterprise configuradas:
          credenciales, brechas, CVEs, menciones públicas, exposición en repositorios y superficie pública.
        </div>

        <div class="table-responsive score-table-scroll">
          <table class="table table-hover align-middle">
            <thead>
              <tr>
                <th>Fuente</th>
                <th>Tipo</th>
                <th>Indicador</th>
                <th>Severidad</th>
                <th>Fecha</th>
                <th>Evidencia</th>
                <th>Recomendación</th>
                <th>URL</th>
              </tr>
            </thead>
            <tbody>
              {% for h in hacker_chatter %}
              <tr>
                <td>{{ h.fuente or '—' }}</td>
                <td>{{ h.tipo_exposicion or '—' }}</td>
                <td class="chatter-text">{{ h.indicador or '—' }}</td>
                <td>
                  <span class="badge bg-{{ scorecard_badge_color(h.severidad) }}">
                    {{ h.severidad or '—' }}
                  </span>
                </td>
                <td>{{ h.fecha or '—' }}</td>
                <td class="chatter-text">{{ h.evidencia or '—' }}</td>
                <td class="chatter-text">{{ h.recomendacion or '—' }}</td>
                <td>
                  {% if h.url %}
                    <a href="{{ h.url }}" target="_blank" class="btn btn-sm btn-outline-primary rounded-pill">Abrir</a>
                  {% else %}
                    —
                  {% endif %}
                </td>
              </tr>
              {% else %}
              <tr>
                <td colspan="8" class="text-center text-muted py-4">
                  No se identificaron señales públicas relevantes de exposición.
                </td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>

      <div class="score-card mb-3">
        <h5 class="fw-bold mb-3">🚨 Brechas o incidentes públicos identificados</h5>
        <div class="table-responsive score-table-scroll">
          <table class="table table-hover align-middle">
            <thead>
              <tr>
                <th>Fuente</th>
                <th>Título / Evento</th>
                <th>Fecha</th>
                <th>Severidad</th>
                <th>Descripción</th>
                <th>URL</th>
              </tr>
            </thead>
            <tbody>
              {% for i in incidentes %}
              <tr>
                <td>{{ i.fuente or '—' }}</td>
                <td class="incident-title">{{ i.titulo or '—' }}</td>
                <td>{{ i.fecha_incidente or '—' }}</td>
                <td>
                  <span class="badge bg-{{ scorecard_badge_color(i.severidad) }}">
                    {{ i.severidad or '—' }}
                  </span>
                </td>
                <td>{{ i.descripcion or '—' }}</td>
                <td>
                  {% if i.url %}
                    <a href="{{ i.url }}" target="_blank" class="btn btn-sm btn-outline-primary rounded-pill">Abrir</a>
                  {% else %}
                    —
                  {% endif %}
                </td>
              </tr>
              {% else %}
              <tr>
                <td colspan="6" class="text-center text-muted py-4">
                  No se identificaron brechas o incidentes públicos asociados al proveedor.
                </td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>

      <div class="score-card mb-3">
        <h5 class="fw-bold mb-3">Hallazgos consolidados del Scorecard</h5>
        <div class="table-responsive score-table-scroll">
          <table class="table table-hover align-middle">
            <thead>
              <tr>
                <th>Categoría</th>
                <th>Herramienta</th>
                <th>Control</th>
                <th>Estado</th>
                <th>Riesgo</th>
                <th>Score</th>
                <th>Evidencia</th>
                <th>Recomendación</th>
              </tr>
            </thead>
            <tbody>
              {% for f in findings %}
              <tr>
                <td>{{ f.categoria }}</td>
                <td>{{ f.herramienta or '—' }}</td>
                <td>{{ f.control }}</td>
                <td>{{ f.estado }}</td>
                <td>
                  <span class="badge bg-{{ scorecard_badge_color(f.riesgo) }}">
                    {{ f.riesgo }}
                  </span>
                </td>
                <td>{{ "%.1f"|format(f.score or 0) }}%</td>
                <td class="chatter-text">{{ f.evidencia }}</td>
                <td class="chatter-text">{{ f.recomendacion }}</td>
              </tr>
              {% else %}
              <tr>
                <td colspan="8" class="text-center text-muted">Sin hallazgos registrados.</td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <script>
      (function(){
        const estadoUrl = "{{ url_for('proveedores_scorecard_estado', scorecard_id=run.id) }}";
        const detalleUrl = "{{ url_for('proveedores_scorecard_detalle', scorecard_id=run.id) }}";

        const progressBar = document.getElementById("score-progress-bar");
        const progressText = document.getElementById("score-progress-text");
        const estadoBadge = document.getElementById("score-estado-badge");
        const currentStage = document.getElementById("score-current-stage");
        const currentTool = document.getElementById("score-current-tool");
        const totalMain = document.getElementById("score-total-main");
        const riskBadge = document.getElementById("score-risk-badge");
        const liveDot = document.getElementById("score-live-dot");
        const note = document.getElementById("score-autorefresh-note");
        const errorBox = document.getElementById("score-error-box");

        let finishedAlready = ["finalizado", "error"].includes("{{ run.estado }}");
        let intervalId = null;
        let reloadScheduled = false;

        function setBadgeEstado(estado){
          estadoBadge.className = "badge";

          if(estado === "finalizado"){
            estadoBadge.classList.add("bg-success");
            estadoBadge.textContent = "Finalizado";
          }else if(estado === "error"){
            estadoBadge.classList.add("bg-danger");
            estadoBadge.textContent = "Error";
          }else{
            estadoBadge.classList.add("bg-warning", "text-dark");
            estadoBadge.textContent = estado.charAt(0).toUpperCase() + estado.slice(1);
          }
        }

        function setProgressBar(estado, pct){
          pct = Math.max(0, Math.min(100, parseInt(pct || 0)));

          progressText.textContent = pct;
          progressBar.style.width = pct + "%";
          progressBar.setAttribute("aria-valuenow", pct);
          progressBar.textContent = pct + "%";

          progressBar.className = "progress-bar progress-bar-striped";

          if(estado === "finalizado"){
            progressBar.classList.add("bg-success");
          }else if(estado === "error"){
            progressBar.classList.add("bg-danger");
          }else{
            progressBar.classList.add("bg-warning", "text-dark", "progress-bar-animated");
          }
        }

        function setRiskBadge(nivel){
          riskBadge.textContent = "Riesgo " + (nivel || "Pendiente");
        }

        async function refreshScorecardEstado(){
          try{
            const response = await fetch(estadoUrl, {
              method: "GET",
              headers: {
                "Accept": "application/json",
                "X-Requested-With": "XMLHttpRequest"
              },
              cache: "no-store"
            });

            if(!response.ok){
              return;
            }

            const data = await response.json();

            if(!data.ok){
              return;
            }

            const estado = data.estado || "pendiente";

            setBadgeEstado(estado);
            setProgressBar(estado, data.progress_pct);

            currentStage.textContent = data.current_stage || "—";
            currentTool.textContent = data.current_tool || "—";

            totalMain.textContent = Number(data.score_total || 0).toFixed(1) + "%";
            setRiskBadge(data.nivel_riesgo);

            if(estado === "error"){
              if(liveDot){ liveDot.style.display = "none"; }
              note.textContent = "Actualización automática detenida porque el proceso terminó con error.";
              if(data.error_detalle){
                errorBox.style.display = "block";
                errorBox.textContent = data.error_detalle.substring(0, 1200);
              }
              if(intervalId){ clearInterval(intervalId); }
            }

            if(estado === "finalizado"){
              if(liveDot){ liveDot.style.display = "none"; }
              note.textContent = "Proceso finalizado. Actualizando tablas de hallazgos automáticamente...";

              if(intervalId){ clearInterval(intervalId); }

              if(!reloadScheduled && !finishedAlready){
                reloadScheduled = true;
                setTimeout(function(){
                  window.location.href = detalleUrl;
                }, 1600);
              }
            }

          }catch(e){
            console.warn("No se pudo refrescar el estado del Scorecard:", e);
          }
        }

        if(!finishedAlready){
          refreshScorecardEstado();
          intervalId = setInterval(refreshScorecardEstado, 3000);
        }
      })();
    </script>
    """

    return render_template_string(
        BASE,
        content=Markup(render_template_string(
            body,
            run=run,
            findings=findings,
            incidentes=incidentes,
            hacker_chatter=hacker_chatter,
            total_kali=total_kali,
            read_only=read_only,
            scorecard_badge_color=scorecard_badge_color
        ))
    )



def scorecard_rating_letra(score):
    score = float(score or 0)

    if score >= 90:
        return "A", "Excelente"
    if score >= 80:
        return "B", "Bueno"
    if score >= 70:
        return "C", "Aceptable"
    if score >= 60:
        return "D", "Débil"
    return "F", "Crítico"


def scorecard_rating_color(score):
    score = float(score or 0)

    if score >= 85:
        return "#176b2c"
    if score >= 70:
        return "#c48a00"
    if score >= 50:
        return "#c2410c"
    return "#991b1b"


def scorecard_parse_fecha(fecha):
    try:
        if not fecha:
            return None

        fecha = str(fecha).strip()

        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"):
            try:
                return datetime.strptime(fecha[:19], fmt)
            except Exception:
                pass

        return None
    except Exception:
        return None


def scorecard_get_trend_data(run):
    dominio = limpiar_dominio_scorecard(run["dominio"])
    dominio_base = obtener_dominio_base(dominio)
    proveedor_id = run["proveedor_id"]

    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    if proveedor_id:
        cur.execute("""
            SELECT id, score_total, score_dns, score_ip, score_kali, score_incidentes, score_darkweb,
                   nivel_riesgo, fecha_ejecucion, estado
            FROM scorecard_runs
            WHERE proveedor_id = ?
              AND estado IN ('finalizado', 'error')
            ORDER BY id ASC
        """, (proveedor_id,))
    else:
        cur.execute("""
            SELECT id, score_total, score_dns, score_ip, score_kali, score_incidentes, score_darkweb,
                   nivel_riesgo, fecha_ejecucion, estado
            FROM scorecard_runs
            WHERE lower(dominio) LIKE ?
              AND estado IN ('finalizado', 'error')
            ORDER BY id ASC
        """, (f"%{dominio_base.lower()}%",))

    rows = cur.fetchall()
    conn.close()

    hoy = datetime.now()
    limite = hoy - timedelta(days=30)

    puntos = []

    for r in rows:
        dt = scorecard_parse_fecha(r["fecha_ejecucion"])

        if not dt:
            continue

        if dt < limite:
            continue

        puntos.append({
            "id": r["id"],
            "fecha": dt.strftime("%d/%m"),
            "fecha_full": dt.strftime("%Y-%m-%d %H:%M"),
            "score_total": round(float(r["score_total"] or 0), 1),
            "score_dns": round(float(r["score_dns"] or 0), 1),
            "score_ip": round(float(r["score_ip"] or 0), 1),
            "score_kali": round(float(r["score_kali"] or 0), 1),
            "score_incidentes": round(float(r["score_incidentes"] or 100), 1),
            "score_darkweb": round(float(r["score_darkweb"] or 100), 1),
            "nivel_riesgo": r["nivel_riesgo"] or "Pendiente"
        })

    if len(puntos) < 2:
        puntos = []

        for r in rows[-12:]:
            dt = scorecard_parse_fecha(r["fecha_ejecucion"])

            if not dt:
                continue

            puntos.append({
                "id": r["id"],
                "fecha": dt.strftime("%d/%m"),
                "fecha_full": dt.strftime("%Y-%m-%d %H:%M"),
                "score_total": round(float(r["score_total"] or 0), 1),
                "score_dns": round(float(r["score_dns"] or 0), 1),
                "score_ip": round(float(r["score_ip"] or 0), 1),
                "score_kali": round(float(r["score_kali"] or 0), 1),
                "score_incidentes": round(float(r["score_incidentes"] or 100), 1),
                "score_darkweb": round(float(r["score_darkweb"] or 100), 1),
                "nivel_riesgo": r["nivel_riesgo"] or "Pendiente"
            })

    return puntos


def scorecard_get_risk_counts(run_id):
    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COALESCE(severidad, riesgo, 'Bajo') AS sev, COUNT(*) AS total
        FROM scorecard_findings
        WHERE run_id = ?
        GROUP BY COALESCE(severidad, riesgo, 'Bajo')
    """, (run_id,))
    findings = cur.fetchall()

    cur.execute("""
        SELECT COALESCE(severidad, 'Bajo') AS sev, COUNT(*) AS total
        FROM scorecard_darkweb_exposures
        WHERE run_id = ?
        GROUP BY COALESCE(severidad, 'Bajo')
    """, (run_id,))
    exposures = cur.fetchall()

    cur.execute("""
        SELECT COALESCE(severidad, 'Bajo') AS sev, COUNT(*) AS total
        FROM scorecard_incidents
        WHERE run_id = ?
        GROUP BY COALESCE(severidad, 'Bajo')
    """, (run_id,))
    incidents = cur.fetchall()

    conn.close()

    counts = {
        "Crítico": 0,
        "Alto": 0,
        "Medio": 0,
        "Bajo": 0
    }

    def normalizar(sev):
        sev = (sev or "Bajo").strip()
        if sev in ["Critico", "Crítico", "critical", "Critical"]:
            return "Crítico"
        if sev in ["Alto", "high", "High"]:
            return "Alto"
        if sev in ["Medio", "medium", "Medium", "Moderado"]:
            return "Medio"
        return "Bajo"

    for grupo in [findings, exposures, incidents]:
        for row in grupo:
            counts[normalizar(row["sev"])] += int(row["total"] or 0)

    total = sum(counts.values())

    return counts, total


def scorecard_get_recent_findings(run_id, limit=5):
    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT categoria, herramienta, control, estado, riesgo, severidad, score, evidencia, recomendacion, fecha
        FROM scorecard_findings
        WHERE run_id = ?
        ORDER BY
          CASE COALESCE(severidad, riesgo)
            WHEN 'Crítico' THEN 1
            WHEN 'Critico' THEN 1
            WHEN 'Alto' THEN 2
            WHEN 'Medio' THEN 3
            WHEN 'Bajo' THEN 4
            ELSE 5
          END,
          id DESC
        LIMIT ?
    """, (run_id, limit))

    rows = cur.fetchall()
    conn.close()

    return rows


def scorecard_get_peer_comparison(run):
    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT AVG(score_total) AS promedio
        FROM scorecard_runs
        WHERE estado = 'finalizado'
          AND score_total > 0
    """)
    promedio = cur.fetchone()["promedio"] or 0

    cur.execute("""
        SELECT MAX(score_total) AS mejor
        FROM scorecard_runs
        WHERE estado = 'finalizado'
          AND score_total > 0
    """)
    mejor = cur.fetchone()["mejor"] or 0

    conn.close()

    return {
        "actual": round(float(run["score_total"] or 0), 1),
        "promedio": round(float(promedio or 0), 1),
        "mejor": round(float(mejor or 0), 1)
    }



def scorecard_get_monthly_comparison(run):
    dominio = limpiar_dominio_scorecard(run["dominio"])
    dominio_base = obtener_dominio_base(dominio)
    proveedor_id = run["proveedor_id"]

    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    if proveedor_id:
        cur.execute("""
            SELECT fecha_ejecucion, score_total
            FROM scorecard_runs
            WHERE proveedor_id = ?
              AND estado = 'finalizado'
              AND score_total > 0
            ORDER BY fecha_ejecucion ASC
        """, (proveedor_id,))
    else:
        cur.execute("""
            SELECT fecha_ejecucion, score_total
            FROM scorecard_runs
            WHERE lower(dominio) LIKE ?
              AND estado = 'finalizado'
              AND score_total > 0
            ORDER BY fecha_ejecucion ASC
        """, (f"%{dominio_base.lower()}%",))

    rows = cur.fetchall()
    conn.close()

    meses = {}

    for r in rows:
        dt = scorecard_parse_fecha(r["fecha_ejecucion"])
        if not dt:
            continue

        key = dt.strftime("%Y-%m")
        label = dt.strftime("%m/%Y")

        if key not in meses:
            meses[key] = {
                "label": label,
                "scores": []
            }

        meses[key]["scores"].append(float(r["score_total"] or 0))

    data = []

    for key in sorted(meses.keys())[-12:]:
        values = meses[key]["scores"]
        avg = sum(values) / len(values) if values else 0
        data.append({
            "label": meses[key]["label"],
            "score": round(avg, 1)
        })

    return data


def scorecard_issue_summary(scorecard_id):
    """
    Resumen real para la vista SecurityScorecard GRAC.

    - Riesgos críticos: hallazgos con severidad Crítico/Critico
    - Riesgos altos: hallazgos con severidad Alto
    - Vulnerabilidades: hallazgos de Kali Linux con severidad Alto/Crítico
    - Servicios expuestos: hallazgos de Shodan o tipo_exposicion relacionado con servicios/puertos/CVEs
    """

    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    # Riesgos críticos en hallazgos consolidados
    cur.execute("""
        SELECT COUNT(*) AS total
        FROM scorecard_findings
        WHERE run_id = ?
          AND COALESCE(severidad, riesgo, '') IN ('Crítico', 'Critico')
    """, (scorecard_id,))
    criticos = cur.fetchone()["total"] or 0

    # Riesgos altos en hallazgos consolidados
    cur.execute("""
        SELECT COUNT(*) AS total
        FROM scorecard_findings
        WHERE run_id = ?
          AND COALESCE(severidad, riesgo, '') = 'Alto'
    """, (scorecard_id,))
    altos = cur.fetchone()["total"] or 0

    # Vulnerabilidades reales desde Kali Linux
    cur.execute("""
        SELECT COUNT(*) AS total
        FROM scorecard_findings
        WHERE run_id = ?
          AND categoria = 'Kali Linux Scan'
          AND COALESCE(severidad, riesgo, '') IN ('Crítico', 'Critico', 'Alto', 'Medio')
    """, (scorecard_id,))
    vulnerabilidades = cur.fetchone()["total"] or 0

    # Servicios expuestos desde Shodan / Exposure
    cur.execute("""
        SELECT COUNT(*) AS total
        FROM scorecard_darkweb_exposures
        WHERE run_id = ?
          AND (
                LOWER(COALESCE(fuente, '')) LIKE '%shodan%'
             OR LOWER(COALESCE(tipo_exposicion, '')) LIKE '%servicio%'
             OR LOWER(COALESCE(tipo_exposicion, '')) LIKE '%puerto%'
             OR LOWER(COALESCE(tipo_exposicion, '')) LIKE '%cve%'
             OR LOWER(COALESCE(indicador, '')) LIKE '%puerto%'
             OR LOWER(COALESCE(evidencia, '')) LIKE '%puerto%'
          )
    """, (scorecard_id,))
    servicios_expuestos = cur.fetchone()["total"] or 0

    conn.close()

    return {
        "criticos": int(criticos),
        "altos": int(altos),
        "vulnerabilidades": int(vulnerabilidades),
        "servicios_expuestos": int(servicios_expuestos)
    }


@app.route("/proveedores/scorecard/<int:scorecard_id>/rating")
@login_required
def proveedores_scorecard_rating(scorecard_id):
    user, allowed, read_only = scorecard_user_permiso()

    if not allowed:
        flash("No tiene permiso para acceder al Scorecard de Proveedores.", "danger")
        return redirect(url_for("menu"))

    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM scorecard_runs WHERE id = ?", (scorecard_id,))
    run = cur.fetchone()
    conn.close()

    if not run:
        abort(404)

    score_total = round(float(run["score_total"] or 0), 1)
    letra, texto_rating = scorecard_rating_letra(score_total)
    color_rating = scorecard_rating_color(score_total)

    trend = scorecard_get_trend_data(run)
    monthly = scorecard_get_monthly_comparison(run)

    counts, total_riesgos = scorecard_get_risk_counts(scorecard_id)
    summary = scorecard_issue_summary(scorecard_id)

    recent_findings = scorecard_get_recent_findings(scorecard_id, limit=4)
    peer = scorecard_get_peer_comparison(run)

    risk_factor_scores = [
        {"label": "Salud DNS", "score": round(float(run["score_dns"] or 0), 1), "canvas": "gaugeDns"},
        {"label": "Reputación IP", "score": round(float(run["score_ip"] or 0), 1), "canvas": "gaugeIp"},
        {"label": "Kali Linux", "score": round(float(run["score_kali"] or 0), 1), "canvas": "gaugeKali"},
        {"label": "Incidentes / Brechas", "score": round(float(run["score_incidentes"] or 100), 1), "canvas": "gaugeIncidentes"},
        {"label": "Exposición / Hacker Chatter", "score": round(float(run["score_darkweb"] or 100), 1), "canvas": "gaugeDarkweb"},
    ]

    trend_labels = [x["fecha"] for x in trend]
    trend_scores = [x["score_total"] for x in trend]

    monthly_labels = [x["label"] for x in monthly]
    monthly_scores = [x["score"] for x in monthly]

    risk_labels = ["Crítico", "Alto", "Medio", "Bajo"]
    risk_values = [
        counts.get("Crítico", 0),
        counts.get("Alto", 0),
        counts.get("Medio", 0),
        counts.get("Bajo", 0)
    ]

    peer_labels = ["Proveedor", "Promedio", "Mejor"]
    peer_values = [peer["actual"], peer["promedio"], peer["mejor"]]

    gauge_labels = [x["label"] for x in risk_factor_scores]
    gauge_scores = [x["score"] for x in risk_factor_scores]
    gauge_canvas_ids = [x["canvas"] for x in risk_factor_scores]

    body = """
    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .rating-shell{
        width:96%;
        max-width:1480px;
        margin:26px auto 24px auto;
      }

      .score-header-card{
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

      .score-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .score-header-card::after{
        content:"📊";
        order:-1;
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
        position:relative;
        z-index:1;
      }

      .score-header-text{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
        color:#ffffff !important;
        font-size:1.32rem;
        font-weight:950;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
        position:relative;
        z-index:1;
      }

      .score-header-text::before{
        content:"SGSI · Rating Scorecard";
        display:block;
        width:max-content;
        max-width:100%;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
        text-shadow:none;
      }

      .action-bar{
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:10px;
        margin:10px 0 14px;
        flex-wrap:wrap;
      }

      .btn{
        border-radius:10px !important;
        font-weight:900;
        padding:.48rem 1.05rem;
        font-size:.86rem;
        box-shadow:0 4px 10px rgba(0,0,0,.08);
      }

      .ssc-frame{
        background:rgba(245,248,252,.96);
        border:1px solid rgba(219,230,244,.9);
        border-radius:18px;
        padding:12px;
        box-shadow:0 12px 24px rgba(15,23,42,.18);
      }

      .ssc-card{
        background:rgba(255,255,255,.985);
        border:1px solid #dbe6f4;
        border-radius:14px;
        box-shadow:0 6px 14px rgba(15,23,42,.075);
        padding:10px 12px;
        height:100%;
        overflow:hidden;
      }

      .ssc-top{
        display:grid;
        grid-template-columns:.95fr .50fr 1.25fr;
        gap:7px;
        align-items:stretch;
      }

      .company-title{
        font-size:1.05rem;
        font-weight:950;
        color:#172033;
        margin-bottom:6px;
        line-height:1.1;
      }

      .company-meta{
        font-size:.68rem;
        font-weight:800;
        color:#334155;
        margin-bottom:2px;
        line-height:1.22;
      }

      .rating-circle{
        width:108px;
        height:108px;
        border-radius:50%;
        margin:0 auto;
        background:{{ color_rating }};
        color:#fff;
        display:flex;
        flex-direction:column;
        align-items:center;
        justify-content:center;
        box-shadow:0 12px 22px rgba(15,23,42,.22);
        border:4px solid rgba(255,255,255,.55);
      }

      .rating-letter{
        font-size:2.75rem;
        line-height:.82;
        font-weight:950;
      }

      .rating-score{
        font-size:1.26rem;
        font-weight:950;
        margin-top:5px;
      }

      .rating-label{
        margin-top:6px;
        padding:3px 8px;
        border-radius:999px;
        background:#eef5ff;
        border:1px solid #d8e9ff;
        color:#0b4a8f;
        font-size:.64rem;
        font-weight:950;
        text-align:center;
        line-height:1.1;
      }

      .section-title{
        font-size:.80rem;
        font-weight:950;
        color:#0b4a8f;
        margin-bottom:5px;
        line-height:1.1;
      }

      .chart-box{
        height:118px;
        position:relative;
      }

      .chart-box-small{
        height:132px;
        position:relative;
      }

      .empty-note{
        border-radius:9px;
        background:#fff7ed;
        border:1px solid #fed7aa;
        color:#9a3412;
        padding:5px 7px;
        font-weight:800;
        font-size:.66rem;
        margin-top:5px;
        line-height:1.15;
      }

      .issue-card{
        margin-top:9px;
        padding:8px 10px;
      }

      .issue-row{
        display:grid;
        grid-template-columns:repeat(4,1fr);
        gap:7px;
      }

      .issue-pill{
        border:1px solid #dbe6f4;
        border-radius:10px;
        padding:6px 8px;
        background:#fff;
        display:flex;
        align-items:center;
        gap:6px;
        font-weight:900;
        color:#1e293b;
        font-size:.70rem;
        min-height:34px;
      }

      .issue-dot{
        width:20px;
        height:20px;
        border-radius:7px;
        color:#fff;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:.62rem;
        font-weight:950;
        flex:0 0 auto;
      }

      .dot-critical{background:#991b1b;}
      .dot-high{background:#c2410c;}
      .dot-medium{background:#d97706;}
      .dot-low{background:#0b4a8f;}

      .main-grid{
        display:grid;
        grid-template-columns:.98fr 1.02fr;
        gap:7px;
        margin-top:9px;
      }

      .left-stack,
      .right-stack{
        display:grid;
        gap:7px;
      }

      .right-stack{
        grid-template-columns:1fr 1fr;
      }

      .right-stack .full{
        grid-column:1 / -1;
      }

      .gauge-grid{
        display:grid;
        grid-template-columns:repeat(5,1fr);
        gap:6px;
      }

      .gauge-card{
        border:1px solid rgba(190,210,235,.95);
        border-radius:14px;
        background:
          radial-gradient(circle at 50% 20%,rgba(255,255,255,.98),rgba(241,247,255,.96) 58%,rgba(230,239,252,.95) 100%);
        padding:7px 7px 6px 7px;
        min-height:124px;
        display:flex;
        flex-direction:column;
        align-items:center;
        justify-content:flex-start;
        overflow:hidden;
        box-shadow:
          inset 0 1px 0 rgba(255,255,255,.95),
          0 7px 16px rgba(15,23,42,.10);
        position:relative;
      }

      .gauge-card::before{
        content:"";
        position:absolute;
        top:5px;
        left:8px;
        right:8px;
        height:24px;
        background:linear-gradient(180deg,rgba(255,255,255,.80),rgba(255,255,255,0));
        border-radius:999px;
        pointer-events:none;
      }

      .gauge-title{
        width:100%;
        text-align:center;
        font-size:.62rem;
        font-weight:950;
        color:#17365d;
        line-height:1.08;
        min-height:24px;
        margin-bottom:1px;
        display:flex;
        align-items:center;
        justify-content:center;
        position:relative;
        z-index:2;
      }

      .gauge-canvas-wrap{
        width:100%;
        height:76px;
        position:relative;
        z-index:2;
      }

      .gauge-score{
        margin-top:-5px;
        font-size:1rem;
        font-weight:950;
        color:#0f3769;
        line-height:1;
        position:relative;
        z-index:2;
      }

      .gauge-state{
        margin-top:3px;
        font-size:.56rem;
        font-weight:950;
        border-radius:999px;
        padding:2px 8px;
        line-height:1;
        position:relative;
        z-index:2;
        border:1px solid rgba(255,255,255,.8);
        box-shadow:0 3px 8px rgba(15,23,42,.10);
      }

      .gauge-state.bajo{
        background:#dcfce7;
        color:#166534;
      }

      .gauge-state.medio{
        background:#fef3c7;
        color:#92400e;
      }

      .gauge-state.alto{
        background:#ffedd5;
        color:#9a3412;
      }

      .gauge-state.critico{
        background:#fee2e2;
        color:#991b1b;
      }

      .finding-table{
        width:100%;
        border-collapse:separate;
        border-spacing:0;
      }

      .finding-table th{
        background:linear-gradient(135deg,#1d5fa9,#2f7fd1) !important;
        color:#ffffff !important;
        font-weight:950;
        padding:5px 6px;
        font-size:.66rem;
        line-height:1.1;
      }

      .finding-table td{
        border-bottom:1px solid #edf2f7;
        padding:5px 6px;
        font-size:.66rem;
        font-weight:700;
        vertical-align:middle;
        line-height:1.12;
      }

      .finding-table td:first-child{
        max-width:230px;
        white-space:nowrap;
        overflow:hidden;
        text-overflow:ellipsis;
      }

      .severity-badge{
        border-radius:999px;
        padding:3px 7px;
        color:#fff;
        font-size:.60rem;
        font-weight:950;
        display:inline-block;
        line-height:1;
      }

      .sev-critical{background:#991b1b;}
      .sev-high{background:#c2410c;}
      .sev-medium{background:#d97706;}
      .sev-low{background:#0b4a8f;}

      @media(max-width:1200px){
        .ssc-top,
        .main-grid,
        .right-stack{
          grid-template-columns:1fr;
        }

        .right-stack .full{
          grid-column:auto;
        }

        .chart-box,
        .chart-box-small{
          height:150px;
        }

        .gauge-grid{
          grid-template-columns:repeat(3,1fr);
        }
      }

      @media(max-width:720px){
        .score-header-card{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .score-header-card::after{
          margin:0;
        }

        .score-header-text,
        .score-header-text::before{
          text-align:center;
          margin-left:auto;
          margin-right:auto;
        }

        .issue-row{
          grid-template-columns:repeat(2,1fr);
        }

        .gauge-grid{
          grid-template-columns:repeat(2,1fr);
        }

        .score-header-text{
          font-size:1.20rem;
        }
      }
    </style>

    <div class="rating-shell">
      <div class="score-header-card">
        <h1 class="score-header-text">SecurityScorecard GRAC</h1>
      </div>

      <div class="action-bar">
        <a href="{{ url_for('proveedores_scorecard_detalle', scorecard_id=run.id) }}" class="btn btn-outline-secondary px-4">
          Volver al detalle
        </a>

        <a href="{{ url_for('proveedores_scorecard_dashboard') }}" class="btn btn-primary px-4">
          Dashboard Scorecard
        </a>
      </div>

      <div class="ssc-frame">
        <div class="ssc-top">
          <div class="ssc-card">
            <div class="company-title">{{ run.proveedor_nombre or 'Proveedor no asociado' }}</div>
            <div class="company-meta"><strong>Dominio:</strong> {{ run.dominio }}</div>
            <div class="company-meta"><strong>IP:</strong> {{ run.ip_resuelta or '—' }}</div>
            <div class="company-meta"><strong>Fecha evaluación:</strong> {{ run.fecha_ejecucion }}</div>
            <div class="company-meta"><strong>Estado:</strong> {{ run.estado }}</div>
          </div>

          <div class="ssc-card text-center">
            <div class="rating-circle">
              <div class="rating-letter">{{ letra }}</div>
              <div class="rating-score">{{ "%.1f"|format(score_total) }}</div>
            </div>
            <div class="rating-label">Calificación de seguridad · {{ texto_rating }}</div>
          </div>

          <div class="ssc-card">
            <div class="section-title">Tendencia del score — últimos 30 días</div>
            <div class="chart-box">
              <canvas id="trendChart"></canvas>
            </div>
            {% if trend|length < 2 %}
              <div class="empty-note">
                Ejecuta varios Scorecards del mismo proveedor para ver tendencia real.
              </div>
            {% endif %}
          </div>
        </div>

        <div class="ssc-card issue-card">
          <div class="section-title">Resumen de hallazgos</div>
          <div class="issue-row">
            <div class="issue-pill">
              <span class="issue-dot dot-critical">{{ summary.criticos }}</span>
              Riesgos críticos
            </div>
            <div class="issue-pill">
              <span class="issue-dot dot-high">{{ summary.altos }}</span>
              Riesgos altos
            </div>
            <div class="issue-pill">
              <span class="issue-dot dot-medium">{{ summary.vulnerabilidades }}</span>
              Vulnerabilidades
            </div>
            <div class="issue-pill">
              <span class="issue-dot dot-low">{{ summary.servicios_expuestos }}</span>
              Servicios expuestos
            </div>
          </div>
        </div>

        <div class="main-grid">
          <div class="left-stack">
            <div class="ssc-card">
              <div class="section-title">Factores de riesgo</div>

              <div class="gauge-grid">
                {% for f in risk_factor_scores %}
                <div class="gauge-card">
                  <div class="gauge-title">{{ f.label }}</div>
                  <div class="gauge-canvas-wrap">
                    <canvas id="{{ f.canvas }}"></canvas>
                  </div>
                  <div class="gauge-score">{{ "%.1f"|format(f.score) }}</div>
                  <div class="gauge-state
                    {% if f.score >= 85 %}bajo
                    {% elif f.score >= 70 %}medio
                    {% elif f.score >= 50 %}alto
                    {% else %}critico{% endif %}">
                    {% if f.score >= 85 %}
                      Bajo
                    {% elif f.score >= 70 %}
                      Medio
                    {% elif f.score >= 50 %}
                      Alto
                    {% else %}
                      Crítico
                    {% endif %}
                  </div>
                </div>
                {% endfor %}
              </div>
            </div>

            <div class="ssc-card">
              <div class="section-title">Hallazgos recientes</div>
              <table class="finding-table">
                <thead>
                  <tr>
                    <th>Hallazgo</th>
                    <th>Severidad</th>
                    <th>Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {% for f in recent_findings %}
                  {% set sev = f.severidad or f.riesgo or 'Bajo' %}
                  <tr>
                    <td title="{{ f.control or f.categoria }}">{{ f.control or f.categoria }}</td>
                    <td>
                      <span class="severity-badge
                        {% if sev in ['Crítico','Critico'] %}sev-critical
                        {% elif sev == 'Alto' %}sev-high
                        {% elif sev == 'Medio' %}sev-medium
                        {% else %}sev-low{% endif %}">
                        {{ sev }}
                      </span>
                    </td>
                    <td>{{ f.estado or 'Abierto' }}</td>
                  </tr>
                  {% else %}
                  <tr>
                    <td colspan="3" class="text-center text-muted">Sin hallazgos registrados.</td>
                  </tr>
                  {% endfor %}
                </tbody>
              </table>
            </div>
          </div>

          <div class="right-stack">
            <div class="ssc-card">
              <div class="section-title">Desglose de riesgo</div>
              <div class="chart-box-small">
                <canvas id="riskChart"></canvas>
              </div>
            </div>

            <div class="ssc-card">
              <div class="section-title">Comparación con pares</div>
              <div class="chart-box-small">
                <canvas id="peerChart"></canvas>
              </div>
            </div>

            <div class="ssc-card full">
              <div class="section-title">Comparación mensual del proveedor</div>
              <div class="chart-box-small">
                <canvas id="monthlyChart"></canvas>
              </div>
              {% if monthly|length < 2 %}
                <div class="empty-note">
                  Para comparar por mes, ejecuta evaluaciones en meses diferentes o carga históricos.
                </div>
              {% endif %}
            </div>
          </div>
        </div>
      </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

    <script>
      const trendLabels = {{ trend_labels|tojson }};
      const trendScores = {{ trend_scores|tojson }};
      const riskLabels = {{ risk_labels|tojson }};
      const riskValues = {{ risk_values|tojson }};
      const peerLabels = {{ peer_labels|tojson }};
      const peerValues = {{ peer_values|tojson }};
      const monthlyLabels = {{ monthly_labels|tojson }};
      const monthlyScores = {{ monthly_scores|tojson }};

      const gaugeLabels = {{ gauge_labels|tojson }};
      const gaugeScores = {{ gauge_scores|tojson }};
      const gaugeCanvasIds = {{ gauge_canvas_ids|tojson }};

      function chartBaseOptions(maxY=true){
        return {
          responsive: true,
          maintainAspectRatio: false,
          layout: { padding: 0 },
          scales: maxY ? {
            y: {
              min: 0,
              max: 100,
              ticks: { stepSize: 25, font: { size: 9 } },
              grid: { lineWidth: .5 }
            },
            x: {
              ticks: { font: { size: 9 }, maxRotation: 0, autoSkip: true },
              grid: { display: false }
            }
          } : {},
          plugins: {
            legend: { display: false },
            tooltip: { bodyFont: { size: 10 }, titleFont: { size: 10 } }
          }
        }
      }

      function gaugeState(score){
        score = Number(score || 0);
        if(score >= 85){ return 'Bajo'; }
        if(score >= 70){ return 'Medio'; }
        if(score >= 50){ return 'Alto'; }
        return 'Crítico';
      }

      const gaugeNeedlePlugin = {
        id: 'gaugeNeedlePlugin',
        afterDatasetDraw(chart, args, pluginOptions){
          if(chart.config.type !== 'doughnut' || !chart.config.options.plugins.gaugeNeedle){
            return;
          }

          const score = Number(chart.config.options.plugins.gaugeNeedle.score || 0);
          const ctx = chart.ctx;
          const meta = chart.getDatasetMeta(0);
          if(!meta || !meta.data || !meta.data[0]){
            return;
          }

          const arc = meta.data[0];
          const x = arc.x;
          const y = arc.y;
          const outerRadius = arc.outerRadius;
          const innerRadius = arc.innerRadius;
          const needleLength = outerRadius - 9;

          const angle = Math.PI + (Math.PI * Math.max(0, Math.min(100, score)) / 100);

          ctx.save();

          // sombra de aguja
          ctx.translate(x, y);
          ctx.rotate(angle);

          ctx.beginPath();
          ctx.moveTo(-5, 2);
          ctx.lineTo(needleLength, 0);
          ctx.lineTo(-5, -2);
          ctx.closePath();
          ctx.fillStyle = 'rgba(15,23,42,.28)';
          ctx.fill();

          ctx.beginPath();
          ctx.moveTo(-6, 3);
          ctx.lineTo(needleLength - 2, 0);
          ctx.lineTo(-6, -3);
          ctx.closePath();
          ctx.fillStyle = '#172033';
          ctx.fill();

          ctx.restore();

          // centro
          ctx.save();
          ctx.beginPath();
          ctx.arc(x, y, 8, 0, Math.PI * 2);
          ctx.fillStyle = '#ffffff';
          ctx.shadowColor = 'rgba(15,23,42,.25)';
          ctx.shadowBlur = 7;
          ctx.shadowOffsetY = 2;
          ctx.fill();

          ctx.beginPath();
          ctx.arc(x, y, 4.5, 0, Math.PI * 2);
          ctx.fillStyle = '#172033';
          ctx.shadowBlur = 0;
          ctx.fill();
          ctx.restore();

          // etiquetas 0 / 50 / 100
          ctx.save();
          ctx.fillStyle = '#475569';
          ctx.font = '700 8px Arial';
          ctx.textAlign = 'center';
          ctx.fillText('0', x - outerRadius + 12, y + 12);
          ctx.fillText('50', x, y - outerRadius + 16);
          ctx.fillText('100', x + outerRadius - 12, y + 12);
          ctx.restore();
        }
      };

      Chart.register(gaugeNeedlePlugin);

      function buildGauge(canvasId, score, label){
        const ctx = document.getElementById(canvasId);
        if(!ctx){ return; }

        score = Math.max(0, Math.min(100, Number(score || 0)));

        new Chart(ctx, {
          type: 'doughnut',
          data: {
            labels: ['Crítico', 'Alto', 'Medio', 'Bajo'],
            datasets: [{
              data: [50, 20, 15, 15],
              backgroundColor: ['#991b1b', '#c2410c', '#d97706', '#087c3d'],
              borderColor: '#ffffff',
              borderWidth: 2,
              circumference: 180,
              rotation: 270,
              cutout: '68%',
              borderRadius: 5
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: {
              padding: {
                top: 4,
                left: 2,
                right: 2,
                bottom: 0
              }
            },
            plugins: {
              legend: { display: false },
              tooltip: { enabled: false },
              gaugeNeedle: {
                score: score
              }
            }
          }
        });
      }

      function buildAllGauges(){
        for(let i = 0; i < gaugeCanvasIds.length; i++){
          buildGauge(gaugeCanvasIds[i], gaugeScores[i], gaugeLabels[i]);
        }
      }

      function buildTrend(){
        const ctx = document.getElementById('trendChart');

        new Chart(ctx, {
          type: 'line',
          data: {
            labels: trendLabels,
            datasets: [{
              label: 'Score',
              data: trendScores,
              tension: 0.35,
              fill: true,
              borderWidth: 2,
              pointRadius: 3,
              pointHoverRadius: 4
            }]
          },
          options: chartBaseOptions(true)
        });
      }

      function buildRisk(){
        const ctx = document.getElementById('riskChart');

        new Chart(ctx, {
          type: 'doughnut',
          data: {
            labels: riskLabels,
            datasets: [{
              data: riskValues,
              backgroundColor: ['#991b1b', '#c2410c', '#d97706', '#0b4a8f'],
              borderWidth: 1
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '58%',
            layout: { padding: 0 },
            plugins: {
              legend: {
                position: 'right',
                labels: {
                  boxWidth: 9,
                  font: { size: 9 },
                  padding: 6
                }
              },
              tooltip: {
                bodyFont: { size: 10 },
                titleFont: { size: 10 }
              }
            }
          }
        });
      }

      function buildPeer(){
        const ctx = document.getElementById('peerChart');

        new Chart(ctx, {
          type: 'bar',
          data: {
            labels: peerLabels,
            datasets: [{
              label: 'Score',
              data: peerValues,
              backgroundColor: ['#087c3d', '#334155', '#0b4a8f'],
              borderWidth: 1
            }]
          },
          options: chartBaseOptions(true)
        });
      }

      function buildMonthly(){
        const ctx = document.getElementById('monthlyChart');

        new Chart(ctx, {
          type: 'line',
          data: {
            labels: monthlyLabels,
            datasets: [{
              label: 'Score mensual',
              data: monthlyScores,
              tension: 0.35,
              fill: false,
              borderWidth: 2,
              pointRadius: 3
            }]
          },
          options: chartBaseOptions(true)
        });
      }

      buildAllGauges();
      buildTrend();
      buildRisk();
      buildPeer();
      buildMonthly();
    </script>
    """

    return render_template_string(
        BASE,
        content=Markup(render_template_string(
            body,
            run=run,
            score_total=score_total,
            letra=letra,
            texto_rating=texto_rating,
            color_rating=color_rating,
            trend=trend,
            monthly=monthly,
            summary=summary,
            counts=counts,
            total_riesgos=total_riesgos,
            recent_findings=recent_findings,
            risk_factor_scores=risk_factor_scores,
            trend_labels=trend_labels,
            trend_scores=trend_scores,
            risk_labels=risk_labels,
            risk_values=risk_values,
            peer_labels=peer_labels,
            peer_values=peer_values,
            monthly_labels=monthly_labels,
            monthly_scores=monthly_scores,
            gauge_labels=gauge_labels,
            gauge_scores=gauge_scores,
            gauge_canvas_ids=gauge_canvas_ids
        ))
    )

@app.route("/proveedores/scorecard/<int:scorecard_id>/eliminar", methods=["POST"])
@login_required
def proveedores_scorecard_eliminar(scorecard_id):
    user, allowed, read_only = scorecard_user_permiso()

    if not allowed:
        flash("No tiene permiso para eliminar Scorecards.", "danger")
        return redirect(url_for("menu"))

    if read_only:
        flash("El rol Auditor no puede eliminar Scorecards.", "danger")
        return redirect(url_for("proveedores_scorecard_dashboard"))

    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM scorecard_runs WHERE id = ?", (scorecard_id,))
    run = cur.fetchone()

    if not run:
        conn.close()
        flash("No se encontró el Scorecard seleccionado.", "warning")
        return redirect(url_for("proveedores_scorecard_dashboard"))

    cur.execute("DELETE FROM scorecard_findings WHERE run_id = ?", (scorecard_id,))
    cur.execute("DELETE FROM scorecard_outputs WHERE run_id = ?", (scorecard_id,))
    cur.execute("DELETE FROM scorecard_incidents WHERE run_id = ?", (scorecard_id,))
    cur.execute("DELETE FROM scorecard_darkweb_exposures WHERE run_id = ?", (scorecard_id,))
    cur.execute("DELETE FROM scorecard_runs WHERE id = ?", (scorecard_id,))

    conn.commit()
    conn.close()

    registrar_log(
        getattr(user, "username", "Sistema"),
        f"Eliminó Scorecard de proveedor ID {scorecard_id}: {run['proveedor_nombre']} - {run['dominio']}"
    )

    flash("Scorecard eliminado correctamente.", "success")
    return redirect(url_for("proveedores_scorecard_dashboard"))

@app.route("/proveedores/scorecard/<int:scorecard_id>/kali")
@login_required
def proveedores_scorecard_kali_detalle(scorecard_id):
    user, allowed, read_only = scorecard_user_permiso()

    if not allowed:
        flash("No tiene permiso para acceder al detalle Kali del Scorecard.", "danger")
        return redirect(url_for("menu"))

    if read_only:
        flash("El rol Auditor no tiene acceso al detalle técnico Kali Linux.", "warning")
        return redirect(url_for("proveedores_scorecard_detalle", scorecard_id=scorecard_id))

    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM scorecard_runs WHERE id = ?", (scorecard_id,))
    run = cur.fetchone()

    if not run:
        conn.close()
        abort(404)

    cur.execute("""
        SELECT *
        FROM scorecard_findings
        WHERE run_id = ?
          AND categoria = 'Kali Linux Scan'
        ORDER BY 
          CASE riesgo
            WHEN 'Crítico' THEN 1
            WHEN 'Alto' THEN 2
            WHEN 'Medio' THEN 3
            WHEN 'Bajo' THEN 4
            ELSE 5
          END,
          herramienta ASC,
          id ASC
    """, (scorecard_id,))
    findings_kali = cur.fetchall()

    cur.execute("""
        SELECT *
        FROM scorecard_outputs
        WHERE run_id = ?
        ORDER BY id ASC
    """, (scorecard_id,))
    outputs = cur.fetchall()

    conn.close()

    body = """
    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .score-shell{
        width:96%;
        max-width:1650px;
        margin:26px auto 24px auto;
      }

      .score-header-card{
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

      .score-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .score-header-overlay{
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

      .score-header-overlay::before{
        content:"🧪";
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

      .score-header-text{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
        color:#ffffff !important;
        font-size:1.32rem;
        font-weight:950;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
        position:relative;
        z-index:1;
      }

      .score-header-text::before{
        content:"SGSI · Resultados Kali Linux";
        display:block;
        width:max-content;
        max-width:100%;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
        text-shadow:none;
      }

      .score-card,
      .card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
        padding:20px;
      }

      .soft-table-wrap{
        background:rgba(255,255,255,.96);
        border-radius:18px;
        overflow:hidden;
        box-shadow:0 12px 24px rgba(15,23,42,.18);
        border:1px solid rgba(219,230,244,.9);
      }

      .kali-table-scroll{
        max-height:620px;
        overflow:auto;
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
        font-weight:900 !important;
        border:none !important;
        white-space:nowrap;
        vertical-align:middle !important;
        text-align:center;
        padding:9px 8px;
      }

      .table tbody td,
      .table td{
        vertical-align:top !important;
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

      .evidence-cell{
        min-width:520px;
        max-width:760px;
        white-space:pre-wrap;
        font-size:.86rem;
        line-height:1.45;
      }

      .recommend-cell{
        min-width:360px;
        white-space:normal;
        word-break:break-word;
        overflow-wrap:anywhere;
        line-height:1.45;
      }

      pre{
        white-space:pre-wrap;
        max-height:520px;
        overflow:auto;
        background:#0b1f33;
        color:#dceeff;
        padding:16px;
        border-radius:14px;
        font-size:.84rem;
        border:1px solid rgba(255,255,255,.12);
        box-shadow:inset 0 1px 0 rgba(255,255,255,.08);
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

      @media (max-width:992px){
        .score-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .score-header-card{
          min-height:88px;
        }

        .score-header-text{
          font-size:1.20rem;
        }

        .score-card,
        .card{
          padding:16px;
        }

        .evidence-cell{
          min-width:420px;
        }
      }

      @media (max-width:768px){
        .score-header-overlay{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .score-header-overlay::before{
          margin:0;
        }

        .score-header-text,
        .score-header-text::before{
          text-align:center;
          margin-left:auto;
          margin-right:auto;
        }
      }
    </style>

    <div class="score-shell">
      <div class="score-header-card">
        <div class="score-header-overlay">
          <h1 class="score-header-text">Detalle Escaneo Kali Linux — Scorecard Proveedor</h1>
        </div>
      </div>

      <div class="d-flex justify-content-between mb-3">
        <a href="{{ url_for('proveedores_scorecard_detalle', scorecard_id=run.id) }}"
           class="btn btn-outline-secondary rounded-pill px-4">
          Volver al Scorecard
        </a>

        <a href="{{ url_for('proveedores_scorecard_kali_detalle', scorecard_id=run.id) }}"
           class="btn btn-primary rounded-pill px-4">
          🔄 Actualizar
        </a>
      </div>

      <div class="score-card mb-3">
        <div class="row">
          <div class="col-md-8">
            <h4 class="fw-bold mb-2">{{ run.proveedor_nombre or 'Proveedor no asociado' }}</h4>
            <p class="mb-1"><strong>Dominio:</strong> {{ run.dominio }}</p>
            <p class="mb-1"><strong>IP:</strong> {{ run.ip_resuelta or '—' }}</p>
            <p class="mb-1"><strong>Estado:</strong> {{ run.estado }}</p>
            <p class="mb-1"><strong>Etapa:</strong> {{ run.current_stage or '—' }}</p>
            <p class="mb-0"><strong>Herramienta actual:</strong> {{ run.current_tool or '—' }}</p>
          </div>
          <div class="col-md-4 text-center">
            <div class="fs-1 fw-bold text-primary">{{ "%.1f"|format(run.score_kali or 0) }}%</div>
            <div class="fw-bold text-muted">Score Kali Linux</div>
          </div>
        </div>
      </div>

      <div class="soft-table-wrap mb-3">
        <div class="p-3 pb-0">
          <h5 class="fw-bold mb-2">Vulnerabilidades / hallazgos detectados por Kali</h5>
        </div>

        <div class="table-responsive kali-table-scroll">
          <table class="table table-hover align-middle mb-0">
            <thead>
              <tr>
                <th>ID</th>
                <th>Herramienta</th>
                <th>Control</th>
                <th>Estado</th>
                <th>Riesgo</th>
                <th>Score</th>
                <th>Evidencia técnica</th>
                <th>Recomendación</th>
                <th>Archivo</th>
              </tr>
            </thead>
            <tbody>
              {% for f in findings_kali %}
              <tr>
                <td>#{{ f.id }}</td>
                <td><strong>{{ f.herramienta or '—' }}</strong></td>
                <td>{{ f.control or '—' }}</td>
                <td>{{ f.estado or '—' }}</td>
                <td>
                  <span class="badge bg-{{ 'success' if f.riesgo == 'Bajo' else 'warning text-dark' if f.riesgo == 'Medio' else 'danger' }}">
                    {{ f.riesgo or '—' }}
                  </span>
                </td>
                <td>{{ "%.1f"|format(f.score or 0) }}%</td>
                <td class="evidence-cell">{{ f.evidencia or '—' }}</td>
                <td class="recommend-cell">{{ f.recomendacion or '—' }}</td>
                <td style="min-width:260px;">{{ f.archivo_salida or '—' }}</td>
              </tr>
              {% else %}
              <tr>
                <td colspan="9" class="text-center text-muted py-4">
                  No hay hallazgos Kali registrados para este Scorecard.
                </td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>

      <div class="soft-table-wrap mb-3">
        <div class="p-3 pb-0">
          <h5 class="fw-bold mb-2">Salidas por herramienta</h5>
        </div>

        <div class="table-responsive kali-table-scroll">
          <table class="table table-hover align-middle mb-0">
            <thead>
              <tr>
                <th>Herramienta</th>
                <th>Exit Code</th>
                <th>Duración</th>
                <th>Comando</th>
                <th>Archivo salida</th>
              </tr>
            </thead>
            <tbody>
              {% for o in outputs %}
              <tr>
                <td><strong>{{ o.herramienta }}</strong></td>
                <td>{{ o.exit_code }}</td>
                <td>{{ "%.1f"|format(o.duracion_segundos or 0) }} s</td>
                <td style="min-width:520px; white-space:pre-wrap;">{{ o.comando or '—' }}</td>
                <td style="min-width:320px;">{{ o.archivo_salida or '—' }}</td>
              </tr>
              {% else %}
              <tr>
                <td colspan="5" class="text-center text-muted py-4">
                  No hay salidas técnicas registradas.
                </td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>

      {% if run.salida_consola %}
      <div class="score-card">
        <h5 class="fw-bold mb-3">Log consolidado del escaneo Kali</h5>
        <pre>{{ run.salida_consola }}</pre>
      </div>
      {% endif %}
    </div>
    """

    return render_template_string(
        BASE,
        content=Markup(render_template_string(
            body,
            run=run,
            findings_kali=findings_kali,
            outputs=outputs
        ))
    )

def scorecard_score_darkweb(total_hallazgos, credencial_confirmada=False):
    if credencial_confirmada:
        return scorecard_get_param("darkweb_score_credenciales_confirmadas", 20), "Crítico"

    total_hallazgos = int(total_hallazgos or 0)

    if total_hallazgos <= 0:
        return scorecard_get_param("darkweb_score_sin_hallazgos", 100), "Bajo"
    if total_hallazgos <= 2:
        return scorecard_get_param("darkweb_score_1_2", 80), "Medio"
    if total_hallazgos <= 5:
        return scorecard_get_param("darkweb_score_3_5", 60), "Alto"

    return scorecard_get_param("darkweb_score_mas_5", 40), "Crítico"


def guardar_scorecard_darkweb_exposure(run_id, proveedor_id, proveedor_nombre, dominio, item):
    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO scorecard_darkweb_exposures
        (run_id, proveedor_id, proveedor_nombre, dominio, fuente, tipo_exposicion,
         indicador, severidad, fecha, evidencia, recomendacion, url,
         credencial_confirmada, detalle_json, fecha_registro)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id,
        proveedor_id,
        proveedor_nombre,
        dominio,
        item.get("fuente"),
        item.get("tipo_exposicion"),
        item.get("indicador"),
        item.get("severidad"),
        item.get("fecha"),
        item.get("evidencia"),
        item.get("recomendacion"),
        item.get("url"),
        1 if item.get("credencial_confirmada") else 0,
        json.dumps(item, ensure_ascii=False),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def consultar_hibp_domain_scorecard(dominio):
    resultados = []
    api_key = os.getenv("HIBP_API_KEY", "").strip()

    if not api_key or not dominio:
        return resultados

    try:
        url = f"https://haveibeenpwned.com/api/v3/breachedDomain/{dominio}"
        headers = {
            "hibp-api-key": api_key,
            "user-agent": "GRAC-Scorecard-SGSI"
        }

        resp = requests.get(url, headers=headers, timeout=20)

        if resp.status_code == 404:
            return []

        if resp.status_code in [401, 403]:
            resultados.append({
                "fuente": "Have I Been Pwned",
                "tipo_exposicion": "Consulta no autorizada / dominio no verificado",
                "indicador": dominio,
                "severidad": "Medio",
                "fecha": "",
                "evidencia": "HIBP requiere API Key válida y dominio verificado para búsqueda por dominio.",
                "recomendacion": "Configurar HIBP_API_KEY y verificar el dominio en Have I Been Pwned.",
                "url": "https://haveibeenpwned.com/API/v3",
                "credencial_confirmada": False
            })
            return resultados

        if resp.status_code != 200:
            return []

        data = resp.json() or {}

        for alias, breaches in data.items():
            correo = f"{alias}@{dominio}"
            breaches = breaches or []

            resultados.append({
                "fuente": "Have I Been Pwned",
                "tipo_exposicion": "Correo corporativo en brecha",
                "indicador": correo,
                "severidad": "Crítico",
                "fecha": "",
                "evidencia": "Brechas asociadas: " + ", ".join(breaches[:10]),
                "recomendacion": "Forzar cambio de contraseña, revisar MFA, validar cuentas activas y solicitar plan de remediación al proveedor.",
                "url": "https://haveibeenpwned.com/",
                "credencial_confirmada": True
            })

    except Exception as e:
        print("Error consultando HIBP Scorecard:", repr(e))

    return resultados


def consultar_darkweb_gdelt_osint_scorecard(proveedor_nombre, dominio):
    resultados = []

    try:
        terminos = []

        if proveedor_nombre and proveedor_nombre != "Proveedor no asociado":
            terminos += [
                f'"{proveedor_nombre}" "dark web"',
                f'"{proveedor_nombre}" "credential leak"',
                f'"{proveedor_nombre}" "password leak"',
                f'"{proveedor_nombre}" "stealer logs"',
                f'"{proveedor_nombre}" "data dump"',
            ]

        if dominio:
            terminos += [
                f'"{dominio}" "dark web"',
                f'"{dominio}" "credential leak"',
                f'"{dominio}" "password leak"',
                f'"{dominio}" "stealer logs"',
                f'"{dominio}" "data dump"',
            ]

        query = " OR ".join(terminos[:8])
        if not query:
            return []

        resp = requests.get(
            "https://api.gdeltproject.org/api/v2/doc/doc",
            params={
                "query": query,
                "mode": "ArtList",
                "format": "json",
                "maxrecords": 10,
                "sort": "HybridRel"
            },
            timeout=15
        )

        if resp.status_code != 200:
            return []

        data = resp.json() or {}
        vistos = set()

        for art in data.get("articles") or []:
            titulo = (art.get("title") or "").strip()
            link = (art.get("url") or "").strip()

            if not titulo or not link or link.lower() in vistos:
                continue

            vistos.add(link.lower())

            texto = titulo.lower()
            severidad = "Medio"

            if any(x in texto for x in ["password", "credential", "stealer", "dump", "dark web", "leak"]):
                severidad = "Alto"

            if any(x in texto for x in ["millions", "massive", "critical", "ransomware"]):
                severidad = "Crítico"

            resultados.append({
                "fuente": "GDELT + búsqueda OSINT",
                "tipo_exposicion": "Mención pública de exposición / leak",
                "indicador": dominio or proveedor_nombre,
                "severidad": severidad,
                "fecha": art.get("seendate") or "",
                "evidencia": titulo[:600],
                "recomendacion": "Validar fuente, solicitar confirmación al proveedor y requerir evidencia de contención.",
                "url": link,
                "credencial_confirmada": False
            })

    except Exception as e:
        print("Error consultando GDELT Dark Web OSINT:", repr(e))

    return resultados


def evaluar_darkweb_exposure_scorecard(run_id, proveedor_id, proveedor_nombre, dominio):
    exposiciones = []

    exposiciones += consultar_hibp_domain_scorecard(dominio)
    exposiciones += consultar_darkweb_gdelt_osint_scorecard(proveedor_nombre, dominio)

    vistos = set()
    dedup = []

    for item in exposiciones:
        key = f"{item.get('fuente')}|{item.get('indicador')}|{item.get('url')}|{item.get('evidencia')}".lower()
        if key in vistos:
            continue
        vistos.add(key)
        dedup.append(item)

    for item in dedup:
        guardar_scorecard_darkweb_exposure(run_id, proveedor_id, proveedor_nombre, dominio, item)

    total = len(dedup)
    credencial_confirmada = any(x.get("credencial_confirmada") for x in dedup)
    score, riesgo = scorecard_score_darkweb(total, credencial_confirmada)

    evidencia = (
        f"Fuentes consultadas: Have I Been Pwned + GDELT + búsqueda OSINT. Hallazgos identificados: {total}."
        if total else
        "Fuentes consultadas: Have I Been Pwned + GDELT + búsqueda OSINT. No se identificaron hallazgos de exposición pública o dark web."
    )

    guardar_scorecard_finding(run_id, {
        "categoria": "Dark Web / Exposure Intelligence",
        "herramienta": "Have I Been Pwned + GDELT + búsqueda OSINT",
        "control": "Exposición Dark Web / Leaks",
        "estado": "Con hallazgos" if total else "Sin hallazgos",
        "riesgo": riesgo,
        "severidad": riesgo,
        "score": score,
        "evidencia": evidencia,
        "recomendacion": "Validar fuentes, solicitar explicación al proveedor, rotar credenciales comprometidas y verificar MFA." if total else "Mantener monitoreo periódico."
    })

    return score, riesgo, total, credencial_confirmada

@app.route("/proveedores/scorecard/parametros", methods=["GET", "POST"])
@login_required
def proveedores_scorecard_parametros():
    user, allowed, read_only = scorecard_user_permiso()

    if not allowed:
        flash("No tiene permiso para parametrizar Scorecard.", "danger")
        return redirect(url_for("menu"))

    if read_only:
        flash("El rol Auditor no puede modificar parámetros.", "danger")
        return redirect(url_for("proveedores_scorecard_dashboard"))

    conn = get_scorecard_db_connection()
    cur = conn.cursor()

    if request.method == "POST":
        accion = request.form.get("accion")

        if accion == "guardar_parametros":
            claves_numericas = [
                "peso_dns",
                "peso_ip",
                "peso_kali",
                "peso_incidentes",
                "peso_darkweb",
                "darkweb_score_sin_hallazgos",
                "darkweb_score_1_2",
                "darkweb_score_3_5",
                "darkweb_score_mas_5",
                "darkweb_score_credenciales_confirmadas",
            ]

            for clave in claves_numericas:
                valor = request.form.get(clave, type=float)
                if valor is None:
                    valor = scorecard_get_param(clave, 0)

                cur.execute("""
                    INSERT INTO scorecard_parametros (clave, valor, descripcion)
                    VALUES (?, ?, ?)
                    ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor
                """, (
                    clave,
                    valor,
                    clave.replace("_", " ").title()
                ))

            conn.commit()

            registrar_log(
                getattr(user, "username", "Sistema"),
                "Actualizó parámetros generales del Scorecard de Proveedores"
            )

            flash("Parámetros generales actualizados correctamente.", "success")
            conn.close()
            return redirect(url_for("proveedores_scorecard_parametros"))

        elif accion == "agregar_riesgo":
            nombre = (request.form.get("nombre_riesgo") or "").strip()
            score_min = request.form.get("score_min", type=float)
            color_bootstrap = (request.form.get("color_bootstrap") or "secondary").strip()
            orden = request.form.get("orden", type=int) or 0

            if not nombre:
                flash("Debe indicar el nombre del nivel de riesgo.", "danger")
                conn.close()
                return redirect(url_for("proveedores_scorecard_parametros"))

            if score_min is None:
                flash("Debe indicar el score mínimo del nivel de riesgo.", "danger")
                conn.close()
                return redirect(url_for("proveedores_scorecard_parametros"))

            cur.execute("""
                INSERT INTO scorecard_risk_levels
                (nombre, score_min, color_bootstrap, orden, activo, fecha_creacion)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                nombre,
                score_min,
                color_bootstrap,
                orden,
                1,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))

            conn.commit()

            registrar_log(
                getattr(user, "username", "Sistema"),
                f"Agregó nivel de riesgo Scorecard: {nombre} desde {score_min}"
            )

            flash("Nivel de riesgo agregado correctamente.", "success")
            conn.close()
            return redirect(url_for("proveedores_scorecard_parametros"))

        elif accion == "actualizar_riesgos":
            ids = request.form.getlist("risk_id")

            for rid in ids:
                nombre = (request.form.get(f"nombre_{rid}") or "").strip()
                score_min = request.form.get(f"score_min_{rid}", type=float)
                color_bootstrap = (request.form.get(f"color_{rid}") or "secondary").strip()
                orden = request.form.get(f"orden_{rid}", type=int) or 0
                activo = 1 if request.form.get(f"activo_{rid}") else 0

                if not nombre:
                    continue

                if score_min is None:
                    score_min = 0

                cur.execute("""
                    UPDATE scorecard_risk_levels
                    SET nombre = ?, score_min = ?, color_bootstrap = ?, orden = ?, activo = ?
                    WHERE id = ?
                """, (
                    nombre,
                    score_min,
                    color_bootstrap,
                    orden,
                    activo,
                    rid
                ))

            conn.commit()

            registrar_log(
                getattr(user, "username", "Sistema"),
                "Actualizó niveles dinámicos de riesgo del Scorecard"
            )

            flash("Niveles de riesgo actualizados correctamente.", "success")
            conn.close()
            return redirect(url_for("proveedores_scorecard_parametros"))

        elif accion == "eliminar_riesgo":
            rid = request.form.get("risk_id_delete", type=int)

            if rid:
                cur.execute("DELETE FROM scorecard_risk_levels WHERE id = ?", (rid,))
                conn.commit()

                registrar_log(
                    getattr(user, "username", "Sistema"),
                    f"Eliminó nivel de riesgo Scorecard ID {rid}"
                )

                flash("Nivel de riesgo eliminado correctamente.", "success")

            conn.close()
            return redirect(url_for("proveedores_scorecard_parametros"))

    cur.execute("SELECT * FROM scorecard_parametros ORDER BY clave ASC")
    rows = cur.fetchall()

    cur.execute("""
        SELECT *
        FROM scorecard_risk_levels
        ORDER BY score_min DESC, orden ASC, id ASC
    """)
    risk_levels = cur.fetchall()

    conn.close()

    params = {r["clave"]: r for r in rows}

    body = """
    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .score-shell{
        width:96%;
        max-width:1500px;
        margin:26px auto 24px auto;
      }

      .score-header-card{
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

      .score-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(135deg,rgba(255,255,255,.05) 0px,rgba(255,255,255,.05) 1px,transparent 1px,transparent 14px);
        pointer-events:none;
      }

      .score-header-card::after{
        content:"⚙️";
        order:-1;
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
        position:relative;
        z-index:1;
      }

      .score-header-text{
        max-width:1100px;
        width:100%;
        display:block !important;
        transform:none !important;
        color:#ffffff !important;
        font-size:1.32rem;
        font-weight:950;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
        position:relative;
        z-index:1;
      }

      .score-header-text::before{
        content:"SGSI · Parámetros Scorecard";
        display:block;
        width:max-content;
        max-width:100%;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
        text-shadow:none;
      }

      .score-card,
      .card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
        padding:24px;
        margin-bottom:18px;
      }

      .param-section-title,
      .card h5,
      .card h6{
        font-weight:950;
        font-size:.95rem;
        color:#0b4a8f;
        margin-bottom:16px;
        padding-bottom:8px;
        border-bottom:2px solid rgba(59,130,246,.18);
      }

      .soft-table-wrap,
      .table-responsive{
        max-height:72vh;
        overflow-y:auto;
        overflow-x:auto;
        background:#ffffff;
        border-radius:14px;
        border:1px solid #dbe6f4;
        box-shadow:0 12px 24px rgba(15,23,42,.10);
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
        font-weight:900 !important;
        border:none !important;
        white-space:nowrap;
        vertical-align:middle !important;
        text-align:center;
        padding:9px 8px;
      }

      .table tbody td,
      .table td{
        vertical-align:middle !important;
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

      .risk-help{
        font-size:.86rem;
        color:#607086;
        font-weight:700;
        line-height:1.45;
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

      @media (max-width:992px){
        .score-shell{
          width:98%;
          margin:8px auto 22px auto;
        }

        .score-header-card{
          min-height:88px;
        }

        .score-header-text{
          font-size:1.20rem;
        }

        .score-card,
        .card{
          padding:16px;
        }
      }

      @media (max-width:768px){
        .score-header-card{
          flex-direction:column;
          text-align:center;
          gap:10px;
        }

        .score-header-card::after{
          margin:0;
        }

        .score-header-text,
        .score-header-text::before{
          text-align:center;
          margin-left:auto;
          margin-right:auto;
        }
      }
    </style>

    <div class="score-shell">
      <div class="score-header-card">
        <h1 class="score-header-text">Parametrización Scorecard de Proveedores</h1>
      </div>

      <div class="score-card">
        <form method="POST">
          <input type="hidden" name="accion" value="guardar_parametros">

          <h5 class="param-section-title">1. Pesos del Score Total</h5>

          <div class="alert alert-info">
            La suma recomendada es 100%. Si la suma cambia, el sistema normaliza automáticamente los pesos.
          </div>

          <div class="row g-3 mb-4">
            {% for key,label in [
              ('peso_dns','DNS Health (%)'),
              ('peso_ip','IP Reputation (%)'),
              ('peso_kali','Kali Linux (%)'),
              ('peso_incidentes','Incidentes / Brechas (%)'),
              ('peso_darkweb','Dark Web Exposure (%)')
            ] %}
            <div class="col-md">
              <label class="form-label fw-bold">{{ label }}</label>
              <input type="number" step="0.01" min="0" max="100" name="{{ key }}" class="form-control"
                     value="{{ params[key].valor if key in params else 0 }}">
            </div>
            {% endfor %}
          </div>

          <hr>

          <h5 class="param-section-title">2. Score Dark Web / Exposure Intelligence</h5>

          <div class="alert alert-secondary">
            Fuentes consultadas: <strong>Have I Been Pwned + GDELT + búsqueda OSINT</strong>.
          </div>

          <div class="row g-3 mb-4">
            {% for key,label in [
              ('darkweb_score_sin_hallazgos','Sin hallazgos'),
              ('darkweb_score_1_2','1 a 2 hallazgos'),
              ('darkweb_score_3_5','3 a 5 hallazgos'),
              ('darkweb_score_mas_5','Más de 5 hallazgos'),
              ('darkweb_score_credenciales_confirmadas','Credenciales confirmadas')
            ] %}
            <div class="col-md">
              <label class="form-label fw-bold">{{ label }}</label>
              <input type="number" step="0.01" min="0" max="100" name="{{ key }}" class="form-control"
                     value="{{ params[key].valor if key in params else 0 }}">
            </div>
            {% endfor %}
          </div>

          <div class="d-flex justify-content-end">
            <button class="btn btn-primary rounded-pill px-4">
              💾 Guardar parámetros generales
            </button>
          </div>
        </form>
      </div>

      <div class="score-card">
        <h5 class="param-section-title">3. Agregar nivel de riesgo</h5>

        <form method="POST">
          <input type="hidden" name="accion" value="agregar_riesgo">

          <div class="row g-3 align-items-end">
            <div class="col-md-4">
              <label class="form-label fw-bold">Nombre del nivel</label>
              <input type="text" name="nombre_riesgo" class="form-control" placeholder="Ej: Aceptable, Moderado, Alto, Crítico" required>
            </div>

            <div class="col-md-2">
              <label class="form-label fw-bold">Score mínimo</label>
              <input type="number" step="0.01" min="0" max="100" name="score_min" class="form-control" required>
            </div>

            <div class="col-md-3">
              <label class="form-label fw-bold">Color Bootstrap</label>
              <select name="color_bootstrap" class="form-select">
                <option value="success">Verde / success</option>
                <option value="warning text-dark">Amarillo / warning</option>
                <option value="danger">Rojo / danger</option>
                <option value="dark">Negro / dark</option>
                <option value="secondary">Gris / secondary</option>
                <option value="primary">Azul / primary</option>
                <option value="info text-dark">Info / info</option>
              </select>
            </div>

            <div class="col-md-1">
              <label class="form-label fw-bold">Orden</label>
              <input type="number" name="orden" class="form-control" value="0">
            </div>

            <div class="col-md-2">
              <button class="btn btn-success rounded-pill w-100">
                ➕ Agregar
              </button>
            </div>
          </div>

          <div class="risk-help mt-2">
            El sistema evalúa desde el score más alto hacia abajo. Ejemplo: Aceptable desde 85, Moderado desde 70, Elevado desde 50, Crítico desde 0.
          </div>
        </form>
      </div>

      <div class="score-card">
        <h5 class="param-section-title">4. Niveles de riesgo configurados</h5>

        <form method="POST">
          <input type="hidden" name="accion" value="actualizar_riesgos">

          <div class="soft-table-wrap">
            <div class="table-responsive">
              <table class="table table-hover align-middle mb-0">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Nombre</th>
                    <th>Score mínimo</th>
                    <th>Color</th>
                    <th>Orden</th>
                    <th>Activo</th>
                    <th>Eliminar</th>
                  </tr>
                </thead>
                <tbody>
                  {% for r in risk_levels %}
                  <tr>
                    <td>
                      #{{ r.id }}
                      <input type="hidden" name="risk_id" value="{{ r.id }}">
                    </td>

                    <td>
                      <input type="text" name="nombre_{{ r.id }}" class="form-control" value="{{ r.nombre }}">
                    </td>

                    <td>
                      <input type="number" step="0.01" min="0" max="100" name="score_min_{{ r.id }}" class="form-control" value="{{ r.score_min }}">
                    </td>

                    <td>
                      <select name="color_{{ r.id }}" class="form-select">
                        {% for val,label in [
                          ('success','Verde / success'),
                          ('warning text-dark','Amarillo / warning'),
                          ('danger','Rojo / danger'),
                          ('dark','Negro / dark'),
                          ('secondary','Gris / secondary'),
                          ('primary','Azul / primary'),
                          ('info text-dark','Info / info')
                        ] %}
                          <option value="{{ val }}" {% if r.color_bootstrap == val %}selected{% endif %}>{{ label }}</option>
                        {% endfor %}
                      </select>
                    </td>

                    <td>
                      <input type="number" name="orden_{{ r.id }}" class="form-control" value="{{ r.orden or 0 }}">
                    </td>

                    <td class="text-center">
                      <input type="checkbox" name="activo_{{ r.id }}" class="form-check-input" {% if r.activo %}checked{% endif %}>
                    </td>

                    <td>
                      <button type="submit"
                              formaction="{{ url_for('proveedores_scorecard_parametros') }}"
                              formmethod="POST"
                              name="accion"
                              value="eliminar_riesgo"
                              class="btn btn-sm btn-outline-danger rounded-pill"
                              onclick="this.form.risk_id_delete.value='{{ r.id }}'; return confirm('¿Eliminar este nivel de riesgo?');">
                        Eliminar
                      </button>
                    </td>
                  </tr>
                  {% else %}
                  <tr>
                    <td colspan="7" class="text-center text-muted py-4">
                      No hay niveles de riesgo configurados.
                    </td>
                  </tr>
                  {% endfor %}
                </tbody>
              </table>
            </div>
          </div>

          <input type="hidden" name="risk_id_delete" value="">

          <div class="d-flex justify-content-between mt-3">
            <a href="{{ url_for('proveedores_scorecard_dashboard') }}" class="btn btn-outline-secondary rounded-pill px-4">
              Volver
            </a>

            <button class="btn btn-primary rounded-pill px-4">
              💾 Guardar niveles de riesgo
            </button>
          </div>
        </form>
      </div>
    </div>
    """

    return render_template_string(
        BASE,
        content=Markup(render_template_string(
            body,
            params=params,
            risk_levels=risk_levels
        ))
    )


# =============================================================================
#            SCORECARD TERCEROS INDEPENDIENTE
#            DNS HEALTH / IP REPUTATION / HACKER CHATTER / ESCANEO KALI PROPIO
# =============================================================================


SCORECARD_PROPONENTES_DB_PATH = os.path.join(app.instance_path, "scorecard_proponentes.db")
SCORECARD_PROPONENTES_UPLOAD_DIR = os.path.join(app.instance_path, "scorecard_proponentes_outputs")
os.makedirs(SCORECARD_PROPONENTES_UPLOAD_DIR, exist_ok=True)


# ============================================================
# DB INDEPENDIENTE SCORECARD PROPONENTES
# ============================================================

def get_scorecard_proponentes_db_connection():
    os.makedirs(app.instance_path, exist_ok=True)
    conn = sqlite3.connect(SCORECARD_PROPONENTES_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_scorecard_proponentes_db():
    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    # ===== PARAMETROS =====
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scorecard_parametros (
            clave TEXT PRIMARY KEY,
            valor REAL NOT NULL,
            descripcion TEXT
        )
    """)

    # ===== NIVELES DE RIESGO =====
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scorecard_risk_levels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            score_min REAL NOT NULL DEFAULT 0,
            color_bootstrap TEXT DEFAULT 'secondary',
            orden INTEGER DEFAULT 0,
            activo INTEGER DEFAULT 1,
            fecha_creacion TEXT NOT NULL
        )
    """)

    parametros_default = [
        ("peso_dns", 20, "Peso DNS Health"),
        ("peso_ip", 15, "Peso IP Reputation"),
        ("peso_kali", 35, "Peso Kali Linux"),
        ("peso_incidentes", 15, "Peso Incidentes/Brechas"),
        ("peso_darkweb", 15, "Peso Dark Web / Exposure Intelligence"),

        ("darkweb_score_sin_hallazgos", 100, "Sin hallazgos de riesgo"),
        ("darkweb_score_bajo", 90, "Hallazgos de severidad Baja"),
        ("darkweb_score_medio", 75, "Hallazgos de severidad Media"),
        ("darkweb_score_alto", 55, "Hallazgos de severidad Alta"),
        ("darkweb_score_critico", 25, "Hallazgos de severidad Crítica"),
        ("darkweb_score_credenciales_confirmadas", 20, "Credenciales confirmadas"),

        ("dns_score_a_ok", 100, "Registro A/CNAME OK"),
        ("dns_score_a_no_detectado", 0, "Registro A/CNAME no detectado"),
        ("dns_score_mx_ok", 100, "MX OK"),
        ("dns_score_mx_no_detectado", 70, "MX no detectado"),
        ("dns_score_ns_ok", 100, "NS OK"),
        ("dns_score_ns_no_detectado", 0, "NS no detectado"),
        ("dns_score_spf_ok", 100, "SPF OK"),
        ("dns_score_spf_no_configurado", 0, "SPF no configurado"),
        ("dns_score_dmarc_ok", 100, "DMARC OK"),
        ("dns_score_dmarc_p_none", 70, "DMARC p=none"),
        ("dns_score_dmarc_no_configurado", 0, "DMARC no configurado"),
    ]

    for clave, valor, descripcion in parametros_default:
        cur.execute("""
            INSERT OR IGNORE INTO scorecard_parametros (clave, valor, descripcion)
            VALUES (?, ?, ?)
        """, (clave, valor, descripcion))

    # ===== RISK LEVELS =====
    cur.execute("SELECT COUNT(*) FROM scorecard_risk_levels")
    if cur.fetchone()[0] == 0:
        niveles = [
            ("Bajo", 85, "success", 1),
            ("Medio", 70, "warning text-dark", 2),
            ("Alto", 50, "danger", 3),
            ("Crítico", 0, "dark", 4),
        ]

        for n in niveles:
            cur.execute("""
                INSERT INTO scorecard_risk_levels
                (nombre, score_min, color_bootstrap, orden, activo, fecha_creacion)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                n[0], n[1], n[2], n[3], 1,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))

    conn.commit()
    conn.close()

init_scorecard_proponentes_db()


def migrar_scorecard_proponentes_informe_ai():
    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(scorecard_proponentes_runs)")
    cols = [r["name"] for r in cur.fetchall()]

    if "informe_ejecutivo_ai" not in cols:
        cur.execute("ALTER TABLE scorecard_proponentes_runs ADD COLUMN informe_ejecutivo_ai TEXT")

    if "informe_ejecutivo_editado" not in cols:
        cur.execute("ALTER TABLE scorecard_proponentes_runs ADD COLUMN informe_ejecutivo_editado TEXT")

    if "informe_ejecutivo_fecha" not in cols:
        cur.execute("ALTER TABLE scorecard_proponentes_runs ADD COLUMN informe_ejecutivo_fecha TEXT")

    if "informe_ejecutivo_usuario" not in cols:
        cur.execute("ALTER TABLE scorecard_proponentes_runs ADD COLUMN informe_ejecutivo_usuario TEXT")

    conn.commit()
    conn.close()


migrar_scorecard_proponentes_informe_ai()

def migrar_scorecard_proponentes_herramientas_kali():
    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(scorecard_proponentes_runs)")
    cols = [r["name"] for r in cur.fetchall()]

    if "herramientas_kali" not in cols:
        cur.execute("ALTER TABLE scorecard_proponentes_runs ADD COLUMN herramientas_kali TEXT")

    conn.commit()
    conn.close()

migrar_scorecard_proponentes_herramientas_kali()


SCORECARD_PROPONENTES_HERRAMIENTAS_KALI_VALIDAS = [
    "nmap",
    "whatweb",
    "nikto",
    "testssl",
    "nuclei",
    "zap"
]


def scorecard_proponentes_normalizar_herramientas_kali(lista):
    herramientas = []

    for h in lista or []:
        h = (h or "").strip().lower()
        if h in SCORECARD_PROPONENTES_HERRAMIENTAS_KALI_VALIDAS and h not in herramientas:
            herramientas.append(h)

    if not herramientas:
        herramientas = ["nmap", "nikto", "nuclei"]

    return herramientas


def scorecard_proponentes_label_herramientas_kali(herramientas):
    labels = {
        "nmap": "Nmap",
        "whatweb": "WhatWeb",
        "nikto": "Nikto",
        "testssl": "testssl",
        "nuclei": "Nuclei",
        "zap": "OWASP ZAP Full Scan"
    }

    return ", ".join(labels.get(h, h) for h in herramientas or [])

# ============================================================
# PERMISOS - SCORECARD PROPONENTES / TERCEROS
# ============================================================

SCORECARD_PROPONENTES_PERMISO = "Security Scorecard de Terceros"


def scorecard_proponentes_user_permiso():
    user = User.query.get(session.get("user_id"))

    if not user:
        return None, False, False

    if user.role == "admin":
        return user, True, False

    if user.role == "auditor":
        return user, True, True

    if verificar_permiso(user, SCORECARD_PROPONENTES_PERMISO):
        return user, True, False

    return user, False, False


# ============================================================
# UTILIDADES PROPONENTES
# ============================================================

def scorecard_proponentes_run_dir(run_id, dominio):
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", dominio or "target")
    path = os.path.join(SCORECARD_PROPONENTES_UPLOAD_DIR, f"scorecard_proponente_{run_id}_{safe}")
    os.makedirs(path, exist_ok=True)
    return path


def scorecard_proponentes_output_file(run_dir, herramienta, ext="txt"):
    herramienta = re.sub(r"[^a-zA-Z0-9_.-]+", "_", herramienta or "output")
    return os.path.join(run_dir, f"{herramienta}.{ext}")


def scorecard_proponentes_set_progress(run_id, pct=None, stage=None, tool=None, estado=None, error=None):
    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    updates = []
    params = []

    if pct is not None:
        updates.append("progress_pct = ?")
        params.append(max(0, min(100, int(pct))))

    if stage is not None:
        updates.append("current_stage = ?")
        params.append(stage)

    if tool is not None:
        updates.append("current_tool = ?")
        params.append(tool)

    if estado is not None:
        updates.append("estado = ?")
        params.append(estado)

    if error is not None:
        updates.append("error_detalle = ?")
        params.append(error)

    if updates:
        params.append(run_id)
        cur.execute(f"""
            UPDATE scorecard_proponentes_runs
            SET {', '.join(updates)}
            WHERE id = ?
        """, params)
        conn.commit()

    conn.close()


def guardar_scorecard_proponentes_finding(run_id, item):
    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO scorecard_proponentes_findings
        (run_id, categoria, herramienta, control, estado, riesgo, severidad, score,
         evidencia, recomendacion, archivo_salida, detalle_json, fecha)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id,
        item.get("categoria"),
        item.get("herramienta"),
        item.get("control"),
        item.get("estado"),
        item.get("riesgo"),
        item.get("severidad"),
        float(item.get("score") or 0),
        item.get("evidencia"),
        item.get("recomendacion"),
        item.get("archivo_salida"),
        json.dumps(item, ensure_ascii=False),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def guardar_scorecard_proponentes_output(run_id, herramienta, comando, archivo_salida, exit_code, duracion):
    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO scorecard_proponentes_outputs
        (run_id, herramienta, comando, archivo_salida, exit_code, duracion_segundos, fecha)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id,
        herramienta,
        comando,
        archivo_salida,
        int(exit_code or 0),
        float(duracion or 0),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def guardar_scorecard_proponentes_incidente(run_id, proponente_nombre, dominio, item):
    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO scorecard_proponentes_incidents
        (run_id, proponente_nombre, dominio, fuente, titulo, url,
         fecha_incidente, severidad, descripcion, detalle_json, fecha_registro)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id,
        proponente_nombre,
        dominio,
        item.get("fuente"),
        item.get("titulo"),
        item.get("url"),
        item.get("fecha_incidente"),
        item.get("severidad"),
        item.get("descripcion"),
        json.dumps(item, ensure_ascii=False),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def guardar_scorecard_proponentes_darkweb_exposure(run_id, proponente_nombre, dominio, item):
    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO scorecard_proponentes_darkweb_exposures
        (run_id, proponente_nombre, dominio, fuente, tipo_exposicion,
         indicador, severidad, fecha, evidencia, recomendacion, url,
         credencial_confirmada, detalle_json, fecha_registro)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id,
        proponente_nombre,
        dominio,
        item.get("fuente"),
        item.get("tipo_exposicion"),
        item.get("indicador"),
        item.get("severidad"),
        item.get("fecha"),
        item.get("evidencia"),
        item.get("recomendacion"),
        item.get("url"),
        1 if item.get("credencial_confirmada") else 0,
        json.dumps(item, ensure_ascii=False),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()

# ============================================================
# DNS HEALTH PARAMETRIZABLE - PROPONENTES
# ============================================================

def evaluar_dns_health_proponentes_scorecard(dominio):
    findings = []

    dominio_original = limpiar_dominio_scorecard(dominio)
    dominio_base = obtener_dominio_base(dominio_original)

    registros_a = dns_any_scorecard(dominio_original, "A")

    registros_cname = []
    if not registros_a:
        registros_cname = dns_any_scorecard(dominio_original, "CNAME")

    registros_mx = dns_any_scorecard(dominio_base, "MX")
    registros_ns = dns_any_scorecard(dominio_base, "NS")

    txt_root = dns_txt_scorecard(dominio_base)
    txt_dmarc = dns_txt_scorecard(f"_dmarc.{dominio_base}")

    spf_ok = any("v=spf1" in x.lower() for x in txt_root)
    dmarc_ok = any("v=dmarc1" in x.lower() for x in txt_dmarc)

    dmarc_policy = ""
    for item in txt_dmarc:
        low = item.lower()
        if "p=reject" in low:
            dmarc_policy = "reject"
        elif "p=quarantine" in low:
            dmarc_policy = "quarantine"
        elif "p=none" in low:
            dmarc_policy = "none"

    scores_componentes = []

    def add(control, estado, riesgo, puntaje, evidencia, recomendacion, regla):
        scores_componentes.append(float(puntaje or 0))
        findings.append({
            "categoria": "DNS Health",
            "herramienta": "DNS Resolver",
            "control": control,
            "estado": estado,
            "riesgo": riesgo,
            "severidad": riesgo,
            "score": puntaje,
            "evidencia": evidencia,
            "recomendacion": recomendacion,
            "detalle": {
                "regla_calculo": regla,
                "modelo_score": "DNS Health parametrizable por control: A/CNAME, MX, NS, SPF y DMARC."
            }
        })

    if registros_a:
        puntaje = scorecard_proponentes_get_param("dns_score_a_ok", 100)
        add("Registro A", "OK", "Bajo", puntaje,
            f"{dominio_original}: " + ", ".join(registros_a[:8]),
            "Mantener monitoreo de resolución pública.",
            f"Registro A detectado → Score {puntaje}")
    elif registros_cname:
        puntaje = scorecard_proponentes_get_param("dns_score_a_ok", 100)
        add("Registro A/CNAME", "OK por CNAME", "Bajo", puntaje,
            f"{dominio_original} apunta por CNAME a: " + ", ".join(registros_cname[:8]),
            "Mantener monitoreo de resolución pública y destino CNAME autorizado.",
            f"Registro CNAME detectado → Score {puntaje}")
    else:
        puntaje = scorecard_proponentes_get_param("dns_score_a_no_detectado", 0)
        add("Registro A", "No detectado", "Alto", puntaje,
            f"No se encontraron registros A ni CNAME para {dominio_original}.",
            "Validar publicación DNS del dominio o subdominio evaluado.",
            f"Registro A/CNAME no detectado → Score {puntaje}")

    if registros_mx:
        puntaje = scorecard_proponentes_get_param("dns_score_mx_ok", 100)
        add("MX", "OK", "Bajo", puntaje,
            f"{dominio_base}: " + ", ".join(registros_mx[:8]),
            "Mantener proveedores MX autorizados.",
            f"MX detectado → Score {puntaje}")
    else:
        puntaje = scorecard_proponentes_get_param("dns_score_mx_no_detectado", 70)
        add("MX", "No detectado en dominio base", "Bajo", puntaje,
            f"No se encontraron registros MX para {dominio_base}. Esto puede ser aceptable si el dominio no recibe correo.",
            "Confirmar si el proveedor usa este dominio para correo. Si lo usa, configurar MX.",
            f"MX no detectado → Score {puntaje}")

    if registros_ns:
        puntaje = scorecard_proponentes_get_param("dns_score_ns_ok", 100)
        add("NS", "OK", "Bajo", puntaje,
            f"{dominio_base}: " + ", ".join(registros_ns[:8]),
            "Mantener gobierno sobre la administración DNS.",
            f"NS detectado → Score {puntaje}")
    else:
        puntaje = scorecard_proponentes_get_param("dns_score_ns_no_detectado", 0)
        add("NS", "No detectado en dominio base", "Medio", puntaje,
            f"No se encontraron registros NS para {dominio_base}.",
            "Validar delegación DNS del dominio base.",
            f"NS no detectado → Score {puntaje}")

    if spf_ok:
        puntaje = scorecard_proponentes_get_param("dns_score_spf_ok", 100)
        add("SPF", "OK", "Bajo", puntaje,
            f"Se detectó registro SPF en {dominio_base}.",
            "Evitar configuraciones demasiado permisivas como +all.",
            f"SPF detectado → Score {puntaje}")
    else:
        puntaje = scorecard_proponentes_get_param("dns_score_spf_no_configurado", 0)
        add("SPF", "No configurado en dominio base", "Alto", puntaje,
            f"No se encontró TXT con v=spf1 en {dominio_base}.",
            "Configurar SPF para mitigar spoofing si el dominio envía correo.",
            f"SPF no configurado → Score {puntaje}")

    if not dmarc_ok:
        puntaje = scorecard_proponentes_get_param("dns_score_dmarc_no_configurado", 0)
        add("DMARC", "No configurado en dominio base", "Alto", puntaje,
            f"No se encontró _dmarc.{dominio_base}.",
            "Configurar DMARC con política gradual.",
            f"DMARC no configurado → Score {puntaje}")
    elif dmarc_policy == "none":
        puntaje = scorecard_proponentes_get_param("dns_score_dmarc_p_none", 70)
        add("DMARC", "Configurado p=none", "Medio", puntaje,
            f"DMARC existe en _dmarc.{dominio_base}, pero está en modo monitoreo.",
            "Avanzar gradualmente a quarantine o reject.",
            f"DMARC p=none → Score {puntaje}")
    else:
        puntaje = scorecard_proponentes_get_param("dns_score_dmarc_ok", 100)
        add("DMARC", "OK", "Bajo", puntaje,
            f"Política DMARC en _dmarc.{dominio_base}: {dmarc_policy or 'definida'}.",
            "Mantener monitoreo DMARC.",
            f"DMARC enforce detectado → Score {puntaje}")

    score = round(sum(scores_componentes) / len(scores_componentes), 2) if scores_componentes else 0
    return max(0, min(100, score)), findings

# ============================================================
# INCIDENT HISTORY PROPONENTES
# ============================================================

def evaluar_incident_history_proponentes_scorecard(run_id, proponente_nombre, dominio):
    incidentes = consultar_incidentes_osint_scorecard(proponente_nombre, dominio)

    for item in incidentes:
        guardar_scorecard_proponentes_incidente(run_id, proponente_nombre, dominio, item)

    total = len(incidentes)
    score, riesgo = scorecard_score_incidentes(incidentes)

    evidencia = (
        f"Se identificaron {total} referencias públicas o históricas asociadas a incidentes, brechas, ransomware, leaks o ataques."
        if total else
        "No se identificaron referencias públicas relevantes de brechas o incidentes en la consulta OSINT básica."
    )

    guardar_scorecard_proponentes_finding(run_id, {
        "categoria": "Incident History",
        "herramienta": "Catálogo histórico + OSINT Público",
        "control": "Brechas e incidentes de seguridad",
        "estado": "Con hallazgos" if total else "Sin hallazgos",
        "riesgo": riesgo,
        "severidad": riesgo,
        "score": score,
        "evidencia": evidencia,
        "recomendacion": (
            "Validar manualmente las fuentes públicas encontradas, solicitar explicación formal al proponente "
            "y pedir evidencia de remediación, mejoras de seguridad y controles posteriores al incidente."
            if total else
            "Mantener monitoreo periódico de noticias e incidentes públicos."
        )
    })

    return score, riesgo, total

def scorecard_proponentes_score_hacker_chatter_por_severidad(
    total_hallazgos,
    credencial_confirmada=False,
    severidad_max="Bajo"
):
    total_hallazgos = int(total_hallazgos or 0)
    severidad_max = (severidad_max or "Bajo").strip()

    if total_hallazgos <= 0:
        return (
            scorecard_proponentes_get_param("darkweb_score_sin_hallazgos", 100),
            "Bajo",
            "Sin hallazgos de riesgo. Score parametrizado aplicado."
        )

    if credencial_confirmada:
        return (
            scorecard_proponentes_get_param("darkweb_score_credenciales_confirmadas", 20),
            "Crítico",
            "Credenciales confirmadas detectadas. Se aplica score crítico parametrizado."
        )

    if severidad_max in ["Crítico", "Critico", "Critical"]:
        return (
            scorecard_proponentes_get_param("darkweb_score_critico", 25),
            "Crítico",
            "Se detectó severidad máxima Crítica. Score parametrizado aplicado."
        )

    if severidad_max in ["Alto", "Alta", "High"]:
        return (
            scorecard_proponentes_get_param("darkweb_score_alto", 55),
            "Alto",
            "Se detectó severidad máxima Alta. Score parametrizado aplicado."
        )

    if severidad_max in ["Medio", "Media", "Medium"]:
        return (
            scorecard_proponentes_get_param("darkweb_score_medio", 75),
            "Medio",
            "Se detectó severidad máxima Media. Score parametrizado aplicado."
        )

    return (
        scorecard_proponentes_get_param("darkweb_score_bajo", 90),
        "Bajo",
        "Solo se detectaron hallazgos de severidad Baja. Score parametrizado aplicado."
    )

# ============================================================
# HACKER CHATTER / EXPOSURE INTELLIGENCE PROPONENTES
# SCORING POR SEVERIDAD MÁXIMA
# ============================================================

def evaluar_hacker_chatter_proponentes_scorecard(run_id, proponente_nombre, dominio, ip):
    scorecard_proponentes_set_progress(
        run_id,
        pct=30,
        stage="Consultando Hacker Chatter / Exposure Intelligence",
        tool="OSINT / APIs Proponentes"
    )

    hallazgos = []

    # ============================================================
    # LeakCheck independiente Proponentes
    # ============================================================
    try:
        api_key_leakcheck = scorecard_proponentes_get_api_key("leakcheck")

        if api_key_leakcheck:
            dominio_base = obtener_dominio_base(dominio)

            resp = requests.get(
                f"https://leakcheck.io/api/v2/query/{dominio_base}",
                params={"type": "domain", "limit": 100},
                headers={"Accept": "application/json", "X-API-Key": api_key_leakcheck},
                timeout=25
            )

            if resp.status_code == 200:
                data = resp.json() or {}
                found, results = scorecard_leakcheck_extraer_resultados(data)

                if found > 0:
                    hallazgos.append({
                        "fuente": "LeakCheck API - Proponentes",
                        "tipo_exposicion": "Credenciales / identidades filtradas",
                        "indicador": f"{dominio_base} - {found} registros encontrados",
                        "severidad": "Crítico" if found > 10 else "Alto" if found > 2 else "Medio",
                        "fecha": datetime.now().strftime("%Y-%m-%d"),
                        "evidencia": f"LeakCheck reportó {found} registros reales asociados al dominio {dominio_base}.",
                        "recomendacion": "Solicitar al proponente investigación formal, rotación de credenciales, MFA obligatorio y evidencia de remediación.",
                        "url": "https://leakcheck.io/",
                        "credencial_confirmada": True,
                        "detalle": {
                            "found": found,
                            "raw_passwords_omitted": True,
                            "penaliza_score": True,
                            "fuente_valida": True
                        }
                    })

            elif resp.status_code in [400, 401, 403, 422, 429]:
                hallazgos.append({
                    **scorecard_api_error_item(
                        "LeakCheck API - Proponentes",
                        f"HTTP {resp.status_code}: {resp.text[:300]}"
                    ),
                    "detalle": {
                        "no_penaliza_score": True,
                        "api_error": True,
                        "fuente_valida": False
                    }
                })

    except Exception as e:
        hallazgos.append({
            **scorecard_api_error_item("LeakCheck API - Proponentes", repr(e)),
            "detalle": {
                "no_penaliza_score": True,
                "api_error": True,
                "fuente_valida": False
            }
        })

    # ============================================================
    # HIBP independiente Proponentes
    # ============================================================
    try:
        api_key_hibp = scorecard_proponentes_get_api_key("hibp")

        if api_key_hibp:
            dominio_base = obtener_dominio_base(dominio)

            headers = {
                "hibp-api-key": api_key_hibp,
                "User-Agent": "GRAC-SGSI-Scorecard-Proponentes/1.0",
                "Accept": "application/json"
            }

            resp = requests.get(
                f"https://haveibeenpwned.com/api/v3/breacheddomain/{dominio_base}",
                params={"truncateResponse": "false"},
                headers=headers,
                timeout=25
            )

            if resp.status_code == 200:
                data = resp.json() or {}
                total_accounts = len(data.keys()) if isinstance(data, dict) else 0

                if total_accounts > 0:
                    hallazgos.append({
                        "fuente": "Have I Been Pwned API - Proponentes",
                        "tipo_exposicion": "Cuentas del dominio en brechas",
                        "indicador": f"{dominio_base} - {total_accounts} cuentas afectadas",
                        "severidad": "Crítico" if total_accounts > 10 else "Alto" if total_accounts > 2 else "Medio",
                        "fecha": datetime.now().strftime("%Y-%m-%d"),
                        "evidencia": f"HIBP reportó {total_accounts} cuentas reales del dominio {dominio_base} asociadas a brechas.",
                        "recomendacion": "Exigir al proponente revisión de cuentas afectadas, rotación de credenciales, MFA y detección de password reuse.",
                        "url": "https://haveibeenpwned.com/",
                        "credencial_confirmada": True,
                        "detalle": {
                            "total_accounts": total_accounts,
                            "raw_accounts_masked": True,
                            "penaliza_score": True,
                            "fuente_valida": True
                        }
                    })

            elif resp.status_code == 404:
                pass

            elif resp.status_code in [400, 401, 403, 429]:
                hallazgos.append({
                    **scorecard_api_error_item(
                        "Have I Been Pwned API - Proponentes",
                        f"HTTP {resp.status_code}: dominio no verificado, API key inválida, cuota o rate limit."
                    ),
                    "detalle": {
                        "no_penaliza_score": True,
                        "api_error": True,
                        "fuente_valida": False
                    }
                })

    except Exception as e:
        hallazgos.append({
            **scorecard_api_error_item("Have I Been Pwned API - Proponentes", repr(e)),
            "detalle": {
                "no_penaliza_score": True,
                "api_error": True,
                "fuente_valida": False
            }
        })

    # ============================================================
    # Shodan independiente Proponentes
    # ============================================================
    try:
        api_key_shodan = scorecard_proponentes_get_api_key("shodan")

        if api_key_shodan and ip:
            resp = requests.get(
                f"https://api.shodan.io/shodan/host/{ip}",
                params={"key": api_key_shodan},
                timeout=25
            )

            if resp.status_code == 200:
                data = resp.json() or {}

                ports = data.get("ports") or []
                vulns = data.get("vulns") or {}
                hostnames = data.get("hostnames") or []

                cves = []

                if isinstance(vulns, dict):
                    for cve, detail in vulns.items():
                        cvss = 0
                        try:
                            if isinstance(detail, dict):
                                cvss = float(detail.get("cvss") or 0)
                        except Exception:
                            cvss = 0

                        cves.append({
                            "cve": cve,
                            "cvss": cvss
                        })

                critical_cves = [x for x in cves if x["cvss"] >= 9]
                high_cves = [x for x in cves if 7 <= x["cvss"] < 9]

                if critical_cves:
                    severidad = "Crítico"
                elif high_cves or len(cves) > 0:
                    severidad = "Alto"
                else:
                    severidad = "Bajo"

                if cves:
                    hallazgos.append({
                        "fuente": "Shodan API - Proponentes",
                        "tipo_exposicion": "CVEs / servicios vulnerables expuestos",
                        "indicador": f"{ip} - CVEs: {len(cves)} - Puertos: {', '.join(str(p) for p in ports[:20])}",
                        "severidad": severidad,
                        "fecha": datetime.now().strftime("%Y-%m-%d"),
                        "evidencia": f"Shodan reportó {len(cves)} CVEs reales para la IP {ip}.",
                        "recomendacion": "Validar exposición de servicios, aplicar parches, cerrar puertos innecesarios y corregir CVEs.",
                        "url": f"https://www.shodan.io/host/{ip}",
                        "credencial_confirmada": False,
                        "detalle": {
                            "ip": ip,
                            "ports": ports,
                            "hostnames": hostnames,
                            "cves": cves[:50],
                            "critical_cves": critical_cves[:20],
                            "high_cves": high_cves[:20],
                            "org": data.get("org"),
                            "isp": data.get("isp"),
                            "country": data.get("country_name"),
                            "penaliza_score": True,
                            "fuente_valida": True
                        }
                    })

                elif ports:
                    hallazgos.append({
                        "fuente": "Shodan API - Proponentes",
                        "tipo_exposicion": "Servicios observados sin CVEs",
                        "indicador": f"{ip} - puertos observados: {', '.join(str(p) for p in ports[:20])}",
                        "severidad": "Bajo",
                        "fecha": datetime.now().strftime("%Y-%m-%d"),
                        "evidencia": f"Shodan reportó {len(ports)} puertos observados, pero sin CVEs asociadas.",
                        "recomendacion": "Validar que los servicios expuestos sean esperados. No penaliza score por ausencia de CVEs.",
                        "url": f"https://www.shodan.io/host/{ip}",
                        "credencial_confirmada": False,
                        "detalle": {
                            "ip": ip,
                            "ports": ports,
                            "hostnames": hostnames,
                            "cves": [],
                            "no_penaliza_score": True,
                            "fuente_valida": True,
                            "informativo": True
                        }
                    })

            elif resp.status_code == 404:
                pass

            elif resp.status_code in [400, 401, 403, 429]:
                hallazgos.append({
                    **scorecard_api_error_item(
                        "Shodan API - Proponentes",
                        f"HTTP {resp.status_code}: API key inválida, sin créditos o rate limit."
                    ),
                    "detalle": {
                        "no_penaliza_score": True,
                        "api_error": True,
                        "fuente_valida": False
                    }
                })

    except Exception as e:
        hallazgos.append({
            **scorecard_api_error_item("Shodan API - Proponentes", repr(e)),
            "detalle": {
                "no_penaliza_score": True,
                "api_error": True,
                "fuente_valida": False
            }
        })

    # ============================================================
    # OSINT público informativo
    # ============================================================
    for fuente_func, nombre_fuente in [
        (consultar_hacker_chatter_gdelt_scorecard, "GDELT"),
        (consultar_certificados_ct_scorecard, "crt.sh"),
        (consultar_github_exposure_scorecard, "GitHub OSINT"),
    ]:
        try:
            if nombre_fuente == "GDELT":
                items = fuente_func(proponente_nombre, dominio)
            elif nombre_fuente == "GitHub OSINT":
                items = fuente_func(proponente_nombre, dominio)
            else:
                items = fuente_func(dominio)

            for item in items or []:
                detalle = item.get("detalle") if isinstance(item.get("detalle"), dict) else {}
                detalle["no_penaliza_score"] = True
                detalle["informativo_osint"] = True
                detalle["fuente_valida"] = True
                item["detalle"] = detalle
                item["credencial_confirmada"] = False
                hallazgos.append(item)

        except Exception as e:
            print(f"Error {nombre_fuente} proponentes:", repr(e))

    # ============================================================
    # Clasificación final por severidad máxima
    # ============================================================

    severidad_orden = {
        "Bajo": 1,
        "Medio": 2,
        "Alto": 3,
        "Crítico": 4,
        "Critico": 4
    }

    severidad_max = "Bajo"
    credencial_confirmada = False
    total_riesgo = 0
    total_info = 0
    total_cves = 0
    fuentes_penalizadas = []
    fuentes_informativas = []

    for item in hallazgos:
        detalle = item.get("detalle") or {}

        penaliza = bool(detalle.get("penaliza_score"))
        no_penaliza = bool(detalle.get("no_penaliza_score"))

        if penaliza and not no_penaliza:
            total_riesgo += 1
            fuentes_penalizadas.append(item.get("fuente") or "Fuente no identificada")

            sev = item.get("severidad") or "Bajo"
            if severidad_orden.get(sev, 0) > severidad_orden.get(severidad_max, 0):
                severidad_max = sev

            if item.get("credencial_confirmada"):
                credencial_confirmada = True

            try:
                if isinstance(detalle, dict):
                    total_cves += len(detalle.get("cves") or [])
            except Exception:
                pass
        else:
            total_info += 1
            fuentes_informativas.append(item.get("fuente") or "Fuente informativa")

        guardar_scorecard_proponentes_darkweb_exposure(
            run_id,
            proponente_nombre,
            dominio,
            item
        )

    score, riesgo, regla_score = scorecard_proponentes_score_hacker_chatter_por_severidad(
        total_riesgo,
        credencial_confirmada=credencial_confirmada,
        severidad_max=severidad_max
    )

    estado = "Con hallazgos de riesgo" if total_riesgo else "Sin hallazgos de riesgo"

    evidencia = (
        f"Se identificaron {total_riesgo} hallazgos válidos que penalizan el score "
        f"y {total_info} hallazgos informativos que no afectan el cálculo. "
        f"Severidad máxima detectada: {severidad_max}. "
        f"Regla aplicada: {regla_score} "
        f"Fuentes que penalizan: {', '.join(sorted(set(fuentes_penalizadas))) if fuentes_penalizadas else 'Ninguna'}."
    )

    recomendacion = (
        "Validar hallazgos con el proponente, solicitar evidencias de remediación, rotación de credenciales, "
        "MFA, hardening, cierre de servicios expuestos y confirmación formal de contención."
        if total_riesgo else
        "No se encontraron hallazgos válidos que afecten el score. Mantener monitoreo periódico."
    )

    guardar_scorecard_proponentes_finding(run_id, {
        "categoria": "Hacker Chatter / Exposure Intelligence",
        "herramienta": "LeakCheck + HIBP + Shodan + GDELT + crt.sh + GitHub",
        "control": "Credenciales, identidades, brechas, CVEs, chatter y superficie expuesta",
        "estado": estado,
        "riesgo": riesgo,
        "severidad": riesgo,
        "score": score,
        "evidencia": evidencia,
        "recomendacion": recomendacion,
        "detalle": {
            "total_hallazgos_riesgo": total_riesgo,
            "total_hallazgos_info": total_info,
            "severidad_max": severidad_max,
            "credencial_confirmada": credencial_confirmada,
            "total_cves": total_cves,
            "fuentes_penalizadas": list(sorted(set(fuentes_penalizadas))),
            "fuentes_informativas": list(sorted(set(fuentes_informativas))),
            "api_scope": "proponentes_independiente",
            "regla_calculo": regla_score,
            "modelo_score": "Scoring por severidad máxima: Sin hallazgos, Bajo, Medio, Alto, Crítico o Credenciales confirmadas."
        }
    })

    scorecard_proponentes_set_progress(
        run_id,
        pct=40,
        stage="Hacker Chatter / Exposure Intelligence finalizado",
        tool=None
    )

    return score, riesgo, total_riesgo, credencial_confirmada

# ============================================================
# KALI SCAN INDEPENDIENTE PROPONENTES
# ============================================================

# ============================================================
# KALI SCORECARD PROPONENTES USANDO EL MISMO MOTOR DE
# REGISTRO DE VULNERABILIDADES
# ============================================================

def scorecard_proponentes_map_severidad_vuln(sev):
    sev = (sev or "").strip()

    if sev in ["Crítica", "Critica", "Critical"]:
        return "Crítico"

    if sev in ["Alta", "High"]:
        return "Alto"

    if sev in ["Media", "Medium"]:
        return "Medio"

    return "Bajo"


def scorecard_proponentes_score_kali_desde_findings(findings):
    criticas = 0
    altas = 0
    medias = 0
    bajas = 0

    for f in findings:
        sev = (f.severidad or "").strip()

        if sev in ["Crítica", "Critica"]:
            criticas += 1
        elif sev == "Alta":
            altas += 1
        elif sev == "Media":
            medias += 1
        else:
            bajas += 1

    descuento = (criticas * 25) + (altas * 15) + (medias * 7) + (bajas * 3)
    score = 100 - min(100, descuento)

    return max(0, min(100, score)), {
        "criticas": criticas,
        "altas": altas,
        "medias": medias,
        "bajas": bajas,
        "total": len(findings)
    }


def scorecard_proponentes_copiar_findings_vuln(scorecard_run_id, vuln_run_id):
    findings = VulnerabilityScanFinding.query.filter_by(
        run_id=vuln_run_id
    ).order_by(VulnerabilityScanFinding.id.asc()).all()

    for f in findings:
        riesgo = scorecard_proponentes_map_severidad_vuln(f.severidad)

        guardar_scorecard_proponentes_finding(scorecard_run_id, {
            "categoria": "Kali Linux Scan",
            "herramienta": f.fuente or "Kali Linux",
            "control": f.titulo or "Hallazgo técnico",
            "estado": "Detectado",
            "riesgo": riesgo,
            "severidad": riesgo,
            "score": (
                20 if riesgo == "Crítico"
                else 45 if riesgo == "Alto"
                else 70 if riesgo == "Medio"
                else 100
            ),
            "evidencia": f.evidencia or f.descripcion or "Hallazgo detectado por el motor de vulnerabilidades.",
            "recomendacion": f.recomendacion_base or "Validar el hallazgo, aplicar remediación y repetir el escaneo.",
            "archivo_salida": "",
            "detalle": {
                "vulnerability_scan_run_id": vuln_run_id,
                "vulnerability_finding_id": f.id,
                "fuente_original": f.fuente,
                "titulo_original": f.titulo,
                "severidad_original": f.severidad,
                "cvss": f.cvss,
                "cve": f.cve,
                "puerto": f.puerto,
                "protocolo": f.protocolo,
                "servicio": f.servicio
            }
        })

    return findings

def scorecard_proponentes_sync_from_vuln_run(scorecard_run_id, vuln_run_id, min_pct=45, max_pct=95):
    vuln_run = VulnerabilityScanRun.query.get(vuln_run_id)
    if not vuln_run:
        return

    vuln_pct = int(vuln_run.progress_pct or 0)
    mapped_pct = min_pct + int((vuln_pct / 100) * (max_pct - min_pct))

    stage = vuln_run.current_stage or "Ejecutando escaneo Kali Linux"
    tool = vuln_run.current_tool or "Kali Linux"

    if tool == "dispatcher":
        tool = "Inicializando"

    scorecard_proponentes_set_progress(
        scorecard_run_id,
        pct=mapped_pct,
        stage=stage,
        tool=tool,
        estado="ejecutando"
    )


def ejecutar_scan_web_scorecard_proponentes_sin_whatweb(
    run,
    cfg,
    run_dir,
    crear_vulns=False,
    crear_planes=False,
    scorecard_run_id=None
):
    target = normalizar_target_para_scan(run.target)
    host = extraer_host_de_target(target)
    logs = []

    try:
        herramientas = json.loads(run.herramientas or "[]")
    except Exception:
        herramientas = []

    herramientas = scorecard_proponentes_normalizar_herramientas_kali(herramientas)

    # =========================
    # NMAP
    # =========================
    if "nmap" in herramientas:
        if scan_check_cancel(run.id):
            scan_mark_stopped(run.id)
            return logs

        scan_set_progress(run.id, pct=10, stage="Ejecutando Nmap", tool="nmap")
        db.session.commit()

        if scorecard_run_id:
            scorecard_proponentes_sync_from_vuln_run(scorecard_run_id, run.id)

        if host:
            res_nmap = ejecutar_nmap(run.id, cfg, host, run_dir)
            logs.append(f"[NMAP]\nSTDOUT:\n{res_nmap['stdout']}\nSTDERR:\n{res_nmap['stderr']}\n")

            findings = parse_nmap_xml(run_dir)
            guardar_findings_y_sincronizar(run, findings, run_dir, crear_vulns, crear_planes)

    # =========================
    # WHATWEB
    # =========================
    if "whatweb" in herramientas:
        if scan_check_cancel(run.id):
            scan_mark_stopped(run.id)
            return logs

        scan_set_progress(run.id, pct=25, stage="Ejecutando WhatWeb", tool="whatweb")
        db.session.commit()

        if scorecard_run_id:
            scorecard_proponentes_sync_from_vuln_run(scorecard_run_id, run.id)

        res_whatweb = ejecutar_whatweb(run.id, cfg, target, run_dir)
        logs.append(f"[WHATWEB]\nSTDOUT:\n{res_whatweb['stdout']}\nSTDERR:\n{res_whatweb['stderr']}\n")

        findings = parse_txt_findings_generic(
            scan_output_file(run_dir, "whatweb_scan", "txt"),
            "whatweb"
        )
        guardar_findings_y_sincronizar(run, findings, run_dir, crear_vulns, crear_planes)

    # =========================
    # NIKTO
    # =========================
    if "nikto" in herramientas:
        if scan_check_cancel(run.id):
            scan_mark_stopped(run.id)
            return logs

        scan_set_progress(run.id, pct=40, stage="Ejecutando Nikto", tool="nikto")
        db.session.commit()

        if scorecard_run_id:
            scorecard_proponentes_sync_from_vuln_run(scorecard_run_id, run.id)

        res_nikto = ejecutar_nikto(run.id, cfg, target, run_dir)
        logs.append(f"[NIKTO]\nSTDOUT:\n{res_nikto['stdout']}\nSTDERR:\n{res_nikto['stderr']}\n")

        findings = parse_txt_findings_generic(
            scan_output_file(run_dir, "nikto_scan", "txt"),
            "nikto"
        )
        guardar_findings_y_sincronizar(run, findings, run_dir, crear_vulns, crear_planes)

    # =========================
    # TESTSSL
    # =========================
    if "testssl" in herramientas:
        if scan_check_cancel(run.id):
            scan_mark_stopped(run.id)
            return logs

        ssl_target = target

        if ssl_target.startswith("http://"):
            ssl_target = "https://" + ssl_target.replace("http://", "", 1)

        scan_set_progress(run.id, pct=55, stage="Ejecutando testssl", tool="testssl")
        db.session.commit()

        if scorecard_run_id:
            scorecard_proponentes_sync_from_vuln_run(scorecard_run_id, run.id)

        res_testssl = ejecutar_testssl(run.id, cfg, ssl_target, run_dir)
        logs.append(f"[TESTSSL]\nSTDOUT:\n{res_testssl['stdout']}\nSTDERR:\n{res_testssl['stderr']}\n")

        findings = parse_txt_findings_generic(
            scan_output_file(run_dir, "testssl_scan", "txt"),
            "testssl"
        )
        guardar_findings_y_sincronizar(run, findings, run_dir, crear_vulns, crear_planes)

    # =========================
    # NUCLEI
    # =========================
    if "nuclei" in herramientas:
        if scan_check_cancel(run.id):
            scan_mark_stopped(run.id)
            return logs

        scan_set_progress(run.id, pct=70, stage="Ejecutando Nuclei", tool="nuclei")
        db.session.commit()

        if scorecard_run_id:
            scorecard_proponentes_sync_from_vuln_run(scorecard_run_id, run.id)

        res_nuclei = ejecutar_nuclei(run.id, cfg, target, run_dir)
        logs.append(f"[NUCLEI]\nSTDOUT:\n{res_nuclei['stdout']}\nSTDERR:\n{res_nuclei['stderr']}\n")

        findings = parse_nuclei_jsonl(run_dir)
        guardar_findings_y_sincronizar(run, findings, run_dir, crear_vulns, crear_planes)

    # =========================
    # OWASP ZAP FULL SCAN
    # =========================
    if "zap" in herramientas:
        if scan_check_cancel(run.id):
            scan_mark_stopped(run.id)
            return logs

        scan_set_progress(run.id, pct=85, stage="Ejecutando OWASP ZAP Full Scan", tool="zap")
        db.session.commit()

        if scorecard_run_id:
            scorecard_proponentes_sync_from_vuln_run(scorecard_run_id, run.id)

        res_zap = ejecutar_zap(run.id, cfg, target, run_dir)
        logs.append(f"[OWASP_ZAP_FULL_SCAN]\nSTDOUT:\n{res_zap['stdout']}\nSTDERR:\n{res_zap['stderr']}\n")

        findings = parse_zap_findings(run_dir)
        guardar_findings_y_sincronizar(run, findings, run_dir, crear_vulns, crear_planes)

    if scorecard_run_id:
        scorecard_proponentes_sync_from_vuln_run(scorecard_run_id, run.id)

    return logs


def ejecutar_full_scan_scorecard_proponentes_sin_whatweb(run_id, scorecard_run_id, crear_vulns=False, crear_planes=False):
    run = VulnerabilityScanRun.query.get_or_404(run_id)

    run.estado = "ejecutando"
    run.fecha_inicio = datetime.utcnow()
    run.progress_pct = 1
    run.current_tool = "Inicializando"
    run.current_stage = "Preparando herramientas de escaneo"
    run.cancel_requested = False
    run.stopped_by_user = False
    run.active_pid = None
    run.active_command = None
    db.session.commit()

    scorecard_proponentes_sync_from_vuln_run(scorecard_run_id, run.id)

    run_dir = scan_run_dir(run.id, run.target)
    log_path = scan_output_file(run_dir, "scan_log", "txt")

    try:
        cfg = _scan_cfg()

        faltantes = validar_herramientas_scan(cfg)
        if faltantes:
            raise RuntimeError("Herramientas no encontradas: " + " | ".join(faltantes))

        if run.target_type == "url":
            logs = ejecutar_scan_web_scorecard_proponentes_sin_whatweb(
                run,
                cfg,
                run_dir,
                crear_vulns,
                crear_planes,
                scorecard_run_id=scorecard_run_id
            )
        else:
            logs = ejecutar_scan_ip(
                run,
                cfg,
                run_dir,
                crear_vulns,
                crear_planes
            )

        scorecard_proponentes_sync_from_vuln_run(scorecard_run_id, run.id)

        run = VulnerabilityScanRun.query.get(run.id)

        if run.estado == "detenido" or run.cancel_requested:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("\n\n".join(logs or []))

            run.archivo_log = log_path
            run.salida_consola = ("\n\n".join(logs or []))[:20000]
            run.current_stage = "Escaneo detenido"
            run.current_tool = None
            run.active_pid = None
            run.active_command = None
            db.session.commit()

            scorecard_proponentes_set_progress(
                scorecard_run_id,
                pct=99,
                stage="Escaneo Kali detenido",
                tool=None,
                estado="error",
                error="Escaneo detenido por el usuario."
            )

            return {"ok": False, "stopped": True}

        scan_set_progress(run.id, pct=95, stage="Consolidando resultados", tool="sync")
        scorecard_proponentes_sync_from_vuln_run(scorecard_run_id, run.id)

        with open(log_path, "w", encoding="utf-8") as f:
            f.write("\n\n".join(logs or []))

        run = VulnerabilityScanRun.query.get(run.id)
        run.archivo_log = log_path
        run.salida_consola = ("\n\n".join(logs or []))[:20000]

        resumir_hallazgos_run(run)

        run.estado = "finalizado"
        run.progress_pct = 100
        run.current_stage = "Escaneo Kali finalizado"
        run.current_tool = None
        run.active_pid = None
        run.active_command = None
        run.fecha_fin = datetime.utcnow()
        db.session.commit()

        scorecard_proponentes_sync_from_vuln_run(scorecard_run_id, run.id)

        try:
            pdf_path = build_vulnerability_scan_pdf(run.id)
            run.archivo_reporte_pdf = pdf_path
            db.session.commit()
        except Exception:
            pass

        return {
            "ok": True,
            "findings": run.total_hallazgos or 0,
            "vulns": run.created_vulns or 0,
            "planes": run.created_plans or 0
        }

    except Exception as e:
        tb = traceback.format_exc()

        run = VulnerabilityScanRun.query.get(run_id)
        if run:
            run.estado = "error"
            run.error_detalle = f"{str(e)}\n\n{tb}"
            run.fecha_fin = datetime.utcnow()
            run.current_stage = "Error en la ejecución"
            run.current_tool = None
            run.active_pid = None
            run.active_command = None
            run.salida_consola = ((run.salida_consola or "") + "\n\n[TRACEBACK]\n" + tb)[-20000:]
            run.archivo_log = log_path if os.path.exists(os.path.dirname(log_path)) else None
            db.session.commit()

        scorecard_proponentes_set_progress(
            scorecard_run_id,
            pct=100,
            stage="Error ejecutando Kali",
            tool=None,
            estado="error",
            error=tb
        )

        return {"ok": False, "error": str(e)}

def ejecutar_scorecard_proponentes_kali_independiente(run_id, dominio):
    scorecard_proponentes_set_progress(
        run_id,
        pct=45,
        stage="Inicializando escaneo Kali con herramientas seleccionadas",
        tool="Inicializando",
        estado="ejecutando"
    )

    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM scorecard_proponentes_runs
        WHERE id = ?
    """, (run_id,))

    scorecard_run = cur.fetchone()
    conn.close()

    if not scorecard_run:
        raise RuntimeError("Scorecard de Proponentes no encontrado.")

    herramientas_kali = []

    try:
        if "herramientas_kali" in scorecard_run.keys() and scorecard_run["herramientas_kali"]:
            herramientas_kali = json.loads(scorecard_run["herramientas_kali"] or "[]")
    except Exception:
        herramientas_kali = []

    if not herramientas_kali:
        try:
            resumen_tmp = json.loads(scorecard_run["resumen_json"] or "{}")
            herramientas_kali = resumen_tmp.get("herramientas_kali") or []
        except Exception:
            herramientas_kali = []

    herramientas_kali = scorecard_proponentes_normalizar_herramientas_kali(herramientas_kali)

    target = target_url_scorecard(dominio)
    target_type = detectar_tipo_objetivo(target)
    cfg = _scan_cfg()

    vuln_run = VulnerabilityScanRun(
        target=normalizar_target_para_scan(target) if target_type == "url" else target,
        target_type=target_type,
        scan_mode="scorecard_proponentes",
        scanner_mode=cfg.modo,
        estado="ejecutando",
        fecha_inicio=datetime.utcnow(),
        fecha_fin=None,
        ejecutado_por=scorecard_run["usuario"] or "Sistema",
        responsable_asignado=scorecard_run["usuario"] or "Sistema",
        progress_pct=1,
        current_stage="Encolando escaneo Scorecard de Terceros",
        current_tool="Inicializando",
        cancel_requested=False,
        stopped_by_user=False,
        findings_streamed=0,
        created_vulns=0,
        created_plans=0,
        herramientas=json.dumps(herramientas_kali, ensure_ascii=False)
    )

    db.session.add(vuln_run)
    db.session.commit()

    scorecard_proponentes_set_progress(
        run_id,
        pct=50,
        stage="Escaneo Kali iniciado con: " + scorecard_proponentes_label_herramientas_kali(herramientas_kali),
        tool="Kali Linux"
    )

    try:
        ejecutar_full_scan_scorecard_proponentes_sin_whatweb(
            vuln_run.id,
            run_id,
            crear_vulns=False,
            crear_planes=False
        )

        vuln_run = VulnerabilityScanRun.query.get(vuln_run.id)

        findings = scorecard_proponentes_copiar_findings_vuln(
            run_id,
            vuln_run.id
        )

        score_kali, resumen_kali = scorecard_proponentes_score_kali_desde_findings(findings)

        conn = get_scorecard_proponentes_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT score_dns, score_ip, score_incidentes, score_darkweb, resumen_json
            FROM scorecard_proponentes_runs
            WHERE id = ?
        """, (run_id,))

        row = cur.fetchone()

        score_dns = float(row["score_dns"] or 0) if row else 0
        score_ip = float(row["score_ip"] or 0) if row else 0
        score_incidentes = float(row["score_incidentes"] or 100) if row else 100
        score_darkweb = float(row["score_darkweb"] or 100) if row else 100

        score_total = scorecard_proponentes_calcular_total(
            score_dns,
            score_ip,
            score_kali,
            score_incidentes,
            score_darkweb,
            incluir_kali=True
        )

        nivel = nivel_riesgo_scorecard_proponentes(score_total)

        try:
            resumen_base = json.loads(row["resumen_json"] or "{}") if row else {}
        except Exception:
            resumen_base = {}

        resumen_final = {
            **resumen_base,
            "dns_score": score_dns,
            "ip_score": score_ip,
            "kali_score": score_kali,
            "kali_ejecutado": True,
            "kali_motor": "Registro de Vulnerabilidades",
            "herramientas_kali": herramientas_kali,
            "herramientas_kali_label": scorecard_proponentes_label_herramientas_kali(herramientas_kali),
            "vulnerability_scan_run_id": vuln_run.id,
            "incident_score": score_incidentes,
            "darkweb_score": score_darkweb,
            "score_total": score_total,
            "nivel_riesgo": nivel,
            "kali": resumen_kali
        }

        salida = vuln_run.salida_consola or ""

        cur.execute("""
            UPDATE scorecard_proponentes_runs
            SET score_kali = ?,
                score_total = ?,
                nivel_riesgo = ?,
                estado = ?,
                progress_pct = ?,
                current_stage = ?,
                current_tool = ?,
                resumen_json = ?,
                salida_consola = ?,
                fecha_fin = ?
            WHERE id = ?
        """, (
            score_kali,
            score_total,
            nivel,
            "finalizado",
            100,
            "Escaneo Kali finalizado con herramientas: " + scorecard_proponentes_label_herramientas_kali(herramientas_kali),
            None,
            json.dumps(resumen_final, ensure_ascii=False),
            salida[:25000],
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            run_id
        ))

        conn.commit()
        conn.close()

        guardar_scorecard_proponentes_output(
            run_id,
            "Registro de Vulnerabilidades",
            f"VulnerabilityScanRun #{vuln_run.id} | Herramientas: {scorecard_proponentes_label_herramientas_kali(herramientas_kali)}",
            vuln_run.archivo_log or "",
            0,
            0
        )

    except Exception as e:
        tb = traceback.format_exc()

        scorecard_proponentes_set_progress(
            run_id,
            pct=100,
            stage="Error ejecutando Kali con herramientas seleccionadas",
            tool=None,
            estado="error",
            error=tb
        )

        raise e


def scorecard_proponentes_kali_worker(run_id, dominio):
    with app.app_context():
        try:
            ejecutar_scorecard_proponentes_kali_independiente(run_id, dominio)
        except Exception:
            tb = traceback.format_exc()
            scorecard_proponentes_set_progress(
                run_id,
                pct=100,
                stage="Error en escaneo Kali de Proponentes usando Registro de Vulnerabilidades",
                tool=None,
                estado="error",
                error=tb
            )


# ============================================================
# APIs INDEPENDIENTES SCORECARD PROPONENTES
# ============================================================

def init_scorecard_proponentes_api_db():
    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS scorecard_proponentes_api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proveedor TEXT NOT NULL UNIQUE,
            api_key_encrypted TEXT,
            activo INTEGER DEFAULT 0,
            notas TEXT,
            actualizado_por TEXT,
            fecha_actualizacion TEXT NOT NULL
        )
    """)

    proveedores_default = [
        ("leakcheck", "LeakCheck API para Proponentes"),
        ("hibp", "Have I Been Pwned API para Proponentes"),
        ("shodan", "Shodan API para Proponentes"),
    ]

    for proveedor, notas in proveedores_default:
        cur.execute("""
            INSERT OR IGNORE INTO scorecard_proponentes_api_keys
            (proveedor, api_key_encrypted, activo, notas, actualizado_por, fecha_actualizacion)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            proveedor,
            "",
            0,
            notas,
            "Sistema",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

    conn.commit()
    conn.close()


init_scorecard_proponentes_api_db()


def scorecard_proponentes_get_api_key(proveedor):
    proveedor = (proveedor or "").strip().lower()

    try:
        conn = get_scorecard_proponentes_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT api_key_encrypted, activo
            FROM scorecard_proponentes_api_keys
            WHERE proveedor = ?
            LIMIT 1
        """, (proveedor,))

        row = cur.fetchone()
        conn.close()

        if not row:
            return ""

        if int(row["activo"] or 0) != 1:
            return ""

        return scorecard_decrypt_api_key(row["api_key_encrypted"])

    except Exception:
        return ""


def scorecard_proponentes_api_status():
    proveedores = ["leakcheck", "hibp", "shodan"]
    estado = {}

    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    for proveedor in proveedores:
        cur.execute("""
            SELECT *
            FROM scorecard_proponentes_api_keys
            WHERE proveedor = ?
            LIMIT 1
        """, (proveedor,))

        row = cur.fetchone()

        if row:
            api_key = scorecard_decrypt_api_key(row["api_key_encrypted"])
            estado[proveedor] = {
                "activo": int(row["activo"] or 0) == 1,
                "configurada": bool(api_key),
                "mask": scorecard_mask_api_key(api_key),
                "fecha": row["fecha_actualizacion"],
                "notas": row["notas"] or ""
            }
        else:
            estado[proveedor] = {
                "activo": False,
                "configurada": False,
                "mask": "No configurada",
                "fecha": "",
                "notas": ""
            }

    conn.close()
    return estado


def scorecard_proponentes_guardar_api_key(proveedor, api_key, activo, usuario):
    proveedor = (proveedor or "").strip().lower()
    api_key = (api_key or "").strip()

    encrypted = scorecard_encrypt_api_key(api_key) if api_key else ""

    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO scorecard_proponentes_api_keys
        (proveedor, api_key_encrypted, activo, notas, actualizado_por, fecha_actualizacion)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(proveedor) DO UPDATE SET
            api_key_encrypted = excluded.api_key_encrypted,
            activo = excluded.activo,
            actualizado_por = excluded.actualizado_por,
            fecha_actualizacion = excluded.fecha_actualizacion
    """, (
        proveedor,
        encrypted,
        1 if activo and api_key else 0,
        proveedor,
        usuario,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


# ============================================================
# DASHBOARD PROPONENTES / TERCEROS
# ============================================================

@app.route("/proponentes/scorecard")
@login_required
def proponentes_scorecard_dashboard():
    user, allowed, read_only = scorecard_proponentes_user_permiso()

    if not allowed:
        flash("No tiene permiso para acceder al Security Scorecard de Terceros.", "danger")
        return redirect(url_for("menu"))

    puede_configurar = (
        user.role == "admin"
        or (
            user.role != "auditor"
            and verificar_permiso(user, SCORECARD_PROPONENTES_PERMISO)
        )
    )

    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM scorecard_proponentes_runs
        ORDER BY id DESC
        LIMIT 100
    """)
    runs = cur.fetchall()

    cur.execute("SELECT COUNT(*) AS total FROM scorecard_proponentes_runs")
    total_runs = cur.fetchone()["total"] or 0

    cur.execute("""
        SELECT AVG(score_total) AS promedio
        FROM scorecard_proponentes_runs
        WHERE estado = 'finalizado'
    """)
    promedio = cur.fetchone()["promedio"] or 0

    cur.execute("""
        SELECT COUNT(*) AS total
        FROM scorecard_proponentes_runs
        WHERE nivel_riesgo IN ('Alto', 'Crítico', 'Critico')
    """)
    alto_critico = cur.fetchone()["total"] or 0

    cur.execute("""
        SELECT COUNT(*) AS total
        FROM scorecard_proponentes_runs
        WHERE estado IN ('pendiente', 'ejecutando')
    """)
    en_ejecucion = cur.fetchone()["total"] or 0

    conn.close()

    body = """
    <style>
      body{
        background-image:url('/static/img/ccsgsi.jpg');
        background-size:cover;
        background-position:center;
        background-attachment:fixed;
        background-repeat:no-repeat;
      }

      .prop-score-shell{
        width:96%;
        max-width:1500px;
        margin:26px auto 24px auto;
      }

      .prop-score-header-card{
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

      .prop-score-header-card::before{
        content:"";
        position:absolute;
        inset:0;
        background:
          radial-gradient(circle at 92% 12%,rgba(255,255,255,.20),transparent 25%),
          repeating-linear-gradient(
            135deg,
            rgba(255,255,255,.05) 0px,
            rgba(255,255,255,.05) 1px,
            transparent 1px,
            transparent 14px
          );
        pointer-events:none;
      }

      .prop-score-title{
        display:flex;
        align-items:center;
        justify-content:flex-start;
        gap:14px;
        color:#ffffff;
        position:relative;
        z-index:1;
        width:100%;
      }

      .prop-score-icon{
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
      }

      .prop-score-pill{
        display:inline-block;
        background:rgba(255,255,255,.18);
        border-radius:999px;
        padding:3px 10px;
        font-size:.65rem;
        font-weight:800;
        margin-bottom:4px;
        color:#ffffff;
      }

      .prop-score-title h2{
        color:#ffffff !important;
        font-weight:950;
        font-size:1.32rem;
        line-height:1.1;
        text-shadow:0 3px 10px rgba(0,0,0,.35);
        margin:0 !important;
      }

      .score-action-row{
        display:flex;
        justify-content:center;
        gap:10px;
        flex-wrap:wrap;
        margin:10px 0 14px;
      }

      .score-action-row .btn,
      .btn{
        border-radius:10px !important;
        min-height:32px;
        padding:8px 18px !important;
        font-size:.82rem;
        font-weight:900;
        box-shadow:0 8px 16px rgba(15,23,42,.15);
      }

      /* =========================================================
         BOTON CONFIGURAR API AZUL
      ========================================================= */

      .btn-api-blue{
        background:linear-gradient(135deg,#0b4a8f,#2f7fd1) !important;
        border:none !important;
        color:#ffffff !important;
        border-radius:12px !important;
        min-height:36px !important;
        padding:10px 22px !important;
        font-size:.84rem !important;
        font-weight:900 !important;
        box-shadow:0 10px 22px rgba(20,89,166,.35) !important;
        transition:all .18s ease-in-out;
      }

      .btn-api-blue:hover{
        background:linear-gradient(135deg,#0f4f97,#266fbb) !important;
        color:#ffffff !important;
        transform:translateY(-1px);
        box-shadow:0 14px 26px rgba(20,89,166,.45) !important;
      }

      .btn-api-blue:focus,
      .btn-api-blue:active{
        background:linear-gradient(135deg,#0f4f97,#266fbb) !important;
        color:#ffffff !important;
        outline:none !important;
        box-shadow:0 0 0 .18rem rgba(47,127,209,.25) !important;
      }

      .soft-card{
        background:rgba(255,255,255,.96) !important;
        border-radius:18px !important;
        backdrop-filter:blur(8px);
        box-shadow:0 12px 24px rgba(15,23,42,.18) !important;
        border:1px solid rgba(219,230,244,.9) !important;
        overflow:hidden;
      }

      .metric-card{
        background:#ffffff;
        border:1px solid #dbe6f4;
        border-radius:16px;
        box-shadow:0 8px 18px rgba(15,23,42,.10);
        padding:18px;
        height:100%;
      }

      .metric-label{
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
        margin-bottom:8px;
      }

      .metric-value{
        color:#0b4a8f;
        font-size:1.8rem;
        font-weight:950;
        line-height:1;
      }

      .table-wrap{
        max-height:72vh;
        overflow-y:auto;
        overflow-x:auto;
        background:#ffffff;
        border-radius:14px;
        border:1px solid #dbe6f4;
        box-shadow:0 12px 24px rgba(15,23,42,.10);
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
        font-weight:900 !important;
        border:none !important;
        white-space:nowrap;
        vertical-align:middle !important;
        text-align:center;
        padding:9px 8px;
      }

      .table tbody td{
        vertical-align:middle !important;
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

      .badge{
        border-radius:999px;
        font-size:.70rem;
        padding:.35rem .65rem;
        font-weight:900;
      }

      .acciones-score{
        display:flex;
        justify-content:center;
        gap:6px;
        flex-wrap:wrap;
        min-width:260px;
      }

      .acciones-score .btn{
        padding:6px 10px !important;
        min-height:32px;
        font-size:.74rem;
      }
    </style>

    <div class="prop-score-shell">

      <div class="prop-score-header-card">
        <div class="prop-score-title">
          <div class="prop-score-icon">⚡</div>
          <div>
            <div class="prop-score-pill">SGSI · Scorecard</div>
            <h2>Security Scorecard de Terceros</h2>
          </div>
        </div>
      </div>

      <div class="score-action-row">
        {% if puede_configurar %}
          <a href="{{ url_for('admin_scorecard_proponentes_apis') }}" class="btn btn-api-blue">
              🔐 Configurar APIs
          </a>

          <a href="{{ url_for('proponentes_scorecard_parametros') }}" class="btn btn-secondary">
            ⚙️ Parámetros Scorecard
          </a>
        {% endif %}

        {% if not read_only %}
          <a href="{{ url_for('proponentes_scorecard_scan_nuevo') }}" class="btn btn-primary">
            🚀 Ejecutar Escaneo Scorecard
          </a>
        {% endif %}
      </div>

      <div class="soft-card p-3 mb-4">
        <h6 class="fw-bold text-primary mb-2">FUENTES ENTERPRISE CONFIGURADAS</h6>
        <span class="badge bg-secondary me-1">LeakCheck</span>
        <span class="badge bg-secondary me-1">HIBP</span>
        <span class="badge bg-secondary me-1">Shodan</span>
        <span class="badge bg-info text-dark me-1">OSINT público activo</span>
      </div>

      <div class="row g-3 mb-4">
        <div class="col-md-3">
          <div class="metric-card">
            <div class="metric-label">Evaluaciones Ejecutadas</div>
            <div class="metric-value">{{ total_runs }}</div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="metric-card">
            <div class="metric-label">Score Promedio</div>
            <div class="metric-value">{{ "%.1f"|format(promedio) }}%</div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="metric-card">
            <div class="metric-label">Riesgos Críticos / No Aceptables</div>
            <div class="metric-value text-danger">{{ alto_critico }}</div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="metric-card">
            <div class="metric-label">En Ejecución</div>
            <div class="metric-value text-primary">{{ en_ejecucion }}</div>
          </div>
        </div>
      </div>

      <div class="soft-card p-3">
        <h5 class="fw-bold mb-3">📋 Historial de Scorecard de Terceros</h5>

        <div class="table-wrap">
          <table class="table table-hover align-middle mb-0">
            <thead>
              <tr>
                <th>ID</th>
                <th>Tercero</th>
                <th>Dominio</th>
                <th>IP</th>
                <th>DNS</th>
                <th>IP Rep.</th>
                <th>Kali</th>
                <th>Hacker Chatter</th>
                <th>Total</th>
                <th>Riesgo</th>
                <th>Estado</th>
                <th>Progreso</th>
                <th class="text-center">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {% for r in runs %}
              <tr>
                <td class="fw-bold">#{{ r.id }}</td>
                <td>{{ r.proponente_nombre }}</td>
                <td>{{ r.dominio }}</td>
                <td>{{ r.ip_resuelta or "—" }}</td>
                <td>{{ "%.1f"|format(r.score_dns or 0) }}</td>
                <td>{{ "%.1f"|format(r.score_ip or 0) }}</td>
                <td>{{ "%.1f"|format(r.score_kali or 0) }}</td>
                <td>{{ "%.1f"|format(r.score_darkweb or 100) }}</td>
                <td class="fw-bold">{{ "%.1f"|format(r.score_total or 0) }}</td>
                <td>
                  <span class="badge bg-{{ scorecard_proponentes_badge_color(r.nivel_riesgo or 'Pendiente') }}">
                    {{ r.nivel_riesgo or "Pendiente" }}
                  </span>
                </td>
                <td>
                  {% if r.estado == 'finalizado' %}
                    <span class="badge bg-success">Finalizado</span>
                  {% elif r.estado == 'error' %}
                    <span class="badge bg-danger">Error</span>
                  {% elif r.estado == 'ejecutando' %}
                    <span class="badge bg-primary">Ejecutando</span>
                  {% else %}
                    <span class="badge bg-secondary">{{ r.estado or "Pendiente" }}</span>
                  {% endif %}
                </td>
                <td style="min-width:130px;">
                  <div class="progress" style="height:18px;border-radius:20px;">
                    <div class="progress-bar" style="width:{{ r.progress_pct or 0 }}%;">
                      {{ r.progress_pct or 0 }}%
                    </div>
                  </div>
                </td>
                <td class="text-center">
                  <div class="acciones-score">
                    <a href="{{ url_for('proponentes_scorecard_detalle', scorecard_id=r.id) }}" class="btn btn-sm btn-outline-primary">
                      Ver detalle
                    </a>

                    <a href="{{ url_for('proponentes_scorecard_rating', scorecard_id=r.id) }}" class="btn btn-sm btn-outline-success">
                      📊 Gráfica
                    </a>

                    {% if not read_only %}
                      <form method="POST"
                            action="{{ url_for('proponentes_scorecard_eliminar', scorecard_id=r.id) }}"
                            style="display:inline;"
                            onsubmit="return confirm('¿Seguro que desea eliminar este Security Scorecard de Terceros? Esta acción no se puede deshacer.');">
                        <button type="submit" class="btn btn-sm btn-outline-danger">
                          🗑️ Eliminar
                        </button>
                      </form>
                    {% endif %}
                  </div>
                </td>
              </tr>
              {% else %}
              <tr>
                <td colspan="13" class="text-center text-muted py-4">
                  No existen scorecards de terceros registrados.
                </td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>

    </div>
    """

    return render_template_string(
        BASE,
        content=Markup(render_template_string(
            body,
            runs=runs,
            total_runs=total_runs,
            promedio=float(promedio or 0),
            alto_critico=alto_critico,
            en_ejecucion=en_ejecucion,
            read_only=read_only,
            user=user,
            puede_configurar=puede_configurar,
            scorecard_proponentes_badge_color=scorecard_proponentes_badge_color
        ))
    )

# ============================================================
# SECURITYSCORECARD GRAC - PROPONENTES
# MISMO DISEÑO QUE PROVEEDORES
# ============================================================

def scorecard_proponentes_rating_letra(score):
    score = float(score or 0)

    if score >= 90:
        return "A", "Excelente"
    if score >= 80:
        return "B", "Bueno"
    if score >= 70:
        return "C", "Aceptable"
    if score >= 60:
        return "D", "Débil"
    return "F", "Crítico"


def scorecard_proponentes_rating_color(score):
    score = float(score or 0)

    if score >= 90:
        return "#087c3d"
    if score >= 80:
        return "#15803d"
    if score >= 70:
        return "#d97706"
    if score >= 60:
        return "#c2410c"
    return "#991b1b"


def scorecard_proponentes_get_trend_data(run):
    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT fecha_ejecucion, score_total
        FROM scorecard_proponentes_runs
        WHERE LOWER(TRIM(proponente_nombre)) = LOWER(TRIM(?))
          AND estado = 'finalizado'
          AND fecha_ejecucion >= datetime('now', '-30 days')
        ORDER BY fecha_ejecucion ASC
    """, (run["proponente_nombre"],))

    rows = cur.fetchall()
    conn.close()

    data = []
    for r in rows:
        fecha = str(r["fecha_ejecucion"] or "")[:10]
        data.append({
            "fecha": fecha,
            "score_total": round(float(r["score_total"] or 0), 1)
        })

    if not data:
        data.append({
            "fecha": str(run["fecha_ejecucion"] or "")[:10],
            "score_total": round(float(run["score_total"] or 0), 1)
        })

    return data


def scorecard_proponentes_get_monthly_comparison(run):
    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT substr(fecha_ejecucion, 1, 7) AS mes,
               AVG(score_total) AS score
        FROM scorecard_proponentes_runs
        WHERE LOWER(TRIM(proponente_nombre)) = LOWER(TRIM(?))
          AND estado = 'finalizado'
        GROUP BY substr(fecha_ejecucion, 1, 7)
        ORDER BY mes ASC
        LIMIT 12
    """, (run["proponente_nombre"],))

    rows = cur.fetchall()
    conn.close()

    data = []
    for r in rows:
        data.append({
            "label": r["mes"] or "N/A",
            "score": round(float(r["score"] or 0), 1)
        })

    if not data:
        data.append({
            "label": str(run["fecha_ejecucion"] or "")[:7],
            "score": round(float(run["score_total"] or 0), 1)
        })

    return data


def scorecard_proponentes_get_risk_counts(scorecard_id):
    conn = get_scorecard_proponentes_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COALESCE(severidad, riesgo, 'Bajo') AS sev,
               COUNT(*) AS total
        FROM scorecard_proponentes_findings
        WHERE run_id = ?
        GROUP BY COALESCE(severidad, riesgo, 'Bajo')
    """, (scorecard_id,))

    rows = cur.fetchall()
    conn.close()

    counts = {
        "Crítico": 0,
        "Alto": 0,
        "Medio": 0,
        "Bajo": 0
    }

    for r in rows:
        sev = r["sev"] or "Bajo"

        if sev == "Critico":
            sev = "Crítico"

        if sev not in counts:
            sev = "Bajo"

        counts[sev] += int(r["total"] or 0)

    total = sum(counts.values())
    return counts, total


