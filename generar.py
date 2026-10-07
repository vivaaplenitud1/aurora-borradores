#!/usr/bin/env python3
"""
Genera 1 artículo diario en BORRADOR para usagastosfinales.com.
Nunca publica. Solo status=draft. Pensado para GitHub Actions o VPS Hostinger.

Uso:
  python generar.py --dry-run          # sin claves; muestra payload
  python generar.py                    # flujo real (requiere env vars)
  python generar.py --tema-id 1        # forzar un tema
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from filtro import (
    STATUS_PERMITIDO,
    exigir_draft_o_abortar,
    filtrar_articulo,
    cargar_fuentes,
    cargar_reglas,
)

ROOT = Path(__file__).resolve().parent
TEMAS_CSV = ROOT / "temas.csv"
USER_AGENT = (
    "AuroraBorradores/1.0 (+https://usagastosfinales.com; articulo-educativo; bot)"
)

# ---------------------------------------------------------------------------
# Artículo de muestra (dry-run, sin API)
# ---------------------------------------------------------------------------
MUESTRA_TITULO = (
    "¿Qué pasa con mi hipoteca si me enfermo gravemente o fallezco?"
)
MUESTRA_EXCERPT = (
    "Cómo un seguro de vida con beneficios en vida puede ayudar a proteger "
    "la casa de familias hispanas en Florida si hay una enfermedad grave."
)
MUESTRA_URLS = [
    "https://content.naic.org/consumer/life-insurance.htm",
    "https://content.naic.org/sites/default/files/model-law-620.pdf",
    "https://www.consumerfinance.gov/consumer-tools/mortgages/answers/",
]


def _relleno_parrafos(n_palabras_aprox: int = 1000) -> str:
    """Genera párrafos educativos en español (~n_palabras) sin frases prohibidas."""
    base = (
        "Para muchas familias hispanas en Florida, la casa es el centro de la vida "
        "y el mayor compromiso económico. Si quien aporta el ingreso principal "
        "enfrenta una enfermedad grave, crónica o terminal que califique según la "
        "póliza, algunas pólizas de seguro de vida permiten adelantar parte del "
        "beneficio en vida. Ese dinero puede ayudar a seguir pagando la hipoteca "
        "y los gastos del hogar mientras la familia se organiza. "
        "Es importante entender que no es dinero extra: sale del beneficio por "
        "fallecimiento, se paga con un descuento y depende de la aseguradora, "
        "de las cláusulas (riders) y de que el diagnóstico cumpla la definición "
        "de la póliza. También puede haber efectos fiscales o en ayudas públicas; "
        "consulte a un profesional. "
        "El PMI protege al prestamista, no a su familia. Un seguro de vida "
        "personal deja el control en manos de los beneficiarios. "
        "Aurora Final es un organizador donde la familia guarda pólizas, "
        "contactos, hipoteca, documentos y la última voluntad en un solo lugar; "
        "no es un seguro, no aprueba coberturas ni da precios. "
    )
    partes = []
    total = 0
    while total < n_palabras_aprox:
        partes.append(f"<p>{base}</p>")
        total += len(base.split())
    return "\n".join(partes)


def articulo_muestra() -> dict[str, str]:
    reglas = cargar_reglas()
    eslogan = reglas["eslogan"]
    descargo = reglas["descargo"]
    cta = reglas["cta_neutra"]
    marca = reglas["marca_revision_html"]

    cuerpo = f"""
