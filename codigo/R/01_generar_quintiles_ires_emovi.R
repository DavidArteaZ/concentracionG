# =============================================================================
# 01_generar_quintiles_ires_emovi.R
#
# Proyecto: Movilidad social y complejidad económica (ESRU-EMOVI 2023)
#
# Qué hace este script (y nada más):
#   1. Aplica los filtros previos al MCA del CEEY (educ, padres_edu, region_14).
#   2. Construye el Índice de Recursos Económicos COMPARABLE (IRE) actual y de
#      origen con MCA por cohorte, con corrección de signo adaptativa (D4).
#   3. Genera tres versiones del IRE de origen (D11):
#        - irec_or_ceey : regla del CEEY ("no sabe" -> 0 en tarjeta, ahorro y
#                         auto; p22 = 999 tal cual). SOLO para validar (T3).
#        - irec_or_na   : PRINCIPAL. "no sabe" -> NA; p22 = 999 -> NA (T5).
#        - irec_or_imp  : robustez. irec_or_na con activos imputados por
#                         missMDA::imputeMCA (solo cohorte de análisis).
#   4. Quintil nacional del CEEY (4 cohortes) y matriz de transición (T3).
#   5. Posición de destino y de origen DENTRO de la cohorte de análisis (D2, D3):
#      percentil continuo ponderado (empates = percentil promedio) y quintil.
#   6. Variante de robustez de D11: MCA sin los filtros de educ y padres_edu.
#   7. Tablas de diagnóstico: flujo de la muestra (T6), tasas de "no sabe"
#      (T6, T11), diagnóstico de los MCA, correlaciones entre versiones.
#
# Qué NO hace (va en scripts posteriores):
#   - Unión con el ICE (T17), exclusión de p20_COD = 33333/99999 (T18),
#     construcción de X (D6, D10, D13), auditoría de fugas (T4).
#   - IRE NO comparable (D1, robustez): su código no está en el .do del CEEY
#     disponible (viene en el programa del Módulo de Inclusión Financiera 2023).
#
# Fuente de la réplica: codigo/Informe de movilidad social en México 2025.do,
#   sección "INFORMACIÓN PARA 2023" (líneas 421-932).
#
# Desviaciones deliberadas respecto al .do (se reportan en el paper, T2):
#   a) FactoMineR::MCA sobre la matriz indicadora; el .do usa method(burt).
#      El eje principal es el mismo; la escala puede diferir.
#   b) El signo se orienta para que el índice tenga correlación ponderada
#      positiva con la proporción de activos que posee la persona. El .do
#      multiplica siempre por -1.
#   c) Solo en la versión principal (irec_or_na): "no sabe" -> NA y
#      p22 = 999 -> NA. La versión irec_or_ceey conserva la regla del .do.
#
# Pesos:
#   - factor_ceey = round(factor) * 10 (traducción literal de los dos redondeos
#     del .do). Se usa en los MCA y en todo lo que replica al CEEY (T3).
#   - factor (original, sin redondear) se usa en todas las posiciones propias
#     del proyecto (percentiles y quintiles dentro de la cohorte), T9.
#
# Salidas:
#   data/clean/01_generar_ires_quintiles_esru.rds  (una fila por persona con
#     region_14 no faltante; la muestra principal es muestra_ceey == TRUE)
#   data/clean/01_ire_resultados/*.csv  (diagnósticos)
#   data/clean/01_ire_resultados/sessionInfo_01.txt
#
# Nota de autoría: la réplica inicial del .do en R se hizo con ayuda de IA.
# =============================================================================

# ==========================================
# 0. Librerías y parámetros
# ==========================================
# install.packages(c("haven", "dplyr", "FactoMineR", "missMDA", "here"))
library(haven)
library(dplyr)
library(FactoMineR)
library(missMDA)
library(here)

SEMILLA           <- 20260929
COHORTE_ANALISIS  <- 1L     # 25-34 años (D2)
NCP_IMPUTACION    <- NULL   # NULL = se elige por validación cruzada (estim_ncpMCA)
NBSIM_CV          <- 20L    # repeticiones de la validación cruzada de ncp
NCP_MAX_CV        <- 10L    # tope de ncp en la validación cruzada. Con 5, la
                            # corrida del 29/09/2026 eligió ncp = 5 (en el tope).

