# NOTAS
# Para este código se replicó el código que el CEEY utiliza en Stata en R
# lo más fiel posible. Para hacer esto posible en esta parte del trabajo
# sí utilizamos IA.

# Ninguno de los integrantes del equipo cuenta con licencia de Stata, en
# momentos posteriores planeamos conseguirla y replicar más fielmente la
# metodología del CEEY, pero por ahora trabajaremos con esto para poder
# continuar con el desarrollo del proyecto.

# install.packages("FactoMineR")
# install.packages("Hmisc")

# ==========================================
# 0. Cargar librerías necesarias
# ==========================================
library(haven)
library(dplyr)
library(FactoMineR)
library(Hmisc)
library(here)

# ==========================================
# 1. Cargar base de datos
# ==========================================
esru <- read_dta(here("data","raw","entrevistado_2023.dta"))

n_original <- nrow(esru)

# ==========================================
# 2. Funciones auxiliares
# ==========================================

# Equivalente a crear una binaria después de que el .do recodifica 2 -> 0 y
# deja cualquier otro código no válido como missing.
binaria_01 <- function(x) {
  case_when(x == 1 ~ 1, x == 2 | x == 0 ~ 0, TRUE ~ NA_real_)
}

# Aproximación transparente a: xtile nueva = x [pw = w], nq(5).
# El corte ponderado es el menor valor cuya frecuencia acumulada alcanza cada
# 20 %. Los empates no se separan: todos los valores iguales quedan abajo.
xtile_ponderado <- function(x, w, nq = 5L) {
  valido <- !is.na(x) & !is.na(w) & w > 0
  salida <- rep(NA_integer_, length(x))
  if (!any(valido)) return(salida)
  
  orden <- order(x[valido])
  xs <- x[valido][orden]
  ws <- w[valido][orden]
  acumulado <- cumsum(ws)
  objetivos <- (seq_len(nq - 1L) / nq) * sum(ws)
  cortes <- vapply(objetivos, function(z) xs[which(acumulado >= z)[1]], numeric(1))
  
  # Usar > (no >=) mantiene cada valor igual al punto de corte en el quintil
  # inferior, como una clasificación construida a partir de cuantiles.
  salida[valido] <- 1L + rowSums(outer(x[valido], cortes, `>`))
  salida
}

# Estima por cohorte y escribe coordenadas sólo para e(sample), es decir, sólo
# para observaciones completas en todos los activos y con ponderador válido.
mca_por_cohorte <- function(datos, activos, cohorte, peso) {
  indice <- rep(NA_real_, nrow(datos))
  
  for (grupo in 1:4) {
    muestra <- datos[[cohorte]] == grupo &
      complete.cases(datos[, activos, drop = FALSE]) &
      !is.na(datos[[peso]]) & datos[[peso]] > 0
    muestra[is.na(muestra)] <- FALSE
    
    if (!any(muestra)) next
    
    x <- as.data.frame(lapply(datos[muestra, activos, drop = FALSE], factor))
    ajuste <- MCA(
      x,
      row.w = datos[[peso]][muestra],
      ncp = 1,
      graph = FALSE
    )
    
    # El .do cambia siempre el signo; no aplica una regla adaptativa posterior.
    indice[muestra] <- -ajuste$ind$coord[, 1]
  }
  
  indice
}

# ==========================================
# 3. Muestra y ponderador usados por el CEEY antes de los MCA
# ==========================================

# En el .do de 2023 se eliminan primero quienes no tienen educación propia,
# máximo educativo parental o región de origen. padres_edu ya viene construido
# en la base publicada; si no existe, se reproduce a partir de educp y educm.
if (!"padres_edu" %in% names(esru)) {
  esru <- esru %>%
    mutate(
      padres_edu = case_when(
        is.na(educp) & is.na(educm) ~ NA_real_,
        TRUE ~ pmax(educp, educm, na.rm = TRUE)
      )
    )
}

esru <- esru %>%
  filter(!is.na(educ), !is.na(padres_edu), !is.na(region_14)) %>%
  # Traducción literal de los dos redondeos del .do. Multiplicar todo por 10 no
  # cambia el MCA ni los cortes; el primer round() sí puede cambiar levemente
  # los pesos relativos.
  mutate(factor_ceey = round(factor) * 10)

n_filtros_ceey <- nrow(esru)

# ==========================================
# 4. Generación de Índice de Recursos Económicos (IRE) actual

# Metodología del CEEY para calcular el IRE actual comparable 2017-2023

# El cálculo es ligeramente distinto al del IRE actual NO comparable 2023

# El IRE actual NO comparable es más completo (no pierde información
# por ganar comparabilidad) y su cálculo viene especificado en el
# programa de cálculo de la ESRU-EMOVI Módulo de Inclusión Financiera (2023),
# pero nos decidimos por utilizar el comparable (cuyo cálculo viene
# especificado en el programa de cálculo de la ESRU-EMOVI) porque tiene
# una documentación más robusta sobre su elaboración y evidencia más clara
# de dónde fue utilizado. Una vez le preguntemos al CEEY cuál considera más
# apropiado, podremos confirmar si usar el comparable o el no comparable
# ==========================================

