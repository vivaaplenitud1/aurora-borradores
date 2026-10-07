"""Filtro de calidad: bloquea borradores que incumplen reglas de Florida / marca."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

STATUS_PERMITIDO = "draft"
STATUS_PROHIBIDOS = frozenset(
    {"publish", "future", "private", "pending", "trash", "auto-draft"}
)


@dataclass
class ResultadoFiltro:
    ok: bool
    problemas: list[str] = field(default_factory=list)

    def bloquear(self, motivo: str) -> None:
        self.ok = False
        self.problemas.append(motivo)


def cargar_reglas(ruta: str | Path | None = None) -> dict[str, Any]:
    if ruta is None:
        ruta = Path(__file__).resolve().parent / "reglas.yaml"
    with open(ruta, encoding="utf-8") as f:
        return yaml.safe_load(f)


def cargar_fuentes(ruta: str | Path | None = None) -> dict[str, Any]:
    if ruta is None:
        ruta = Path(__file__).resolve().parent / "fuentes.yaml"
    with open(ruta, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _quitar_comentarios_html(texto: str) -> str:
    return re.sub(r"<!--.*?-->", "", texto, flags=re.DOTALL)


def _contar_palabras(texto: str) -> int:
    limpio = re.sub(r"<[^>]+>", " ", texto)
    limpio = re.sub(r"\s+", " ", limpio).strip()
    return len(limpio.split()) if limpio else 0


def _urls_en_texto(texto: str) -> list[str]:
    return re.findall(r"https?://[^\s\)\]\"'<>]+", texto)


def _dominio_ok(url: str, dominios: list[str]) -> bool:
    try:
        host = urlparse(url).hostname or ""
    except Exception:
        return False
    host = host.lower().lstrip("www.")
    for d in dominios:
        d = d.lower().lstrip("www.")
        if host == d or host.endswith("." + d):
            return True
    return False


def validar_status(status: str) -> ResultadoFiltro:
    """Nunca publicar: solo 'draft' está permitido."""
    r = ResultadoFiltro(ok=True)
    s = (status or "").strip().lower()
    if s != STATUS_PERMITIDO:
        r.bloquear(
            f"status rechazado: '{status}'. Solo se permite status='{STATUS_PERMITIDO}'."
        )
    return r


def exigir_draft_o_abortar(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Guarda de código: fuerza status=draft y aborta si alguien intenta otro valor.
    Lanza ValueError si el payload pedía algo distinto de draft.
    """
    pedido = payload.get("status", STATUS_PERMITIDO)
    check = validar_status(str(pedido))
    if not check.ok:
        raise ValueError("; ".join(check.problemas))
    out = dict(payload)
    out["status"] = STATUS_PERMITIDO
    return out


def filtrar_articulo(
    *,
    titulo: str,
    contenido: str,
    excerpt: str,
    urls_fuentes_usadas: list[str] | None = None,
    reglas: dict[str, Any] | None = None,
    fuentes_cfg: dict[str, Any] | None = None,
    skip_word_count: bool = False,
) -> ResultadoFiltro:
    """Evalúa el artículo. ok=False → NO crear el borrador en WordPress."""
    reglas = reglas or cargar_reglas()
    fuentes_cfg = fuentes_cfg or cargar_fuentes()
    r = ResultadoFiltro(ok=True)

    texto_visible = _quitar_comentarios_html(contenido or "")
    corpus = f"{titulo or ''}\n{excerpt or ''}\n{texto_visible}"

    # 1) Frases / patrones prohibidos
    for patron in reglas.get("prohibido_regex") or []:
        if patron in (reglas.get("permitir_si_cita_irs") or []):
            continue
        try:
            # Nota visible REVISAR (mayúsculas). El verbo «revisar» se permite.
            flags = 0 if patron == r"\bREVISAR\b" else re.IGNORECASE
            if re.search(patron, corpus, flags=flags):
                r.bloquear(f"patrón prohibido coincide: /{patron}/")
        except re.error as e:
            r.bloquear(f"regex inválida en reglas.yaml: {patron} ({e})")

    # Excepción impuesto federal
    if re.search(r"impuesto\s+federal", corpus, flags=re.IGNORECASE):
        urls = (urls_fuentes_usadas or []) + _urls_en_texto(corpus)
        if not any("irs.gov" in u.lower() for u in urls):
            r.bloquear(
                "«impuesto federal» solo se permite si el artículo cita irs.gov"
            )

    # 2) Fuentes: ≥2 URLs de dominios permitidos
    urls = list(urls_fuentes_usadas or [])
    urls += _urls_en_texto(contenido or "")
    # dedupe preservando orden
    vistas: set[str] = set()
    urls_uniq: list[str] = []
    for u in urls:
        u = u.rstrip(".,;)")
        if u not in vistas:
            vistas.add(u)
            urls_uniq.append(u)

    dominios = fuentes_cfg.get("dominios_permitidos") or []
    urls_ok = [u for u in urls_uniq if _dominio_ok(u, dominios)]
    minimo = int(reglas.get("fuentes_minimas") or 2)
    if len(urls_ok) < minimo:
        r.bloquear(
            f"fuentes insuficientes: {len(urls_ok)} URL(s) oficiales "
            f"(mínimo {minimo}). URLs vistas: {urls_uniq[:5]}"
        )

    # 3) Formato
    if not skip_word_count:
        n = _contar_palabras(texto_visible)
        pmin = int(reglas.get("palabras_min") or 900)
        pmax = int(reglas.get("palabras_max") or 1400)
        if n < pmin or n > pmax:
            r.bloquear(f"conteo de palabras fuera de rango: {n} (esperado {pmin}-{pmax})")

    excerpt_max = int(reglas.get("excerpt_max") or 155)
    if len(excerpt or "") > excerpt_max:
        r.bloquear(f"excerpt demasiado largo: {len(excerpt)} > {excerpt_max}")

    eslogan = (reglas.get("eslogan") or "").strip()
    if eslogan and eslogan not in (contenido or ""):
        r.bloquear(f"falta el eslogan exacto: «{eslogan}»")

    descargo_frag = "Contenido educativo"
    if descargo_frag.lower() not in (contenido or "").lower():
        r.bloquear("falta el descargo fijo al final del artículo")

    if re.search(r"\btestamento\b", corpus, flags=re.IGNORECASE):
        # Ya cubierto por regex, pero mensaje explícito
        if not any("testament" in p.lower() for p in r.problemas):
            r.bloquear("contiene «testamento»; usar siempre «última voluntad»")

    return r
