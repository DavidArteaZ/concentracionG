# ESRU-EMOVI 2023: municipal coverage, mobility matrices, and appendices.
# Run: Rscript mobility_analysis.R [input.rds] [output_directory]
# Leaves the source unchanged; preserves previously constructed IRE scores and quintiles.
packages <- c("dplyr", "tidyr", "ggplot2", "survey", "gridExtra", "ragg", "sf", "jsonlite")
missing_packages <- packages[!vapply(packages, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing_packages)) stop("Install these packages: ", paste(missing_packages, collapse = ", "))
suppressPackageStartupMessages({library(dplyr); library(tidyr); library(ggplot2); library(survey)})
args <- commandArgs(trailingOnly = TRUE)
# Locate this script under Rscript or source(), independently of getwd().
script_argument <- grep("^--file=", commandArgs(), value = TRUE)
source_files <- Filter(Negate(is.null), lapply(sys.frames(), function(f) f$ofile))
script_path <- if (length(source_files)) tail(source_files, 1)[[1]] else
  if (length(script_argument)) sub("^--file=", "", script_argument[1]) else NA_character_
if (is.na(script_path)) stop("Run the saved script with source() or Rscript to locate its folder.")
image_dir <- dirname(normalizePath(script_path, mustWork = TRUE))
input_path <- if (length(args)) args[1] else "/Users/andonigarritzayala/Desktop/01_generar_ires_quintiles_esru.rds"
output_dir <- if (length(args) > 1) args[2] else "mobility_outputs"
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

# EDITABLE SETTINGS. Do not recalculate quintiles within individual regions.
config <- list(age_min = 25, age_max = 34,
            origin_ire = "irec_or_ceey", destination_ire = "irec_act",
            origin_quintile = "q_or_c1_ceey", destination_quintile = "q_act_c1",
            region = "region_14", municipality = "p20_COD", weight = "factor",
            upm = "upm_muestra", stratum = "est")
# Update both IRE and quintile variables if selecting a different specification.
# National-quintile alternative: q_or_nac_ceey and q_act_nac_ceey.
# region_14 identifies origin; region identifies current residence.
region_names <- c("North", "Northwest", "North-central", "Central", "South")
blue_theme <- function(type = c("general", "matrix", "points")) {
  type <- match.arg(type)
  theme_object <- theme_minimal(base_size = 12) + theme(
    plot.title = element_text(face = "bold", color = "#102A43", size = 15),
    plot.subtitle = element_text(color = "#486581", size = 11, margin = margin(b = 12)),
    axis.title = element_text(face = "bold", color = "#243B53"),
    axis.text = element_text(color = "#334E68"),
    plot.caption = element_text(color = "#627D98", hjust = 0, margin = margin(t = 10)),
    plot.title.position = "plot", plot.caption.position = "plot")
  if (type == "matrix") theme_object <- theme_object + theme(
    strip.text = element_text(face = "bold", color = "#102A43"),
    strip.background = element_rect(fill = "#D9E2EC", color = NA),
    panel.grid = element_blank(), panel.spacing = grid::unit(1, "lines"),
    legend.title = element_text(face = "bold", color = "#243B53"),
    legend.text = element_text(color = "#334E68"))
  else if (type == "points") theme_object <- theme_object + theme(
    panel.grid.minor = element_blank(), panel.grid.major.y = element_blank(),
    panel.grid.major.x = element_line(color = "#D9E2EC", linewidth = 0.4))
  else theme_object <- theme_object + theme(panel.grid.minor = element_blank(),
                           panel.grid.major = element_line(color = "#D9E2EC", linewidth = 0.3))
  theme_object
}
save_csv <- function(x, name) write.csv(x, file.path(output_dir, paste0(name, ".csv")),
                                       row.names = FALSE, na = "", fileEncoding = "UTF-8")
base <- readRDS(input_path)
required_variables <- c("edad", unlist(config[3:length(config)]))
if (!all(required_variables %in% names(base))) stop("Missing variables: ", paste(setdiff(required_variables, names(base)), collapse = ", "))
dictionary <- data.frame(variable = required_variables, description = c(
  "Respondent age", "Origin economic resource index", "Destination economic resource index",
  "Origin quintile", "Destination quintile", "Region used for grouping",
  "Origin municipality at age 14: five-digit geographic code", "Respondent survey weight",
  "Primary sampling unit", "Survey design stratum"))
save_csv(dictionary, "dictionary_variables")
d <- data.frame(edad = base$edad, ire_o = base[[config$origin_ire]], ire_d = base[[config$destination_ire]],
                qo = base[[config$origin_quintile]], qd = base[[config$destination_quintile]],
                region_code = base[[config$region]], raw_municipality = as.character(base[[config$municipality]]),
                weight = base[[config$weight]], upm = base[[config$upm]], stratum = base[[config$stratum]])
