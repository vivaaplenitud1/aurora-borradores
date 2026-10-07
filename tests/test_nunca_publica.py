"""Pruebas: el código NUNCA permite status distinto de draft."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


from filtro import exigir_draft_o_abortar, validar_status, STATUS_PERMITIDO


def test_validar_status_solo_draft():
    assert validar_status("draft").ok
    assert validar_status("DRAFT").ok
    for malo in ("publish", "pending", "future", "private", "trash", ""):
        r = validar_status(malo)
        assert not r.ok, malo


def test_exigir_draft_fuerza_y_aborta():
    ok = exigir_draft_o_abortar({"title": "x", "status": "draft", "content": "c"})
    assert ok["status"] == STATUS_PERMITIDO

    for malo in ("publish", "pending", "future", "private"):
        try:
            exigir_draft_o_abortar({"title": "x", "status": malo})
            raise AssertionError(f"debió abortar con status={malo}")
        except ValueError as e:
            assert "draft" in str(e).lower()


def test_payload_sin_status_queda_draft():
    out = exigir_draft_o_abortar({"title": "x", "content": "y"})
    assert out["status"] == "draft"


def test_generar_construir_payload_siempre_draft():
    sys.path.insert(0, str(ROOT))
    from generar import construir_payload, articulo_muestra

    art = articulo_muestra()
    payload = construir_payload(art)
    assert payload["status"] == "draft"
    # Intentar colar publish debe fallar
    try:
        exigir_draft_o_abortar({**payload, "status": "publish"})
        raise AssertionError("debió abortar")
    except ValueError:
        pass


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
