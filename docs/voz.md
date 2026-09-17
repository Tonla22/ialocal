# Voz local

## TTS disponible según el navegador

“Escuchar” y “Leer respuestas automáticamente” usan `speechSynthesis` filtrando
`localService=true` y voces en español. No se usa un motor remoto como fallback.
Si no hay una voz local, la interfaz lo informa. Las voces dependen de Windows y
del navegador. El contrato `voice/tts.py` permite agregar Piper posteriormente.

## STT opcional

La interfaz graba como máximo un minuto por clip y envía el audio al backend local.
El adaptador usa faster-whisper en CPU/int8. Por defecto está deshabilitado y no
se descarga nada automáticamente; requiere varios cientos de MB adicionales.

Con el servidor detenido, desde la carpeta del proyecto:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-voice.txt
```

Descargá de forma explícita un modelo CTranslate2 compatible con faster-whisper
y colocá **todos** sus archivos dentro de `data/models/whisper`. Por ejemplo, si
querés autorizar esa descarga:

```powershell
.\.venv\Scripts\python.exe -c "from huggingface_hub import snapshot_download; snapshot_download('Systran/faster-whisper-base', local_dir='data/models/whisper')"
```

Luego configurá `.env` y reiniciá:

```dotenv
VOICE_ENABLED=true
STT_MODEL_PATH=data/models/whisper
```

El servidor usa `local_files_only=True`: los pedidos de audio nunca disparan
descargas del modelo. Se elimina el archivo temporal de audio al terminar.
El micrófono solo se abre al tocar su botón y obtener permiso del navegador.
Una transcripción se agrega al cuadro de texto para que la revises antes de enviarla.

Pendiente: conversación full-duplex, interrupción de TTS al hablar, cancelación
del cómputo de transcripción en ejecución y carga persistente optimizada del modelo.
No se ha probado reconocimiento real de voz sin instalar el motor y modelo opcionales.