d$age_cohort <- !is.na(d$edad) & d$edad >= config$age_min & d$edad <= config$age_max
d$valid_design <- is.finite(d$weight) & d$weight > 0 & !is.na(d$upm) & nzchar(d$upm) & !is.na(d$stratum)
d$valid_matrix <- d$qo %in% 1:5 & d$qd %in% 1:5
d$region <- region_names[match(d$region_code, 1:5)]
# Structural validity only; not validation against a historical INEGI municipality catalog.
mun <- suppressWarnings(as.integer(d$raw_municipality))
d$municipality <- ifelse(!is.na(mun), sprintf("%05d", mun), NA_character_)
d$valid_municipality <- !is.na(mun) & mun %/% 1000 %in% 1:32 & mun %% 1000 > 0 & mun %% 1000 < 999
d$municipality[!d$valid_municipality] <- NA_character_
save_csv(d %>% filter(age_cohort, !valid_municipality) %>% count(raw_municipality, name = "n"), "municipalities_unidentified")
sample_flow <- data.frame(stage = c("Input data", "Respondents aged 25-34",
  "Positive survey weight and identified PSU and stratum",
  "Valid origin and destination quintiles (Q1-Q5)",
  "Identified region of residence at age 14",
  "Structurally valid municipality code at age 14"),
                    n = c(nrow(d), sum(d$age_cohort), sum(d$age_cohort & d$valid_design),
                          sum(d$age_cohort & d$valid_design & d$valid_matrix),
                          sum(d$age_cohort & d$valid_design & d$valid_matrix & !is.na(d$region)),
                          sum(d$age_cohort & d$valid_design & d$valid_matrix & !is.na(d$region) & d$valid_municipality)))
sample_flow$excluded_at_step <- c(NA_integer_, head(sample_flow$n, -1) - tail(sample_flow$n, -1))
save_csv(sample_flow, "sample_flow")

# Municipality counts are interviews, not estimated municipal populations.
coh <- d %>% filter(age_cohort)
municipal_counts <- coh %>% filter(valid_municipality) %>% group_by(municipality) %>% summarise(
  n_age_cohort = n(), n_matrix = sum(valid_design & valid_matrix),
  n_origin_ire = sum(is.finite(ire_o)), n_destination_ire = sum(is.finite(ire_d)), .groups = "drop") %>%
  mutate(pct_identified_cohort = 100 * n_age_cohort / sum(n_age_cohort),
         pct_identified_matrix = 100 * n_matrix / sum(n_matrix)) %>% arrange(desc(n_matrix), municipality)
save_csv(municipal_counts, "observations_by_origin_municipality")
municipal_summary <- bind_rows(lapply(c("n_age_cohort", "n_matrix"), function(v) {
  z <- municipal_counts[[v]]; z <- z[z > 0]
  data.frame(sample = v, municipalities = length(z), interviews = sum(z),
             minimum = min(z), p25 = unname(quantile(z, .25)), median = median(z),
             mean = mean(z), p75 = unname(quantile(z, .75)), maximum = max(z),
             municipalities_n_below_5 = sum(z < 5), municipalities_n_below_10 = sum(z < 10))
}))
save_csv(municipal_summary, "coverage_summary_municipal")
save_csv(municipal_counts %>% mutate(n_range = cut(n_matrix, c(-1,0,4,9,19,49,Inf),
  labels = c("0", "1-4", "5-9", "10-19", "20-49", "50 or more"))) %>%
  count(n_range, name = "municipalities", .drop = FALSE), "size_distribution_municipal")

# Construct the survey design BEFORE restricting the age cohort: domain analysis.
# Use the available first-stage information without finite population correction.
# Confirm est and upm_muestra against the survey technical documentation.
options(survey.lonely.psu = "adjust", survey.adjust.domain.lonely = TRUE)
design <- svydesign(ids = ~upm, strata = ~stratum, weights = ~weight,
                    data = d[d$valid_design, ], nest = TRUE)
dm <- subset(design, age_cohort & valid_matrix)

