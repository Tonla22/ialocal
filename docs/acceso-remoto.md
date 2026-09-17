# Acceso fuera de tu WiFi mediante Tailscale

La configuración está preparada; Tailscale **no se instala ni activa automáticamente**.
Instalarlo agrega una interfaz de red y un servicio a Windows. Revisá ese cambio
antes de instalarlo desde su sitio oficial.

1. Instalá Tailscale en esta PC y en tu teléfono/otra computadora.
2. Iniciá sesión con la misma cuenta y protegela con autenticación de dos factores.
3. Permití el acceso únicamente a tus dispositivos mediante las reglas de tu tailnet.
4. Iniciá Nexo con `start.bat`.
5. En PowerShell, ejecutá:

```powershell
tailscale serve --bg http://127.0.0.1:8765
tailscale serve status
```

Seguí los pasos de Tailscale para habilitar HTTPS si los solicita. El comando
muestra una URL como `https://tu-pc.tu-red.ts.net`. Es accesible dentro de la
tailnet, no públicamente. **No uses `tailscale funnel`.**

6. En `.env` cambiá:

```dotenv
APP_ORIGIN=https://tu-pc.tu-red.ts.net
SESSION_SECURE=true
```

7. Reiniciá Nexo. Abrí esa URL con Tailscale conectado en ambos dispositivos y
   volvé a iniciar sesión. Usá también esa URL HTTPS desde la PC cuando las
   cookies Secure estén activadas; el HTTP local no permite esa sesión.

Ollama sigue en loopback, no se cambia OLLAMA_HOST y no se publica 11434.
No hay que abrir puertos del router. La computadora debe estar encendida y sin
suspender para acceder. Cámara y micrófono son los del dispositivo que abre la
interfaz; no activan los sensores de la PC anfitriona a distancia.

Para retirar el acceso:

```powershell
tailscale serve reset
```

Restaurá APP_ORIGIN local y SESSION_SECURE=false si volvés a usar solo HTTP local.

Documentación: https://tailscale.com/docs/reference/tailscale-cli/serve
