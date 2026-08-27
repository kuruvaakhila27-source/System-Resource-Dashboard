import streamlit as st
import psutil
import pandas as pd
import plotly.graph_objects as go
import time
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

CPU_WARNING = 80
RAM_WARNING = 80
DISK_WARNING = 90

# =========================================================
# SESSION STATE
# =========================================================

if "history" not in st.session_state:
    st.session_state.history = []

if "last_update" not in st.session_state:
    st.session_state.last_update = None


# =========================================================
# CROSS-PLATFORM DISK PATH
# =========================================================

def get_disk_path():
    """
    Returns a disk path that works on both
    Windows and Linux/macOS.
    """

    if hasattr(psutil, "disk_partitions"):

        try:
            partitions = psutil.disk_partitions(
                all=False
            )

            for partition in partitions:

                try:
                    usage = psutil.disk_usage(
                        partition.mountpoint
                    )

                    return partition.mountpoint

                except (
                    PermissionError,
                    FileNotFoundError,
                    OSError
                ):
                    continue

        except Exception:
            pass

    # Linux / Streamlit Cloud fallback
    return "/"


# =========================================================
# SYSTEM INFORMATION
# =========================================================

def get_system_info():

    cpu = psutil.cpu_percent(
        interval=0.5
    )

    memory = psutil.virtual_memory()

    disk_path = get_disk_path()

    try:

        disk = psutil.disk_usage(
            disk_path
        )

    except (
        FileNotFoundError,
        PermissionError,
        OSError
    ):

        disk = psutil.disk_usage("/")

    network = psutil.net_io_counters()

    battery = psutil.sensors_battery()

    return {
        "cpu": cpu,
        "ram": memory.percent,
        "ram_used": memory.used / (1024 ** 3),
        "ram_total": memory.total / (1024 ** 3),
        "disk": disk.percent,
        "disk_used": disk.used / (1024 ** 3),
        "disk_total": disk.total / (1024 ** 3),
        "disk_path": disk_path,
        "upload": network.bytes_sent,
        "download": network.bytes_recv,
        "battery": (
            battery.percent
            if battery
            else None
        ),
        "charging": (
            battery.power_plugged
            if battery
            else None
        )
    }


# =========================================================
# NETWORK SPEED
# =========================================================

def get_network_speed():

    first = psutil.net_io_counters()

    time.sleep(0.5)

    second = psutil.net_io_counters()

    upload_speed = (
        second.bytes_sent
        - first.bytes_sent
    ) / 0.5

    download_speed = (
        second.bytes_recv
        - first.bytes_recv
    ) / 0.5

    return upload_speed, download_speed


# =========================================================
# PROCESS INFORMATION
# =========================================================

