# Exportacion compatible con el lector de columnas decimales de GeoDa 1.22.1.
# Ausencia de una propiedad = campo no establecido (unset), que GeoDa reconoce
# como undefined. Un null explicito puede confundirse con cero en ese lector.
exportar_geojson_geoda <- function(base, salida) {
  stopifnot(inherits(base,"sf"),!anyDuplicated(base$CVEGEO),!anyNA(base$CVEGEO))
  if(file.exists(salida)) stop("La salida GeoJSON ya existe: ",salida)
  dir.create(dirname(salida),recursive=TRUE,showWarnings=FALSE)
  intermedio <- tempfile(fileext=".geojson")
  on.exit(unlink(intermedio),add=TRUE)
  sf::st_write(base,intermedio,driver="GeoJSON",quiet=TRUE,
    layer=sub("\\.geojson$","",basename(salida)),
    layer_options=c("RFC7946=NO","SIGNIFICANT_FIGURES=17","COORDINATE_PRECISION=17"))
  atributos <- sf::st_drop_geometry(base)
  incompletas <- names(atributos)[vapply(atributos,anyNA,logical(1))]
  stopifnot(all(grepl("^[A-Za-z0-9_]+$",incompletas)))
  patron <- paste0(',\\s*"(',paste(incompletas,collapse="|"),')"\\s*:\\s*null')
  entrada <- file(intermedio,open="rt",encoding="UTF-8")
  archivo_salida <- file(salida,open="wt",encoding="UTF-8")
  tryCatch({
    repeat {
      lineas <- readLines(entrada,n=16,warn=FALSE)
      if(!length(lineas)) break
      if(length(incompletas)) lineas <- gsub(patron,"",lineas,perl=TRUE)
      writeLines(lineas,archivo_salida,useBytes=TRUE)
    }
  },finally={close(entrada);close(archivo_salida)})
  comprobacion <- sf::st_read(salida,quiet=TRUE,stringsAsFactors=FALSE)
  stopifnot(nrow(comprobacion)==nrow(base),identical(names(comprobacion),names(base)),
    identical(comprobacion$CVEGEO,base$CVEGEO),sf::st_crs(comprobacion)==sf::st_crs(base),
    identical(sf::st_as_binary(sf::st_geometry(comprobacion)),sf::st_as_binary(sf::st_geometry(base))))
  for(v in names(atributos)) {
    stopifnot(identical(is.na(base[[v]]),is.na(comprobacion[[v]])))
    if(is.numeric(base[[v]])) stopifnot(isTRUE(all.equal(base[[v]],comprobacion[[v]],tolerance=1e-13,check.attributes=FALSE)))
    else stopifnot(identical(base[[v]],comprobacion[[v]]))
  }
  invisible(salida)
}
