********************************************************************************
***				  INFORME DE MOVILIDAD SOCIAL EN MÉXICO 2025 				 ***
***				  CENTRO DE ESTUDIOS ESPINOSA YGLESIAS (CEEY)				 ***
********************************************************************************

version 15.1     
clear all             

/* IMPORTANTE: 

	
 Esta rutina fue escrita a partir de la versión 15 de Stata, es posible que el 
 código no pueda ejecutarse de manera correcta en versiones anteriores del software.

 Los cálculos presentados corresponden al capítulo 2 y 3 del informe, para ello
 se utilizan los siguientes archivos:
	1) entrevistado_2023.dta
	2) ingreso_2017.dta
	3) ESRU-EMOVI 2017 Entrevistado.dta
 Es importante señalar que este último archivo también se encuentra disponible
 en la página del CEEY en https://ceey.org.mx/contenido/que-hacemos/emovi-pre/
 
 Cualquier duda, puede escribir a encuesta@ceey.org.mx

 Este programa utiliza dos directorios de trabajo, los cuales se ubican en las 
 siguientes carpetas:
	1) Bases originales (data): "C:\Informe de MS\Bases de datos"
	2) Bases finales (bases): "C:\Informe de MS\Bases finales"

	
 Para poder ejecutar correctamente, es necesario cambiar estas ubicaciones a 
 partir de los siguientes globals (gl)*/

 global data17 = "C:\Users\RocioEspinosa\Mi unidad\CEEY\Encuestas CEEY\EMOVI 17\Bases\Finales"
 global data23 = "C:\Users\RocioEspinosa\Mi unidad\CEEY_ESRU-EMOVI 2023\8. Información para publicar\Bases de datos\Data"
 global bases = "C:\Users\RocioEspinosa\Mi unidad\CEEY_ESRU-EMOVI 2023\8. Información para publicar\Bases de datos\Bases"


********************************************************************************
************************** INFORMACIÓN PARA 2017 *******************************
********************************************************************************

*** Variable de ingreso imputado (ver Torres, Monroy-Gómez-Franco y Vélez-Grajales, 2025) 
use  "$data17\ESRU-EMOVI 2017 Entrevistado.dta", clear 
merge 1:1 folio using "$data17\ingreso_2017.dta"
drop _merge
label var ingc_pc "Ingreso per cápita del hogar - imputado"


********************** Generación variables para analisis **********************
rename p23 edo_or
gen region_14=.
rename p05 edad_ent


gen sex_ent=1 if p06==2
replace sex_ent=0 if p06==1


gen niveduc2=1 if p13==97 | p13==1 | p13==2
replace niveduc2=2 if p13==3 | p13==4
replace niveduc2=3 if p13==5 | p13==6 | p13==7 | p13==9
replace niveduc2=4 if p13==8 | p13==10 | p13==11 | p13==12
label value niveduc2 niveduc2


* Regiones de origen (a los 14 años de edad del entrevistado)
* Región 1: Norte
replace region_14=1 if edo_or==2 | edo_or==5 | edo_or==8 | edo_or==19 ///
| edo_or==26 | edo_or==28

* Región 2: Norte-occidente
replace region_14=2 if edo_or==3 | edo_or==10 | edo_or==18 | edo_or==25 /// 
| edo_or==32

* Región 3: Centro-norte
replace region_14=3 if edo_or==1 | edo_or==6 | edo_or==14 | edo_or==16 /// 
| edo_or==24

* Región 4: Centro
replace region_14=4 if edo_or==11 | edo_or==13 | edo_or==15 /// 
| edo_or==17 | edo_or==21 | edo_or==22 | edo_or==29 | edo_or==9

* Región 5: Sur
replace region_14=5 if edo_or==4 | edo_or==7 | edo_or==12 | edo_or==20 /// 
| edo_or==23 | edo_or==27 | edo_or==30 | edo_or==31
label var region_14 "Región de origen"

* Condición rural/urbano
gen urbano_o=1 if p24<5
replace urbano_o=0 if urbano_o==.

* Cohortes de edad
gen cohorte=1 if edad_ent>=25 & edad_ent<35
replace cohorte=2 if edad_ent>=35 & edad_ent<45
replace cohorte=3 if edad_ent>=45 & edad_ent<55
replace cohorte=4 if edad_ent>=55 & edad_ent<65

*** Nivel educativo concluido del entrevistado ***
* Sin estudios
gen educ=.
replace educ=1 if p13==97
replace educ=1 if p13==1

* Primaria incompleta
replace educ=2 if p13==2 & (p14>=1 & p14<=5)

* Primaria completa
replace educ=3 if p13==2 & p14==6
replace educ=3 if p13==3 & (p14>=1 & p14<=2)
replace educ=3 if p13==4 & (p14>=1 & p14<=2)

* Secundaria
replace educ=4 if p13==3 & (p14>=3 & p14!=.)
replace educ=4 if p13==4 & (p14>=3 & p14!=.)
replace educ=4 if p13==5 & (p14>=1 & p14<=2)
replace educ=4 if p13==6 & (p14>=1 & p14<=2)
replace educ=4 if p13==7 & (p14>=1 & p14<=2)
replace educ=4 if p13==9 & (p14>=1 & p14<=2)

* Prepatatoria
replace educ=5 if p13==5 & (p14>=3 & p14!=.)
replace educ=5 if p13==6 & (p14>=3 & p14!=.)
replace educ=5 if p13==7 & (p14>=3 & p14!=.)
replace educ=5 if p13==8 & (p14>=1 & p14<=2)
replace educ=5 if p13==9 & (p14>=3 & p14!=.)
replace educ=5 if p13==10 & (p14>=1 & p14<=3)
replace educ=5 if p13==11 & (p14>=1 & p14<=3)

* Profesional
replace educ=6 if p13==8 & (p14>=3 & p14!=.)
replace educ=6 if p13==10 & (p14>=4 & p14!=.)
replace educ=6 if p13==11 & (p14>=4 & p14!=.)
replace educ=6 if p13==12

*** Nivel educativo concluido del padre ***
gen educ_padre=.
replace educ_padre=1 if p42==2
replace educ_padre=1 if p43==1

