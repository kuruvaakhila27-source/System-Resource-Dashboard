import streamlit as st
import psutil
import pandas as pd
import plotly.graph_objects as go
import time
import os
from datetime import datetime

# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="System Resource Dashboard",
    page_icon="🖥️",
    layout="wide"
)

# =========================================================
# CONSTANTS
# =========================================================

DEFAULT_CPU_WARNING = 80
DEFAULT_RAM_WARNING = 80
DEFAULT_DISK_WARNING = 90


# =========================================================
# SESSION STATE
# =========================================================

if "history" not in st.session_state:
    st.session_state.history = []

if "previous_network" not in st.session_state:
    st.session_state.previous_network = None

if "previous_network_time" not in st.session_state:
    st.session_state.previous_network_time = None


# =========================================================
# SAFE DISK PATH
# =========================================================

def get_disk_path():

    # Windows
    if os.name == "nt":

        path = os.environ.get(
            "SystemDrive",
            "C:"
        )

        if os.path.exists(path):
            return path

        return "C:"

    # Linux / Streamlit Cloud / macOS
    return "/"


# =========================================================
# SAFE DISK USAGE
# =========================================================

def get_disk_usage():

    possible_paths = []

    if os.name == "nt":

        system_drive = os.environ.get(
            "SystemDrive",
            "C:"
        )

        possible_paths.append(
            system_drive
        )

    possible_paths.append("/")

    for path in possible_paths:

        try:

            if os.path.exists(path):

                return (
                    psutil.disk_usage(path),
                    path
                )

        except (
            FileNotFoundError,
            PermissionError,
            OSError
        ):
            continue

    return None, "Unavailable"


# =========================================================
# SAFE BATTERY
# =========================================================

def get_battery():

    try:

        battery = psutil.sensors_battery()

        if battery is None:
            return None

        return {
            "percent": battery.percent,
            "charging": battery.power_plugged
        }

    except (
        FileNotFoundError,
        PermissionError,
        OSError,
        AttributeError
    ):

        return None


# =========================================================
# SAFE NETWORK
# =========================================================

def get_network():

    try:

        network = psutil.net_io_counters()

        if network is None:
            return None

        return {
            "sent": network.bytes_sent,
            "received": network.bytes_recv
        }

    except (
        FileNotFoundError,
        PermissionError,
        OSError
    ):

        return None


# =========================================================
# SYSTEM INFORMATION
# =========================================================

def get_system_info():

    # CPU
    try:

        cpu = psutil.cpu_percent(
            interval=0.3
        )

    except Exception:

        cpu = 0


    # RAM
    try:

        memory = psutil.virtual_memory()

        ram_percent = memory.percent
        ram_used = memory.used / (
            1024 ** 3
        )
        ram_total = memory.total / (
            1024 ** 3
        )

    except Exception:

        ram_percent = 0
        ram_used = 0
        ram_total = 0


    # Disk
    disk, disk_path = get_disk_usage()

    if disk is not None:

        disk_percent = disk.percent

        disk_used = disk.used / (
            1024 ** 3
        )

        disk_total = disk.total / (
            1024 ** 3
        )

    else:

        disk_percent = 0
        disk_used = 0
        disk_total = 0


    # Network
    network = get_network()


    # Battery
    battery = get_battery()


    return {
        "cpu": cpu,
        "ram": ram_percent,
        "ram_used": ram_used,
        "ram_total": ram_total,
        "disk": disk_percent,
        "disk_used": disk_used,
        "disk_total": disk_total,
        "disk_path": disk_path,
        "network": network,
        "battery": battery
    }


# =========================================================
# NETWORK SPEED
# =========================================================

def calculate_network_speed():

    current = get_network()

    if current is None:
        return 0, 0

    current_time = time.time()

    previous = (
        st.session_state.previous_network
    )

    previous_time = (
        st.session_state.previous_network_time
    )

    st.session_state.previous_network = current

    st.session_state.previous_network_time = (
        current_time
    )

    if previous is None or previous_time is None:

        return 0, 0

    elapsed = current_time - previous_time

    if elapsed <= 0:
        return 0, 0

    upload = (
        current["sent"]
        - previous["sent"]
    ) / elapsed

    download = (
        current["received"]
        - previous["received"]
    ) / elapsed

    return upload, download


# =========================================================
# BYTE FORMATTER
# =========================================================

def format_speed(value):

    if value < 1024:

        return f"{value:.0f} B/s"

    if value < 1024 ** 2:

        return (
            f"{value / 1024:.2f} KB/s"
        )

    if value < 1024 ** 3:

        return (
            f"{value / (1024 ** 2):.2f} MB/s"
        )

    return (
        f"{value / (1024 ** 3):.2f} GB/s"
    )


# =========================================================
# PROCESS INFORMATION
# =========================================================

