import marimo

__generated_with = "0.16.2"
app = marimo.App(width="medium")


@app.cell
def _(mo):
    mo.md("# FRENZ Data Collection Dashboard")
    return


@app.cell
def _(mo):
    # Instructions in an accordion/expandable section
    instructions = mo.accordion({
        "ℹ️ How to Use": mo.md("""
        1. **Connect Device**: Click "Scan for Devices", select your FRENZ device, then "Connect"
        2. **Start Recording**: Once connected, click "Start Recording" to begin data collection
        3. **Monitor Data**: View real-time visualizations in the tabs below
        4. **Log Events**: Enter event descriptions and click "Add Event" to annotate the data
        5. **Stop Recording**: Click "Stop Recording" to save all data to disk

        **Data Storage**: Automatically saved to `data/` directory (HDF5 for sensors, JSON for events)
        """)
    })
    instructions
    return (instructions,)


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _():
    # Import required libraries
    import os
    import time
    from pathlib import Path
    import plotly.graph_objects as go
    from collections import deque
    from datetime import datetime

    # Import custom modules
    from device_manager import DeviceManager, DeviceStatus
    from frenz_collector import FrenzCollector
    from data_storage import DataStorage
    from event_logger import EventLogger
    return DeviceStatus, FrenzCollector, datetime, deque, go, time


@app.cell
def _(FrenzCollector):
    # Initialize collector and device manager
    collector = FrenzCollector()
    return (collector,)


@app.cell
def _(deque, time):
    # Initialize data buffers for visualization
    MAX_BUFFER_SIZE = 500  # Keep last 500 data points for each plot

    data_buffers = {
        'focus': deque(maxlen=MAX_BUFFER_SIZE),
        'poas': deque(maxlen=MAX_BUFFER_SIZE),
        'posture': deque(maxlen=MAX_BUFFER_SIZE),
        'power_bands': {
            'alpha': deque(maxlen=MAX_BUFFER_SIZE),
            'beta': deque(maxlen=MAX_BUFFER_SIZE),
            'gamma': deque(maxlen=MAX_BUFFER_SIZE),
            'theta': deque(maxlen=MAX_BUFFER_SIZE),
            'delta': deque(maxlen=MAX_BUFFER_SIZE),
        },
        'signal_quality': deque(maxlen=MAX_BUFFER_SIZE),
        'imu': {
            'x': deque(maxlen=MAX_BUFFER_SIZE),
            'y': deque(maxlen=MAX_BUFFER_SIZE),
            'z': deque(maxlen=MAX_BUFFER_SIZE),
        },
        'ppg': {
            'green': deque(maxlen=MAX_BUFFER_SIZE),
            'red': deque(maxlen=MAX_BUFFER_SIZE),
            'ir': deque(maxlen=MAX_BUFFER_SIZE),
        },
        'hr': deque(maxlen=MAX_BUFFER_SIZE),  # Heart rate
        'spo2': deque(maxlen=MAX_BUFFER_SIZE),  # Blood oxygen saturation
        'events': deque(maxlen=50)  # Keep last 50 events
    }

    # Initialize time reference - will be reset when recording starts
    buffer_start_time = {'time': time.time(), 'recording_started': False}
    return buffer_start_time, data_buffers


@app.cell
def _(mo):
    mo.md("""## Device Connection""")
    return


@app.cell
def _(mo):
    # Create scan button using run_button for better reactivity
    scan_button = mo.ui.run_button(label="Scan for Devices", kind="neutral")
    return (scan_button,)


@app.cell
def _(collector, mo, scan_button):
    # Handle scanning and create device selector
    # run_button.value is None initially, then a timestamp when clicked
    available_devices = []
    scan_status = ""
    device_selector = None

    if scan_button.value:
        scan_status = "🔍 Scanning for devices..."
        print(f"Starting device scan...")
        try:
            devices = collector.device_manager.scan_devices()
            print(f"Scan complete. Found {len(devices)} devices: {devices}")

            if devices:
                available_devices = [f"{d['id']} ({d['name']}, RSSI: {d['rssi']})" for d in devices]
                scan_status = f"✅ Found {len(devices)} device(s)"

                # Create device selector with actual devices
                device_selector = mo.ui.radio(
                    options=available_devices,
                    value=available_devices[0],
                    label="Select a device:"
                )
            else:
                available_devices = []
                scan_status = "⚠️ No FRENZ devices found. Make sure device is on and in range."
                device_selector = mo.md("*No devices available*")

        except Exception as e:
            available_devices = []
            scan_status = f"❌ Scan error: {str(e)}"
            print(f"Scan error: {e}")
            device_selector = mo.md(f"*Error: {str(e)}*")
    else:
        # Initial state - haven't scanned yet
        scan_status = "Click 'Scan for Devices' to begin"
        device_selector = mo.md("*Click 'Scan for Devices' button above to find devices*")
    return available_devices, device_selector, scan_status