esru <- esru %>%
  mutate(
    ac1  = binaria_01(p96n),
    ac2  = binaria_01(p95d),
    ac3  = binaria_01(p96b),
    ac4  = binaria_01(p96l),
    ac5  = binaria_01(p95a),
    ac6  = case_when(is.na(p99) ~ NA_real_, p99 >= 1 ~ 1, p99 == 0 ~ 0,
                     TRUE ~ NA_real_),
    ac7  = binaria_01(p96i),
    ac8  = binaria_01(p96d),
    ac9 = case_when(
      p97d == 1 | p97j == 1 ~ 1,
      p97d %in% c(0, 2) & p97j %in% c(0, 2) ~ 0,
      TRUE ~ NA_real_
    ),
    ac10 = binaria_01(p96a),
    ac11 = binaria_01(p96o),
    ac12 = binaria_01(p95e),
    ac13 = case_when(
      p97e == 1 | p97f == 1 ~ 1,
      p97e %in% c(0, 2) & p97f %in% c(0, 2) ~ 0,
      TRUE ~ NA_real_
    ),
    ac14 = binaria_01(p97a),
    ac15 = binaria_01(p97b),
    ac16 = binaria_01(p97c),
    hacina = tamhog / p89,
    hac = case_when(hacina <= 2.5 ~ 1, hacina > 2.5 ~ 0,
                    TRUE ~ NA_real_)
  )

activos_actual <- c(paste0("ac", 1:16), "hac")
esru$ireccomp_act <- mca_por_cohorte(
  esru, activos_actual, "cohorte", "factor_ceey"
)

# ==========================================
# 5. Generación de Índice de Recursos Económicos (IRE) de origen

# Metodología del CEEY para calcular el IRE de origen comparable 2017-2023

# El cálculo es ligeramente distinto al del IRE de origen NO comparable 2023

# El IRE de origen NO comparable es más completo (no pierde información
# por ganar comparabilidad) y su cálculo viene especificado en el
# programa de cálculo de la ESRU-EMOVI Módulo de Inclusión Financiera (2023),
# pero nos decidimos por utilizar el comparable (cuyo cálculo viene
# especificado en el programa de cálculo de la ESRU-EMOVI) porque tiene
# una documentación más robusta sobre su elaboración y evidencia más clara
# de dónde fue utilizado. Una vez le preguntemos al CEEY cuál considera más
# apropiado, podremos confirmar siusar el comparable o el no comparable
# ==========================================

esru <- esru %>%
  mutate(
    # En el .do, tras recodificar 2 -> 0 y 8 -> missing, tarjeta_or y ahorro_or
    # terminan en cero incluso si ambos insumos son missing.
    tarjeta_or = if_else(p32f == 1 | p32g == 1, 1, 0, missing = 0),
    ahorro_or  = if_else(p32k == 1 | p32l == 1, 1, 0, missing = 0),
    auto_or = case_when(!is.na(p30) & p30 >= 1 ~ 1, p30 == 0 ~ 0,
                        TRUE ~ NA_real_),
    hacina_or = p22 / p23,
    hac_or = case_when(hacina_or <= 2.5 ~ 1, hacina_or > 2.5 ~ 0,
                       TRUE ~ NA_real_),
    ac_or1  = binaria_01(p31a),
    ac_or2  = binaria_01(p32a),
    ac_or3  = binaria_01(p31b),
    ac_or4  = binaria_01(p31h),
    ac_or5  = binaria_01(p31c),
    ac_or6  = binaria_01(p26a),
    ac_or7  = binaria_01(p31e),
    ac_or8  = binaria_01(p31d),
    ac_or9  = binaria_01(p31k),
    ac_or10 = binaria_01(p26b),
    ac_or11 = binaria_01(p31m),
    ac_or12 = binaria_01(p31i),
    ac_or13 = binaria_01(p32b),
    ac_or14 = binaria_01(p31g),
    # El .do convierte explícitamente el automóvil missing en cero aquí.
    ac_or15 = if_else(auto_or == 1, 1, 0, missing = 0),
    ac_or16 = binaria_01(p26d),
    ac_or17 = case_when(
      p32e == 1 | ahorro_or == 1 ~ 1,
      p32e %in% c(0, 2) & ahorro_or == 0 ~ 0,
      TRUE ~ NA_real_
    ),
    ac_or18 = case_when(tarjeta_or == 1 ~ 1, tarjeta_or == 0 ~ 0,
                        TRUE ~ NA_real_),
    ac_or19 = binaria_01(p26e)
  )

activos_origen <- c(paste0("ac_or", 1:19), "hac_or")
esru$ireccomp_or <- mca_por_cohorte(
  esru, activos_origen, "cohorte", "factor_ceey"
)

# ==========================================
# 6. Quintiles nacionales
# ==========================================

# El CEEY elimina primero los IRE de origen faltantes y después los actuales;
# por tanto, ambos quintiles se calculan sobre exactamente la misma muestra.
esru_ire <- esru %>%
  filter(!is.na(ireccomp_or), !is.na(ireccomp_act)) %>%
  mutate(
    quintilecomp_or  = xtile_ponderado(ireccomp_or, factor_ceey, 5),
    quintilecomp_act = xtile_ponderado(ireccomp_act, factor_ceey, 5)
  )

n_final <- nrow(esru_ire)

# Comprobaciones rápidas
stopifnot(
  all(esru_ire$quintilecomp_or %in% 1:5),
  all(esru_ire$quintilecomp_act %in% 1:5)
)

print(
  esru_ire %>%
    summarise(
      n = n(),
      ire_or_min = min(ireccomp_or),
      ire_or_max = max(ireccomp_or),
      ire_act_min = min(ireccomp_act),
      ire_act_max = max(ireccomp_act)
    )
)

print(prop.table(xtabs(factor_ceey ~ quintilecomp_or, data = esru_ire)))
print(prop.table(xtabs(factor_ceey ~ quintilecomp_act, data = esru_ire)))


## Antes de terminar, el código naturalmente filtra algunas observaciones
n_original - n_filtros_ceey

## Y además algunas tienen datos faltantes, también se excluyen; en total
## se pierden:
n_original - n_final

## Dimensión final
dim(esru_ire)

# Guardar base con IRE de origen y actual
saveRDS(
  esru_ire,
  here("data", "clean", "01_generar_ires_quintiles_esru.rds")
)