def get_processes():

    rows = []

    try:

        processes = psutil.process_iter(
            [
                "pid",
                "name",
                "cpu_percent",
                "memory_percent"
            ]
        )

        for process in processes:

            try:

                info = process.info

                rows.append(
                    {
                        "PID": info.get(
                            "pid",
                            "N/A"
                        ),
                        "Process": info.get(
                            "name",
                            "Unknown"
                        ),
                        "CPU %": round(
                            info.get(
                                "cpu_percent",
                                0
                            ) or 0,
                            2
                        ),
                        "Memory %": round(
                            info.get(
                                "memory_percent",
                                0
                            ) or 0,
                            2
                        )
                    }
                )

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess
            ):

                continue

    except Exception:

        return pd.DataFrame(
            columns=[
                "PID",
                "Process",
                "CPU %",
                "Memory %"
            ]
        )


    df = pd.DataFrame(rows)

    if not df.empty:

        df = df.sort_values(
            "CPU %",
            ascending=False
        )

    return df


# =========================================================
# HEADER
# =========================================================

st.title(
    "🖥️ System Resource Dashboard"
)

st.caption(
    "Real-time monitoring of CPU, RAM, disk, "
    "network, battery and running processes."
)


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.header(
        "⚙️ Dashboard Controls"
    )

    refresh_rate = st.slider(
        "🔄 Refresh Interval",
        min_value=2,
        max_value=10,
        value=3
    )

    st.divider()

    st.subheader(
        "⚠️ Alert Thresholds"
    )

    cpu_threshold = st.slider(
        "CPU Warning (%)",
        min_value=50,
        max_value=100,
        value=DEFAULT_CPU_WARNING
    )

    ram_threshold = st.slider(
        "RAM Warning (%)",
        min_value=50,
        max_value=100,
        value=DEFAULT_RAM_WARNING
    )

    disk_threshold = st.slider(
        "Disk Warning (%)",
        min_value=50,
        max_value=100,
        value=DEFAULT_DISK_WARNING
    )

    st.divider()

    if st.button(
        "🧹 Clear History",
        use_container_width=True
    ):

        st.session_state.history = []

        st.success(
            "Monitoring history cleared."
        )

        st.rerun()


# =========================================================
# GET SYSTEM DATA
# =========================================================

system = get_system_info()

upload_speed, download_speed = (
    calculate_network_speed()
)

current_time = datetime.now()

# =========================================================
# HISTORY
# =========================================================

history_record = {
    "Time": current_time.strftime(
        "%H:%M:%S"
    ),
    "CPU": round(
        system["cpu"],
        2
    ),
    "RAM": round(
        system["ram"],
        2
    ),
    "Disk": round(
        system["disk"],
        2
    )
}

st.session_state.history.append(
    history_record
)

# Keep latest 100 records

if len(
    st.session_state.history
) > 100:

    st.session_state.history = (
        st.session_state.history[-100:]
    )


# =========================================================
# TOP METRICS
# =========================================================

col1, col2, col3, col4 = st.columns(4)


with col1:

    st.metric(
        "🧠 CPU Usage",
        f"{system['cpu']:.1f}%"
    )


with col2:

    st.metric(
        "💾 RAM Usage",
        f"{system['ram']:.1f}%"
    )


with col3:

    st.metric(
        "💽 Disk Usage",
        f"{system['disk']:.1f}%"
    )


with col4:

    battery = system["battery"]

    if battery is not None:

        battery_value = (
            f"{battery['percent']:.0f}%"
        )

        if battery["charging"]:

            battery_value += " ⚡"

        st.metric(
            "🔋 Battery",
            battery_value
        )

    else:

        st.metric(
            "🔋 Battery",
            "N/A"
        )


# =========================================================
# ALERTS
# =========================================================

st.divider()

st.subheader(
    "🚨 System Alerts"
)

alerts = []


if system["cpu"] >= cpu_threshold:

    alerts.append(
        f"🧠 CPU usage is high: "
        f"{system['cpu']:.1f}%"
    )


if system["ram"] >= ram_threshold:

    alerts.append(
        f"💾 RAM usage is high: "
        f"{system['ram']:.1f}%"
    )


if system["disk"] >= disk_threshold:

    alerts.append(
        f"💽 Disk usage is high: "
        f"{system['disk']:.1f}%"
    )


if alerts:

    for alert in alerts:

        st.warning(alert)

else:

    st.success(
        "✅ All monitored resources "
        "are within normal limits."
    )


# =========================================================
# RESOURCE DETAILS
# =========================================================

st.divider()

st.subheader(
    "📊 Resource Details"
)

resource1, resource2, resource3 = (
    st.columns(3)
)