replace educ_padre=2 if p43==2 & (p44>=1 & p44<=5)

replace educ_padre=3 if p43==2 & p44==6
replace educ_padre=3 if p43==3 & (p44>=1 & p44<=2)
replace educ_padre=3 if p43==4 & (p44>=1 & p44<=2)

replace educ_padre=4 if p43==3 & (p44>=3 & p44!=.)
replace educ_padre=4 if p43==4 & (p44>=3 & p44!=.)
replace educ_padre=4 if p43==5 & (p44>=1 & p44<=2)
replace educ_padre=4 if p43==6 & (p44>=1 & p44<=2)
replace educ_padre=4 if p43==7 & (p44>=1 & p44<=2)
replace educ_padre=4 if p43==9 & (p44>=1 & p44<=2)

replace educ_padre=5 if p43==5 & (p44>=3 & p44!=.)
replace educ_padre=5 if p43==6 & (p44>=3 & p44!=.)
replace educ_padre=5 if p43==7 & (p44>=3 & p44!=.)
replace educ_padre=5 if p43==8 & (p44>=1 & p44<=2)
replace educ_padre=5 if p43==9 & (p44>=3 & p44!=.)
replace educ_padre=5 if p43==10 & (p44>=1 & p44<=3)
replace educ_padre=5 if p43==11 & (p44>=1 & p44<=3)

replace educ_padre=6 if p43==8 & (p44>=3 & p44!=.)
replace educ_padre=6 if p43==10 & (p44>=4 & p44!=.)
replace educ_padre=6 if p43==11 & (p44>=4 & p44!=.)
replace educ_padre=6 if p43==12

*** Nivel educativo concluido de la madre ***
gen educ_madre=.

replace educ_madre=1 if p42m==2
replace educ_madre=1 if p43m==1

replace educ_madre=2 if p43m==2 & (p44m>=1 & p44m<=5)

replace educ_madre=3 if p43m==2 & p44m==6
replace educ_madre=3 if p43m==3 & (p44m>=1 & p44m<=2)
replace educ_madre=3 if p43m==4 & (p44m>=1 & p44m<=2)

replace educ_madre=4 if p43m==3 & (p44m>=3 & p44m!=.)
replace educ_madre=4 if p43m==4 & (p44m>=3 & p44m!=.)
replace educ_madre=4 if p43m==5 & (p44m>=1 & p44m<=2)
replace educ_madre=4 if p43m==6 & (p44m>=1 & p44m<=2)
replace educ_madre=4 if p43m==7 & (p44m>=1 & p44m<=2)
replace educ_madre=4 if p43m==9 & (p44m>=1 & p44m<=2)

replace educ_madre=5 if p43m==5 & (p44m>=3 & p44m!=.)
replace educ_madre=5 if p43m==6 & (p44m>=3 & p44m!=.)
replace educ_madre=5 if p43m==7 & (p44m>=3 & p44m!=.)
replace educ_madre=5 if p43m==8 & (p44m>=1 & p44m<=2)
replace educ_madre=5 if p43m==9 & (p44m>=3 & p44m!=.)
replace educ_madre=5 if p43m==10 & (p44m>=1 & p44m<=3)
replace educ_madre=5 if p43m==11 & (p44m>=1 & p44m<=3)

replace educ_madre=6 if p43m==8 & (p44m>=3 & p44m!=.)
replace educ_madre=6 if p43m==10 & (p44m>=4 & p44m!=.)
replace educ_madre=6 if p43m==11 & (p44m>=4 & p44m!=.)
replace educ_madre=6 if p43m==12

label var educ "Nivel educativo del entrevistado"
label var educ_padre "Nivel educativo del padre del entrevistado"
label var educ_madre "Nivel educativo de la madre del entrevistado"

label define educ 1 "Sin estudios" 2 "Primaria incompleta" 3 "Primaria" 4 "Secundaria" 5 "Preparatoria" 6 "Profesional"
label value educ educ_padre educ_madre educ

* Clasificación agrupada de educación del entrevistado
gen educ_2=.
replace educ_2=1 if educ==1 | educ==2 | educ==3
replace educ_2=2 if educ==4
replace educ_2=3 if educ==5
replace educ_2=4 if educ==6
label var educ_2 "Segunda clasificación de educación del entrevistado, grados completos"

* Clasificación agrupada de educación de los padres
gen educ_padre_2=.
replace educ_padre_2=1 if educ_padre==1 | educ_padre==2 | educ_padre==3
replace educ_padre_2=2 if educ_padre==4
replace educ_padre_2=3 if educ_padre==5
replace educ_padre_2=4 if educ_padre==6

gen educ_madre_2=.
replace educ_madre_2=1 if educ_madre==1 | educ_madre==2 | educ_madre==3
replace educ_madre_2=2 if educ_madre==4
replace educ_madre_2=3 if educ_madre==5
replace educ_madre_2=4 if educ_madre==6

label var educ_padre_2 "Segunda clasificación de educación del padre, grados completos"
label var educ_padre_2 "Segunda clasificación de educación de la madre,  grados completos"

label define educ_2 1 "A lo más primaria" 2 "Secundaria" 3 "Preparatoria" 4 "Profesional"
label value educ_2 educ_padre_2 educ_madre_2 educ_2

* Máximo nivel educativo concluido de los padres
egen niveducpad=rowmax(educ_padre_2 educ_madre_2)
replace niveducpad=educ_madre_2 if educ_padre_2==. & educ_madre_2!=.
replace niveducpad=educ_padre_2 if educ_madre_2==. & educ_padre_2!=.
replace niveducpad=. if educ_madre_2==. & educ_padre_2==.
label value niveducpad educ_2


************** GENERACIÓN DEL ÍNDICE DE RECURSOS ECONÓMICOS ********************

****** HOGAR ACTUAL *******

* Recodificamos los preguntas de los activos y servicios del hogar para poder 
* estimar el índice mediante MCA (Análisis de Correspondencias Múltiples)