<!-- borrador-ia: revisar -->
<h1>{html.escape(MUESTRA_TITULO)}</h1>
<p>Si usted o su pareja enferman de gravedad, ¿quién paga la casa? Esta guía
explica, en español y con fuentes oficiales, cómo el <strong>seguro de vida con
beneficios en vida</strong> puede ayudar a proteger la hipoteca y a dejar las
cosas en orden. No es un «seguro de fallecimiento» aislado: el foco es cuidar
la vida de la familia hoy.</p>
<h2>Proteger la casa en vida y si usted falta</h2>
{_relleno_parrafos(950)}
<h2>Preguntas frecuentes</h2>
<h3>¿El dinero del beneficio en vida se le paga al banco?</h3>
<p>En una póliza personal, el pago suele ir al asegurado o a quien indique la
póliza, no automáticamente al prestamista. Compare con el seguro de crédito
hipotecario, donde el beneficiario suele ser el acreedor.</p>
<h3>¿Aurora Final es un seguro?</h3>
<p>No. Aurora Final es un organizador. Sirve para que la familia sepa dónde está
cada documento y cuál es la última voluntad. No cotiza ni aprueba pólizas.</p>
<h2>Fuentes</h2>
<ul>
<li><a href="{MUESTRA_URLS[0]}">NAIC — Life Insurance (consumidor)</a></li>
<li><a href="{MUESTRA_URLS[1]}">NAIC — Modelo 620 (beneficios acelerados)</a></li>
<li><a href="{MUESTRA_URLS[2]}">CFPB — Respuestas sobre hipotecas</a></li>
</ul>
<p><em>{eslogan}</em></p>
<p>{cta}</p>
<p><small>{descargo}</small></p>
{marca}
""".strip()
    return {
        "title": MUESTRA_TITULO,
        "excerpt": MUESTRA_EXCERPT,
        "content": cuerpo,
    }


# ---------------------------------------------------------------------------
# Temas CSV
# ---------------------------------------------------------------------------
def leer_temas(ruta: Path = TEMAS_CSV) -> list[dict[str, str]]:
    with open(ruta, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def guardar_temas(filas: list[dict[str, str]], ruta: Path = TEMAS_CSV) -> None:
    if not filas:
        return
    campos = list(filas[0].keys())
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(filas)


def siguiente_tema(
    filas: list[dict[str, str]], tema_id: int | None = None
) -> tuple[int, dict[str, str]]:
    pendientes = [
        (i, r)
        for i, r in enumerate(filas)
        if (r.get("estado") or "").strip().lower() == "pendiente"
    ]
    if tema_id is not None:
        for i, r in enumerate(filas):
            if str(r.get("id")) == str(tema_id):
                return i, r
        raise SystemExit(f"No se encontró tema id={tema_id}")
    if not pendientes:
        raise SystemExit("No quedan temas pendientes en temas.csv")
    if len(pendientes) < 10:
        print(
            f"AVISO: solo quedan {len(pendientes)} temas pendientes (<10).",
            file=sys.stderr,
        )
    return pendientes[0]


def urls_del_tema(tema: dict[str, str]) -> list[str]:
    raw = tema.get("fuentes_sugeridas") or ""
    return [u.strip() for u in raw.split("|") if u.strip()]


def filtrar_urls_permitidas(urls: list[str], fuentes_cfg: dict) -> list[str]:
    dominios = fuentes_cfg.get("dominios_permitidos") or []
    ok = []
    for u in urls:
        try:
            host = (urlparse(u).hostname or "").lower().lstrip("www.")
        except Exception:
            continue
        for d in dominios:
            d = d.lower().lstrip("www.")
            if host == d or host.endswith("." + d):
                ok.append(u)
                break
    return ok


# ---------------------------------------------------------------------------
# Descarga de fuentes (sin Google Search grounding)
# ---------------------------------------------------------------------------
def html_a_texto(raw: bytes, content_type: str = "") -> str:
    ct = (content_type or "").lower()
    if "pdf" in ct or raw[:4] == b"%PDF":
        try:
            from pypdf import PdfReader
            import io

            reader = PdfReader(io.BytesIO(raw))
            parts = []
            for page in reader.pages[:30]:
                parts.append(page.extract_text() or "")
            return "\n".join(parts)
        except Exception as e:
            return f"[PDF no legible: {e}]"
    text = raw.decode("utf-8", errors="replace")
    text = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", text)
    text = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:12000]


def descargar_fuentes(urls: list[str]) -> list[dict[str, str]]:
    out = []
    for u in urls:
        try:
            resp = requests.get(
                u, timeout=45, headers={"User-Agent": USER_AGENT}, allow_redirects=True
            )
            if resp.status_code != 200:
                print(f"  fuente {resp.status_code}: {u}", file=sys.stderr)
                continue
            texto = html_a_texto(resp.content, resp.headers.get("Content-Type", ""))
            if len(texto) < 80:
                print(f"  fuente vacía: {u}", file=sys.stderr)
                continue
            out.append({"url": u, "texto": texto[:10000]})
        except requests.RequestException as e:
            print(f"  error descargando {u}: {e}", file=sys.stderr)
    return out


# ---------------------------------------------------------------------------
# Modelos (Gemini → GLM opcional). Sin grounding.
# ---------------------------------------------------------------------------
MODELOS_GEMINI_POR_DEFECTO = "gemini-3.8-flash,gemini-flash-latest,gemini-3.5-flash-lite"


def llamar_gemini(prompt: str, api_key: str, modelo: str = "gemini-3.8-flash") -> str:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{modelo}:generateContent"
    )
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 16384},
    }
    resp = requests.post(
        url, json=body, timeout=180, headers={"x-goog-api-key": api_key}
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Gemini {resp.status_code}: {resp.text[:500]}")
    data = resp.json()
    parts = (
        data.get("candidates") or [{}]
    )[0].get("content", {}).get("parts") or []
    return "".join(p.get("text", "") for p in parts).strip()


def llamar_glm(prompt: str, api_key: str, modelo: str = "glm-4.7-flash") -> str:
    """API general de z.ai (NO el plan Coding). Env: GLM_API_KEY o ZAI_API_KEY."""
    url = "https://api.z.ai/api/paas/v4/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": modelo,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
    }
    resp = requests.post(url, headers=headers, json=body, timeout=120)
    if resp.status_code >= 400:
        raise RuntimeError(f"GLM {resp.status_code}: {resp.text[:500]}")
    data = resp.json()
    return (
        data.get("choices") or [{}]
    )[0].get("message", {}).get("content", "").strip()


def generar_con_modelos(prompt: str) -> str:
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    glm_key = (
        os.environ.get("GLM_API_KEY", "").strip()
        or os.environ.get("ZAI_API_KEY", "").strip()
    )
    errores = []
    if gemini_key:
        modelos = [
            m.strip()
            for m in (os.environ.get("GEMINI_MODELS") or MODELOS_GEMINI_POR_DEFECTO).split(",")
            if m.strip()
        ]
        for modelo in modelos:
            try:
                return llamar_gemini(prompt, gemini_key, modelo)
            except Exception as e:
                errores.append(f"{modelo}: {e}")
                time.sleep(2)
    if glm_key:
        try:
            return llamar_glm(prompt, glm_key)
        except Exception as e:
            errores.append(f"glm: {e}")
    raise RuntimeError(
        "No se pudo generar el artículo. "
        + "; ".join(errores)
        + (" (falta GEMINI_API_KEY)" if not gemini_key else "")
    )


def construir_prompt(tema: dict[str, str], fuentes: list[dict[str, str]]) -> str:
    reglas = cargar_reglas()
    bloques = []
    for f in fuentes:
        bloques.append(f"URL: {f['url']}\nTEXTO:\n{f['texto'][:6000]}\n")
    fuentes_txt = "\n---\n".join(bloques)
    return f"""Eres un redactor educativo en español para familias hispanas de Florida.
