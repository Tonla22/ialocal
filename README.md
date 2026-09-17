# Nexo · IA local

Asistente local para Windows con React + TypeScript, FastAPI, Ollama y SQLite.
Chat por streaming, conversaciones persistentes y agente con herramientas y aprobación.
El frontend compilado y la API se sirven desde **http://127.0.0.1:8765**.
Ollama permanece en `http://localhost:11434`; no se abre ningún puerto del router.

## Inicio rápido

1. Abrí Ollama.
2. La primera vez, ejecutá `setup.bat` si todavía no se instalaron las dependencias.
3. Ejecutá `start.bat` y dejá la consola abierta.
4. Abrí **http://127.0.0.1:8765** en el navegador.
5. En la primera entrada copiá el código de `data/setup-key.txt` y creá una contraseña de al menos 12 caracteres. El código se elimina al crear la cuenta.

No necesitás activar el entorno virtual manualmente ni iniciar dos servidores.
Si ya hay una instancia, el script informa que está abierta. Para detener una
instancia iniciada con start.bat, presioná Ctrl+C en su consola.
También podés ejecutar `stop.bat`; identifica solo el servidor de este proyecto.
Si hay acciones activas, usá primero STOP AGENT para cancelarlas antes de cerrar.

## Requisitos e instalación

Windows 10/11, Python **3.12**, Node **22 o superior**, npm y Ollama.
Las dependencias se instalan en `.venv` y `frontend/node_modules`; no se modifican
variables del sistema ni la política de ejecución persistente de PowerShell.
Los .bat usan `ExecutionPolicy Bypass` solo para el proceso que ejecuta el script.

En PowerShell, desde la carpeta del proyecto:

```powershell
Set-Location -LiteralPath "$([Environment]::GetFolderPath('Desktop'))\proyecto ia local"
.\setup.bat
.\start.bat
```

La instalación necesita Internet. El chat con modelos locales ya descargados
no necesita Internet. React, Markdown, iconos y estilos se sirven localmente,
sin fuentes remotas, CDN, telemetría ni servicios externos de voz.

## Modelos

El selector consulta `/api/tags` de Ollama. Se detectaron modelos locales durante
la instalación; los nombres que aparecen en la interfaz siempre se consultan en vivo.
La aplicación no descarga modelos automáticamente.
El modelo inicial es **qwen3:8b**, verificado con llamadas reales a herramientas.
En la prueba, qwen2.5-coder:7b respondió al chat pero escribió la llamada a herramienta
como texto; ese texto **no se ejecuta**. Preferí Qwen3 para el modo agente.

Si necesitás instalar un modelo por tu cuenta:

```powershell
ollama list
ollama pull qwen2.5-coder:7b
```

Los modelos ocupan varios GB fuera del proyecto, en la ubicación administrada
por Ollama. Cambiá el modelo desde el selector de la cabecera. El modo agente
requiere capacidad `tools`; adjuntar imágenes requiere `vision`. El backend
verifica las capacidades con `/api/show`, sin deducirlas del nombre.

## Estado de las fases

| Capacidad | Estado |
|---|---|
| Fase 1: chat, streaming, modelos, historial, SQLite, consulta segura de archivos | Implementado |
| Fase 2: escritura, copia, movimiento, carpetas, terminal, aprobaciones, agente, logs, STOP | Implementado |
| Captura de pantalla | Implementada desde el selector de pantalla del navegador, con permiso por captura |
| Control nativo de PC, mouse, teclado, ventanas y Playwright | Pendiente: interfaz modular preparada; no se ejecuta control nativo |
| Micrófono y dictado | Interfaz y adaptador faster-whisper implementados; requiere dependencias y modelo local opcionales |
| TTS | Voces locales en español del navegador; disponibilidad según navegador/Windows |
| Cámara e imágenes | Implementadas con permiso explícito y validación de visión del modelo |
| Memoria | Historial, contexto temporal y notas persistentes; búsqueda vectorial pendiente |
| Acceso remoto | Configuración e instrucciones para Tailscale; activación manual pendiente |

No se reemplazan herramientas por respuestas simuladas. Lo pendiente está
marcado en la interfaz. La pantalla compartida se captura una vez y se apaga;
no hay vigilancia continua ni cámara automática.

## Arquitectura