* Activos del hogar
gen ac1  = cond(p126o==1, 1, cond(p126o==2, 0, .))  // Computadora
gen ac2  = cond(p125d==1, 1, cond(p125d==2, 0, .))  // Boiler
gen ac3  = cond(p126b==1, 1, cond(p126b==2, 0, .))  // Lavadora
gen ac4  = cond(p126m==1, 1, cond(p126m==2, 0, .))  // Internet
gen ac5  = cond(p125a==1, 1, cond(p125a==2, 0, .))  // Agua entubada
gen ac6  = cond(p131==., ., cond(p131>=1, 1, 0))    // Automóvil
gen ac7  = cond(p126j==1, 1, cond(p126j==2, 0, .))  // Televisión de cable
gen ac8  = cond(p126d==1, 1, cond(p126d==2, 0, .))  // Horno microondas
gen ac9  = cond(inlist(1, p128b, p128c), 1, cond(p128b==2 & p128c==2, 0, .))  // Cuenta de cheques
gen ac10 = cond(p126a==1, 1, cond(p126a==2, 0, .))  // Estufa
gen ac11 = cond(p126r==1, 1, cond(p126r==2, 0, .))  // Vehículo trabajo
gen ac12 = cond(p125e==1, 1, cond(p125e==2, 0, .))  // Servicio doméstico
gen ac13 = cond(inlist(1, p128d, p128e), 1, cond(p128d==2 & p128e==2, 0, .))  // Tarjeta de crédito
gen ac14 = cond(p129a==1, 1, cond(p129a==2, 0, .))  // Otra casa
gen ac15 = cond(p129b==1, 1, cond(p129b==2, 0, .))  // Local comercial
gen ac16 = cond(p129e==1, 1, cond(p129e==2, 0, .))  // Terreno o campo

* Hacinamiento
gen hacina = tamhog / p121
gen hac = cond(hacina <= 2.5, 1, 0)

*** INDICE DE RECURSOS ECONOMICOS DEL HOGAR ACTUAL ***
*** Lista de activos utilizados ***
/*ac1: Computadora
ac2: Boiler
ac3: Lavadora
ac4: Internet
ac5: Agua entubada
ac6: Automóvil
ac7: Televisión de cable
ac8: Horno de microondas 
ac9: Cuenta de cheques
ac10: Estufa
ac11: Vehículo de trabajo (tractor o maquinaria agrícola)
ac12: Servicio doméstico
ac13: Tarjeta de crédito
ac14: Otra casa
ac15: Local para uso comercial
ac16: Terreno o campo
hac: Hacinamiento*/

* Loop por cada cohorte (Cohorte 1: Entre 25 y 34 años, Cohorte 2: Entre 35 y 44 años, Cohorte 3: Entre 45 y 54 años, Cohorte 4: Entre 55 y 64 años)
forvalues i = 1/4 {
	mca ac1 ac2 ac3 ac4 ac5 ac6 ac7 ac8 ac9 ac10 ac11 ac12 ac13 ac14 ac15 ac16 hac [fw=factor] if cohorte==`i', method(burt)
	predict i_actrec`i' if e(sample)
	replace i_actrec`i'=i_actrec`i'*(-1)
	summ i_actrec`i'
	gen ireccomp_act`i'=i_actrec`i'
}

* Consolidar índice general, los quintiles y los percentiles para toda la población
gen ireccomp_act=ireccomp_act1 if cohorte==1
replace ireccomp_act=ireccomp_act2 if cohorte==2
replace ireccomp_act=ireccomp_act3 if cohorte==3
replace ireccomp_act=ireccomp_act4 if cohorte==4


****** HOGAR DE ORIGEN *******

* Activos y servicios del hogar de origen
gen ac_or1  = cond(p33_a==1, 1, cond(p33_a==2, 0, cond(p33_a==8, ., .)))   // Estufa
gen ac_or2  = cond(p34_a==1, 1, cond(p34_a==2, 0, cond(p34_a==8, ., .)))   // Otra vivienda
gen ac_or3  = cond(p33_b==1, 1, cond(p33_b==2, 0, cond(p33_b==8, ., .)))   // Lavadora
gen ac_or4  = cond(p33_h==1, 1, cond(p33_h==2, 0, cond(p33_h==8, ., .)))   // TV de cable
gen ac_or5  = cond(p33_c==1, 1, cond(p33_c==2, 0, cond(p33_c==8, ., .)))   // Refrigerador
gen ac_or6  = cond(p30_a==1, 1, cond(p30_a==2, 0, cond(p30_a==8, ., .)))   // Agua entubada
gen ac_or7  = cond(p33_e==1, 1, cond(p33_e==2, 0, cond(p33_e==8, ., .)))   // Televisión
gen ac_or8  = cond(p33_d==1, 1, cond(p33_d==2, 0, cond(p33_d==8, ., .)))   // Línea telefónica
gen ac_or9  = cond(p33_k==1, 1, cond(p33_k==2, 0, cond(p33_k==8, ., .)))   // Computadora
gen ac_or10 = cond(p30_b==1, 1, cond(p30_b==2, 0, cond(p30_b==9, ., .)))   // Electricidad
gen ac_or11 = cond(p33_n==1, 1, cond(p33_n==2, 0, cond(p33_n==8, ., .)))   // VHS/DVD
gen ac_or12 = cond(p33_i==1, 1, cond(p33_i==2, 0, cond(p33_i==8, ., .)))   // Microondas
gen ac_or13 = cond(p34_b==1, 1, cond(p34_b==2, 0, cond(p34_b==9, ., .)))   // Local comercial
gen ac_or14 = cond(p33_g==1, 1, cond(p33_g==2, 0, cond(p33_g==8, ., .)))   // Aspiradora
gen ac_or15 = cond(p34_e==1, 1, cond(p34_e==2, 0, cond(p34_e==8, ., .)))   // Automóvil
gen ac_or16 = cond(p30_d==1, 1, cond(p30_d==2, 0, cond(p30_d==8, ., .)))   // Boiler

*Cuenta bancaria
gen ac_or17=1 if p32_a==1 | p32_b==1
replace ac_or17=0 if (p32_a==2 & p32_b==2) |  (p32_a==2 & p32_b==8) |(p32_a==8 & p32_b==2) 
replace ac_or17=. if p32_a==8 & p32_b==8

