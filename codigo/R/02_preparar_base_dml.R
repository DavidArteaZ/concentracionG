# =============================================================================
# 02_preparar_base_dml.R
#
# Proyecto: Movilidad social y complejidad económica (ESRU-EMOVI 2023)
#
# Qué hace este script (y nada más):
#   1. Parte de la salida del script 01 (muestra CEEY, cohorte 1) y aplica las
#      exclusiones de la muestra de análisis: T18 (sin municipio a los 14 o en
#      el extranjero) y los casos con p20_COD inexistente (pendiente de D21).
#   2. Une el ICE del municipio de origen (T17, D21): municipios creados
#      después de los 14 años reciben el ICE del municipio padre.
#   3. Asigna el ICE al año en que la persona tenía 14 (D15): interpolación
#      lineal (principal), año censal más cercano y 2003 (robustez). Lo mismo
#      para las 33 especificaciones alternativas del ICE.
#   4. Escala del municipio de origen (D20): log de población en el año a los
#      14 según CONAPO (principal, 13/10/2026); censos del INEGI interpolados,
#      log de UE totales y categorías de Soloaga et al. (robustez).
#   5. Recodifica los predictores de origen: "no sabe" -> NA con una tabla
#      explícita de códigos por variable (D11), sí/no -> 1/0, p22 = 999 -> NA
#      (T5), hacinamiento continuo (D12).
#   6. Define los roles de cada variable (Y, tratamiento, X principal,
#      X robustez, Z, mediadores, grupos, pesos) y audita fugas (T4).
#   7. Variables binarias de movilidad observada para robustez (D9),
#      mediadores (4.3) y migración (D14).
#   8. Escribe la base para el DML en Python y sus diagnósticos.
#
# Qué NO hace:
#   - No recalcula el IRE ni los percentiles (vienen del script 01).
#   - No calcula ni modifica el ICE (protocolo de V1): solo lo lee de
#     data/clean/ice/ice_para_dml.csv.
#   - No codifica variables nominales en dummies ni estandariza el ICE. Eso
#     se hace en el DML (Python), con los tipos de diccionario_variables_02.csv.
#   - No construye la formalidad municipal (D18): sus fuentes aún no están en
#     el repositorio.
#
# Insumos:
#   data/clean/01_generar_ires_quintiles_esru.rds        (script 01)
#   data/clean/ice/ice_para_dml.csv                      (codigo/ice, módulo 07)
#   data/clean/ice/municipios_padre_hijo.csv             (codigo/ice, módulo 05)
#   data/raw/pobproy_conapo.csv                          (CONAPO, 1990-2040)
#   data/raw/ice/poblacion_municipal.csv                 (censos INEGI)
#   data/raw/ESRU_mun.dta                                (CEEY, D22)
#
# Salidas:
#   data/clean/02_base_dml.csv   (una fila por persona de la muestra de análisis;
#                                 NA como celda vacía; códigos como texto)
#   data/clean/02_base_dml.rds   (la misma base)
#   data/clean/02_resultados/*.csv, sessionInfo_02.txt  (diagnósticos)
# =============================================================================

# ==========================================
# 0. Librerías y parámetros
# ==========================================
# install.packages(c("haven", "dplyr", "here"))
library(haven)
library(dplyr)
library(here)

COHORTE_ANALISIS <- 1L
ANIO_ENCUESTA    <- 2023L
ANIOS_ICE        <- c(2003L, 2008L, 2013L)   # años censales que cubren 2003-2012
# D20, modificada el 13/10/2026: la principal usa la población de CONAPO del
# año exacto a los 14 (serie anual 1990-2040; antes de 2015 es una
# reconstrucción de la conciliación demográfica, no un conteo). Robustez:
# censos del INEGI 2000, 2005 y 2010 interpolados; quienes tenían 14 en
# 2011-2012 reciben la población de 2010 (sin información posterior a los 14).
ANIOS_POB        <- c(2000L, 2005L, 2010L)

COD_SIN_MUNICIPIO <- c("33333", "99999")  # T18: extranjero / no especificado
COD_INEXISTENTE   <- c("03030")           # D21: no existe en el catálogo;
                                          # se excluye hasta revisarlo a mano

