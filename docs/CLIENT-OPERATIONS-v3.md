# Operación y mantenimiento del kit cliente

## Dos recorridos

El cliente abre Excel de escritorio, trabaja una copia privada de la plantilla,
completa los datos de corte, revisa propuestas y registra sus decisiones. La
guía de uso está en `client/GUIA_SEMANAL.html`. El archivo HTML funciona sin
servidor ni conexión. La plantilla puede operar sin Python ni agentes.

El analista puede validar esa copia con `scripts/review_client_workbook.py`.
La salida es un nuevo directorio dentro de `.local/client-runs`: JSON exacto,
informe legible, lista de correcciones y una solicitud de revisión nativa. La
solicitud conserva el hash del JSON; prepararla no equivale a ejecutar un agente.
Los agregados de este recorrido no se cargan en el almacén sintético v0.2.

## Primer corte y cierre semanal

1. Conservar el libro fuente en un directorio privado y registrar su corte.
2. Comprobar las cuatro tablas de entrada contra sus fuentes. Cada fecha/SKU
   tiene una fila consolidada. El conteo de inventario corresponde al corte.
3. Completar los parámetros. Las declaraciones de cobertura en CONFIG son
   afirmaciones de quien prepara el corte, no verificaciones automáticas.
4. Recalcular en Excel. Resolver las advertencias antes de interpretar una
   propuesta. `0` es un dato explícito; una celda vacía significa pendiente.
5. Elegir cantidades sólo como escenario; revisar MOQ, múltiplos, costo puesto
   en almacén, fecha de pago y los mínimos diarios de caja.
6. Registrar hasta tres decisiones con responsable, métrica, límite y fecha de
   revisión. Guardar la versión del corte y conservar pendientes para la semana
   siguiente. El libro no ejecuta decisiones ni hace conciliación bancaria.

## Semántica que debe mantenerse

- Los importes del kit están en **pesos MXN**, con hasta dos decimales. El
  oráculo calcula con Decimal; el núcleo v0.2 mantiene su contrato en centavos.
- Precio objetivo y margen son escenarios con costos actuales. La contribución
  observada usa el costo histórico opcional de VENTAS. Si falta, queda pendiente.
- Ventas netas y costo histórico pueden ser negativos por ajustes de otro
  periodo. Un reingreso físico es distinto de una devolución y de un reembolso.
- Disponibilidad física excluye tránsito. Un tránsito confirmado sólo compensa
  la necesidad si llegará dentro del plazo. Si está vencido o fuera del plazo,
  la propuesta queda para revisión.
- La propuesta no estima demanda perdida durante quiebres. Se requiere una
  ventana completa de disponibilidad para calcular una cantidad condicional.
- El pago de una compra elegida se modela completo en una fecha. No se registra
  de nuevo en CAJA. Anticipos, parcialidades y obligaciones ya registradas
  requieren un plan reconciliado para evitar duplicaciones.
- Los 91 cierres diarios detectan una salida anterior a una entrada dentro de
  una semana. No modelan orden ni hora de los movimientos del mismo día.
- El presupuesto previo usa el menor cierre base y la apertura. Es conservador:
  la decisión final también depende de las fechas de pago elegidas.

## Construcción y verificación

Instalar las herramientas opcionales con `python -m pip install -r
requirements-client.txt`. La versión original del motor v0.2 no necesita estas
dependencias; el kit y sus pruebas sí usan openpyxl/XlsxWriter.

```powershell
python scripts/build_client_workbook.py --output client
python scripts/verify_client_v3.py prepare --directory .local/client-excel-tests
./scripts/recalculate_client_excel.ps1 -InputDirectory .local/client-excel-tests -EvidenceDirectory .local/client-excel-tests/engine
python scripts/verify_client_v3.py check --directory .local/client-excel-tests --engine-receipt .local/client-excel-tests/engine/excel-recalculation.json --output .local/client-excel-tests/checks.json
./scripts/recalculate_client_excel.ps1 -InputDirectory client -EvidenceDirectory evidence/v0.3/excel -ExportPdf
python scripts/verify_client_v3.py check --directory client --engine-receipt evidence/v0.3/excel/excel-recalculation.json --output evidence/v0.3/workbook-checks.json
python scripts/package_client.py
python scripts/audit_release.py
```

El script de Excel crea una instancia nueva, oculta y sin macros/eventos;
no se conecta a libros que tenga abiertos el usuario. Requiere Windows con
Excel de escritorio y una sesión interactiva disponible. En el sandbox de Codex
puede necesitar ejecución escalada para acceder a COM. Los recibos registran
motor, versión y hash exacto de cada libro guardado después del recálculo.

La CI vuelve a comprobar hashes, cachés y aritmética independiente de los libros
publicados. No presenta esa comprobación como una nueva ejecución de Excel en
Linux. Después de cualquier cambio de fórmulas se repiten el recálculo real,
el contraste, la inspección visual y la revisión independiente.

## Publicación y privacidad

Sólo los nombres exactos de los dos libros generados están permitidos en la
auditoría de publicación. Sus hashes deben coincidir con el manifiesto; no se
permiten macros, vínculos a libros externos ni objetos incrustados.
El empaquetador comprueba que cada entrada coincide con el generador vacío o
sintético antes de producir el ZIP. La revisión de patrones no garantiza que
cualquier texto arbitrario esté libre de datos personales.

Nunca cambiar el generador o el manifiesto para publicar un corte real. No
subir `.local`, libros llenos, reportes privados ni referencias personales.
El acceso a GitHub continúa aislado a `erickinorganico` mediante el wrapper del
proyecto. Las pruebas no usan cuentas bancarias, tiendas ni fuentes de producción.