@app.cell
def _(mo):
    # Create connection buttons - use run_button for action buttons
    connect_button = mo.ui.run_button(label="Connect", kind="success")
    disconnect_button = mo.ui.run_button(label="Disconnect", kind="danger")
    # Create light toggle switch
    light_toggle = mo.ui.switch(label="Device Light", value=False)
    return connect_button, disconnect_button, light_toggle


@app.cell
def _(collector, light_toggle):
    # Handle light toggle
    if light_toggle.value != (not collector.device_manager.light_off):
        result = collector.device_manager.toggle_light(light_toggle.value)
        if result.get("requires_reconnect"):
            print(f"⚠️  {result['message']}")
    return


@app.cell
def _(
    DeviceStatus,
    collector,
    connect_button,
    device_selector,
    disconnect_button,
):
    # Handle connections - only act if not already in the desired state
    current_status = collector.device_manager.get_status()

    if connect_button.value and current_status != DeviceStatus.CONNECTED:
        # Check if device_selector has a value attribute (it's a UI element)
        if hasattr(device_selector, 'value') and device_selector.value:
            try:
                device_id = device_selector.value.split(" ")[0]
                print(f"Attempting to connect to device: {device_id}")
                collector.device_manager.connect(device_id)
            except Exception as e:
                print(f"Connection error: {e}")
                pass  # Error already printed
        else:
            print("No device selected or scan not performed")

    if disconnect_button.value and current_status == DeviceStatus.CONNECTED:
        try:
            print("Disconnecting device...")
            # Stop recording first if active
            if collector.is_recording:
                print("Stopping active recording before disconnect...")
                collector.stop_recording()
            collector.device_manager.disconnect()
            print("Device disconnected successfully")
        except Exception as e:
            print(f"Disconnect error: {e}")
            pass  # Error already printed

    # Get status after potential connection changes
    device_status = collector.device_manager.get_status()
    status_color = {
        DeviceStatus.CONNECTED: "green",
        DeviceStatus.CONNECTING: "yellow",
        DeviceStatus.DISCONNECTED: "red",
        DeviceStatus.ERROR: "red",
        DeviceStatus.SCANNING: "blue"
    }.get(device_status, "gray")

    status_text = f"**Status:** <span style='color: {status_color}'>{device_status.value}</span>"
    return device_status, status_text


@app.cell
def _(
    DeviceStatus,
    available_devices,
    connect_button,
    device_selector,
    device_status,
    disconnect_button,
    light_toggle,
    mo,
    scan_button,
    scan_status,
    status_text,
):
    # Display device connection UI
    device_list_display = mo.md("")
    if scan_button.value and available_devices:
        device_list_display = mo.md(f"**Found devices:**\n" + "\n".join([f"- {d}" for d in available_devices]))

    # Show only relevant button based on connection status
    _is_connected_ui = device_status == DeviceStatus.CONNECTED
    connection_controls = disconnect_button if _is_connected_ui else mo.hstack([connect_button])

    # Display the UI - this will be shown in the notebook
    mo.vstack([
        mo.hstack([scan_button, mo.md(status_text)]),
        mo.md(f"**{scan_status}**") if scan_status else mo.md(""),
        device_list_display if available_devices else mo.md(""),
        mo.md("---"),
        device_selector if not _is_connected_ui else mo.md(""),
        mo.md("---") if not _is_connected_ui else mo.md(""),
        mo.hstack([connection_controls, light_toggle]),
        mo.md("*Note: Toggle light before connecting, or reconnect after changing.*")
    ])
    return


@app.cell
def _(mo):
    mo.md("""## Recording Controls""")
    return


@app.cell
def _(DeviceStatus, device_status, mo):
    # Create recording buttons - use run_button for action buttons
    is_connected = device_status == DeviceStatus.CONNECTED
    start_button = mo.ui.run_button(label="Start Recording", kind="success", disabled=not is_connected)
    stop_button = mo.ui.run_button(label="Stop Recording", kind="danger")
    return start_button, stop_button


