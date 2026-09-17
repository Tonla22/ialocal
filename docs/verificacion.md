# Verificación realizada · 17 de septiembre de 2026

## Entorno

- Windows; Python 3.12 y Node 24.16.0 encontrados en el equipo.
- Proyecto instalado en `C:\Users\tonto\OneDrive\Desktop\proyecto ia local`.
- Ollama respondió en `http://localhost:11434` y devolvió cuatro modelos.
- Pruebas de interfaz en una instancia separada, puerto 8766, con SQLite de
  prueba. La cuenta definitiva de puerto 8765 queda sin configurar.

## Resultados

- Compilación de React/TypeScript: correcta.
- Auditoría npm de dependencias de producción: cero vulnerabilidades informadas.
- Suite de backend: autenticación, CSRF, origen/Host, expiración, contraseña,
  rutas, enlaces duros, límites de archivos, aprobación/rechazo, revocación de
  herramientas, ejecución y cancelación de procesos, historial, agent loop,
  límite de iteraciones, visión y memoria. Resultado final en `logs/tests-final.txt`.
- Chat real con **qwen3:8b**: respondió “Nexo funciona.” mediante streaming.
  Primera carga observada: 54,72 s; ese valor es una observación, no una garantía.
- Agente real con **qwen3:8b**: llamada estructurada a `listar_archivos`, resultado
  real de la carpeta autorizada y respuesta posterior. Turno observado: 7,02 s.
- Se detectó una limitación de **qwen2.5-coder:7b** en esta instalación: escribió
  JSON como texto en vez de usar tool_calls. No se ejecutó ese texto.
- Interfaz: inicio de sesión, selector, Herramientas, Sistema y conversación
  real comprobados en navegador. Respuesta: “La interfaz está funcionando.”
- STOP AGENT interrumpió una generación real; se conservó la respuesta parcial
  con “Respuesta interrumpida”.
- Diseño revisado en 1280×720 y 390×844. Sin errores o advertencias en consola
  del navegador durante esas comprobaciones.

## Límites de lo comprobado

- Cámara y micrófono no se activaron durante la verificación.
- Motor STT y modelo Whisper opcionales no se instalaron; el botón permanece
  deshabilitado hasta tenerlos disponibles. No se afirma transcripción real probada.
- TTS depende de que el navegador exponga una voz local española.
- Visión: validación y envío de imágenes probados en tests aislados; no se
  presenta como prueba de precisión visual de los modelos.
- Control nativo de PC/Playwright y búsqueda semántica están pendientes.
- Tailscale está documentado, no instalado ni expuesto. No se abrieron puertos.
- La detención de procesos no revierte acciones que ya terminaron.

## Repetición

La suite automática no requiere Ollama. Para repetir la comprobación real:

1. Desde la carpeta raíz: `.\.venv\Scripts\python.exe scripts\serve-review.py`.
2. En otra consola: `.\.venv\Scripts\python.exe scripts\check-ollama.py`.
3. Cerrá la instancia de revisión con Ctrl+C. La contraseña de esa instancia
   es únicamente para pruebas, aparece en su script y nunca se utiliza en la
   instancia personal. No expongas el puerto 8766.

`data/verification-report.json` conserva los eventos y resultados de Ollama.
