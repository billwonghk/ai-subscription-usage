# AI Subscription Usage

[English](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Français](README.fr.md) | [Deutsch](README.de.md) | **Español**

Una aplicación de barra de menú / bandeja del sistema, local y sin necesidad de cuenta, que lee los registros de uso almacenados en tu propio equipo de ChatGPT, Claude Code, Claude Desktop, Gemini CLI y Grok, y compara el valor equivalente en API de los últimos 30 días con lo que realmente pagas por cada suscripción. Todo se ejecuta en tu propio equipo — sin clave de API de IA, sin inicio de sesión de cuenta, sin acceso a OAuth/Auth Token/Cookies, y sin ningún servicio en la nube de por medio.

⭐ Si esta herramienta te ayudó a saber si tu suscripción de IA realmente vale la pena, una Star ayuda a que otras personas la encuentren.

📺 **Vídeo de demostración:** YouTube (enlace próximamente) · Bilibili (enlace próximamente)

**Funciones**
- Panel de 30 días: tokens totales/de entrada/de salida, valor equivalente en API, coste de suscripción efectivo y múltiplo de valor, por proveedor
- Gráficos diarios de tokens y múltiplo de valor, desglosados por modelo
- Historial de planes de suscripción (mensual/anual, prorrateado según la fecha de vigencia)
- Detección automática de los registros de uso locales, con un método seguro y de lista blanca para señalar una carpeta que no sea la predeterminada
- Los precios de los modelos compatibles se actualizan automáticamente alrededor de una vez por semana con los datos públicos de precios de la API de [OpenRouter](https://openrouter.ai/) — sin necesidad de edición manual
- Siete idiomas: English, Français, Deutsch, Español, 简体中文, 日本語, 한국어
- Inicio automático al arrancar sesión, intervalo de actualización ajustable, acceso con un clic a tu carpeta de datos locales
- Diagnósticos anonimizados solo mediante consentimiento explícito — nunca contenido de conversaciones, rutas de archivos ni credenciales

**Capturas de pantalla**

| Informe | Ajustes |
| --- | --- |
| ![Panel del informe](assets/screenshots/report.png) | ![Panel de ajustes](assets/screenshots/settings.png) |

Detalle por proveedor (tokens y valor por modelo), y el mismo informe en chino:

![Detalle del proveedor Claude](assets/screenshots/report-claude-tab.png)
![Informe en chino](assets/screenshots/report-zh.png)

El método de comparación con DeepSeek y su correspondencia completa de modelo a nivel están documentados en la guía de configuración integrada en la app:

![Metodología de comparación con DeepSeek y tabla de correspondencia de modelos](assets/screenshots/deepseek-methodology-en.png)

**Cómo obtenerlo**

Descarga la última versión desde la página de [Releases](../../releases):
- **macOS**: `AI-Subscription-Usage-macOS.zip` — descomprímelo y mueve `AI Subscription Usage.app` a la carpeta Aplicaciones.
- **Windows**: `AI-Subscription-Usage-Windows-Setup.exe` para una instalación normal (acceso directo en el menú Inicio, desinstalación adecuada), o `AI-Subscription-Usage-Windows-Portable.zip` si prefieres simplemente descomprimir y ejecutar el .exe directamente, sin que se escriba nada en el registro ni en Program Files.

Cada versión incluye también un archivo `SHA256SUMS.txt` para verificar tu descarga. La versión de Windows se compila y se prueba automáticamente en la integración continua, pero todavía no se ha probado manualmente en un equipo Windows físico — consulta la tabla más abajo.

¿Prefieres compilarlo tú mismo desde el código fuente?

```bash
python3 -m venv .venv-desktop
.venv-desktop/bin/pip install -r requirements-desktop.txt
.venv-desktop/bin/pip install pyinstaller
.venv-desktop/bin/pyinstaller --clean --noconfirm ai-subscription-usage.spec
```

La compilación de macOS se genera en `dist/AI Subscription Usage.app`; la de Windows en `dist/AI Subscription Usage.exe`.

## Qué se ha verificado hasta ahora

| Plataforma | macOS (aplicación + CLI) | Windows (aplicación + CLI) |
| --- | --- | --- |
| ChatGPT | ✅ Funciona, verificado | 🟡 Misma ruta de código, debería funcionar — no probado en un Windows real |
| Claude | ✅ Funciona, verificado (la aplicación y el CLI comparten el mismo registro) | 🟡 La aplicación tiene una ruta específica para Windows; el CLI también debería funcionar — no probado en un Windows real |
| Gemini CLI | ✅ Funciona, verificado | 🟡 Debería funcionar — no probado en un Windows real |
| Gemini Desktop (Antigravity/Spark) | ❌ Confirmado que no es posible | ❌ Probablemente tampoco sea posible (mismo producto) — no confirmado específicamente |
| Grok | 🟡 El código debería ser correcto, pero no hay datos reales de Grok en este equipo para verificarlo | 🟡 Tampoco verificado, y las pruebas en Windows tampoco se han realizado |

Gemini Desktop (Antigravity/Spark) guarda sus archivos de sesión locales de forma cifrada (`~/.gemini/antigravity/conversations/*.pb`), sin una estructura legible ni una API local segura y documentada, por lo que no se puede leer el uso de tokens para este producto — aparece como detectado pero sin precio calculado.

Si tienes un equipo con Windows, o usas Grok de verdad, las pruebas y comentarios son especialmente bienvenidos — son las dos áreas que no se pueden verificar aquí. Abre un [Issue](../../issues) si encuentras algún problema.

## Resumen

Los números de versión se muestran en el menú de la bandeja, en la página del informe y en la página de ayuda. macOS guarda los datos del usuario en `~/Library/Application Support/AI Subscription Usage/`; Windows los guarda en `%LOCALAPPDATA%\AI Subscription Usage\`. Una actualización solo reemplaza el programa, la base de datos de precios integrada, los archivos de idioma y los adaptadores — los planes de suscripción, la configuración de las fuentes de datos, el idioma elegido, el consentimiento de diagnósticos y los informes locales nunca son sobrescritos por el instalador. Antes de migrar la configuración, los archivos originales se respaldan en `backups/` dentro del directorio de datos del usuario.

La versión pública publicada en GitHub no contiene planes de suscripción, resultados de detección, rutas absolutas locales, recuentos de tokens ni informes generados — los resultados de detección siempre se generan en tiempo real, en el equipo donde está instalada la aplicación. El flujo de publicación ejecuta primero `scripts/privacy_check.py` y detiene la compilación si falla.

## Fuentes de datos

| Plataforma | Carpeta local | Qué se contabiliza |
| --- | --- | --- |
| ChatGPT | `~/.codex/sessions/` | JSONL interno de Codex; entrada, salida y entrada en caché |
| Claude Code | `~/.claude/projects/` | Entrada, salida, lectura de caché y escritura de caché |
| Claude Desktop | `~/Library/Application Support/Claude/local-agent-mode-sessions/` | Detecta sesiones de la aplicación de escritorio; el uso de tokens se agrega mediante el registro JSONL compartido de Claude |
| Gemini CLI | `~/.gemini/tmp/*/chats/` | Entrada, salida, tokens de razonamiento y de caché |
| Antigravity Desktop | `~/.gemini/antigravity/` | Detectado automáticamente; sin precio mientras los campos de tokens del formato `.pb` no estén verificados |
| Antigravity CLI | `~/.gemini/antigravity-cli/` | Detectado automáticamente; sin precio mientras el formato no esté verificado |
| Grok Build | `~/.grok/logs/unified.jsonl` | Prioriza la lectura exacta de tokens de entrada, salida, razonamiento y caché |
| Origen alternativo de Grok Build | `~/.grok/sessions/**/signals.json` | Se usa solo cuando no existe `unified.jsonl`; se marca como estimación |

Los nombres de los modelos deben coincidir exactamente con `config/pricing.json`. Los modelos desconocidos siguen contabilizando sus tokens, pero no se calcula ningún valor equivalente en API para ellos, ni se les aplica el precio de otro modelo. La base de datos de precios puede almacenar precios distintos según la fecha de vigencia; los registros históricos usan el precio que estaba vigente ese día.

## Generación desde la línea de comandos

```bash
python3 src/ai_usage_report.py --days 30
```

El resultado se escribe en `outputs/ai-usage-report.html`. El botón "Actualizar datos locales" de la esquina superior derecha se comunica con el punto de conexión de actualización local que la aplicación de escritorio expone en `127.0.0.1:17653`; ese puerto solo está vinculado a loopback y nunca se expone a la red local ni a internet.

## Barra de menú de macOS y bandeja de Windows

La aplicación de escritorio ofrece: abrir informe, actualizar ahora, actualizar precios de modelos, buscar actualizaciones de la aplicación, cambiar de idioma, configuración y guía de uso, un interruptor de diagnósticos anónimos, y salir. En el primer inicio, abre automáticamente la configuración y guía de uso, que muestra el estado de detección de las fuentes de datos locales, comandos de diagnóstico y una instrucción de configuración segura que puedes copiar a tu propio asistente de IA local. De forma predeterminada, actualiza los datos locales y comprueba la versión de la aplicación cada 24 horas.

## Detección automática y configuración asistida por IA

La aplicación solo comprueba las carpetas predeterminadas registradas — nunca escanea todo el disco. Ejecuta `AI Subscription Usage --doctor --json` para ver el estado de detección de ChatGPT, Claude Desktop, Claude Code, Gemini CLI, Antigravity Desktop, Antigravity CLI y Grok. Las carpetas que no son las predeterminadas se configuran mediante comandos controlados:

```bash
AI\ Subscription\ Usage --configure-source --provider chatgpt --surface chatgpt-desktop --format codex-jsonl --path "$HOME/.codex/sessions"
AI\ Subscription\ Usage --verify-sources --json
```

`SETUP_WITH_AI.md` se puede entregar a tu propio asistente de IA local — ChatGPT, Claude Code, Gemini CLI u otro — que solo podrá invocar los comandos de diagnóstico de solo lectura y de configuración controlada indicados arriba. El archivo de configuración nunca acepta comandos, direcciones de red, credenciales ni código de análisis arbitrario.

```bash
python3 -m venv .venv-desktop
.venv-desktop/bin/pip install -r requirements-desktop.txt
.venv-desktop/bin/python src/desktop_app.py
```

La aplicación de escritorio es un proceso de barra de menú/bandeja que se ejecuta de forma continua. Antes de iniciarla, asegúrate de que ningún otro programa esté usando ya el puerto `17653`; al salir desde el menú se detienen tanto el icono de la bandeja como el punto de conexión de actualización local.

## Varios idiomas

La interfaz de escritorio incluye recursos en inglés, francés, alemán, español, chino simplificado, japonés y coreano. Por defecto sigue el idioma del sistema operativo y se puede cambiar desde la página de ajustes. Ningún campo calculado ni ningún dato de precios cambia según el idioma.

## Actualizaciones de la base de datos de precios

`config/pricing.json` almacena la versión de precios, las fuentes oficiales, los precios de los modelos y las fechas de vigencia. El cliente descarga las actualizaciones de precios desde un manifiesto, verifica la suma de comprobación SHA-256 y la estructura de los campos, y luego reemplaza de forma atómica la base de datos de precios local. Esta herramienta está pensada para mostrar una tendencia, no para ser una referencia de precios perfectamente exacta, así que la fuente de actualización son los datos públicos de precios de la API de [OpenRouter](https://openrouter.ai/) — un proxy de LLM muy conocido cuyos precios de API generalmente siguen las tarifas oficiales.

`config/model_id_map.json` asocia los nombres de modelo locales de este proyecto con su identificador exacto en OpenRouter. `scripts/fetch_pricing.py` usa esa correspondencia para obtener los precios actuales y reescribir `config/pricing.json` y `config/pricing-manifest.json`; `.github/workflows/update-pricing.yml` lo ejecuta automáticamente alrededor de una vez por semana y solo confirma (commit) los cambios cuando un precio realmente ha cambiado. Un cambio de precio real se registra como un nuevo período con fecha, de modo que las fechas de informes pasadas sigan usando la tarifa que realmente estaba vigente entonces. Los modelos que ya tienen un calendario con fechas escrito a mano quedan al margen de esta automatización. Cuando los registros de uso muestran un nombre de modelo completamente nuevo que aún no está en la correspondencia, simplemente se muestra sin precio hasta que se añade una línea en `config/model_id_map.json` — la aplicación de escritorio también intenta una actualización de precios al instante en cuanto detecta un modelo nuevo.

La pestaña de detalle de cada proveedor también muestra su tasa de aciertos de caché durante el período, además de un coste estimado si el mismo uso se hubiera ejecutado en [DeepSeek](https://www.deepseek.com/). Cada modelo se asigna a un nivel DeepSeek V4 Flash o Pro según su clase de capacidad (véase `config/deepseek_tier_map.json`), usando los precios públicos propios de DeepSeek (también actualizados mediante OpenRouter) y la proporción real de aciertos/fallos de caché de ese período, no una proporción estimada. Los modelos insignia sin un equivalente real en DeepSeek también se comparan con el nivel Pro, deliberadamente a favor de DeepSeek, para que la comparación nunca resulte exagerada.

## Diagnósticos anónimos

Los diagnósticos anónimos están desactivados por defecto y solo se envían después de activarlos explícitamente en los ajustes. Los campos permitidos se limitan a: versión de la aplicación, sistema operativo, idioma, módulo con el error, tipo de error, una traza de pila anonimizada y el estado de los adaptadores. Nunca se envían: contenido de conversaciones, instrucciones, respuestas, nombres de usuario, rutas de archivos locales, claves de API, detalles de suscripción, desglose de tokens ni registros en bruto. El `telemetry_endpoint` se completará cuando se publique el servicio de recepción de diagnósticos.

## Publicaciones automáticas

`.github/workflows/release.yml` ejecuta las pruebas después de publicar una etiqueta de versión, compila los artefactos de macOS y Windows, genera las sumas de comprobación SHA-256 y crea una GitHub Release. Las actualizaciones totalmente automáticas requieren además una dirección de repositorio de GitHub, un Developer ID de macOS, credenciales de notarización y un certificado de firma de código de Windows.

## Licencia

Este proyecto se publica bajo la licencia [PolyForm Noncommercial 1.0.0](LICENSE) — de uso, estudio, modificación y difusión libres para cualquier fin no comercial. No se permite el uso comercial. ¿Tienes preguntas sobre la licencia o sobre un caso de uso concreto? Abre un [Issue](../../issues). El código de terceros reutilizado debe seguir registrando su licencia, aviso de derechos de autor y origen en `THIRD_PARTY_NOTICES.md`.
