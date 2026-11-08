# Resumen deportivo personal

## Evolución · fase 2: nota personal /10 y encaje

Se sustituye la acumulación de puntos antiguos por una escala personal estable sobre diez.
El correo muestra la nota y su nivel, con el desglose breve de interés deportivo y afinidad.
DAZN, Movistar Plus+, canales abiertos, madrugada y visionado parcial afectan al encaje en el
plan, sin modificar la nota del evento. Un canal distinto no se penaliza.

«Imprescindible» se reserva para notas desde 8. El mejor candidato de menor nota se presenta
como «Lo mejor del día»; si no hay candidatos suficientes, aparece «Día tranquilo».
La selección requiere 6,5; las alternativas 4,5. Se mantiene el máximo de cuatro citas y ocho alternativas.
No se cambian las notas por añadir o quitar otros partidos del día.

Los criterios y pesos iniciales están en `CRITERIOS.md`; las reglas en `resumen/puntuacion.py`.
No se han ajustado para reproducir las seis notas del evaluador: se prueban también favoritos,
finales de otros deportes, días flojos y cambios de canal/horario.
Los tests históricos de puntuación se adaptan a la nueva escala; las referencias originales de Colab
permanecen congeladas e intactas. Se conservan el disparo de las 05:00 Europe/Madrid, la ejecución
manual y football-data. No se ha enviado ningún correo desde las pruebas.

---

## Evolución del recomendador · fase 1: información incompleta

Se reconocen categorías de tenis por texto explícito o catálogo verificado de torneos de 2026,
con fuente en el calendario ATP. El catálogo incluye los cuatro Grand Slam, los nueve Masters 1000,
los dieciséis ATP 500 y tres ATP 250. Las categorías inferidas por nombre no se reutilizan
automáticamente en otras temporadas; hay que revisar el catálogo. Una categoría explícita
en la fuente prevalece sobre el catálogo. WTA, Challenger, ITF y categorías juveniles no se
confunden con el circuito ATP principal.

Un jugador sin bonus personal queda neutral: se elimina la resta adicional de dos puntos.
Una semifinal o final de torneo reconocido puede entrar aunque los jugadores no estén en la
lista personal. No se amplían por esta vía todas las primeras rondas.
Las competiciones de fútbol admitidas que no tenían regla de puntuación reciben una base neutral
de 1,5 puntos, equivalente a la de las otras ligas secundarias. No se cambian los umbrales del plan,
las puntuaciones de canales, los pesos de favoritos ni se convierte todavía la escala a notas /10.
Se incorporan alias de Lyon, Marsella, Newcastle, Benfica, Porto, Sporting y Sevilla.

El correo muestra etiquetas ATP 500, ATP 250, Masters 1000 o Grand Slam en los eventos reconocidos;
si falta la categoría, indica «Categoría por confirmar». Los modelos y prendas de camisetas siguen intactos.

80 pruebas: categorías por alias y temporada, prevalencia del dato explícito, neutralidad sin datos,
finales con jugadores fuera de lista, base de ligas incompletas, alias y metadatos en el correo/adjunto.
Horario mantenido: 05:00 Europe/Madrid. API football-data y ejecución manual sin cambios.

Fuentes:
- https://www.atptour.com/en/news/what-is-the-2026-atp-tour-calendar/
- https://www.atptour.com/-/media/files/media-guide/2026/2026-atp-media-guide-full-updated.pdf

---

## Tus plataformas destacadas

DAZN y sus canales aparecen con etiqueta amarilla y ✓; el canal general Movistar Plus+,
con etiqueta azul y ✓. Se aplica al resumen, al listado completo y al adjunto.
En texto también se añade ✓. Es el acceso declarado por el usuario, no una consulta a sus cuentas.
M+ LALIGA, Liga de Campeones, Vamos y Deportes se muestran de forma neutra: no se presume
que pertenezcan a la suscripción del canal general. Los demás eventos siguen disponibles.
Este cambio es visual y no altera las puntuaciones.

Por decisión del usuario, se mantiene la API football-data y `FOOTBALL_API_KEY` para complementar
la agenda al asociar camisetas con los partidos de hoy.

---

## Correo visual y listado completo

El correo presenta el imprescindible en una tarjeta destacada, horas grandes, nombres de equipos,
competición, puntuación y los canales concretos publicados. También conserva el partido de la
camiseta, su alternativa al azar y los avisos de visionado parcial o eventos en curso.

Al final del resumen se incluye «Ver todos los eventos filtrados», seguido del listado completo
en orden cronológico, sin limitarlo a los cuatro seleccionados ni a las ocho alternativas.
El mismo listado se adjunta como `todos_eventos.html`, para poder abrirlo aparte si el cliente
de correo no sigue enlaces internos o recorta un mensaje largo. No requiere alojar una web.
La vista previa local guarda también ese archivo. En modo camiseta no se añade una agenda vacía.

Se muestran los nombres de canales tal como los publica la fuente, incluidos M+ y sus variantes;
esto no implica que todos estén incluidos en Movistar Plus+ Lite o en tu plan DAZN.
No se han cambiado las puntuaciones de canales en esta actualización.
Se recupera además `eventoUnaColumna`: el nombre del gran premio o de la prueba que el scraping
anterior omitía en eventos sin local/visitante. Los filtros y umbrales deportivos no cambian.

Hay 73 pruebas correctas, incluyendo listado sin omisiones, orden cronológico, adjunto HTML,
canales publicados, escape de texto externo y extracción de descripciones de pruebas.
La muestra guardada del 25/10/2026 tiene 283 filas de eventos y 53 filtrados simulando las 08:30.
Las reglas actuales todavía dejan fuera deportes como motociclismo, golf, pádel o fútbol americano;
el automovilismo suele quedar por debajo del umbral del plan, pero aparece en el listado filtrado.

Para recibir la versión nueva: Actions → Resumen deportivo diario → **Run workflow** → rama **main**.
No uses «Re-run jobs» sobre una ejecución antigua para probar cambios de código: vuelve a ejecutar
el commit de aquella ejecución. La recepción que se mostró durante esta revisión correspondía
a la versión anterior a las mejoras funcionales.

---

## Mejoras funcionales: tercera tanda, camisetas

El correo muestra una camiseta vinculada a un partido de hoy cuando hay coincidencias en tu colección,
con rival, hora y competición, más una alternativa al azar. Si no hay coincidencias, muestra solo
la aleatoria. La alternativa es de otro equipo siempre que la colección lo permita.

Se priorizan Atlético y Aston Villa si juegan; después, el interés del partido y su hora.
El modelo se elige al azar entre las camisetas de ese equipo. No hay historial entre días,
por lo que una camiseta puede repetirse.

En modo `ambos` se aprovechan también los eventos de fútbol de la agenda, aunque no aparezcan
en el plan principal. En modo `camiseta` se usa la API como antes. Si falla una fuente, se intenta
aprovechar la otra; si no hay partidos disponibles, se conserva la elección al azar y el aviso de error.
Se mantiene `FOOTBALL_API_KEY`: no necesitas cambiar los secretos de GitHub.