# Conditional probability: destination j GIVEN origin i. Each row sums to 100%.
# Korn-Graubard beta CIs with variance accounting for strata, PSUs, and weights.
# Do not estimate beta CIs at p=0 or 1; zero observed events do not imply certainty.
matrix <- bind_rows(lapply(c("National", region_names), function(g) {
  dg <- if (g == "National") dm else subset(dm, region == g & !is.na(region))
  bind_rows(lapply(1:5, function(i) {
    di <- subset(dg, qo == i)
    z <- di$variables
    bind_rows(lapply(1:5, function(j) {
      row_n <- nrow(z); cell_n <- sum(z$qd == j)
      p <- if (row_n) weighted.mean(z$qd == j, z$weight) else NA_real_
      li <- ls <- se <- NA_real_; status <- "No origin observations"
      if (row_n) {
        di_j <- update(di, event = as.numeric(qd == j))
        se <- as.numeric(SE(svymean(~event, di_j)))
        status <- "CI available"
        if (p <= 0 || p >= 1) status <- "CI unavailable: boundary proportion"
        else {
          fit <- tryCatch(svyciprop(~event, di_j, method = "beta", level = .95), error = function(e) NULL)
          if (!is.null(fit)) {ci <- as.numeric(confint(fit)); li <- ci[1]; ls <- ci[2]}
          if (!is.finite(li) || !is.finite(ls)) status <- "CI unavailable"
        }
      }
      data.frame(scope = g, origin_quintile = i, destination_quintile = j, cell_n = cell_n,
                 row_n = row_n, percent = 100*p, ci95_lower = 100*li,
                 ci95_upper = 100*ls, standard_error_pp = 100*se,
                 row_kish_effective_n = if(row_n) sum(z$weight)^2/sum(z$weight^2) else NA_real_,
                 cell_n_below_5 = cell_n < 5, ci_status = status)
    }))
  }))
}))
save_csv(matrix, "matrix_cells_ci95")
domain_diagnostics <- bind_rows(lapply(c("National", region_names), function(g) {
  z <- dm$variables
  if (g != "National") z <- z[!is.na(z$region) & z$region == g, ]
  z %>% group_by(qo, stratum) %>% summarise(psus = n_distinct(upm), interviews = n(), .groups = "drop") %>%
    mutate(scope = g, singleton_psu_domain = psus == 1)
}))
save_csv(domain_diagnostics, "domain_design_diagnostics")
stopifnot(all(abs((matrix %>% group_by(scope, origin_quintile) %>%
  summarise(s = sum(percent), .groups = "drop") %>% filter(is.finite(s)))$s - 100) < 1e-7))
for (g in c("National", region_names)) {
  appendix <- matrix %>% filter(scope == g) %>% mutate(cell = ifelse(is.finite(ci95_lower),
    sprintf("%.1f%% [%.1f; %.1f]; n=%d", percent, ci95_lower, ci95_upper, cell_n),
    sprintf("%.1f%% [CI unavailable]; n=%d", percent, cell_n))) %>%
    select(origin_quintile, row_n, destination_quintile, cell) %>%
    pivot_wider(names_from = destination_quintile, values_from = cell, names_prefix = "destination_Q")
  save_csv(appendix, paste0("appendix_matrix_", g))
}
plot_matrix <- function(m, subtitle_text, facets = FALSE) {
  p <- ggplot(m, aes(factor(destination_quintile), factor(origin_quintile), fill = percent)) +
    geom_tile(color = "white", linewidth = .5) +
    geom_text(aes(label = sprintf("%.1f%%", percent), color = percent >= 50), size = 3.6) +
    scale_color_manual(values = c("FALSE" = "#102A43", "TRUE" = "white"), guide = "none") +
    scale_fill_gradient(low = "#F0F4F8", high = "#08519C", limits = c(0,100), name = "%") +
    scale_y_discrete(limits = as.character(5:1)) + coord_equal() +
    labs(title = "Intergenerational economic resource mobility", subtitle = subtitle_text,
      x = "Destination quintile", y = "Origin quintile",
      caption = "Source: authors' calculations, ESRU-EMOVI 2023. Ages 25-34.\nWeighted row percentages; quintiles retained from input. Q1: lowest resources.") + blue_theme("matrix")
  if (facets) p <- p + facet_wrap(~scope, ncol = 3)
  p
}
mn <- plot_matrix(filter(matrix, scope == "National"), "National")
mr <- plot_matrix(mutate(filter(matrix, scope != "National"), scope = factor(scope, levels = region_names)), "By region of origin (residence at age 14)", TRUE)
for (ext in c("png", "pdf")) {
  ggsave(file.path(output_dir, paste0("matrix_national.", ext)), mn, width = 8, height = 7, dpi = 300)
  ggsave(file.path(output_dir, paste0("regional_matrices.", ext)), mr, width = 14, height = 10, dpi = 300)
}
# All six matrices in a single image; a shared color scale enables comparison.
all_matrices <- matrix %>% mutate(scope = factor(scope, levels = c("National", region_names)))
combined_matrix_plot <- plot_matrix(all_matrices,
  "National and regions of origin | Ages 25-34", facets = TRUE) +
  theme(plot.title = element_text(size = 27, margin = margin(b = 8)),
        plot.subtitle = element_text(size = 18, margin = margin(b = 16)),
        strip.text = element_text(size = 15),
        plot.margin = margin(14, 14, 14, 14))
ggsave(file.path(image_dir, "figure_mobility_all_matrices.png"), combined_matrix_plot,
       device = ragg::agg_png, width = 14, height = 10, dpi = 300, bg = "white")