# Referencia T3: cifras publicadas por el CEEY (presentación del Informe de
# Movilidad Social en México 2025, julio de 2025), redondeadas a enteros.
# Q1 -> (Q1..Q5) = 50, 28, 14, 7, 2. Por sexo: Q1->Q1 mujeres 51, hombres 49;
# Q5->Q5 mujeres 47, hombres 53. El total de Q5->Q5 no se publica; se usa 50.
# Corrida del 29/09/2026: Q1->Q1 = 50.3, Q5->Q5 = 50.7 (T3 cerrada).
REF_T3 <- c(q1_q1 = 50, q5_q5 = 50)
TOL_T3 <- 2  # puntos porcentuales

set.seed(SEMILLA)

dir_res <- here("data", "clean", "01_ire_resultados")
dir.create(dir_res, recursive = TRUE, showWarnings = FALSE)

# ==========================================
# 1. Datos
# ==========================================
esru_raw <- read_dta(here("data", "raw", "entrevistado_2023.dta")) %>%
  zap_labels()

stopifnot(!anyDuplicated(esru_raw$index))
stopifnot(all(!is.na(esru_raw$factor) & esru_raw$factor > 0))

# ==========================================
# 2. Funciones auxiliares
# ==========================================

# Binaria 1/0 tras el recode (2 = 0) del .do. Cualquier otro código
# (8 = "no sabe", NA) queda como NA.
binaria_01 <- function(x) {
  case_when(x == 1 ~ 1, x %in% c(0, 2) ~ 0, TRUE ~ NA_real_)
}

# 1 si alguno de los dos es "sí"; 0 si ambos son "no"; NA en otro caso.
# Regla principal de D11 para tarjeta y ahorro de origen.
una_de_dos <- function(a, b) {
  case_when(
    a == 1 | b == 1                ~ 1,
    a %in% c(0, 2) & b %in% c(0, 2) ~ 0,
    TRUE                            ~ NA_real_
  )
}

# Equivalente a: xtile nueva = x [pw = w], nq(nq).
# Corte k = menor valor cuya frecuencia ponderada acumulada alcanza k/nq.
# Los valores iguales al corte quedan en el grupo inferior. Cuando el
# acumulado coincide exactamente con k/nq, Stata usa el promedio de x_i y
# x_{i+1} como corte; la clasificación resultante es idéntica.
xtile_ponderado <- function(x, w, nq = 5L) {
  valido <- !is.na(x) & !is.na(w) & w > 0
  salida <- rep(NA_integer_, length(x))
  if (!any(valido)) return(salida)

  orden <- order(x[valido])
  xs <- x[valido][orden]
  ws <- w[valido][orden]
  acumulado <- cumsum(ws)
  objetivos <- (seq_len(nq - 1L) / nq) * sum(ws)
  cortes <- vapply(objetivos, function(z) xs[which(acumulado >= z)[1]],
                   numeric(1))

  salida[valido] <- 1L + rowSums(outer(x[valido], cortes, `>`))
  salida
}

# Percentil continuo ponderado (D3), escala 0-100.
# pct(v) = 100 * [W(x < v) + W(x = v) / 2] / W_total
# Los empates reciben el percentil promedio de su grupo. Por construcción,
# la media ponderada del percentil es exactamente 50.
# Se redondea a 10 decimales solo para detectar empates numéricos.
pct_ponderado <- function(x, w) {
  valido <- !is.na(x) & !is.na(w) & w > 0
  salida <- rep(NA_real_, length(x))
  if (!any(valido)) return(salida)

  xv <- round(x[valido], 10)
  wv <- w[valido]
  niveles <- sort(unique(xv))
  w_nivel <- as.numeric(tapply(wv, factor(xv, levels = niveles), sum))
  w_abajo <- cumsum(w_nivel) - w_nivel
  pct_nivel <- 100 * (w_abajo + w_nivel / 2) / sum(wv)
  salida[valido] <- pct_nivel[match(xv, niveles)]
  salida
}

