"""
Real-time resource monitoring for Jupyter notebooks with live dashboard.
Tracks CPU, RAM, and GPU usage with spike detection and function-level profiling.
"""

import psutil
import threading
import time
from collections import deque
from dataclasses import dataclass, asdict
from datetime import datetime
import json
from typing import Optional, List, Dict, Any
import numpy as np


@dataclass
class ResourceSnapshot:
    """Single measurement of system resources."""
    timestamp: float
    cpu_percent: float
    ram_percent: float
    ram_mb: float
    gpu_percent: Optional[float] = None
    gpu_memory_mb: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ResourceMonitor:
    """
    Real-time resource monitoring with history and spike detection.
    """

    def __init__(self, buffer_size: int = 1000, gpu_enabled: bool = True):
        self.buffer_size = buffer_size
        self.history = deque(maxlen=buffer_size)
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.interval = 0.1  # 100ms sampling

        self.gpu_enabled = gpu_enabled
        self.gpu_available = False
        if gpu_enabled:
            self._check_gpu()

        # Statistics
        self.start_time = None
        self.baseline_ram_mb = None

    def _check_gpu(self):
        """Check if GPU monitoring is available."""
        try:
            import pynvml
            pynvml.nvmlInit()
            self.gpu_available = True
        except Exception:
            self.gpu_available = False

    def _get_gpu_stats(self) -> tuple:
        """Get GPU usage and memory."""
        if not self.gpu_available:
            return None, None

        try:
            import pynvml
            devices = pynvml.nvmlDeviceGetCount()
            if devices == 0:
                return None, None

            # Use first GPU
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)

            gpu_percent = util.gpu
            gpu_memory_mb = mem.used / (1024 ** 2)
            return gpu_percent, gpu_memory_mb
        except Exception:
            return None, None

    def _measure(self) -> ResourceSnapshot:
        """Take a single resource measurement."""
        cpu = psutil.cpu_percent(interval=0.01)
        ram = psutil.virtual_memory()
        gpu_percent, gpu_mem = self._get_gpu_stats()

        snapshot = ResourceSnapshot(
            timestamp=time.time(),
            cpu_percent=cpu,
            ram_percent=ram.percent,
            ram_mb=ram.used / (1024 ** 2),
            gpu_percent=gpu_percent,
            gpu_memory_mb=gpu_mem
        )

        return snapshot

    def start(self):
        """Start monitoring in background thread."""
        if self.running:
            return

        self.start_time = time.time()
        self.baseline_ram_mb = psutil.virtual_memory().used / (1024 ** 2)
        self.running = True

        def monitor_loop():
            while self.running:
                try:
                    snapshot = self._measure()
                    self.history.append(snapshot)
                    time.sleep(self.interval)
                except Exception as e:
                    print(f"Monitoring error: {e}")
                    time.sleep(self.interval)

        self.thread = threading.Thread(target=monitor_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop monitoring."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)

    def get_latest(self) -> Optional[ResourceSnapshot]:
        """Get most recent measurement."""
        if self.history:
            return self.history[-1]
        return None

    def get_history(self, seconds: Optional[int] = None) -> List[ResourceSnapshot]:
        """Get history, optionally filtered to last N seconds."""
        history = list(self.history)

        if seconds and history:
            cutoff_time = time.time() - seconds
            history = [s for s in history if s.timestamp >= cutoff_time]

        return history

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregated statistics."""
        if not self.history:
            return {}

        snapshots = list(self.history)
        cpu_values = [s.cpu_percent for s in snapshots]
        ram_values = [s.ram_percent for s in snapshots]

        stats = {
            'count': len(snapshots),
            'duration_seconds': snapshots[-1].timestamp - snapshots[0].timestamp,
            'cpu': {
                'current': cpu_values[-1] if cpu_values else 0,
                'mean': np.mean(cpu_values),
                'max': np.max(cpu_values),
                'min': np.min(cpu_values),
                'std': np.std(cpu_values),
            },
            'ram': {
                'current_mb': snapshots[-1].ram_mb,
                'current_percent': ram_values[-1] if ram_values else 0,
                'mean_percent': np.mean(ram_values),
                'max_percent': np.max(ram_values),
                'peak_increase_mb': (snapshots[-1].ram_mb - self.baseline_ram_mb) if self.baseline_ram_mb else 0,
            }
        }

        # GPU stats if available
        if self.gpu_available:
            gpu_utils = [s.gpu_percent for s in snapshots if s.gpu_percent is not None]
            gpu_mems = [s.gpu_memory_mb for s in snapshots if s.gpu_memory_mb is not None]

            if gpu_utils:
                stats['gpu'] = {
                    'current': gpu_utils[-1],
                    'mean': np.mean(gpu_utils),
                    'max': np.max(gpu_utils),
                    'memory_mb_peak': np.max(gpu_mems) if gpu_mems else 0,
                }

        return stats

    def detect_spikes(self, threshold_percent: int = 80) -> List[Dict[str, Any]]:
        """
        Detect resource usage spikes.
        Returns list of spike events with timestamp and details.
        """
        if len(self.history) < 2:
            return []

        snapshots = list(self.history)
        spikes = []

        # CPU spike detection
        cpu_values = [s.cpu_percent for s in snapshots]
        for i in range(1, len(cpu_values)):
            if cpu_values[i] > threshold_percent and (i == 1 or cpu_values[i-1] <= threshold_percent):
                spike = {
                    'type': 'cpu',
                    'timestamp': snapshots[i].timestamp,
                    'value': cpu_values[i],
                    'threshold': threshold_percent,
                }
                spikes.append(spike)

        # RAM spike detection (sudden increase)
        ram_values = [s.ram_mb for s in snapshots]
        if len(ram_values) > 10:
            recent_baseline = np.mean(ram_values[-20:-10])
            for i in range(10, len(ram_values)):
                if ram_values[i] > recent_baseline * 1.2:  # 20% increase
                    spike = {
                        'type': 'ram',
                        'timestamp': snapshots[i].timestamp,
                        'value': ram_values[i],
                        'increase_pct': ((ram_values[i] - recent_baseline) / recent_baseline) * 100,
                    }
                    spikes.append(spike)

        return spikes

    def reset(self):
        """Clear history and reset baseline."""
        self.history.clear()
        self.baseline_ram_mb = psutil.virtual_memory().used / (1024 ** 2)


class FunctionProfiler:
    """Profile resource usage of individual functions."""

    def __init__(self, monitor: ResourceMonitor):
        self.monitor = monitor
        self.profiles: Dict[str, Dict[str, Any]] = {}

    def profile(self, func_name: str, func, *args, **kwargs) -> Any:
        """
        Execute function while profiling resource usage.
        Returns (result, profile_dict)
        """
        # Baseline before execution
        baseline = self.monitor.get_latest()
        if not baseline:
            # Take immediate measurement
            baseline = self.monitor._measure()

        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()

        # Measurements after execution
        latest = self.monitor.get_latest()

        # Calculate deltas
        duration = end_time - start_time
        cpu_avg = np.mean([s.cpu_percent for s in self.monitor.get_history(seconds=int(duration) + 1)])

        profile = {
            'function': func_name,
            'duration_seconds': duration,
            'cpu_avg': cpu_avg,
            'ram_start_mb': baseline.ram_mb,
            'ram_end_mb': latest.ram_mb if latest else baseline.ram_mb,
            'ram_delta_mb': (latest.ram_mb if latest else baseline.ram_mb) - baseline.ram_mb,
        }

        # GPU profiling if available
        if self.monitor.gpu_available and baseline.gpu_memory_mb and latest and latest.gpu_memory_mb:
            profile['gpu_memory_delta_mb'] = latest.gpu_memory_mb - baseline.gpu_memory_mb

        self.profiles[func_name] = profile
        return result

    def get_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Get all function profiles."""
        return self.profiles

    def report(self) -> str:
        """Generate text report of all profiles."""
        if not self.profiles:
            return "No profiles recorded yet."

        lines = ["Function Profiling Report", "=" * 60]

        for func_name, profile in self.profiles.items():
            lines.append(f"\n{func_name}:")
            lines.append(f"  Duration: {profile['duration_seconds']:.2f}s")
            lines.append(f"  CPU Avg:  {profile['cpu_avg']:.1f}%")
            lines.append(f"  RAM Δ:    {profile['ram_delta_mb']:.1f} MB")
            if 'gpu_memory_delta_mb' in profile:
                lines.append(f"  GPU Δ:    {profile['gpu_memory_delta_mb']:.1f} MB")

        return "\n".join(lines)


# Global instances for easy access
_monitor: Optional[ResourceMonitor] = None
_profiler: Optional[FunctionProfiler] = None


def init_monitoring(gpu_enabled: bool = True) -> tuple:
    """Initialize global monitoring system."""
    global _monitor, _profiler

    _monitor = ResourceMonitor(gpu_enabled=gpu_enabled)
    _profiler = FunctionProfiler(_monitor)

    _monitor.start()

    return _monitor, _profiler


def get_monitor() -> ResourceMonitor:
    """Get global monitor instance."""
    global _monitor
    if _monitor is None:
        init_monitoring()
    return _monitor


def get_profiler() -> FunctionProfiler:
    """Get global profiler instance."""
    global _profiler
    if _profiler is None:
        init_monitoring()
    return _profiler


def stop_monitoring():
    """Stop global monitoring."""
    global _monitor
    if _monitor:
        _monitor.stop()