Las 64 prendas siguen intactas. `data/alias_camisetas.json` relaciona nombres como «Sporting Lisboa»
y «Sporting CP», o «FC Porto» y «Porto», sin confundir clubes distintos como Celtic y Boston Celtics.
No se asignan a otro club los nombres ambiguos «Casablanca» u «Orlando» sin confirmación.

Hay 67 pruebas correctas, incluidas asociación, alias, alternativas, partidos cancelados o antiguos,
y fallos de fuentes. La prueba ficticia está disponible sin credenciales ni envío:

```powershell
python -m resumen --modo ambos --sin-conexion --salida vista_previa
```

Para probarlo por correo desde GitHub: Actions → Resumen deportivo diario → Run workflow → `ambos`.
El horario diario se ha adelantado a las 05:00 de Madrid para disponer del resumen al despertar.

---

## Mejoras funcionales: segunda tanda

La agenda respeta tu disponibilidad desde las 06:30 hasta las 00:00, ampliando las noches de
viernes y sábado hasta las 01:00 del sábado/domingo. Incluye la tabla del día siguiente si
está publicada; si falta, lo indica en el correo en lugar de inventar la cobertura nocturna.

Cada evento incluye fecha y final estimado. Si excede tu hora límite pero puedes ver al menos
30 minutos, aparece marcado como visionado parcial con la hora de corte. La madrugada pierde
un punto y el visionado parcial medio punto; siguen siendo candidatos si su interés es alto.
Al ejecutar manualmente se descartan los terminados y se señalan los eventos en curso.

El plan fija el imprescindible y recorre los candidatos restantes de mayor a menor puntuación,
comprobando solapamientos con duraciones estimadas por deporte. La presentación se mantiene
cronológica; las alternativas siguen ordenadas por puntuación. No se garantiza la combinación
con la mayor suma global de puntos, y las duraciones reales pueden variar.

Hay 57 pruebas: se comprueban también el cruce de medianoche, viernes/sábado/domingo,
los límites de disponibilidad, el visionado parcial, la lectura de la tabla de mañana y los
solapamientos por deporte. La selección de camiseta y los nuevos pesos deportivos/canales
todavía están pendientes; consulta `PREFERENCIAS.md` para ver el estado completo.

Prueba sin envío: `python -m resumen --modo eventos --salida vista_previa`.
Desde Actions, el modo `eventos` envía el resumen real con la nueva agenda y tus secretos actuales.

---

## Mejoras funcionales: primera tanda

Se han corregido las fases de eliminatorias, el bonus duplicado de Estudiantes, los alias de
equipos y el reconocimiento de competiciones. La calidad de un partido cuenta sus participantes
en lugar de etiquetas coincidentes. Se conservan todos los eventos seleccionados en el plan y
las alternativas se ordenan por puntuación antes de limitarse a ocho.

Las preferencias indicadas por el usuario y el estado de cada mejora están en `PREFERENCIAS.md`.
El horario de disponibilidad, los nuevos pesos deportivos, los canales concretos y la recomendación
de camiseta por evento todavía no se habían aplicado en esta tanda. El horario diario actual es las 05:00.

Hay 49 pruebas. Las siete pruebas de referencia mantienen congelado el comportamiento original;
las pruebas del recomendador actual comprueban ya las correcciones aprobadas, sin exigir que
se reproduzcan los errores originales. Las secciones de migración siguientes se conservan como
registro histórico; las referencias a alternativas por hora corresponden a aquella versión.

Para probar el nuevo resumen sin enviar correo:

```powershell
.\.venv\Scripts\python.exe -m resumen --modo eventos --salida vista_previa
```

Desde GitHub, ejecutar manualmente «Resumen deportivo diario» en modo `eventos` envía un
correo real con la nueva lógica. No es necesario cambiar secretos ni la configuración horaria.

---

## GitHub Actions: ejecución diaria y desde el móvil

Repositorio: https://github.com/Killherrero13/RECOMENDADOR-DEPORTIVO

El workflow «Resumen deportivo diario» programa ambos procesos a las **05:00 Europe/Madrid**.
La zona horaria del propio schedule contempla invierno y verano; GitHub puede iniciar
la ejecución con retraso. El correo llegará después de completar las consultas y el envío.
Se adelantó desde las 08:30 el 26/10/2026 para dejar margen antes de despertarse;
si el correo no ha llegado, sigue disponible la ejecución manual desde el móvil.
El workflow debe estar en la rama predeterminada del repositorio para programarse.

### Configura estos cuatro secretos

En Settings → Secrets and variables → Actions → New repository secret:

| Nombre exacto | Valor |
| --- | --- |
| `FOOTBALL_API_KEY` | La clave de football-data que ya probaste |
| `SMTP_USERNAME` | La dirección Gmail desde la que enviaste la prueba |
| `SMTP_PASSWORD` | La contraseña de aplicación de Google que ya funcionó |
| `EMAIL_TO` | La dirección donde quieres recibir el resumen |

Enlace directo: https://github.com/Killherrero13/RECOMENDADOR-DEPORTIVO/settings/secrets/actions

No se necesita `EMAIL_FROM`: el remitente será `SMTP_USERNAME`. No subas archivos `.env`,
contraseñas ni claves al repositorio. No se imprimen los secretos en los logs.
Los secretos solo se entregan al paso de ejecución real; las pruebas no los reciben.

### Primera ejecución desde GitHub

1. Abre Actions → «Resumen deportivo diario» → Run workflow.
2. Deja la rama predeterminada y selecciona `ambos`.
3. Pulsa Run workflow una vez. Esa ejecución envía un correo real.
4. Comprueba el estado de la ejecución y la recepción en Gmail.

Después podrás lanzarlo igual desde el navegador del móvil y elegir `ambos`, `eventos` o `camiseta`.
Cada lanzamiento manual envía un correo nuevo; no se aplica deduplicación entre lanzamientos.
No hace falta mantener encendido tu ordenador.

### Qué comprueba GitHub

- «Comprobaciones sin correo» se ejecuta al subir cambios o abrir una propuesta de cambios.
  Instala dependencias y ejecuta las 41 pruebas sin contactar con las fuentes ni Gmail.
- El workflow diario también ejecuta las pruebas antes de consultar y enviar.
- Si falla una fuente, se envía lo disponible con aviso y la ejecución queda en rojo.
- Si falla Gmail, la ejecución queda en rojo. Revisa la bandeja antes de repetir para evitar duplicados.
- Solo se permite una ejecución del resumen a la vez; una nueva no cancela un envío en curso.
- Los jobs tienen límite de diez minutos y permisos de lectura del repositorio.
- No se publican los resúmenes como artefactos de GitHub. Quedan el correo y los logs de diagnóstico.

Activa las notificaciones de fallos de Actions en tu configuración de GitHub. Si el repositorio
es público, GitHub puede desactivar la programación tras 60 días sin actividad: comprueba el
workflow si deja de llegar el correo. En privado, revisa también el cupo mensual de tu cuenta.

La recepción real con Gmail en local fue confirmada por el usuario. La Fase 6 solo quedará
validada tras una ejecución manual correcta en GitHub y después la primera ejecución programada.

