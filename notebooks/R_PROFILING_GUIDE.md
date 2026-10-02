# R Resource Monitoring - Complete Guide

Comprehensive resource monitoring system for R-based Jupyter notebooks. **No Python dependencies.**

## Architecture

### Files

- **r_resource_monitor.R** - Core `ResourceMonitor` R6 class
  - System resource measurement via ps, /proc, nvidia-smi
  - History tracking
  - Statistics aggregation
  - Spike detection

- **r_profiling_helpers.R** - Convenience functions
  - `profile_operation()` - wrapper for named profiling
  - `show_monitoring_dashboard()` - live stats display
  - Warning contexts (memory, CPU)
  - Report generation

## Quick Start (see R_SETUP_QUICKSTART.md)

```R
# Setup (first cell)
source("r_resource_monitor.R")
source("r_profiling_helpers.R")
setup_notebook_profiling()

# Use (every major operation)
profile_operation("LoadAtera", {
  atera.obj <- LoadAtera(...)
})

# View
show_monitoring_dashboard()
print_profiler_report()
```

## Core Functions

### Initialization

```R
# One-time setup
setup_notebook_profiling()
# Initializes monitor, shows system info and dashboard

# Or manually
init_monitoring()
```

### Monitoring

```R
# Get global monitor
monitor <- get_monitor()

# Take a measurement
monitor$measure()

# Get latest measurement
latest <- monitor$get_latest()
# Returns: timestamp, cpu_percent, ram_mb, ram_percent, gpu_percent, gpu_memory_mb

# Get history
history <- monitor$get_history()
history <- monitor$get_history(seconds = 60)  # Last 60 seconds

# Get statistics
stats <- monitor$get_stats()
# Returns: count, duration_seconds, cpu, ram, gpu

# Detect spikes
spikes <- monitor$detect_spikes(cpu_threshold = 80)

# Reset
monitor$reset()
```

### Profiling

```R
# Profile a named operation
profile_operation("My Operation", {
  result <- do_something()
})
# Automatically logs duration, CPU avg, RAM delta, GPU delta

# Get profiling report
print_profiler_report()

# Show live dashboard
show_monitoring_dashboard()
```

### Warnings

```R
# Warn if RAM exceeds threshold
with_memory_warning({
  heavy_operation()
}, threshold_percent = 85)

# Warn if peak CPU exceeds threshold
with_cpu_warning({
  cpu_intensive_operation()
}, threshold_percent = 90)
```

### System Info

```R
print_system_info()
# Shows: CPU cores, RAM total, R version, GPU available
```

## ResourceMonitor R6 Class

### Methods

#### `$measure()`
Take a single resource measurement. Returns measurement data frame.

```R
measurement <- monitor$measure()
# timestamp, cpu_percent, ram_mb, ram_percent, gpu_percent, gpu_memory_mb
```

#### `$get_latest()`
Get most recent measurement.

```R
latest <- monitor$get_latest()
cat(sprintf("Current RAM: %.0f MB (%.1f%%)\n", 
            latest$ram_mb, latest$ram_percent))
```

#### `$get_history(seconds = NULL)`
Get measurement history, optionally filtered to last N seconds.

```R
all_history <- monitor$get_history()
recent <- monitor$get_history(seconds = 300)  # Last 5 minutes
```

#### `$get_stats()`
Aggregated statistics: min, max, mean, std dev for CPU/RAM/GPU.

```R
stats <- monitor$get_stats()

# CPU stats
cat(sprintf("CPU: mean=%.1f%%, max=%.1f%%\n",
            stats$cpu$mean, stats$cpu$max))

# RAM stats
cat(sprintf("RAM: peak_increase=%.0f MB\n",
            stats$ram$peak_increase_mb))

# GPU stats (if available)
if (!is.null(stats$gpu)) {
  cat(sprintf("GPU: max=%.1f%%\n", stats$gpu$max))
}
```

#### `$detect_spikes(cpu_threshold = 80)`
Detect sudden resource usage spikes.

```R
spikes <- monitor$detect_spikes(cpu_threshold = 80)

for (i in seq_len(nrow(spikes))) {
  spike <- spikes[i, ]
  cat(sprintf("Spike: %s at %.2f (value: %.1f)\n",
              spike$type, spike$timestamp, spike$value))
}
```

#### `$reset()`
Clear history and reset baseline for clean measurements.

