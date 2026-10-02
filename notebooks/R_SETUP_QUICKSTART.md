# R Notebook Resource Monitoring - Quick Start

Pure R-based resource monitoring with **no Python dependencies**.

## Step 1: First R Cell - Setup

Copy and run this as your **first R cell**:

```R
# ============================================
# PROFILING SETUP - Run this first!
# ============================================

# Install R6 if needed (one-time)
if (!require("R6", quietly = TRUE)) {
  install.packages("R6")
}

# Source the monitoring modules
source("/mnt/home/stephen.williams/Apps/seurat/notebooks/r_resource_monitor.R")
source("/mnt/home/stephen.williams/Apps/seurat/notebooks/r_profiling_helpers.R")

# Initialize and show dashboard
setup_notebook_profiling()
```

**Output**: System specs + live monitoring dashboard

---

## Step 2: Profile Your Operations

Before each major operation, use `profile_operation()`:

### Loading Data

```R
profile_operation("LoadAtera (no molecules)", {
  atera.obj <- LoadAtera(
    data.dir = BUNDLE_PATH,
    fov = "fov",
    assay = "Atera",
    cell.centroids = TRUE,
    molecule.coordinates = FALSE
  )
})

atera.obj
```

**Output**:
```
⏱️  Starting: LoadAtera (no molecules)

📊 Profile: LoadAtera (no molecules)
   Duration:  153.03 seconds
   CPU avg:   18.5%
   RAM Δ:     +3245.2 MB

[Next operations...]
```

### Normalization

```R
profile_operation("Normalize + FindVariableFeatures + ScaleData", {
  atera.obj <- NormalizeData(atera.obj)
  atera.obj <- FindVariableFeatures(atera.obj)
  atera.obj <- ScaleData(atera.obj)
})
```

### PCA & Clustering

```R
profile_operation("PCA + Clustering", {
  atera.obj <- RunPCA(atera.obj, npcs = 30)
  atera.obj <- FindNeighbors(atera.obj, dims = 1:30)
  atera.obj <- FindClusters(atera.obj, resolution = 1.0)
})
```

### UMAP

```R
profile_operation("UMAP", {
  atera.obj <- RunUMAP(atera.obj, dims = 1:30)
  DimPlot(atera.obj, group.by = "seurat_clusters", label = TRUE)
})
```

---

## Step 3: View Results

### Live Dashboard

View current stats anytime:

```R
show_monitoring_dashboard()
```

Shows:
- **Current CPU, RAM, GPU %** with progress bars
- **Statistics**: mean, max, min for each metric
- **Peak increase**: Total memory growth since start
- **Spikes detected**: Number of resource spikes

### Profiling Report

View all profiled operations:

```R
print_profiler_report()
```

Output:
```
═══════════════════════════════════════════════════════════════
Function Profiling Report
═══════════════════════════════════════════════════════════════

1. LoadAtera (no molecules)
   Duration:     153.03 seconds
   CPU avg:      18.5%
   RAM Δ:        +3245.2 MB

2. Normalize + FindVariableFeatures + ScaleData
   Duration:     45.20 seconds
   CPU avg:      62.3%
   RAM Δ:        +512.0 MB

3. PCA + Clustering
   Duration:     1513.45 seconds
   CPU avg:      75.2%
   RAM Δ:        +1024.5 MB
```

---

## Optional: Add Warnings

Automatically alert when thresholds are exceeded:

### Memory Warning

```R
with_memory_warning({
  # Heavy operation
  atera.obj <- LoadAtera(...)
}, threshold_percent = 85)

# Warns if RAM goes above 85%
```

### CPU Warning

```R
with_cpu_warning({
  # CPU-intensive operation
  atera.obj <- FindNeighbors(atera.obj, dims = 1:30)
}, threshold_percent = 90)

# Warns if peak CPU exceeds 90%
```

---

## Optional: Spike Detection