@app.cell
def _(collector, start_button, stop_button):
    # Handle recording
    if start_button.value and not collector.is_recording:
        try:
            collector.start_recording()
        except Exception as e:
            print(f"Error starting recording: {e}")

    if stop_button.value and collector.is_recording:
        try:
            summary = collector.stop_recording()
            print(f"Recording stopped. Data saved to: {summary.get('session_path', 'Unknown')}")
        except Exception as e:
            print(f"Error stopping recording: {e}")
    return


@app.cell
def _(mo):
    # Create refresh control for recording status
    refresh_recording_status = mo.ui.refresh(default_interval="1s")
    return (refresh_recording_status,)


@app.cell
def _(collector, mo, refresh_recording_status, start_button, stop_button, time):
    # Display recording status - driven by refresh control
    # The refresh control must be referenced for it to trigger
    refresh_recording_status

    _is_recording = collector.is_recording
    if _is_recording:
        elapsed_time = time.time() - collector.session_start_time
        hours, remainder = divmod(elapsed_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        duration_str = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"

        try:
            _stats = collector.get_session_stats()
            samples_collected = _stats.get('samples_collected', 0)

            # Get storage stats for total samples
            storage_stats = _stats.get('storage_stats', {})
            total_samples = storage_stats.get('total_samples', 0)

            # Estimate data size (rough estimate: ~4 bytes per sample per channel)
            # Assuming multiple channels and data types
            data_size_mb = (total_samples * 4 * 10) / (1024 * 1024)  # Rough estimate
        except Exception as e:
            samples_collected = 0
            total_samples = 0
            data_size_mb = 0

        status_display = mo.md(f"""
        **Recording Status:** 🔴 Recording
        **Duration:** {duration_str}
        **Samples (collected):** {samples_collected:,}
        **Samples (stored):** {total_samples:,}
        **Est. Data Size:** {data_size_mb:.2f} MB
        """)
    else:
        status_display = mo.md("**Recording Status:** ⚪ Not Recording")
        data_size_mb = 0
        duration_str = "00:00:00"
        samples_collected = 0

    # Show only relevant recording button based on status
    recording_controls = start_button if not _is_recording else stop_button

    # Display UI and refresh control together
    mo.vstack([
        recording_controls,
        status_display,
        mo.Html(f"<div style='display:none'>{refresh_recording_status}</div>")  # Hidden refresh timer
    ])
    return


@app.cell
def _(mo):
    mo.md("""## Current Status""")
    return


@app.cell
def _(collector, mo, refresh_recording_status):
    # Posture and real-time status display
    refresh_recording_status

    posture_text = "Unknown"
    hr_text = "--"
    spo2_text = "--"

    if collector.is_recording and collector.device_manager.is_connected():
        _streamer_status = collector.device_manager.get_streamer()
        if _streamer_status and hasattr(_streamer_status, 'SCORES'):
            try:
                _posture_val = _streamer_status.SCORES.get('posture')
                if _posture_val:
                    posture_text = _posture_val.capitalize()

                _hr_val = _streamer_status.SCORES.get('hr')
                if _hr_val is not None:
                    hr_text = f"{int(_hr_val)} BPM"

                _spo2_val = _streamer_status.SCORES.get('spo2')
                if _spo2_val is not None:
                    spo2_text = f"{int(_spo2_val)}%"
            except Exception:
                pass

    # Color code based on values
    hr_color = "#2ecc71" if hr_text != "--" else "#95a5a6"
    spo2_color = "#2ecc71" if "%" in spo2_text and int(spo2_text.replace("%","")) > 95 else "#e67e22" if "%" in spo2_text else "#95a5a6"

    status_card = mo.Html(f"""
    <div style="border: 1px solid #ddd; border-radius: 4px; padding: 12px; margin: 10px 0; background: #fafafa;">
        <div style="display: flex; justify-content: space-around; align-items: center;">
            <div style="text-align: center;">
                <div style="font-weight: 600; font-size: 11px; color: #7f8c8d; text-transform: uppercase; letter-spacing: 0.5px;">Posture</div>
                <div style="font-size: 18px; margin-top: 6px; color: #2c3e50;">{posture_text}</div>
            </div>
            <div style="text-align: center;">
                <div style="font-weight: 600; font-size: 11px; color: #7f8c8d; text-transform: uppercase; letter-spacing: 0.5px;">Heart Rate</div>
                <div style="font-size: 18px; margin-top: 6px; color: {hr_color}; font-weight: 500;">{hr_text}</div>
            </div>
            <div style="text-align: center;">
                <div style="font-weight: 600; font-size: 11px; color: #7f8c8d; text-transform: uppercase; letter-spacing: 0.5px;">Blood Oxygen</div>
                <div style="font-size: 18px; margin-top: 6px; color: {spo2_color}; font-weight: 500;">{spo2_text}</div>
            </div>
        </div>
    </div>
    """)

    status_card
    return


@app.cell
def _(mo):
    mo.md("""## Real-Time Visualizations""")
    return


@app.cell
def _():
    # Diagnostic section removed - no longer needed
    return


@app.cell
def _(mo):
    # Create refresh controls
    refresh_focus = mo.ui.refresh(default_interval="2s")
    refresh_poas = mo.ui.refresh(default_interval="30s")
    refresh_power = mo.ui.refresh(default_interval="2s")
    refresh_signal = mo.ui.refresh(default_interval="5s")
    refresh_imu = mo.ui.refresh(default_interval="1s")
    refresh_ppg = mo.ui.refresh(default_interval="1s")
    return refresh_focus, refresh_poas, refresh_power, refresh_signal, refresh_imu, refresh_ppg


@app.cell
def _(buffer_start_time, collector, data_buffers, go, mo, refresh_focus, refresh_recording_status, time):
    # Update and plot focus data
    refresh_focus
    # Force dependency on recording status to ensure cell re-runs when recording starts/stops
    refresh_recording_status

    _is_rec = collector.is_recording

    # Reset buffer start time when recording starts
    if _is_rec and not buffer_start_time['recording_started']:
        buffer_start_time['time'] = time.time()
        buffer_start_time['recording_started'] = True
        # Clear all buffers
        data_buffers['focus'].clear()
    elif not _is_rec and buffer_start_time['recording_started']:
        buffer_start_time['recording_started'] = False

    if _is_rec:
        _streamer = collector.device_manager.get_streamer()
        if _streamer:
            try:
                # Check if SCORES attribute exists
                if hasattr(_streamer, 'SCORES'):
                    focus_score = _streamer.SCORES.get("focus_score")
                    if focus_score is not None:
                        _current_time_focus = time.time() - buffer_start_time['time']
                        data_buffers['focus'].append((_current_time_focus, focus_score))
            except Exception as e:
                pass

    # Create focus plot
    if len(data_buffers['focus']) > 0:
        _times_focus, _values_focus = zip(*data_buffers['focus'])
        focus_fig = go.Figure()
        focus_fig.add_trace(go.Scatter(
            x=list(_times_focus),
            y=list(_values_focus),
            mode='lines',
            name='Focus Score',
            line=dict(color='blue', width=2)
        ))
        focus_fig.update_layout(
            title=f'Focus Score (n={len(data_buffers["focus"])})',
            xaxis_title='Time (seconds)',
            yaxis_title='Score (0-100)',
            yaxis=dict(range=[0, 100]),  # Focus scores are 0-100, not 0-1
            height=500
        )
    else:
        focus_fig = go.Figure()
        focus_fig.add_annotation(
            text="Waiting for focus data...",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14)
        )
        focus_fig.update_layout(title='Focus Score', height=500)

    focus_plot = mo.ui.plotly(focus_fig)
    return (focus_plot,)