*Tarjeta de credito
gen ac_or18=1 if p32_c==1 | p32_d==1
replace ac_or18=0 if (p32_c==2 & p32_d==2) | (p32_c==2 & p32_d==8) | (p32_c==8 & p32_d==2)
replace ac_or18=. if p32_c==8 & p32_d==8

*Servicio domestico
gen ac_or19=1 if p30_e==1
replace ac_or19=0 if p30_e==2
replace ac_or19=. if p30_e==8

*Hacinamiento, hogar de origen
gen har=p27/p28_1  
gen hac_or=1 if har<=2.5
replace hac_or=0 if har>2.5

*** INDICE DE RECURSOS ECONOMICOS DEL HOGAR DE ORIGEN ***
*** Lista de activos utilizados ***
/*ac_or1: Estufa
ac_or2: Otra vivienda
ac_or3: Lavadora
ac_or4: Televisión de cable
ac_or5: Refrigerador
ac_or6: Agua entubada
ac_or7: Televisión
ac_or8: Línea telefónica
ac_or9: Computadora
ac_or10: Electricidad
ac_or11: VHS/DVD 
ac_or12: Microondas
ac_or13: Local comercial
ac_or14: Aspiradora
ac_or15: Automóvil
ac_or16: Boiler
ac_or17: Cuenta bancario
ac_or18: Tarjeta de crédito
ac_or19: Servicio doméstico
hac_or: Hacinamiento*/

* Loop por cada cohorte (Cohorte 1: Entre 25 y 34 años, Cohorte 2: Entre 35 y 44 años, 
* Cohorte 3: Entre 45 y 54 años, Cohorte 4: Entre 55 y 64 años)
forvalues i = 1/4 {
	mca ac_or1-ac_or19 hac_or [fw=factor] if cohorte==`i', method(burt)
	predict i_orrec`i' if e(sample)
	replace i_orrec`i'=i_orrec`i'*(-1)
	summ i_orrec`i'
	gen ireccomp_or`i'=i_orrec`i'
}

* Consolidar índice general, quintiles y percentile para toda la población
gen ireccomp_or=ireccomp_or1 if cohorte==1
replace ireccomp_or=ireccomp_or2 if cohorte==2
replace ireccomp_or=ireccomp_or3 if cohorte==3
replace ireccomp_or=ireccomp_or4 if cohorte==4

* Limpiamos la base de valores faltante en el índice de origen
drop  if ireccomp_or==.

*Creamos los quintiles 

xtile quintilecomp_or=ireccomp_or [pw=factor] , nq(5)
xtile quintilecomp_act=ireccomp_act [pw=factor] , nq(5)


* Se etiquetan las variables generadas
label var ireccomp_or "Índice de recursos económicos COMPARABLE - hogar de origen"
label var quintilecomp_or "Quintil de recursos económicos COMPARABLE - hogar de origen"
label var ireccomp_act "Índice de recursos económicos COMPARABLE - hogar actual"
label var quintilecomp_act "Quintil de recursos económicos COMPARABLE - hogar actual"

* Limpiamos la base de valores faltante en el nivel educativo máximo de los padres
drop if niveducpad==.

gen povline=.
replace povline=2234.15 if rururb==1
replace povline=3191.54 if rururb==0

gen extpovline=. 
replace extpovline=1130.92 if rururb==1
replace extpovline=1491.07 if rururb==0


* Eliminamos variables auxiliares y otras no necesarias para el análisis
drop Estado-recontacto est_dis-tamhog sex_ent-ireccomp_or
gen year=2017


save "$bases\EMOVI2017_comp.dta", replace


********************************************************************************
************************** INFORMACIÓN PARA 2023 *******************************
********************************************************************************

use "$data23\entrevistado_2023.dta", clear 

**Redondeamos el factor de expansión para su uso
gen factor2=round(factor)
label var factor2 "Factores enteros para mca"
rename factor factor_
rename factor2 factor
summ factor*


************** GENERACIÓN DEL ÍNDICE DE RECURSOS ECONÓMICOS ********************

****** HOGAR ACTUAL *******

*** Lista de activos ***
/*hac: hacinamiento
auto: automovil
p94a: sala y/o comedor 
p94b: jardin
p94d: patio
p94e: cuarto de televisión o estudio
p94f: cochera o cajón de estacionamiento
p95a: agua entubada 
p95d: calentador de agua (boiler, solar)
p95e: servicio doméstico (personas que reciben un pago por limpiar, lavar, planchar, jardinero, chofer particular)
p96a: estufa de gas o eléctrica
p96b: lavadora de ropa
p96c: refrigerador
p96d: horno de microondas 
p96i: televisión de paga (TV por cable, Netflix, etc.) 
p96j: línea telefónica fija
p96l: conexión a internet 
p96n: computadora 
p96o: maquinaria o equipo agrícola 
p97a: otra vivienda o departamento 
p97d: alguna cuenta bancaria (de débito, ahorro o cheques)
p97g: cuenta o tarjeta de nómina (donde depositan su sueldo)
tipov_ac2_2: casa que comparte terreno con otra(s) */


* Recodificamos los preguntas de los activos y servicios del hogar a variables binarias (1,0)
* para poder estimar el índice mediante MCA (Análisis de Correspondencias Múltiples)

* Activos y espacios de la vivienda
foreach x in a b c d e f g{
recode p94`x' (2=0)
}

* Servicios de la vivienda
foreach x in a b c d e{
recode p95`x' (2=0)
}

* Artículos propiedad del hogar
foreach x in a b c d e f g h i j k l m n o p q r{
recode p96`x' (2=0)
}

* Bienes propiedad del hogar
foreach x in a b c d e f g h i j k l m n{
recode p97`x' (2=0)
}

* Automóvil
gen auto=1 if p99>=1 & p99!=.
replace auto=0 if p99==0

* Material de piso
gen piso=1 if p88==2 | p88==3
replace piso=0 if p88==1

* Tenencia de la vivienda
gen viv_ac=.
replace viv_ac=1 if (p91==3 | p91==4) & p92>=1 & p92<=3
replace viv_ac=0 if (p91==3 | p91==4) & p92==4
replace viv_ac=0 if p91==1 | p91==2 | p91==5 | p91==6

