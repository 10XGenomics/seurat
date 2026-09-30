# Jupyter Notebook Resource Monitoring Guide

Complete system for real-time CPU, RAM, and GPU monitoring with spike detection for your Atera analysis notebook.

## Quick Start (2 minutes)

### 1. Add Setup Cell (at beginning of notebook)

Add this as your **first Python cell** before any R code:

```python
# Install dependencies if needed
import subprocess
import sys

for pkg in ['psutil', 'plotly', 'ipywidgets', 'numpy']:
    try:
        __import__(pkg)
    except ImportError:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', pkg])

# Import and initialize profiling
import sys
sys.path.insert(0, '/mnt/home/stephen.williams/Apps/seurat/notebooks')

from profiling_helpers import setup_notebook_profiling

# Start monitoring
setup_notebook_profiling(gpu_enabled=True)
```

This will:
- Check and install required packages
- Display your system specifications
- Start background resource monitoring
- Show a live dashboard

### 2. Profile Your R Cells

Wrap heavy operations with the profiler:

```python
# Before your R LoadAtera cell
from profiling_helpers import RCellProfiler

# Python cell before R code
with RCellProfiler("Load Atera (no molecules)"):
    pass  # The profiler tracks time; R code runs separately
```

Then run your R cell:

```R
# Actual R code - this gets profiled
atera.obj <- LoadAtera(
    data.dir = BUNDLE_PATH,
    fov = "fov",
    assay = "Atera",
    cell.centroids = TRUE,
    molecule.coordinates = FALSE
)
```

### 3. View Results

The dashboard automatically updates showing:
- **Current CPU, RAM, GPU usage** with color-coded progress bars
- **Peak and average statistics** for the monitoring session
- **Spike detection** for sudden resource spikes
- **Function profiles** with resource delta for each profiled operation
- **Time series chart** of last 5 minutes (if Plotly available)

## Features

### Live Dashboard

Displays in real-time:
- CPU % (current, mean, max, std dev)
- RAM % and absolute memory (MB)
- GPU % and memory if available
- Peak RAM increase since baseline
- Number of detected spikes
- Last 5 function profiles executed

### Spike Detection

Automatically detects:
- **CPU spikes**: Usage jumps above 80% threshold
- **RAM spikes**: Sudden 20%+ increase in memory

View spikes in dashboard or programmatically:

```python
from resource_monitor import get_monitor

monitor = get_monitor()
spikes = monitor.detect_spikes(threshold_percent=80)
for spike in spikes:
    print(f"{spike['type'].upper()}: {spike['value']:.1f}% at {spike['timestamp']}")
```

### Function Profiling

Track resource usage of Python functions:

```python
from profiling_helpers import profile_function

@profile_function
def my_preprocessing_step():
    # Heavy computation
    pass

# Will automatically be profiled and logged
my_preprocessing_step()
```

View all profiles:

```python
from resource_monitor import get_profiler

profiler = get_profiler()
print(profiler.report())
```

### Manual Profiling Context

For R operations or complex workflows:

```python
from profiling_helpers import RCellProfiler

with RCellProfiler("Normalize + FindVariableFeatures"):
    # R code executes here - resources are tracked
    # You can also put Python code here
    pass
```

Outputs:
```
⏱️  Starting profile: Normalize + FindVariableFeatures
📊 Profile: Normalize + FindVariableFeatures
   Duration: 245.32s
   CPU avg: 45.3%
   RAM Δ: 2048.5 MB
   GPU Δ: 512.3 MB
```

### Memory/CPU Warnings

Automatically warn when thresholds are exceeded:

```python
from profiling_helpers import MemoryWarning, CPUWarning

# Warn if RAM goes above 85%
with MemoryWarning(threshold_percent=85):
    # Heavy operation
    pass

# Warn if peak CPU exceeds 90%
with CPUWarning(threshold_percent=90):
    # CPU-intensive operation
    pass
```

### Export Data

Export monitoring data for analysis:

```python
from resource_monitor import get_monitor

monitor = get_monitor()
history = monitor.get_history()
stats = monitor.get_stats()
spikes = monitor.detect_spikes()

# Data is in dicts/lists, easily serializable
import json
with open('monitoring_data.json', 'w') as f:
    json.dump({
        'stats': stats,
        'spikes': spikes,
        'history': [h.to_dict() for h in history]
    }, f, indent=2, default=str)
```

Also use dashboard's "Export JSON" button for one-click export.

### System Information

View your system specs:

```python
from profiling_helpers import print_system_info, get_system_info

# Print to console
print_system_info()

# Get as dict
info = get_system_info()
print(f"RAM: {info['ram_total_gb']:.1f} GB")
print(f"CPU cores: {info['cpu_cores']}")
```

## Integration with Your Atera Notebook

Here's how to structure your notebook:

### Cell 1: Setup & Monitoring
```python
import subprocess, sys
for pkg in ['psutil', 'plotly', 'ipywidgets', 'numpy']:
    try: __import__(pkg)
    except: subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', pkg])

sys.path.insert(0, '/mnt/home/stephen.williams/Apps/seurat/notebooks')
from profiling_helpers import setup_notebook_profiling, RCellProfiler
setup_notebook_profiling(gpu_enabled=True)
```