Documentación: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#onschedule

---

## Fase 5: envío por Gmail

Se incorpora `resumen/correo.py`, usando solo bibliotecas estándar de Python.
El envío es opcional: únicamente ocurre al añadir `--enviar`.
La presentación de la Fase 4 fue revisada y aceptada por el usuario.

### Primera prueba real: un correo de demostración

1. Activa la verificación en dos pasos en la cuenta Gmail que enviará el resumen.
2. En https://myaccount.google.com/apppasswords crea una contraseña de aplicación
   con nombre «Resumen deportivo». No utilices tu contraseña habitual de Google.
3. Desde la carpeta del proyecto, ejecuta:

```powershell
.\probar_correo.ps1
```

El asistente pide la cuenta remitente, el destino (Enter para enviártelo a ti mismo)
y la contraseña de aplicación oculta. Envía un único email marcado `[DEMO]` con HTML y texto.
No consulta football-data ni la web de eventos. Las variables temporales se restauran al terminar;
no se escribe la contraseña en archivos. No pegues esa contraseña en el chat.
Si PowerShell impide ejecutar el archivo, puedes ejecutar esta alternativa que aplica solo a ese proceso:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\probar_correo.ps1
```

Si tu entorno no existe aún, créalo con las instrucciones de la Fase 2.
Comprueba recepción y presentación en Gmail desde el móvil. Si no lo ves, revisa Spam y Enviados.
El mensaje «Gmail ha aceptado el correo para su entrega» confirma aceptación SMTP;
la recepción en la bandeja debe comprobarse por separado.

Google requiere verificación en dos pasos para las contraseñas de aplicación; la opción puede no
estar disponible con Protección Avanzada o determinadas cuentas administradas. Si falta esa opción,
indícalo antes de continuar: habría que valorar OAuth u otro servicio de envío.
Fuente: https://support.google.com/accounts/answer/185833?hl=es

### Configuración para ejecución normal y futuro GitHub Actions

Variables obligatorias: `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_TO`.
`EMAIL_FROM` es opcional y debe coincidir con `SMTP_USERNAME` si se indica.
Solo se admite un destinatario para esta automatización personal.
El servidor se fija a `smtp.gmail.com`, puerto 465, con TLS desde el inicio y validación del certificado.
No se necesitan más paquetes de Python.

Con las variables configuradas en el entorno:

```powershell
# Genera y envía ambos resultados reales; requiere también FOOTBALL_API_KEY.
.\.venv\Scripts\python.exe -m resumen --modo ambos --enviar --salida vista_previa
# Solo eventos reales; no necesita FOOTBALL_API_KEY.
.\.venv\Scripts\python.exe -m resumen --modo eventos --enviar
```

Sin `--enviar` no se conecta con Gmail. Tampoco se consultan las fuentes deportivas si
se solicita envío pero falta la configuración de correo.
Si falla una fuente se envía el resumen parcial; si fallan ambas se envía el aviso de fallo.
En ambos casos la ejecución termina en error, aunque el correo se haya enviado.
Un fallo SMTP también produce salida 1. Se permiten hasta tres intentos solo ante un rechazo
temporal explícito (4xx) o una interrupción de red anterior a la entrega. Si la conexión cae durante
la entrega sin respuesta definitiva, no se reintenta: el correo podría haber sido aceptado.
Los errores muestran fase y códigos SMTP, nunca contraseñas, direcciones ni respuestas crudas.

### Verificación

41 pruebas automáticas correctas, incluidas ocho nuevas para configuración, mensaje multipart,
conexión cifrada, autenticación, fallos sanitizados, destinatario rechazado, envío explícito
y envío parcial con estado de error. SMTP está simulado en las pruebas: no se ha enviado ningún
correo real desde este entorno. Se ha comprobado también la sintaxis del asistente PowerShell.

La prueba real de recepción queda pendiente de tu ejecución. No avanzaremos al workflow diario
hasta confirmar que recibes y lees correctamente ese primer correo.

---

## Fase 4: resumen combinado y vista previa

El nuevo coordinador ejecuta los procesos de forma independiente. Genera una única presentación
en HTML adaptable al ancho de pantalla y texto, sin enviar correo. Las reglas de recomendación
no han cambiado. Las fases 2 y 3 fueron probadas y confirmadas como correctas por el usuario.

### Revisión visual sin credenciales

Desde esta carpeta:

```powershell
.\.venv\Scripts\python.exe -m resumen --sin-conexion --salida vista_previa
Start-Process .\vista_previa\resumen.html
```

El ejemplo está marcado como DEMO y contiene datos ficticios. También puedes abrir directamente
`vista_previa/resumen.html`, ya generado en esta entrega. Al estrechar la ventana a un ancho
similar al de un móvil, el texto debe ajustarse sin desplazamiento horizontal.
La apariencia final en cada aplicación de correo se comprobará al enviar el primer mensaje en la Fase 5.

### Tres modos

```powershell
# Ambos procesos; requiere FOOTBALL_API_KEY configurada en el entorno.
.\.venv\Scripts\python.exe -m resumen --modo ambos --salida vista_previa
# Solo eventos; no requiere clave.
.\.venv\Scripts\python.exe -m resumen --modo eventos --salida vista_previa
# Solo camiseta y los partidos de la API.
.\.venv\Scripts\python.exe -m resumen --modo camiseta --salida vista_previa
```

El modo por defecto ahora es `ambos`. Para introducir la clave sin guardarla en el historial,
utiliza el bloque de PowerShell de la Fase 2, cambiando su orden de ejecución por:

```powershell
.\.venv\Scripts\python.exe -m resumen --modo ambos --salida vista_previa
```

`--salida` guarda `resumen.html` y `resumen.txt`, sobrescribiendo la vista previa anterior.
Sin esa opción se muestra solo la versión de texto en la terminal.

### Contenido y fallos parciales

- Camiseta elegida y aviso honesto de que no tiene partido asociado.
- Imprescindible, plan principal y alternativas, conservando su orden original por hora.
- En modo combinado con eventos disponibles no se repite la lista de partidos de football-data.
- En modo camiseta, o si falla eventos, sí se muestran los partidos disponibles de football-data.
- Un fallo de una fuente no impide intentar la otra. Se incluye un aviso y el asunto lleva
  `[CON ERRORES]`. También se guarda la vista previa parcial y se devuelve código 1.
- Si fallan ambas fuentes, se genera el aviso de fallo total, también con código 1.
- Código 0 significa que todos los procesos solicitados terminaron correctamente.
- Los errores inesperados se registran con el tipo de excepción, sin incluir su detalle potencialmente sensible.
- Los textos de fuentes externas se escapan antes de insertarlos en HTML.

Comprobación automática: 33 pruebas correctas, incluidos los tres modos, guardado UTF-8,
equivalencia de contenido HTML/texto, escape HTML y fallos parciales y totales simulados.
No se ha ejecutado aquí el modo combinado con tu credencial real: las fuentes por separado ya
están validadas, y la integración se prueba con datos controlados sin acceder a tu clave.

Tu siguiente paso es revisar la vista previa y confirmar que el contenido y la presentación
te sirven. La siguiente fase añadirá el envío SMTP; todavía no hay configuración ni envíos de correo.

---

## Fase 3: eventos fuera de Colab

Se han separado descarga y extracción (`resumen/fuente_eventos.py`), preferencias
(`resumen/preferencias_eventos.py`) y recomendación (`resumen/eventos.py`).
Las funciones de puntuación y agenda, los filtros y sus constantes se han conservado del original.
No se realizan consultas al importar los módulos.

### Tu prueba

Desde esta carpeta, utilizando el entorno creado en la Fase 2:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m resumen --modo eventos
```

