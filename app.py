"Khwezi Mining - Health, Safety and Equipment Monitoring App."

import time
from datetime import date, datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from core import alerts
from core import analysis
from core import auth
from core import config
from core import data_loader
from core import equipment
from core import incidents
from core import reports
from core import risk
from core import safety
from core import validators


st.set_page_config(
    page_title = "Khwezi Mining Monitor",
    page_icon = "⛏️",
    layout = "wide"
)

AMBER = "#C77700"
CHARCOAL = "#2B2B2B"

STATUS_LABEL = {
    "CRITICAL": "🔴 CRITICAL",
    "WARNING": "🟠 WARNING",
    "NORMAL": "🟢 NORMAL",
    "OK": "🟢 OK"
}

CONDITION_COLOURS = {
    "NORMAL": "#2E7D32",
    "WARNING": "#EF8F00",
    "CRITICAL": "#C62828"
}


st.markdown(
    """
    <style>
    .block-container {padding-top: 1.5rem;}
    h1, h2, h3 {color: #2B2B2B;}
    [data-testid = "stMetric"] {
        background:#F3F1EC;
        border-left: 6px solid #C77700;
        padding: 10px 14px;
        border-radius: 6px;
    }
    .banner {
        background:#2B2B2B;
        color:#fff;
        padding:14px 20px;
        border-radius:8px;
        border-bottom:5px solid #C77700;
        margin-bottom:12px;
    }
    .banner h2 {color:#fff; margin:0;}
    .banner p {margin:0; color:#E0DCD0;}
    </style>
    """,
    unsafe_allow_html = True
)


# Small helper functions

def flash_message(kind, message):
    st.session_state["flash"] = (kind, message)


def show_flash():
    if "flash" not in st.session_state:
        return

    kind, message = st.session_state.pop("flash")
    getattr(st, kind)(message)


def show_errors(errors):
    for error in errors:
        st.error(error)


def show_table(data, **kwargs):
    if data is None or len(data) == 0:
        st.info("No records to display.")
        return

    st.dataframe(data, hide_index = True, **kwargs)


def add_status_labels(data, columns):
    result = data.copy()

    for column in columns:
        if column in result:
            result[column] = result[column].map(
                lambda value: STATUS_LABEL.get(value, value)
            )

    return result


def show_chart(chart_info, data):
    if not chart_info or data is None or len(data) == 0:
        return

    chart_type = chart_info["kind"]
    x_value = chart_info["x"]
    y_value = chart_info["y"]
    title = chart_info["title"]

    if chart_type == "bar":
        figure = px.bar(
            data,
            x = x_value,
            y = y_value,
            title = title,
            color_discrete_sequence = [AMBER]
        )
    elif chart_type == "line":
        figure = px.line(
            data,
            x = x_value,
            y = y_value,
            title = title,
            markers = True,
            color_discrete_sequence =[AMBER]
        )
    else:
        figure = px.pie(
            data,
            names = x_value,
            values = y_value,
            title = title,
            color = x_value,
            color_discrete_map = CONDITION_COLOURS,
            color_discrete_sequence = px.colors.sequential.Oranges_r
        )

    figure.update_layout(margin = dict(l = 10, r = 10, t = 50, b = 10))
    st.plotly_chart(figure)


def show_metrics(items, items_per_row = 4):
    items = list(items)

    for start in range(0, len(items), items_per_row):
        columns = st.columns(items_per_row)

        for column, (label, value) in zip(
            columns, items[start:start + items_per_row]
        ):
            column.metric(label, value)


# a) Login Portal [Access Control]

