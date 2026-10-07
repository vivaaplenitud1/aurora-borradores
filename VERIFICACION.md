# Verificación independiente del programa `programa-articulo-diario`

**Fecha:** martes 6 de octubre de 2026 (~19:50 ET)  
**Verificador:** independiente (subagente; no es el builder)  
**Gold standard:** `../automatizacion-articulo-diario-v2.md`, `../temas-v2.csv`, `../automatizacion-verificacion.md`  
**Programa:** `/workspace/beneficios-en-vida/programa-articulo-diario/`  
**Alcance:** solo lectura + re-ejecución de tests/dry-run. No se contactó usagastosfinales.com ni se creó/empujo repo en GitHub. No se reescribió código (no hubo bug crítico).

---

## Veredicto global: **APPROVED**

El entregable cumple el plan v2 en lo esencial: solo `status=draft`, Colaborador sin subida de medios, filtro con tests, Gemini 2.5 Flash sin grounding, temas = `temas-v2.csv`, cron 10:17 America/New_York + systemd, secretos por env, dry-run sin claves, LEEME con pasos de José. Hay desviaciones menores no bloqueantes (lista abajo).

---

## Pruebas re-ejecutadas (esta verificación)

### Unit tests
```
PASS  test_articulo_limpio_pasa
PASS  test_bloquea_testamento
PASS  test_bloquea_lovable
PASS  test_bloquea_garantizado
PASS  test_bloquea_gratis
PASS  test_bloquea_npn_y_licencia
PASS  test_bloquea_direccion
PASS  test_bloquea_competidor
PASS  test_bloquea_sin_fuentes
PASS  test_impuesto_federal_exige_irs
PASS  test_impuesto_federal_ok_con_irs
PASS  test_comentario_html_revisar_no_bloquea
12/12 ok

PASS  test_validar_status_solo_draft
PASS  test_exigir_draft_fuerza_y_aborta
PASS  test_payload_sin_status_queda_draft
PASS  test_generar_construir_payload_siempre_draft
4/4 ok
```
Comando: `.venv/bin/python tests/test_filtro.py && .venv/bin/python tests/test_nunca_publica.py` → exit 0.

### Dry-run
```
=== DRY-RUN (sin claves, sin WordPress, sin modelos) ===
Filtro de calidad: OK
...
"status": "draft",
...
status forzado: draft
```
Comando: `.venv/bin/python generar.py --dry-run` → exit 0. Coincide con `dry-run-salida.txt`.

---

## Checklist

| # | Criterio | Resultado | Evidencia |
|---|---|---|---|
| 1 | Siempre `status=draft`; rechaza publish; Colaborador-safe (sin upload de media) | **PASS** | `construir_payload` / `exigir_draft_o_abortar` / `wp_crear_borrador` fuerzan y verifican `draft`; `STATUS_PROHIBIDOS` incluye publish/pending/…; tests `test_nunca_publica.py` 4/4. Media: solo `GET /wp/v2/media` (búsqueda) o `FEATURED_IMAGE_IDS`; **ningún** `POST /wp/v2/media`. |
| 2 | Filtro: testamento, Lovable, garantías/promesas, gratis/free (valor añadido), licencia/NPN/dirección, competidores; tests pasan | **PASS** | `reglas.yaml` `prohibido_regex` cubre `\btestament\w*`, Lovable, garantizado/aprobación garantizada, gratis/free/sin costo, NPN, licencia, dirección, teléfono, Monarch/MetLife/etc. Tests 12/12 PASS. Nota: «gratuita» (p. ej. revisión de 14 días) **sí** pasa; «free look» en inglés **bloquea** (`\bfree\b`) — ver desviaciones. |
| 3 | Gemini 2.5 Flash free tier; **sin** Google Search grounding; URLs oficiales de temas | **PASS** | `llamar_gemini(..., "gemini-2.5-flash")`; body sin tools/grounding; `descargar_fuentes` + whitelist `fuentes.yaml`; falla si &lt;2 fuentes. Comentarios/LEEME lo documentan. |
| 4 | Respaldo opcional GLM-4.7-Flash por API general (no Coding) | **PASS** | `llamar_glm` → `https://api.z.ai/api/paas/v4/chat/completions`, modelo `glm-4.7-flash`; env `GLM_API_KEY` / `ZAI_API_KEY`; `.env.example` aclara «NO el plan Coding». |
| 5 | Secretos solo por env; `.env.example` presente; nada hardcodeado | **PASS** | `.env.example` con placeholders; no hay `.env` en el árbol; escaneo sin claves tipo AIza/sk-/ghp_; `.gitignore` excluye `.env`. |
| 6 | GitHub Actions cron ~10:17 America/New_York + systemd VPS | **PASS** | `.github/workflows/articulo-diario.yml`: `cron: "17 10 * * *"` + `timezone: America/New_York` + `workflow_dispatch`. `systemd/articulo-diario.timer`: `OnCalendar=*-*-* 10:17:00 America/New_York`. Service con `EnvironmentFile=.env`. |
| 7 | Temas CSV; progreso/dedup; español FL hispano; beneficios en vida + Aurora Final organizador; eslogan; «última voluntad» nunca «testamento» | **PASS** | `temas.csv` md5 = `temas-v2.csv` (60 filas; 20/20/10/7/3; 0 «testament»). Prompt + reglas con eslogan exacto, Aurora organizador, última voluntad. Progreso: marca `borrador`+`post_id`+fecha. Dedup: `GET .../posts?search=...&status=draft,publish` (aviso; crea draft igual para revisión humana). |
| 8 | Dry-run sin claves; salida con `status=draft` | **PASS** | Re-ejecutado exit 0; payload `"status": "draft"`; archivo `dry-run-salida.txt` coherente. |
| 9 | `LEEME.md` en español llano con pasos exactos de José | **PASS** | Hostinger Tools (apagado), Colaborador `borradores-ia` + app password, 10–20 imágenes, Gemini en aistudio.google.com sin facturación, repo privado / VPS systemd, revisión diaria. |
| 10 | Sin contacto al sitio en vivo; sin crear/push de repo GitHub en este trabajo | **PASS** | Verificador no llamó a WP ni APIs con secretos; carpeta sin `.git`; no se usaron tools de create/push de repo. |
| 11 | Desviaciones listadas por el builder | **N/A** | El builder **no** dejó un archivo de desviaciones. A continuación: desviaciones halladas por el verificador y juicio. |

