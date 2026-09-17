# Límites de seguridad

Este es un asistente personal de un único usuario. No es un sandbox de sistema
operativo ni está diseñado como servicio público multiusuario.

- El servidor escucha en loopback y valida Host y Origin; no permite CORS externo.
- Las mutaciones requieren Origin autorizado, X-Local-App y CSRF de sesión.
- Las sesiones expiran, la contraseña tiene hash scrypt y hay límite de intentos.
- El primer registro requiere un código aleatorio que solo se entrega mediante
  un archivo local. Nunca se ofrece ese código en una API pública.
- Las herramientas solo son llamadas desde el backend; no hay endpoint de ejecución
  arbitraria de herramientas accesible sin el circuito del agente.
- React Markdown no habilita HTML crudo; las imágenes externas de Markdown no
  se cargan para evitar solicitudes inesperadas. Los enlaces se abren aparte.
- Las herramientas de archivos restringen rutas, tamaños y búsquedas. Rechazan
  traversal, rutas absolutas, ADS de Windows, junctions, symlinks y enlaces duros.
- Las carpetas autorizadas no deben ser cambiadas simultáneamente por procesos
  adversarios. Las validaciones de rutas no ofrecen aislamiento contra carreras
  deliberadas del sistema de archivos por otro proceso del mismo usuario.
- **PowerShell tiene los permisos completos del usuario**. No está confinado por
  AUTHORIZED_ROOTS. Siempre requiere aprobación; queda apagado por defecto.
  No apruebes comandos que no entiendas. Un archivo leído puede contener instrucciones
  maliciosas: los permisos se verifican aunque el modelo siga esas instrucciones.
- STOP cancela futuras acciones y el stream. Para PowerShell termina el árbol
  del proceso en curso, pero no deshace archivos escritos ni comandos ya completados.
  Tampoco puede retirar efectos externos o tareas desprendidas del árbol por un
  comando que autorizaste. No existe promesa de rollback ni de detención instantánea
  de una operación atómica ya iniciada.
- Las operaciones de archivos son pequeñas y sin threads que puedan seguir
  escribiendo después de que STOP confirme la cancelación.
- Base de datos y logs no están cifrados. La auditoría incluye parámetros y
  resultados; puede contener texto sensible. Protegé la carpeta y sus backups.
- Al estar en un Escritorio de OneDrive, los datos pueden salir del equipo por
  la sincronización de Windows. La aplicación en sí no los envía a servicios cloud.
- Un atacante con acceso a tu cuenta de Windows puede leer la base y reemplazar
  archivos del proyecto. La autenticación web no protege contra ese adversario.

Los límites de terminal no se basan en listas de palabras: el clasificador es
informativo y todos los comandos necesitan consentimiento individual.

Antes de habilitar control nativo de PC se requiere un adaptador con validación
de ventana activa, ejecución serial, parada de emergencia y aprobación. Actualmente
el interruptor de control nativo está inhabilitado y marcado como pendiente.
