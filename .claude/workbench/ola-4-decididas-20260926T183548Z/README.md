# Ola 4: causas ya decididas que seguían deteniendo lotes, y falsos «sin tildes»

## Causas decididas que no se retraducían

«auditabilidad» tenía su fila de glosario desde la ola 3 y seguía deteniendo
dos lotes como causa compartida: `advance` se detiene ante toda compartida
antes de retraducir, así que la decisión nunca llegaba al texto. Lo mismo con
`prose:forbidden:*` (la lista de prohibidas es la decisión) y con U+FFFD (daño
de un fragmento, no una causa que se decida una vez). `classify` las manda a
retraducción aunque aparezcan en varias notas.

## Falsos positivos del eje «sin tildes»

«Microsoft Research Asia», «Lin Min», «Lei Jun» y «4 h 25 min» salían como
«asía», «mín» y «leí». Una mayúscula dentro de la oración es un nombre propio
y una unidad tras un número no lleva tilde; al inicio de oración («Tambien
dijo») y en minúscula («la tecnica») la señal sigue saliendo.

## Decisiones de glosario

`pipeline` y `pull request` se conservan (uso del original zh);
anthropomorphization se traduce «atribución de rasgos humanos», con
«antropomorfización» rechazada. Se miden después de su retraducción.

## TDD y anulación (`annul-summary.txt`)

R1 (sin el salto de nombre propio) y R2 (sin el de unidad) hacen caer la
prueba de tildes; R3 (sin la ruta de causa decidida), sólo la suya.
