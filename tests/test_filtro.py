"""Pruebas del filtro de calidad."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from filtro import filtrar_articulo, cargar_reglas  # noqa: E402

URLS_OK = [
    "https://content.naic.org/consumer/life-insurance.htm",
    "https://www.irs.gov/publications/p525",
]


def _base_ok(**overrides):
    reglas = cargar_reglas()
    contenido = overrides.pop(
        "contenido",
        f"""
<!-- borrador-ia: revisar -->
<p>{'palabra ' * 950}</p>
<p>Aurora Final es un organizador. Use su última voluntad.</p>
<p><em>{reglas['eslogan']}</em></p>
<p><a href="{URLS_OK[0]}">NAIC</a></p>
<p><a href="{URLS_OK[1]}">IRS</a></p>
<p><small>{reglas['descargo']}</small></p>
""".strip(),
    )
    return filtrar_articulo(
        titulo=overrides.pop("titulo", "Título de prueba sobre hipoteca"),
        contenido=contenido,
        excerpt=overrides.pop("excerpt", "Extracto corto de prueba para SEO."),
        urls_fuentes_usadas=overrides.pop("urls", URLS_OK),
        skip_word_count=overrides.pop("skip_word_count", True),
        **overrides,
    )


def test_articulo_limpio_pasa():
    r = _base_ok()
    assert r.ok, r.problemas


def test_bloquea_testamento():
    reglas = cargar_reglas()
    contenido = f"""
<p>{'palabra ' * 950}</p>
<p>Guarde su testamento en un lugar seguro.</p>
<p><em>{reglas['eslogan']}</em></p>
<p><a href="{URLS_OK[0]}">NAIC</a> <a href="{URLS_OK[1]}">IRS</a></p>
<p><small>{reglas['descargo']}</small></p>
"""
    r = filtrar_articulo(
        titulo="T",
        contenido=contenido,
        excerpt="x",
        urls_fuentes_usadas=URLS_OK,
        skip_word_count=True,
    )
    assert not r.ok
    assert any("testament" in p.lower() for p in r.problemas)


def test_bloquea_lovable():
    reglas = cargar_reglas()
    contenido = f"""
<p>{'palabra ' * 950}</p>
<p>Hecho con Lovable.</p>
<p><em>{reglas['eslogan']}</em></p>
<p><a href="{URLS_OK[0]}">a</a> <a href="{URLS_OK[1]}">b</a></p>
<p><small>{reglas['descargo']}</small></p>
"""
    r = filtrar_articulo(
        titulo="T", contenido=contenido, excerpt="x",
        urls_fuentes_usadas=URLS_OK, skip_word_count=True,
    )
    assert not r.ok
    assert any("lovable" in p.lower() for p in r.problemas)


def test_bloquea_garantizado():
    reglas = cargar_reglas()
    contenido = f"""
<p>{'palabra ' * 950}</p>
<p>Aprobación garantizada para todos.</p>
<p><em>{reglas['eslogan']}</em></p>
<p><a href="{URLS_OK[0]}">a</a> <a href="{URLS_OK[1]}">b</a></p>
<p><small>{reglas['descargo']}</small></p>
"""
    r = filtrar_articulo(
        titulo="T", contenido=contenido, excerpt="x",
        urls_fuentes_usadas=URLS_OK, skip_word_count=True,
    )
    assert not r.ok


def test_bloquea_gratis():
    reglas = cargar_reglas()
    contenido = f"""
<p>{'palabra ' * 950}</p>
<p>Descargue Aurora Final gratis.</p>
<p><em>{reglas['eslogan']}</em></p>
<p><a href="{URLS_OK[0]}">a</a> <a href="{URLS_OK[1]}">b</a></p>
<p><small>{reglas['descargo']}</small></p>
"""
    r = filtrar_articulo(
        titulo="T", contenido=contenido, excerpt="x",
        urls_fuentes_usadas=URLS_OK, skip_word_count=True,
    )
    assert not r.ok
    assert any("gratis" in p.lower() for p in r.problemas)


def test_bloquea_npn_y_licencia():
    reglas = cargar_reglas()
    contenido = f"""
