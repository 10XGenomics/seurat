# =============================================================================
# Pure R Resource Monitoring System
# Track CPU, RAM, GPU usage without Python dependencies
# =============================================================================

#' R6 Class: ResourceMonitor
#'
#' Real-time resource monitoring using system commands (ps, /proc, nvidia-smi)
#'
#' @export
ResourceMonitor <- R6::R6Class(
  "ResourceMonitor",
  public = list(
    history = NULL,
    start_time = NULL,
    baseline_ram_mb = NULL,
    gpu_available = FALSE,
    buffer_size = 1000,

    #' Initialize
    #' @param buffer_size Maximum number of measurements to keep in history
    initialize = function(buffer_size = 1000) {
      self$history <- data.frame(
        timestamp = numeric(),
        cpu_percent = numeric(),
        ram_mb = numeric(),
        ram_percent = numeric(),
        gpu_percent = numeric(),
        gpu_memory_mb = numeric()
      )
      self$buffer_size <- buffer_size
      self$start_time <- Sys.time()
      self$baseline_ram_mb <- private$get_ram_mb()
      self$gpu_available <- private$check_gpu()
    },

    #' Take a resource measurement
    measure = function() {
      ts <- as.numeric(Sys.time())
      cpu <- private$get_cpu_percent()
      ram_mb <- private$get_ram_mb()
      ram_pct <- private$get_ram_percent()

      gpu_pct <- NA_real_
      gpu_mem <- NA_real_

      if (self$gpu_available) {
        gpu_data <- private$get_gpu_stats()
        gpu_pct <- gpu_data$percent
        gpu_mem <- gpu_data$memory_mb
      }

      new_row <- data.frame(
        timestamp = ts,
        cpu_percent = cpu,
        ram_mb = ram_mb,
        ram_percent = ram_pct,
        gpu_percent = gpu_pct,
        gpu_memory_mb = gpu_mem
      )

      self$history <- rbind(self$history, new_row)

      # Keep buffer size reasonable
      if (nrow(self$history) > self$buffer_size) {
        self$history <- self$history[-(1:(nrow(self$history) - self$buffer_size)), ]
      }

      invisible(new_row)
    },

    #' Get latest measurement
    get_latest = function() {
      if (nrow(self$history) == 0) return(NULL)
      self$history[nrow(self$history), ]
    },

    #' Get history from last N seconds
    get_history = function(seconds = NULL) {
      if (nrow(self$history) == 0) return(NULL)

      if (is.null(seconds)) {
        return(self$history)
      }

      cutoff_time <- as.numeric(Sys.time()) - seconds
      self$history[self$history$timestamp >= cutoff_time, ]
    },

    #' Get aggregated statistics
    get_stats = function() {
      if (nrow(self$history) == 0) return(list())

      cpu_vals <- self$history$cpu_percent
      ram_vals <- self$history$ram_percent
      ram_mb_vals <- self$history$ram_mb

      stats <- list(
        count = nrow(self$history),
        duration_seconds = as.numeric(Sys.time()) - as.numeric(self$start_time),
        cpu = list(
          current = cpu_vals[length(cpu_vals)],
          mean = mean(cpu_vals, na.rm = TRUE),
          max = max(cpu_vals, na.rm = TRUE),
          min = min(cpu_vals, na.rm = TRUE),
          sd = sd(cpu_vals, na.rm = TRUE)
        ),
        ram = list(
          current_mb = ram_mb_vals[length(ram_mb_vals)],
          current_percent = ram_vals[length(ram_vals)],
          mean_percent = mean(ram_vals, na.rm = TRUE),
          max_percent = max(ram_vals, na.rm = TRUE),
          peak_increase_mb = ram_mb_vals[length(ram_mb_vals)] - self$baseline_ram_mb
        )
      )

      # GPU stats if available
      if (self$gpu_available) {
        gpu_vals <- self$history$gpu_percent[!is.na(self$history$gpu_percent)]
        gpu_mem_vals <- self$history$gpu_memory_mb[!is.na(self$history$gpu_memory_mb)]

        if (length(gpu_vals) > 0) {
          stats$gpu <- list(
            current = gpu_vals[length(gpu_vals)],
            mean = mean(gpu_vals, na.rm = TRUE),
            max = max(gpu_vals, na.rm = TRUE),
            memory_mb_peak = max(gpu_mem_vals, na.rm = TRUE)
          )
        }
      }

      stats
    },

    #' Detect resource usage spikes
    detect_spikes = function(cpu_threshold = 80) {
      if (nrow(self$history) < 2) return(data.frame())

      spikes <- list()

      # CPU spikes
      cpu_vals <- self$history$cpu_percent
      for (i in 2:length(cpu_vals)) {
        if (cpu_vals[i] > cpu_threshold && (i == 2 || cpu_vals[i-1] <= cpu_threshold)) {
          spikes[[length(spikes) + 1]] <- data.frame(
            type = "cpu",
            timestamp = self$history$timestamp[i],
            value = cpu_vals[i],
            threshold = cpu_threshold
          )
        }
      }

      # RAM spikes (20% increase detection)
      ram_vals <- self$history$ram_mb
      if (length(ram_vals) > 10) {
        recent_baseline <- mean(ram_vals[max(1, length(ram_vals)-20):max(1, length(ram_vals)-10)])
        for (i in 11:length(ram_vals)) {
          if (ram_vals[i] > recent_baseline * 1.2) {
            spikes[[length(spikes) + 1]] <- data.frame(
              type = "ram",
              timestamp = self$history$timestamp[i],
              value = ram_vals[i],
              increase_pct = ((ram_vals[i] - recent_baseline) / recent_baseline) * 100
            )
          }
        }
      }

      if (length(spikes) == 0) {
        return(data.frame())
      }

      do.call(rbind, spikes)
    },

    #' Reset monitoring data
    reset = function() {
      self$history <- data.frame(
        timestamp = numeric(),
        cpu_percent = numeric(),
        ram_mb = numeric(),
        ram_percent = numeric(),
        gpu_percent = numeric(),
        gpu_memory_mb = numeric()
      )
      self$baseline_ram_mb <- private$get_ram_mb()
      self$start_time <- Sys.time()
    },

    #' Print a summary of current stats
    print_summary = function() {
      stats <- self$get_stats()

      cat("═══════════════════════════════════════════\n")
      cat("Resource Monitoring Summary\n")
      cat("═══════════════════════════════════════════\n")

      if (length(stats) == 0) {
        cat("No measurements yet.\n")
        return(invisible(stats))
      }

      cat(sprintf("Duration: %.1f seconds\n", stats$duration_seconds))
      cat(sprintf("Samples: %d\n\n", stats$count))

      cat("CPU Usage:\n")
      cat(sprintf("  Current: %.1f%%\n", stats$cpu$current))
      cat(sprintf("  Mean:    %.1f%%\n", stats$cpu$mean))
      cat(sprintf("  Max:     %.1f%%\n", stats$cpu$max))
      cat(sprintf("  StdDev:  %.1f%%\n\n", stats$cpu$sd))

      cat("RAM Usage:\n")
      cat(sprintf("  Current:  %.0f MB (%.1f%%)\n", stats$ram$current_mb, stats$ram$current_percent))
      cat(sprintf("  Mean:     %.1f%%\n", stats$ram$mean_percent))
      cat(sprintf("  Max:      %.1f%%\n", stats$ram$max_percent))
      cat(sprintf("  Peak Δ:   +%.0f MB\n\n", stats$ram$peak_increase_mb))

      if (!is.null(stats$gpu)) {
        cat("GPU Usage:\n")
        cat(sprintf("  Current: %.1f%%\n", stats$gpu$current))
        cat(sprintf("  Mean:    %.1f%%\n", stats$gpu$mean))
        cat(sprintf("  Max:     %.1f%%\n", stats$gpu$max))
        cat(sprintf("  Peak Memory: %.0f MB\n\n", stats$gpu$memory_mb_peak))
      }

      spikes <- self$detect_spikes()
      cat(sprintf("Spikes Detected: %d\n", nrow(spikes)))

      invisible(stats)
    }
  ),

  private = list(
    #' Get current CPU percentage using ps command
    get_cpu_percent = function() {
      tryCatch({
        # Get CPU usage for current process
        pid <- Sys.getpid()
        cmd <- sprintf("ps -p %d -o %%cpu= 2>/dev/null", pid)
        result <- system(cmd, intern = TRUE)

        if (length(result) == 0 || result == "") {
          return(0)
        }

        as.numeric(trimws(result))
      }, error = function(e) 0)
    },

    #' Get current RAM usage in MB for current process
    get_ram_mb = function() {
      tryCatch({
        pid <- Sys.getpid()

        # Try /proc first (Linux)
        proc_file <- sprintf("/proc/%d/status", pid)
        if (file.exists(proc_file)) {
          content <- readLines(proc_file)
          rss_line <- grep("^VmRSS:", content, value = TRUE)
          if (length(rss_line) > 0) {
            kb <- as.numeric(strsplit(rss_line, "\\s+")[[1]][2])
            return(kb / 1024)  # Convert KB to MB
          }
        }

        # Fallback: use ps command
        cmd <- sprintf("ps -p %d -o rss= 2>/dev/null", pid)
        result <- system(cmd, intern = TRUE)
        if (length(result) > 0 && result != "") {
          kb <- as.numeric(trimws(result))
          return(kb / 1024)  # Convert KB to MB
        }

        return(0)
      }, error = function(e) 0)
    },

    #' Get system RAM percentage
    get_ram_percent = function() {
      tryCatch({
        # Try /proc/meminfo (Linux)
        if (file.exists("/proc/meminfo")) {
          lines <- readLines("/proc/meminfo")
          total_line <- grep("^MemTotal:", lines, value = TRUE)
          avail_line <- grep("^MemAvailable:", lines, value = TRUE)

          if (length(total_line) > 0 && length(avail_line) > 0) {
            total_kb <- as.numeric(strsplit(total_line, "\\s+")[[1]][2])
            avail_kb <- as.numeric(strsplit(avail_line, "\\s+")[[1]][2])
            used_kb <- total_kb - avail_kb
            return((used_kb / total_kb) * 100)
          }
        }

        return(0)
      }, error = function(e) 0)
    },

    #' Check if GPU is available via nvidia-smi
    check_gpu = function() {
      tryCatch({
        result <- system("nvidia-smi --version", intern = TRUE, ignore.stderr = TRUE)
        length(result) > 0
      }, error = function(e) FALSE)
    },

    #' Get GPU stats
    get_gpu_stats = function() {
      tryCatch({
        # Query first GPU
        cmd <- "nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader,nounits -i 0"
        result <- system(cmd, intern = TRUE, ignore.stderr = TRUE)

        if (length(result) == 0 || result == "") {
          return(list(percent = NA_real_, memory_mb = NA_real_))
        }

        parts <- strsplit(trimws(result), ",")[[1]]
        gpu_pct <- as.numeric(trimws(parts[1]))
        gpu_mem_mb <- as.numeric(trimws(parts[2]))

        list(percent = gpu_pct, memory_mb = gpu_mem_mb)
      }, error = function(e) {
        list(percent = NA_real_, memory_mb = NA_real_)
      })
    }
  )
)

# Global monitor instance
.global_monitor <- NULL

#' Get or initialize global monitor
#' @export
get_monitor <- function() {
  if (is.null(.global_monitor)) {
    if (!require("R6", quietly = TRUE)) {
      stop("R6 package required. Install with: install.packages('R6')")
    }
    assign(".global_monitor", ResourceMonitor$new(), envir = parent.env(environment()))
  }
  get(".global_monitor", envir = parent.env(environment()))
}

#' Initialize monitoring system
#' @export
init_monitoring <- function() {
  if (!require("R6", quietly = TRUE)) {
    install.packages("R6")
    require("R6", quietly = TRUE)
  }

  monitor <- get_monitor()
  cat("✓ Resource monitoring initialized\n")
  cat(sprintf("  GPU available: %s\n", ifelse(monitor$gpu_available, "Yes", "No")))

  invisible(monitor)
}
