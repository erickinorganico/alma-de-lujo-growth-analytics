# Alma OS — empieza aquí

Este paquete es una guía **informativa y sintética** para preparar el corte semanal sin exponer información del negocio. El recorrido público empieza con las fuentes y las políticas; la demo pública sirve para conocer el resultado antes de entregar una copia privada a la persona analista.

## 1. Prepara las fuentes

1. Abre la [plantilla vacía](../FUENTES/operating-v1-blank.xlsx). Incluye las **22 tablas** requeridas y sus encabezados canónicos.
2. Consulta el [diccionario de campos](../DICCIONARIO/DICCIONARIO-v1.json) y el [manifiesto de la plantilla](../FUENTES/workbook-manifest.json).
3. Captura únicamente hechos observados. **Vacío no significa cero**: si aún no conoces un dato, déjalo vacío y conserva la cobertura como desconocida.
4. Guarda el archivo lleno como una **copia privada** fuera de este ZIP. No reemplaces la plantilla original.

El registro canónico contiene exactamente estas 22 tablas: `sku_catalog`, `sales_aggregates`, `availability_daily`, `unmet_demand`, `inventory_counts`, `inventory_movements`, `inventory_reservations`, `cost_versions`, `cost_components`, `cost_allocations`, `purchase_orders`, `purchase_receipts`, `obligations`, `obligation_payments`, `cash_events`, `cash_balance_evidence`, `budgets`, `budget_allocations`, `expenses`, `quality_events`, `sales_readiness` y `loans`. También se incluyen packs CSV vacíos y sintéticos completos en `FUENTES/source-packs/`.

## 2. Elige una política separada

Las políticas no son tablas de datos y no autorizan acciones comerciales:

- `operating-metrics-review-template-v1.json` tiene estado **REVIEW**. Es una plantilla sin aprobación del owner y debe permanecer así hasta que exista una aprobación verificable fuera del kit.
- `operating-metrics-synthetic-v1.json` tiene estado **SYNTHETIC_EXAMPLE** y sólo valida el ejemplo sintético incluido.

No uses la política sintética para un corte real. La persona analista recibe por separado la copia privada y la política aplicable.

## 3. Revisa el ejemplo resuelto

- Abre la [demo pública](../PORTAL/index.html) en el navegador. Funciona sin internet.
- Sigue el [recorrido sintético](../EJEMPLO/RECORRIDO-SINTETICO.md) para entender fuentes, métricas, alertas y decisiones.
- Revisa el estado mostrado: **WAITING** espera evidencia; **BLOCKED** exige corregir una entrada o contrato; **REVIEW** permite lectura, pero no implica aprobación.

## 4. Entrega privada y límites

Entrega a la persona analista la copia privada del workbook o pack y el archivo de política por un canal acordado. No pegues datos reales en la demo ni dentro de este ZIP.

Este ZIP no contiene el runtime de analistas y no puede ejecutar un corte privado. Tampoco carga, sincroniza, publica ni ejecuta acciones externas. El procesamiento real ocurre en el repositorio local del analista y sus resultados permanecen en `.local/`, fuera del paquete distribuible.

Continúa con la [guía semanal](GUIA_SEMANAL.html) o consulta el [manifiesto verificable](../PACKAGE-MANIFEST.json).
