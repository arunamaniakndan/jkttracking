import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, date, time

# ----------------- PAGE CONFIGURATION -----------------
st.set_page_config(
    page_title="Operations Production Portal",
    page_icon="🏢",
    layout="wide"
)

# ----------------- SUPABASE CONFIGURATION -----------------
# Fallback keys directly if secrets.toml is absent
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

# ----------------- ID GENERATOR HELPER -----------------
def generate_auto_id(table_name: str, id_column: str, prefix: str) -> str:
    try:
        res = supabase.table(table_name).select(id_column).execute()
        count = len(res.data) + 1 if res.data else 1
        return f"{prefix}{count:04d}"
    except Exception:
        # Fallback with timestamp if query fails
        return f"{prefix}{int(time.time()) % 10000:04d}"

# ----------------- SESSION STATE -----------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_info" not in st.session_state:
    st.session_state.user_info = {
        "emp_id": "",
        "emp_name": "Guest",
        "emp_role": "USER"
    }

# ----------------- AUTHENTICATION LOGIC -----------------
def login(emp_id, password):
    try:
        res = (
            supabase.table("master_employe")
            .select("*")
            .ilike("emp_id", emp_id.strip())
            .eq("emp_pwd", password.strip())
            .execute()
        )
        
        if res.data:
            user = res.data[0]
            if user.get("emp_status") != "Active":
                st.error("Your account is not active. Please contact administrator.")
                return False
            
            if user.get("expiry_date"):
                exp_date = datetime.strptime(user["expiry_date"], "%Y-%m-%d").date()
                if exp_date < date.today():
                    st.error("Your account has expired. Please contact administrator.")
                    return False

            st.session_state.authenticated = True
            st.session_state.user_info = {
                "emp_id": user["emp_id"],
                "emp_name": user["emp_name"],
                "emp_role": user.get("emp_role", "USER").upper()
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
        "emp_role": "USER"
    }
    st.rerun()

# ----------------- LOGIN WINDOW -----------------
if not st.session_state.authenticated:
    _, col_login, _ = st.columns([1, 1.5, 1])
    with col_login:
        st.markdown("<h2 style='text-align: center;'>🔐 Operations Portal Login</h2>", unsafe_allow_html=True)
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

st.sidebar.markdown(f"### 👤 Welcome, **{emp_name}**")
st.sidebar.caption(f"**Emp ID:** `{emp_id}` | **Role:** `{role}`")
if st.sidebar.button("Logout", use_container_width=True):
    logout()
st.sidebar.markdown("---")

if role == "ADMIN":
    menu_options = [
        "1. Master Employee",
        "2. Master Customer",
        "3. Master Project",
        "4. Master Process",
        "5. Master Job",
        "6. Job Entry"
    ]
else:
    menu_options = ["6. Job Entry"]

selected_page = st.sidebar.radio("Navigation", menu_options)