# Cortes de tamaño de Soloaga et al. (2025), robustez de D20.
CORTES_SOLOAGA <- c(0, 15000, 50000, 350000, Inf)

dir_res <- here("data", "clean", "02_resultados")
dir.create(dir_res, recursive = TRUE, showWarnings = FALSE)

# ==========================================
# 1. Datos
# ==========================================
esru <- readRDS(here("data", "clean", "01_generar_ires_quintiles_esru.rds"))

ice <- read.csv(here("data", "clean", "ice", "ice_para_dml.csv"),
                colClasses = c(cve_mun = "character"))
padre_hijo <- read.csv(here("data", "clean", "ice", "municipios_padre_hijo.csv"),
                       colClasses = c(cve_mun_hijo = "character",
                                      cve_mun_padre = "character",
                                      otros_padres = "character"))
pob <- read.csv(here("data", "raw", "ice", "poblacion_municipal.csv"),
                colClasses = c(CVEGEO = "character"), check.names = FALSE)
# CONAPO: una fila por municipio, sexo y año; CLAVE sin el 0 inicial en las
# entidades 1-9. Se suman hombres y mujeres.
# Solo se usan columnas numéricas y SEXO (ASCII), así que no se recodifica el
# texto. Si el archivo trae BOM, la primera columna llega como "<BOM>CLAVE".
conapo <- read.csv(here("data", "raw", "pobproy_conapo.csv"),
                   encoding = "UTF-8", check.names = FALSE)
stopifnot(grepl("CLAVE$", names(conapo)[1], useBytes = TRUE))
names(conapo)[1] <- "CLAVE"
conapo <- conapo[, c("CLAVE", "SEXO", "ANO", "POB_TOTAL")]
stopifnot(setequal(unique(conapo$SEXO), c("HOMBRES", "MUJERES")))
conapo <- conapo %>%
  mutate(cve_mun = sprintf("%05d", as.integer(CLAVE))) %>%
  group_by(cve_mun, anio = ANO) %>%
  summarise(pob = sum(POB_TOTAL), n_filas = n(), .groups = "drop")
stopifnot(all(conapo$n_filas == 2))
mun_actual <- read_dta(here("data", "raw", "ESRU_mun.dta")) %>% zap_labels()

stopifnot(!anyDuplicated(ice[c("cve_mun", "anio")]))
stopifnot(!anyDuplicated(pob$CVEGEO))
stopifnot(!anyDuplicated(mun_actual$index))
stopifnot(all(nchar(ice$cve_mun) == 5), all(nchar(pob$CVEGEO) == 5))

# ==========================================
# 2. Funciones auxiliares
# ==========================================
# Sí/No de la ESRU (1 = sí, 2 = no) a 1/0. Cualquier otro código (8 = NS) -> NA.
si_no_01 <- function(x) case_when(x == 1 ~ 1, x == 2 ~ 0, TRUE ~ NA_real_)

# Valor de una columna del ICE para un municipio y un año.
valor_ice <- function(cve, anio, columna) {
  ice[[columna]][match(paste(cve, anio), paste(ice$cve_mun, ice$anio))]
}

# Interpolación lineal de v entre (t0, v0) y (t1, v1), evaluada en t.
interpolar <- function(t, t0, t1, v0, v1) v0 + (t - t0) / (t1 - t0) * (v1 - v0)

# Años censales adyacentes: t0 = mayor año <= t; t1 = siguiente.
anio_inferior <- function(t, anios) {
  sapply(t, function(x) max(anios[anios <= x]))
}

paso <- function(d, etiqueta) {
  data.frame(paso = etiqueta, n = nrow(d), n_pond = sum(d$factor))
}

# ==========================================
# 3. Muestra de análisis (D2 paso 4, T18, D21)
# ==========================================
d0 <- esru %>% filter(muestra_ceey, cohorte == COHORTE_ANALISIS)
stopifnot(all(!is.na(d0$pct_act_c1)), all(!is.na(d0$q_or_c1_imp)))

d0 <- d0 %>% mutate(cve_or = sprintf("%05d", as.integer(p20_COD)))
stopifnot(all(nchar(d0$cve_or) == 5))