```R
monitor$reset()
# Now get_stats() will measure only from this point
```

#### `$print_summary()`
Print formatted summary of current stats.

```R
monitor$print_summary()
```

### Properties

#### `$history`
Data frame of all measurements.

```R
head(monitor$history)
# timestamp, cpu_percent, ram_mb, ram_percent, gpu_percent, gpu_memory_mb
```

#### `$gpu_available`
Logical: GPU monitoring available?

```R
if (monitor$gpu_available) {
  cat("GPU monitoring enabled\n")
}
```

## Usage Patterns

### Pattern 1: Profile Individual Operations

Best for identifying bottlenecks.

```R
profile_operation("Load data", {
  data <- LoadAtera(...)
})

profile_operation("Normalize", {
  data <- NormalizeData(data)
  data <- FindVariableFeatures(data)
})

profile_operation("PCA", {
  data <- RunPCA(data)
})

print_profiler_report()
```

Output shows duration, CPU, memory delta for each step.

### Pattern 2: Compare Two Approaches

A/B test different methods.

```R
# Method 1
profile_operation("Load without transcripts", {
  obj1 <- LoadAtera(..., molecule.coordinates = FALSE)
})

stats1 <- get_monitor()$get_stats()
reset_monitoring()

# Method 2
profile_operation("Load with transcripts", {
  obj2 <- LoadAtera(..., molecule.coordinates = TRUE)
})

stats2 <- get_monitor()$get_stats()

# Compare:
cat(sprintf("Method 1 peak RAM: %.0f MB\n", stats1$ram$peak_increase_mb))
cat(sprintf("Method 2 peak RAM: %.0f MB\n", stats2$ram$peak_increase_mb))
```

### Pattern 3: Watch for Resource Leaks

Monitor memory over time.

```R
for (i in 1:10) {
  cat(sprintf("Iteration %d: ", i))
  profile_operation(sprintf("Iteration %d", i), {
    result <- do_operation()
  })
  
  stats <- get_monitor()$get_stats()
  cat(sprintf("Current RAM: %.0f MB\n", stats$ram$current_mb))
}

# If RAM keeps growing, you have a leak
print_profiler_report()
```

### Pattern 4: Detect Bottlenecks

Long duration + low CPU = I/O bound. Long duration + high CPU = CPU bound.

```R
profile_operation("Data loading (I/O)", {
  data <- readRDS("large_file.rds")  # Low CPU, high disk I/O
})

profile_operation("Matrix computation (CPU)", {
  result <- t(data) %*% data  # High CPU
})

# Check report to see CPU % for each
print_profiler_report()
```

## Advanced Usage

### Manual Measurement Loop

For custom tracking:

```R
monitor <- get_monitor()

# Take measurements over time
for (i in 1:100) {
  monitor$measure()
  Sys.sleep(0.1)
}

# Analyze
history <- monitor$get_history()
plot(history$timestamp, history$cpu_percent, type = 'l',
     main = "CPU Usage", xlab = "Time", ylab = "CPU %")
```

### Spike Analysis

Find what caused spikes:

```R
monitor$reset()

# Run workflow
profile_operation("Full workflow", {
  # ... all operations ...
})

# Analyze spikes
spikes <- monitor$detect_spikes(cpu_threshold = 75)

if (nrow(spikes) > 0) {
  cat(sprintf("Found %d spikes:\n", nrow(spikes)))
  print(spikes)
  
  # Timestamps tell you when to investigate
  for (spike_time in spikes$timestamp) {
    cat(sprintf("Spike at %.2f - check your logs\n", spike_time))
  }
}
```

### Memory Delta Tracking

Track memory changes between operations:

```R
# Get baseline
baseline_mb <- get_monitor()$get_latest()$ram_mb

profile_operation("Heavy operation", {
  result <- do_work()
})

final_mb <- get_monitor()$get_latest()$ram_mb
delta_mb <- final_mb - baseline_mb

cat(sprintf("Memory increase: %.0f MB\n", delta_mb))

if (delta_mb > 1000) {
  cat("⚠️  Large memory allocation detected\n")
}
```

### Multi-step Profiling

Profile a complex workflow step by step:

