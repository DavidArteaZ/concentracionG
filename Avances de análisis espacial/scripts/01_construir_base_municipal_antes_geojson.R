# Base espacial municipal: movilidad relativa por IRE y estructura productiva 2023.
# No reconstruye indices ni recalcula posiciones. No modifica archivos de entrada.
# Uso: Rscript scripts/01_construir_base_municipal.R [raiz_proyecto] [base_IRE.rds] [raiz_salida]
# El tercer argumento permite preparar y verificar resultados en otra carpeta.
required <- c("sf", "dplyr", "readr", "haven")
missing <- required[!vapply(required, requireNamespace, logical(1), quietly=TRUE)]
if (length(missing)) stop("Faltan paquetes: ", paste(missing,collapse=", "))
suppressPackageStartupMessages({library(sf);library(dplyr);library(readr)})
args <- commandArgs(trailingOnly=TRUE)
script_arg <- grep("^--file=",commandArgs(),value=TRUE)
script_path <- normalizePath(sub("^--file=","",script_arg[1]),mustWork=TRUE)
project_root <- if(length(args)>=1) normalizePath(args[1],mustWork=TRUE) else dirname(dirname(script_path))
default_ire <- paste0("/Users/andonigarritzayala/Desktop/Tec/Semestre IX (Concentración CD)/Proyecto de investigación/",
  "Avances de la investigación/Entregas/Entregas (Nayeli)/Primera entrega (primer borrador)/",
  "Correcciones/Código e imágenes extra/01_generar_ires_quintiles_esru.rds")
ire_path <- normalizePath(if(length(args)>=2) args[2] else default_ire,mustWork=TRUE)
output_root <- if(length(args)>=3) args[3] else project_root
clean <- file.path(output_root,"data","clean")
docs <- file.path(output_root,"docs")
dir.create(clean,recursive=TRUE,showWarnings=FALSE)
dir.create(docs,recursive=TRUE,showWarnings=FALSE)
stem <- "municipios_mov_ice_2023"
shp_path <- file.path(clean,paste0(stem,".shp"))
if (any(file.exists(file.path(clean,paste0(stem,c(".shp",".shx",".dbf",".prj",".cpg",".csv",".rds"))))))
  stop("Ya existen salidas con este nombre; no se sobrescriben automaticamente.")
raw <- file.path(project_root,"data","raw")
shape_path <- file.path(raw,"00mun.shp")
ice_path <- file.path(raw,"ice_municipal.csv")
ec_path <- file.path(raw,"ecomplexity_rama_ue_2023.csv")
saic_path <- file.path(raw,"2023_SAIC_Exporta_202698_037586.csv")
save_table <- function(x,path) write_csv(as.data.frame(x),path,na="NA")
weighted_safe <- function(x,w) {
  ok <- is.finite(x)&is.finite(w)&w>0
  if(!any(ok)) return(NA_real_)
  sum(x[ok]*w[ok])/sum(w[ok])
}

# 1. Poligonos originales: una fila por municipio, sin recorte ni disolucion.
g <- st_read(shape_path,quiet=TRUE,stringsAsFactors=FALSE)
stopifnot(!anyDuplicated(g$CVEGEO), all(g$CVEGEO==paste0(g$CVE_ENT,g$CVE_MUN)),
          !any(st_is_empty(g)), all(st_is_valid(g)), !is.na(st_crs(g)))
original_n <- nrow(g)
original_crs <- st_crs(g)
original_geom <- st_as_binary(st_geometry(g))

# 2. Misma especificacion de IRE que las matrices previas del proyecto.
# El script de generacion tambien ofrece *_na e *_imp: no se sustituyen aqui.
b <- readRDS(ire_path)
needed <- c("index","edad","p20_COD","factor","ingc_pc",
  "pct_or_c1_ceey","pct_act_c1","q_or_c1_ceey","q_act_c1")
stopifnot(all(needed %in% names(b)),!anyDuplicated(b$index))
municipality <- suppressWarnings(as.integer(as.character(b$p20_COD)))
valid_code <- !is.na(municipality)&municipality%/%1000 %in% 1:32&municipality%%1000>0&municipality%%1000<999
d <- data.frame(id=b$index,edad=as.numeric(b$edad),cvegeo=ifelse(valid_code,sprintf("%05d",municipality),NA_character_),
  w=as.numeric(b$factor),ro=as.numeric(b$pct_or_c1_ceey),rd=as.numeric(b$pct_act_c1),
  qo=as.integer(b$q_or_c1_ceey),qd=as.integer(b$q_act_c1),ing=as.numeric(b$ingc_pc))