d1 <- d0 %>% filter(!cve_or %in% COD_SIN_MUNICIPIO)
d2 <- d1 %>% filter(!cve_or %in% COD_INEXISTENTE)

flujo <- bind_rows(
  paso(d0, "0. Muestra CEEY, cohorte 1 (salida del script 01)"),
  paso(d1, "1. Sin p20_COD = 33333/99999 (T18)"),
  paso(d2, "2. Sin p20_COD inexistente (03030, pendiente D21)")
)

# ==========================================
# 4. Municipio al que se asigna el ICE (D21)
# ==========================================
# Municipios declarados que no tienen ICE en algún año censal necesario:
# se les asigna el municipio padre en TODOS los años (también en población,
# pliegues y agrupación), porque a los 14 la persona vivía en territorio del
# padre.
sin_ice_algun_anio <- function(cve) {
  sapply(cve, function(m) any(is.na(match(paste(m, ANIOS_ICE),
                                          paste(ice$cve_mun, ice$anio)))))
}
cods_sin_ice <- unique(d2$cve_or[sin_ice_algun_anio(d2$cve_or)])
stopifnot(all(cods_sin_ice %in% padre_hijo$cve_mun_hijo))

d2 <- d2 %>%
  mutate(
    hijo_d21 = cve_or %in% cods_sin_ice,
    cve_ice  = if_else(hijo_d21,
                       padre_hijo$cve_mun_padre[match(cve_or, padre_hijo$cve_mun_hijo)],
                       cve_or)
  )
stopifnot(!any(sin_ice_algun_anio(unique(d2$cve_ice))))

tabla_d21 <- d2 %>%
  filter(hijo_d21) %>%
  count(cve_or, cve_ice, name = "n") %>%
  mutate(nombre_hijo  = padre_hijo$nombre_hijo[match(cve_or, padre_hijo$cve_mun_hijo)],
         nombre_padre = padre_hijo$nombre_padre[match(cve_or, padre_hijo$cve_mun_hijo)])
print(tabla_d21)

# ==========================================
# 5. ICE al año en que la persona tenía 14 (D15)
# ==========================================
# La base no tiene fecha de nacimiento: el año a los 14 tiene un error de
# hasta un año (D15, nota del 08/10/2026).
d2 <- d2 %>%
  mutate(
    anio14   = ANIO_ENCUESTA - edad + 14,
    t0_ice   = anio_inferior(anio14, ANIOS_ICE[-length(ANIOS_ICE)]),
    t1_ice   = ANIOS_ICE[match(t0_ice, ANIOS_ICE) + 1],
    # Año censal más cercano (robustez a). No hay empates: los años están a
    # 5 años de distancia y anio14 es entero.
    t_cercano = ifelse(anio14 - t0_ice <= t1_ice - anio14, t0_ice, t1_ice)
  )
stopifnot(all(d2$anio14 >= min(ANIOS_ICE) & d2$anio14 <= max(ANIOS_ICE)))

cols_ice <- c("ice", grep("^ice_", names(ice), value = TRUE))
for (cc in cols_ice) {
  sufijo <- sub("^ice", "", cc)  # "" para la base, "_clase", etc.
  v0 <- valor_ice(d2$cve_ice, d2$t0_ice, cc)
  v1 <- valor_ice(d2$cve_ice, d2$t1_ice, cc)
  d2[[paste0("ice14", sufijo)]] <- interpolar(d2$anio14, d2$t0_ice, d2$t1_ice, v0, v1)
  if (cc == "ice") {
    d2$ice14_cercano <- valor_ice(d2$cve_ice, d2$t_cercano, cc)
    d2$ice14_2003    <- valor_ice(d2$cve_ice, rep(2003L, nrow(d2)), cc)
  }
}
stopifnot(all(!is.na(d2$ice14)), all(!is.na(d2$ice14_cercano)),
          all(!is.na(d2$ice14_2003)))