@app.cell
def _(buffer_start_time, collector, data_buffers, go, mo, refresh_poas, refresh_recording_status, time):
    # Update and plot POAS data
    refresh_poas
    # Force dependency on recording status
    refresh_recording_status

    _is_rec_poas = collector.is_recording

    # Reset buffer when recording starts
    if _is_rec_poas and not buffer_start_time['recording_started']:
        data_buffers['poas'].clear()

    if _is_rec_poas:
        _streamer_poas = collector.device_manager.get_streamer()
        if _streamer_poas:
            try:
                if hasattr(_streamer_poas, 'SCORES'):
                    poas_score = _streamer_poas.SCORES.get("poas")  # Key is "poas" not "poas_score"
                    if poas_score is not None:
                        _current_time_poas = time.time() - buffer_start_time['time']
                        data_buffers['poas'].append((_current_time_poas, poas_score))
            except Exception as e:
                pass

    # Create POAS plot
    if data_buffers['poas']:
        _times_poas, _values_poas = zip(*data_buffers['poas'])
        poas_fig = go.Figure()
        poas_fig.add_trace(go.Scatter(
            x=list(_times_poas),
            y=list(_values_poas),
            mode='lines+markers',
            name='POAS Score',
            line=dict(color='green', width=2)
        ))
        poas_fig.update_layout(
            title=f'POAS (Presence of Attention Score) (n={len(data_buffers["poas"])})',
            xaxis_title='Time (seconds)',
            yaxis_title='Score',
            height=500
        )
    else:
        poas_fig = go.Figure()
        poas_fig.add_annotation(
            text="Waiting for POAS data...",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14)
        )
        poas_fig.update_layout(title='POAS Score', height=500)

    poas_plot = mo.ui.plotly(poas_fig)
    return (poas_plot,)


