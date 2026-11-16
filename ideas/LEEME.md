# Buscador de ideas virales (versión propia de Jose Miguel)

## Cómo funciona
1. **Domingo, 07:10 (Madrid):** el flujo `ideas-buscar.yml` busca en YouTube con los filtros de `ideas/config.json` y guarda `ideas/resultados/AAAA-MM-DD_ideas.{json,csv,md}`. Usa ~1.200 unidades del cupo de CasaClic (el que sobra antes de que se reinicie a las 9:00).
2. **Domingo, 10:37:** tarea programada de Claude. Lee los resultados, los pasa a una hoja de Google, elige **4 ideas** y escribe 4 fichas en `ideas/fichas/pendientes/`: 2 sin fecha (se suben el domingo) y 2 con `"subir_desde": "<fecha del miércoles>"` (se suben solas el miércoles a las 11:20).
   **Objetivo: 4 Shorts a la semana, de 1 minuto cada uno.**
3. Al subir una ficha, el flujo `ideas-short.yml` fabrica el Short (voz Piper, fotos de Wikimedia, música propia) y lo sube **en PRIVADO**. Jose Miguel decide si se publica.

## Filtros (config.json)
`idioma`, `pais`, `idioma_estricto`, `periodo_dias`, `visitas_min/max`, `duracion_min/max_seg`, `formato` (todos/cortos/largos), `suscriptores_min/max`, `outlier_min`, `visitas_dia_min`, `interaccion_min_pct`, `rpm_min_usd`, `orden` (outlier/visitas/visitas_dia/interaccion). Cada búsqueda puede llevar sus propios `filtros` y `excluir`.

- **Outlier** = visitas del vídeo ÷ mediana de los últimos vídeos de su canal. ×10 = 10 veces más de lo normal.
- **RPM / ingresos**: estimación orientativa por nicho (AIR Media-Tech 2026, medianas en USD; cortos 3–14 % del largo). Cambio USD→EUR del BCE. Nunca son ingresos reales.

## Reglas para escribir una ficha (Claude)
- Idea propia inspirada en la tendencia. **Nunca copiar** título, guion ni imágenes del vídeo original.
- **Nada de promesas de salud** ni curas («hace crecer el pelo en zonas calvas», «quita el dolor»…). Solo cosas ciertas y prudentes.
- **Duración: 55–65 s** (Jose Miguel quiere vídeos de 1 minuto). Unas 11–13 escenas de 12–15 palabras cada una (~150 palabras en total). Primera escena = gancho fuerte. Última escena la pone el campo `cierre`.
- `imagen`: lista de 2–3 búsquedas en inglés, concretas («sliced banana», «banana slices»).
- Descripción con el enlace del producto del canal:
  - CasaClic Oficial → `https://hotm.io/n7G5jK`
  - Belleza Ancestral → `https://go.hotmart.com/M108343227O`
- Canales con token en GitHub: «CasaClic Oficial» (`YT_REFRESH_TOKEN`), «Chollos de Belleza» (`YT_CHOLLOS_REFRESH_TOKEN`). «Belleza Ancestral» necesita el secreto `YT_BELLEZA_REFRESH_TOKEN` (si falta, el vídeo se fabrica pero no se sube).
- Ejemplo de ficha: `ideas/fichas/hechas/2026-11-16_helado-platano-v2.json` (o `pendientes/` si aún no se ha subido).

## Cupo de YouTube (10.000 unidades/día, proyecto CasaClic)
Cada subida gasta ~1.600. Máximo **2 Shorts nuevos por día** (por eso se reparten: 2 el domingo y 2 el miércoles) desde aquí para no dejar sin cupo a los robots de CasaClic y Chollos.