# El municipio está en el núcleo de estimación del ICE en ambos años usados.
d2$en_nucleo14 <- valor_ice(d2$cve_ice, d2$t0_ice, "en_nucleo") %in% c(TRUE, "True") &
                  valor_ice(d2$cve_ice, d2$t1_ice, "en_nucleo") %in% c(TRUE, "True")

# ==========================================
# 6. Escala del municipio de origen (D20)
# ==========================================
# Principal: CONAPO en el año exacto a los 14 (municipio padre en D21).
d2$log_pob14 <- log(conapo$pob[match(paste(d2$cve_ice, d2$anio14),
                                     paste(conapo$cve_mun, conapo$anio))])

# Robustez: censos del INEGI interpolados (log, crecimiento geométrico).
pob_log <- function(cve, anio) {
  m <- as.matrix(pob[, as.character(ANIOS_POB)])
  log(m[cbind(match(cve, pob$CVEGEO), match(as.character(anio), colnames(m)))])
}
stopifnot(all(d2$cve_ice %in% pob$CVEGEO))

d2 <- d2 %>%
  mutate(
    anio14_pob = pmin(anio14, max(ANIOS_POB)),           # 2011-2012 -> 2010
    t0_pob     = anio_inferior(anio14_pob, ANIOS_POB[-length(ANIOS_POB)]),
    t1_pob     = ANIOS_POB[match(t0_pob, ANIOS_POB) + 1]
  )
d2$log_pob14_censo <- interpolar(d2$anio14_pob, d2$t0_pob, d2$t1_pob,
                           pob_log(d2$cve_ice, d2$t0_pob),
                           pob_log(d2$cve_ice, d2$t1_pob))
d2$tam_soloaga14 <- cut(exp(d2$log_pob14), CORTES_SOLOAGA, right = FALSE,
                        labels = c("<15mil", "15-50mil", "50-350mil", ">=350mil"))

# Robustez (a) de D20: log de UE totales, interpolado con los años del ICE.
d2$log_ue14 <- interpolar(d2$anio14, d2$t0_ice, d2$t1_ice,
                          valor_ice(d2$cve_ice, d2$t0_ice, "log_ue_total"),
                          valor_ice(d2$cve_ice, d2$t1_ice, "log_ue_total"))
stopifnot(all(!is.na(d2$log_pob14)), all(!is.na(d2$log_pob14_censo)),
          all(!is.na(d2$log_ue14)))

# ==========================================
# 7. Recodificación de predictores de origen (D10-D13, D17, T5)
# ==========================================
# Códigos de "no sabe" / "no especificado" por variable, tomados del
# Diccionario ESRU EMOVI 2023 (hoja Entrevistado). No se usa una regla
# general "8 = NS": en p28 el 8 y el 9 son categorías válidas, en p42 el 8 es
# un nivel educativo y en p30 el 8 es un conteo.
# p46 = 99 no está en el diccionario (20 casos en la cohorte 1); se trata
# como no especificado.
codigos_ns <- list(
  p26a = 8, p26b = 8, p26c = 8, p27 = 8,
  p29a = 8, p29b = 8, p29c = 8, p29d = 8, p29e = 8, p29f = 8, p29g = 8,
  p31f = 8, p31j = 8, p31l = 8, p31n = 8, p31o = 8,
  p32c = 8, p32d = 8, p32h = 8, p32i = 8, p32j = 8, p32k = 8, p32l = 8,
  p32m = 8, p32n = 8, p32o = 8,
  p33a = 8, p33b = 8, p33c = 8, p33d = 8, p33e = 8, p33f = 8, p33g = 8,
  p33h = 8, p33i = 8,
  p41a = c(8, 9), p41b = c(8, 9), p42a = 98, p42b = 98, p43a = 9, p43b = 9,
  p44a = 8, p44b = 8, p45a = 8, p45b = 8,
  p46 = c(8, 99), p49 = 8, p50 = 8, p51 = 8, p55 = 8, p56 = 8,
  p57 = 98, p22 = 999
)
ns_conteo <- data.frame(
  variable = names(codigos_ns),
  codigos_ns = sapply(codigos_ns, paste, collapse = "/"),
  n_ns = sapply(names(codigos_ns), function(v) sum(d2[[v]] %in% codigos_ns[[v]])),
  n_na_original = sapply(names(codigos_ns), function(v) sum(is.na(d2[[v]])))
)
for (v in names(codigos_ns)) {
  d2[[v]] <- ifelse(d2[[v]] %in% codigos_ns[[v]], NA, d2[[v]])
}