Esta ejecución no requiere clave API ni envía correo. Contrasta el imprescindible, el plan
y las alternativas con el cuaderno ejecutado el mismo día. Si coinciden, queda validada la fase.
La ejecución de camisetas sigue disponible con `--modo camiseta` (también es el modo por defecto).
Para un ejemplo ficticio sin conexión, añade `--sin-conexion` a cualquiera de los dos modos.
El modo combinado se incorporará en la Fase 4.

### Verificación realizada

- 25 pruebas automáticas correctas: las 19 anteriores y seis de eventos.
- Descarga real HTTP 200 el 25/10/2026, con tres tablas: hoy y próximos días.
- 283 eventos en la primera tabla, cuya cabecera indica 25/10/2026.
- Se guardó ese HTML en `tests/fixtures/eventos_real_2026-10-25.html` para repetir las pruebas sin conexión.
- Los 283 eventos extraídos coinciden con el scraping original sobre el mismo HTML.
- Los filtros, puntuaciones, plan y alternativas coinciden con el original tanto en el día
  ficticio de referencia como en el HTML real guardado.
- Se comprueba que la recomendación no modifica los eventos de entrada.

La muestra HTML es solo material de prueba; nunca se utiliza como sustituto de una descarga fallida.
Todavía queda comprobar el acceso desde los servidores de GitHub Actions en la fase de despliegue.

### Errores y límites

La descarga usa tiempos máximos y hasta tres intentos para errores de conexión y HTTP 5xx.
HTTP 403/429, tabla ausente, fecha ausente o distinta de la esperada y tabla sin eventos
reconocibles producen un mensaje claro y salida 1, en lugar de una agenda vacía silenciosa.
Una tabla vacía se trata de manera conservadora como error de fuente; aún no tenemos una
muestra fiable de cómo representa la web un día sin emisiones.
Una tabla con eventos válidos pero ninguno que supere los filtros sí genera un resultado vacío válido.

Se conservan las horas publicadas por la web, que no incluyen zona horaria explícita en cada fila;
se usa la fecha de Madrid para validar la cabecera. No se ha añadido exclusión de eventos ya
pasados ni corregido los comportamientos de puntuación y agenda documentados en la Fase 1.
Las alternativas mantienen su orden original por hora.

---

## Fase 2: camisetas fuera de Colab

El módulo `resumen/camisetas.py` lee la colección JSON, consulta football-data y devuelve
un resultado estructurado. La elección sigue siendo aleatoria y no se vincula a los partidos.
Los originales de `referencia/` permanecen intactos.