@app.cell
def _(buffer_start_time, collector, data_buffers, go, mo, refresh_power, refresh_recording_status, time):
    # Update and plot power bands
    refresh_power
    # Force dependency on recording status
    refresh_recording_status

    _is_rec_power = collector.is_recording

    # Reset buffers when recording starts
    if _is_rec_power and not buffer_start_time['recording_started']:
        for band in ['alpha', 'beta', 'gamma', 'theta', 'delta']:
            data_buffers['power_bands'][band].clear()

    if _is_rec_power:
        _streamer_power = collector.device_manager.get_streamer()
        if _streamer_power:
            try:
                if hasattr(_streamer_power, 'SCORES'):
                    # Power bands are individual keys, not a dict
                    _current_time_power = time.time() - buffer_start_time['time']
                    _bands_found = 0
                    for band in ['alpha', 'beta', 'gamma', 'theta', 'delta']:
                        band_data = _streamer_power.SCORES.get(band)
                        if band_data is not None:
                            # band_data is array [LF, OTEL, RF, OTER, AVG], use AVG (last value)
                            if hasattr(band_data, '__len__') and len(band_data) >= 5:
                                avg_power = band_data[-1]  # Use average value
                                data_buffers['power_bands'][band].append((_current_time_power, avg_power))
                                _bands_found += 1
                    if _bands_found > 0:
                        pass
            except Exception as e:
                pass

    # Create power bands plot
    power_fig = go.Figure()
    _colors_power = {'alpha': 'red', 'beta': 'blue', 'gamma': 'green', 'theta': 'purple', 'delta': 'orange'}

    has_data = False
    for _band_power, _color_power in _colors_power.items():
        if data_buffers['power_bands'][_band_power]:
            has_data = True
            _times_band, _values_band = zip(*data_buffers['power_bands'][_band_power])
            power_fig.add_trace(go.Scatter(
                x=list(_times_band),
                y=list(_values_band),
                mode='lines',
                name=_band_power.capitalize(),
                line=dict(color=_color_power, width=2)
            ))

    if has_data:
        # Count total points across all bands
        _total_points = sum(len(data_buffers['power_bands'][b]) for b in _colors_power.keys())
        power_fig.update_layout(
            title=f'EEG Power Bands (n={_total_points} total)',
            xaxis_title='Time (seconds)',
            yaxis_title='Power (dB)',
            height=500,
            showlegend=True
        )
    else:
        power_fig.add_annotation(
            text="Waiting for power band data...",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14)
        )
        power_fig.update_layout(title='EEG Power Bands', height=500)

    power_plot = mo.ui.plotly(power_fig)
    return (power_plot,)


@app.cell
def _(buffer_start_time, collector, data_buffers, go, mo, refresh_signal, refresh_recording_status):
    # Update and plot signal quality
    refresh_signal
    # Force dependency on recording status
    refresh_recording_status

    _is_rec_signal = collector.is_recording

    # Reset buffer when recording starts
    if _is_rec_signal and not buffer_start_time['recording_started']:
        data_buffers['signal_quality'].clear()

    if _is_rec_signal:
        _streamer_signal = collector.device_manager.get_streamer()
        if _streamer_signal:
            try:
                if hasattr(_streamer_signal, 'SCORES'):
                    signal_data = _streamer_signal.SCORES.get("sqc_scores")  # Key is "sqc_scores" not "signal_quality"
                    if signal_data is not None:
                        data_buffers['signal_quality'].clear()
                        data_buffers['signal_quality'].append(signal_data)
            except Exception as e:
                pass

    # Create signal quality plot
    if data_buffers['signal_quality']:
        latest_quality = list(data_buffers['signal_quality'])[-1]

        # Signal quality is a 4-element array (one per EEG channel)
        if hasattr(latest_quality, '__len__') and len(latest_quality) == 4:
            _channels = ['Left Frontal', 'Left Ear', 'Right Frontal', 'Right Ear']
            _values_signal = list(latest_quality)

            signal_fig = go.Figure()
            signal_fig.add_trace(go.Bar(
                x=_channels,
                y=_values_signal,
                marker_color=['green' if v > 0.7 else 'orange' if v > 0.4 else 'red' for v in _values_signal]
            ))
            signal_fig.update_layout(
                title='Signal Quality by Channel (Current)',
                xaxis_title='Channel',
                yaxis_title='Quality (0-1)',
                yaxis=dict(range=[0, 1.2]),
                height=500
            )
        else:
            signal_fig = go.Figure()
            signal_fig.add_annotation(
                text=f"Invalid signal quality data format: {type(latest_quality)}, len={len(latest_quality) if hasattr(latest_quality, '__len__') else 'N/A'}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=14)
            )
    else:
        signal_fig = go.Figure()
        signal_fig.add_annotation(
            text="Waiting for signal quality data...",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14)
        )
        signal_fig.update_layout(title='Signal Quality', height=500)

    signal_plot = mo.ui.plotly(signal_fig)
    return (signal_plot,)