Escribes para el sitio usagastosfinales.com. NO inventes cifras. Usa SOLO las
fuentes oficiales que te paso abajo.

TEMA:
- Título sugerido: {tema.get('titulo')}
- Palabra clave: {tema.get('palabra_clave')}
- Categoría: {tema.get('categoria')}
- Ángulo: {tema.get('angulo')}

REGLAS OBLIGATORIAS:
1. Enfoque: seguro de vida CON BENEFICIOS EN VIDA (proteger/pagar hipoteca,
   dejar cosas pagadas, cobro en vida ante enfermedad crítica/crónica/terminal).
   Nunca «seguro de muerte».
2. Siempre «última voluntad». NUNCA «testamento» ni variantes.
3. Aurora Final = organizador (no es seguro; no da precios ni aprueba).
4. Eslogan exacto: «{reglas['eslogan']}»
5. NO menciones Lovable, NPN, número de licencia, dirección, teléfonos,
   nombres de aseguradoras competidoras ni funerarias.
6. NO uses «gratis», «sin costo», «free», «garantizado», «aprobación garantizada»,
   «sin rechazo», «Medicare paga», «programa federal/del gobierno».
7. «Impuesto federal» solo si citas irs.gov.
8. CTA neutra: «{reglas['cta_neutra']}»
9. Al final, el descargo exacto:
   {reglas['descargo']}
10. Formato: HTML Gutenberg simple (h2/h3, p, ul/li, FAQ). 900–1400 palabras.
11. Incluye sección «Fuentes» con enlaces a las URLs oficiales usadas.
12. Primera línea del contenido: comentario HTML {reglas['marca_revision_html']}
13. Meta descripción ≤155 caracteres (la devolverás aparte).
14. No escribas la palabra REVISAR en texto visible.

Responde SOLO con JSON válido (sin markdown):
{{
  "title": "...",
  "excerpt": "...",
  "content": "...html..."
}}

