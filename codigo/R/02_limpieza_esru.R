# NOTA: el script de limpieza no parte de "data/raw/" ya que
# el script 01 guarda el archivo a partir del cuál este script 
# trabaja en "data/clean".

# ==========================================
# 0. Cargar librerías
# ==========================================
library(here)
library(tidyverse)

# ==========================================
# 1. Cargar base de datos (ESRU con IRE)
# ==========================================
esru2 <- readRDS(here("data","clean","01_generar_ires_quintiles_esru.rds"))

observaciones_inicial <- nrow(esru2)

NA_antes <- sum(is.na(esru2)) / (nrow(esru2) * ncol(esru2)) * 100

# ==========================================
# 2. Restringir la edad a 25-34 (para los que tenemos ECI de origen)
# ==========================================
esru2 <- esru2 |> 
  filter(edad>=25 & edad<=34)

observaciones_edad <- nrow(esru2)

# ==========================================
# 3. Conservar a quien vive en el mismo estado que a los 14 años
# ==========================================
esru2 <- esru2 |>
  filter(
    unclass(entidad) == unclass(p19)
  )

observaciones_entidad <- nrow(esru2)

# ==========================================
# 4. Renombrar para que sean iguales a como están en la ENIGH
# ==========================================

# Algunas de estas variables no tienen exactamente este nombre en la ENIGH
# en esos casos esto se debe a que la variable de la ENIGH necesita
# modificarse para ser comparable con la ESRU, y después se le dará el nombre
# aquí especificado (por ejemplo, jefe_hogar se sacará de parentesco: 101 -> 1;
# cualquier otro código -> 0)

esru2 <- esru2 %>% 
  rename(
    entidad_14 = p19, # Variables personales
    hablaind = p111,
    nivelaprob = educ,
    edo_conyug = p16,
    sinco = p64_SINCO, # Variables laborales
    contrato = p69,
    htrab = p72,
    medtrab = p68,
    scian = p67_SCIAN,
    inst_imss = p18_1, # Variables de afiliación médica
    inst_issste = p18_2,
    inst_publica_especial = p18_3,
    inst_no_contributiva = p18_4,
    inst_privada = p18_5,
    inst_otra = p18_6,
    sin_afiliacion = p18_7,
    mat_pisos = p88, # Variables de vivienda
    cuart_dorm = p89,
    num_cuarto = p90,
    tenencia = p91,
    tipo_viv = p93,
    agua_ent = p95a,
    disp_elect = p95b,
    bano = p95c,
    calentador = p95d,
    servicio_domestico = p95e,
    estufa = p96a, # Elementos en el hogar
    lavadora = p96b,
    refrigerador = p96c,
    microondas = p96d,
    television_digital = p96e,
    tostador = p96f,
    videojuegos = p96g,
    aspiradora = p96h,
    audiovisual_pagado = p96i,
    telefono = p96j,
    celular = p96k,
    conex_inte = p96l,
    tableta = p96m,
    computadora = p96n,
    motocicleta = p96q,
    bicicleta_triciclo = p96r,
    vehiculos = p99,
  )

# ==========================================
# 5. Seleccionar columnas
# ==========================================
# Mantenemos rururb pero sin renombrarla, ya que más bien el análogo en ENIGH
# es el que debe renombrarse

esru2 <- esru2 %>% 
  select(
    index, edad, sexo, entidad, entidad_14, rururb, hablaind, nivelaprob,edo_conyug, jefe_hogar,
    tamhog, sinco, scian, contrato,htrab,medtrab, inst_imss, inst_issste,
    inst_publica_especial, inst_no_contributiva, inst_privada, inst_otra,
    sin_afiliacion, mat_pisos, cuart_dorm, num_cuarto, tenencia, tipo_viv,
    agua_ent, disp_elect, bano, calentador, servicio_domestico, estufa,
    lavadora, refrigerador, microondas, television_digital, tostador,
    videojuegos, aspiradora, audiovisual_pagado, telefono, celular, conex_inte,
    tableta, computadora, motocicleta, bicicleta_triciclo, vehiculos,
    ireccomp_or, ireccomp_act, quintilecomp_or, quintilecomp_act, factor_ceey
  )

# ==========================================
# 6. Eliminar NA
# ==========================================
esru2_limpia <- esru2 |>
  drop_na()

observaciones_sin_NA <- nrow(esru2_limpia)

NA_despues <- sum(is.na(esru2_limpia))

# ==========================================
# 7. Crear log de decisiones
# ==========================================

log <- data.frame(
  Variable = c(
    "edad",
    "entidad y entidad_14",
    "nombres de variables",
    "variables seleccionadas",
    "múltiples variables"
  ),
  Problema = c(
    "La ESRU contiene personas de diferentes edades",
    "Algunas personas viven en una entidad distinta a la que vivían a los 14 años",
    "Los nombres de ESRU y ENIGH son diferentes",
    "La base contiene variables que no se utilizarán en el análisis",
    "Algunas observaciones tienen datos faltantes."
  ),
  
  Decision = c(
    "Conservar personas de 25 a 34 años",
    "Mantener personas cuya entidad actual es igual a la entidad a los 14 años",
    "Renombrar las variables ESRU con nombres comunes para ambas bases",
    "Conservar las variables homologables, los IRE, los quintiles y el ponderador",
    "Eliminar observaciones con al menos un NA"
  ),
  
  Justificacion = c(
    "Para estas edades se tiene el ECI de cuando tenían 14 años",
    "El proyecto analizará a personas que permanecieron en la misma entidad",
    "Esto facilitará la homologación posterior con ENIGH",
    "Estas variables se utilizarán en el modelo de imputación y el análisis posterior",
    "Se trabajará con casos completos en el modelo"
  ),
  
  n_afectados = c(
    observaciones_inicial - observaciones_edad,
    observaciones_edad - observaciones_entidad,
    0,
    0,
    observaciones_entidad - observaciones_sin_NA
  )
)

log

# ==========================================
# 8. Guardar
# ==========================================
saveRDS(
  esru2_limpia,
  here("data", "clean", "02_esru_limpia.rds")
)