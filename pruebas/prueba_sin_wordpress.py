"""Prueba real con Gemini SIN tocar WordPress: genera, filtra y guarda el artículo en un archivo."""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import generar as g
from filtro import filtrar_articulo
filas = g.leer_temas()
idx, tema = g.siguiente_tema(filas, None)
print("Tema", tema.get("id"), tema.get("titulo"))
urls = g.filtrar_urls_permitidas(g.urls_del_tema(tema), g.cargar_fuentes())
fuentes = g.descargar_fuentes(urls)
print("Fuentes cargadas:", len(fuentes), [f["url"] for f in fuentes])
prompt = g.construir_prompt(tema, fuentes)
art = g.parsear_json_modelo(g.generar_con_modelos(prompt))
r = filtrar_articulo(titulo=art["title"], contenido=art["content"], excerpt=art["excerpt"], urls_fuentes_usadas=[f["url"] for f in fuentes])
print("Filtro OK:", r.ok, r.problemas)
p = g.construir_payload(art, featured_media=None)
assert p["status"] == "draft"
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "articulo-prueba.json")
json.dump({"tema": tema, "filtro_ok": r.ok, "problemas": r.problemas, "payload": p}, open(out, "w"), ensure_ascii=False, indent=2)
print("Guardado en", out)