@app.cell
def _(buffer_start_time, collector, data_buffers, go, mo, refresh_imu, refresh_recording_status, time):
    # Update and plot IMU data
    refresh_imu
    # Force dependency on recording status
    refresh_recording_status

    _is_rec_imu = collector.is_recording

    # Reset buffer when recording starts
    if _is_rec_imu and not buffer_start_time['recording_started']:
        data_buffers['imu']['x'].clear()
        data_buffers['imu']['y'].clear()
        data_buffers['imu']['z'].clear()

    if _is_rec_imu:
        _streamer_imu = collector.device_manager.get_streamer()
        if _streamer_imu:
            try:
                imu_data = _streamer_imu.DATA.get("RAW", {}).get("IMU")
                if imu_data is not None and hasattr(imu_data, 'shape') and imu_data.shape[0] > 0:
                    # IMU data shape is [N, 4]: timestamp, x, y, z
                    latest_imu = imu_data[-1, 1:]  # Skip timestamp, get x, y, z
                    _current_time_imu = time.time() - buffer_start_time['time']
                    data_buffers['imu']['x'].append((_current_time_imu, latest_imu[0]))
                    data_buffers['imu']['y'].append((_current_time_imu, latest_imu[1]))
                    data_buffers['imu']['z'].append((_current_time_imu, latest_imu[2]))
            except Exception as e:
                pass

    # Create IMU plot
    if any(len(data_buffers['imu'][axis]) > 0 for axis in ['x', 'y', 'z']):
        imu_fig = go.Figure()

        for _axis_imu, _color_imu in [('x', 'red'), ('y', 'green'), ('z', 'blue')]:
            if data_buffers['imu'][_axis_imu]:
                _times_imu, _values_imu = zip(*data_buffers['imu'][_axis_imu])
                imu_fig.add_trace(go.Scatter(
                    x=_times_imu, y=_values_imu,
                    mode='lines',
                    name=f'{_axis_imu.upper()}-axis',
                    line=dict(color=_color_imu, width=2)
                ))

        imu_fig.update_layout(
            title=f'IMU (Accelerometer) (n={len(data_buffers["imu"]["x"])})',
            xaxis_title='Time (s)',
            yaxis_title='Acceleration (g)',
            height=500,
            showlegend=True
        )
    else:
        imu_fig = go.Figure()
        imu_fig.add_annotation(
            text="Waiting for IMU data...",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14)
        )
        imu_fig.update_layout(title='IMU (Accelerometer)', height=500)

    imu_plot = mo.ui.plotly(imu_fig)
    return (imu_plot,)


