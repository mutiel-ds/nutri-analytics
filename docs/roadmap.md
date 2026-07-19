# Roadmap (post-V1)

La **V0** (app completa en Streamlit) y la **V1** (servidor MCP local) están publicadas. Este documento recoge las líneas de mejora evaluadas y su orden de prioridad. Cada punto se convertirá en decisiones de diseño (D12, D13...) cuando se aborde.

## V1.1 — Solidez

Auditoría extensiva del repositorio con agentes revisores en paralelo (corrección, robustez, seguridad, rendimiento) y verificación adversarial de hallazgos.

**Arreglos ya identificados en `filtros.py`:**
- Normalización de acentos: "salmon" debe coincidir con "salmón" (usar `unicodedata`).
- Coincidencia por límites de palabra en el filtro de ingredientes: "sal" no debe coincidir con "ensalada".

**Fuera de alcance deliberado:** sinónimos y fuzzy matching. Esa semántica la aporta el agente MCP, no el motor de filtros. El filtro de ingredientes solo mira el array de ingredientes (comportamiento documentado, no bug).

**Revisión de calidad de la suite unitaria** (137 tests actuales): cobertura, tipificación y edge cases.

## V1.2 — Tests end-to-end

Cierra el "a futuro" establecido en D10.

- **AppTest** (framework oficial de Streamlit, sin navegador, rápido y determinista): capa de tests de página.
- **Playwright** para 3-4 flujos críticos en navegador real: crear receta → planificar semana → verificar Dashboard → exportar contexto. Suite pequeña a propósito, pues la automatización de widgets de Streamlit es frágil.

## V2 — Agente de IA integrado en la app

Nueva página de chat (`st.chat_input` + API de Anthropic con tool use) que consume las mismas funciones puras que la UI y el servidor MCP (tercer consumidor de D9).

Al estar la app desplegada en la nube, esto lleva el agente al móvil sin infraestructura adicional. Requiere API key de Anthropic en los secretos del hosting; coste por uso.

Cubre la mayor parte del caso de uso del MCP remoto con una fracción de su complejidad.

## V2.1 — Auditoría UX/UI

Sobre la app desplegada:

- **Lighthouse** y **axe-core** (accesibilidad y rendimiento).
- Revisión heurística asistida por agentes (capturas + heurísticas de usabilidad de Nielsen) con hallazgos priorizados.

Limitación asumida: el techo de personalización de Streamlit es bajo. Se buscan mejoras de jerarquía/flujo/accesibilidad, no un rediseño.

## V3 — Servidor MCP remoto (condicional)

Solo si tras la V2 se quiere usar las apps nativas de Claude/ChatGPT/Gemini contra los datos. Implica transporte HTTP, OAuth, hosting con la Secret key y TLS: pasar de "script local" a "operar un servicio".

## Horizonte — App multi-usuario pública

Cambio de categoría, no incremento. Requiere:

- **Supabase Auth** con políticas de RLS por usuario.
- Rediseño de D1 (RLS con políticas por usuario, columna `user_id` en las 5 tablas).
- Tratamiento legal de datos de salud de terceros (categoría especial en el RGPD: consentimiento, términos, responsabilidad).

La lógica pura actual (D9) sobrevive al cambio; se abordará como proyecto propio con fase de diseño dedicada.