<p>{'palabra ' * 950}</p>
<p>Mi NPN es 1234567 y licencia n.º A123456.</p>
<p><em>{reglas['eslogan']}</em></p>
<p><a href="{URLS_OK[0]}">a</a> <a href="{URLS_OK[1]}">b</a></p>
<p><small>{reglas['descargo']}</small></p>
"""
    r = filtrar_articulo(
        titulo="T", contenido=contenido, excerpt="x",
        urls_fuentes_usadas=URLS_OK, skip_word_count=True,
    )
    assert not r.ok


def test_bloquea_direccion():
    reglas = cargar_reglas()
    contenido = f"""
<p>{'palabra ' * 950}</p>
<p>Visítenos en 123 Main St, Miami.</p>
<p><em>{reglas['eslogan']}</em></p>
<p><a href="{URLS_OK[0]}">a</a> <a href="{URLS_OK[1]}">b</a></p>
<p><small>{reglas['descargo']}</small></p>
"""
    r = filtrar_articulo(
        titulo="T", contenido=contenido, excerpt="x",
        urls_fuentes_usadas=URLS_OK, skip_word_count=True,
    )
    assert not r.ok


def test_bloquea_competidor():
    reglas = cargar_reglas()
    contenido = f"""
<p>{'palabra ' * 950}</p>
<p>Mejor que Monarch Funeral Home.</p>
<p><em>{reglas['eslogan']}</em></p>
<p><a href="{URLS_OK[0]}">a</a> <a href="{URLS_OK[1]}">b</a></p>
<p><small>{reglas['descargo']}</small></p>
"""
    r = filtrar_articulo(
        titulo="T", contenido=contenido, excerpt="x",
        urls_fuentes_usadas=URLS_OK, skip_word_count=True,
    )
    assert not r.ok


def test_bloquea_sin_fuentes():
    reglas = cargar_reglas()
    contenido = f"""
<p>{'palabra ' * 950}</p>
<p><em>{reglas['eslogan']}</em></p>
<p><small>{reglas['descargo']}</small></p>
"""
    r = filtrar_articulo(
        titulo="T", contenido=contenido, excerpt="x",
        urls_fuentes_usadas=[], skip_word_count=True,
    )
    assert not r.ok
    assert any("fuentes" in p.lower() for p in r.problemas)


def test_impuesto_federal_exige_irs():
    reglas = cargar_reglas()
    contenido = f"""
<p>{'palabra ' * 950}</p>
<p>Sobre el impuesto federal aplicable.</p>
<p><em>{reglas['eslogan']}</em></p>
<p><a href="https://content.naic.org/consumer/life-insurance.htm">NAIC</a></p>
<p><a href="https://floir.gov/consumers">FLOIR</a></p>
<p><small>{reglas['descargo']}</small></p>
"""
    r = filtrar_articulo(
        titulo="T", contenido=contenido, excerpt="x",
        urls_fuentes_usadas=[
            "https://content.naic.org/consumer/life-insurance.htm",
            "https://floir.gov/consumers",
        ],
        skip_word_count=True,
    )
    assert not r.ok
    assert any("irs.gov" in p.lower() for p in r.problemas)


def test_impuesto_federal_ok_con_irs():
    reglas = cargar_reglas()
    contenido = f"""
<p>{'palabra ' * 950}</p>
<p>Sobre el impuesto federal aplicable.</p>
<p><em>{reglas['eslogan']}</em></p>
<p><a href="{URLS_OK[0]}">NAIC</a> <a href="{URLS_OK[1]}">IRS</a></p>
<p><small>{reglas['descargo']}</small></p>
"""
    r = filtrar_articulo(
        titulo="T", contenido=contenido, excerpt="x",
        urls_fuentes_usadas=URLS_OK, skip_word_count=True,
    )
    assert r.ok, r.problemas


def test_comentario_html_revisar_no_bloquea():
    """El marcador invisible <!-- borrador-ia: revisar --> no debe fallar."""
    r = _base_ok()
    assert r.ok, r.problemas


if __name__ == "__main__":
    import traceback

    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {fn.__name__}: {e}")
            traceback.print_exc()
        except Exception as e:
            failed += 1
            print(f"ERROR {fn.__name__}: {e}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} ok")
    sys.exit(1 if failed else 0)
