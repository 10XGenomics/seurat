# Quick Setup - Copy & Paste Into Your Notebook

## Step 1: First Python Cell (Setup & Dashboard)

Copy this entire cell and run it **before any other code**:

```python
# ============================================
# PROFILING SETUP - Run this first!
# ============================================

import subprocess
import sys

# Install required packages
for pkg in ['psutil', 'plotly', 'ipywidgets', 'numpy']:
    try:
        __import__(pkg)
    except ImportError:
        print(f"Installing {pkg}...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', pkg])

# Add notebooks directory to path
sys.path.insert(0, '/mnt/home/stephen.williams/Apps/seurat/notebooks')

# Import profiling tools
from profiling_helpers import setup_notebook_profiling, RCellProfiler
from resource_monitor import get_monitor, get_profiler

# Initialize and display dashboard
print("=" * 60)
print("PROFILING SYSTEM STARTING")
print("=" * 60)
setup_notebook_profiling(gpu_enabled=True)
```

**Output**: You'll see your system specs and a live updating dashboard.

---

## Step 2: Wrap Your R Cells

Before each major R operation, add a Python cell with the profiler context.

### For Loading Data

**Python cell:**
```python
with RCellProfiler("LoadAtera (no molecules)"):
    pass
```

**Then your R cell** (right after):
```R
atera.obj <- LoadAtera(
    data.dir = BUNDLE_PATH,
    fov = "fov",
    assay = "Atera",
    cell.centroids = TRUE,
    molecule.coordinates = FALSE
)
atera.obj
```

### For Normalization

**Python cell:**
```python
with RCellProfiler("Normalize + FindVariableFeatures + ScaleData"):
    pass
```

**Then your R cells:**
```R
atera.obj <- NormalizeData(atera.obj)
atera.obj <- FindVariableFeatures(atera.obj)
atera.obj <- ScaleData(atera.obj)
```

### For PCA & Clustering

**Python cell:**
```python
with RCellProfiler("PCA + Clustering"):
    pass
```

**Then your R cells:**
```R
atera.obj <- RunPCA(atera.obj, npcs = 30)
atera.obj <- FindNeighbors(atera.obj, dims = 1:30)
atera.obj <- FindClusters(atera.obj, resolution = 1.0)
```

### For UMAP

**Python cell:**
```python
with RCellProfiler("UMAP"):
    pass
```

**Then your R cell:**
```R
atera.obj <- RunUMAP(atera.obj, dims = 1:30)
DimPlot(atera.obj, group.by = "seurat_clusters", label = TRUE)
```

---

## Step 3: View Results

The dashboard updates automatically showing:

1. **Real-time metrics**
   - CPU % with color coding (green/yellow/red)
   - RAM % and absolute memory (MB)
   - GPU % if available

2. **Statistics panel**
   - Peak and average for CPU, RAM, GPU
   - Total memory increase since start

3. **Function profiles**
   - Duration, CPU, RAM delta for each profiled operation
   - Shows last 5 operations

4. **Time series chart**
   - CPU and RAM % over last 5 minutes
   - Interactive hover for exact values

5. **Spike detection**
   - Automatic alerts for CPU spikes (>80%)
   - RAM spike detection (>20% increase)

---

## Optional: View Detailed Report

Add this cell anytime to see all profiles so far:

```python
from resource_monitor import get_profiler

profiler = get_profiler()
print(profiler.report())
```

Output:
```
Function Profiling Report
============================================================

LoadAtera (no molecules):
  Duration: 153.03s
  CPU Avg:  18.5%
  RAM Δ:    3245.2 MB

Normalize + FindVariableFeatures + ScaleData:
  Duration: 45.20s
  CPU Avg:  62.3%
  RAM Δ:    512.0 MB

PCA + Clustering:
  Duration: 1513.45s
  CPU Avg:  75.2%
  RAM Δ:    1024.5 MB
```

---

## Optional: Export Data

Add this cell to export all monitoring data:

```python
from resource_monitor import get_monitor
import json

monitor = get_monitor()

data = {
    'statistics': monitor.get_stats(),
    'spikes': monitor.detect_spikes(),
}

print(json.dumps(data, indent=2, default=str))
```

Or click **"Export JSON"** button in the dashboard.

---

## Optional: Reset Between Major Sections

If you want clean measurements for different parts:

```python
from resource_monitor import get_monitor

monitor = get_monitor()
monitor.reset()
print("✓ Monitoring data cleared")
```

---

## What to Look For

### Memory leaks?
- RAM should stabilize after operations
- Check `peak_increase_mb` in statistics
- If growing unbounded, `reset()` and narrow down which step

### CPU bottlenecks?
- Look for long durations with high CPU %
- Compare CPU % across different operations
- GPU % should be high if using GPU acceleration

### Spike detection?
- Dashboard automatically flags spikes
- Check spike timestamp against slow operations
- May indicate swapping or garbage collection

---

## That's It!

Your notebook now has real-time resource monitoring with:
- ✅ Live updating dashboard
- ✅ Line-by-line profiling of major operations
- ✅ Spike detection for sudden resource usage
- ✅ Peak tracking for memory and CPU
- ✅ Export functionality

The monitoring runs in a background thread with minimal overhead (<1% CPU).

---

## Troubleshooting

**Dashboard not showing?**
- Make sure first cell completed successfully
- Check that packages installed: `import psutil`

**GPU not detected?**
- Run `!nvidia-smi` in a cell to check if available
- Set `gpu_enabled=False` in setup if not using

**Need help?**
- See `PROFILING_GUIDE.md` for detailed documentation
- Check docstrings: `help(RCellProfiler)`, `help(setup_notebook_profiling)`

---

**Ready to go!** Run that first cell and watch your resources in real-time. 📊