cor_pond <- function(x, y, w) {
  ok <- !is.na(x) & !is.na(y) & !is.na(w)
  cov.wt(cbind(x[ok], y[ok]), wt = w[ok], cor = TRUE)$cor[1, 2]
}

# Factores con etiquetas únicas por variable (evita categorías con el mismo
# nombre en FactoMineR/missMDA; no cambia el MCA).
a_factores <- function(df) {
  as.data.frame(lapply(names(df), function(v) {
    factor(ifelse(is.na(df[[v]]), NA, paste0(v, "_", df[[v]])))
  }), col.names = names(df))
}

# Orientación del signo (D4): correlación ponderada positiva con la
# proporción de activos que posee la persona (1 = más recursos en todas las
# variables activas, incluido hac/hac_or, donde 1 = sin hacinamiento).
orientar <- function(coord, activos_df, w) {
  prop_activos <- rowMeans(activos_df, na.rm = TRUE)
  r <- cor_pond(coord, prop_activos, w)
  list(signo = if (r < 0) -1 else 1, r = r)
}

# MCA por cohorte sobre casos completos (equivale a predict ... if e(sample)).
mca_por_cohorte <- function(datos, activos, peso, version, cohortes = 1:4) {
  indice <- rep(NA_real_, nrow(datos))
  diag <- list()

  for (g in cohortes) {
    muestra <- datos$cohorte == g &
      complete.cases(datos[, activos, drop = FALSE])
    muestra[is.na(muestra)] <- FALSE
    if (!any(muestra)) next

    w <- datos[[peso]][muestra]
    ajuste <- MCA(a_factores(datos[muestra, activos, drop = FALSE]),
                  row.w = w, ncp = 1, graph = FALSE)
    coord <- ajuste$ind$coord[, 1]
    o <- orientar(coord, datos[muestra, activos, drop = FALSE], w)
    indice[muestra] <- o$signo * coord

    diag[[length(diag) + 1]] <- data.frame(
      version = version, cohorte = g,
      n_cohorte = sum(datos$cohorte == g, na.rm = TRUE),
      n_mca = sum(muestra), eig1 = ajuste$eig[1, 1],
      pct_inercia1 = ajuste$eig[1, 2], ncp_imput = NA_integer_,
      r_signo = o$r, signo = o$signo
    )
  }
  list(indice = indice, diag = bind_rows(diag))
}

# MCA con imputación (robustez de D11). Solo la cohorte indicada.
mca_imputado <- function(datos, activos, peso, version, cohorte, ncp = NULL) {
  indice <- rep(NA_real_, nrow(datos))
  sub <- datos$cohorte == cohorte
  sub[is.na(sub)] <- FALSE

  x <- a_factores(datos[sub, activos, drop = FALSE])
  w <- datos[[peso]][sub]

  if (is.null(ncp)) {
    set.seed(SEMILLA)
    cv <- estim_ncpMCA(x, ncp.min = 0, ncp.max = NCP_MAX_CV, method = "Regularized",
                       method.cv = "Kfold", nbsim = NBSIM_CV, pNA = 0.05,
                       verbose = FALSE)
    ncp <- cv$ncp
  }
  imp <- imputeMCA(x, ncp = ncp, method = "Regularized", row.w = w,
                   seed = SEMILLA)
  ajuste <- MCA(x, tab.disj = imp$tab.disj, row.w = w, ncp = 1,
                graph = FALSE)
  coord <- ajuste$ind$coord[, 1]
  o <- orientar(coord, datos[sub, activos, drop = FALSE], w)
  indice[sub] <- o$signo * coord

  diag <- data.frame(
    version = version, cohorte = cohorte, n_cohorte = sum(sub),
    n_mca = sum(sub), eig1 = ajuste$eig[1, 1],
    pct_inercia1 = ajuste$eig[1, 2], ncp_imput = ncp,
    r_signo = o$r, signo = o$signo
  )
  list(indice = indice, diag = diag)
}