# Cohorte y ponderador acordados. Cada indicador usa solo las variables que necesita.
# No se exige UPM, estrato, ingreso ni otra variable para calcular la movilidad.
# No hay umbrales de observaciones municipales.
d <- d %>% filter(edad %in% 25:34,is.finite(w),w>0,!is.na(cvegeo))
qdata <- d %>% filter(qo %in% 1:5,qd %in% 1:5)
pdata <- d %>% filter(is.finite(ro),is.finite(rd))
stopifnot(all(pdata$ro>=0 & pdata$ro<=100),all(pdata$rd>=0 & pdata$rd<=100),
  all(is.finite(d$ing[!is.na(d$ing)])),all(d$ing[!is.na(d$ing)]>=0))
qstats <- qdata %>% group_by(cvegeo) %>% summarise(
  asc_pct=100*weighted_safe(as.numeric(qd>qo),w),
  des_pct=100*weighted_safe(as.numeric(qd<qo),w),
  per_pct=100*weighted_safe(as.numeric(qd==qo),w),
  sal_q1=weighted_safe(as.numeric(qd[qo==1]>1),w[qo==1]),.groups="drop")
pstats <- pdata %>% group_by(cvegeo) %>% summarise(
  cam_pct=weighted_safe(rd-ro,w),mov_abs=weighted_safe(abs(rd-ro),w),.groups="drop")
# Ingreso: todos los individuos de la cohorte con ingreso disponible, aunque falten
# sus quintiles o percentiles. ingc_pc ya viene imputado por la fuente.
income <- d %>% group_by(cvegeo) %>% summarise(ing_pc=weighted_safe(ing,w),.groups="drop")
mobility <- full_join(pstats,qstats,by="cvegeo") %>% full_join(income,by="cvegeo")
stopifnot(!anyDuplicated(mobility$cvegeo))

# 3. ECI: especificacion base de 2023, con mayor precision que el archivo por rama.
ice <- read_csv(ice_path,col_types=cols(cve_mun=col_character()),show_col_types=FALSE) %>%
  filter(anio==2023,especificacion=="base")
stopifnot(!anyDuplicated(ice$cve_mun))
ec <- read_csv(ec_path,col_types=cols(clave_municipio=col_character(),rama=col_character()),show_col_types=FALSE)
stopifnot(all(ec[["año"]]==2023),!anyDuplicated(ec[c("clave_municipio","rama")]))
pci <- ec %>% distinct(rama,pci)
stopifnot(!anyDuplicated(pci$rama),all(is.finite(pci$pci)))
comparison <- ec %>% distinct(clave_municipio,eci) %>% inner_join(ice,by=c("clave_municipio"="cve_mun"))
stopifnot(nrow(comparison)==nrow(ice),all(abs(comparison$eci-comparison$ice)<0.00001))

# 4. UE: solo registros Rama de cuatro digitos; excluye clases y agregados estatales.
s <- read_csv(saic_path,skip=4,col_types=cols(.default=col_character()),
              name_repair="minimal",show_col_types=FALSE)
s <- s[,1:6]
branches <- s %>% filter(`Año Censal`=="2023",!is.na(Municipio),
  grepl("^Rama [0-9]{4} ",`Actividad económica`)) %>% transmute(
  cvegeo=paste0(substr(Entidad,1,2),substr(Municipio,1,3)),
  rama=substr(`Actividad económica`,6,9),
  nombre_rama=sub("^Rama [0-9]{4} ","",`Actividad económica`),
  ue=suppressWarnings(as.numeric(`UE Unidades económicas`)))
stopifnot(!anyDuplicated(branches[c("cvegeo","rama")]),all(grepl("^[0-9]{5}$",branches$cvegeo)),
  all(is.finite(branches$ue)),all(branches$ue>=0),all(branches$ue==floor(branches$ue)))