```text
frontend/src/         React, CSS, Markdown y lector SSE
backend/app/
  main.py            Rutas HTTP, límites, autenticación y frontend estático
  config.py          Configuración .env
  database.py        Capa SQLite
  auth.py            Contraseñas scrypt, sesiones y CSRF
  providers/         Contrato ChatProvider y adaptador Ollama
  agent.py           Agent loop, eventos, aprobaciones y cancelación
  tools/             Registro, esquemas Pydantic, archivos y PowerShell
  computer_control/  Contrato para futuros adaptadores nativos
  voice/             STT y contrato de TTS
  memory.py          Contrato para un futuro recuperador semántico
data/                Base SQLite, configuración de instalación y carpeta autorizada
logs/                Salida del servidor; auditoría funcional en SQLite
tools/               Documentación de extensiones
scripts/             Inicio, instalación y comprobaciones
docs/                Seguridad, voz, acceso remoto y verificación
```

Se eligió React/Vite en lugar de Next porque no se necesita renderizado del lado
del servidor. FastAPI sirve la compilación del frontend y la API bajo un solo
origen: menos procesos, autenticación más simple y acceso remoto más fácil.
SSE sobre `fetch` lleva tokens, estados y aprobaciones; no hace falta WebSocket
para el chat o el dictado por clips. Un futuro modo dúplex puede agregarlo.

## Configuración

Copiá `.env.example` a `.env` si hace falta. Reiniciá después de modificar `.env`.
No guardes contraseñas en el código. La contraseña se almacena con scrypt y sal
aleatoria, las sesiones en SQLite como hashes, y la cookie es HttpOnly/SameSite.

- `OLLAMA_URL`: URL del proveedor local; nunca exponer 11434 a Internet.
- `OLLAMA_MODEL`: selección inicial; después prevalece la selección guardada en SQLite.
- `DATABASE_PATH`: SQLite, por defecto `data/assistant.sqlite3`.
- `AUTHORIZED_ROOTS`: carpetas separadas por `;`. Por defecto **solo `data/workspace`**.
- `APP_ORIGIN`: origen autorizado de la interfaz. Ver acceso remoto para HTTPS.
- `SESSION_SECURE`: `true` cuando se usa HTTPS remoto.
- `MAX_ITERATIONS`: valor inicial; modificable entre 1 y 12 en la interfaz.
- `VOICE_ENABLED`, `STT_MODEL_PATH`: activar STT cuando esté instalado localmente.
- `VISION_ENABLED`: habilitar o deshabilitar imágenes, cámara y capturas.
- `COMPUTER_CONTROL_ENABLED`: reservado; actualmente no activa control nativo.

El backend escucha únicamente en `127.0.0.1`. Autenticación, lista de orígenes,
CSRF, cabeceras de seguridad y herramientas se verifican en el servidor.
No se habilita CORS para sitios externos.

## Herramientas y agente

En **Chat**, el modelo solo responde. En **Agente**, el modelo recibe los esquemas
de las herramientas habilitadas, puede solicitarlas y recibe sus resultados.
Cada turno tiene un límite configurable de iteraciones y 8 llamadas por iteración.
El contexto temporal de herramientas se mantiene durante el turno; en el historial
quedan los mensajes y en la auditoría quedan las acciones. No se muestra ni guarda
el campo privado `thinking`.

Las consultas de archivos están habilitadas inicialmente. La escritura y la
terminal están deshabilitadas hasta que las actives en **Herramientas**.
Las acciones de escritura piden aprobación por defecto; se puede cambiar en
Configuración. **PowerShell siempre pide aprobación**, incluso si el texto parece
de lectura. El clasificador solo informa; no se usa como barrera de seguridad.

Para probar archivos, creá un `.txt` en `data/workspace`, elegí Agente y pedí:
“Listá los archivos de mi carpeta autorizada”. El agente usa rutas relativas.
Las carpetas pueden elegirse por índice `root`: 0 es la primera autorizada.

La aprobación muestra los parámetros completos, incluido el comando o contenido
del archivo. Está vinculada al turno, la sesión y una acción exacta; vence en
3 minutos y no puede reutilizarse. Apagar una herramienta o todas detiene la
ejecución activa. STOP cancela generación y aprobaciones y solicita terminar
el árbol del proceso PowerShell en ejecución. Ver límites en `docs/seguridad.md`.