# ==========================================
# 3. Filtros previos al MCA (muestra del CEEY) y flujo de la muestra (T6)
# ==========================================
# padres_edu = máximo de educp y educm (egen rowmax del .do).
esru <- esru_raw %>%
  mutate(
    padres_edu = case_when(
      is.na(educp) & is.na(educm) ~ NA_real_,
      TRUE ~ pmax(educp, educm, na.rm = TRUE)
    ),
    factor_ceey = round(factor) * 10
  )

paso <- function(d, etiqueta) {
  data.frame(
    paso = etiqueta,
    n_total = nrow(d),
    n_cohorte_analisis = sum(d$cohorte == COHORTE_ANALISIS, na.rm = TRUE)
  )
}

f0 <- esru
f1 <- f0 %>% filter(!is.na(educ))
f2 <- f1 %>% filter(!is.na(padres_edu))
f3 <- f2 %>% filter(!is.na(region_14))

flujo <- bind_rows(
  paso(f0, "0. Base original"),
  paso(f1, "1. Con educ (filtro CEEY, secuencial)"),
  paso(f2, "2. Con padres_edu (filtro CEEY, secuencial)"),
  paso(f3, "3. Con region_14 = muestra CEEY previa al MCA")
)
rm(f0, f1, f2, f3)

# Base de salida: todas las personas con region_14. La variante de robustez
# de D11 conserva a quienes no tienen educ o padres_edu.
esru <- esru %>%
  filter(!is.na(region_14)) %>%
  mutate(muestra_ceey = !is.na(educ) & !is.na(padres_edu))

# ==========================================
# 4. Activos del hogar actual (IRE actual comparable)
# ==========================================
esru <- esru %>%
  mutate(
    ac1  = binaria_01(p96n),  # computadora
    ac2  = binaria_01(p95d),  # boiler
    ac3  = binaria_01(p96b),  # lavadora
    ac4  = binaria_01(p96l),  # internet
    ac5  = binaria_01(p95a),  # agua entubada
    ac6  = case_when(p99 >= 1 ~ 1, p99 == 0 ~ 0, TRUE ~ NA_real_),  # auto
    ac7  = binaria_01(p96i),  # TV de paga
    ac8  = binaria_01(p96d),  # microondas
    ac9  = una_de_dos(p97d, p97j),  # cuenta bancaria
    ac10 = binaria_01(p96a),  # estufa
    ac11 = binaria_01(p96o),  # maquinaria agrícola
    ac12 = binaria_01(p95e),  # servicio doméstico
    ac13 = una_de_dos(p97e, p97f),  # tarjeta de crédito
    ac14 = binaria_01(p97a),  # otra vivienda
    ac15 = binaria_01(p97b),  # local comercial
    ac16 = binaria_01(p97c),  # terreno
    hacina = tamhog / p89,
    # En Stata un missing es mayor que 2.5, así que el .do asigna hac = 0 a un
    # cociente faltante. Se replica; en 2023 no hay p89 = 0 ni faltantes.
    hac = case_when(hacina <= 2.5 ~ 1, TRUE ~ 0)
  )

activos_actual <- c(paste0("ac", 1:16), "hac")

# ==========================================
# 5. Activos del hogar de origen: regla CEEY y regla principal (D11, T5)
# ==========================================
activos_origen_base <- c(paste0("ac_or", 1:19), "hac_or")