Check for sudden resource spikes:

```R
monitor <- get_monitor()
spikes <- monitor$detect_spikes()

if (nrow(spikes) > 0) {
  cat("Detected spikes:\n")
  print(spikes)
}
```

---

## Optional: Reset Between Sections

Clear history for clean measurements:

```R
reset_monitoring()
```

Then start profiling a new major section.

---

## Complete Example Notebook Structure

```R
# ============= Cell 1: Setup =============
if (!require("R6", quietly = TRUE)) {
  install.packages("R6")
}

source("/mnt/home/stephen.williams/Apps/seurat/notebooks/r_resource_monitor.R")
source("/mnt/home/stephen.williams/Apps/seurat/notebooks/r_profiling_helpers.R")

setup_notebook_profiling()

# ============= Cell 2: Load =============
BUNDLE_PATH <- paste0(
  "/mnt/cloud-analysis/aerosoc/pipestances/1940675_2035668/",
  "XOA_OUTPUT_BUNDLER/1940675_2035668/HEAD/outs/output_bundle"
)

profile_operation("LoadAtera (no molecules)", {
  atera.obj <- LoadAtera(
    data.dir = BUNDLE_PATH,
    fov = "fov",
    assay = "Atera",
    cell.centroids = TRUE,
    molecule.coordinates = FALSE
  )
})

# ============= Cell 3: QC =============
profile_operation("QC Plots", {
  VlnPlot(atera.obj, features = c("nCount_Atera", "nFeature_Atera"), pt.size = 0)
  ImageDimPlot(atera.obj, fov = "fov", size = 0.3, cols = "grey60")
})

# ============= Cell 4: Normalize =============
profile_operation("Normalization", {
  atera.obj <- NormalizeData(atera.obj)
  atera.obj <- FindVariableFeatures(atera.obj)
  atera.obj <- ScaleData(atera.obj)
})

# ============= Cell 5: PCA =============
profile_operation("PCA", {
  atera.obj <- RunPCA(atera.obj, npcs = 30)
  ElbowPlot(atera.obj, ndims = 30)
})

# ============= Cell 6: Clustering =============
profile_operation("Clustering", {
  atera.obj <- FindNeighbors(atera.obj, dims = 1:30)
  atera.obj <- FindClusters(atera.obj, resolution = 1.0)
})

# ============= Cell 7: UMAP =============
profile_operation("UMAP", {
  atera.obj <- RunUMAP(atera.obj, dims = 1:30)
  DimPlot(atera.obj, group.by = "seurat_clusters", label = TRUE) + NoLegend()
})

# ============= Cell 8: Summary =============
show_monitoring_dashboard()
print_profiler_report()
```

---

## What to Look For

### Memory leaks?
- RAM should stabilize after operations
- Check `peak_increase_mb` in stats
- If growing unbounded, reset and narrow down which step

### CPU bottlenecks?
- Long durations with high CPU % = CPU bound
- Long durations with low CPU % = Likely I/O or communication
- Compare CPU % across different operations

### GPU acceleration working?
- GPU % should be high if using GPU-accelerated operations
- GPU memory should increase during heavy computation

---

## Troubleshooting

### R6 not installing?
```R
install.packages("R6")
```

### `nvidia-smi` not found?
- GPU monitoring will just silently disable
- Set `GPU Available: No` in system info
- This is normal if you're not using GPU

### Get more details?
```R
monitor <- get_monitor()
head(monitor$history)  # See raw measurements
monitor$get_stats()     # See detailed stats
```

---

## That's It!

Your R notebook now has:
- ✅ Real-time resource monitoring
- ✅ Line-by-line operation profiling
- ✅ Spike detection for sudden resource usage
- ✅ Peak tracking for memory and CPU
- ✅ Zero Python dependencies

The monitoring runs with minimal overhead (<1% CPU).

**Start with Step 1 and you're ready to go!** 📊