@app.cell
def _(buffer_start_time, collector, data_buffers, go, mo, refresh_ppg, refresh_recording_status, time):
    # Update and plot PPG data
    refresh_ppg
    # Force dependency on recording status
    refresh_recording_status

    _is_rec_ppg = collector.is_recording

    # Reset buffer when recording starts
    if _is_rec_ppg and not buffer_start_time['recording_started']:
        data_buffers['ppg']['green'].clear()
        data_buffers['ppg']['red'].clear()
        data_buffers['ppg']['ir'].clear()

    if _is_rec_ppg:
        _streamer_ppg = collector.device_manager.get_streamer()
        if _streamer_ppg:
            try:
                ppg_data = _streamer_ppg.DATA.get("RAW", {}).get("PPG")
                if ppg_data is not None and hasattr(ppg_data, 'shape') and ppg_data.shape[0] > 0:
                    # PPG data shape is [N, 4]: timestamp, green, red, IR
                    latest_ppg = ppg_data[-1, 1:]  # Skip timestamp, get G, R, IR
                    _current_time_ppg = time.time() - buffer_start_time['time']
                    data_buffers['ppg']['green'].append((_current_time_ppg, latest_ppg[0]))
                    data_buffers['ppg']['red'].append((_current_time_ppg, latest_ppg[1]))
                    data_buffers['ppg']['ir'].append((_current_time_ppg, latest_ppg[2]))
            except Exception as e:
                pass

    # Create PPG plot
    if any(len(data_buffers['ppg'][ch]) > 0 for ch in ['green', 'red', 'ir']):
        ppg_fig = go.Figure()

        for _channel_ppg, _color_ppg in [('green', 'green'), ('red', 'red'), ('ir', 'darkred')]:
            if data_buffers['ppg'][_channel_ppg]:
                _times_ppg, _values_ppg = zip(*data_buffers['ppg'][_channel_ppg])
                ppg_fig.add_trace(go.Scatter(
                    x=_times_ppg, y=_values_ppg,
                    mode='lines',
                    name=f'{_channel_ppg.upper()}',
                    line=dict(color=_color_ppg, width=2)
                ))

        ppg_fig.update_layout(
            title=f'PPG (Photoplethysmography) (n={len(data_buffers["ppg"]["green"])})',
            xaxis_title='Time (s)',
            yaxis_title='Intensity',
            height=500,
            showlegend=True
        )
    else:
        ppg_fig = go.Figure()
        ppg_fig.add_annotation(
            text="Waiting for PPG data...",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14)
        )
        ppg_fig.update_layout(title='PPG (Photoplethysmography)', height=500)

    ppg_plot = mo.ui.plotly(ppg_fig)
    return (ppg_plot,)


@app.cell
def _(mo):
    # Heart Rate refresh control
    refresh_hr = mo.ui.refresh(options=["1s", "2s", "5s"], default_interval="2s")
    return (refresh_hr,)


@app.cell
def _(buffer_start_time, collector, data_buffers, go, mo, refresh_hr, refresh_recording_status, time):
    # Heart Rate visualization
    refresh_hr
    refresh_recording_status

    hr_fig = go.Figure()

    if collector.is_recording and collector.device_manager.is_connected():
        _streamer_hr = collector.device_manager.get_streamer()
        if _streamer_hr and hasattr(_streamer_hr, 'SCORES'):
            try:
                hr_value = _streamer_hr.SCORES.get('hr')
                if hr_value is not None:
                    _current_time_hr = time.time() - buffer_start_time['time']
                    data_buffers['hr'].append((_current_time_hr, int(hr_value)))
            except Exception as e:
                pass

    # Create HR plot
    if len(data_buffers['hr']) > 0:
        hr_fig = go.Figure()

        _times_hr, _values_hr = zip(*data_buffers['hr'])
        hr_fig.add_trace(go.Scatter(
            x=_times_hr, y=_values_hr,
            mode='lines+markers',
            name='Heart Rate',
            line=dict(color='red', width=3),
            marker=dict(size=4)
        ))

        hr_fig.update_layout(
            title=f'Heart Rate (n={len(data_buffers["hr"])})',
            xaxis_title='Time (s)',
            yaxis_title='BPM',
            height=300,
            showlegend=False,
            yaxis=dict(range=[40, 180])  # Typical HR range
        )
    else:
        hr_fig = go.Figure()
        hr_fig.add_annotation(
            text="Waiting for HR data...",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14)
        )
        hr_fig.update_layout(title='Heart Rate', height=300)

    hr_plot = mo.ui.plotly(hr_fig)
    return (hr_plot,)


@app.cell
def _(mo):
    # SpO2 refresh control
    refresh_spo2 = mo.ui.refresh(options=["1s", "2s", "5s"], default_interval="2s")
    return (refresh_spo2,)