construir_origen <- function(d, regla) {
  if (regla == "ceey") {
    # Traducción del .do: tarjeta y ahorro valen 0 aun si ambos insumos son
    # "no sabe"; el auto faltante se vuelve 0; p22 = 999 se usa tal cual
    # (queda como hacinado).
    tarjeta <- if_else(d$p32f == 1 | d$p32g == 1, 1, 0, missing = 0)
    ahorro  <- if_else(d$p32k == 1 | d$p32l == 1, 1, 0, missing = 0)
    auto    <- case_when(d$p30 >= 1 ~ 1, d$p30 == 0 ~ 0, TRUE ~ 0)
    hacina  <- d$p22 / d$p23
    hac_or  <- case_when(hacina <= 2.5 ~ 1, TRUE ~ 0)
  } else if (regla == "na") {
    # D11: "no sabe" -> NA. T5: p22 = 999 ("no recuerda") -> NA.
    # p30 no tiene código de "no sabe" (rango 0-20), así que auto no cambia.
    tarjeta <- una_de_dos(d$p32f, d$p32g)
    ahorro  <- una_de_dos(d$p32k, d$p32l)
    auto    <- case_when(d$p30 >= 1 ~ 1, d$p30 == 0 ~ 0, TRUE ~ NA_real_)
    hacina  <- if_else(d$p22 == 999, NA_real_, d$p22) / d$p23
    hac_or  <- case_when(hacina <= 2.5 ~ 1, hacina > 2.5 ~ 0,
                         TRUE ~ NA_real_)
  } else stop("regla desconocida")

  out <- tibble(
    ac_or1  = binaria_01(d$p31a),  # estufa
    ac_or2  = binaria_01(d$p32a),  # otra vivienda
    ac_or3  = binaria_01(d$p31b),  # lavadora
    ac_or4  = binaria_01(d$p31h),  # TV por cable
    ac_or5  = binaria_01(d$p31c),  # refrigerador
    ac_or6  = binaria_01(d$p26a),  # agua entubada
    ac_or7  = binaria_01(d$p31e),  # televisor
    ac_or8  = binaria_01(d$p31d),  # teléfono fijo
    ac_or9  = binaria_01(d$p31k),  # computadora
    ac_or10 = binaria_01(d$p26b),  # electricidad
    ac_or11 = binaria_01(d$p31m),  # VHS/DVD
    ac_or12 = binaria_01(d$p31i),  # microondas
    ac_or13 = binaria_01(d$p32b),  # local comercial
    ac_or14 = binaria_01(d$p31g),  # aspiradora
    ac_or15 = auto,                # automóvil
    ac_or16 = binaria_01(d$p26d),  # boiler
    ac_or17 = case_when(           # cuenta de ahorro / cheques
      d$p32e == 1 | ahorro == 1         ~ 1,
      d$p32e %in% c(0, 2) & ahorro == 0 ~ 0,
      TRUE                              ~ NA_real_
    ),
    ac_or18 = tarjeta,             # tarjeta de crédito
    ac_or19 = binaria_01(d$p26e),  # servicio doméstico
    hac_or  = hac_or               # 1 = sin hacinamiento
  )
  names(out) <- paste0(names(out), "_", regla)
  out
}

esru <- bind_cols(esru, construir_origen(esru, "ceey"),
                  construir_origen(esru, "na"))

activos_or_ceey <- paste0(activos_origen_base, "_ceey")
activos_or_na   <- paste0(activos_origen_base, "_na")

# ==========================================
# 6. IRE comparable: especificación principal (muestra CEEY)
# ==========================================
ceey <- esru$muestra_ceey
d_ceey <- esru[ceey, ]

res_act     <- mca_por_cohorte(d_ceey, activos_actual, "factor_ceey", "act")
res_or_ceey <- mca_por_cohorte(d_ceey, activos_or_ceey, "factor_ceey", "or_ceey")
res_or_na   <- mca_por_cohorte(d_ceey, activos_or_na,   "factor_ceey", "or_na")
res_or_imp  <- mca_imputado(d_ceey, activos_or_na, "factor_ceey", "or_imp",
                            cohorte = COHORTE_ANALISIS, ncp = NCP_IMPUTACION)

esru$irec_act     <- NA_real_
esru$irec_or_ceey <- NA_real_
esru$irec_or_na   <- NA_real_
esru$irec_or_imp  <- NA_real_
esru$irec_act[ceey]     <- res_act$indice
esru$irec_or_ceey[ceey] <- res_or_ceey$indice
esru$irec_or_na[ceey]   <- res_or_na$indice
esru$irec_or_imp[ceey]  <- res_or_imp$indice

# ==========================================
# 7. Robustez D11: MCA sin los filtros de educ y padres_edu
# ==========================================
res_act_sf   <- mca_por_cohorte(esru, activos_actual, "factor_ceey", "act_sinfiltro")
res_or_na_sf <- mca_por_cohorte(esru, activos_or_na, "factor_ceey", "or_na_sinfiltro")
esru$irec_act_sf   <- res_act_sf$indice
esru$irec_or_na_sf <- res_or_na_sf$indice

