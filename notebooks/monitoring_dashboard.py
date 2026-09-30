"""
Interactive monitoring dashboard for Jupyter notebooks.
Displays real-time CPU, RAM, and GPU usage with live charts.
"""

from IPython.display import display, HTML, clear_output
import ipywidgets as widgets
from ipywidgets import HBox, VBox, Output, FloatProgress, HTML as HTMLWidget
import threading
import time
from datetime import datetime
import json
from typing import Optional

try:
    import plotly.graph_objects as go
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

from resource_monitor import ResourceMonitor, get_monitor, get_profiler


class MonitoringDashboard:
    """Interactive dashboard for resource monitoring."""

    def __init__(self, monitor: Optional[ResourceMonitor] = None, update_interval: int = 1):
        """
        Initialize dashboard.

        Parameters:
        - monitor: ResourceMonitor instance (uses global if None)
        - update_interval: Update frequency in seconds
        """
        self.monitor = monitor or get_monitor()
        self.update_interval = update_interval
        self.running = False
        self.update_thread = None

        # Create widgets
        self._create_widgets()

    def _create_widgets(self):
        """Create dashboard widgets."""

        # Title
        self.title = HTMLWidget(value="<h2>Resource Monitor Dashboard</h2>")

        # Status indicators
        self.timestamp_display = HTMLWidget()
        self.status_display = HTMLWidget()

        # Current values
        self.cpu_progress = FloatProgress(
            value=0, min=0, max=100,
            description='CPU:',
            bar_style='info',
            orientation='horizontal'
        )
        self.ram_progress = FloatProgress(
            value=0, min=0, max=100,
            description='RAM:',
            bar_style='info',
            orientation='horizontal'
        )
        self.gpu_progress = FloatProgress(
            value=0, min=0, max=100,
            description='GPU:',
            bar_style='info',
            orientation='horizontal'
        )

        # Stats display
        self.stats_display = HTMLWidget()

        # Chart output
        self.chart_output = Output()

        # Function profiles
        self.profiles_display = HTMLWidget()

        # Control buttons
        self.reset_button = widgets.Button(description='Reset Data')
        self.reset_button.on_click(self._on_reset)

        self.export_button = widgets.Button(description='Export JSON')
        self.export_button.on_click(self._on_export)

        # Update indicator
        self.update_indicator = HTMLWidget()

        self._update_displays()

    def _get_bar_color(self, value: float, high_threshold: float = 80) -> str:
        """Get color based on value."""
        if value > high_threshold:
            return 'danger'
        elif value > 60:
            return 'warning'
        return 'success'

    def _update_displays(self):
        """Update all dashboard displays."""
        try:
            latest = self.monitor.get_latest()
            if not latest:
                return

            # Timestamp
            ts = datetime.fromtimestamp(latest.timestamp).strftime('%Y-%m-%d %H:%M:%S')
            self.timestamp_display.value = f"<small>Updated: {ts}</small>"

            # Progress bars
            self.cpu_progress.value = latest.cpu_percent
            self.cpu_progress.bar_style = self._get_bar_color(latest.cpu_percent)

            self.ram_progress.value = latest.ram_percent
            self.ram_progress.bar_style = self._get_bar_color(latest.ram_percent)

            if latest.gpu_percent is not None:
                self.gpu_progress.value = latest.gpu_percent
                self.gpu_progress.bar_style = self._get_bar_color(latest.gpu_percent)

            # Statistics
            stats = self.monitor.get_stats()
            if stats:
                cpu_stat = stats.get('cpu', {})
                ram_stat = stats.get('ram', {})

                stats_html = "<b>Statistics:</b><br>"
                stats_html += f"CPU: {cpu_stat.get('current', 0):.1f}% (avg: {cpu_stat.get('mean', 0):.1f}%, max: {cpu_stat.get('max', 0):.1f}%)<br>"
                stats_html += f"RAM: {ram_stat.get('current_percent', 0):.1f}% ({ram_stat.get('current_mb', 0):.0f} MB)<br>"
                stats_html += f"Peak increase: {ram_stat.get('peak_increase_mb', 0):.0f} MB<br>"

                if 'gpu' in stats:
                    gpu_stat = stats['gpu']
                    stats_html += f"GPU: {gpu_stat.get('current', 0):.1f}% (avg: {gpu_stat.get('mean', 0):.1f}%, peak mem: {gpu_stat.get('memory_mb_peak', 0):.0f} MB)<br>"

                self.stats_display.value = stats_html

            # Spikes
            spikes = self.monitor.detect_spikes(threshold_percent=80)
            spike_text = f"<b>Spikes detected:</b> {len(spikes)}"
            self.status_display.value = spike_text

            # Function profiles
            profiles = get_profiler().get_profiles()
            if profiles:
                prof_html = "<b>Function Profiles:</b><br>"
                for func_name, profile in list(profiles.items())[-5:]:  # Last 5
                    prof_html += f"{func_name}: {profile['duration_seconds']:.2f}s, Δ RAM: {profile['ram_delta_mb']:.1f}MB<br>"
                self.profiles_display.value = prof_html

            # Update timestamp
            self.update_indicator.value = f"<small style='color:green'>● Live</small>"

        except Exception as e:
            self.update_indicator.value = f"<small style='color:red'>Error: {str(e)[:50]}</small>"

    def _update_chart(self):
        """Update time series chart."""
        if not PLOTLY_AVAILABLE:
            return

        history = self.monitor.get_history(seconds=300)  # Last 5 minutes
        if not history:
            return

        try:
            times = [h.timestamp for h in history]
            cpu_vals = [h.cpu_percent for h in history]
            ram_vals = [h.ram_percent for h in history]

            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=times, y=cpu_vals, mode='lines',
                name='CPU %', line=dict(color='blue', width=2)
            ))

            fig.add_trace(go.Scatter(
                x=times, y=ram_vals, mode='lines',
                name='RAM %', line=dict(color='red', width=2)
            ))

            fig.update_layout(
                title='Resource Usage (Last 5 minutes)',
                xaxis_title='Time',
                yaxis_title='Usage %',
                hovermode='x unified',
                height=400,
                margin=dict(l=40, r=40, t=40, b=40),
            )

            with self.chart_output:
                clear_output(wait=True)
                display(fig)

        except Exception as e:
            print(f"Chart error: {e}")

    def _on_reset(self, button):
        """Reset monitoring data."""
        self.monitor.reset()
        self._update_displays()
        self._update_chart()

    def _on_export(self, button):
        """Export monitoring data as JSON."""
        data = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'gpu_available': self.monitor.gpu_available,
            },
            'statistics': self.monitor.get_stats(),
            'history': [h.to_dict() for h in self.monitor.get_history()],
            'spikes': self.monitor.detect_spikes(),
        }

        filename = f"resource_monitor_{int(time.time())}.json"

        # Display download link
        json_str = json.dumps(data, indent=2, default=str)

        from IPython.display import JSON
        display(JSON(data))

        print(f"\nData available as: {filename}")

    def _update_loop(self):
        """Background update loop."""
        while self.running:
            try:
                self._update_displays()
                if PLOTLY_AVAILABLE:
                    self._update_chart()
                time.sleep(self.update_interval)
            except Exception as e:
                print(f"Update error: {e}")
                time.sleep(self.update_interval)

    def show(self):
        """Display the dashboard."""
        display(self.title)

        controls = HBox([self.reset_button, self.export_button, self.update_indicator])
        display(controls)

        display(self.timestamp_display)
        display(self.cpu_progress)
        display(self.ram_progress)
        display(self.gpu_progress)

        display(self.stats_display)
        display(self.status_display)
        display(self.profiles_display)

        if PLOTLY_AVAILABLE:
            display(self.chart_output)
            self._update_chart()

        # Start update thread
        self.running = True
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()

    def stop(self):
        """Stop the dashboard."""
        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=2)


def show_dashboard(update_interval: int = 1) -> MonitoringDashboard:
    """
    Display monitoring dashboard in notebook.

    Parameters:
    - update_interval: Update frequency in seconds (default 1)

    Returns:
    - MonitoringDashboard instance
    """
    monitor = get_monitor()
    dashboard = MonitoringDashboard(monitor, update_interval=update_interval)
    dashboard.show()
    return dashboard
