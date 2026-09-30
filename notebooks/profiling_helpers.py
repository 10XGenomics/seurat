"""
Convenience decorators and helpers for profiling R and Python code in notebooks.
"""

from functools import wraps
import time
from typing import Callable, Any
from resource_monitor import get_monitor, get_profiler
import subprocess
import json


def profile_function(func: Callable) -> Callable:
    """
    Decorator to automatically profile a function's resource usage.

    Usage:
        @profile_function
        def my_heavy_function():
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        profiler = get_profiler()
        return profiler.profile(func.__name__, func, *args, **kwargs)
    return wrapper


class RCellProfiler:
    """
    Helper for profiling R cells in notebooks.

    Usage in notebook:
        from profiling_helpers import RCellProfiler

        with RCellProfiler("my_operation"):
            # R code here...
            LoadAtera(...)
    """

    def __init__(self, name: str):
        self.name = name
        self.profiler = get_profiler()
        self.start_time = None
        self.baseline = None

    def __enter__(self):
        self.baseline = get_monitor()._measure()
        self.start_time = time.time()
        print(f"⏱️  Starting profile: {self.name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        final = get_monitor().get_latest()

        if final:
            ram_delta = final.ram_mb - self.baseline.ram_mb
            cpu_avg = get_monitor().get_stats()['cpu'].get('mean', 0)

            result = f"""
📊 Profile: {self.name}
   Duration: {duration:.2f}s
   CPU avg: {cpu_avg:.1f}%
   RAM Δ: {ram_delta:.1f} MB
"""
            if self.baseline.gpu_percent is not None and final.gpu_memory_mb is not None:
                gpu_delta = final.gpu_memory_mb - self.baseline.gpu_memory_mb
                result += f"   GPU Δ: {gpu_delta:.1f} MB\n"

            print(result)

            # Store in profiler
            self.profiler.profiles[self.name] = {
                'function': self.name,
                'duration_seconds': duration,
                'cpu_avg': cpu_avg,
                'ram_start_mb': self.baseline.ram_mb,
                'ram_end_mb': final.ram_mb,
                'ram_delta_mb': ram_delta,
            }

        return False


def get_system_info() -> dict:
    """Get system hardware information."""
    import psutil

    info = {
        'cpu_cores': psutil.cpu_count(logical=False),
        'cpu_threads': psutil.cpu_count(logical=True),
        'ram_total_gb': psutil.virtual_memory().total / (1024**3),
        'python_version': __import__('sys').version,
    }

    # GPU info
    try:
        import pynvml
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        if device_count > 0:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            props = pynvml.nvmlDeviceGetProperties(handle)
            info['gpu_name'] = props.name
            info['gpu_memory_gb'] = pynvml.nvmlDeviceGetMemoryInfo(handle).total / (1024**3)
    except Exception:
        pass

    return info


def print_system_info():
    """Print system information to console."""
    import json
    info = get_system_info()
    print("System Information:")
    print(json.dumps(info, indent=2))


def get_r_memory_usage() -> dict:
    """
    Get R memory usage via rpy2 if available.
    Works only if R kernel is active.
    """
    try:
        import rpy2.robjects as ro

        # Get R memory usage
        ro.r('gc()')  # Force garbage collection
        mem_info = ro.r('memory.size()')

        return {
            'memory_mb': float(mem_info[0]),
        }
    except Exception as e:
        return {'error': str(e)}


def compare_snapshots(name1: str, name2: str, monitor=None) -> None:
    """
    Compare two named snapshots from monitoring history.

    Usage:
        monitor.mark_snapshot('before_heavy_computation')
        # ... do work ...
        monitor.mark_snapshot('after_heavy_computation')
        compare_snapshots('before_heavy_computation', 'after_heavy_computation')
    """
    if monitor is None:
        from resource_monitor import get_monitor
        monitor = get_monitor()

    print(f"Comparison: {name1} → {name2}")
    print("Feature not yet implemented. Store snapshots manually for now.")


class MemoryWarning:
    """Context manager to warn when RAM usage exceeds threshold."""

    def __init__(self, threshold_percent: int = 85):
        self.threshold = threshold_percent
        self.monitor = get_monitor()
        self.baseline = None

    def __enter__(self):
        self.baseline = self.monitor.get_latest()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        current = self.monitor.get_latest()
        if current and current.ram_percent > self.threshold:
            print(f"⚠️  WARNING: RAM usage at {current.ram_percent:.1f}% (threshold: {self.threshold}%)")
        return False


class CPUWarning:
    """Context manager to warn when CPU usage exceeds threshold."""

    def __init__(self, threshold_percent: int = 90):
        self.threshold = threshold_percent
        self.monitor = get_monitor()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        stats = self.monitor.get_stats()
        cpu_stats = stats.get('cpu', {})
        if cpu_stats.get('max', 0) > self.threshold:
            print(f"⚠️  WARNING: Peak CPU usage {cpu_stats['max']:.1f}% (threshold: {self.threshold}%)")
        return False


def setup_notebook_profiling(gpu_enabled: bool = True) -> None:
    """
    Complete setup for notebook profiling.
    Call this once at the start of your notebook.

    Example:
        from profiling_helpers import setup_notebook_profiling
        setup_notebook_profiling()
    """
    from resource_monitor import init_monitoring
    from monitoring_dashboard import show_dashboard

    print("Initializing profiling system...")

    # Show system info
    print_system_info()
    print()

    # Initialize monitoring
    monitor, profiler = init_monitoring(gpu_enabled=gpu_enabled)
    print(f"✓ Monitoring initialized (GPU: {'enabled' if gpu_enabled else 'disabled'})")
    print()

    # Show dashboard
    print("Starting live dashboard...\n")
    show_dashboard(update_interval=1)


# IPython magic commands (if in Jupyter)
def register_magic_commands():
    """Register iPython magic commands for profiling."""
    try:
        from IPython import get_ipython
        ipython = get_ipython()

        if ipython is None:
            return

        # Register line magic for quick profiling
        @ipython.register_magic_function
        def profile(line):
            """Profile an R expression with %profile EXPR"""
            from profiling_helpers import RCellProfiler
            # This is a placeholder - actual implementation would evaluate line
            print(f"Would profile: {line}")
            return None

    except Exception:
        pass


if __name__ == '__main__':
    # Test when run directly
    print_system_info()