---

## Desviaciones vs plan (halladas por el verificador)

| Desviación | ¿Aceptable? | Notas |
|---|---|---|
| Sin revisor LLM (plan §7.5 Groq/Gemini JSON `{cumple,problemas[]}`) | **Sí** | El filtro regex + reescritura 1× + revisión humana del borrador cubren las reglas duras del checklist #2. Mejora futura, no bloqueante. |
| Cadena de modelos: `2.5-flash` → `2.0-flash` → GLM (plan: 2.5 → **3.x** → GLM → OpenRouter) | **Sí** | Checklist exige Gemini 2.5 + GLM opcional; 2.0 y ausencia de OpenRouter/Groq en runtime están documentados como reservados en `.env.example`. |
| Workflow se llama `articulo-diario.yml` (plan: `diario.yml`) | **Sí** | Nombre coherente con LEEME y `name: articulo-diario`. |
| Payload WP sin `categories` | **Sí (menor)** | José puede categorizar al publicar; el Colaborador solo asigna categorías existentes. Mejora opcional. |
| Dedup solo avisa y crea draft igual | **Sí** | Alineado con revisión humana; no publica. |
| `\bfree\b` bloquea la frase inglesa «free look» | **Sí, con decisión de José** | Temas 51/56 usan «gratuita» (pasa el filtro). Si el modelo cita «free look» de fuentes EN, fallará y reescribirá. José puede decidir una excepción regex (`free\s+look`) más adelante. |
| Sin URL context de Gemini (solo descarga HTML/PDF) | **Sí** | El plan marca la descarga como opción **preferida** (b). |

Ninguna desviación es crítica → **no se modificó código**.

---

## Must-fix (solo si se quiere pulir; no bloquean APPROVED)

1. *(Opcional)* Añadir excepción regex para `free look` / `free-look` si se quiere citar el término inglés de las guías CFO/NAIC en el tema 51.
2. *(Opcional)* Asignar `categories` existentes vía REST según `tema['categoria']`.
3. *(Opcional)* Cadena de respaldo: `gemini-2.5-flash` → modelo 3.x Flash free → GLM; revisor LLM ligero.
4. *(Operativo, José)* Crear repo privado `aurora-borradores`, secretos, usuario Colaborador, bank de imágenes / `FEATURED_IMAGE_IDS`, y elegir Actions vs VPS si el CDN Hostinger bloquea.

---

## Qué debe decidir José antes de montar secretos/repo

1. **GitHub Actions primero** o **VPS Hostinger** (si prevé 403/405 `hcdn`).
2. Subir 10–20 imágenes y anotar IDs para `FEATURED_IMAGE_IDS` (recomendado; el Colaborador no sube medios).
3. Crear `borradores-ia` (Colaborador) + application password; confirmar Hostinger Tools «Disable application passwords» **apagado**.
4. Clave Gemini Free en aistudio.google.com **sin facturación**; opcional `GLM_API_KEY` (API general z.ai).
5. Si acepta que «free look» en inglés quede bloqueado a favor de «revisión gratuita».

---

**APPROVED** — listo para que Grok Bot se lo entregue a José con la lista operativa de arriba.
