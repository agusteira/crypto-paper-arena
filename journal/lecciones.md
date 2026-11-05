# Lecciones — manual vivo

Reglas concretas que salen de la evidencia. Cada una con fecha y los trades que la respaldan. Si deja de funcionar, se tacha (~~así~~) o se ajusta.

**Estado (2026-11-05): 1 trade cerrado (T4, −5,6%). Muestra mínima: todo sigue siendo hipótesis.**

## Hipótesis de trabajo (sin evidencia propia todavía, a validar)
- H1 (2026-11-02): con el mercado ampliamente en baja, entrar parcial (≈50% del capital) y con tope ~22% por moneda. A evaluar con T1–T3.
- H2 (2026-11-02): cada orden cuesta ~0,15% (0,1% comisión + 0,05% slippage); no operar sin una razón clara que supere ese costo.
- H3 (2026-11-02): respetar el stop definido al entrar (cierre de vela 4h) en lugar de moverlo. Aplicada en T4 (2026-11-05): ojo, en velas verticales el stop por cierre ejecuta bastante peor que el nivel (−5,6% real vs ≈ −4% planeado); dimensionar contando ese deslizamiento.
- ~~H4~~ → reemplazada por R1/R2 abajo. (2026-11-05, respaldo: T4, n=1): no sumar a una moneda que ya supera el tope ~22% del equity, y preferir sumar en el retest del nivel roto que en la vela de extensión del breakout.

- ~~Gatillo "sumar BTC si cierra 4h > 78.600"~~ (2026-11-02): **anulado 2026-11-05.** Era una compra en la vela de impulso (T4: compra 80.736, stop 76.389, −5,6%). Reemplazado por R1.

## Reglas de trabajo (2026-11-05) — origen: crítica de Agus + T4
Contexto: Agus marcó el patrón "comprás cuando sube y vendés cuando baja". Evidencia propia: **1 trade (T4)**, muestra mínima; estas son reglas de trabajo tomadas de práctica estándar (Van Tharp: R y position sizing; break-and-retest), no reglas probadas con mis datos. Se revisan en cada revisión semanal.

- **R1 · Entrar en retroceso, no en la vela de impulso.** Compra solo cuando el precio vuelve al nivel roto o a un soporte 4h y una vela 4h cierra rechazándolo (mecha abajo, cierre arriba del nivel). Nunca comprar con la última vela 4h > +2% ni con el precio >2% arriba del nivel de referencia. Si no hay retroceso, me pierdo el trade y lo acepto. (T4, crítica de Agus)
- **R2 · Invalidación antes de entrar, tamaño desde el stop.** Antes de la orden: nivel de invalidación (debajo del mínimo del retest/soporte) y riesgo máx ≈1% del equity (~US$1) por trade, contando ~1,5% extra de deslizamiento del stop por cierre 4h. Tamaño = riesgo / (distancia al stop + 1,5%). Tope 25% del equity por moneda. (Van Tharp; T4 ejecutó −5,6% vs −4% planeado)
- **R3 · Objetivo ≥ 2R antes de entrar.** Si hasta la siguiente resistencia no hay al menos 2× la distancia al stop (neto del ~0,3% ida y vuelta de costos), no entro. (Van Tharp, expectativa; H2)
- **R4 · No comprar caídas en tendencia bajista ("cuchillo que cae").** "Buy the dip" solo si el 7d de la moneda o de BTC no está en mínimos nuevos y el soporte aguantó al cierre 4h. Comprar barato ≠ comprar mientras cae. (break-and-retest: operar a favor del marco mayor)
- **R5 · Sumar solo a ganadoras, solo en retroceso, solo con stop movido.** Para agregar: la posición previa en ganancia, el stop total del conjunto queda en break-even o mejor y la suma respeta R1–R2. Nada de promediar a ciegas, ni hacia arriba ni hacia abajo. (T4)
- **R6 · El stop no se negocia, pero se pone donde la idea está rota.** Vender en el stop no es el error; el error fue entrar lejos del stop. No sacar stops para "no vender en baja". (H3, T4)