# Sí/No -> 1/0 (después de quitar el NS).
vars_si_no <- c(paste0("p26", c("a", "b", "c")),
                paste0("p29", letters[1:7]),
                paste0("p31", c("f", "j", "l", "n", "o")),
                paste0("p32", c("c", "d", "h", "i", "j", "k", "l", "m", "n", "o")),
                paste0("p33", letters[1:9]),
                "p41a", "p41b", "p44a", "p44b", "p45a", "p45b", "p111")
for (v in vars_si_no) d2[[v]] <- si_no_01(d2[[v]])

d2 <- d2 %>%
  mutate(
    mujer       = as.numeric(sexo == 2),
    hacina_or   = p22 / p23,                          # D12, continuo
    p112_num    = match(p112, LETTERS[1:11]),         # A (más claro) = 1 ... K = 11
    rural14     = as.numeric(p21 == 5)                # pueblo < 2,500 hab.
  )
stopifnot(all(!is.na(d2$p112_num) | is.na(d2$p112) | d2$p112 == ""))

# ==========================================
# 8. Variables de resultado, Z, mediadores y migración
# ==========================================
d2 <- d2 %>%
  mutate(
    # D9, robustez: movilidad observada (con el quintil de origen imputado, D19).
    y_sube_quintil   = as.numeric(q_act_c1 > q_or_c1_imp),
    y_sube_2quintil  = as.numeric(q_act_c1 - q_or_c1_imp >= 2),
    y_q12_a_q45      = ifelse(q_or_c1_imp <= 2, as.numeric(q_act_c1 >= 4), NA_real_),
    ent_or           = substr(cve_ice, 1, 2)
  )

# Migración (D14): municipio actual de ESRU_mun.dta.
d2$cve_actual <- sprintf("%05d", as.integer(
  mun_actual$municipio[match(d2$index, mun_actual$index)]))
stopifnot(all(!is.na(d2$cve_actual)))
d2$migro <- as.numeric(d2$cve_actual != d2$cve_or)
# ICE del municipio actual en 2023: solo descriptivo y para el mediador de
# migración (D14). Es una posición relativa dentro de 2023, no un nivel
# comparable con el ICE de origen; el cambio es un cambio de posición.
d2$ice_actual_2023 <- valor_ice(d2$cve_actual, rep(2023L, nrow(d2)), "ice")
d2$migro_mas_complejo <- as.numeric(d2$migro == 1 & d2$ice_actual_2023 > d2$ice14)

# ==========================================
# 9. Roles de las variables
# ==========================================
# D10: activos de origen. Los 19 activos del IRE (regla na) sin el
# hacinamiento binario (D12 usa p22, p23 y su cociente) y sin agua
# (ac_or6 = p26a) ni electricidad (ac_or10 = p26b), que D6 manda a robustez
# como servicios de la vivienda.
activos_ire <- setdiff(paste0("ac_or", 1:19, "_na"), c("ac_or6_na", "ac_or10_na"))
activos_ampliados <- c("p25", "p27", "p28",
                       paste0("p29", letters[1:7]),
                       paste0("p31", c("f", "j", "l", "n", "o")),
                       paste0("p32", c("c", "d", "h", "i", "j", "k", "l", "m", "n", "o")))

x_principal <- c(
  activos_ire, activos_ampliados,
  "p22", "p23", "hacina_or",                               # D12
  "irec_or_na", "q_or_c1_imp",                             # D11, D19
  "educp", "educm", "p41a", "p41b", "p42a", "p42b",        # D13
  "p43a", "p43b", "p44a", "p44b",
  "clasep", "clasem", "p46", "p49", "p51", "p55", "p50", "p56",
  "p39", "p40", "p57", "p58", "p45a", "p45b",
  "mujer", "edad", "p111",                                 # D13, D17, T16
  "p113dL", "p113da", "p113db", "p113mL", "p113ma", "p113mb",
  "region_14", "p21",                                      # D6
  "log_pob14"                                              # D20
)
x_robustez_extra <- c("ac_or6_na", "ac_or10_na", "p26c",   # D6: servicios
                      paste0("p33", letters[1:9]),         # D6: barrio
                      "p110", "p112_num",                  # D17
                      "log_ue14")                          # D20 (a)