# IRE: use the common matrix sample to compare origin and destination summaries.
# Weighted quantiles: inverse of the weighted empirical distribution.
wquant <- function(x, w, probs) {
  o <- order(x); x <- x[o]; w <- w[o]; f <- cumsum(w)/sum(w)
  vapply(probs, function(p) x[which(f >= p)[1]], numeric(1))
}
descriptive_statistics <- bind_rows(lapply(c("ire_o", "ire_d"), function(v) {
  z <- dm$variables; ok <- is.finite(z[[v]]); x <- z[[v]][ok]; w <- z$weight[ok]
  if (!length(x)) stop("No valid IRE scores for ", v)
  mu <- weighted.mean(x,w); qu <- wquant(x,w,c(.25,.5,.75))
  data.frame(index = if(v == "ire_o") "Origin IRE" else "Destination IRE",
    n = length(x), missing_in_matrix_sample = sum(!ok), weighted_mean = mu,
    weighted_sd = sqrt(sum(w*(x-mu)^2)/sum(w)), minimum = min(x),
    weighted_p25 = qu[1], weighted_median = qu[2], weighted_p75 = qu[3], maximum = max(x))
}))
save_csv(descriptive_statistics, "appendix_descriptive_statistics_ire")
saveRDS(config, file.path(output_dir, "configuration.rds"))
capture.output(sessionInfo(), file = file.path(output_dir, "sessionInfo.txt"))
capture.output(print(sample_flow), print(municipal_summary), print(descriptive_statistics), file = file.path(output_dir, "execution_summary.txt"))
message("Outputs saved to: ", normalizePath(output_dir))

# Readable appendix tables, ready to review or print from a browser.
html_escape <- function(x) {
  x <- gsub("&", "&amp;", as.character(x), fixed = TRUE)
  x <- gsub("<", "&lt;", x, fixed = TRUE)
  gsub(">", "&gt;", x, fixed = TRUE)
}
html_table <- function(x) {
  x[] <- lapply(x, function(z) if (is.numeric(z)) format(round(z, 3), trim = TRUE) else z)
  header <- paste0("<th>", html_escape(names(x)), "</th>", collapse = "")
  rows <- apply(x, 1, function(z) paste0("<tr>", paste0("<td>", html_escape(z), "</td>", collapse = ""), "</tr>"))
  paste0("<table><thead><tr>", header, "</tr></thead><tbody>", paste(rows, collapse = ""), "</tbody></table>")
}
html <- c('<!doctype html><html lang="en"><meta charset="utf-8"><title>Mobility appendices</title>',
  '<style>body{font-family:Arial;color:#102A43;margin:32px;max-width:1200px}table{border-collapse:collapse;font-size:12px;margin-bottom:24px}th,td{border:1px solid #D9E2EC;padding:8px;text-align:left}th{background:#D9E2EC}h2{margin-top:32px}@media print{h2{break-before:page}table{break-inside:avoid}}</style>',
  '<h1>ESRU-EMOVI 2023: mobility appendices</h1>',
  '<p>Population analyzed: ages 25-34. Regional matrices use region of origin at age 14. Quintile classifications are retained from the input data, not recalculated by region.</p>',
  '<h2>Sample selection</h2>', html_table(sample_flow),
  '<h2>Origin municipality coverage</h2>', html_table(municipal_summary),
  '<p>Municipal counts are unweighted interviews. Municipality codes are checked for structural validity only. Detailed counts are provided in observations_by_origin_municipality.csv. These counts do not establish municipal representativeness.</p>',
  '<h2>Economic resource index (IRE) descriptive statistics</h2>', html_table(descriptive_statistics),
  '<p>Both indices are summarized in the common matrix sample. Means, standard deviations, and quartiles are weighted. Standard deviation is the weighted distribution standard deviation, not a standard error. Minimum and maximum are observed values. Index scores are not monetary amounts.</p>')
for (g in c("National", region_names)) {
  tab <- read.csv(file.path(output_dir, paste0("appendix_matrix_", g, ".csv")), check.names = FALSE)
  html <- c(html, paste0("<h2>Transition matrix: ", g, "</h2>"), html_table(tab))
}
html <- c(html,
  '<p>Cell format: weighted percentage [95% confidence interval]; unweighted cell n. row_n is the unweighted number with that origin quintile. Each row sums to 100% before rounding.</p>',
  '<p>Intervals use the Korn-Graubard beta method with weights (factor), PSUs (upm_muestra), and strata (est), under a first-stage with-replacement approximation. The full design is built before cohort and quintile domain restrictions. Singleton-PSU domains use the survey adjustment option and are listed in domain_design_diagnostics.csv. No finite population correction is supplied. Confirm the design specification against the technical documentation before publication.</p>',
  '<p>Intervals are conditional on the supplied IRE scores and quintile cutoffs; they do not propagate uncertainty from index construction, cutoffs, missing-data handling, or nonresponse. These are pointwise intervals, not simultaneous intervals. Cells with observed probability zero or one have unavailable beta intervals. Missing municipality codes are retained in mobility matrices if quintiles and design fields are valid.</p>',
  '</html>')