# CPU
with resource1:

    st.write(
        "### 🧠 CPU"
    )

    st.progress(
        min(
            int(system["cpu"]),
            100
        )
    )

    st.write(
        f"Usage: **{system['cpu']:.1f}%**"
    )

    try:

        cpu_count = psutil.cpu_count()

    except Exception:

        cpu_count = "N/A"

    st.write(
        f"Logical CPUs: **{cpu_count}**"
    )


# RAM
with resource2:

    st.write(
        "### 💾 Memory"
    )

    st.progress(
        min(
            int(system["ram"]),
            100
        )
    )

    st.write(
        f"Used: **{system['ram_used']:.2f} GB**"
    )

    st.write(
        f"Total: **{system['ram_total']:.2f} GB**"
    )


# Disk
with resource3:

    st.write(
        "### 💽 Disk"
    )

    st.progress(
        min(
            int(system["disk"]),
            100
        )
    )

    st.write(
        f"Used: **{system['disk_used']:.2f} GB**"
    )

    st.write(
        f"Total: **{system['disk_total']:.2f} GB**"
    )

    st.caption(
        f"Drive: `{system['disk_path']}`"
    )


# =========================================================
# NETWORK
# =========================================================

st.divider()

st.subheader(
    "🌐 Network Activity"
)

network1, network2 = st.columns(2)


with network1:

    st.metric(
        "⬆️ Upload Speed",
        format_speed(
            upload_speed
        )
    )


with network2:

    st.metric(
        "⬇️ Download Speed",
        format_speed(
            download_speed
        )
    )


# =========================================================
# LIVE RESOURCE CHART
# =========================================================

st.divider()

st.subheader(
    "📈 Live Resource Usage"
)

if st.session_state.history:

    history_df = pd.DataFrame(
        st.session_state.history
    )

    fig = go.Figure()


    fig.add_trace(
        go.Scatter(
            x=history_df["Time"],
            y=history_df["CPU"],
            mode="lines+markers",
            name="CPU %"
        )
    )


    fig.add_trace(
        go.Scatter(
            x=history_df["Time"],
            y=history_df["RAM"],
            mode="lines+markers",
            name="RAM %"
        )
    )


    fig.add_trace(
        go.Scatter(
            x=history_df["Time"],
            y=history_df["Disk"],
            mode="lines+markers",
            name="Disk %"
        )
    )


    fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Usage (%)",
        yaxis=dict(
            range=[0, 100]
        ),
        height=450
    )


    st.plotly_chart(
        fig,
        use_container_width=True
    )


# =========================================================
# RUNNING PROCESSES
# =========================================================

st.divider()

st.subheader(
    "⚙️ Running Processes"
)

process_df = get_processes()

if not process_df.empty:

    st.dataframe(
        process_df.head(15),
        use_container_width=True,
        hide_index=True
    )

else:

    st.info(
        "Process information is unavailable "
        "on this environment."
    )


# =========================================================
# MONITORING HISTORY
# =========================================================

st.divider()

st.subheader(
    "🕒 Monitoring History"
)

if st.session_state.history:

    history_df = pd.DataFrame(
        st.session_state.history
    )

    st.dataframe(
        history_df,
        use_container_width=True,
        hide_index=True
    )


    csv_data = history_df.to_csv(
        index=False
    )


    st.download_button(
        "⬇️ Download System History",
        data=csv_data,
        file_name=(
            "system_resource_history.csv"
        ),
        mime="text/csv",
        use_container_width=True
    )

else:

    st.info(
        "No monitoring history available."
    )


# =========================================================
# PROJECT INFORMATION
# =========================================================

st.divider()

st.subheader(
    "💡 How This Project Works"
)

st.markdown(
    """
    ### 1️⃣ System Data Collection

    The application uses Python's `psutil` library
    to collect system resource information.

    ### 2️⃣ Resource Monitoring

    The dashboard monitors:

    - 🧠 CPU usage
    - 💾 RAM usage
    - 💽 Disk usage
    - 🌐 Network activity
    - 🔋 Battery status
    - ⚙️ Running processes

    ### 3️⃣ Alerts

    Configurable thresholds detect high CPU,
    RAM and disk utilization.

    ### 4️⃣ Visualization

    Resource usage is displayed using interactive
    Plotly charts.

    ### 5️⃣ History

    Recent monitoring readings are stored in the
    current application session.

    ### 6️⃣ Export

    Monitoring history can be downloaded as CSV.
    """
)


# =========================================================
# PLATFORM NOTE
# =========================================================

st.info(
    "💡 When deployed on Streamlit Cloud, the dashboard "
    "monitors the cloud server rather than your personal PC. "
    "Battery information may show N/A because cloud servers "
    "normally do not expose a physical battery."
)


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "🖥️ System Resource Dashboard • "
    "Built with Python + Streamlit + psutil"
)


# =========================================================
# AUTO REFRESH
# =========================================================

time.sleep(
    refresh_rate
)

st.rerun()