# T4: variables que nunca pueden entrar en X.
prohibidas <- c(paste0("ac", 1:16), "hac", "hacina", "p89",
                grep("^p9[4-9]", names(d2), value = TRUE), "tamhog",
                "educ", paste0("p", 8:18), grep("^p18_", names(d2), value = TRUE),
                paste0("p", 59:113), "clase", "cmo", "ocup", "ingc_pc",
                "jefe_hogar", "region", "entidad", "rururb", "est", "upm_muestra",
                "irec_act", "pct_act_c1", "q_act_c1", "cve_actual", "migro",
                "ice_actual_2023", "migro_mas_complejo")
# p110, p111, p112 y p113* son excepciones documentadas (D13, D17).
excepciones_t4 <- c("p110", "p111", "p112_num",
                    "p113dL", "p113da", "p113db", "p113mL", "p113ma", "p113mb")
fuga <- intersect(c(x_principal, x_robustez_extra),
                  setdiff(prohibidas, excepciones_t4))
if (length(fuga) > 0) stop("T4: variables prohibidas en X: ", paste(fuga, collapse = ", "))
stopifnot(all(c(x_principal, x_robustez_extra) %in% names(d2)))
stopifnot(!anyDuplicated(c(x_principal, x_robustez_extra)))

y_vars   <- c("pct_act_c1", "q_act_c1", "y_sube_quintil", "y_sube_2quintil",
              "y_q12_a_q45")
trat     <- c("ice14", "ice14_cercano", "ice14_2003",
              setdiff(grep("^ice14_", names(d2), value = TRUE),
                      c("ice14_cercano", "ice14_2003")))
z_vars   <- c("q_or_c1_imp", "mujer", "region_14", "rural14")
mediad   <- c("educ", "p9", "p10", "p18_1", "p18_2", "p18_3", "p65", "clase",
              "cmo", "migro", "migro_mas_complejo", "ice_actual_2023")
grupos   <- c("cve_ice", "upm_muestra", "est", "ent_or")
ids      <- c("index", "cve_or", "cve_actual", "hijo_d21", "anio14",
              "en_nucleo14", "tam_soloaga14", "log_pob14_censo",
              "q_or_c1_na", "q_or_c1_ceey", "irec_or_imp", "pct_or_c1_imp",
              "algun_ns_or")
pesos    <- "factor"

# Tipo de cada variable para el DML (las nominales se convierten en dummies
# en Python; las ordinales y continuas entran como números).
nominales <- c("p27", "p28", "clasep", "clasem", "p46", "p49", "p51", "p55",
               "p50", "p56", "p39", "p40", "region_14", "p110",
               "p65", "clase", "cmo")
binarias  <- c(activos_ire, "ac_or6_na", "ac_or10_na",
               intersect(vars_si_no, c(x_principal, x_robustez_extra)),
               "mujer", "rural14", "y_sube_quintil", "y_sube_2quintil",
               "y_q12_a_q45", "p18_1", "p18_2", "p18_3", "migro",
               "migro_mas_complejo")
tipo_de <- function(v) {
  if (v %in% nominales) "nominal"
  else if (v %in% binarias) "binaria"
  else if (v %in% c("p25", "educp", "educm", "p42a", "p42b", "p43a", "p43b",
                    "p21", "q_or_c1_imp", "q_act_c1", "educ", "p9", "p10",
                    "p112_num")) "ordinal"
  else "continua"
}