```R
# Don't reset - accumulate all measurements
profile_operation("Step 1: Load", { ... })
profile_operation("Step 2: QC", { ... })
profile_operation("Step 3: Normalize", { ... })
profile_operation("Step 4: PCA", { ... })
profile_operation("Step 5: Cluster", { ... })

# View complete timeline
show_monitoring_dashboard()
print_profiler_report()

# Get overall stats
overall <- get_monitor()$get_stats()
cat(sprintf("Total duration: %.0f seconds\n", overall$duration_seconds))
cat(sprintf("Total RAM increase: %.0f MB\n", overall$ram$peak_increase_mb))
```

## Interpreting Results

### CPU %
- **Mean < 20%**: I/O bound, waiting on disk/network
- **Mean 40-70%**: Well-balanced workload
- **Mean > 80%**: CPU saturated

### RAM
- **Linear growth**: Expected (loading data, storing results)
- **Sudden spikes**: Temporary arrays or matrices
- **Never decreases**: Possible memory leak

### GPU
- **0%**: Not using GPU, or operation doesn't support it
- **50-100%**: GPU is working
- **100% but slow**: May be memory-bound (check memory %)

### Spikes
- **CPU spike**: Sudden computation load
- **RAM spike**: Large temporary allocation
- **Repeating**: Pattern detection - may indicate inefficiency

## Troubleshooting

### RAM showing 0%?
- System may not expose memory info via /proc
- Check: `file.exists("/proc/meminfo")`
- Try: `cat /proc/meminfo` in terminal

### GPU not detected?
```R
# Check nvidia-smi
system("nvidia-smi --version")

monitor <- get_monitor()
monitor$gpu_available  # Should be TRUE if working
```

### CPU % seems wrong?
- Measuring per-process CPU (not system-wide)
- `ps` may report differently on some systems
- Cross-check with system tools: `top`, `htop`

### History growing too large?
```R
# History is capped at buffer_size (default 1000)
# Each measurement ~ 50 bytes
# 1000 samples = ~50 KB

monitor$reset()  # Clear history
```

## Performance

Overhead of monitoring system:
- **CPU**: <1% (background measurement thread sleeps 90% of time)
- **Memory**: ~50 KB for 1000 measurements
- **I/O**: Minimal (only reads /proc and runs ps occasionally)

Safe to leave running throughout entire notebook.

## Tips for Large Dataset Processing

1. **Profile incrementally**: Load → Normalize → PCA → Clustering
2. **Watch memory**: Should stabilize after each step
3. **Compare approaches**: Use reset() between A/B tests
4. **Detect patterns**: Run multiple iterations, look for leaks
5. **Export for analysis**: Save history for external analysis

```R
# Export history to CSV
history <- get_monitor()$get_history()
write.csv(history, "monitoring_history.csv", row.names = FALSE)

# Export stats to JSON
stats <- get_monitor()$get_stats()
jsonlite::write_json(stats, "monitoring_stats.json")
```

## Example: Complete Atera Workflow Analysis

```R
# Setup
source("r_resource_monitor.R")
source("r_profiling_helpers.R")
setup_notebook_profiling()

BUNDLE_PATH <- "..."

# Profile each step
profile_operation("LoadAtera", {
  atera.obj <- LoadAtera(data.dir = BUNDLE_PATH, ...)
})

profile_operation("Normalize", {
  atera.obj <- NormalizeData(atera.obj)
  atera.obj <- FindVariableFeatures(atera.obj)
  atera.obj <- ScaleData(atera.obj)
})

profile_operation("PCA", {
  atera.obj <- RunPCA(atera.obj, npcs = 30)
})

profile_operation("Clustering", {
  atera.obj <- FindNeighbors(atera.obj, dims = 1:30)
  atera.obj <- FindClusters(atera.obj, resolution = 1.0)
})

profile_operation("UMAP", {
  atera.obj <- RunUMAP(atera.obj, dims = 1:30)
})

# Summary
show_monitoring_dashboard()
print_profiler_report()

# Analysis
spikes <- get_monitor()$detect_spikes()
cat(sprintf("Total spikes: %d\n", nrow(spikes)))

stats <- get_monitor()$get_stats()
cat(sprintf("Total workflow time: %.0f seconds\n", stats$duration_seconds))
cat(sprintf("Peak memory increase: %.0f MB\n", stats$ram$peak_increase_mb))
```

---

**Ready to profile!** Start with R_SETUP_QUICKSTART.md or dive into any section above. 📊