def login_page():
    st.markdown(
        '<div class = "banner"><h2>⛏️ Khwezi Mining Monitor</h2>'
        '<p>Health, Safety and Equipment Monitoring - secure login</p></div>',
        unsafe_allow_html = True
    )

    locked_until = st.session_state.get("locked_until", 0)

    if time.time() < locked_until:
        remaining = int(locked_until - time.time())
        st.error(
            f"Too many failed attempts. Try again in {remaining} seconds."
        )
        return

    _, middle, _ = st.columns([1, 1.2, 1])

    with middle:
        with st.form("login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type = "password")
            login_clicked = st.form_submit_button("Log in")

        if login_clicked:
            user = auth.authenticate(username, password)

            if user:
                st.session_state.update(user = user, attempts = 0)
                st.rerun()

            st.session_state["attempts"] = (
                st.session_state.get("attempts", 0) + 1
            )

            attempts_left = (
                auth.MAX_ATTEMPTS - st.session_state["attempts"]
            )

            if attempts_left <= 0:
                st.session_state["locked_until"] = time.time() + 30
                st.session_state["attempts"] = 0
                st.error(
                    "Too many failed attempts. Login locked for 30 seconds."
                )
            else:
                st.error(
                    "Invalid username/password, or the account is inactive. "
                    f"{attempts_left} attempt(s) left."
                )

        with st.expander("Demo accounts (prototype only)"):
            demo_accounts = pd.DataFrame({
                "Role": config.ROLES,
                "Username": [
                    "admin", "safety", "engineer", "maint", "manager"
                ],
                "Password": [
                    "Admin@123",
                    "Safety@123",
                    "Mining@123",
                    "Maint@123",
                    "Manager@123"
                ]
            })
            st.table(demo_accounts)


# Dashboard

def page_dashboard(bundle, user):
    role = user["role"]

    st.header("Khwezi Mining Monitoring Dashboard")
    show_metrics(data_loader.kpis(bundle, role).items())

    alert_data = alerts.filter_by_permissions(bundle.alerts, role)

    left, right = st.columns(2)

    with left:
        if role in config.PERMISSIONS["incidents"]:
            show_chart(
                {
                    "kind": "line",
                    "x": "month",
                    "y": "incidents",
                    "title": "Safety incidents per month"
                },
                incidents.monthly_trend(bundle.incidents)
            )

        if role in config.PERMISSIONS["equipment"]:
            equipment_summary = (
                bundle.equipment
                .groupby("equipment_type")["availability"]
                .mean()
                .round(1)
                .reset_index()
            )

            show_chart(
                {
                    "kind": "bar",
                    "x": "equipment_type",
                    "y": "availability",
                    "title": "Average availability by equipment type (%)"
                },
                equipment_summary
            )

    with right:
        if role in config.PERMISSIONS["equipment"]:
            condition_summary = (
                bundle.equipment["condition"]
                .value_counts()
                .rename_axis("condition")
                .reset_index(name="count")
            )

            show_chart(
                {
                    "kind": "pie",
                    "x": "condition",
                    "y": "count",
                    "title": "Equipment condition"
                },
                condition_summary
            )

        if len(alert_data):
            alert_summary = (
                alert_data.groupby(["category", "severity"])
                .size()
                .reset_index(name="alerts")
            )

            figure = px.bar(
                alert_summary,
                x="category",
                y="alerts",
                color="severity",
                title="Active alerts by category",
                color_discrete_map={
                    "CRITICAL": "#C62828",
                    "WARNING": "#EF8F00"
                }
            )
            st.plotly_chart(figure)

    st.subheader("Top critical alerts")

    critical = (
        alert_data[alert_data["severity"] == "CRITICAL"].head(8)
        if len(alert_data)
        else alert_data
    )

    if len(critical):
        critical = critical[
            [
                "alert_id",
                "severity",
                "category",
                "entity_id",
                "parameter",
                "value",
                "status"
            ]
        ]
        show_table(add_status_labels(critical, ["severity"]))
    else:
        show_table(critical)


# Alerts

def page_alerts(bundle, user):
    st.header("Alerts and Notifications")

    alert_data = alerts.filter_by_permissions(bundle.alerts, user["role"])

    if alert_data.empty:
        st.success("No active alerts.")
        return

    left, right = st.columns(2)

    severity = left.multiselect(
        "Severity",
        ["CRITICAL", "WARNING"],
        default=["CRITICAL", "WARNING"]
    )

    category = right.multiselect(
        "Category",
        sorted(alert_data["category"].unique()),
        default=sorted(alert_data["category"].unique())
    )

    filtered = alert_data[
        alert_data["severity"].isin(severity)
        & alert_data["category"].isin(category)
    ]

    st.caption(f"{len(filtered)} alerts shown")
    show_table(add_status_labels(filtered, ["severity"]))

    st.subheader("Alert notice")

    if len(filtered):
        selected = st.selectbox(
            "Select analysis alert to view the formatted notice",
            filtered["alert_id"]
            + " - "
            + filtered["entity_id"]
            + " - "
            + filtered["parameter"]
        )

        alert_id = selected.split(" - ")[0]
        row = filtered[filtered["alert_id"] == alert_id].iloc[0]

        st.code(alerts.format_alert_text(row), language=None)

        st.download_button(
            "Download all alerts (CSV)",
            filtered.to_csv(index=False),
            "alerts.csv",
            "text/csv"
        )


# b) Worker Health and Safety Monitoring

def page_workers(bundle, user):
    st.header("Worker Health and Safety Monitoring")
    show_flash()

    workers = bundle.workers

    overview, unsafe, register, add_worker = st.tabs(
        ["Overview", "Unsafe conditions", "Worker register", "Add worker"]
    )

    with overview:
        show_metrics([
            ("Total workers", len(workers)),
            ("PPE compliance (%)", safety.ppe_compliance_rate(workers)),
            ("Near misses", int(workers["near_misses"].sum())),
            (
                "High/critical risk",
                int(
                    workers["risk_class"]
                    .isin(["High", "Critical"])
                    .sum()
                )
            )
        ])

        summary = safety.department_summary(workers)
        show_table(summary)

        show_chart(
            {
                "kind": "bar",
                "x": "department",
                "y": "ppe_compliance_%",
                "title": "PPE compliance by department (%)"
            },
            summary
        )

    with unsafe:
        unsafe_workers = safety.unsafe_workers(workers)

        st.caption(
            f"{len(unsafe_workers)} workers have at least one warning."
        )

        critical_only = st.checkbox("Show CRITICAL only")

        if critical_only:
            unsafe_workers = unsafe_workers[
                unsafe_workers["worst"] == "CRITICAL"
            ]

        if len(unsafe_workers):
            columns = [
                "worker_id",
                "department",
                "shift",
                "worst",
                "warnings",
                "fatigue_level",
                "risk_score"
            ]
            show_table(add_status_labels(
                unsafe_workers[columns],
                ["worst"]
            ))
        else:
            show_table(unsafe_workers)

    with register:
        left, middle, right = st.columns(3)

        departments = left.multiselect("Department", config.DEPARTMENTS)
        shifts = middle.multiselect("Shift", config.SHIFTS)
        risk_classes = right.multiselect(
            "Risk class",
            [item[2] for item in config.RISK_BANDS]
        )

        filtered = workers

        if departments:
            filtered = filtered[
                filtered["department"].isin(departments)
            ]

        if shifts:
            filtered = filtered[filtered["shift"].isin(shifts)]

        if risk_classes:
            filtered = filtered[
                filtered["risk_class"].isin(risk_classes)
            ]

        st.caption(f"{len(filtered)} workers")
        show_table(filtered)

    with add_worker:
        with st.form("add_worker", clear_on_submit=True):
            first, second, third = st.columns(3)

            worker_id = first.text_input(
                "Worker ID",
                value=safety.next_worker_id(workers)
            )
            department = second.selectbox("Department", config.DEPARTMENTS)
            job_role = third.text_input("Job role")

            first, second, third = st.columns(3)

            shift = first.selectbox("Shift", config.SHIFTS)
            ppe = second.radio(
                "PPE compliant?",
                ["Yes", "No"],
                horizontal=True
            )
            training = third.selectbox(
                "Safety training status",
                config.TRAINING_STATUS
            )

            first, second, third, fourth = st.columns(4)

            fatigue = first.number_input(
                "Fatigue level (1-10)", 1, 10, 3
            )
            observations = second.number_input(
                "Safety observations", 0, 1000, 0
            )
            near_misses = third.number_input(
                "Near misses", 0, 1000, 0
            )
            previous_incidents = fourth.number_input(
                "Previous incidents", 0, 1000, 0
            )

            first, second = st.columns(2)

            likelihood = first.slider(
                "Likelihood (1-5)", 1, 5, 2
            )
            consequence = second.slider(
                "Consequence (1-5)", 1, 5, 2
            )

            submitted =st.form_submit_button("Add worker")

        if submitted:
            worker = {
                "worker_id": worker_id.strip().upper(),
                "department": department,
                "job_role": job_role.strip(),
                "shift": shift,
                "ppe_compliant": ppe,
                "training_status": training,
                "fatigue_level": fatigue,
                "safety_observations": observations,
                "near_misses": near_misses,
                "previous_incidents": previous_incidents,
                "likelihood": likelihood,
                "consequence": consequence
            }

            errors = validators.validate_worker(
                worker,
                workers["worker_id"]
            )

            if errors:
                show_errors(errors)
            else:
                raw = data_loader.read_workers()
                raw.loc[len(raw)] = worker
                data_loader.save("workers", raw)

                risk_score = likelihood * consequence
                warnings = safety.worker_warnings({
                    **worker,
                    "risk_score": risk_score,
                    "risk_class": risk.classify_risk(risk_score)
                })

                message = f"Worker {worker['worker_id']} added."

                if warnings:
                    message += " Warnings: " + "; ".join(
                        text for _, text in warnings
                    )

                flash_message("success", message)
                st.rerun()


# C) Safety incidents Database 

def page_incidents(bundle, user):
    st.header("Safety Incident Database")
    show_flash()

    incident_data = bundle.incidents

    view, add, categorise, trends = st.tabs(
        [
            "View / search / filter",
            "Add incident",
            "Categorise and count",
            "Trends"
        ]
    )

    with view:
        search = st.text_input(
            "Search (ID, location, cause, type, ...)"
        )

        first, second, third = st.columns(3)

        start_date = first.date_input(
            "From",
            incident_data["date"].min().date()
            if len(incident_data)
            else date.today()
        )
        end_date = second.date_input(
            "To",
            incident_data["date"].max().date()
            if len(incident_data)
            else date.today()
        )
        departments = third.multiselect(
            "Department",
            config.DEPARTMENTS
        )

        first, second, third, fourth = st.columns(4)

        shifts = first.multiselect("Shift", config.SHIFTS)
        incident_types = second.multiselect(
            "Incident type",
            config.INCIDENT_TYPES
        )
        severities = third.multiselect(
            "Severity",
            config.SEVERITIES
        )
        statuses = fourth.multiselect(
            "Status",
            config.INCIDENT_STATUS
        )

        if start_date > end_date:
            st.error("'From' date must not be after 'To' date.")
        else:
            filtered = incidents.filter_incidents(
                incident_data,
                start_date,
                end_date,
                departments,
                shifts,
                incident_types,
                severities,
                statuses
            )

            filtered = incidents.search_incidents(
                filtered,
                search
            ).copy()

            filtered["date"] = filtered["date"].dt.strftime("%Y-%m-%d")

            st.caption(f"{len(filtered)} incidents match.")
            show_table(filtered)

            if len(filtered):
                st.download_button(
                    "Download results (CSV)",
                    filtered.to_csv(index = False),
                    "incidents_filtered.csv",
                    "text/csv"
                )

    with add:
        with st.form("add_incident", clear_on_submit = True):
            first, second, third = st.columns(3)

            incident_date = first.date_input(
                "Date",
                date.today(),
                max_value=date.today()
            )
            incident_time = second.time_input(
                "Time",
                datetime.now().time().replace(
                    second =0,
                    microsecond=0
                )
            )
            location = third.selectbox(
                "Location",
                config.LOCATIONS
            )

            first, second, third = st.columns(3)

            department = first.selectbox(
                "Department",
                config.DEPARTMENTS
            )
            incident_type = second.selectbox(
                "Incident type",
                config.INCIDENT_TYPES
            )
            severity = third.selectbox(
                "Severity",
                config.SEVERITIES
            )

            first, second, third, fourth = st.columns(4)

            injury_status = first.selectbox(
                "Injury status",
                config.INJURY_STATUS
            )
            lost_time = second.radio(
                "Lost-time injury?",
                ["No", "Yes"],
                horizontal=True
            )
            cause = third.selectbox(
                "Cause",
                config.CAUSES
            )
            status = fourth.selectbox(
                "Incident status",
                config.INCIDENT_STATUS
            )

            corrective_action = st.text_input(
                "Corrective action (write 'Pending' if undecided)"
            )

            submitted = st.form_submit_button("Add incident")

        if submitted:
            time_text = incident_time.strftime("%H:%M")

            incident = {
                "incident_id": incidents.next_incident_id(
                    incident_data,
                    incident_date.year
                ),
                "date": incident_date.isoformat(),
                "time": time_text,
                "shift": incidents.shift_from_time(time_text),
                "location": location,
                "department": department,
                "incident_type": incident_type,
                "severity": severity,
                "injury_status": injury_status,
                "lost_time_injury": lost_time,
                "cause": cause,
                "corrective_action": corrective_action.strip(),
                "status": status
            }

            errors = validators.validate_incident(incident)

            if errors:
                show_errors(errors)
            else:
                raw = pd.read_csv(config.FILES["incidents"])
                raw.loc[len(raw)] = incident
                raw.to_csv(
                    config.FILES["incidents"],
                    index=False
                )

                message = (
                    f"Incident {incident['incident_id']} recorded "
                    f"(shift: {incident['shift']})."
                )

                if severity == "Critical":
                    message +=  " CRITICAL incident - escalate immediately."
                    flash_message("error", message)
                else:
                    flash_message("success", message)

                st.rerun()

    with categorise:
        group_by = st.selectbox(
            "Count incidents by",
            [
                "department",
                "shift",
                "incident_type",
                "severity",
                "location",
                "cause",
                "status",
                "injury_status",
                "lost_time_injury"
            ]
        )

        counts = incidents.count_by(incident_data, group_by)

        first, second = st.columns([1, 2])

        with first:
            show_table(counts)

        with second:
            show_chart(
                {
                    "kind": "bar",
                    "x": group_by,
                    "y": "count",
                    "title": f"Incidents by {group_by}"
                },
                counts
            )

        st.subheader("Incident type by severity")

        category_table = incidents.categorise(incident_data)

        if len(category_table):
            st.dataframe(category_table)

    with trends:
        show_chart(
            {
                "kind": "line",
                "x": "month",
                "y": "incidents",
                "title": "Incidents per month"
            },
            incidents.monthly_trend(incident_data)
        )

        if len(incident_data):
            monthly = (
                incident_data.assign(
                    month=incident_data["date"].dt.strftime("%Y-%m")
                )
                .groupby(["month", "shift"])
                .size()
                .reset_index(name = "incidents")
            )

            st.plotly_chart(
                px.line(
                    monthly,
                    x = "month",
                    y = "incidents",
                    color = "shift",
                    markers = True,
                    title = "Monthly incidents by shift"
                )
            )

            department_severity = (
                incident_data
                .groupby(["department", "severity"])
                .size()
                .reset_index(name = "incidents")
            )

            st.plotly_chart(
                px.bar(
                    department_severity,
                    x = "department",
                    y = "incidents",
                    color = "severity",
                    title = "Incidents by department and severity"
                )
            )


# Equipment Databadse and Condition Monitoring 

EQ_FIELDS = [
    "equipment_id",
    "equipment_type",
    "manufacturer",
    "department",
    "operating_hours",
    "temperature",
    "vibration",
    "fuel_consumption",
    "brake_status",
    "tyre_status",
    "engine_status",
    "maintenance_status",
    "uptime_hours",
    "downtime_hours",
    "last_service_date",
    "next_service_due",
    "alerts_30d"
]


def page_equipment(bundle, user):
    st.header("Equipment Database and Condition Monitoring")
    show_flash()

    equipment_data = bundle.equipment

    register, monitor, update, add = st.tabs(
        [
            "Equipment register",
            "Condition monitor",
            "Update readings",
            "Add equipment"
        ]
    )

    with register:
        first, second = st.columns(2)

        equipment_types = first.multiselect(
            "Equipment type",
            config.EQUIPMENT_TYPES
        )
        conditions = second.multiselect(
            "Condition",
            ["NORMAL", "WARNING", "CRITICAL"]
        )

        filtered = equipment_data

        if equipment_types:
            filtered = filtered[
                filtered["equipment_type"].isin(equipment_types)
            ]

        if conditions:
            filtered = filtered[
                filtered["condition"].isin(conditions)
            ]

        columns = [
            "equipment_id",
            "equipment_type",
            "manufacturer",
            "operating_hours",
            "temperature",
            "vibration",
            "fuel_consumption",
            "brake_status",
            "tyre_status",
            "engine_status",
            "maintenance_status",
            "downtime_hours",
            "availability",
            "condition"
        ]

        show_table(
            add_status_labels(filtered[columns], ["condition"])
        )

    with monitor:
        selected_id = st.selectbox(
            "Equipment",
            equipment_data["equipment_id"]
        )

        row = equipment_data[
            equipment_data["equipment_id"] == selected_id
        ].iloc[0]

        first, second, third = st.columns(3)

        first.metric(
            "Temperature (deg config)",
            row["temperature"],
            STATUS_LABEL[row["temp_status"]],
            delta_color="off"
        )
        second.metric(
            "Vibration (mm/s)",
            row["vibration"],
            STATUS_LABEL[row["vib_status"]],
            delta_color="off"
        )
        third.metric(
            "Availability (%)",
            row["availability"]
        )

        message = f"{row['condition']}: {row['condition_message']}"

        {
            "NORMAL": st.success,
            "WARNING": st.warning,
            "CRITICAL": st.error
        }[row["condition"]](message)

        st.caption(
            "Thresholds are educational prototype values only - "
            "not manufacturer or mine safety limits."
        )

        st.subheader("All units needing attention")

        attention = equipment_data[
            equipment_data["condition"] != "NORMAL"
        ].sort_values(
            "condition",
            ascending=False
        )

        if len(attention):
            columns = [
                "equipment_id",
                "equipment_type",
                "temperature",
                "vibration",
                "condition",
                "condition_message"
            ]
            show_table(
                add_status_labels(attention[columns], ["condition"])
            )
        else:
            show_table(attention)

    with update:
        selected_id = st.selectbox(
            "Equipment to update",
            equipment_data["equipment_id"],
            key="update_equipment"
        )

        row = equipment_data[
            equipment_data["equipment_id"] == selected_id
        ].iloc[0]

        with st.form("update_equipment_form"):
            first, second, third, fourth = st.columns(4)

            temperature = first.number_input(
                "Temperature (deg config)",
                -20.0,
                250.0,
                float(row["temperature"]),
                0.1
            )
            vibration = second.number_input(
                "Vibration (mm/s)",
                0.0,
                100.0,
                float(row["vibration"]),
                0.1
            )
            fuel = third.number_input(
                "Fuel (L/h)",
                0.0,
                1000.0,
                float(row["fuel_consumption"]),
                0.1
            )
            operating_hours = fourth.number_input(
                "Operating hours",
                0,
                10_000_000,
                int(row["operating_hours"])
            )

            first, second, third = st.columns(3)

            brake = first.selectbox(
                "Brake status",
                config.COMPONENT_STATUS,
                config.COMPONENT_STATUS.index(row["brake_status"])
            )
            tyre = second.selectbox(
                "Tyre status",
                config.COMPONENT_STATUS,
                config.COMPONENT_STATUS.index(row["tyre_status"])
            )
            engine = third.selectbox(
                "Engine status",
                config.COMPONENT_STATUS,
                config.COMPONENT_STATUS.index(row["engine_status"])
            )

            first, second, third = st.columns(3)

            uptime = first.number_input(
                "Uptime this period (h)",
                0.0,
                100000.0,
                float(row["uptime_hours"]),
                0.5
            )
            downtime = second.number_input(
                "Downtime this period (h)",
                0.0,
                100000.0,
                float(row["downtime_hours"]),
                0.5
            )
            maintenance = third.selectbox(
                "Maintenance status",
                config.MAINTENANCE_STATUS,
                config.MAINTENANCE_STATUS.index(row["maintenance_status"])
            )

            submitted = st.form_submit_button("Save reading")

        if submitted:
            updated = {
                "equipment_id": selected_id,
                "equipment_type": row["equipment_type"],
                "manufacturer": row["manufacturer"],
                "temperature": temperature,
                "vibration": vibration,
                "fuel_consumption": fuel,
                "operating_hours": operating_hours,
                "brake_status": brake,
                "tyre_status": tyre,
                "engine_status": engine,
                "uptime_hours": uptime,
                "downtime_hours": downtime,
                "maintenance_status": maintenance
            }

            errors = validators.validate_equipment(
                updated,
                is_new = False
            )

            if errors:
                show_errors(errors)
            else:
                raw = data_loader.read_equipment()
                index = raw.index[
                    raw["equipment_id"] == selected_id
                ][0]

                fields_to_update = [
                    "temperature",
                    "vibration",
                    "fuel_consumption",
                    "operating_hours",
                    "brake_status",
                    "tyre_status",
                    "engine_status",
                    "uptime_hours",
                    "downtime_hours",
                    "maintenance_status"
                ]

                for field in fields_to_update:
                    raw.loc[index, field] = updated[field]

                data_loader.save("equipment", raw)

                condition, messages = equipment.condition_report({
                    **row.to_dict(),
                    **updated
                })

                message = (
                    f"{selected_id}: {condition} - "
                    f"{' '.join(messages)}"
                )

                message_type = {
                    "NORMAL": "success",
                    "WARNING": "warning",
                    "CRITICAL": "error"
                }[condition]

                flash_message(message_type, message)
                st.rerun()

    with add:
        with st.form("add_equipment", clear_on_submit=True):
            first, second, third = st.columns(3)

            equipment_type = first.selectbox(
                "Equipment type",
                config.EQUIPMENT_TYPES
            )
            equipment_id = second.text_input(
                "Equipment ID (e.g. TRK-013)",
                value=equipment.next_equipment_id(
                    equipment_data,
                    config.EQUIPMENT_TYPES[0]
                )
            )
            manufacturer = third.text_input("Manufacturer")

            first, second, third = st.columns(3)

            department = first.selectbox(
                "Department",
                config.DEPARTMENTS
            )
            operating_hours = second.number_input(
                "Operating hours",
                0,
                10_000_000,
                0
            )
            maintenance_status = third.selectbox(
                "Maintenance status",
                config.MAINTENANCE_STATUS
            )

            submitted = st.form_submit_button("Add equipment")

        if submitted:
            new_equipment = {
                "equipment_id": equipment_id.strip().upper(),
                "equipment_type": equipment_type,
                "manufacturer": manufacturer.strip(),
                "temperature": 25.0,
                "vibration": 0.0,
                "operating_hours": operating_hours,
                "fuel_consumption": 0.0,
                "uptime_hours": 0.0,
                "downtime_hours": 0.0,
                "brake_status": "N/A",
                "tyre_status": "N/A",
                "engine_status": "OK",
                "maintenance_status": maintenance_status
            }

            errors = validators.validate_equipment(
                new_equipment,
                equipment_data["equipment_id"]
            )

            expected_prefix = config.EQUIPMENT_PREFIX.get(
                equipment_type,
                "???"
            )

            if not new_equipment["equipment_id"].startswith(
                expected_prefix + "-"
            ):
                errors.append(
                    f"ID for a {equipment_type} should start with "
                    f"{expected_prefix}-."
                )

            if errors:
                show_errors(errors)
            else:
                raw = data_loader.read_equipment()

                new_row = {
                    **new_equipment,
                    "department": department,
                    "last_service_date": pd.Timestamp(bundle.ref_date),
                    "next_service_due": (
                        pd.Timestamp(bundle.ref_date)
                        + pd.Timedelta(days=90)
                    ),
                    "alerts_30d": 0
                }

                raw.loc[len(raw)] = [
                    new_row[field]
                    for field in EQ_FIELDS
                ]

                data_loader.save("equipment", raw)

                flash_message(
                    "success",
                    f"Equipment {new_equipment['equipment_id']} added. "
                    "Use 'Update readings' to enter sensor values."
                )
                st.rerun()


# f) Equipment Maintanance Monitoring

def page_maintenance(bundle, user):
    st.header("Equipment Maintenance Monitoring")
    show_flash()

    equipment_data = bundle.equipment

    st.caption(
        "Availability = Operating Time / "
        "(Operating Time + Downtime) x 100"
    )

    maintenance_groups = equipment.maintenance_lists(equipment_data)

    show_metrics(
        [(name, len(data)) for name, data in maintenance_groups.items()],
        items_per_row = 6
    )

    tabs = st.tabs(
        list(maintenance_groups) + ["Log service"]
    )

    columns = [
        "equipment_id",
        "equipment_type",
        "department",
        "maintenance_state",
        "next_service_due",
        "downtime_hours",
        "availability",
        "alerts_30d"
    ]

    for tab, (name, data) in zip(
        tabs,
        maintenance_groups.items()
    ):
        with tab:
            if len(data):
                table = data[columns].copy()
                table["next_service_due"] = (
                    table["next_service_due"]
                    .dt.strftime("%Y-%m-%d")
                )
                show_table(table)
            else:
                show_table(data)

    with tabs[-1]:
        selected_id = st.selectbox(
            "Equipment",
            equipment_data["equipment_id"],
            key="service_equipment"
        )

        if st.button("Log service completed"):
            raw = data_loader.read_equipment()

            index = raw.index[
                raw["equipment_id"] == selected_id
            ][0]

            raw.loc[index, "last_service_date"] = (
                pd.Timestamp(bundle.ref_date)
            )
            raw.loc[index, "next_service_due"] = (
                pd.Timestamp(bundle.ref_date)
                + pd.Timedelta(days=90)
            )
            raw.loc[index, "maintenance_status"] = "Operational"
            raw.loc[index, "alerts_30d"] = 0

            data_loader.save("equipment", raw)

            flash_message(
                "success",
                f"Service logged for {selected_id}; "
                "next service due in 90 days."
            )
            st.rerun()


# g) Risk assessment

def page_risk(bundle, user):
    st.header("Risk Assessment")

    first, second = st.columns(2)

    likelihood = first.slider(
        "Likelihood (1 = rare, 5 = almost certain)",
        1,
        5,
        3
    )
    consequence = second.slider(
        "Consequence (1 = insignificant, 5 = catastrophic)",
        1,
        5,
        3
    )

    result = risk.assess(likelihood, consequence)

    st.metric(
        f"Risk score = {likelihood} x {consequence}",
        f"{result['score']}  ({result['level']})"
    )

    if result["level"] in ("High", "Critical"):
        st.error(result["warning"])
    elif result["level"] == "Medium":
        st.warning(
            "Medium risk: manage with routine controls and monitor."
        )
    else:
        st.success(
            "Low risk: acceptable with existing controls."
        )

    st.subheader("Risk matrix")
    st.dataframe(risk.risk_matrix())

    st.caption(
        "1-4 Low, 5-9 Medium, 10-16 High, 17-25 Critical"
    )

    st.subheader("Worker risk register")

    workers = bundle.workers

    risk_counts = (
        workers["risk_class"]
        .value_counts()
        .reindex([item[2] for item in config.RISK_BANDS])
        .fillna(0)
        .astype(int)
        .rename_axis("risk_class")
        .reset_index(name="workers")
    )

    show_chart(
        {
            "kind": "bar",
            "x": "risk_class",
            "y": "workers",
            "title": "Workers by risk class"
        },
        risk_counts
    )

    high_risk = workers[
        workers["risk_class"].isin(["High", "Critical"])
    ].sort_values(
        "risk_score",
        ascending=False
    )

    show_table(
        high_risk[
            [
                "worker_id",
                "department",
                "job_role",
                "shift",
                "likelihood",
                "consequence",
                "risk_score",
                "risk_class"
            ]
        ]
    )


# Data analysis

def page_analysis(bundle, user):
    st.header("Interactive Data Analysis")

    questions = analysis.available_questions(user["role"])

    if not questions:
        st.info(
            "No analysis questions are available for your role."
        )
        return

    incident_data = bundle.incidents

    first, second = st.columns(2)

    start_date = first.date_input(
        "Period start",
        incident_data["date"].min().date()
        if len(incident_data)
        else date.today(),
        key="analysis_start"
    )

    end_date = second.date_input(
        "Period end",
        incident_data["date"].max().date()
        if len(incident_data)
        else date.today(),
        key="analysis_end"
    )

    if start_date > end_date:
        st.error("Period start must not be after period end.")
        return

    groups = sorted({question.group for question in questions})

    selected_group = st.radio(
        "Topic",
        groups,
        horizontal = True
    )

    group_questions = [
        question
        for question in questions
        if question.group == selected_group
    ]

    selected_question = st.selectbox(
        "Business question",
        [
            f"{question.qid}: {question.text}"
            for question in group_questions
        ]
    )

    question = next(
        question
        for question in group_questions
        if selected_question.startswith(question.qid + ":")
    )

    answer = question.fn(
        bundle,
        analysis.Ctx(
            pd.Timestamp(start_date),
            pd.Timestamp(end_date)
        )
    )

    if "\n" not in answer.text:
        st.success(answer.text)
    else:
        st.info(answer.text)

    first, second = st.columns(2)

    with first:
        show_table(answer.table)

    with second:
        show_chart(answer.chart, answer.table)


# Reports

def page_reports(bundle, user):
    st.header("Reports")

    report_text = reports.build_text_report(
        bundle,
        user["role"],
        user["username"]
    )

    st.code(report_text, language = None)

    st.download_button(
        "Download summary report (TXT)",
        report_text,
        f"monitoring_report_{bundle.ref_date}.txt",
        "text/plain"
    )

    st.subheader("Data exports")

    downloadable = reports.downloadable_tables(
        bundle,
        user["role"]
    )

    for name, data in downloadable.items():
        st.download_button(
            f"Download {name} (CSV)",
            data.to_csv(index = False),
            f"{name}.csv",
            "text/csv",
            key = f"download_{name}"
        )


# User management

def page_users(bundle, user):
    st.header("User Management")
    show_flash()

    users = auth.load_users()

    show_table(
        users[["username", "full_name", "role", "active"]]
    )

    add_user, activate_user, reset_password = st.tabs(
        ["Add user", "Activate / deactivate", "Reset password"]
    )

    with add_user:
        with st.form("add_user", clear_on_submit = True):
            first, second = st.columns(2)

            username = first.text_input("Username")
            full_name = second.text_input("Full name")

            first, second = st.columns(2)

            role = first.selectbox("Role", config.ROLES)
            password = second.text_input(
                "Initial password",
                type = "password"
            )

            submitted = st.form_submit_button("Create user")

        if submitted:
            success, message = auth.add_user(
                username,
                full_name,
                role,
                password
            )

            if success:
                flash_message("success", message)
                st.rerun()

            st.error(message)

    with activate_user:
        selected_user = st.selectbox(
            "User",
            users["username"],
            key="active_user"
        )

        current_status = users.loc[
            users["username"] == selected_user,
            "active"
        ].iloc[0]

        if selected_user == user["username"]:
            st.info("You cannot deactivate your own account.")
        elif st.button(
            "Deactivate" if current_status == "Yes" else "Activate"
        ):
            auth.set_active(
                selected_user,
                current_status != "Yes"
            )

            new_status = (
                "inactive"
                if current_status == "Yes"
                else "active"
            )

            flash_message(
                "success",
                f"{selected_user} is now {new_status}."
            )
            st.rerun()

    with reset_password:
        selected_user = st.selectbox(
            "User",
            users["username"],
            key="password_user"
        )

        new_password = st.text_input(
            "New password",
            type = "password"
        )

        if st.button("Reset password"):
            success, message = auth.reset_password(
                selected_user,
                new_password
            )

            if success:
                st.success(message)
            else:
                st.error(message)


# Available pages

PAGES = {
    "Dashboard": ("dashboard", page_dashboard),
    "Alerts": ("dashboard", page_alerts),
    "Worker Safety": ("worker_safety", page_workers),
    "Safety Incidents": ("incidents", page_incidents),
    "Equipment": ("equipment", page_equipment),
    "Maintenance": ("maintenance", page_maintenance),
    "Risk Assessment": ("risk", page_risk),
    "Data Analysis": ("dashboard", page_analysis),
    "Reports": ("reports", page_reports),
    "Manage Users": ("manage_users", page_users)
}


def main():
    user = st.session_state.get("user")

    if not user:
        login_page()
        return

    sidebar = st.sidebar

    sidebar.markdown("### ⛏️ Khwezi Mining Monitor")
    sidebar.write(
        f"**{user['full_name']}**  \n"
        f"Role: {user['role']}"
    )

    reference_date = sidebar.date_input(
        "Reference date",
        date.today(),
        help="Date used to decide due / overdue maintenance."
    )

    allowed_pages = [
        page_name
        for page_name, (permission, _) in PAGES.items()
        if auth.has_permission(user["role"], permission)
    ]

    selected_page = sidebar.radio(
        "Navigation",
        allowed_pages
    )

    if sidebar.button("Log out"):
        st.session_state.clear()
        st.rerun()

    try:
        bundle = data_loader.build_bundle(reference_date)
    except FileNotFoundError:
        st.error(
            "Data files not found. Run: "
            "python data/generate_data.py"
        )
        return

    permission, page_function = PAGES[selected_page]

    if not auth.has_permission(user["role"], permission):
        st.error("Access denied for your role.")
        return

    page_function(bundle, user)


if __name__ == "__main__":
    main()