* Tipo de vivienda
gen tipov_ac=p93
recode tipov_ac (1=1) (2=2) (3 4 5 6 7 8 9=3) 
tab tipov_ac, gen (tipov_ac2_)

* Tarjeta de crédito
gen tarjeta=1 if p97e==1
replace tarjeta=1 if p97f==1 & tarjeta==.
replace tarjeta=0 if tarjeta==.

* Ahorro
gen ahorro=.
replace ahorro=1 if p97j==1
replace ahorro=1 if p97k==1 & ahorro==.
replace ahorro=0 if ahorro==.

* Computadora
gen ac1=.
replace ac1=1 if p96n==1
replace ac1=0 if p96n==0

* Boiler
gen ac2=.
replace ac2=1 if p95d==1
replace ac2=0 if p95d==0

* Lavadora
gen ac3=.
replace ac3=1 if p96b==1
replace ac3=0 if p96b==0

* Internet
gen ac4=.
replace ac4=1 if p96l==1
replace ac4=0 if p96l==0

* Agua entubada
gen ac5=.
replace ac5=1 if p95a==1
replace ac5=0 if p95a==0

* Automóvil
gen ac6=.
replace ac6=1 if p99>=1 & p99!=.
replace ac6=0 if auto==0

*Televisión de cable
gen ac7=.
replace ac7=1 if p96i==1
replace ac7=0 if p96i==0

* Horno de microondas
gen ac8=.
replace ac8=1 if p96d==1
replace ac8=0 if p96d==0

* Cuenta de cheques
gen ac9=.
replace ac9=1 if p97d==1 | p97j==1
replace ac9=0 if p97d==0 & p97j==0

* Estufa
gen ac10=.
replace ac10=1 if p96a==1
replace ac10=0 if p96a==0

* Vehículo de trabajo (tractor o maquinaria agrícola)
gen ac11=.
replace ac11=1 if p96o==1
replace ac11=0 if p96o==0

* Servicio doméstico
gen ac12=.
replace ac12=1 if p95e==1
replace ac12=0 if p95e==0

* Tarjeta de crédito
gen ac13=.
replace ac13=1 if p97e==1 | p97f==1
replace ac13=0 if p97e==0 & p97f==0

* Otra casa
gen ac14=.
replace ac14=1 if p97a==1
replace ac14=0 if p97a==0

* Local para uso comercial
gen ac15=.
replace ac15=1 if p97b==1
replace ac15=0 if p97b==0

* Terreno o campo
gen ac16=.
replace ac16=1 if p97c==1
replace ac16=0 if p97c==0

* Hacinamiento
gen hacina=tamhog/p89 
gen hac=1 if hacina<=2.5
replace hac=0 if hacina>2.5

* Máximo nivel educativo alcanzado de los padres
egen padres_edu=rowmax(educp educm)
replace padres_edu=educm if educp==. & educm!=.
replace padres_edu=educp if educm==. & educp!=.
replace padres_edu=. if educm==. & educp==.
label var padres_edu "Máximo nivel educativo de los padres"


drop if educ==. 
drop if padres_edu==.

drop if region_14==.

**Redondeamos el factor de expansión para su uso
rename factor fac
gen factor2=fac*10
gen factor=round(factor2)
label var factor "Factores enteros para mca"
summ fac*

gen id=1
tab id[aw=fac]
tab id[aw=factor]

** Generamos el índice de recursos económicos para el hogar actual mediante el MCA para cada cohorte
** (Cohorte 1: Entre 25 y 34 años, Cohorte 2: Entre 35 y 44 años, Cohorte 3: Entre 45 y 54 años, Cohorte 4: Entre 55 y 64 años)
mca ac1-ac16 hac [fw=factor] if cohorte==1, method(burt)
predict i_actrec1 if e(sample)
replace i_actrec1=i_actrec1*(-1)
summ i_actrec1
gen ireccomp_act1=i_actrec1

mca ac1-ac16 hac [fw=factor] if cohorte==2, method(burt)
predict i_actrec2 if e(sample)
replace i_actrec2=i_actrec2*(-1)
summ i_actrec2
gen ireccomp_act2=i_actrec2

mca ac1-ac16 hac [fw=factor] if cohorte==3, method(burt)
predict i_actrec3 if e(sample)
replace i_actrec3=i_actrec3*(-1)
summ i_actrec3
gen ireccomp_act3=i_actrec3

mca ac1-ac16 hac [fw=factor] if cohorte==4, method(burt)
predict i_actrec4 if e(sample)
replace i_actrec4=i_actrec4*(-1)
summ i_actrec4
gen ireccomp_act4=i_actrec4


* Consolidar índice general para toda la población
gen ireccomp_act=ireccomp_act1 if cohorte==1
replace ireccomp_act=ireccomp_act2 if cohorte==2
replace ireccomp_act=ireccomp_act3 if cohorte==3
replace ireccomp_act=ireccomp_act4 if cohorte==4


****** HOGAR DE ORIGEN *******

*** Lista de activos utilizados ***
*hac_or: hacinamiento
*auto_or: automovil 
*p26a: agua entubada dentro de la vivienda 
*p26b: electricidad 
*p26c: baño dentro de la vivienda
*p26d: calentador de agua 
*p26e: servicio doméstico (personas que reciben un pago por limpiar, lavar, planchar, jardinero, chofer particular)
*p29a: sala y/o comedor 
*p29b: jardín
*p29f: cochera o cajón de estacionamiento 
*p29g: cuarto separado para cocinar 
*p31a: estufa de gas o eléctrica 
*p31b: lavadora de ropa 
*p31c: refrigerador 
*p31d: teléfono fijo 
*p31e: televisor 
*p31g: aspiradora 
*p31h: televisión por cable 
*p31i: horno de microondas 
*p31k: computadora, laptop o tablet 
*p31m: videocasetera o reproductor de DVD 
*p31o: bicicleta y/o triciclo para transportarse
*p32a: otra vivienda o departamento (diferente a la casa en la que vivían)
*p32b: un local comercial 
*p32e: alguna cuenta de ahorro (bancaria o de una caja popular) 
*tarjeta_or: tarjeta de crédito bancaria o departamental 
*ahorro_or: cuenta de cheques o depósitos a plazo fijo 
*tipov_or2_3: casa diferente a única en terreno o que comparte terreno con otra


