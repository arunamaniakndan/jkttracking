import io
import socket
import time
from datetime import date, datetime
import pandas as pd
import streamlit as st
from supabase import Client, create_client

# ----------------- PAGE CONFIGURATION -----------------
st.set_page_config(
    page_title="JKT Production Tracking",
    page_icon="🏢",
    layout="wide",
)

# ----------------- HIDE STREAMLIT TOOLBAR & TOP-RIGHT BUTTONS -----------------
hide_streamlit_style = """
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .stActionButton {display: none !important;}
        [data-testid="stToolbar"] {visibility: hidden !important; display: none !important;}
        [data-testid="stDecoration"] {visibility: hidden !important; display: none !important;}
        [data-testid="stStatusWidget"] {visibility: hidden !important; display: none !important;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# ----------------- SUPABASE CONFIGURATION -----------------
DEFAULT_URL = "https://tbeqbqgbteexnpneypjp.supabase.co"
DEFAULT_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRiZXFicWdidGVleG5wbmV5cGpwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODc3NjE4NjMsImV4cCI6MjEwMzMzNzg2M30.S9JhQxwHuolBw3ZMPZ2u2P5ApfL7KwDEIK3VAwcpoYY"

try:
    SUPABASE_URL = st.secrets.get("SUPABASE_URL", DEFAULT_URL)
    SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", DEFAULT_KEY)
except Exception:
    SUPABASE_URL = DEFAULT_URL
    SUPABASE_KEY = DEFAULT_KEY


@st.cache_resource
def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


supabase = get_supabase_client()


# ----------------- SYSTEM INFO HELPER -----------------
def get_system_info():
    """Captures current machine hostname and network IP address automatically."""
    try:
        sys_name = socket.gethostname()
        sys_loc = socket.gethostbyname(sys_name)
    except Exception:
        sys_name = "Unknown-Host"
        sys_loc = "127.0.0.1"
    return sys_name, sys_loc


# ----------------- ID GENERATOR HELPER -----------------
def generate_auto_id(table_name: str, id_column: str, prefix: str) -> str:
    try:
        res = supabase.table(table_name).select(id_column).execute()
        count = len(res.data) + 1 if res.data else 1
        return f"{prefix}{count:04d}"
    except Exception:
        return f"{prefix}{int(time.time()) % 10000:04d}"


# ----------------- SESSION STATE INITIALIZATION -----------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_info" not in st.session_state:
    st.session_state.user_info = {
        "emp_id": "",
        "emp_name": "Guest",
        "emp_role": "USER",
    }


# ----------------- AUTHENTICATION LOGIC -----------------
def login(emp_id_val, password):
    try:
        res = (
            supabase.table("master_employe")
            .select("*")
            .ilike("emp_id", emp_id_val.strip())
            .eq("emp_pwd", password.strip())
            .execute()
        )

        if res.data:
            user = res.data[0]
            if user.get("emp_status") != "Active":
                st.error("Your account is not active. Please contact the administrator.")
                return False

            if user.get("expiry_date"):
                exp_date = datetime.strptime(user["expiry_date"], "%Y-%m-%d").date()
                if exp_date < date.today():
                    st.error("Your account has expired. Please contact the administrator.")
                    return False

            st.session_state.authenticated = True
            st.session_state.user_info = {
                "emp_id": user["emp_id"],
                "emp_name": user["emp_name"],
                "emp_role": user.get("emp_role", "USER").upper(),
            }
            return True
        else:
            st.error("Invalid Employee ID or Password.")
            return False
    except Exception as e:
        st.error(f"Authentication error: {e}")
        return False


def logout():
    st.session_state.authenticated = False
    st.session_state.user_info = {
        "emp_id": "",
        "emp_name": "Guest",
        "emp_role": "USER",
    }
    st.rerun()


# ----------------- LOGIN WINDOW -----------------
if not st.session_state.authenticated:
    _, col_login, _ = st.columns([1, 1.5, 1])
    with col_login:
        st.markdown(
            "<h2 style='text-align: center;'>🔐 Operations Portal Login</h2>",
            unsafe_allow_html=True,
        )
        with st.form("login_form", clear_on_submit=False):
            emp_id_input = st.text_input("Employee ID")
            emp_pwd_input = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)

            if submitted:
                if emp_id_input and emp_pwd_input:
                    if login(emp_id_input, emp_pwd_input):
                        st.success("Login successful!")
                        st.rerun()
                else:
                    st.warning("Please fill in both fields.")
    st.stop()

# ----------------- AUTHENTICATED WORKSPACE -----------------
current_user = st.session_state.get("user_info", {})
emp_name = current_user.get("emp_name", "User")
emp_id = current_user.get("emp_id", "")
role = current_user.get("emp_role", "USER")

current_sys_name, current_sys_loc = get_system_info()

# Sidebar Info
st.sidebar.markdown(f"### 👤 Welcome, **{emp_name}**")
st.sidebar.caption(f"**Emp ID:** `{emp_id}` | **Role:** `{role}`")
st.sidebar.caption(f"💻 **Host:** `{current_sys_name}` (`{current_sys_loc}`)")
if st.sidebar.button("Logout", use_container_width=True):
    logout()
st.sidebar.markdown("---")

# Navigation Menu
if role == "ADMIN":
    menu_options = [
        "1. Master Employee",
        "2. Master Customer",
        "3. Master Project",
        "4. Master Process",
        "5. Master Job",
        "6. Job Entry",
        "7. Reports",
    ]
else:
    menu_options = ["6. Job Entry", "7. Reports"]

selected_page = st.sidebar.radio("Navigation", menu_options)

# ----------------- 1. MASTER EMPLOYEE -----------------
if selected_page == "1. Master Employee" and role == "ADMIN":
    st.title("👨‍💼 Master Employee")

    emp_res = supabase.table("master_employe").select("*").order("created_at", desc=True).execute()
    emp_list = emp_res.data if emp_res.data else []

    emp_name_dropdown_options = ["➕ Create New Employee"] + [
        f"{e['emp_name']} ({e['emp_id']})" for e in emp_list if e.get("emp_name")
    ]
    selected_emp_name_opt = st.selectbox("Employee Name (Select existing or create new):", emp_name_dropdown_options)

    is_edit_mode = selected_emp_name_opt != "➕ Create New Employee"
    selected_emp = None

    if is_edit_mode:
        selected_emp_id = selected_emp_name_opt.split("(")[-1].rstrip(")")
        selected_emp = next((e for e in emp_list if e["emp_id"] == selected_emp_id), None)
        active_emp_id = selected_emp["emp_id"]
        st.warning(f"✏️ **Edit Mode:** Modifying Employee **{selected_emp['emp_name']}** (`{active_emp_id}`)")
    else:
        active_emp_id = generate_auto_id("master_employe", "emp_id", "JKT")
        st.info(f"✨ **Create Mode:** System Generated Employee ID: **{active_emp_id}**")

    with st.form("emp_form"):
        c1, c2 = st.columns(2)
        f_emp_id = c1.text_input("Employee ID", value=active_emp_id, disabled=False)
        if is_edit_mode:
            f_emp_name = c2.text_input("Employee Name *", value=selected_emp.get("emp_name", ""))
        else:
            f_emp_name = c2.text_input("Enter New Employee Name *", value="")

        c3, c4, c5 = st.columns(3)
        default_pwd = selected_emp.get("emp_pwd", "") if selected_emp else ""
        f_emp_pwd = c3.text_input("Password *", value=default_pwd, type="password")

        role_options = ["USER", "ADMIN"]
        curr_role_idx = role_options.index(selected_emp.get("emp_role", "USER")) if selected_emp and selected_emp.get("emp_role") in role_options else 0
        f_emp_role = c4.selectbox("Role", role_options, index=curr_role_idx)

        exp_val = (
            datetime.strptime(selected_emp["expiry_date"], "%Y-%m-%d").date()
            if selected_emp and selected_emp.get("expiry_date")
            else date(2030, 12, 31)
        )
        f_expiry_date = c5.date_input("Expiry Date", value=exp_val)

        c6, c7 = st.columns(2)
        status_options = ["Active", "Inactive", "Suspended"]
        curr_status_idx = status_options.index(selected_emp.get("emp_status", "Active")) if selected_emp and selected_emp.get("emp_status") in status_options else 0
        f_emp_status = c6.selectbox("Status", status_options, index=curr_status_idx)
        remarks = c7.text_area("Remarks", value=selected_emp.get("remarks", "") if selected_emp else "")

        btn_label = "💾 Update Employee" if is_edit_mode else "➕ Add Employee"
        if st.form_submit_button(btn_label, type="primary", use_container_width=True):
            if f_emp_name.strip() and f_emp_pwd.strip():
                emp_payload = {
                    "emp_id": f_emp_id.strip(),
                    "emp_name": f_emp_name.strip(),
                    "emp_pwd": f_emp_pwd.strip(),
                    "emp_role": f_emp_role,
                    "expiry_date": str(f_expiry_date),
                    "emp_status": f_emp_status,
                    "remarks": remarks.strip(),
                }
                if is_edit_mode:
                    supabase.table("master_employe").update(emp_payload).eq("emp_id", active_emp_id).execute()
                    st.success(f"Employee '{f_emp_name}' updated successfully.")
                else:
                    supabase.table("master_employe").insert(emp_payload).execute()
                    st.success(f"Employee '{f_emp_name}' registered successfully with ID {f_emp_id.strip()}.")
                st.rerun()
            else:
                st.error("Employee Name and Password are required.")

    st.subheader("Employee Registry")
    data = supabase.table("master_employe").select("emp_id, emp_name, emp_role, expiry_date, emp_status, remarks").order("created_at", desc=True).execute()
    if data.data:
        st.dataframe(pd.DataFrame(data.data), use_container_width=True)

# ----------------- 2. MASTER CUSTOMER -----------------
elif selected_page == "2. Master Customer" and role == "ADMIN":
    st.title("🏢 Master Customer")

    cust_res = supabase.table("master_customer").select("*").order("created_at", desc=True).execute()
    cust_list = cust_res.data if cust_res.data else []

    cust_name_dropdown_options = ["➕ Create New Customer"] + [
        f"{c['cust_name']} ({c['cust_id']})" for c in cust_list if c.get("cust_name")
    ]
    selected_cust_name_opt = st.selectbox("Customer Name (Select existing or create new):", cust_name_dropdown_options)

    is_edit_mode = selected_cust_name_opt != "➕ Create New Customer"
    selected_cust_record = None

    if is_edit_mode:
        selected_cust_id = selected_cust_name_opt.split("(")[-1].rstrip(")")
        selected_cust_record = next((c for c in cust_list if c["cust_id"] == selected_cust_id), None)
        active_cust_id = selected_cust_record["cust_id"]
        st.warning(f"✏️ **Edit Mode:** Modifying Customer **{selected_cust_record['cust_name']}** (`{active_cust_id}`)")
    else:
        active_cust_id = generate_auto_id("master_customer", "cust_id", "JKTCU")
        st.info(f"✨ **Create Mode:** System Generated Customer ID: **{active_cust_id}**")

    with st.form("cust_form"):
        c1, c2, c3 = st.columns(3)
        cust_id_val = c1.text_input("Customer ID", value=active_cust_id)
        if is_edit_mode:
            cust_name_input = c2.text_input("Customer Name *", value=selected_cust_record.get("cust_name", ""))
        else:
            cust_name_input = c2.text_input("Enter New Customer Name *", value="")

        curr_year = int(selected_cust_record.get("cust_year", date.today().year)) if selected_cust_record else date.today().year
        cust_year = c3.number_input("Customer Year", min_value=2000, max_value=2099, value=curr_year, step=1)

        c4, c5 = st.columns(2)
        cust_status_opts = ["Active", "Inactive"]
        curr_cust_status_idx = cust_status_opts.index(selected_cust_record.get("cust_status", "Active")) if selected_cust_record and selected_cust_record.get("cust_status") in cust_status_opts else 0
        cust_status = c4.selectbox("Status", cust_status_opts, index=curr_cust_status_idx)
        remarks = c5.text_area("Remarks", value=selected_cust_record.get("remarks", "") if selected_cust_record else "")

        btn_label = "💾 Update Customer" if is_edit_mode else "➕ Add Customer"
        if st.form_submit_button(btn_label, type="primary", use_container_width=True):
            if cust_name_input.strip():
                cust_payload = {
                    "cust_id": cust_id_val.strip(),
                    "cust_name": cust_name_input.strip(),
                    "cust_year": int(cust_year),
                    "cust_status": cust_status,
                    "remarks": remarks.strip(),
                }
                if is_edit_mode:
                    supabase.table("master_customer").update(cust_payload).eq("cust_id", active_cust_id).execute()
                    st.success(f"Customer '{cust_name_input}' updated successfully.")
                else:
                    supabase.table("master_customer").insert(cust_payload).execute()
                    st.success(f"Customer '{cust_name_input}' registered successfully with ID {cust_id_val.strip()}.")
                st.rerun()
            else:
                st.error("Customer Name is required.")

    st.subheader("Customer Registry")
    data = supabase.table("master_customer").select("*").order("created_at", desc=True).execute()
    if data.data:
        st.dataframe(pd.DataFrame(data.data), use_container_width=True)

# ----------------- 3. MASTER PROJECT -----------------
elif selected_page == "3. Master Project" and role == "ADMIN":
    st.title("📁 Master Project")

    pro_res = supabase.table("master_project").select("*").order("created_at", desc=True).execute()
    pro_list = pro_res.data if pro_res.data else []

    pro_name_dropdown_options = ["➕ Create New Project"] + [
        f"{p['pro_name']} ({p['pro_id']})" for p in pro_list if p.get("pro_name")
    ]
    selected_pro_name_opt = st.selectbox("Project Name (Select existing or create new):", pro_name_dropdown_options)

    is_edit_mode = selected_pro_name_opt != "➕ Create New Project"
    selected_pro = None

    if is_edit_mode:
        selected_pro_id = selected_pro_name_opt.split("(")[-1].rstrip(")")
        selected_pro = next((p for p in pro_list if p["pro_id"] == selected_pro_id), None)
        active_pro_id = selected_pro["pro_id"]
        st.warning(f"✏️ **Edit Mode:** Modifying Project **{selected_pro['pro_name']}** (`{active_pro_id}`)")
    else:
        active_pro_id = generate_auto_id("master_project", "pro_id", "PRO")
        st.info(f"✨ **Create Mode:** System Generated Project ID: **{active_pro_id}**")

    with st.form("pro_form"):
        c1, c2 = st.columns(2)
        c1.text_input("Project ID", value=active_pro_id, disabled=True)
        if is_edit_mode:
            pro_name = c2.text_input("Project Name *", value=selected_pro.get("pro_name", ""))
        else:
            pro_name = c2.text_input("Enter New Project Name *", value="")

        remarks = st.text_area("Remarks", value=selected_pro.get("remarks", "") if selected_pro else "")

        btn_label = "💾 Update Project" if is_edit_mode else "➕ Add Project"
        if st.form_submit_button(btn_label, type="primary", use_container_width=True):
            if pro_name.strip():
                pro_payload = {
                    "pro_name": pro_name.strip(),
                    "remarks": remarks.strip(),
                }
                if is_edit_mode:
                    supabase.table("master_project").update(pro_payload).eq("pro_id", active_pro_id).execute()
                    st.success(f"Project '{pro_name}' updated successfully.")
                else:
                    pro_payload["pro_id"] = active_pro_id
                    supabase.table("master_project").insert(pro_payload).execute()
                    st.success(f"Project '{pro_name}' created successfully with ID {active_pro_id}.")
                st.rerun()
            else:
                st.error("Project Name is required.")

    st.subheader("Project Registry")
    data = supabase.table("master_project").select("*").order("created_at", desc=True).execute()
    if data.data:
        st.dataframe(pd.DataFrame(data.data), use_container_width=True)

# ----------------- 4. MASTER PROCESS -----------------
elif selected_page == "4. Master Process" and role == "ADMIN":
    st.title("⚙️ Master Process")

    proc_res = supabase.table("master_process").select("*").order("created_at", desc=True).execute()
    proc_list = proc_res.data if proc_res.data else []

    proc_name_dropdown_options = ["➕ Create New Process"] + [
        f"{p['process_name']} ({p['process_id']})" for p in proc_list if p.get("process_name")
    ]
    selected_proc_name_opt = st.selectbox("Process Name (Select existing or create new):", proc_name_dropdown_options)

    is_edit_mode = selected_proc_name_opt != "➕ Create New Process"
    selected_proc = None

    if is_edit_mode:
        selected_proc_id = selected_proc_name_opt.split("(")[-1].rstrip(")")
        selected_proc = next((p for p in proc_list if p["process_id"] == selected_proc_id), None)
        active_proc_id = selected_proc["process_id"]
        st.warning(f"✏️ **Edit Mode:** Modifying Process **{selected_proc['process_name']}** (`{active_proc_id}`)")
    else:
        active_proc_id = generate_auto_id("master_process", "process_id", "PRC")
        st.info(f"✨ **Create Mode:** System Generated Process ID: **{active_proc_id}**")

    with st.form("process_form"):
        c1, c2, c3 = st.columns(3)
        c1.text_input("Process ID", value=active_proc_id, disabled=True)
        if is_edit_mode:
            process_name = c2.text_input("Process Name *", value=selected_proc.get("process_name", ""))
        else:
            process_name = c2.text_input("Enter New Process Name *", value="")

        proc_status_opts = ["Active", "Inactive"]
        curr_proc_status_idx = proc_status_opts.index(selected_proc.get("process_status", "Active")) if selected_proc and selected_proc.get("process_status") in proc_status_opts else 0
        process_status = c3.selectbox("Status", proc_status_opts, index=curr_proc_status_idx)
        remarks = st.text_area("Remarks", value=selected_proc.get("remarks", "") if selected_proc else "")

        btn_label = "💾 Update Process" if is_edit_mode else "➕ Add Process"
        if st.form_submit_button(btn_label, type="primary", use_container_width=True):
            if process_name.strip():
                proc_payload = {
                    "process_name": process_name.strip(),
                    "process_status": process_status,
                    "remarks": remarks.strip(),
                }
                if is_edit_mode:
                    supabase.table("master_process").update(proc_payload).eq("process_id", active_proc_id).execute()
                    st.success(f"Process '{process_name}' updated successfully.")
                else:
                    proc_payload["process_id"] = active_proc_id
                    supabase.table("master_process").insert(proc_payload).execute()
                    st.success(f"Process '{process_name}' registered successfully with ID {active_proc_id}.")
                st.rerun()
            else:
                st.error("Process Name is required.")

    st.subheader("Process Registry")
    data = supabase.table("master_process").select("*").order("created_at", desc=True).execute()
    if data.data:
        st.dataframe(pd.DataFrame(data.data), use_container_width=True)

# ----------------- 5. MASTER JOB -----------------
elif selected_page == "5. Master Job" and role == "ADMIN":
    st.title("📋 Master Job Management")

    cust_res = supabase.table("master_customer").select("cust_name").eq("cust_status", "Active").execute()
    pro_res = supabase.table("master_project").select("pro_name").execute()
    all_jobs_res = supabase.table("master_job").select("*").order("created_at", desc=True).execute()

    cust_options = [c["cust_name"] for c in cust_res.data] if cust_res.data else []
    pro_options = [p["pro_name"] for p in pro_res.data] if pro_res.data else []
    jobs_list = all_jobs_res.data if all_jobs_res.data else []

    job_name_dropdown_options = ["➕ Create New Job"] + [
        f"{j['job_name']} ({j['job_id']})" for j in jobs_list if j.get("job_name")
    ]
    selected_job_name_opt = st.selectbox("Job Name (Select existing or create new):", job_name_dropdown_options)

    is_edit_mode = selected_job_name_opt != "➕ Create New Job"
    selected_job = None

    if is_edit_mode:
        selected_job_id = selected_job_name_opt.split("(")[-1].rstrip(")")
        selected_job = next((j for j in jobs_list if j["job_id"] == selected_job_id), None)
        active_job_id = selected_job["job_id"]
        st.warning(f"✏️ **Edit Mode:** Modifying Job **{selected_job['job_name']}** (`{active_job_id}`)")
    else:
        active_job_id = generate_auto_id("master_job", "job_id", f"JOB-{datetime.now().strftime('%Y%m')}-")
        st.info(f"✨ **Create Mode:** System Generated Job ID: **{active_job_id}**")

    with st.form("master_job_form"):
        c1, c2, c3, c4 = st.columns(4)
        c1.text_input("Job ID", value=active_job_id, disabled=True)

        c_idx = cust_options.index(selected_job["cust_name"]) if selected_job and selected_job.get("cust_name") in cust_options else 0
        cust_name = c2.selectbox("Customer Name", cust_options if cust_options else ["None"], index=c_idx)

        p_idx = pro_options.index(selected_job["pro_name"]) if selected_job and selected_job.get("pro_name") in pro_options else 0
        pro_name = c3.selectbox("Project Name", pro_options if pro_options else ["None"], index=p_idx)

        if is_edit_mode:
            job_name = c4.text_input("Job Name *", value=selected_job.get("job_name", ""))
        else:
            job_name = c4.text_input("Enter New Job Name *", value="")

        c5, c6, c7 = st.columns(3)
        rec_default = (
            datetime.strptime(selected_job["rec_date"], "%Y-%m-%d").date()
            if selected_job and selected_job.get("rec_date")
            else date.today()
        )
        rec_date = c5.date_input("Received Date", value=rec_default)

        due_default = (
            datetime.strptime(selected_job["due_date"], "%Y-%m-%d").date()
            if selected_job and selected_job.get("due_date")
            else date.today()
        )
        due_date = c6.date_input("Due Date", value=due_default)

        pages = c7.number_input("Pages", min_value=0, value=int(selected_job.get("pages", 0)) if selected_job else 0, step=1)

        c8, c9, c10 = st.columns(3)
        curr_spend_hrs = float(selected_job.get("spend_hrs", 0.0)) if selected_job else 0.0
        c8.text_input("Spend Hours (Auto-calculated)", value=f"{curr_spend_hrs:.2f} hrs", disabled=True)

        job_cost = c9.number_input(
            "Job Cost ($/₹)",
            min_value=0.0,
            value=float(selected_job.get("job_cost", 0.0)) if selected_job else 0.0,
            step=1.0,
            format="%.2f",
        )

        job_statuses = ["Pending", "In Progress", "Completed", "On Hold", "Cancelled"]
        s_idx = job_statuses.index(selected_job.get("job_status", "Pending")) if selected_job and selected_job.get("job_status") in job_statuses else 0
        job_status = c10.selectbox("Job Status", job_statuses, index=s_idx)

        remarks = st.text_area("Remarks", value=selected_job.get("remarks", "") if selected_job else "")

        btn_label = "💾 Update Job Details" if is_edit_mode else "➕ Save New Job"
        if st.form_submit_button(btn_label, type="primary", use_container_width=True):
            if job_name.strip() and cust_options and pro_options:
                job_payload = {
                    "cust_name": cust_name,
                    "pro_name": pro_name,
                    "job_name": job_name.strip(),
                    "rec_date": str(rec_date),
                    "due_date": str(due_date),
                    "pages": int(pages),
                    "job_cost": float(job_cost),
                    "job_status": job_status,
                    "remarks": remarks.strip(),
                }
                if is_edit_mode:
                    supabase.table("master_job").update(job_payload).eq("job_id", active_job_id).execute()
                    st.success(f"Job '{job_name}' updated successfully.")
                else:
                    job_payload["job_id"] = active_job_id
                    job_payload["spend_hrs"] = 0.00
                    supabase.table("master_job").insert(job_payload).execute()
                    st.success(f"Job '{job_name}' registered successfully with ID {active_job_id}.")
                st.rerun()
            else:
                st.error("Job Name, Customer, and Project are required.")

    st.subheader("All Master Jobs Registry")
    data = supabase.table("master_job").select("*").order("created_at", desc=True).execute()
    if data.data:
        st.dataframe(pd.DataFrame(data.data), use_container_width=True)

# ----------------- 6. JOB ENTRY -----------------
elif selected_page == "6. Job Entry":
    st.title("⏱️ Production Job Entry")

    tab_start, tab_end, tab_logs = st.tabs(
        ["▶️ Start / Edit Task", "⏹️ End Active Process", "📊 Production Logs"]
    )

    # TAB 1: START OR EDIT TASK
    with tab_start:
        cust_res = supabase.table("master_customer").select("cust_name").eq("cust_status", "Active").execute()
        pro_res = supabase.table("master_project").select("pro_name").execute()
        job_res = supabase.table("master_job").select("job_name").execute()
        proc_res = supabase.table("master_process").select("process_name").eq("process_status", "Active").execute()

        cust_options = [c["cust_name"] for c in cust_res.data] if cust_res.data else []
        for default_non_prod in ["TRAINING", "DOWNTIME"]:
            if default_non_prod not in cust_options:
                cust_options.append(default_non_prod)

        pro_options = [p["pro_name"] for p in pro_res.data] if pro_res.data else []
        job_options = [j["job_name"] for j in job_res.data] if job_res.data else []
        proc_options = (
            [pr["process_name"] for pr in proc_res.data]
            if proc_res.data
            else ["Pagination", "XML Conversion", "QC Review", "Training", "System Maintenance"]
        )

        entry_query = supabase.table("job_entry").select("*").order("id", desc=True)
        if role != "ADMIN":
            entry_query = entry_query.eq("emp_id", emp_id)
        all_entries_res = entry_query.limit(50).execute()
        entry_list = all_entries_res.data if all_entries_res.data else []

        entry_combo_options = ["➕ Start New Task"] + [
            f"ID {e['id']} | Job: {e['job_name']} | Chap: {e.get('chap_name', '')} | Proc: {e.get('process', '')} ({e.get('job_status', 'In Progress')})"
            for e in entry_list
        ]
        selected_entry_option = st.selectbox("Task Selector (Select existing to edit or create new):", entry_combo_options)

        is_entry_edit_mode = selected_entry_option != "➕ Start New Task"
        selected_entry = None

        if is_entry_edit_mode:
            selected_entry_id = int(selected_entry_option.split(" | ")[0].replace("ID ", ""))
            selected_entry = next((e for e in entry_list if e["id"] == selected_entry_id), None)
            st.warning(f"✏️ **Edit Mode:** Modifying Task Entry **#{selected_entry_id}**")
        else:
            st.info("✨ **Start Mode:** Launching a new task with background machine & user tracking.")

        default_cust_idx = (
            cust_options.index(selected_entry["cust_name"])
            if selected_entry and selected_entry.get("cust_name") in cust_options
            else 0
        )
        selected_cust = st.selectbox("Customer Selection *", cust_options if cust_options else ["None"], index=default_cust_idx)
        is_non_prod = str(selected_cust).upper() in ["TRAINING", "DOWNTIME"]

        if is_non_prod:
            st.info(f"💡 **{selected_cust} Mode Active:** Project, Job Name, and Chapter fields are optional and set to N/A automatically.")

        existing_chaps = sorted(list({e["chap_name"] for e in entry_list if e.get("chap_name") and e.get("chap_name") != "N/A"}))
        chap_dropdown_options = ["➕ Enter New Chapter / Unit"] + existing_chaps

        with st.form("job_entry_form"):
            c1, c2, c3 = st.columns(3)
            c1.text_input("Selected Customer", value=selected_cust, disabled=True)

            if is_non_prod:
                pro_name = c2.text_input("Project", value="N/A", disabled=True)
                job_name = c3.text_input("Job Name", value="N/A", disabled=True)
            else:
                p_idx = pro_options.index(selected_entry["pro_name"]) if selected_entry and selected_entry.get("pro_name") in pro_options else 0
                pro_name = c2.selectbox("Project", pro_options if pro_options else ["None"], index=p_idx)

                j_idx = job_options.index(selected_entry["job_name"]) if selected_entry and selected_entry.get("job_name") in job_options else 0
                job_name = c3.selectbox("Job Name", job_options if job_options else ["None"], index=j_idx)

            c4, c5 = st.columns(2)
            if is_non_prod:
                chap_name = c4.text_input("Chapter / Unit Name", value="N/A", disabled=True)
            else:
                curr_chap_val = selected_entry.get("chap_name", "") if selected_entry else ""
                chap_select_idx = (
                    chap_dropdown_options.index(curr_chap_val)
                    if curr_chap_val in chap_dropdown_options
                    else 0
                )
                selected_chap_opt = c4.selectbox("Chapter / Unit Selection", chap_dropdown_options, index=chap_select_idx)
                
                if selected_chap_opt == "➕ Enter New Chapter / Unit":
                    chap_name = c4.text_input("Enter Chapter / Unit Name *", value=curr_chap_val)
                else:
                    chap_name = selected_chap_opt

            pr_idx = proc_options.index(selected_entry["process"]) if selected_entry and selected_entry.get("process") in proc_options else 0
            process = c5.selectbox("Process", proc_options, index=pr_idx)

            if is_entry_edit_mode:
                c6, c7 = st.columns(2)
                entry_statuses = ["In Progress", "Completed", "On Hold", "Cancelled"]
                s_idx = entry_statuses.index(selected_entry.get("job_status", "In Progress")) if selected_entry.get("job_status") in entry_statuses else 0
                e_status = c6.selectbox("Status", entry_statuses, index=s_idx)
                time_taken = c7.text_input("Time Taken", value=selected_entry.get("time_taken", "Running..."))

            remarks = st.text_area("Remarks", value=selected_entry.get("remarks", "") if selected_entry else "")

            btn_label = "💾 Update Job Entry" if is_entry_edit_mode else "▶️ Start Job Now"
            if st.form_submit_button(btn_label, type="primary", use_container_width=True):
                valid_submission = False
                if is_non_prod:
                    chap_name = "N/A"
                    pro_name = "N/A"
                    job_name = "N/A"
                    valid_submission = True
                else:
                    if chap_name.strip() and job_options and cust_options and pro_options and job_name != "None":
                        valid_submission = True

                if valid_submission:
                    sys_name, sys_loc = get_system_info()

                    if is_entry_edit_mode:
                        supabase.table("job_entry").update({
                            "cust_name": selected_cust,
                            "pro_name": pro_name,
                            "job_name": job_name,
                            "chap_name": chap_name.strip(),
                            "process": process,
                            "job_status": e_status,
                            "time_taken": time_taken,
                            "remarks": remarks.strip(),
                        }).eq("id", selected_entry_id).execute()
                        st.success(f"Job Entry #{selected_entry_id} updated successfully.")
                        st.rerun()
                    else:
                        active_check = (
                            supabase.table("job_entry")
                            .select("id, job_name, chap_name, process")
                            .eq("emp_id", emp_id)
                            .eq("job_status", "In Progress")
                            .execute()
                        )

                        if active_check.data:
                            running_task = active_check.data[0]
                            st.error(
                                f"⚠️ You already have an active process running: "
                                f"**{running_task['job_name']}** ({running_task['chap_name']} - {running_task['process']}). "
                                f"Please end the active task before starting a new one."
                            )
                        else:
                            start_iso = datetime.now().isoformat()
                            supabase.table("job_entry").insert({
                                "emp_id": emp_id,
                                "emp_name": emp_name,
                                "cust_name": selected_cust,
                                "pro_name": pro_name,
                                "job_name": job_name,
                                "chap_name": chap_name.strip(),
                                "process": process,
                                "start_time": start_iso,
                                "end_time": None,
                                "time_taken": "Running...",
                                "job_status": "In Progress",
                                "system_start_name": sys_name,
                                "system_start_location": sys_loc,
                                "system_end_name": None,
                                "system_end_location": None,
                                "remarks": f"Started by {emp_name}. {remarks}".strip(),
                            }).execute()

                            if not is_non_prod:
                                supabase.table("master_job").update({"job_status": "In Progress"}).eq("job_name", job_name).execute()

                            st.success(
                                f"Started '{process}' for '{selected_cust}' by {emp_name} [{emp_id}] on [{sys_name} / {sys_loc}] at {datetime.now().strftime('%H:%M:%S')}"
                            )
                            st.rerun()
                else:
                    st.error("Please enter Chapter Name and ensure Customer, Project, and Job are selected.")

    # TAB 2: END TASK
    with tab_end:
        st.subheader("Open Tasks Currently Running" if role == "ADMIN" else f"Your Active Running Task ({emp_name})")

        open_tasks_query = (
            supabase.table("job_entry")
            .select("*")
            .eq("job_status", "In Progress")
            .order("id", desc=True)
        )

        if role != "ADMIN":
            open_tasks_query = open_tasks_query.eq("emp_id", emp_id)

        open_tasks = open_tasks_query.execute()

        if open_tasks.data:
            df_open = pd.DataFrame(open_tasks.data)
            display_cols = [
                c
                for c in [
                    "id",
                    "emp_id",
                    "emp_name",
                    "cust_name",
                    "job_name",
                    "chap_name",
                    "process",
                    "system_start_name",
                    "system_start_location",
                    "start_time",
                    "job_status",
                ]
                if c in df_open.columns
            ]
            st.dataframe(df_open[display_cols], use_container_width=True)

            task_dict = {
                f"ID {t['id']} | Cust: {t.get('cust_name', 'N/A')} | Job: {t['job_name']} | Chap: {t['chap_name']} | Proc: {t.get('process', '')} | Start Host: {t.get('system_start_name', 'N/A')}": t
                for t in open_tasks.data
            }

            with st.form("end_task_form"):
                selected_label = st.selectbox("Select Active Task to Complete:", list(task_dict.keys()))
                end_remarks = st.text_area("Completion Remarks (Optional)")

                if st.form_submit_button(
                    "⏹️ Complete & Update Task Time",
                    type="primary",
                    use_container_width=True,
                ):
                    task = task_dict[selected_label]
                    task_id = task["id"]
                    t_job_name = task["job_name"]
                    t_cust_name = str(task.get("cust_name", "")).upper()

                    start_dt = datetime.fromisoformat(task["start_time"].replace("Z", "+00:00")).replace(tzinfo=None)
                    end_dt = datetime.now()

                    diff = end_dt - start_dt
                    elapsed_seconds = max(0, diff.total_seconds())
                    added_hours = elapsed_seconds / 3600.0

                    hrs, rem = divmod(elapsed_seconds, 3600)
                    mins, _ = divmod(rem, 60)
                    time_taken_str = f"{int(hrs)}h {int(mins)}m"

                    end_sys_name, end_sys_loc = get_system_info()

                    # 1. Update job_entry record
                    supabase.table("job_entry").update(
                        {
                            "end_time": end_dt.isoformat(),
                            "time_taken": time_taken_str,
                            "job_status": "Completed",
                            "system_end_name": end_sys_name,
                            "system_end_location": end_sys_loc,
                            "remarks": f"{task.get('remarks', '')} | Finished by {emp_name}: {end_remarks}".strip(" | "),
                        }
                    ).eq("id", task_id).execute()

                    # 2. Update spend_hrs in master_job only if standard production job
                    if t_cust_name not in ["TRAINING", "DOWNTIME"] and t_job_name != "N/A":
                        job_query = supabase.table("master_job").select("spend_hrs").eq("job_name", t_job_name).execute()
                        current_spend_hrs = 0.0
                        if job_query.data and job_query.data[0].get("spend_hrs") is not None:
                            current_spend_hrs = float(job_query.data[0]["spend_hrs"])

                        new_total_hrs = round(current_spend_hrs + added_hours, 2)
                        supabase.table("master_job").update({"spend_hrs": new_total_hrs}).eq("job_name", t_job_name).execute()
                        st.success(
                            f"Task finished by {emp_name} on [{end_sys_name} / {end_sys_loc}]. Duration: {time_taken_str}. "
                            f"Added {added_hours:.2f} hrs to Job '{t_job_name}' (Total Spend Hours: {new_total_hrs} hrs)."
                        )
                    else:
                        st.success(
                            f"Task ({t_cust_name}) finished by {emp_name} on [{end_sys_name} / {end_sys_loc}]. Duration: {time_taken_str}."
                        )
                    st.rerun()
        else:
            st.info("No active tasks are currently running." if role == "ADMIN" else "You have no active tasks running.")

    # TAB 3: LOGS
    with tab_logs:
        st.subheader("All Production Logs" if role == "ADMIN" else f"Production Logs ({emp_name})")

        logs_query = supabase.table("job_entry").select("*").order("id", desc=True)

        if role != "ADMIN":
            logs_query = logs_query.eq("emp_id", emp_id)

        all_logs = logs_query.execute()

        if all_logs.data:
            st.dataframe(pd.DataFrame(all_logs.data), use_container_width=True)
        else:
            st.info("No production logs found." if role == "ADMIN" else "No production logs found for your account.")

# ----------------- 7. REPORTS (CUSTOMER, PROJECT, JOB, PROCESS, EMPLOYEE, DATE RANGE) -----------------
elif selected_page == "7. Reports":
    st.title("📊 Production Reports & Analytics")
    st.caption("Filter and export production activity across Customer, Project, Job, Process, Employee, and Date Range.")

    # Fetch lookup data for dropdown filters
    cust_res = supabase.table("master_customer").select("cust_name").execute()
    pro_res = supabase.table("master_project").select("pro_name").execute()
    job_res = supabase.table("master_job").select("job_name").execute()
    proc_res = supabase.table("master_process").select("process_name").execute()
    emp_res = supabase.table("master_employe").select("emp_id, emp_name").execute()

    filter_customers = sorted(list({c["cust_name"] for c in cust_res.data if c.get("cust_name")})) if cust_res.data else []
    for non_prod in ["TRAINING", "DOWNTIME"]:
        if non_prod not in filter_customers:
            filter_customers.append(non_prod)

    filter_projects = sorted(list({p["pro_name"] for p in pro_res.data if p.get("pro_name")})) if pro_res.data else []
    filter_jobs = sorted(list({j["job_name"] for j in job_res.data if j.get("job_name")})) if job_res.data else []
    filter_processes = sorted(list({p["process_name"] for p in proc_res.data if p.get("process_name")})) if proc_res.data else []

    if role == "ADMIN":
        filter_employees = [f"{e['emp_name']} ({e['emp_id']})" for e in emp_res.data if e.get("emp_name")] if emp_res.data else []
    else:
        filter_employees = [f"{emp_name} ({emp_id})"]

    # Filter Controls Container
    with st.expander("🔍 Filter Controls", expanded=True):
        f1, f2, f3 = st.columns(3)
        sel_cust = f1.multiselect("Customer", options=filter_customers, default=[])
        sel_pro = f2.multiselect("Project", options=filter_projects, default=[])
        sel_job = f3.multiselect("Job Name", options=filter_jobs, default=[])

        f4, f5, f6 = st.columns(3)
        sel_proc = f4.multiselect("Process", options=filter_processes, default=[])

        if role == "ADMIN":
            sel_emp = f5.multiselect("Employee", options=filter_employees, default=[])
        else:
            sel_emp = f5.multiselect("Employee", options=filter_employees, default=filter_employees, disabled=True)

        today = date.today()
        first_day_month = today.replace(day=1)
        sel_date_range = f6.date_input(
            "Date Range (Start - End)",
            value=(first_day_month, today),
            max_value=today,
        )

    # Validate and parse date range
    if isinstance(sel_date_range, (tuple, list)) and len(sel_date_range) == 2:
        start_date, end_date = sel_date_range
    elif isinstance(sel_date_range, (tuple, list)) and len(sel_date_range) == 1:
        start_date = end_date = sel_date_range[0]
    else:
        start_date = end_date = today

    start_iso = datetime.combine(start_date, datetime.min.time()).isoformat()
    end_iso = datetime.combine(end_date, datetime.max.time()).isoformat()

    # Query Supabase with date bounds
    report_query = (
        supabase.table("job_entry")
        .select("*")
        .gte("start_time", start_iso)
        .lte("start_time", end_iso)
        .order("start_time", desc=True)
    )

    if role != "ADMIN":
        report_query = report_query.eq("emp_id", emp_id)

    raw_data = report_query.execute()
    records = raw_data.data if raw_data.data else []

    if records:
        df = pd.DataFrame(records)

        # Apply multi-select filters in Pandas
        if sel_cust:
            df = df[df["cust_name"].isin(sel_cust)]
        if sel_pro:
            df = df[df["pro_name"].isin(sel_pro)]
        if sel_job:
            df = df[df["job_name"].isin(sel_job)]
        if sel_proc:
            df = df[df["process"].isin(sel_proc)]
        if sel_emp and role == "ADMIN":
            emp_ids = [e.split("(")[-1].rstrip(")") for e in sel_emp]
            df = df[df["emp_id"].isin(emp_ids)]

        # Calculate exact numeric hours for analytics
        def compute_hours(row):
            if row.get("start_time") and row.get("end_time"):
                try:
                    s = datetime.fromisoformat(row["start_time"].replace("Z", "+00:00")).replace(tzinfo=None)
                    e = datetime.fromisoformat(row["end_time"].replace("Z", "+00:00")).replace(tzinfo=None)
                    return max(0.0, (e - s).total_seconds() / 3600.0)
                except Exception:
                    return 0.0
            return 0.0

        df["calculated_hrs"] = df.apply(compute_hours, axis=1)

        # High-level Summary Metrics
        total_tasks = len(df)
        completed_tasks = len(df[df["job_status"] == "Completed"])
        total_hours = df["calculated_hrs"].sum()
        active_tasks_count = len(df[df["job_status"] == "In Progress"])

        st.markdown("---")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Tasks", total_tasks)
        m2.metric("Completed Tasks", completed_tasks)
        m3.metric("Running Tasks", active_tasks_count)
        m4.metric("Total Hours Logged", f"{total_hours:.2f} hrs")

        # Summary Visual Charts
        st.markdown("### 📈 Summary Breakdown")
        c_left, c_right = st.columns(2)
        with c_left:
            st.caption("⏱️ Total Hours by Process")
            proc_hours = df.groupby("process")["calculated_hrs"].sum().sort_values(ascending=False)
            if not proc_hours.empty and proc_hours.sum() > 0:
                st.bar_chart(proc_hours)
            else:
                st.info("No hour data available for process breakdown.")

        with c_right:
            st.caption("🏢 Total Tasks by Customer")
            cust_counts = df["cust_name"].value_counts()
            if not cust_counts.empty:
                st.bar_chart(cust_counts)
            else:
                st.info("No task data available for customer breakdown.")

        # Detailed Report Table
        st.markdown("### 📋 Filtered Production Logs")
        display_columns = [
            c for c in [
                "id",
                "emp_id",
                "emp_name",
                "cust_name",
                "pro_name",
                "job_name",
                "chap_name",
                "process",
                "start_time",
                "end_time",
                "time_taken",
                "job_status",
                "system_start_name",
                "system_start_location",
                "system_end_name",
                "system_end_location",
                "remarks",
            ] if c in df.columns
        ]

        st.dataframe(df[display_columns], use_container_width=True)

        # Export to CSV
        csv_buffer = io.StringIO()
        df[display_columns].to_csv(csv_buffer, index=False)
        st.download_button(
            label="📥 Download Filtered Report (CSV)",
            data=csv_buffer.getvalue(),
            file_name=f"production_report_{start_date}_to_{end_date}.csv",
            mime="text/csv",
            type="primary",
        )
    else:
        st.info("No production records found matching the selected filters and date range.")
