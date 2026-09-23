# Una sesión resuelta con el ejemplo

**Todos estos datos son sintéticos.** Sirven para practicar con
`Alma_de_Lujo_EJEMPLO.xlsx`; no describen el desempeño real de la marca.
El corte del ejercicio es el 21 de septiembre de 2026.

## 1. Revisar una compra que parece razonable por producto

El calcetín negro (`PIL-NEGRO`) tiene 10 unidades disponibles, 60 entregadas
y 4 reingresadas en 28 días completos. Su consumo observado es 2 unidades/día.
Con plazo de 14 días y seguridad de 7, la necesidad es `2 × 21 - 10 = 32`.
El mínimo y el múltiplo del proveedor elevan la propuesta a **36 unidades**.
Compra más flete cuestan $90 por unidad: el escenario compromete **$3,240**.

La cantidad es condicional. Antes de actuar hay que comprobar los costos, el
conteo, el plazo y las condiciones del proveedor con información real.

## 2. Comparar la propuesta con el plan completo de caja

El ejemplo incluye también **60 tops** elegidos, aunque su propuesta por
reposición es de **12**. Una cantidad elegida puede tener otro motivo comercial;
el libro muestra su efecto para que el responsable lo discuta.

| Escenario didáctico | Negro | Top | Compra total | Menor cierre diario | Piso definido |
| --- | ---: | ---: | ---: | ---: | ---: |
| Elección inicial del archivo | 36 | 60 | $24,240 | $32,760 | $40,000 |
| Cambiar sólo el top a 12 | 36 | 12 | $7,440 | $49,560 | $40,000 |

Para reproducirlo, guarda una copia del ejemplo y cambia **STOCK!I14** de `60`
a `12`. Conserva las fechas y todos los demás datos. En
**FLUJO_13_SEMANAS** el plan deja de rebasar el piso en ese escenario.
El presupuesto conservador previo a propuestas es **$17,000**.

Esto no prueba que 12 tops sean la compra óptima. Enseña a discutir una
alternativa, su consumo de caja y la razón comercial de elegir más unidades.
Si cambian los pagos o los cobros, hay que recalcular el escenario.

## 3. Resolver los pendientes sin inventar demanda

| Variante | Qué se observa en el ejemplo | Siguiente paso |
| --- | --- | --- |
| Negro | Propuesta condicional de 36 | Confirmar proveedor, conteo y caja. |
| Arena | Disponible suficiente; propuesta 0 | Vigilar el siguiente corte, sin inferir que dejó de venderse. |
| Lila | Falta costo de compra | Conseguir el costo y volver a evaluar precio/reposición. |
| Verde | Sólo 14 días de disponibilidad en una ventana de 28 | Medir disponibilidad y demanda perdida; no extrapolar ventas como demanda total. |
| Azul | Tránsito confirmado fuera del plazo | Verificar fecha antes de duplicar la compra. |
| Vino | Tránsito sin confirmar | Pedir confirmación y fecha al responsable de compras. |
| Rosa | Pre lanzamiento | Usar un piloto con presupuesto y métrica propios. |

Para los calcetines con costos completos, el escenario calcula un precio
objetivo de **$221.28** con costo variable de $104, comisión de 8% y margen
objetivo de 45%: `104 / (1 - 0.08 - 0.45)`, redondeado hacia arriba al centavo.
El precio del ejemplo es $299. Este cálculo no indica que debas bajar el precio
ni prueba cuánto comprarían los clientes a otro precio.

## Qué registrar al terminar

Abre `REGISTRO_DECISIONES.csv`. Para cada decisión acordada registra:

- SKU o referencia y motivo; qué evidencia falta o respalda la decisión.
- Responsable y fecha de revisión.
- Métrica principal, por ejemplo unidades disponibles al próximo corte.
- Límite, por ejemplo conservar el piso de caja con fuentes completas.
- Condición de cierre: mantener, ajustar o descartar después de revisar el corte.

No se ejecutó una compra, un pago ni un cambio de precio al resolver este
ejercicio. El valor está en llegar a la reunión con alternativas cuantificadas
y salir con una decisión que pueda revisarse.