* Recodificamos los preguntas de los activos y servicios del hogar a variables binarias (1,0)
* para poder estimar el índice mediante MCA (Análisis de Correspondencias Múltiples)

* Servicios y espacios de la vivienda
foreach x in a b c d e{
recode p26`x' (2=0) (8=.)
}

foreach x in a b c d e f g{
recode p29`x' (2=0) (8=.)
}

* Artículos propiedad del hogar 
foreach x in a b c d e f g h i j k l m n o {
recode p31`x' (2=0) (8=.)
}

* Bienes propiedad del hogar
foreach x in a b c d e f g h i j k l m n o{
recode p32`x' (2=0) (8=.)
}

* Material de piso
gen piso_or=p25
recode piso_or (2 3=1) (1=0)

* Automóvil
gen auto_or=1 if p30>=1 & p30!=.
replace auto_or=0 if p30==0

* Tenencia de la vivienda
gen viv_or=.
replace viv_or=1 if p27==3
replace viv_or=0 if p27!=3 & p27!=.

* Tipo de vivienda
gen tipov_or=p28
recode tipov_or (1=1) (2=2) (3 4 5 6 7 8 9=3) 
tab tipov_or, gen(tipov_or2_) 

* Hacinamiento
gen hacina_or=p22/p23
gen hac_or=1 if hacina_or<=2.5
replace hac_or=0 if hacina_or>2.5

* Tarjeta de crédito
gen tarjeta_or=.
replace tarjeta_or=1 if p32f==1
replace tarjeta_or=1 if p32g==1 & tarjeta_or==.
replace tarjeta_or=0 if tarjeta_or==.

* Ahorro
gen ahorro_or=.
replace ahorro_or=1 if p32k==1
replace ahorro_or=1 if p32l==1 & ahorro_or==.
replace ahorro_or=0 if ahorro_or==.

* Estufa
gen ac_or1=1 if p31a==1
replace ac_or1=0 if p31a==0
replace ac_or1=. if p31a==.

* Otra vivienda
gen ac_or2=1 if p32a==1
replace ac_or2=0 if p32a==0
replace ac_or2=. if p32a==.

* Lavadora 
gen ac_or3=1 if p31b==1
replace ac_or3=0 if p31b==0
replace ac_or3=. if p31b==.

* Televisión de cable
gen ac_or4=1 if p31h==1
replace ac_or4=0 if p31h==0
replace ac_or4=. if p31h==.

* Refrigerador
gen ac_or5=1 if p31c==1
replace ac_or5=0 if p31c==0
replace ac_or5=. if p31c==.

* Agua entubada
gen ac_or6=1 if p26a==1
replace ac_or6=0 if p26a==0
replace ac_or6=. if p26a==8

* Televisión
gen ac_or7=1 if p31e==1
replace ac_or7=0 if p31e==0
replace ac_or7=. if p31e==.

* Línea telefónica
gen ac_or8=1 if p31d==1
replace ac_or8=0 if p31d==0
replace ac_or8=. if p31d==.

* Computadora 
gen ac_or9=1 if p31k==1
replace ac_or9=0 if p31k==0
replace ac_or9=. if p31k==.

* Electricidad
gen ac_or10=1 if p26b==1
replace ac_or10=0 if p26b==0
replace ac_or10=. if p26b==.

* VHS/DVD (solo para ciertos grupos de edad)
gen ac_or11=1 if p31m==1
replace ac_or11=0 if p31m==0
replace ac_or11=. if p31m==.

* Microondas (solo para ciertos grupos de edad)
gen ac_or12=1 if p31i==1
replace ac_or12=0 if p31i==0
replace ac_or12=. if p31i==.

* Local comercial
gen ac_or13=1 if p32b==1
replace ac_or13=0 if p32b==0
replace ac_or13=. if p32b==.

* Aspiradora
gen ac_or14=1 if p31g==1
replace ac_or14=0 if p31g==0
replace ac_or14=. if p31g==.

* Automóvil
gen ac_or15=1 if auto_or==1
replace ac_or15=0 if auto_or==0
replace ac_or15=0 if auto_or==.

* Boiler
gen ac_or16=1 if p26d==1
replace ac_or16=0 if p26d==0
replace ac_or16=. if p26d==.

* Cuenta bancaria
gen ac_or17=1 if (p32e==1 | ahorro_or==1)
replace ac_or17=0 if p32e==0 & ahorro_or==0 
replace ac_or17=. if p32e==. & ahorro_or==.

* Tarjeta de crédito
gen ac_or18=1 if tarjeta_or==1
replace ac_or18=0 if tarjeta_or==0
replace ac_or18=. if tarjeta_or==.

* Servicio doméstico
gen ac_or19=1 if p26e==1 
replace ac_or19=0 if p26e==0
replace ac_or19=. if p26e==.

** Generamos el índice de recursos económicos para el hogar de origen mediante el MCA para cada cohorte
** (Cohorte 1: Entre 25 y 34 años, Cohorte 2: Entre 35 y 44 años, Cohorte 3: Entre 45 y 54 años, Cohorte 4: Entre 55 y 64 años)
mca ac_or1-ac_or19 hac_or [fw=factor] if cohorte==1, method(burt)
predict i_orrec1 if e(sample)
replace i_orrec1=i_orrec1*(-1)
summ i_orrec1
gen ireccomp_or1=i_orrec1

mca ac_or1-ac_or19 hac_or [fw=factor] if cohorte==2, method(burt)
predict i_orrec2 if e(sample)
replace i_orrec2=i_orrec2*(-1)
summ i_orrec2
gen ireccomp_or2=i_orrec2

mca ac_or1-ac_or19 hac_or [fw=factor] if cohorte==3, method(burt)
predict i_orrec3 if e(sample)
replace i_orrec3=i_orrec3*(-1)
summ i_orrec3
gen ireccomp_or3=i_orrec3