totals <- branches %>% group_by(cvegeo) %>% summarise(ue_2023=sum(ue),.groups="drop")
present <- branches %>% filter(ue>0) %>% left_join(pci,by="rama")
availability <- present %>% group_by(cvegeo) %>% summarise(
  ramas_presentes=n(),pci_faltantes=sum(!is.finite(pci)),.groups="drop")
# La complejidad se ordena por PCI, no por UE, RCA, mcp ni ECI.
# Ante un empate exacto, desempata el codigo SCIAN ascendente (regla determinista).
selected <- present %>% filter(is.finite(pci)) %>% group_by(cvegeo) %>%
  arrange(desc(pci),rama,.by_group=TRUE) %>% slice_head(n=5) %>%
  mutate(orden=row_number()) %>% ungroup()
# Las ramas sin PCI quedan fuera del ordenamiento. Se eligen hasta cinco de las
# restantes, segun la decision expresa del usuario. Si no queda ninguna, NA.
top <- selected %>% group_by(cvegeo) %>% summarise(
  ue_top5=sum(ue),.groups="drop")
economy <- totals %>% left_join(top,by="cvegeo") %>%
  full_join(ice %>% transmute(cvegeo=cve_mun,eci_2023=ice),by="cvegeo") %>%
  mutate(pct_top5=ifelse(ue_2023>0,100*ue_top5/ue_2023,NA_real_))
stopifnot(all(economy$ue_top5<=economy$ue_2023,na.rm=TRUE))

# 5. Area en km2 calculada en Albers equivalente sobre GRS80. La geometria de salida
# conserva el CRS LCC original. Se usa una proyeccion equivalente para evitar
# interpretar directamente el area de una proyeccion conforme como area real.
equal_area <- "+proj=aea +lat_1=17.5 +lat_2=29.5 +lat_0=12 +lon_0=-102 +x_0=2500000 +y_0=0 +ellps=GRS80 +units=m +type=crs"
g$area_km2 <- as.numeric(st_area(st_transform(g,equal_area)))/1e6
stopifnot(all(is.finite(g$area_km2)),all(g$area_km2>0))
result <- g %>% left_join(mobility,by=c("CVEGEO"="cvegeo")) %>%
  left_join(economy,by=c("CVEGEO"="cvegeo")) %>% mutate(den_top5=ue_top5/area_km2) %>%
  select(CVEGEO,CVE_ENT,CVE_MUN,NOMGEO,cam_pct,asc_pct,des_pct,per_pct,mov_abs,sal_q1,
         ing_pc,eci_2023,ue_2023,ue_top5,pct_top5,den_top5,area_km2)

# 6. Comprobaciones de consistencia antes y despues de escribir.
stopifnot(nrow(result)==original_n,identical(result$CVEGEO,g$CVEGEO),
  st_crs(result)==original_crs,identical(st_as_binary(st_geometry(result)),original_geom),
  all(abs(result$asc_pct+result$des_pct+result$per_pct-100)<1e-8,na.rm=TRUE),
  all(result$sal_q1>=0 & result$sal_q1<=1,na.rm=TRUE),
  all(result$mov_abs>=abs(result$cam_pct)-1e-8,na.rm=TRUE))
numeric_names <- names(st_drop_geometry(result))[vapply(st_drop_geometry(result),is.numeric,logical(1))]
stopifnot(all(vapply(st_drop_geometry(result)[numeric_names],function(x)all(is.finite(x)|is.na(x)),logical(1))),
  all(nchar(names(st_drop_geometry(result)))<=10))
st_write(result,shp_path,driver="ESRI Shapefile",layer_options="ENCODING=UTF-8",quiet=TRUE)
save_table(st_drop_geometry(result),file.path(clean,paste0(stem,".csv")))
saveRDS(result,file.path(clean,paste0(stem,".rds")))
back <- st_read(shp_path,quiet=TRUE,stringsAsFactors=FALSE)
stopifnot(nrow(back)==original_n,identical(names(back),names(result)),
  identical(back$CVEGEO,result$CVEGEO),st_crs(back)==original_crs,
  identical(st_as_binary(st_geometry(back)),original_geom))
for(v in numeric_names) {
  stopifnot(identical(is.na(back[[v]]),is.na(result[[v]])),
    isTRUE(all.equal(back[[v]],result[[v]],tolerance=1e-10,check.attributes=FALSE)))
}