FUENTES OFICIALES (usa solo estas):
{fuentes_txt}
"""


def parsear_json_modelo(texto: str) -> dict[str, str]:
    texto = texto.strip()
    if texto.startswith("```"):
        texto = re.sub(r"^```(?:json)?\s*", "", texto)
        texto = re.sub(r"\s*```$", "", texto)
    data = json.loads(texto)
    return {
        "title": (data.get("title") or "").strip(),
        "excerpt": (data.get("excerpt") or "").strip(),
        "content": (data.get("content") or "").strip(),
    }


# ---------------------------------------------------------------------------
# WordPress REST (solo draft)
# ---------------------------------------------------------------------------
def wp_auth() -> tuple[str, str, str]:
    url = (os.environ.get("WP_URL") or "").rstrip("/")
    user = os.environ.get("WP_USER") or ""
    pwd = os.environ.get("WP_APP_PASSWORD") or ""
    if not url or not user or not pwd:
        raise SystemExit("Faltan WP_URL, WP_USER o WP_APP_PASSWORD")
    return url, user, pwd


def wp_buscar_duplicado(base: str, auth: tuple[str, str], palabra: str) -> bool:
    r = requests.get(
        f"{base}/wp-json/wp/v2/posts",
        params={"search": palabra, "status": "draft,publish", "per_page": 5},
        auth=auth,
        timeout=30,
        headers={"User-Agent": USER_AGENT},
    )
    if r.status_code >= 400:
        print(f"AVISO búsqueda duplicados: {r.status_code}", file=sys.stderr)
        return False
    return bool(r.json())


def ids_imagenes_configurados() -> list[int]:
    """Lista opcional de IDs de media ya subidos: env FEATURED_IMAGE_IDS=12,34,56."""
    raw = (os.environ.get("FEATURED_IMAGE_IDS") or "").strip()
    if not raw:
        return []
    out = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            out.append(int(part))
    return out


def wp_buscar_imagen(base: str, auth: tuple[str, str], prefijo: str) -> int | None:
    # 1) Lista configurable de IDs (recomendado si el Colaborador no puede buscar media)
    ids = ids_imagenes_configurados()
    if ids:
        return ids[int(time.time()) % len(ids)]
    if not prefijo:
        return None
    r = requests.get(
        f"{base}/wp-json/wp/v2/media",
        params={"search": prefijo, "media_type": "image", "per_page": 10},
        auth=auth,
        timeout=30,
        headers={"User-Agent": USER_AGENT},
    )
    if r.status_code >= 400:
        return None
    items = r.json() or []
    if not items:
        return None
    idx = int(time.time()) % len(items)
    return int(items[idx]["id"])


def wp_crear_borrador(payload: dict[str, Any]) -> dict[str, Any]:
    """POST solo con status=draft. Aborta si se pide otra cosa o la respuesta no es draft."""
    seguro = exigir_draft_o_abortar(payload)
    if seguro["status"] != STATUS_PERMITIDO:
        raise ValueError("Guardia interna: status distinto de draft")

    base, user, pwd = wp_auth()
    r = requests.post(
        f"{base}/wp-json/wp/v2/posts",
        json=seguro,
        auth=(user, pwd),
        timeout=60,
        headers={"User-Agent": USER_AGENT, "Content-Type": "application/json"},
    )
    if r.status_code in (401, 403):
        code = ""
        try:
            code = (r.json() or {}).get("code", "")
        except Exception:
            pass
        raise RuntimeError(
            f"WordPress rechazó la petición ({r.status_code} {code}). "
            "Si es rest_cannot_publish o el CDN (hcdn) responde 403/405, "
            "usar el VPS o pedir lista blanca de /wp-json/*."
        )
    if r.status_code >= 400:
        raise RuntimeError(f"WordPress error {r.status_code}: {r.text[:800]}")

    data = r.json()
    if (data.get("status") or "").lower() != STATUS_PERMITIDO:
        raise RuntimeError(
            f"La respuesta NO es draft (status={data.get('status')!r}). "
            "Abortando: nunca publicar."
        )
    return data


def construir_payload(
    articulo: dict[str, str], featured_media: int | None = None
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "title": articulo["title"],
        "content": articulo["content"],
        "excerpt": articulo["excerpt"],
        "status": STATUS_PERMITIDO,  # ÚNICO valor permitido
        "comment_status": "closed",
    }
    if featured_media:
        payload["featured_media"] = int(featured_media)
    # Doble seguro
    return exigir_draft_o_abortar(payload)


# ---------------------------------------------------------------------------
# Flujo principal
# ---------------------------------------------------------------------------
def run_dry_run() -> int:
    print("=== DRY-RUN (sin claves, sin WordPress, sin modelos) ===\n")
    articulo = articulo_muestra()
    urls = MUESTRA_URLS
    resultado = filtrar_articulo(
        titulo=articulo["title"],
        contenido=articulo["content"],
        excerpt=articulo["excerpt"],
        urls_fuentes_usadas=urls,
    )
    print("Filtro de calidad:", "OK" if resultado.ok else "BLOQUEADO")
    if resultado.problemas:
        for p in resultado.problemas:
            print(f"  - {p}")
    payload = construir_payload(articulo, featured_media=None)
    # Verificar guardia never-publish
    assert payload["status"] == "draft", "FATAL: status no es draft"
    print("\nPayload JSON que SE ENVIARÍA a POST /wp-json/wp/v2/posts:")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print("\nstatus forzado:", payload["status"])
    return 0 if resultado.ok else 2


def run_real(tema_id: int | None, no_commit_state: bool) -> int:
    filas = leer_temas()
    idx, tema = siguiente_tema(filas, tema_id)
    print(f"Tema #{tema.get('id')}: {tema.get('titulo')}")

    fuentes_cfg = cargar_fuentes()
    urls = filtrar_urls_permitidas(urls_del_tema(tema), fuentes_cfg)
    if len(urls) < 2:
        raise SystemExit(
            f"Menos de 2 URLs permitidas para el tema {tema.get('id')}: {urls}"
        )

    print("Descargando fuentes oficiales (sin Google Search)…")
    fuentes = descargar_fuentes(urls)
    if len(fuentes) < 2:
        raise SystemExit(
            f"Solo se pudieron cargar {len(fuentes)} fuente(s) (mínimo 2). Abortando."
        )

    prompt = construir_prompt(tema, fuentes)
    print("Generando con Gemini (o respaldo GLM)…")
    bruto = generar_con_modelos(prompt)
    articulo = parsear_json_modelo(bruto)

    urls_usadas = [f["url"] for f in fuentes]
    resultado = filtrar_articulo(
        titulo=articulo["title"],
        contenido=articulo["content"],
        excerpt=articulo["excerpt"],
        urls_fuentes_usadas=urls_usadas,
    )
    if not resultado.ok:
        print("Filtro BLOQUEÓ el primer borrador:", file=sys.stderr)
        for p in resultado.problemas:
            print(f"  - {p}", file=sys.stderr)
        print("Reescribiendo una vez…", file=sys.stderr)
        prompt2 = (
            prompt
            + "\n\nCORRECCIÓN OBLIGATORIA. El borrador anterior falló por:\n- "
            + "\n- ".join(resultado.problemas)
            + "\nReescribe el JSON completo corrigiendo TODO eso."
        )
        bruto = generar_con_modelos(prompt2)
        articulo = parsear_json_modelo(bruto)
        resultado = filtrar_articulo(
            titulo=articulo["title"],
            contenido=articulo["content"],
            excerpt=articulo["excerpt"],
            urls_fuentes_usadas=urls_usadas,
        )
        if not resultado.ok:
            print("Filtro BLOQUEÓ de nuevo. No se crea nada en WordPress.", file=sys.stderr)
            for p in resultado.problemas:
                print(f"  - {p}", file=sys.stderr)
            return 3

    base, user, pwd = wp_auth()
    auth = (user, pwd)
    if wp_buscar_duplicado(base, auth, tema.get("palabra_clave") or articulo["title"][:40]):
        print(
            "AVISO: posible duplicado por palabra clave; se crea igual en draft "
            "para que José revise.",
            file=sys.stderr,
        )

    media_id = wp_buscar_imagen(base, auth, tema.get("imagen_prefijo") or "")
    payload = construir_payload(articulo, featured_media=media_id)
    print("Creando borrador en WordPress (status=draft)…")
    data = wp_crear_borrador(payload)
    post_id = data.get("id")
    print(f"OK: borrador id={post_id} status={data.get('status')}")

    # Actualizar estado en CSV
    ahora = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
    filas[idx]["estado"] = "borrador"
    filas[idx]["post_id"] = str(post_id or "")
    filas[idx]["fecha"] = ahora
    if not no_commit_state:
        guardar_temas(filas)
        print("temas.csv actualizado (estado=borrador).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Artículo diario en BORRADOR (nunca publica)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Sin claves: muestra artículo de muestra + filtro + payload JSON",
    )
    parser.add_argument("--tema-id", type=int, default=None)
    parser.add_argument(
        "--no-save-state",
        action="store_true",
        help="No escribir temas.csv tras crear el borrador",
    )
    args = parser.parse_args()
    if args.dry_run:
        return run_dry_run()
    return run_real(args.tema_id, args.no_save_state)


if __name__ == "__main__":
    sys.exit(main())