mca ac_or1-ac_or19 hac_or [fw=factor] if cohorte==4, method(burt)
predict i_orrec4 if e(sample)
replace i_orrec4=i_orrec4*(-1)
summ i_orrec4
gen ireccomp_or4=i_orrec4

* Consolidar índice general para toda la población
gen ireccomp_or=ireccomp_or1 if cohorte==1
replace ireccomp_or=ireccomp_or2 if cohorte==2
replace ireccomp_or=ireccomp_or3 if cohorte==3
replace ireccomp_or=ireccomp_or4 if cohorte==4

mdesc ireccomp_or
drop if ireccomp_or==.
drop if ireccomp_act==.

gen year=2023
tostring index, gen(folio)

rename edad edad_ent

*Condición rural/urbano
replace rururb=0 if rururb==1
replace rururb=1 if rururb==2

label define rural 1 "Rural" 0 "Urban"
label value rururb rural

drop  if ireccomp_or==.

*Creamos los quintiles 
xtile quintilecomp_or=ireccomp_or [pw=factor] , nq(5)
xtile quintilecomp_act=ireccomp_act [pw=factor] , nq(5)

* Se etiquetan las variables generadas
label var ireccomp_or "Índice de recursos económicos COMPARABLE - hogar de origen"
label var quintilecomp_or "Quintil de recursos económicos COMPARABLE - hogar de origen"
label var ireccomp_act "Índice de recursos económicos COMPARABLE - hogar actual"
label var quintilecomp_act "Quintil de recursos económicos COMPARABLE - hogar actual" 


******************* Quintiles internos de cada región ***********************
* Se generan quintiles de de cada índice (origen y actual) tomando en cuenta 
* las distribuciones internas de cada región
forval i=1/5 {
	xtile r`i'quintilecomp_or=ireccomp_or [pw=factor] if region_14==`i', nq(5)
	xtile r`i'quintilecomp_act=ireccomp_act [pw=factor] if region_14==`i', nq(5)
}

forval i=1/5 {
label var r`i'quintilecomp_act "Quintil COMPARABLE al interior de la Región `i' - hogar actual"
label var r`i'quintilecomp_or "Quintil COMPARABLE al interior de la Región `i' - hogar de origen"
}

*Definición de lineas de pobreza
gen povline=.
replace povline=3165.34 if rururb==1
replace povline=4386.21 if rururb==0

gen extpovline=. 
replace extpovline=1701.52 if rururb==1
replace extpovline=2224.83 if rururb==0


drop index id rururb entidad edad_ent-region ocup-factor_ fac-hac ///
	 i_actrec1-ireccomp_or factor2 educp educm upm_muestra est
* Guardamos la base
save "$bases\EMOVI2023_comp.dta", replace 


********************************************************************************
****************************** 	TABULADOS **************************************
********************************************************************************

/*Figura 3. Movilidad social entre dos generaciones: población con origen en los 
hogares con menos recursos económicos */
tab quintilecomp_or quintilecomp_act[aw=factor] if quintilecomp_or==1, row nofreq


/*Figura 4. Movilidad educativa entre dos generaciones: población cuyos padres 
estudiaron primaria o menos*/
tab padres_edu educ [aw=factor] if padres_edu==1, row nofreq


/*Figura 5. Movilidad social entre dos generaciones: personas con origen en los
hogares con menos recursos económicos y que actualmente se encuentran en el mismo
grupo, por regiones*/
bysort region_14: tab quintilecomp_or quintilecomp_act[aw=factor] if quintilecomp_or==1, row nofreq


/*Figura 6. Movilidad social entre dos generaciones: destino de la población con
origen en los hogares con menos recursos económicos, frente a la población con
origen en los hogares con más recursos económicos (porcentaje de personas)*/
tab quintilecomp_or quintilecomp_act[aw=factor] if quintilecomp_or==1, row nofreq
tab quintilecomp_or quintilecomp_act[aw=factor] if quintilecomp_or==5, row nofreq


/*Figura 7. Movilidad social de las mujeres y los hombres: persistencia en los 
grupos 1 y 5 de recursos económicos, y movilidad de largo alcance (porcentaje de
personas)*/
bysort sexo: tab quintilecomp_or quintilecomp_act[aw=factor] if quintilecomp_or==1, row nofreq
bysort sexo: tab quintilecomp_or quintilecomp_act[aw=factor] if quintilecomp_or==5, row nofreq


/*Figura 8. Persistencia en el grupo con menos recursos económicos, por regiones*/
bysort region_14: tab quintilecomp_or quintilecomp_act[aw=factor] if quintilecomp_or==1, row nofreq


/*Figura 9. Persistencia intergeneracional en el grupo con menos recursos 
económicos en México y sus regiones, con base en umbrales comparables y con 
umbrales propios*/
*Norte
tab quintilecomp_or quintilecomp_act[aw=factor] if quintilecomp_or==1 & region_14==1, row nofreq
tab r1quintilecomp_or r1quintilecomp_act[aw=factor] if r1quintilecomp_or==1 & region_14==1, row nofreq

*Norte-occidente
tab quintilecomp_or quintilecomp_act[aw=factor] if quintilecomp_or==1 & region_14==2, row nofreq
tab r2quintilecomp_or r2quintilecomp_act[aw=factor] if r2quintilecomp_or==1 & region_14==2, row nofreq

*Centro-norte
tab quintilecomp_or quintilecomp_act[aw=factor] if quintilecomp_or==1 & region_14==3, row nofreq
tab r3quintilecomp_or r3quintilecomp_act[aw=factor] if r3quintilecomp_or==1 & region_14==3, row nofreq

*Centro
tab quintilecomp_or quintilecomp_act[aw=factor] if quintilecomp_or==1 & region_14==4, row nofreq
tab r4quintilecomp_or r4quintilecomp_act[aw=factor] if r4quintilecomp_or==1 & region_14==4, row nofreq

*Sur
tab quintilecomp_or quintilecomp_act[aw=factor] if quintilecomp_or==1 & region_14==5, row nofreq
tab r5quintilecomp_or r5quintilecomp_act[aw=factor] if r5quintilecomp_or==1 & region_14==5, row nofreq