### Cell 2: Load Atera
```python
with RCellProfiler("Load Atera (no molecules)"):
    pass
```

Then your R cell with LoadAtera()

### Cell 3: Profile Normalization
```python
with RCellProfiler("Normalize + FindVariableFeatures + ScaleData"):
    pass
```

Then your R cells with those operations

### Cell 4: Profile PCA + Clustering
```python
with RCellProfiler("PCA + FindNeighbors + FindClusters"):
    pass
```

Then your R cells

This gives you a clear timeline and resource breakdown for each major step.

## Advanced Usage

### Custom Monitoring Window

Monitor just a specific time range:

```python
from resource_monitor import get_monitor

monitor = get_monitor()

# Get history from last 60 seconds
recent_history = monitor.get_history(seconds=60)
print(f"Captured {len(recent_history)} measurements")
```

### Real-time Spike Checking

Hook up alerts to spike detection:

```python
from resource_monitor import get_monitor
import time

monitor = get_monitor()

while True:
    spikes = monitor.detect_spikes(threshold_percent=80)
    if spikes:
        latest_spike = spikes[-1]
        print(f"⚠️  Spike detected: {latest_spike}")
    time.sleep(5)
```

### Reset Between Operations

Clear monitoring history when starting a new major operation:

```python
from resource_monitor import get_monitor

monitor = get_monitor()

# ... some work ...
print(monitor.get_stats())

# Reset for clean comparison
monitor.reset()

# ... more work ...
print(monitor.get_stats())  # Only measures from reset point
```

### Custom Dashboard Interval

Update dashboard faster or slower:

```python
from monitoring_dashboard import show_dashboard

# Update every 0.5 seconds (more responsive)
dashboard = show_dashboard(update_interval=0.5)

# ... do work ...

# Stop when done
dashboard.stop()
```

## Troubleshooting

### Dashboard not updating?
- Ensure the monitoring thread is running: `get_monitor().running` should be `True`
- Check browser console for Plotly errors
- Try refreshing the notebook cell

### GPU monitoring not working?
- Ensure `nvidia-smi` works: `!nvidia-smi` in a cell
- Install pynvml: `pip install pynvml`
- Set `gpu_enabled=False` in setup if GPU not needed

### High overhead from monitoring?
- Increase sampling interval: modify `self.interval` in `ResourceMonitor` (default 0.1s)
- Reduce chart history: modify seconds parameter in `_update_chart()` (default 300s)
- Disable GPU monitoring if not using: `gpu_enabled=False`

### Memory keeps growing?
- Check history buffer size is reasonable (default 1000 samples = ~100 seconds)
- Call `monitor.reset()` periodically to clear old data
- Monitor memory with: `print(len(list(monitor.history)))`

## Performance Impact

Typical overhead:
- **CPU**: <1% (thread sleeps between samples)
- **Memory**: ~5-10 MB for 1000 sample history
- **GPU**: Minimal if `gpu_enabled=False`

For minimal overhead with large datasets:
```python
from resource_monitor import ResourceMonitor
monitor = ResourceMonitor(buffer_size=500)  # Fewer samples
monitor.interval = 0.5  # Sample every 500ms instead of 100ms
```

## File Structure

```
notebooks/
├── atera_exploration.ipynb       # Your notebook
├── resource_monitor.py           # Core monitoring engine
├── monitoring_dashboard.py       # Live dashboard widget
├── profiling_helpers.py          # Convenience utilities
└── PROFILING_GUIDE.md           # This file
```

## Dependencies

- **psutil**: System resource monitoring (CPU, RAM)
- **numpy**: Statistics calculations
- **pynvml**: GPU monitoring (optional, auto-detected)
- **plotly**: Interactive charts (optional)
- **ipywidgets**: Dashboard UI (optional)

All auto-installed by setup cell if missing.

## Tips for Large Dataset Processing

1. **Profile incrementally**: Load → Normalize → PCA → Clustering, one step at a time with profiling
2. **Watch for memory creep**: RAM should stabilize, not continuously increase
3. **Detect bottlenecks**: Look for long durations + high CPU without proportional compute
4. **GPU tracking**: If using GPU acceleration, watch GPU memory for leaks
5. **Export data**: Save profiles after each major operation for comparison

## Examples

### Example 1: Find memory bottleneck
```python
with RCellProfiler("Loading large transcript data"):
    pass
# Returns: Duration: 312.45s, Δ RAM: 8456.2 MB
# → You found the heavy operation
```

### Example 2: Monitor whole workflow
```python
with RCellProfiler("Complete Seurat workflow"):
    # All your R code goes here via separate cells
    pass
# Gives total resource consumption for comparison with methods
```

### Example 3: Compare two approaches
```python
# Approach 1
with RCellProfiler("Load without transcripts"):
    pass
# ... work ...
stats1 = get_monitor().get_stats()
get_monitor().reset()

# Approach 2
with RCellProfiler("Load with transcripts"):
    pass
# ... work ...
stats2 = get_monitor().get_stats()

# Compare: stats1 vs stats2
```

---

**Questions?** Check the docstrings in each module:
```python
from resource_monitor import ResourceMonitor
help(ResourceMonitor)

from monitoring_dashboard import MonitoringDashboard
help(MonitoringDashboard)

from profiling_helpers import RCellProfiler
help(RCellProfiler)
```