# 7. Trazabilidad fuera de la tabla para GeoDa: definiciones, fuentes y top por rama.
save_table(selected %>% select(cvegeo,orden,rama,nombre_rama,pci,ue),
           file.path(docs,"detalle_top5_ramas_2023.csv"))
save_table(present %>% filter(!is.finite(pci)),file.path(docs,"ramas_sin_pci_2023.csv"))
diff_totals <- totals %>% full_join(ice %>% transmute(cvegeo=cve_mun,ue_total_ice=ue_total),by="cvegeo") %>%
  filter(is.na(ue_2023)|is.na(ue_total_ice)|abs(ue_2023-ue_total_ice)>1e-8)
save_table(diff_totals,file.path(docs,"diferencias_totales_ue_fuentes.csv"))
unmatched <- bind_rows(
  mobility %>% select(cvegeo) %>% mutate(fuente="movilidad_IRE"),
  economy %>% select(cvegeo) %>% mutate(fuente="SAIC_2023")) %>%
  anti_join(st_drop_geometry(g) %>% transmute(cvegeo=CVEGEO),by="cvegeo")
save_table(unmatched,file.path(docs,"claves_sin_geometria.csv"))
fields <- data.frame(
  campo=c("CVEGEO","CVE_ENT","CVE_MUN","NOMGEO","cam_pct","asc_pct","des_pct","per_pct","mov_abs","sal_q1","ing_pc","eci_2023","ue_2023","ue_top5","pct_top5","den_top5","area_km2"),
  descripcion=c("Clave municipal completa: entidad (2) + municipio (3)","Clave de entidad federativa","Clave municipal dentro de la entidad","Nombre municipal original",
    "Cambio promedio ponderado: percentil de destino menos percentil de origen","Porcentaje ponderado que asciende de quintil","Porcentaje ponderado que desciende de quintil","Porcentaje ponderado que permanece en el mismo quintil",
    "Promedio ponderado del valor absoluto del cambio de percentil","Probabilidad ponderada de salir del quintil 1, condicionado a origen en quintil 1",
    "Promedio ponderado del ingreso per capita del hogar imputado por la fuente (ingc_pc)",
    "ECI municipal 2023: ice, especificacion base","Unidades economicas 2023: suma exclusiva de registros Rama municipales del SAIC",
    "UE en hasta cinco ramas presentes con mayor PCI disponible; las ramas sin PCI se excluyen del ordenamiento",
    "100 * ue_top5 / ue_2023","ue_top5 / area_km2","Superficie municipal calculada en proyeccion Albers equivalente, GRS80"),
  unidad=c("Texto de 5 digitos","Texto de 2 digitos","Texto de 3 digitos","Texto","Puntos percentiles (-100 a 100)","Porcentaje (0 a 100)","Porcentaje (0 a 100)","Porcentaje (0 a 100)","Puntos percentiles (0 a 100)","Probabilidad (0 a 1)","Pesos por persona del hogar (variable ingc_pc de la fuente)","Indice estandarizado","Unidades economicas","Unidades economicas","Porcentaje (0 a 100)","Unidades economicas por km2","km2"))
save_table(fields,file.path(docs,"diccionario_base_municipal.csv"))
input_paths <- c(ire_path,ice_path,ec_path,saic_path,file.path(raw,paste0("00mun",c(".shp",".shx",".dbf",".prj",".cpg"))))
save_table(data.frame(archivo=input_paths,md5=unname(tools::md5sum(input_paths))),file.path(docs,"fuentes_y_huellas.csv"))
capture.output(sessionInfo(),file=file.path(docs,"sessionInfo_base_municipal.txt"))
check <- data.frame(campo=names(st_drop_geometry(result)),con_dato=vapply(st_drop_geometry(result),function(x)sum(!is.na(x)),integer(1)),
                    faltantes=vapply(st_drop_geometry(result),function(x)sum(is.na(x)),integer(1)))
save_table(check,file.path(docs,"validacion_campos.csv"))
cat("Base preparada y verificada:",shp_path,"\nMunicipios:",nrow(result),"\n")
print(check,row.names=FALSE)
cat("Municipios con ramas de PCI faltante:",sum(availability$pci_faltantes>0),"\n")
cat("Municipios con menos de cinco ramas:",sum(availability$ramas_presentes<5),"\n")