diag_mca <- bind_rows(res_act$diag, res_or_ceey$diag, res_or_na$diag,
                      res_or_imp$diag, res_act_sf$diag, res_or_na_sf$diag)
print(diag_mca)
stopifnot(all(diag_mca$r_signo * diag_mca$signo > 0))

# ==========================================
# 8. Quintiles nacionales del CEEY (4 cohortes) y validación T3
# ==========================================
# Como en el .do: se descartan los IRE faltantes y ambos quintiles se
# calculan sobre la misma muestra con factor_ceey.
m_t3 <- ceey & !is.na(esru$irec_or_ceey) & !is.na(esru$irec_act)
esru$q_or_nac_ceey  <- NA_integer_
esru$q_act_nac_ceey <- NA_integer_
esru$q_or_nac_ceey[m_t3]  <- xtile_ponderado(esru$irec_or_ceey[m_t3],
                                             esru$factor_ceey[m_t3])
esru$q_act_nac_ceey[m_t3] <- xtile_ponderado(esru$irec_act[m_t3],
                                             esru$factor_ceey[m_t3])

# Matriz de transición: % por renglón, [aw = factor] (tab ..., row nofreq).
matriz_t3 <- esru[m_t3, ] %>%
  group_by(q_or = q_or_nac_ceey, q_act = q_act_nac_ceey) %>%
  summarise(w = sum(factor_ceey), .groups = "drop") %>%
  group_by(q_or) %>%
  mutate(pct = 100 * w / sum(w)) %>%
  ungroup()
matriz_t3_ancha <- xtabs(pct ~ q_or + q_act, data = matriz_t3)
print(round(matriz_t3_ancha, 1))

t3 <- c(
  q1_q1 = matriz_t3$pct[matriz_t3$q_or == 1 & matriz_t3$q_act == 1],
  q5_q5 = matriz_t3$pct[matriz_t3$q_or == 5 & matriz_t3$q_act == 5]
)
t3_ok <- all(abs(t3 - REF_T3) <= TOL_T3)
message(sprintf("T3: Q1->Q1 = %.1f%% (ref. %.0f), Q5->Q5 = %.1f%% (ref. %.0f)",
                t3["q1_q1"], REF_T3["q1_q1"], t3["q5_q5"], REF_T3["q5_q5"]))
if (!t3_ok) {
  warning("T3 NO se replica dentro de la tolerancia. No avanzar hasta revisar.")
}

# ==========================================
# 9. Posiciones propias del proyecto (D2, D3). Pesos: factor original.
# ==========================================
c1 <- ceey & esru$cohorte == COHORTE_ANALISIS

# Destino: percentil y quintil dentro de la cohorte. Incluye a quienes no
# tienen IRE de origen (D11).
esru$pct_act_c1 <- NA_real_
esru$q_act_c1   <- NA_integer_
esru$pct_act_c1[c1] <- pct_ponderado(esru$irec_act[c1], esru$factor[c1])
esru$q_act_c1[c1]   <- xtile_ponderado(esru$irec_act[c1], esru$factor[c1])

# Origen: percentil y quintil dentro de la cohorte, para cada versión.
# Quien no tiene IRE de origen en una versión queda con NA en esa versión.
for (v in c("ceey", "na", "imp")) {
  ire <- esru[[paste0("irec_or_", v)]]
  pct <- rep(NA_real_, nrow(esru))
  q   <- rep(NA_integer_, nrow(esru))
  pct[c1] <- pct_ponderado(ire[c1], esru$factor[c1])
  q[c1]   <- xtile_ponderado(ire[c1], esru$factor[c1])
  esru[[paste0("pct_or_c1_", v)]] <- pct
  esru[[paste0("q_or_c1_", v)]]   <- q
}

# Robustez D2: quintil nacional de destino con las 4 cohortes, SIN descartar
# a quienes no tienen IRE de origen (D11), con el factor original.
esru$q_act_nac <- NA_integer_
esru$q_act_nac[ceey] <- xtile_ponderado(esru$irec_act[ceey], esru$factor[ceey])