writeLines(html, file.path(output_dir, "appendix_tables.html"), useBytes = TRUE)

# Independent 300-dpi table images for insertion into Word.
# Blue headers, alternating row fills, white background, and readable labels.
export_table_image <- function(tab, title, filename, notes, subtitle = "",
                               title_size = 18, subtitle_size = 13) {
  tab[] <- lapply(tab, as.character)
  table_theme <- gridExtra::ttheme_minimal(base_size = 12,
    core = list(fg_params = list(col = "#243B53"),
                bg_params = list(fill = rep(c("white", "#F0F4F8"), length.out = nrow(tab)), col = "#D9E2EC")),
    colhead = list(fg_params = list(col = "#102A43", fontface = "bold"),
                   bg_params = list(fill = "#D9E2EC", col = "white")),
    padding = grid::unit(c(4, 5), "mm"))
  # Measure on the same rendering device used for the final output.
  measuring_path <- tempfile(fileext = ".png")
  ragg::agg_png(measuring_path, width = 12, height = 8, units = "in", res = 300)
  tg <- gridExtra::tableGrob(tab, rows = NULL, theme = table_theme)
  table_width <- grid::convertWidth(sum(tg$widths), "in", valueOnly = TRUE)
  table_height <- grid::convertHeight(sum(tg$heights), "in", valueOnly = TRUE)
  dev.off(); unlink(measuring_path)
  # Account for the enlarged title so that long titles remain fully visible.
  ragg::agg_png(measuring_path, width = 12, height = 8, units = "in", res = 300)
  title_width <- grid::convertWidth(grid::grobWidth(grid::textGrob(title,
    gp = grid::gpar(fontsize = title_size, fontface = "bold"))), "in", valueOnly = TRUE)
  dev.off(); unlink(measuring_path)
  width <- max(8, table_width + 0.6, title_width + 0.6)
  note_lines <- strwrap(notes, width = max(80, floor(width * 13)))
  header_height <- if (nzchar(subtitle)) 0.95 else 0.65
  footer_height <- length(note_lines) * 0.18 + 0.25
  height <- header_height + table_height + footer_height + 0.35
  path <- file.path(image_dir, filename)
  ragg::agg_png(path, width = width, height = height, units = "in", res = 300, background = "white")
  grid::grid.newpage()
  grid::pushViewport(grid::viewport(layout = grid::grid.layout(3, 1,
    heights = grid::unit(c(header_height, table_height, footer_height), "in"))))
  grid::pushViewport(grid::viewport(layout.pos.row = 1))
  grid::grid.text(title, x = grid::unit(.3, "in"), y = .72, just = "left",
    gp = grid::gpar(fontsize = title_size, fontface = "bold", col = "#102A43"))
  if (nzchar(subtitle)) grid::grid.text(subtitle, x = grid::unit(.3, "in"), y = .30,
    just = "left", gp = grid::gpar(fontsize = subtitle_size, col = "#486581"))
  grid::popViewport()
  grid::pushViewport(grid::viewport(layout.pos.row = 2)); grid::grid.draw(tg); grid::popViewport()
  grid::pushViewport(grid::viewport(layout.pos.row = 3))
  grid::grid.text(paste(note_lines, collapse = "\n"), x = grid::unit(.3, "in"),
    y = grid::unit(footer_height - .12, "in"), just = c("left", "top"),
    gp = grid::gpar(fontsize = 10, col = "#627D98", lineheight = 1.1))
  grid::popViewport(2); dev.off()
  invisible(path)
}
fmt_n <- function(z) format(z, big.mark = ",", scientific = FALSE, trim = TRUE)
fmt_score <- function(z) sprintf("%.3f", z)
selection_table <- data.frame("Sample selection step" = sample_flow$stage,
  "Individuals\nremaining" = fmt_n(sample_flow$n),
  "Excluded at\nthis step" = ifelse(is.na(sample_flow$excluded_at_step), "--",
                                   fmt_n(sample_flow$excluded_at_step)), check.names = FALSE)
selection_table[[1]] <- vapply(selection_table[[1]], function(z)
  paste(strwrap(z, width = 47), collapse = "\n"), character(1))
export_table_image(selection_table, "Sample selection", "table_sample_selection.png",
  "Source: authors' calculations, ESRU-EMOVI 2023. Filters are cumulative; exclusions are relative to the preceding row. PSU: primary sampling unit. Counts are unweighted interviews.",
  title_size = 16)