Necesitas Python 3.12 o posterior. Desde esta carpeta, en PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m resumen --sin-conexion
```

La última orden muestra una demostración ficticia; no consulta la API ni necesita clave.
En Linux utiliza `.venv/bin/python` en lugar de `.\.venv\Scripts\python.exe`.
Las dependencias de esta fase son `requests` y, solo en Windows, `tzdata`.
Beautiful Soup se incorporará cuando migremos eventos.

### Prueba real pendiente

Para probar la API real sin guardar la clave en archivos ni en el historial de órdenes,
desde esa misma carpeta en PowerShell:

```powershell
$claveTemporal = Read-Host 'Introduce tu FOOTBALL_API_KEY' -AsSecureString
$env:FOOTBALL_API_KEY = [System.Net.NetworkCredential]::new('', $claveTemporal).Password
try {
    .\.venv\Scripts\python.exe -m resumen
} finally {
    Remove-Item Env:FOOTBALL_API_KEY -ErrorAction SilentlyContinue
    Remove-Variable claveTemporal -ErrorAction SilentlyContinue
}
```

La clave se usa durante la ejecución y se elimina de esa sesión al acabar. No la pegues en el chat.
`.env.example` documenta el nombre; el programa no carga archivos `.env` automáticamente.
Más adelante configuraremos el mismo nombre como GitHub Secret.

Resultado esperado: camiseta, fecha de Madrid y partidos disponibles con su hora y competición.
Una lista vacía es válida; un problema de autenticación, límite, conexión o respuesta inválida
produce un mensaje de error y código de salida 1. El correo todavía no está implementado.
Para completar la comprobación real, comunica si la ejecución termina correctamente; si falla,
comparte solo el mensaje de error del programa, sin la clave.

### Robustez implementada

- Tiempo máximo de conexión de 5 segundos y de lectura de 20 segundos por petición.
- Hasta tres intentos para fallos de conexión, espera agotada y HTTP 5xx, con pausas de 1 y 2 segundos.
- HTTP 401, 403 y 429 se explican sin repetir consultas innecesarias.
- No se siguen redirecciones con la cabecera de autenticación.
- No se imprimen la clave, las cabeceras, el cuerpo HTTP ni las excepciones de red originales.
- Validación del JSON y de los campos necesarios de cada partido del día.
- Consulta por fechas UTC suficientemente amplia y filtrado por día de Madrid. Esto corrige
  la omisión de encuentros cercanos a medianoche, sin cambiar la selección de camiseta.
- Se mantiene el filtro de presentación de dos horas desde el inicio del partido.

La API v4 documenta `dateTo` como exclusivo:
https://docs.football-data.org/general/v4/index.html
La cobertura de partidos sigue dependiendo de tu suscripción a football-data.
No se han añadido pesos, historial ni filtros por estado del partido.

Las pruebas adicionales comprueban la equivalencia de selección con 20 semillas, cambio de hora,
medianoche, errores HTTP, reintentos, respuestas inválidas y resultado estructurado.
La prueba real de API fue realizada por el usuario y confirmada como correcta.

---

## Referencia de la Fase 1

Esta entrega fija una referencia verificable antes de migrar los programas de Colab.
Todavía no es una automatización: no consulta servicios, no usa credenciales y no envía correo.

## Archivos

- `referencia/`: copias byte a byte de los dos archivos recibidos y sus huellas SHA-256.
- `data/camisetas.json`: las 64 camisetas originales, conservando orden, campos y tipos.
- `tests/fixtures/eventos.json`: 13 eventos ficticios para comprobar filtros y agenda.
- `tests/fixtures/resultado_esperado.json`: resultado de referencia revisado, con 9 eventos tras el filtrado.
- `tests/referencia.py`: carga la lógica original mediante el árbol sintáctico de Python; omite las consultas, los imports externos y la ejecución de Colab.
- `tests/test_referencia.py`: siete pruebas sin conexión con la biblioteca estándar.

## Cómo comprobar esta fase

Con Python 3.12, desde esta carpeta:

```console
python -m unittest discover -s tests -v
```

No hay paquetes que instalar para esta fase. Las cadenas de formato del original de eventos requieren Python 3.12 o posterior.
No ejecutes las copias de `referencia/` para esta comprobación: conservan las dependencias y consultas de los originales.

## Resultado del día ficticio

| Hora | Evento | Puntuación | Resultado |
| --- | --- | --- | --- |
| 09:00 | Alcaraz – Sinner, ATP 500 Semifinal | 12 | Mañana |
| 11:00 | Estudiantes – Valencia, Liga Endesa | 15,5 | Imprescindible |
| 13:00 | Arsenal – Chelsea, Premier League | 9,144 | Mediodía |
| 15:00 | At. Madrid – Real Madrid, LaLiga | 11,96 | Tarde |
| 16:00 | Fórmula 1 Carrera | 4,5 | Fuera del plan y alternativas |
| 17:00 | Liverpool – Arsenal, Champions League Semifinal | 14,104 | Alternativa |
| 17:15 | FC Barcelona – Valencia, LaLiga | 9,4876 | Alternativa |
| 20:00 | Aston Villa – Chelsea, Premier League | 9,084 | Alternativa |
| 22:00 | Celtics – Warriors, NBA | 11,8 | Alternativa |

Se excluyen el evento de las 08:00, la hora `PD`, el evento femenino y Primera Federación, según los filtros originales.

## Comportamiento que se conserva

- La camiseta se elige al azar entre las 64 entradas, sin pesos ni relación con los partidos; puede repetirse entre días.
- No existe persistencia ni historial de uso.
- Estudiantes suma dos veces el bonus de 4 puntos.
- `Semifinal` recibe 2,5 puntos porque contiene `final`.
- La agenda toma el imprescindible por puntuación y después recorre el resto por hora; se limita a cuatro seleccionados.
- Dos seleccionados de una misma franja pueden sobrescribirse en el plan visible.
- Las alternativas se ordenan por hora, no por puntuación global.
- El solapamiento permitido es de hasta 30 minutos, con duración estimada de 120 minutos para todos los deportes.
- El filtro efectivo empieza a las 09:00 aunque `DAY_START` indique las 07:00.

Estos comportamientos quedan documentados; no se han corregido en esta fase.

## Alcance de la verificación

Las pruebas comprueban integridad, extracción de la colección, selección aleatoria controlada,
filtros, puntuaciones, agenda, alternativas, ausencia de eventos y límite de solapamiento.
El resultado esperado se obtuvo del original y se revisó; sirve como referencia para contrastar
la futura implementación, no como demostración de que las reglas actuales sean las deseadas.
No se ha verificado aún la API real, el HTML real, SMTP ni la ejecución en GitHub Actions.

## Tu revisión antes de la Fase 2

1. Revisa la colección JSON y la tabla del día ficticio.
2. Confirma que podemos conservar estos comportamientos como referencia de la migración.
3. Si quieres repetir la prueba, utiliza el comando anterior; si no tienes Python local, no es necesario instalarlo para revisar esta entrega.

La extracción original se conserva como referencia. El proceso de camisetas ya se ha preparado en
la Fase 2 descrita arriba. Las credenciales se configuran en el entorno correspondiente, nunca en este documento ni en el chat.


### Explicaciones de las recomendaciones
Cada tarjeta, el texto y el listado adjunto muestran motivos derivados del modelo: cartel, fase, afinidad y acceso declarado. Se distingue el umbral del plan de los solapamientos con eventos elegidos (con duraciones estimadas). No se añaden noticias, forma ni clasificación sin verificar. Las notas y la selección permanecen iguales.


### Planning flexible
El correo presenta una línea temporal de citas principales y opciones voluntarias. Como máximo un aperitivo por cita, de 30 a 60 minutos, con cambio explícito aunque se deje el final sin ver. Una sola opción de fondo, sin solapamientos ni alargar la noche. Los huecos quedan libres; las notas no cambian. Los finales son estimados y no se presume el resultado del partido.


### NBA en diferido sin spoilers
El envío diario añade `--nba` para incluir una sección independiente en modos ambos/eventos. Consulta ESPN por fechas UTC y filtra inicios entre ayer 06:30 y hoy 06:30 Madrid, solo con final confirmado al consultar. El envío a las 05:00 puede tener partidos pendientes; no se reenvía automáticamente al finalizar. Un fallo NBA conserva las otras secciones y marca error parcial.

No se publican marcadores, notas, ganadores ni pistas del desenlace; orden alfabético y etiquetas ver completo/resumen/puedes saltártelo. Conserva las 25 afinidades originales; los cinco equipos ausentes son neutrales. Criterio NBA v2: curva gradual de margen final (80%) y afinidad (20%), con pequeño refuerzo Celtics (+0,04). Sin clasificación ni premio por puntos totales. Umbrales internos: completo 0,74 y resumen 0,50; resto puedes saltártelo. El margen final no representa toda la evolución del encuentro. No alteran notas, camisetas ni planning de directos.

Cuaderno independiente: `cuadernos/ScriptPartidosNBA_actualizado.ipynb`. No requiere claves; instalar requests/tzdata si faltan. La fuente pública puede cambiar. Mejora futura propuesta: comparar porcentajes de victorias con fecha verificada y estudiar evolución por cuartos, sin revelar esas señales en el correo.


La NBA se presenta en un solo bloque naranja con cabecera azul oscuro, tarjetas naranjas y cobertura dentro del mismo bloque. El color es común a todos los partidos; la categoría se comunica por texto. No se muestran notas ni motivos que anticipen el desenlace.


### Bloque visual de camisetas
Una tarjeta independiente en morado y dorado agrupa recomendación por partido y elección al azar. Crema para la asociada al partido, lila para azar, ambas etiquetadas por texto. Si no existe partido asociado, solo se presenta elección al azar. Se conservan selección, API y detalles del partido.


Orden del correo: camisetas, NBA, cita destacada, planning diario y todos los eventos filtrados. El planning se agrupa en un bloque verde petróleo con línea temporal y alternativas dentro del mismo bloque; la información general queda dentro del listado final. Los avisos de ejecución y demostración se mantienen visibles.


### Ajustes tras el correo del 27/10/2026
Celtics siempre Resumen en diferido y verde en todas las tarjetas. Las ocho alternativas se eligen por interés/encaje y se presentan por fecha y hora. Equipos prioritarios antes de competición: Atleti/España rojo y Aston Villa burdeos. Champions azul, Europa League naranja, Conference verde, ligas de fútbol verde azulado; tenis amarillo pelota; NBA naranja, ACB azul claro, Euroliga violeta. El destacado tiene fondo azul oscuro propio y contorno dorado, independiente del deporte. Se aplica en tarjetas, planning, listado completo y adjunto; DAZN/Movistar conservan sus distintivos. Sin spoilers ni cambios en las notas del resto.


Distintivos NBA grandes: completo en verde con ▶, resumen en ámbar con ▷ y puedes saltártelo en gris con —. La tarjeta conserva el color del equipo/deporte. Copas nacionales de fútbol y baloncesto en frambuesa, diferentes de las ligas; se mantiene prioridad de equipos y torneos europeos. No cambian recomendaciones ni orden.


### Fase 1: reconocimiento de equipos y jugadores
Catálogo editorial de perfiles en resumen/perfiles.py, sin afirmar rankings ni forma actuales. Alias exactos por deporte normalizan Barça Basket, FC Bayern Basketball, Fenerbahce Istanbul, Panathinaikos BC, AX Olimpia Milano y otros. Euroliga y ACB tienen referentes separados; Euroleague equivale a Euroliga. No se aumenta su base: dos referentes mantienen +1,5 y uno +0,8. NBA en diferido y fútbol no cambian.

Tenis: figura editorial +1,2 por jugador, referente +0,5 y cruce entre dos reconocidos +0,5 adicional. Se incluyen Paul y Khachanov, además de Shelton, Tiafoe y Musetti. La afinidad conserva su peso, usando el máximo de ambos jugadores y coincidencia por palabras, independiente del orden. El mismo catálogo decide reconocimiento y filtrado. Ronda y categoría mantienen sus pesos. No hay bonus por nacionalidad, juventud, ranking, rachas ni contexto no disponible. Landaluce queda pendiente de fase 2; desconocido no significa jugador de bajo nivel.


### Fase 2: contexto deportivo con fecha y fuentes
En ejecución conectada se consulta contexto antes de calcular notas y planning. No requiere claves nuevas. Cuando el contexto modifica la nota, las tarjetas y el adjunto muestran ajuste efectivo, consulta y fuentes. El texto y la comparación conservan también la trazabilidad de datos validados sin bonus. El modo de demostración sigue sin hacer consultas.

Cobertura: ligas españolas de Primera/Segunda, Premier League, Serie A italiana, Bundesliga y Ligue 1 (ESPN), Euroliga (calendario oficial y clasificación de la última jornada completa), y contraste de categorías en primera ronda de Copa del Rey 2026/27. También ranking ATP fechado (ESPN), con identidad exacta de ambos jugadores y categoría ATP identificada. El catálogo de alias usa coincidencias exactas y nombres alternativos de la fuente, sin aproximaciones por subcadenas. Si identidad u horario difieren, no se asigna contexto.

Validación: temporada correcta, fecha anterior al evento y consulta con antigüedad máxima de 36 horas respecto al inicio. Los resultados deben ser finales y haber empezado al menos tres horas antes del corte. En ligas, el total de partidos y balance de cada club debe coincidir con la clasificación. En Euroliga, el calendario completo y los resultados anteriores al corte deben coincidir con el balance de la tabla; si hay partidos adicionales de una jornada incompleta, se conserva la nota básica para los equipos cuyo balance ya no coincide. No se trasladan tablas actuales a partidos ya iniciados. Con menos de cinco partidos de liga por equipo no se aplican ajustes de clasificación/forma.

Señales y límites: zona alta de ambos equipos (puestos 1–5) +1,0; zona alta y al menos una racha de tres victorias +1,3; ambos con tres victorias seguidas +1,0; un equipo entre los tres primeros +0,5; top-3 invicto con al menos 80% de victorias +1,2; cuatro victorias en los últimos cinco +0,6; tres victorias seguidas +0,5. Se usa SOLO la señal mayor, con techo de +1,5; no se suman posición, invicto y forma. Los cinco últimos se ordenan del más reciente al más antiguo y pertenecen a esa competición.

Copa: +0,6 únicamente cuando un partido identificado por nombres, roles, fecha e inicio enfrenta a un local fuera de Primera con un visitante de Primera, con eliminatoria a partido único confirmada para la edición. La pertenencia se verifica con IDs de los clubes y la lista completa de veinte equipos de Primera. No se infiere una categoría concreta del modesto ni se aplica un bonus general de Copa. Otras ediciones, rondas, datos ambiguos y partidos sin contraste no reciben ese extra.

Ausencias y fallos: se conserva la nota básica, sin castigo y con aviso de cobertura agregada. Consultas agrupadas por liga, hasta tres ligas en paralelo y presupuesto de 45 segundos (una petición ya iniciada puede añadir unos segundos). Un fallo del contexto no cambia el envío del resto de la agenda. La NBA en diferido no cambia. Continúan pendientes la forma reciente y resultados detallados de tenis, estilos de juego, vulnerabilidad específica en Copa y nuevas competiciones. La disponibilidad y los solapamientos solo afectan al encaje, no a la nota.

Ranking ATP: publicación no futura y de antigüedad máxima diez días. Contexto deportivo +0,6 si ambos son top-10, +0,4 si uno es top-10 y el otro top-30, o +0,2 si ambos son top-30. No son acumulativos. Joven español de 18–22 años en top-100 ante top-10: +0,6 a AFINIDAD, no al interés deportivo. No se afirma progresión reciente a partir de edad o ranking. Se muestran fecha de publicación y consulta; sin identidad unívoca o ranking vigente se conserva la base. El distintivo Contexto muestra la diferencia efectiva sobre la nota básica tras aplicar límites.


### Diagnóstico e identidad — primera entrega del plan del 28/10
El contexto se solicita después de aplicar los filtros, únicamente para los eventos relevantes; no cambia la lista de competiciones aprobadas. Cada evento registra estado y motivo: validado con/sin ajuste, parcial, nombre no resuelto/ambiguo, falta de fuente, temporada, fecha, historial incoherente, ranking y tiempo agotado. Un participante sin datos no borra el diagnóstico del otro: se conserva el dato parcial, sin usarlo todavía para puntuar.

Se verificaron los códigos oficiales de Efes (IST), Hapoel (HTA), ASVEL (ASV), Partizan (PAR), Virtus (VIR) y Žalgiris (ZAL). Se normalizan patrocinadores sin añadir estos equipos automáticamente al catálogo de élite. En Euroliga, tabla e histórico se limitan a la misma jornada completa anterior al corte; se muestra la jornada utilizada en los datos guardados. Esto puede recuperar contexto que se perdía por mezclar jornadas.

Al guardar el informe conectado se generan diagnostico.json y diagnostico.html. La instantánea incluye agenda relevante, datos de contexto utilizados, corte, desglose y huella del modelo/catálogos. No incluye correo personal, contraseñas, claves ni marcadores NBA. Se puede reproducir sin red con resumen.diagnostico.reproducir(snapshot), que rechaza versiones de modelo distintas. No almacena las respuestas completas de proveedores: conserva los datos que intervienen en la puntuación.

GitHub conserva ambos diagnósticos como artefacto durante 14 días, incluso ante fallos parciales; un fallo de almacenamiento no bloquea el envío. No se adjuntan al correo diario. No se han modificado pesos, bases ni umbrales. La calidad conjunta, rivalidades y narrativa copera corresponden a las siguientes entregas.
# Añadir eventos a Google Calendar

Las tarjetas y el listado completo incluyen «Añadir partido completo». El planning incluye «Añadir tramo recomendado», con el intervalo concreto de visionado. Se abre Google Calendar con título, fecha, horas, canales y descripción; el usuario revisa y pulsa Guardar. Elegir **Partidazos** en el selector de calendario antes de guardar. El enlace documentado no garantiza preseleccionar un calendario secundario y no escribe directamente en la cuenta.

Las horas se codifican en UTC con zona Europe/Madrid y el final se marca como estimado. No hay sincronización posterior de cambios, prevención de duplicados ni acceso a credenciales de Calendar. La NBA en diferido mantiene su bloque sin reservas automáticas. Los enlaces solo aparecen cuando hay una fecha válida.

Referencia: [enlaces de creación preparados por Google](https://developers.google.com/workspace/calendar/api/concepts/inviting-attendees-to-events).

## Calibración y rivalidades — 30/10/2026

El registro `data/rivalidades.json` contiene 46 parejas: 42 de fútbol y cuatro de baloncesto. Se añadieron 24 parejas documentadas, con cobertura de España, Inglaterra, Alemania, Italia y Francia; además Portugal, Escocia y cuatro cruces de selecciones. Brasil conserva Mineiro–Cruzeiro. El catálogo es selectivo, no una lista exhaustiva de todas las rivalidades existentes. Cada pareja incluye fuente, fecha de revisión, ámbito y región. Los ajustes son decisiones editoriales moderadas, no puntuaciones dictadas por las fuentes.

Los nombres alternativos exactos se mantienen en `data/alias_rivalidades.json`. No se usa coincidencia aproximada: no basta con compartir país, ciudad o un fragmento del nombre. El bonus de rivalidad sigue limitado a +0,6, una sola vez, independiente de la competición. Las parejas de selecciones solo funcionan en competiciones internacionales identificadas; juveniles y categorías femeninas no heredan estas parejas. Este registro no modifica las competiciones admitidas por el filtro.

NBA en directo: la consulta pública de ESPN identifica el encuentro por nombres exactos del proveedor, roles local/visitante, identificadores y hora UTC (tolerancia 15 minutos). Solo acepta estado previo al inicio. La fase debe aparecer explícitamente en las notas del encuentro: grupos +0,3, cuartos +0,6, semifinal +0,9, final +1,2. Si el título ya aporta un premio de ronda, se completa hasta el mayor de los dos premios; no se suman. Una fecha de viernes, fase desconocida o partido no identificado no concede el extra. Un fallo de la fuente conserva la valoración básica. Se guardan únicamente nombres, IDs, fecha, fase y fuentes; nunca marcadores, ganadores o estadísticas NBA. La consulta usa el mismo límite temporal y presupuesto de 45 segundos que el resto del contexto.

Por petición del usuario, Knicks, 76ers, Heat y Thunder quedan neutrales tanto en agenda como en diferido. Celtics conserva su afinidad y la regla «siempre Resumen» en diferido. No se ha añadido contexto de clasificación/rachas NBA en directo: esa cobertura requiere validar muestras y balances antes de puntuarla.

Efes, Partizan, Žalgiris y Virtus reciben reconocimiento histórico de +0,35 por equipo solo en Euroliga; el cartel total se limita a +1,5. No se equiparan automáticamente al resto del catálogo de referentes, ni se afirma buena forma actual por su historia. Fuentes: [palmarés oficial](https://mediacentre.euroleague.net/en/app/2/communication/communication/preview/523), [palmarés actualizado](https://mediacentre.euroleague.net/en/app/2/communication/communication/preview/23235). Berrettini entra como reconocido (+0,5 individual), sin extra de pareja élite por ese perfil; [perfil ATP](https://www.atptour.com/en/players/Matteo%20-Berrettini/BK40/overview). Permanecen la preferencia personal del tenis −0,4 y el umbral de plan 7,5.

En fútbol, una diferencia de diez posiciones o más, con al menos cuatro victorias del mejor clasificado y cuatro derrotas del otro en sus últimos cinco partidos validados de la misma liga, limita a +0,6 el extra contextual. No resta a la base deportiva. No actúa con forma parcial, distancia menor o rachas no opuestas. El motivo y la moderación se conservan en el diagnóstico y las tarjetas.

La regresión compara las mismas entradas fechadas de los días 27 y 28 (87 eventos), con sus fuentes guardadas y sin red. Una vista previa con la agenda guardada del 30 y contexto consultado después se etiqueta como simulación actual, nunca como reproducción del correo matinal. Las pruebas cubren simetría de parejas, alias, ámbito de selecciones, controles sin rivalidad, NBA Cup por encuentro, fase desconocida, metadatos sin spoilers, preferencias y moderación de forma.

## Incidencia de envío — 02/11/2026

El historial público muestra éxito el 31/10 y fallo los días 1 y 2/11 con la misma versión `5b73e20`. El log aportado confirma que se guardó el resumen y después hubo un fallo SMTP. El mensaje anterior ocultaba la clase/código del error; por tanto no permite atribuirlo a contraseña, cuota, contenido o red. No se ha probado un envío real durante la reparación ni se han leído credenciales. La causa original sigue pendiente de una respuesta SMTP identificable.

El envío registra ahora fase (conexión, autenticación, entrega), tipo fijo de error, código SMTP y código ampliado, con lista cerrada de campos. No se conserva la respuesta libre del servidor, que puede incluir datos personales. Con `--salida`, se escribe `envio.json` tanto ante aceptación como ante error. El fallo al guardar ese diagnóstico no cambia una entrega ya aceptada. Un cierre QUIT fallido después de aceptación sigue sin marcar fallo ni repetir el correo.

Reintentos: máximo tres conexiones, con esperas de 5 y 15 segundos, conservando el mensaje y su Message-ID. Solo se repite tras un rechazo explícito temporal 4xx o una interrupción de red previa a la entrega. Un error 5xx, un problema de certificado, un protocolo no soportado o una desconexión de entrega con resultado incierto no se reintentan. El Message-ID no sustituye esta precaución ni garantiza deduplicación al repetir un workflow manualmente.

El artefacto `diagnostico-<run>-<intento>` conserva ahora `envio.json`, la copia HTML/texto del resumen y el listado, además del diagnóstico deportivo, durante 14 días. Se publica incluso cuando falla el paso. Esto permite acceder al contenido generado y al código SMTP sin volver a enviar el correo. No se ha cambiado el horario del workflow ni se ha lanzado un envío de prueba.

Referencias: [excepciones SMTP de Python](https://docs.python.org/3.12/library/smtplib.html), [códigos SMTP de Gmail](https://support.google.com/mail/answer/3726730?hl=en). La próxima ejecución permitirá verificar recuperación o identificar el rechazo permanente concreto; los logs antiguos no contienen ese dato.

## Cobertura y calibración — 07/11/2026

Se preserva el estado publicado por la agenda (texto y metadatos `eventStatus`). Aplazados, cancelados, suspendidos o sin fecha confirmada no entran en recomendaciones ni planning y no generan enlaces de Calendar, ni de partido completo ni de tramo. La comprobación se aplica también en los generadores llamados directamente. «Canal por confirmar» y un canal llamado «TBD» no significan fecha pendiente. El diagnóstico enumera todos los eventos descartados con su motivo; los no programables aparecen también en los avisos del resumen. No hay sincronización con reservas ya guardadas en Google Calendar.

Se corrige el contexto −0,1 ficticio reproducido en Espanyol–Deportivo: referencia y resultado redondean las contribuciones con el mismo criterio. El interés deportivo y la afinidad se muestran con dos decimales; la nota final se redondea a una décima. Contexto y reconocimiento ya están incluidos en el interés deportivo, no se suman de nuevo. Las señales contextuales validadas sin efecto conservan sus fuentes.

Favoritos: Atlético, Aston Villa, Roma y Dortmund usan el mismo refuerzo de afinidad (+1,3, más la preferencia general del fútbol +0,2). Estudiantes recibe +1,3, más baloncesto +0,1; su base de Primera FEB no cambia, por lo que un encuentro ordinario pasa de 4,2 a 4,9. La sección «Tus equipos · para seguir» hace visibles los favoritos fuera del plan principal, sin inflar su mérito deportivo ni obligar a ocupar una plaza. Se comprueba identidad exacta y deporte; Estudiantes LP, Río Cuarto y filiales no heredan la afinidad. Celtics conserva su preferencia y la regla de Resumen en diferido.

`data/perfiles_futbol.json` añade reconocimiento editorial moderado, con alias, fuente y fecha. Athletic, Valencia, Newcastle, Stuttgart, Bologna y Zaragoza: +0,35 por club. En partidos de la liga argentina, Boca/River +0,8 y otros seis clubes +0,35. El cartel total se limita a +2,0. Los pesos son elecciones editoriales; las fuentes documentan identidad e historia, no la puntuación ni la forma actual. No hay premio indiscriminado a todos los clubes de una competición ni coincidencias ambiguas con «Racing» o «Estudiantes» a secas.

El registro pasa de 46 a 50 parejas: Osasuna–Athletic (+0,5), Parma–Bologna (+0,35), Gimnasia Mendoza–Independiente Rivadavia (+0,6) y Zaragoza–Huesca (+0,45), con fuentes primarias. No se fuerza a ningún derbi a alcanzar 7,5. Se autoriza una excepción al filtro de categorías inferiores exclusivamente para parejas documentadas en Primera/Segunda/Tercera Federación o regional; no se admiten por ello filiales, juveniles ni otras competiciones rechazadas.

Ampliación elegida por el usuario: finales mundiales/europeas de selecciones de pádel con España (masculinas o femeninas) y sesiones competitivas de MotoGP. No se añaden Liga F, Mundial femenino Sub-17, boxeo ni Copa de Brasil. WNBA sigue excluida. La excepción de pádel no cambia el filtro femenino de otros deportes. Una final ya iniciada solo se incorpora en una ejecución manual si hay estado explícito de directo; no se deduce que sigue jugando por una duración estimada. Las finales de pádel por selecciones usan 300 minutos estimados por sus varias eliminatorias; el final real no está confirmado. Nota editorial mundial: base 5,8 + final 2,4 + afinidad España 0,6 = 8,8; Europeo: 8,4. No se incorporan finales de circuitos de parejas ni semifinales por compartir la palabra «final».

Motor: sesiones explícitas según competición y descripción, nunca por un canal llamado DAZN MotoGP. F1: libres 4,7/75 min; clasificación 5,4/75 min; sprint 6,0/45 min; carrera 6,4/150 min. MotoGP: clasificación 5,0/60 min; sprint 6,0/45 min; carrera 6,4/60 min. Libres, Moto2/Moto3 y sesiones sin identificar quedan fuera del nuevo filtro de motociclismo. Planning y Calendar comparten la duración estimada; no se añade bonus de eliminatoria al motor.

Se conserva una muestra saneada de siete filas de la agenda pública del 7/11 en `tests/fixtures/cobertura_2026-11-07.html`, con aplazado, finales, sesiones y derbi. Las jornadas guardadas del 27 y 28 mantienen sus 87 eventos y controles neutrales. La vista previa actual usa la agenda y contexto capturados durante la revisión; se etiqueta como comparación de reglas con las mismas entradas, no como reproducción del correo matinal. No se consultan credenciales ni se envían correos de prueba.

Queda pendiente la narrativa tenística automática (recorrido excepcional y jugador local): necesita una fuente estructurada validada con datos anteriores al inicio y un premio acotado que no duplique ranking o fase. No se añade una excepción manual para Van Assche ni se deshacen la preferencia tenis −0,4 o el umbral 7,5.

### Identidad y reconocimiento — 8 de noviembre

Se distingue Admiral Bundesliga (Austria, base 4,3) de la Bundesliga alemana antes de consultar el contexto. Austria, Bélgica, Países Bajos y Portugal indican expresamente cuándo no disponen de clasificación/forma validada; no se amplían los proveedores. Los alias exactos de Joventut, Tenerife, Unicaja y UCAM evitan diferencias por patrocinador. NCAA compara universidades completas: Arkansas, Kansas State, Michigan State y NC State no heredan la selección de otros programas.

El catálogo añade 15 perfiles de fútbol graduados: ocho referentes y siete intermedios (+0,35). Los referentes entran en la misma cuenta que los anteriores: uno aporta +0,8 y dos +2,0; no cobran dos veces. El cartel total sigue limitado a +2,0. En ACB, Tenerife y Unicaja son referentes; UCAM recibe +0,35. Uno aporta +0,8, dos +1,5 y el máximo combinado es +1,5. No se aplica este catálogo ACB a NBA o Euroliga. Fuentes y fecha figuran en los archivos de datos y en el desglose del correo; documentan identidad e historia, no forma actual ni notas objetivas.

Brujas–Anderlecht y Fiorentina–Juventus añaden dos rivalidades documentadas (+0,6 cada una): registro actual de 52 parejas. NASCAR Cup Series distingue sesión y carrera (base 5,2 y 180 minutos estimados). La palabra Championship no genera bonus de final: el formato Chase 2026 y la situación matemática requieren comprobación independiente. No se amplían las competiciones admitidas.

Validación: 249 pruebas automatizadas. La comparación visual local del 8/11 conserva las contribuciones contextuales del correo y aplica las diferencias estructurales: 55 → 54 eventos, con las cuatro citas principales conservadas. Es una simulación controlada, sin reconstrucción de las tablas matinales. Los conjuntos completos del 27/10 y 28/10 conservan 32 y 55 eventos y sus planes; cambia una nota del 28/10 por reconocimiento de Fiorentina. La narrativa automática de tenis y el contexto de ligas sin proveedor siguen pendientes.

Presentación simplificada: las tarjetas y el texto del correo omiten motivos, fuentes y desgloses de puntuación. Estos datos siguen disponibles en el diagnóstico interno. Se conserva la nota final, los canales y los botones de Calendar; se retira la instrucción visible para elegir calendario. Los eventos llevan separadores finos gris oscuro suave (#8995a3), conservando los marcos de favoritos y destacado.

Compactación: Calendar usa un botón visual 📅 + en la esquina superior derecha, con nombre accesible que distingue partido completo y tramo. Las etiquetas Cita principal llevan borde dorado. Las alternativas usan el formato de filas compactas del listado, conservando colores, favoritos, canales, notas y orden cronológico.
