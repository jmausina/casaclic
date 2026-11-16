# Buscador de ideas virales (versión propia de Jose Miguel)

## Cómo funciona
1. **Domingo, 07:10 (Madrid):** el flujo `ideas-buscar.yml` busca en YouTube con los filtros de `ideas/config.json` y guarda `ideas/resultados/AAAA-MM-DD_ideas.{json,csv,md}`. Usa ~1.200 unidades del cupo de CasaClic (el que sobra antes de que se reinicie a las 9:00).
2. **Domingo, 10:37:** tarea programada de Claude. Lee los resultados, los pasa a una hoja de Google, elige **4 ideas** y escribe 4 fichas en `ideas/fichas/pendientes/`: 2 sin fecha (se suben el domingo) y 2 con `"subir_desde": "<fecha del miércoles>"` (se suben solas el miércoles a las 11:20).
   **Objetivo: 4 Shorts a la semana, de 1 minuto cada uno, + 1 vídeo largo a la semana para Belleza Ancestral.**
   La 5.ª ficha es el **vídeo largo** (`"formato": "largo"`, horizontal 1280x720) con `"subir_desde": "<viernes>"`: se sube solo el viernes a las 11:20 y se publica a las 19:00.
3. Al subir una ficha, el flujo `ideas-short.yml` fabrica el Short (voz Piper, fotos de Wikimedia, música propia) y lo sube. **Desde el 16/11 se publican solos** (decisión de Jose Miguel): cada ficha lleva `"privacidad": "public"` y `"hora_publicacion": "19:00"` → YouTube lo publica a las 19:00 de ese día (si ya ha pasado, al momento).

## Filtros (config.json)
`idioma`, `pais`, `idioma_estricto`, `periodo_dias`, `visitas_min/max`, `duracion_min/max_seg`, `formato` (todos/cortos/largos), `suscriptores_min/max`, `outlier_min`, `visitas_dia_min`, `interaccion_min_pct`, `rpm_min_usd`, `orden` (outlier/visitas/visitas_dia/interaccion). Cada búsqueda puede llevar sus propios `filtros` y `excluir`.

- **Outlier** = visitas del vídeo ÷ mediana de los últimos vídeos de su canal. ×10 = 10 veces más de lo normal.
- **RPM / ingresos**: estimación orientativa por nicho (AIR Media-Tech 2026, medianas en USD; cortos 3–14 % del largo). Cambio USD→EUR del BCE. Nunca son ingresos reales.

## Reglas para escribir una ficha (Claude)
- Idea propia inspirada en la tendencia. **Nunca copiar** título, guion ni imágenes del vídeo original.
- **Nada de promesas de salud** ni curas («hace crecer el pelo en zonas calvas», «quita el dolor»…). Solo cosas ciertas y prudentes.
- **Duración: 55–65 s** (Jose Miguel quiere vídeos de 1 minuto). Unas 11–13 escenas de 12–15 palabras cada una (~150 palabras en total). Primera escena = gancho fuerte. Última escena la pone el campo `cierre`.
- `imagen`: lista de 2–3 búsquedas en inglés, concretas («sliced banana», «banana slices»).
- Siempre `"privacidad": "public"` y `"hora_publicacion": "19:00"`.
- Descripción con el enlace del producto del canal:
  - CasaClic Oficial → `https://hotm.io/n7G5jK`
  - Belleza Ancestral → `https://go.hotmart.com/M108343227O`
- Canales con token en GitHub: «CasaClic Oficial» (`YT_REFRESH_TOKEN`), «Chollos de Belleza» (`YT_CHOLLOS_REFRESH_TOKEN`). «Belleza Ancestral» (`YT_BELLEZA_REFRESH_TOKEN`, puesto el 16/11). Reparto semanal: 2 Shorts para Belleza Ancestral y 2 para CasaClic Oficial (uno de cada el domingo y uno de cada el miércoles).
- Ejemplo de ficha: `ideas/fichas/hechas/2026-11-16_helado-platano-v2.json` (o `pendientes/` si aún no se ha subido).

## Vídeo largo semanal (Belleza Ancestral)
- Tema: la mejor idea de «Belleza natural» que dé para 8–10 minutos (puede juntar varias ideas de la semana). Mismo estilo del canal: belleza ancestral de distintas culturas, tono tranquilo, datos ciertos, sin promesas de salud.
- **8–10 minutos**: unas 1.100–1.300 palabras. En vez de `escenas`, usa `secciones`: 25–35 secciones de 3–4 frases (máx. ~18 palabras por frase), cada una con su `rotulo` y su `imagen` (lista de 2–3 búsquedas en inglés muy concretas: «rice water bowl», «rhassoul clay powder»).
- La descripción empieza SIEMPRE por: `📖 Recetario de Belleza Ancestral (40 recetas): https://go.hotmart.com/M108343227O`
- Campos: `"canal": "Belleza Ancestral"`, `"formato": "largo"`, `"privacidad": "public"`, `"hora_publicacion": "19:00"`, `"subir_desde": "<viernes AAAA-MM-DD>"`, `"categoria": "26"`.
- Ejemplo mínimo de la forma: `{"secciones": [{"rotulo": "Japón: el agua de arroz", "imagen": ["rice water bowl", "rice grains"], "frases": ["…", "…", "…"]}], "cierre": "…"}`

## Cupo de YouTube (10.000 unidades/día, proyecto CasaClic)
Cada subida gasta ~1.600. Máximo **2 Shorts nuevos por día** (por eso se reparten: 2 el domingo y 2 el miércoles) desde aquí para no dejar sin cupo a los robots de CasaClic y Chollos.