@app.cell
def _(buffer_start_time, collector, data_buffers, go, mo, refresh_recording_status, refresh_spo2, time):
    # SpO2 visualization
    refresh_spo2
    refresh_recording_status

    spo2_fig = go.Figure()

    if collector.is_recording and collector.device_manager.is_connected():
        _streamer_spo2 = collector.device_manager.get_streamer()
        if _streamer_spo2 and hasattr(_streamer_spo2, 'SCORES'):
            try:
                spo2_value = _streamer_spo2.SCORES.get('spo2')
                if spo2_value is not None:
                    _current_time_spo2 = time.time() - buffer_start_time['time']
                    data_buffers['spo2'].append((_current_time_spo2, int(spo2_value)))
            except Exception as e:
                pass

    # Create SpO2 plot
    if len(data_buffers['spo2']) > 0:
        spo2_fig = go.Figure()

        _times_spo2, _values_spo2 = zip(*data_buffers['spo2'])

        # Color code based on SpO2 level (green: >95, yellow: 90-95, red: <90)
        _colors_spo2 = ['green' if v > 95 else 'orange' if v > 90 else 'red' for v in _values_spo2]

        spo2_fig.add_trace(go.Scatter(
            x=_times_spo2, y=_values_spo2,
            mode='lines+markers',
            name='SpO2',
            line=dict(color='blue', width=3),
            marker=dict(size=4, color=_colors_spo2)
        ))

        spo2_fig.update_layout(
            title=f'SpO2 (Blood Oxygen Saturation) (n={len(data_buffers["spo2"])})',
            xaxis_title='Time (s)',
            yaxis_title='SpO2 (%)',
            height=300,
            showlegend=False,
            yaxis=dict(range=[85, 100])  # Typical SpO2 range
        )
    else:
        spo2_fig = go.Figure()
        spo2_fig.add_annotation(
            text="Waiting for SpO2 data...",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14)
        )
        spo2_fig.update_layout(title='SpO2 (Blood Oxygen Saturation)', height=300)

    spo2_plot = mo.ui.plotly(spo2_fig)
    return (spo2_plot,)


@app.cell
def _(
    focus_plot,
    hr_plot,
    imu_plot,
    mo,
    poas_plot,
    power_plot,
    ppg_plot,
    refresh_focus,
    refresh_hr,
    refresh_imu,
    refresh_poas,
    refresh_power,
    refresh_ppg,
    refresh_signal,
    refresh_spo2,
    signal_plot,
    spo2_plot,
):
    # Display visualization tabs with hidden refresh controls
    tabs = mo.ui.tabs({
        "Focus": focus_plot,
        "POAS": poas_plot,
        "Power Bands": power_plot,
        "Signal Quality": signal_plot,
        "IMU": imu_plot,
        "PPG": ppg_plot,
        "Heart Rate": hr_plot,
        "SpO2": spo2_plot
    })

    # Display tabs and hidden refresh timers
    mo.vstack([
        tabs,
        mo.Html(f"""
        <div style='display:none'>
            {refresh_focus}
            {refresh_poas}
            {refresh_power}
            {refresh_signal}
            {refresh_imu}
            {refresh_ppg}
            {refresh_hr}
            {refresh_spo2}
        </div>
        """)
    ])
    return


@app.cell
def _(mo):
    mo.md("""## Event Annotation""")
    return


@app.cell
def _(mo):
    # Create event controls - use run_button for action buttons
    event_input = mo.ui.text_area(
        placeholder="Enter event description...",
        rows=3,
        full_width=True
    )
    add_event_button = mo.ui.run_button(label="Add Event", kind="success")
    return add_event_button, event_input


@app.cell
def _(add_event_button, collector, data_buffers, event_input):
    # Handle event logging first
    if add_event_button.value and event_input.value and collector.event_logger:
        try:
            _event = collector.event_logger.log_event(
                description=event_input.value,
                category="other"  # Default category
            )
            # Add to buffer for display
            data_buffers['events'].append(_event)
        except Exception as e:
            print(f"Error logging event: {e}")
    return


@app.cell
def _(add_event_button, collector, event_input, mo, refresh_recording_status):
    # Display event controls and count
    # Use refresh_recording_status to update count without re-creating UI
    refresh_recording_status
    event_count = len(collector.event_logger._events) if collector.event_logger else 0

    mo.vstack([
        event_input,
        mo.hstack([
            add_event_button,
            mo.md(f"**Events logged:** {event_count}")
        ])
    ])
    return (event_count,)


@app.cell
def _(collector, data_buffers, datetime, mo):
    # Display recent events
    if collector.event_logger and data_buffers['events']:
        event_table_data = []
        for evt in list(data_buffers['events'])[-10:]:  # Show last 10 events
            event_table_data.append({
                "Time": datetime.fromtimestamp(evt['timestamp']).strftime("%H:%M:%S"),
                "Description": evt['description']
            })

        events_table = mo.ui.table(event_table_data, selection=None)
        mo.vstack([
            mo.md("### Recent Events"),
            events_table
        ])
    else:
        mo.md("### Recent Events\n*No events logged yet*")
    return


if __name__ == "__main__":
    app.run()