/*Figura 10. Persistencia intergeneracional en el grupo con más recursos 
económicos en México y sus regiones, con base en umbrales comparables y con 
umbrales propios*/
*Norte
tab quintilecomp_or quintilecomp_act[aw=factor] if quintilecomp_or==5 & region_14==1, row nofreq
tab r1quintilecomp_or r1quintilecomp_act[aw=factor] if r1quintilecomp_or==5 & region_14==1, row nofreq

*Norte-occidente
tab quintilecomp_or quintilecomp_act[aw=factor] if quintilecomp_or==5 & region_14==2, row nofreq
tab r2quintilecomp_or r2quintilecomp_act[aw=factor] if r2quintilecomp_or==5 & region_14==2, row nofreq

*Centro-norte
tab quintilecomp_or quintilecomp_act[aw=factor] if quintilecomp_or==5 & region_14==3, row nofreq
tab r3quintilecomp_or r3quintilecomp_act[aw=factor] if r3quintilecomp_or==5 & region_14==3, row nofreq

*Centro
tab quintilecomp_or quintilecomp_act[aw=factor] if quintilecomp_or==5 & region_14==4, row nofreq
tab r4quintilecomp_or r4quintilecomp_act[aw=factor] if r4quintilecomp_or==5 & region_14==4, row nofreq

*Sur
tab quintilecomp_or quintilecomp_act[aw=factor] if quintilecomp_or==5 & region_14==5, row nofreq
tab r5quintilecomp_or r5quintilecomp_act[aw=factor] if r5quintilecomp_or==5 & region_14==5, row nofreq


/*Figura 11. Movilidad educativa entre dos generaciones: población cuyos padres
estudiaron primaria o menos, frente a la población con padres que alcanzaron
estudios profesionales (porcentaje de personas)*/
tab padres_edu educ [aw=factor] if padres_edu==1, row nofreq
tab padres_edu educ [aw=factor] if padres_edu==4, row nofreq


/*Figura 12. Movilidad educativa de las mujeres frente a la de los hombres, 
extremos de la distribución educativa (porcentaje de personas)*/
bysort sexo: tab padres_edu educ [aw=factor] if padres_edu==1, row nofreq
bysort sexo: tab padres_edu educ [aw=factor] if padres_edu==4, row nofreq


/*Figura 13. Probabilidad de estudiar el nivel medio superior según el máximo 
nivel educativo alcanzado por los padres, por regiones (porcentaje de personas)
NOTA: los datos que se toman corresponden a la tercera columna (media superior)*/
bysort region_14: tab padres_edu educ [aw=factor], row nofreq


/*Figura 14. Probabilidad de alcanzar estudios profesionales según el máximo
nivel educativo alcanzado por los padres, por regiones (porcentaje de personas)
NOTA: los datos que se toman corresponden a la cuarta columna (profesional)*/
bysort region_14: tab padres_edu educ [aw=factor], row nofreq


/*Figura 15. Persistencia intergeneracional en educación para los extremos
(primaria o menos y estudios profesionales), por región*/
bysort region_14: tab padres_edu educ [aw=factor] if padres_edu==1, row nofreq
bysort region_14: tab padres_edu educ [aw=factor] if padres_edu==4, row nofreq


*****Se junta la información de 2023 y 2017
append using "$bases\EMOVI2017_comp.dta"
label var year "Año de la encuesta"

gen pov=1 if ingc_pc<=povline
replace pov=0 if pov==.
label var pov "Pobreza"

gen extpov=1 if ingc_pc<=extpovline
replace extpov=0 if extpov==.
label var extpov "Pobreza extrema"

label var povline "Línea de pobreza"
label var extpovline "Línea de pobreza extrema"


/*Figura 18. Incidencia de la pobreza en México y sus regiones, 2017 y 2023
(porcentaje de personas)*/
tabstat pov[aw=factor], by(year) nototal
tabstat pov[aw=factor] if region_14==1, by(year) nototal
tabstat pov[aw=factor] if region_14==2, by(year) nototal
tabstat pov[aw=factor] if region_14==3, by(year) nototal
tabstat pov[aw=factor] if region_14==4, by(year) nototal
tabstat pov[aw=factor] if region_14==5, by(year) nototal


/*Figura 19. Persistencia intergeneracional en pobreza absoluta (porcentaje de personas)*/
tabstat pov[aw=factor] if quintilecomp_or<=2, by(year) nototal
tabstat pov[aw=factor] if region_14==1 & quintilecomp_or<=2, by(year) nototal
tabstat pov[aw=factor] if region_14==2 & quintilecomp_or<=2, by(year) nototal
tabstat pov[aw=factor] if region_14==3 & quintilecomp_or<=2, by(year) nototal
tabstat pov[aw=factor] if region_14==4 & quintilecomp_or<=2, by(year) nototal
tabstat pov[aw=factor] if region_14==5 & quintilecomp_or<=2, by(year) nototal


/*Figura 20. Incidencia de la pobreza extrema en México y sus regiones, 2017 y 2023 
(proporción de la población mexicana entre 25 y 64 años) */
tabstat extpov[aw=factor], by(year) nototal
tabstat extpov[aw=factor] if region_14==1, by(year) nototal
tabstat extpov[aw=factor] if region_14==2, by(year) nototal
tabstat extpov[aw=factor] if region_14==3, by(year) nototal
tabstat extpov[aw=factor] if region_14==4, by(year) nototal
tabstat extpov[aw=factor] if region_14==5, by(year) nototal


/*Figura 21. Persistencia intergeneracional en pobreza extrema absoluta*/
tabstat extpov[aw=factor] if quintilecomp_or==1, by(year) nototal
tabstat extpov[aw=factor] if region_14==1 & quintilecomp_or==1, by(year) nototal
tabstat extpov[aw=factor] if region_14==2 & quintilecomp_or==1, by(year) nototal
tabstat extpov[aw=factor] if region_14==3 & quintilecomp_or==1, by(year) nototal
tabstat extpov[aw=factor] if region_14==4 & quintilecomp_or==1, by(year) nototal
tabstat extpov[aw=factor] if region_14==5 & quintilecomp_or==1, by(year) nototal

save "$bases\ESRU_EMOVI_17_23.dta", replace