### Agregar una herramienta

1. Escribí su función en un módulo de `backend/app/tools`.
2. Definí un modelo Pydantic derivado de `Params` para validar sus argumentos.
3. Registrá un `Tool(nombre, descripción, parámetros, permiso, función, grupo)`.
4. Usá permisos `read`, `write` o `always`. No declares `read` en una acción con efectos.
5. Agregá pruebas de autorización, parámetros y cancelación.

Las funciones largas deben ser asíncronas y cancelables. Para procesos externos
usá `tools/process.py`; no lances procesos en segundo plano fuera de ese contrato.
No se importan plugins ni código desde conversaciones o archivos del usuario.

## Voz, visión y memoria

Ver `docs/voz.md` para STT opcional. El botón “Escuchar” usa una voz que el
navegador identifica como local y en español; si no hay una, se informa el error.
La voz automática se configura en Configuración. No se usa Web Speech Recognition
porque algunos navegadores procesan audio en servicios remotos.

Para visión elegí un modelo con esa capacidad y adjuntá hasta 3 imágenes de hasta
4 MB. Podés usar cámara o captura de pantalla con consentimiento del navegador.
El backend decodifica, reduce tamaño y reescribe JPEG antes de enviarlo a Ollama.
Las imágenes no se guardan en el historial de SQLite y solo se envían en ese turno.

La memoria persistente son notas que vos agregás o eliminás. El modelo no modifica
notas automáticamente. El contexto del chat usa los últimos 40 mensajes, sujeto
al contexto de 8192 tokens del proveedor. Búsqueda semántica/vectorial: pendiente.

## Acceso remoto

Ver **docs/acceso-remoto.md**. Se eligió **Tailscale Serve** con HTTPS dentro de
tu red privada Tailscale. No se usa Funnel ni publicación pública. La instalación
de Tailscale modifica la red de Windows: se deja como paso manual informado.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q
Push-Location frontend
npm.cmd run build
Pop-Location
```

Las pruebas aisladas usan SQLite temporal y un proveedor simulado únicamente para
probar errores, streaming, permisos y cancelación de forma determinista. La conexión
real con Ollama se verifica aparte: ver `docs/verificacion.md`.

## Solución de problemas

- **Ollama desconectado**: abrí Ollama, ejecutá `ollama list` y usá “Actualizar conexión y modelos” en Sistema.
- **Modelo lento**: la primera respuesta carga varios GB; elegí un modelo más pequeño. El timeout inicial es 240 segundos. STOP permite cancelar.
- **No puede leer mis archivos**: colocá archivos dentro de `data/workspace` o autorizá otra carpeta en `.env`, luego reiniciá. No se autorizan rutas por pedido del modelo.
- **No ejecuta herramientas**: seleccioná Agente, un modelo con `tools`, activá la herramienta y revisá “Apagar todas”.
- **No escribe**: la herramienta viene apagada; además requiere aprobación por defecto.
- **Imágenes rechazadas**: usá un modelo con `vision` y archivos PNG/JPEG/WebP dentro de los límites.
- **Micrófono desactivado**: STT no está instalado o no encuentra el modelo local. Ver docs/voz.md.
- **Sin voz**: el navegador no expone una voz local en español. Instalá una voz desde las opciones de Windows, si lo deseás; no se instala automáticamente.
- **Puerto ocupado**: cerrá la instancia anterior. No finalices procesos ajenos sin identificarlos.
- **Sesión vencida**: volvé a iniciar sesión. Las sesiones duran 12 horas por defecto.
- **Olvidaste contraseña**: con el servidor detenido, usá `scripts/reset-password.py` localmente; elimina la cuenta y sesiones, conserva conversaciones y genera un nuevo código de instalación en el próximo inicio.
- **Origen no autorizado**: accedé por el origen configurado y reiniciá tras cambiar `.env`.
- **OneDrive**: datos, código de instalación e historial pueden sincronizarse si la carpeta del Escritorio está sincronizada. Usá una carpeta local no sincronizada si necesitás confidencialidad frente a OneDrive.

## Referencias oficiales

- [API de chat de Ollama](https://docs.ollama.com/api/chat)
- [Herramientas de Ollama](https://docs.ollama.com/capabilities/tool-calling)
- [Tailscale Serve](https://tailscale.com/docs/reference/tailscale-cli/serve)