# Robustez D11 (sin filtros de educ y padres_edu): destino dentro de la cohorte.
c1_sf <- esru$cohorte == COHORTE_ANALISIS
esru$pct_act_c1_sf <- NA_real_
esru$pct_act_c1_sf[c1_sf] <- pct_ponderado(esru$irec_act_sf[c1_sf],
                                           esru$factor[c1_sf])
esru$pct_or_c1_na_sf <- NA_real_
esru$pct_or_c1_na_sf[c1_sf] <- pct_ponderado(esru$irec_or_na_sf[c1_sf],
                                             esru$factor[c1_sf])

# ==========================================
# 10. Comprobaciones
# ==========================================
# Media ponderada del percentil = 50 por construcción.
chk_pct <- function(p, w) sum(p * w, na.rm = TRUE) / sum(w[!is.na(p)])
stopifnot(abs(chk_pct(esru$pct_act_c1, esru$factor) - 50) < 1e-8)
stopifnot(all(esru$pct_act_c1[c1] > 0 & esru$pct_act_c1[c1] < 100))

# El IRE actual no debe tener faltantes en la muestra CEEY.
stopifnot(!anyNA(esru$irec_act[ceey]))

# Persistencia por sexo (T3, comparación con las cifras publicadas por sexo).
t3_sexo <- esru[m_t3, ] %>%
  group_by(sexo, q_or = q_or_nac_ceey, q_act = q_act_nac_ceey) %>%
  summarise(w = sum(factor_ceey), .groups = "drop") %>%
  group_by(sexo, q_or) %>%
  mutate(pct = 100 * w / sum(w)) %>%
  ungroup() %>%
  filter((q_or == 1 & q_act %in% c(1, 5)) | (q_or == 5 & q_act == 5))
print(t3_sexo)

# Participación ponderada por quintil (con empates, no será exactamente 20%).
reparto <- bind_rows(
  esru[c1, ] %>% count(q = q_act_c1, wt = factor) %>%
    mutate(variable = "q_act_c1"),
  esru[c1 & !is.na(esru$q_or_c1_na), ] %>% count(q = q_or_c1_na, wt = factor) %>%
    mutate(variable = "q_or_c1_na"),
  esru[m_t3, ] %>% count(q = q_act_nac_ceey, wt = factor_ceey) %>%
    mutate(variable = "q_act_nac_ceey"),
  esru[m_t3, ] %>% count(q = q_or_nac_ceey, wt = factor_ceey) %>%
    mutate(variable = "q_or_nac_ceey")
) %>%
  group_by(variable) %>% mutate(pct = 100 * n / sum(n)) %>% ungroup()
print(reparto)

# ==========================================
# 11. Diagnósticos para el paper
# ==========================================
# 11a. Flujo de la muestra (T6).
flujo <- bind_rows(
  flujo,
  data.frame(
    paso = c(
      "4. Con IRE actual",
      "5a. Con IRE de origen, regla CEEY",
      "5b. Con IRE de origen, regla principal (NS -> NA)",
      "5c. Con IRE de origen imputado (solo cohorte de análisis)",
      "6. Muestra T3 (IRE origen CEEY y actual no faltantes)"
    ),
    n_total = c(sum(ceey & !is.na(esru$irec_act)),
                sum(ceey & !is.na(esru$irec_or_ceey)),
                sum(ceey & !is.na(esru$irec_or_na)),
                sum(ceey & !is.na(esru$irec_or_imp)),
                sum(m_t3)),
    n_cohorte_analisis = c(sum(c1 & !is.na(esru$irec_act)),
                           sum(c1 & !is.na(esru$irec_or_ceey)),
                           sum(c1 & !is.na(esru$irec_or_na)),
                           sum(c1 & !is.na(esru$irec_or_imp)),
                           sum(m_t3 & esru$cohorte == COHORTE_ANALISIS))
  )
)
print(flujo)

# 11b. Faltantes por activo de origen (regla principal) en la cohorte.
faltantes_or <- data.frame(
  activo = activos_or_na,
  n_na = colSums(is.na(esru[c1, activos_or_na])),
  pct_na = 100 * colMeans(is.na(esru[c1, activos_or_na]))
)

