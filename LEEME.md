# Artículo diario en borrador (usagastosfinales.com)

## Qué hace

Cada día genera **un** artículo en español (familias hispanas en Florida) sobre **seguro de vida con beneficios en vida** y lo deja en WordPress como **borrador**. **Nunca publica.** Usted revisa y pulsa Publicar.

- Toma el siguiente tema de `temas.csv` (copia de `../temas-v2.csv`; 60 temas, ~2 meses).
- Descarga páginas oficiales (NAIC, Florida CFO, IRS, etc.). **No** usa Google Search grounding.
- Redacta con Gemini 2.5 Flash (gratis, sin facturación). Respaldo opcional: GLM-4.7-Flash (API general).
- Filtro de calidad: bloquea «testamento», promesas, «gratis», NPN, dirección, competidores, etc.
- Usuario WordPress: Colaborador `borradores-ia` (no puede publicar ni subir medios).

Eslogan: **Ordena tu vida. Honra tu legado.** Aurora Final = organizador, no seguro.

## Qué tiene que hacer José (una vez)

1. **WordPress → Herramientas → Hostinger Tools:** «Disable application passwords» debe estar **apagado**.
2. **Usuarios → Añadir nuevo usuario:** `borradores-ia`, rol **Colaborador**. Luego **Editar → Contraseñas de aplicación**: crear una y guardarla.
3. **Medios:** subir 10–20 imágenes (títulos `hipoteca-01`, `beneficios-01`, `familia-01`, `florida-01`, `aurora-01`…). Anote los IDs y póngalos en el secreto `FEATURED_IMAGE_IDS` (ej. `12,34,56`), o deje que el script busque por prefijo.
4. **aistudio.google.com → Get API key:** clave Gemini **sin activar facturación**.
5. **GitHub (`vivaaplenitud1`) → New repository → `aurora-borradores` (Private):** subir esta carpeta. En **Settings → Secrets and variables → Actions** cargar: `WP_URL`, `WP_USER`, `WP_APP_PASSWORD`, `GEMINI_API_KEY` (opcional `GLM_API_KEY`). Probar: **Actions → articulo-diario → Run workflow**.
6. Si GitHub recibe **403 o 405** (`server: hcdn`): usar el **VPS Hostinger** (alternativa gratis). Copiar la carpeta, crear `.env` (chmod 600) desde `.env.example`, `python -m venv .venv && .venv/bin/pip install -r requirements.txt`, instalar `systemd/articulo-diario.service` y `.timer` (ajustar rutas/User), `systemctl enable --now articulo-diario.timer`.
7. **Cada día (5–10 min):** Entradas → Borradores → leer, corregir, imagen, **Publicar**.

## Prueba local sin claves

```bash
pip install -r requirements.txt
python generar.py --dry-run
```

## Costos

$0 si no activa facturación en Google, no pone tarjeta en GitHub y no compra créditos en OpenRouter.