# Transpose wide summaries without removing any statistics.
coverage_labels <- c("Municipalities", "Individuals", "Minimum interviews per municipality", "25th percentile",
  "Median", "Mean", "75th percentile", "Maximum", "Municipalities with fewer than 5 interviews",
  "Municipalities with fewer than 10 interviews")
coverage_table <- data.frame("Statistic" = coverage_labels,
  "Age cohort (25-34)" = sapply(municipal_summary[1, -1], function(z) if(z == floor(z)) fmt_n(z) else sprintf("%.2f",z)),
  "Matrix sample" = sapply(municipal_summary[2, -1], function(z) if(z == floor(z)) fmt_n(z) else sprintf("%.2f",z)),
  check.names = FALSE)
export_table_image(coverage_table, "Origin municipality coverage", "table_origin_municipality_coverage.png",
  "Source: authors' calculations, ESRU-EMOVI 2023. Both columns include only structurally valid origin municipality codes. Matrix sample additionally requires positive, finite survey weights, identified PSUs and strata, and valid origin and destination quintiles. Municipalities with no matrix observations are excluded from the matrix-sample summary. Counts are unweighted.")
ire_labels <- c("Individuals", "Missing scores in matrix sample", "Weighted mean", "Weighted standard deviation",
                "Minimum", "Weighted 25th percentile", "Weighted median", "Weighted 75th percentile", "Maximum")
ire_table <- data.frame("Statistic" = ire_labels,
  "Origin IRE" = vapply(seq_along(ire_labels), function(k) {
    z <- descriptive_statistics[1,k+1]; if(k <= 2) fmt_n(z) else fmt_score(z)}, character(1)),
  "Destination IRE" = vapply(seq_along(ire_labels), function(k) {
    z <- descriptive_statistics[2,k+1]; if(k <= 2) fmt_n(z) else fmt_score(z)}, character(1)), check.names = FALSE)
export_table_image(ire_table, "Economic resource index (IRE): descriptive statistics", "table_ire_descriptive_statistics.png",
  "Source: authors' calculations, ESRU-EMOVI 2023. Common matrix sample, ages 25-34. Means, standard deviations, and quartiles are weighted; minima and maxima are observed. IRE scores are not monetary amounts.")
for (g in c("National", region_names)) {
  cells <- matrix %>% filter(scope == g) %>% mutate(cell = ifelse(is.finite(ci95_lower),
    sprintf("%.1f%%\n[%.1f; %.1f]\nn = %s", percent, ci95_lower, ci95_upper, fmt_n(cell_n)),
    sprintf("%.1f%%\nCI unavailable\nn = %s", percent, fmt_n(cell_n)))) %>%
    select(origin_quintile, row_n, destination_quintile, cell) %>%
    pivot_wider(names_from = destination_quintile, values_from = cell, names_prefix = "Q")
  cells$origin_quintile <- paste0("Q", cells$origin_quintile)
  cells$row_n <- fmt_n(cells$row_n)
  names(cells) <- c("Origin\nquintile", "Row\nn", paste0("Destination\nQ",1:5))
  export_table_image(cells, paste0("Transition matrix: ", g),
    paste0("table_transition_matrix_", tolower(gsub("-", "_", g)), ".png"),
    "Source: authors' calculations, ESRU-EMOVI 2023. Each cell shows weighted percentage, pointwise 95% confidence interval, and unweighted n. Row n is the origin-quintile denominator. Intervals account for weights, strata, and PSUs, with singleton-domain adjustment. Q1: lowest resources; Q5: highest.",
    "Ages 25-34 | Destination conditional on origin quintile")
}

# Requested distribution: only municipalities represented in the matrix sample.
municipal_distribution <- municipal_counts %>% filter(n_matrix > 0) %>%
  mutate(interview_range = cut(n_matrix, c(0,4,9,19,49,Inf),
    labels = c("1-4", "5-9", "10-19", "20-49", "50 or more"))) %>%
  group_by(interview_range, .drop = FALSE) %>%
  summarise(municipalities = n(), individuals = sum(n_matrix), .groups = "drop") %>%
  mutate(pct_municipalities = 100 * municipalities / sum(municipalities)) %>%
  select(interview_range, municipalities, pct_municipalities, individuals)
municipal_distribution$interview_range <- as.character(municipal_distribution$interview_range)
municipal_distribution <- bind_rows(municipal_distribution, data.frame(interview_range = "Total",
  municipalities = sum(municipal_distribution$municipalities), pct_municipalities = 100,
  individuals = sum(municipal_distribution$individuals)))