roles <- bind_rows(
  data.frame(variable = y_vars, rol = "Y"),
  data.frame(variable = trat, rol = "tratamiento"),
  data.frame(variable = x_principal, rol = "X_principal"),
  data.frame(variable = x_robustez_extra, rol = "X_robustez"),
  data.frame(variable = z_vars, rol = "Z"),
  data.frame(variable = mediad, rol = "mediador"),
  data.frame(variable = grupos, rol = "grupo"),
  data.frame(variable = pesos, rol = "peso"),
  data.frame(variable = ids, rol = "auxiliar")
)
roles$tipo <- sapply(roles$variable, tipo_de)
# Z repite variables de X a propósito (sección 4.2).
salida_vars <- unique(roles$variable)
stopifnot(all(salida_vars %in% names(d2)))

base <- d2[, salida_vars]
base$tam_soloaga14 <- as.character(base$tam_soloaga14)

# ==========================================
# 10. Diagnósticos
# ==========================================
# D2 paso 4: desviación del 20% por quintil después de las exclusiones.
reparto <- bind_rows(
  base %>% count(quintil = q_act_c1, wt = factor) %>%
    mutate(variable = "q_act_c1"),
  base %>% count(quintil = q_or_c1_imp, wt = factor) %>%
    mutate(variable = "q_or_c1_imp")
) %>%
  group_by(variable) %>%
  mutate(pct = 100 * n / sum(n), desviacion_pp = pct - 20) %>%
  ungroup() %>% select(variable, quintil, pct, desviacion_pp)
print(reparto)

faltantes <- data.frame(
  variable = c(x_principal, x_robustez_extra),
  rol = rep(c("X_principal", "X_robustez"),
            c(length(x_principal), length(x_robustez_extra))),
  n_na = sapply(c(x_principal, x_robustez_extra), function(v) sum(is.na(base[[v]]))),
  pct_na_pond = sapply(c(x_principal, x_robustez_extra), function(v)
    100 * sum(base$factor[is.na(base[[v]])]) / sum(base$factor))
)

resumen <- data.frame(
  indicador = c("n", "municipios de origen (cve_ice)", "UPM",
                "personas con ICE del padre (D21)",
                "fuera del núcleo del ICE en t0 o t1",
                "anio14 = 2011-2012 (población de 2010 en la robustez censal)",
                "migró de municipio (ponderado, %)",
                "R2 de ice14 sobre log_pob14 (MCO ponderado)",
                "correlación log_pob14 (CONAPO) vs log_pob14_censo"),
  valor = c(nrow(base), n_distinct(base$cve_ice), n_distinct(base$upm_muestra),
            sum(base$hijo_d21), sum(!base$en_nucleo14),
            sum(base$anio14 > max(ANIOS_POB)),
            100 * weighted.mean(base$migro, base$factor),
            summary(lm(ice14 ~ log_pob14, data = base, weights = factor))$r.squared,
            cor(base$log_pob14, base$log_pob14_censo))
)
print(resumen)

dist_edad <- base %>% count(edad, wt = factor, name = "n_pond") %>%
  mutate(pct_pond = 100 * n_pond / sum(n_pond),
         n = as.vector(table(base$edad)[as.character(edad)]))

# ==========================================
# 11. Guardar
# ==========================================
write.csv(flujo,      file.path(dir_res, "flujo_muestra_02.csv"), row.names = FALSE)
write.csv(tabla_d21,  file.path(dir_res, "municipios_padre_asignados.csv"), row.names = FALSE)
write.csv(ns_conteo,  file.path(dir_res, "codigos_no_sabe.csv"), row.names = FALSE)
write.csv(reparto,    file.path(dir_res, "reparto_quintiles_02.csv"), row.names = FALSE)
write.csv(faltantes,  file.path(dir_res, "faltantes_x.csv"), row.names = FALSE)
write.csv(resumen,    file.path(dir_res, "resumen_02.csv"), row.names = FALSE)
write.csv(dist_edad,  file.path(dir_res, "distribucion_edad.csv"), row.names = FALSE)
write.csv(roles,      file.path(dir_res, "diccionario_variables_02.csv"), row.names = FALSE)

saveRDS(base, here("data", "clean", "02_base_dml.rds"))
write.csv(base, here("data", "clean", "02_base_dml.csv"), row.names = FALSE,
          na = "", fileEncoding = "UTF-8")

writeLines(capture.output(sessionInfo()), file.path(dir_res, "sessionInfo_02.txt"))
