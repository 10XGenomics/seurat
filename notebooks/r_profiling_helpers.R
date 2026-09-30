# =============================================================================
# R Profiling Helpers
# Convenience functions for profiling R operations
# =============================================================================

#' Profile a named operation
#'
#' Wrapper around system.time() with automatic resource tracking
#'
#' @param name Character name of operation
#' @param expr Expression to evaluate and profile
#'
#' @export
#' @examples
#' \dontrun{
#' profile_operation("LoadAtera", {
#'   atera.obj <- LoadAtera(...)
#' })
#' }
profile_operation <- function(name, expr) {
  monitor <- get_monitor()

  # Take baseline
  baseline <- monitor$get_latest()
  if (is.null(baseline)) {
    monitor$measure()
    baseline <- monitor$get_latest()
  }

  cat(sprintf("⏱️  Starting: %s\n", name))

  # Time the operation
  timing <- system.time({
    result <- eval(expr, parent.frame())
  })

  # Take final measurement
  monitor$measure()
  final <- monitor$get_latest()

  # Calculate deltas
  ram_delta_mb <- final$ram_mb - baseline$ram_mb
  duration_s <- timing[3]  # elapsed time

  # Get average CPU during operation
  stats <- monitor$get_stats()
  cpu_avg <- stats$cpu$mean

  cat(sprintf("
📊 Profile: %s
   Duration:  %.2f seconds
   CPU avg:   %.1f%%
   RAM Δ:     %+.1f MB
", name, duration_s, cpu_avg, ram_delta_mb))

  if (!is.na(final$gpu_memory_mb) && !is.na(baseline$gpu_memory_mb)) {
    gpu_delta <- final$gpu_memory_mb - baseline$gpu_memory_mb
    cat(sprintf("   GPU Δ:     %+.1f MB\n", gpu_delta))
  }

  cat("\n")

  invisible(result)
}

#' Memory warning context
#'
#' Warn if memory usage exceeds threshold
#'
#' @param threshold_percent RAM usage threshold (default 85)
#'
#' @export
#' @examples
#' \dontrun{
#' with_memory_warning({
#'   heavy_computation()
#' }, threshold_percent = 85)
#' }
with_memory_warning <- function(expr, threshold_percent = 85) {
  monitor <- get_monitor()
  baseline <- monitor$get_latest()

  result <- eval(expr, parent.frame())

  final <- monitor$get_latest()
  if (!is.null(final) && final$ram_percent > threshold_percent) {
    cat(sprintf("⚠️  WARNING: RAM usage at %.1f%% (threshold: %d%%)\n",
                final$ram_percent, threshold_percent))
  }

  invisible(result)
}

#' CPU warning context
#'
#' Warn if peak CPU usage exceeds threshold
#'
#' @param threshold_percent CPU usage threshold (default 90)
#'
#' @export
with_cpu_warning <- function(expr, threshold_percent = 90) {
  monitor <- get_monitor()

  result <- eval(expr, parent.frame())

  stats <- monitor$get_stats()
  if (!is.null(stats) && !is.null(stats$cpu$max)) {
    if (stats$cpu$max > threshold_percent) {
      cat(sprintf("⚠️  WARNING: Peak CPU usage %.1f%% (threshold: %d%%)\n",
                  stats$cpu$max, threshold_percent))
    }
  }

  invisible(result)
}

#' Get profiler report
#'
#' Print a formatted report of all profiled operations
#'
#' @export
print_profiler_report <- function() {
  if (is.null(.profiler_history)) {
    cat("No operations profiled yet.\n")
    return(invisible(NULL))
  }

  cat("═══════════════════════════════════════════════════════════════\n")
  cat("Function Profiling Report\n")
  cat("═══════════════════════════════════════════════════════════════\n\n")

  for (i in seq_along(.profiler_history)) {
    profile <- .profiler_history[[i]]
    cat(sprintf("%d. %s\n", i, profile$name))
    cat(sprintf("   Duration:     %.2f seconds\n", profile$duration))
    cat(sprintf("   CPU avg:      %.1f%%\n", profile$cpu_avg))
    cat(sprintf("   RAM Δ:        %+.1f MB\n", profile$ram_delta_mb))
    if (!is.na(profile$gpu_delta_mb)) {
      cat(sprintf("   GPU Δ:        %+.1f MB\n", profile$gpu_delta_mb))
    }
    cat("\n")
  }
}

#' System information
#'
#' Print system hardware information
#'
#' @export
print_system_info <- function() {
  cat("═══════════════════════════════════════════\n")
  cat("System Information\n")
  cat("═══════════════════════════════════════════\n")

  # CPU cores
  cat(sprintf("CPU Cores: %d\n", parallel::detectCores()))

  # RAM
  if (file.exists("/proc/meminfo")) {
    lines <- readLines("/proc/meminfo")
    total_line <- grep("^MemTotal:", lines, value = TRUE)
    if (length(total_line) > 0) {
      total_kb <- as.numeric(strsplit(total_line, "\\s+")[[1]][2])
      total_gb <- total_kb / (1024 * 1024)
      cat(sprintf("RAM Total: %.1f GB\n", total_gb))
    }
  }

  # R version
  cat(sprintf("R Version: %s\n", paste(R.version$major, R.version$minor, sep = ".")))

  # GPU
  monitor <- get_monitor()
  cat(sprintf("GPU Available: %s\n", ifelse(monitor$gpu_available, "Yes", "No")))

  cat("\n")
}

#' Display live monitoring dashboard
#'
#' Show real-time resource usage statistics
#'
#' @export
show_monitoring_dashboard <- function() {
  monitor <- get_monitor()

  cat("\n")
  cat("╔═══════════════════════════════════════════════════════╗\n")
  cat("║          LIVE RESOURCE MONITORING DASHBOARD           ║\n")
  cat("╚═══════════════════════════════════════════════════════╝\n\n")

  latest <- monitor$get_latest()
  stats <- monitor$get_stats()

  if (is.null(latest)) {
    cat("No measurements yet. Start profiling an operation.\n")
    return(invisible(NULL))
  }

  # Display current values with progress bar representation
  cat("CURRENT VALUES:\n")
  cat(sprintf("  CPU:  %5.1f%% ", latest$cpu_percent))
  private$draw_bar(latest$cpu_percent, 100)
  cat("\n")

  cat(sprintf("  RAM:  %5.1f%% ", latest$ram_percent))
  private$draw_bar(latest$ram_percent, 100)
  cat(sprintf(" [%.0f MB]\n", latest$ram_mb))

  if (!is.na(latest$gpu_percent)) {
    cat(sprintf("  GPU:  %5.1f%% ", latest$gpu_percent))
    private$draw_bar(latest$gpu_percent, 100)
    cat(sprintf(" [%.0f MB]\n", latest$gpu_memory_mb))
  }

  cat("\nSTATISTICS:\n")
  cat(sprintf("  CPU Mean: %.1f%%, Max: %.1f%%, Min: %.1f%%\n",
              stats$cpu$mean, stats$cpu$max, stats$cpu$min))
  cat(sprintf("  RAM Mean: %.1f%%, Max: %.1f%%\n",
              stats$ram$mean_percent, stats$ram$max_percent))
  cat(sprintf("  Peak RAM increase: +%.0f MB\n", stats$ram$peak_increase_mb))

  spikes <- monitor$detect_spikes()
  cat(sprintf("\nSPIKES DETECTED: %d\n", nrow(spikes)))

  cat("\n")
  invisible(NULL)
}

# Helper function to draw progress bar
private <- list()
private$draw_bar <- function(value, max_val, width = 20) {
  filled <- round((value / max_val) * width)
  bar <- paste0(
    "[",
    paste0(rep("█", filled), collapse = ""),
    paste0(rep("░", width - filled), collapse = ""),
    "]"
  )
  cat(bar)
}

#' Reset all monitoring data
#'
#' Clear history and reset baseline
#'
#' @export
reset_monitoring <- function() {
  monitor <- get_monitor()
  monitor$reset()
  cat("✓ Monitoring data cleared\n")
}

#' Setup notebook profiling
#'
#' Complete initialization for notebook profiling
#' Call this once at the start of your notebook
#'
#' @export
#' @examples
#' \dontrun{
#' setup_notebook_profiling()
#' }
setup_notebook_profiling <- function() {
  cat("Initializing R profiling system...\n\n")

  # Check dependencies
  if (!require("R6", quietly = TRUE)) {
    cat("Installing R6...\n")
    install.packages("R6", quiet = TRUE)
    require("R6", quietly = TRUE)
  }

  # Initialize monitoring
  monitor <- init_monitoring()

  # Show system info
  print_system_info()

  # Show initial dashboard
  show_monitoring_dashboard()

  cat("✓ Ready to profile! Use profile_operation() or wrap code with profiling.\n\n")

  invisible(monitor)
}

# Storage for profiler history
.profiler_history <- list()