save_csv(municipal_distribution, "origin_municipality_distribution")
distribution_table <- data.frame("Individuals per\nmunicipality" = municipal_distribution$interview_range,
  "Number of\nmunicipalities" = fmt_n(municipal_distribution$municipalities),
  "Percentage of\nmunicipalities" = sprintf("%.1f%%", municipal_distribution$pct_municipalities),
  "Total\nindividuals" = fmt_n(municipal_distribution$individuals), check.names = FALSE)
missing_municipality_n <- sum(d$age_cohort & d$valid_design & d$valid_matrix & !d$valid_municipality)
municipality_n <- municipal_counts$n_matrix[municipal_counts$n_matrix > 0]
export_table_image(distribution_table, "Distribution of observations by origin municipality",
  "table_origin_municipality_distribution.png",
  sprintf("Source: authors' calculations, ESRU-EMOVI 2023. Unweighted counts in the matrix sample with structurally valid origin municipality codes. Median: %g individuals per municipality; range: %d-%d. %d matrix-sample individuals have missing or invalid municipality codes and are excluded from this table. Percentages may not sum to 100 after rounding.",
    median(municipality_n), min(municipality_n), max(municipality_n), missing_municipality_n),
  "Municipality of residence at age 14 | Ages 25-34")
message("Word-ready PNG images saved alongside the script: ", image_dir)


# CEEY (2025), Annex 1, printed p. 87 (PDF p. 88).
# Documentation transcribed from the report, not inferred from the input RDS.
# Inclusion flags do not validate how the supplied index scores were constructed.
eri_components <- data.frame(
  variable = c("Household overcrowding", "Car ownership", "Piped water inside the home",
    "Electricity", "Water heater", "Paid domestic worker", "Gas or electric stove",
    "Washing machine", "Refrigerator", "Landline telephone", "Television",
    "Vacuum cleaner", "Cable television", "Microwave oven", "Computer/laptop/tablet",
    "DVD player or cassette recorder", "Another house or apartment", "Commercial premises",
    "Credit card (bank or department store)", "Bank or checking account",
    "Agricultural machinery/equipment", "Internet connection", "Land or plot"),
  origin_household = c(rep(TRUE, 20), rep(FALSE, 3)),
  current_household = c(TRUE, TRUE, TRUE, FALSE, TRUE, TRUE, TRUE, TRUE,
    FALSE, FALSE, FALSE, FALSE, TRUE, TRUE, TRUE, FALSE, TRUE, TRUE, TRUE,
    TRUE, TRUE, TRUE, TRUE)
)
stopifnot(nrow(eri_components) == 23L,
          sum(eri_components$origin_household) == 20L,
          sum(eri_components$current_household) == 17L)
save_csv(eri_components, "appendix_eri_components_ceey_2025")
eri_components_table <- data.frame(
  "Variable" = eri_components$variable,
  "Origin\nhousehold" = ifelse(eri_components$origin_household, "X", ""),
  "Current\nhousehold" = ifelse(eri_components$current_household, "X", ""),
  check.names = FALSE
)
eri_component_notes <- paste(
  "Source: CEEY, Informe de movilidad social en Mexico 2025, Annex 1, p. 87.",
  "Authors' English translation. X: included in the report's comparable economic resource index (ERI);",
  "blank: not marked as included. Current household corresponds to destination."
)
export_table_image(eri_components_table,
  "Variables included in the comparable economic resource index",
  "table_eri_components_ceey_2025.png", eri_component_notes,
  "Origin and current households | CEEY 2025")
# Add the source-based specification to the existing appendix collection.
html <- append(html, c('<h2>Variables included in the comparable economic resource index (ERI)</h2>',
  html_table(eri_components_table), paste0('<p>', html_escape(eri_component_notes), '</p>')),
  after = length(html) - 1L)
writeLines(html, file.path(output_dir, "appendix_tables.html"), useBytes = TRUE)


# Map sample coverage, not municipal representativeness or mobility estimates.
# INEGI API snapshots are cached beside the script. Preserve this cache to reproduce the map.
boundary_dir <- file.path(image_dir, "map_boundaries")
dir.create(boundary_dir, recursive = TRUE, showWarnings = FALSE)
boundary_files <- file.path(boundary_dir, sprintf("municipalities_%02d.geojson", 1:32))
old_timeout <- getOption("timeout")
options(timeout = max(180, old_timeout))
for (k in seq_along(boundary_files)) {
  f <- boundary_files[k]
  if (!file.exists(f)) {
    url <- sprintf("https://gaia.inegi.org.mx/wscatgeo/v2/geo/mgem/%02d", k)
    tmp <- tempfile(fileext = ".geojson")
    tryCatch({
      download.file(url, tmp, mode = "wb", quiet = TRUE)
      check <- jsonlite::fromJSON(tmp, simplifyVector = FALSE)
      if (!length(check$features)) stop("No municipal geometries returned: ", url)
      file.copy(tmp, f, overwrite = FALSE)
    }, error = function(e) stop("Could not obtain INEGI boundaries: ", conditionMessage(e)))
    unlink(tmp)
  }
}
options(timeout = old_timeout)
cartographic_sources <- vapply(boundary_files, function(f) {
  j <- jsonlite::fromJSON(f, simplifyVector = FALSE)
  j$metadatos$Fuente_informacion_vectorial
}, character(1))
writeLines(unique(cartographic_sources), file.path(output_dir, "map_cartographic_source.txt"))
municipal_geometry <- bind_rows(lapply(boundary_files, function(f) sf::st_read(f, quiet = TRUE)))
municipal_geometry$cvegeo <- sprintf("%05d", as.integer(municipal_geometry$cvegeo))
stopifnot(!anyDuplicated(municipal_geometry$cvegeo))
map_counts <- municipal_counts %>% filter(n_matrix > 0) %>% select(municipality, n_matrix)
map_unmatched <- anti_join(map_counts, sf::st_drop_geometry(municipal_geometry),
                          by = c("municipality" = "cvegeo"))