# ----------------- 1. MASTER EMPLOYEE -----------------
if selected_page == "1. Master Employee" and role == "ADMIN":
    st.title("👨‍💼 Master Employee")
    
    auto_emp_id = generate_auto_id("master_employe", "emp_id", "EMP")
    st.info(f"System Generated Employee ID: **{auto_emp_id}**")
    
    with st.form("emp_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        f_emp_name = c1.text_input("Employee Name *")
        f_emp_pwd = c2.text_input("Password *", type="password")
        
        c3, c4, c5 = st.columns(3)
        f_emp_role = c3.selectbox("Role", ["USER", "ADMIN"])
        f_expiry_date = c4.date_input("Expiry Date", value=date(2030, 12, 31))
        f_emp_status = c5.selectbox("Status", ["Active", "Inactive", "Suspended"])
        
        remarks = st.text_area("Remarks")
        
        if st.form_submit_button("➕ Add Employee", type="primary"):
            if f_emp_name and f_emp_pwd:
                supabase.table("master_employe").insert({
                    "emp_id": auto_emp_id,
                    "emp_name": f_emp_name.strip(),
                    "emp_pwd": f_emp_pwd.strip(),
                    "emp_role": f_emp_role,
                    "expiry_date": str(f_expiry_date),
                    "emp_status": f_emp_status,
                    "remarks": remarks
                }).execute()
                st.success(f"Employee {f_emp_name} added with ID: {auto_emp_id}")
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
    
    auto_cust_id = generate_auto_id("master_customer", "cust_id", "CUST")
    st.info(f"System Generated Customer ID: **{auto_cust_id}**")
    
    with st.form("cust_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        cust_name = c1.text_input("Customer Name *")
        cust_year = c2.number_input("Customer Year", min_value=2000, max_value=2099, value=date.today().year, step=1)
        
        c3, c4 = st.columns(2)
        cust_status = c3.selectbox("Status", ["Active", "Inactive"])
        remarks = c4.text_area("Remarks")
        
        if st.form_submit_button("➕ Add Customer", type="primary"):
            if cust_name:
                supabase.table("master_customer").insert({
                    "cust_id": auto_cust_id,
                    "cust_name": cust_name.strip(),
                    "cust_year": int(cust_year),
                    "cust_status": cust_status,
                    "remarks": remarks
                }).execute()
                st.success(f"Customer {cust_name} added with ID: {auto_cust_id}")
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
    
    auto_pro_id = generate_auto_id("master_project", "pro_id", "PRO")
    st.info(f"System Generated Project ID: **{auto_pro_id}**")
    
    with st.form("pro_form", clear_on_submit=True):
        pro_name = st.text_input("Project Name *")
        remarks = st.text_area("Remarks")
        
        if st.form_submit_button("➕ Add Project", type="primary"):
            if pro_name:
                supabase.table("master_project").insert({
                    "pro_id": auto_pro_id,
                    "pro_name": pro_name.strip(),
                    "remarks": remarks
                }).execute()
                st.success(f"Project '{pro_name}' added with ID: {auto_pro_id}")
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
    
    auto_proc_id = generate_auto_id("master_process", "process_id", "PRC")
    st.info(f"System Generated Process ID: **{auto_proc_id}**")
    
    with st.form("process_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        process_name = c1.text_input("Process Name *")
        process_status = c2.selectbox("Status", ["Active", "Inactive"])
        remarks = st.text_area("Remarks")
        
        if st.form_submit_button("➕ Add Process", type="primary"):
            if process_name:
                supabase.table("master_process").insert({
                    "process_id": auto_proc_id,
                    "process_name": process_name.strip(),
                    "process_status": process_status,
                    "remarks": remarks
                }).execute()
                st.success(f"Process '{process_name}' added with ID: {auto_proc_id}")
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
    cust_options = [c["cust_name"] for c in cust_res.data] if cust_res.data else []
    pro_options = [p["pro_name"] for p in pro_res.data] if pro_res.data else []

    mode = st.radio("Select Action Mode:", ["➕ Create New Job", "🔍 View / Select Existing Job"], horizontal=True)

    # MODE 1: CREATE NEW JOB
    if mode == "➕ Create New Job":
        auto_job_id = generate_auto_id("master_job", "job_id", f"JOB-{datetime.now().strftime('%Y%m')}-")
        st.info(f"New Generated Job ID: **{auto_job_id}**")
        
        with st.form("create_job_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            cust_name = c1.selectbox("Customer Name", cust_options if cust_options else ["None"])
            pro_name = c2.selectbox("Project Name", pro_options if pro_options else ["None"])
            job_name = c3.text_input("Job Name *")
            
            c4, c5, c6 = st.columns(3)
            rec_date = c4.date_input("Received Date", value=date.today())
            due_date = c5.date_input("Due Date", value=date.today())
            pages = c6.number_input("Pages", min_value=0, step=1)
            
            c7, c8 = st.columns(2)
            job_cost = c7.number_input("Job Cost ($/₹)", min_value=0.0, step=1.0, format="%.2f")
            job_status = c8.selectbox("Job Status", ["Pending", "In Progress", "Completed", "On Hold", "Cancelled"])
            
            remarks = st.text_area("Remarks")
            
            if st.form_submit_button("➕ Save New Job to Table", type="primary"):
                if job_name and cust_options and pro_options:
                    supabase.table("master_job").insert({
                        "job_id": auto_job_id,
                        "cust_name": cust_name,
                        "pro_name": pro_name,
                        "job_name": job_name.strip(),
                        "rec_date": str(rec_date),
                        "due_date": str(due_date),
                        "pages": int(pages),
                        "spend_hrs": 0.00,  # Starts at 0, updated only via Job Entry
                        "job_cost": float(job_cost),
                        "job_status": job_status,
                        "remarks": remarks
                    }).execute()
                    st.success(f"Job '{job_name}' created successfully with ID: {auto_job_id}")
                    st.rerun()
                else:
                    st.error("Please provide a Job Name and ensure Customers/Projects exist.")

    # MODE 2: VIEW EXISTING JOB (READ-ONLY SPEND HOURS)
    else:
        all_jobs_res = supabase.table("master_job").select("*").order("created_at", desc=True).execute()
        jobs_data = all_jobs_res.data if all_jobs_res.data else []
        
        if jobs_data:
            job_lookup = {f"{j['job_id']} - {j['job_name']} ({j['cust_name']})": j for j in jobs_data}
            selected_job_key = st.selectbox("Select Existing Job to Inspect:", list(job_lookup.keys()))
            selected_job = job_lookup[selected_job_key]
            
            st.markdown("---")
            # Metrics Overview
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Job ID", selected_job["job_id"])
            m2.metric("Total Spend Hours (Read-Only)", f"{float(selected_job.get('spend_hrs') or 0.0):.2f} hrs")
            m3.metric("Pages", selected_job.get("pages", 0))
            m4.metric("Job Cost", f"{float(selected_job.get('job_cost') or 0.0):.2f}")
            
            # Details breakdown
            c1, c2, c3 = st.columns(3)
            c1.text_input("Customer Name", value=selected_job.get("cust_name", ""), disabled=True)
            c2.text_input("Project Name", value=selected_job.get("pro_name", ""), disabled=True)
            c3.text_input("Job Name", value=selected_job.get("job_name", ""), disabled=True)
            
            c4, c5, c6 = st.columns(3)
            c4.text_input("Received Date", value=str(selected_job.get("rec_date", "")), disabled=True)
            c5.text_input("Due Date", value=str(selected_job.get("due_date", "")), disabled=True)
            c6.text_input("Current Status", value=selected_job.get("job_status", ""), disabled=True)
            
            st.text_area("Job Remarks", value=selected_job.get("remarks", "") or "No remarks provided.", disabled=True)
        else:
            st.info("No jobs registered yet. Use 'Create New Job' mode above.")

    st.subheader("All Master Jobs Registry")
    data = supabase.table("master_job").select("*").order("created_at", desc=True).execute()
    if data.data:
        st.dataframe(pd.DataFrame(data.data), use_container_width=True)

# ----------------- 6. JOB ENTRY (AUTOMATIC TIME ACCUMULATION) -----------------
elif selected_page == "6. Job Entry":
    st.title("⏱️ Production Job Entry")
    
    tab_start, tab_end, tab_logs = st.tabs(["▶️ Start Job Process", "⏹️ End Active Process", "📊 Production Logs"])
    
    # TAB 1: START
    with tab_start:
        st.subheader("Start a Task (Automatic Timestamp)")
        cust_res = supabase.table("master_customer").select("cust_name").eq("cust_status", "Active").execute()
        pro_res = supabase.table("master_project").select("pro_name").execute()
        job_res = supabase.table("master_job").select("job_name").execute()
        proc_res = supabase.table("master_process").select("process_name").eq("process_status", "Active").execute()
        
        cust_options = [c["cust_name"] for c in cust_res.data] if cust_res.data else []
        pro_options = [p["pro_name"] for p in pro_res.data] if pro_res.data else []
        job_options = [j["job_name"] for j in job_res.data] if job_res.data else []
        proc_options = [pr["process_name"] for pr in proc_res.data] if proc_res.data else []
        
        with st.form("start_job_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            cust_name = c1.selectbox("Customer", cust_options if cust_options else ["None"])
            pro_name = c2.selectbox("Project", pro_options if pro_options else ["None"])
            job_name = c3.selectbox("Job Name", job_options if job_options else ["None"])
            
            c4, c5 = st.columns(2)
            chap_name = c4.text_input("Chapter / Unit Name *")
            process = c5.selectbox("Process", proc_options if proc_options else ["Pagination", "XML Conversion", "QC Review"])
            remarks = st.text_area("Start Remarks")
            
            if st.form_submit_button("▶️ Start Job Now", type="primary", use_container_width=True):
                if chap_name and job_options:
                    start_iso = datetime.now().isoformat()
                    supabase.table("job_entry").insert({
                        "cust_name": cust_name,
                        "pro_name": pro_name,
                        "job_name": job_name,
                        "chap_name": chap_name.strip(),
                        "process": process,
                        "start_time": start_iso,
                        "end_time": None,
                        "time_taken": "Running...",
                        "job_status": "In Progress",
                        "remarks": f"Started by {emp_name}. {remarks}".strip()
                    }).execute()
                    
                    # Update master_job status
                    supabase.table("master_job").update({"job_status": "In Progress"}).eq("job_name", job_name).execute()
                    
                    st.success(f"Started '{process}' for '{chap_name}' at {datetime.now().strftime('%H:%M:%S')}")
                    st.rerun()
                else:
                    st.error("Please enter Chapter Name and select a valid Job.")

    # TAB 2: END
    with tab_end:
        st.subheader("Open Tasks Currently Running")
        open_tasks = supabase.table("job_entry").select("*").eq("job_status", "In Progress").order("id", desc=True).execute()
        
        if open_tasks.data:
            df_open = pd.DataFrame(open_tasks.data)
            st.dataframe(df_open[["id", "job_name", "chap_name", "process", "start_time", "job_status"]], use_container_width=True)
            
            task_dict = {
                f"ID {t['id']} | Job: {t['job_name']} | Chap: {t['chap_name']} | Proc: {t['process']} (Started: {t['start_time'][:19]})": t
                for t in open_tasks.data
            }
            
            with st.form("end_task_form"):
                selected_label = st.selectbox("Select Active Task to Complete:", list(task_dict.keys()))
                end_remarks = st.text_area("Completion Remarks (Optional)")
                
                if st.form_submit_button("⏹️ Complete & Update Total Spend Time", type="primary", use_container_width=True):
                    task = task_dict[selected_label]
                    task_id = task["id"]
                    t_job_name = task["job_name"]
                    
                    start_dt = datetime.fromisoformat(task["start_time"].replace("Z", "+00:00")).replace(tzinfo=None)
                    end_dt = datetime.now()
                    
                    diff = end_dt - start_dt
                    elapsed_seconds = max(0, diff.total_seconds())
                    added_hours = elapsed_seconds / 3600.0
                    
                    hrs, rem = divmod(elapsed_seconds, 3600)
                    mins, _ = divmod(rem, 60)
                    time_taken_str = f"{int(hrs)}h {int(mins)}m"
                    
                    # 1. Update job_entry
                    supabase.table("job_entry").update({
                        "end_time": end_dt.isoformat(),
                        "time_taken": time_taken_str,
                        "job_status": "Completed",
                        "remarks": f"{task.get('remarks', '')} | Finished: {end_remarks}".strip(" | ")
                    }).eq("id", task_id).execute()
                    
                    # 2. Update spend_hrs in master_job
                    job_query = supabase.table("master_job").select("spend_hrs").eq("job_name", t_job_name).execute()
                    current_spend_hrs = 0.0
                    if job_query.data and job_query.data[0].get("spend_hrs") is not None:
                        current_spend_hrs = float(job_query.data[0]["spend_hrs"])
                    
                    new_total_hrs = round(current_spend_hrs + added_hours, 2)
                    supabase.table("master_job").update({"spend_hrs": new_total_hrs}).eq("job_name", t_job_name).execute()
                    
                    st.success(f"Task completed! Duration: {time_taken_str}. Added {added_hours:.2f} hrs to Job '{t_job_name}' (Total Spend Hours: {new_total_hrs} hrs).")
                    st.rerun()
        else:
            st.info("No active tasks running at the moment.")

    # TAB 3: LOGS
    with tab_logs:
        st.subheader("All Production Logs")
        all_logs = supabase.table("job_entry").select("*").order("id", desc=True).execute()
        if all_logs.data:
            st.dataframe(pd.DataFrame(all_logs.data), use_container_width=True)