def get_processes():

    processes = []

    for process in psutil.process_iter(
        [
            "pid",
            "name",
            "cpu_percent",
            "memory_percent"
        ]
    ):

        try:

            info = process.info

            processes.append(
                {
                    "PID": info["pid"],
                    "Process": info["name"],
                    "CPU %": info[
                        "cpu_percent"
                    ],
                    "Memory %": round(
                        info[
                            "memory_percent"
                        ],
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

    df = pd.DataFrame(
        processes
    )

    if not df.empty:

        df = df.sort_values(
            "CPU %",
            ascending=False
        )

    return df


# =========================================================
# BYTE FORMATTER
# =========================================================

def format_bytes(value):

    if value < 1024:

        return f"{value:.0f} B/s"

    elif value < 1024 ** 2:

        return (
            f"{value / 1024:.2f} KB/s"
        )

    elif value < 1024 ** 3:

        return (
            f"{value / (1024 ** 2):.2f} MB/s"
        )

    else:

        return (
            f"{value / (1024 ** 3):.2f} GB/s"
        )


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
        "🔄 Refresh interval",
        min_value=1,
        max_value=10,
        value=3
    )

    st.divider()

    st.subheader(
        "⚠️ Alert Thresholds"
    )

    cpu_threshold = st.slider(
        "CPU warning (%)",
        min_value=50,
        max_value=100,
        value=CPU_WARNING
    )

    ram_threshold = st.slider(
        "RAM warning (%)",
        min_value=50,
        max_value=100,
        value=RAM_WARNING
    )

    disk_threshold = st.slider(
        "Disk warning (%)",
        min_value=50,
        max_value=100,
        value=DISK_WARNING
    )

    st.divider()

    if st.button(
        "🧹 Clear History",
        use_container_width=True
    ):

        st.session_state.history = []

        st.success(
            "History cleared."
        )

        st.rerun()


# =========================================================
# GET SYSTEM DATA
# =========================================================

system = get_system_info()

upload_speed, download_speed = (
    get_network_speed()
)

now = datetime.now()


# =========================================================
# SAVE HISTORY
# =========================================================

history_entry = {
    "Time": now.strftime(
        "%H:%M:%S"
    ),
    "CPU": system["cpu"],
    "RAM": system["ram"],
    "Disk": system["disk"]
}

st.session_state.history.append(
    history_entry
)

# Keep last 100 records

if len(
    st.session_state.history
) > 100:

    st.session_state.history = (
        st.session_state.history[-100:]
    )

st.session_state.last_update = now


# =========================================================
# TOP METRICS
# =========================================================

c1, c2, c3, c4 = st.columns(4)


with c1:

    st.metric(
        "🧠 CPU Usage",
        f"{system['cpu']:.1f}%"
    )


with c2:

    st.metric(
        "💾 RAM Usage",
        f"{system['ram']:.1f}%"
    )


with c3:

    st.metric(
        "💽 Disk Usage",
        f"{system['disk']:.1f}%"
    )


with c4:

    if system["battery"] is not None:

        battery_text = (
            f"{system['battery']:.0f}%"
        )

        if system["charging"]:

            battery_text += " ⚡"

        st.metric(
            "🔋 Battery",
            battery_text
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
        "✅ System resources are "
        "within normal limits."
    )


# =========================================================
# RESOURCE DETAILS
# =========================================================

st.divider()

st.subheader(
    "📊 Resource Details"
)

r1, r2, r3 = st.columns(3)


with r1:

    st.write("### 🧠 CPU")

    st.progress(
        min(
            int(system["cpu"]),
            100
        )
    )

    st.write(
        f"Current usage: "
        f"**{system['cpu']:.1f}%**"
    )

    st.write(
        f"Logical CPUs: "
        f"**{psutil.cpu_count()}**"
    )


with r2:

    st.write("### 💾 Memory")

    st.progress(
        min(
            int(system["ram"]),
            100
        )
    )

    st.write(
        f"Used: "
        f"**{system['ram_used']:.2f} GB**"
    )

    st.write(
        f"Total: "
        f"**{system['ram_total']:.2f} GB**"
    )


with r3:

    st.write("### 💽 Disk")

    st.progress(
        min(
            int(system["disk"]),
            100
        )
    )

    st.write(
        f"Used: "
        f"**{system['disk_used']:.2f} GB**"
    )

    st.write(
        f"Total: "
        f"**{system['disk_total']:.2f} GB**"
    )

    st.caption(
        f"Monitoring: `{system['disk_path']}`"
    )


# =========================================================
# NETWORK
# =========================================================

st.divider()

st.subheader(
    "🌐 Network Activity"
)

n1, n2 = st.columns(2)


with n1:

    st.metric(
        "⬆️ Upload Speed",
        format_bytes(
            upload_speed
        )
    )


with n2:

    st.metric(
        "⬇️ Download Speed",
        format_bytes(
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
        "Unable to retrieve running processes."
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
    "💡 About This Dashboard"
)

st.markdown(
    """
    This dashboard monitors system resources in real time
    using the Python `psutil` library.

    **Monitored resources:**

    - 🧠 CPU utilization
    - 💾 RAM utilization
    - 💽 Disk utilization
    - 🌐 Network activity
    - 🔋 Battery status
    - ⚙️ Running processes

    The application also provides configurable alerts,
    interactive charts, monitoring history and CSV export.
    """
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