save_csv(map_unmatched, "map_unmatched_municipalities")
if (nrow(map_unmatched)) warning("Unmatched municipality codes excluded from map; see map_unmatched_municipalities.csv.")
map_matched <- semi_join(map_counts, sf::st_drop_geometry(municipal_geometry), by = c("municipality" = "cvegeo"))
map_data <- left_join(municipal_geometry, map_counts, by = c("cvegeo" = "municipality"))
map_data$observation_range <- cut(ifelse(is.na(map_data$n_matrix), 0, map_data$n_matrix),
  breaks = c(-1, 0, 4, 9, 19, 49, Inf),
  labels = c("No observations", "1-4", "5-9", "10-19", "20-49", "50 or more"))
# Mexico Lambert conformal conic projection; simplify only for plotting (100 m tolerance).
map_data <- sf::st_transform(sf::st_make_valid(map_data),
  "+proj=lcc +lat_1=17.5 +lat_2=29.5 +lat_0=12 +lon_0=-102 +datum=WGS84 +units=m +no_defs")
map_data <- sf::st_simplify(map_data, dTolerance = 100, preserveTopology = TRUE)
state_outlines <- map_data %>% group_by(cve_ent) %>% summarise(.groups = "drop")
source_label <- paste(unique(cartographic_sources), collapse = "; ")
coverage_map <- ggplot(map_data) +
  geom_sf(aes(fill = observation_range), color = "#FFFFFF", linewidth = 0.08) +
  geom_sf(data = state_outlines, fill = NA, color = "#627D98", linewidth = 0.22) +
  scale_fill_manual(values = c("No observations" = "#E8EDF2", "1-4" = "#C6DBEF",
      "5-9" = "#9ECAE1", "10-19" = "#6BAED6", "20-49" = "#3182BD", "50 or more" = "#08519C"),
                    drop = FALSE, name = "Number of observations") +
  coord_sf(datum = NA, xlim = c(-2300000, 1700000), ylim = c(200000, 2500000), expand = FALSE) +
  labs(title = "Number of observations by origin municipality",
    subtitle = sprintf("Residence at age 14 | Ages 25-34 | %s municipalities and %s individuals",
                       fmt_n(nrow(map_matched)), fmt_n(sum(map_matched$n_matrix))),
    caption = paste0("Source: authors' calculations, ESRU-EMOVI 2023; INEGI municipal boundaries.\n",
      "Note: Two observations with municipality code 03030 could not be matched to the INEGI boundaries and are excluded from the map.")) +
  guides(fill = guide_legend(ncol = 1, title.position = "top")) +
  theme_void(base_size = 12) + theme(
    plot.title = element_text(size = 22, face = "bold", color = "#102A43", margin = margin(b = 8)),
    plot.subtitle = element_text(size = 14, color = "#486581", margin = margin(b = 12)),
    plot.caption = element_text(size = 10, color = "#627D98", hjust = 0, margin = margin(t = 12)),
    legend.position = "inside", legend.position.inside = c(0.16, 0.28),
    legend.justification = c(0.5, 0.5), legend.background = element_rect(fill = "white", color = NA),
    legend.direction = "vertical", legend.title = element_text(size = 12, face = "bold"), legend.text = element_text(color = "#243B53", size = 12),
    plot.margin = margin(18, 18, 18, 18), plot.background = element_rect(fill = "white", color = NA))
ggsave(file.path(image_dir, "map_origin_municipality_observations.png"), coverage_map,
       device = ragg::agg_png, width = 13, height = 9, dpi = 300, bg = "white")
save_csv(sf::st_drop_geometry(map_data) %>% select(cvegeo, nomgeo, n_matrix, observation_range), "map_municipality_coverage")

if (!is.null(warnings())) capture.output(warnings(), file = file.path(output_dir, "warnings.txt"))