# 11c. Tasas de "no sabe" de origen (T6, T11): alguna respuesta NS (código 8)
# en las preguntas que alimentan el IRE de origen, por cohorte y, en la
# cohorte de análisis, por quintil de destino.
vars_ns <- c("p26a", "p26b", "p26d", "p26e",
             paste0("p31", c("a", "b", "c", "d", "e", "g", "h", "i", "k", "m")),
             paste0("p32", c("a", "b", "e", "f", "g", "k", "l")))
esru$algun_ns_or <- as.integer(rowSums(esru[, vars_ns] == 8, na.rm = TRUE) > 0)

ns_cohorte <- esru[ceey, ] %>%
  group_by(cohorte) %>%
  summarise(n = n(),
            pct_algun_ns = 100 * weighted.mean(algun_ns_or, factor),
            .groups = "drop")
ns_destino <- esru[c1, ] %>%
  group_by(q_act_c1) %>%
  summarise(n = n(),
            pct_algun_ns = 100 * weighted.mean(algun_ns_or, factor),
            pct_sin_irec_or_na = 100 * weighted.mean(is.na(irec_or_na), factor),
            .groups = "drop")
print(ns_cohorte)
print(ns_destino)

# 11d. Correlaciones entre versiones del índice en la cohorte de análisis.
cor_versiones <- data.frame(
  par = c("irec_or_ceey vs irec_or_na",
          "irec_or_na vs irec_or_imp",
          "irec_or_ceey vs irec_or_imp",
          "irec_act vs irec_act_sf (D11 sin filtros)",
          "irec_or_na vs irec_or_na_sf (D11 sin filtros)"),
  pearson_pond = c(
    cor_pond(esru$irec_or_ceey[c1], esru$irec_or_na[c1], esru$factor[c1]),
    cor_pond(esru$irec_or_na[c1],   esru$irec_or_imp[c1], esru$factor[c1]),
    cor_pond(esru$irec_or_ceey[c1], esru$irec_or_imp[c1], esru$factor[c1]),
    cor_pond(esru$irec_act[c1],     esru$irec_act_sf[c1], esru$factor[c1]),
    cor_pond(esru$irec_or_na[c1],   esru$irec_or_na_sf[c1], esru$factor[c1])
  )
)
print(cor_versiones)

write.csv(flujo,           file.path(dir_res, "flujo_muestra.csv"), row.names = FALSE)
write.csv(diag_mca,        file.path(dir_res, "diagnostico_mca.csv"), row.names = FALSE)
write.csv(as.data.frame.matrix(matriz_t3_ancha),
          file.path(dir_res, "t3_matriz_transicion_nacional.csv"))
write.csv(t3_sexo,         file.path(dir_res, "t3_persistencia_por_sexo.csv"), row.names = FALSE)
write.csv(reparto,         file.path(dir_res, "reparto_quintiles.csv"), row.names = FALSE)
write.csv(faltantes_or,    file.path(dir_res, "faltantes_activos_origen_c1.csv"), row.names = FALSE)
write.csv(ns_cohorte,      file.path(dir_res, "ns_origen_por_cohorte.csv"), row.names = FALSE)
write.csv(ns_destino,      file.path(dir_res, "ns_origen_por_quintil_destino_c1.csv"), row.names = FALSE)
write.csv(cor_versiones,   file.path(dir_res, "correlaciones_versiones_ire.csv"), row.names = FALSE)

# ==========================================
# 12. Guardar
# ==========================================
# Una fila por persona con region_14 no faltante.
#   Muestra principal: muestra_ceey == TRUE & cohorte == COHORTE_ANALISIS.
#   Robustez D11 sin filtros: cohorte == COHORTE_ANALISIS (columnas *_sf).
# Ningún script posterior recalcula el IRE.
saveRDS(esru, here("data", "clean", "01_generar_ires_quintiles_esru.rds"))

writeLines(capture.output(sessionInfo()),
           file.path(dir_res, "sessionInfo_01.txt"))
