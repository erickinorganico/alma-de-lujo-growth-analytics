# Alma OS v1.0.0

Alma OS v1.0.0 entrega un portal analítico estático para consulta offline, una plantilla operativa vacía, un libro de ejemplo sintético y guías de uso. El paquete no carga datos ni contiene el runtime semanal del analista.

## Archivos de distribución

- `Alma_OS_v1.0.0.zip`: portal, guías, dos libros y manifiesto de miembros.
- `Alma_OS_v1.0.0.zip.sha256`: SHA-256 del ZIP.
- `Alma_OS_v1.0.0.acceptance.json`: sidecar externo de aceptación del release, ligado al commit/tag, ZIP, checksum, manifiesto, recibos CI y recibos de aceptación.

El ZIP incluye la licencia raíz `LICENSE`. El inventario aprobado no incorpora dependencias ni assets de terceros: `third_party_bundled=false`. Si esto cambia, el release debe incluir un aviso completo con nombre, versión, origen y licencia de cada componente.

## Instalar, actualizar y volver atrás

Verifica el checksum con la primera sección de [RUNBOOK-v1.md](RUNBOOK-v1.md), extrae en una carpeta nueva y abre `PORTAL/index.html`. Para actualizar, conserva la versión anterior, verifica el checksum del nuevo ZIP y extrae en otra carpeta hermana. Comprueba el portal offline antes de cambiar cuál carpeta usas. Para rollback, abre de nuevo el portal anterior y verifica que funciona. La desinstalación elimina sólo la carpeta de paquete que seleccionaste; cualquier raíz privada, incluido `.local`, permanece fuera de esa operación. Consulta el runbook para el smoke de restauración y reglas de respaldo.

## Verificación desde el checkout de desarrollo

Las opciones se pueden consultar con `python scripts/package_release_v1.py --help`, `python scripts/audit_release_v1.py --help`, `python scripts/package_release_v1.py generate-manifest --help` y `python scripts/audit_release_v1.py check-manifest --help`. Los cuatro comandos exactos de CI son:

```powershell
python -m unittest tests.test_release_v1 -v
python scripts/audit_release_v1.py check-manifest --manifest client/v1/release-manifest.json --source-root . --require-version 1.0.0
python scripts/package_release_v1.py preflight --ref HEAD --output build/release-v1/Alma_OS_v1.0.0.zip --checksum build/release-v1/Alma_OS_v1.0.0.zip.sha256
python scripts/audit_release_v1.py audit-preflight --zip build/release-v1/Alma_OS_v1.0.0.zip --checksum build/release-v1/Alma_OS_v1.0.0.zip.sha256 --manifest client/v1/release-manifest.json --require-version 1.0.0
```

El runtime del analista se distribuye en el checkout fuente y requiere Python 3.11 o posterior. Consulta `.\run.ps1 weekly --help` y `.\run.ps1 weekly-resume --help` desde la raíz de ese checkout. El paquete cliente offline no ofrece creación ni continuación de cortes.

## Compatibilidad y estado de aceptación

El portal es HTML/CSS/JSON estático y abre desde el sistema de archivos con un navegador actual. Las hojas son XLSX para Microsoft Excel; la evidencia aceptada usó Excel 16.0 build 20326. El paquete no requiere servidor, conexión, credenciales ni servicio externo.

La aceptación adjunta separa las verificaciones deterministas, las tareas nativas y la inspección real en Excel. Los resultados empresariales de ejemplo son sintéticos; las observaciones históricas y sintéticas no acreditan rendimiento real. Pilates socks permanece como hipótesis en `REVIEW`. La aritmética sirve a analítica gerencial y no es asesoría fiscal. `EXT-01` adopción real y `EXT-02` política quedan `UNKNOWN`. Toda ejecución externa de negocio está `PROHIBITED`. El CI final y la publicación requieren su sidecar externo con evidencia del mismo SHA A.
