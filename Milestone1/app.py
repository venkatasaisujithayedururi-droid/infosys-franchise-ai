
%%writefile app.py
import os, re, html, sqlite3, jwt, bcrypt, datetime, time, secrets, smtplib, ssl
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from streamlit_option_menu import option_menu
from email.message import EmailMessage

# ============================================================
# STREAMLIT LIGHT THEME
# ============================================================
os.makedirs(".streamlit", exist_ok=True)

with open(".streamlit/config.toml", "w") as f:
    f.write(
        '[theme]\n'
        'base="light"\n'
        'primaryColor="#ffd803"\n'
        'backgroundColor="#f9fcfc"\n'
        'secondaryBackgroundColor="#e3f6f5"\n'
        'textColor="#2d334a"\n'
    )

st.set_page_config(
    page_title="Infosys Portal",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# COLORS
# ============================================================
COLORS = {
    "bg_main": "#f9fcfc",
    "bg_sidebar": "#e3f6f5",
    "bg_card": "#ffffff",
    "bg_card_alt": "#bae8e8",
    "text_main": "#2d334a",
    "text_heading": "#272343",
    "text_muted": "#64748b",
    "accent": "#ffd803",
    "accent_hover": "#e6c300",
    "accent_text": "#272343",
    "border": "#272343",
    "border_light": "#bae8e8",
    "success": "#34d399",
    "danger": "#f87171"
}

# ============================================================
# SECRETS / CONFIGURATION (all loaded from environment variables)
# Required : JWT_SECRET
# Optional : ADMIN_EMAIL, ADMIN_PASSWORD   -> creates the admin account
#            SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM
#                                          -> enables "Via OTP" password reset
# ============================================================
JWT_SECRET = os.environ.get("JWT_SECRET")

if not JWT_SECRET:
    st.error("JWT_SECRET is missing. Please load it from Colab Secrets.")
    st.stop()

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "").lower().strip()
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

MAX_FAILS = 5            # failed attempts before a lockout
LOCK_SECONDS = 15 * 60   # lockout length
OTP_VALID_SECONDS = 10 * 60

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

SECURITY_QUESTIONS = [
    "What is your pet name?",
    "What is your mother's maiden name?",
    "What is your favourite city?"
]

# ============================================================
# CUSTOM CSS
# ============================================================
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&family=Inter:wght@300;400;500;600&display=swap');

    html, body, .stApp {{
        background: {COLORS['bg_main']} !important;
        font-family: 'Inter', sans-serif !important;
        color: {COLORS['text_main']} !important;
    }}

    footer, div[data-testid="stDecoration"] {{
        visibility: hidden !important;
        display: none !important;
    }}

    header {{
        background: transparent !important;
        z-index: 999999 !important;
    }}

    button[kind="header"],
    div[data-testid="stSidebarCollapsedControl"] button {{
        visibility: visible !important;
        display: flex !important;
        opacity: 1 !important;
        background-color: {COLORS['accent']} !important;
        border: 2px solid {COLORS['border']} !important;
        border-radius: 8px !important;
        padding: 6px !important;
        margin: 8px !important;
        box-shadow: 3px 3px 0px {COLORS['border']} !important;
    }}

    button[kind="header"] svg,
    div[data-testid="stSidebarCollapsedControl"] svg {{
        fill: {COLORS['text_heading']} !important;
        color: {COLORS['text_heading']} !important;
        stroke: {COLORS['text_heading']} !important;
    }}

    .block-container {{
        padding: 2rem 2.5rem !important;
        max-width: 1200px;
    }}

    h1, h2, h3, h4 {{
        font-family: 'Poppins', sans-serif !important;
        color: {COLORS['text_heading']} !important;
    }}

    label p {{
        font-weight: 600 !important;
        color: {COLORS['text_heading']} !important;
    }}

    div[data-baseweb="base-input"],
    div[data-baseweb="select"] > div {{
        background-color: transparent !important;
        border: none !important;
    }}

    div[data-baseweb="input"],
    div[data-baseweb="select"] {{
        background-color: {COLORS['bg_card']} !important;
        border: 2px solid {COLORS['border']} !important;
        border-radius: 10px !important;
    }}

    div[data-baseweb="input"]:focus-within {{
        border-color: {COLORS['accent']} !important;
        box-shadow: 4px 4px 0px {COLORS['border']} !important;
    }}

    input, div[data-baseweb="select"] span {{
        color: {COLORS['text_main']} !important;
        -webkit-text-fill-color: {COLORS['text_main']} !important;
    }}

    div[data-testid="stButton"] button,
    div[data-testid="stDownloadButton"] button,
    div[data-testid="stFormSubmitButton"] button {{
        background-color: {COLORS['accent']} !important;
        color: {COLORS['accent_text']} !important;
        border: 2px solid {COLORS['border']} !important;
        border-radius: 10px !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        height: 48px !important;
        min-height: 48px !important;
        white-space: nowrap !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        padding: 0px 16px !important;
        box-shadow: 4px 4px 0px {COLORS['border']} !important;
        width: 100%;
        transition: all 0.2s ease !important;
    }}

    div[data-testid="stButton"] button:hover,
    div[data-testid="stDownloadButton"] button:hover,
    div[data-testid="stFormSubmitButton"] button:hover {{
        background-color: {COLORS['accent_hover']} !important;
        transform: translate(-2px, -2px) !important;
        box-shadow: 6px 6px 0px {COLORS['border']} !important;
    }}

    div[data-testid="stButton"] button:disabled,
    div[data-testid="stFormSubmitButton"] button:disabled {{
        opacity: 0.5 !important;
        box-shadow: none !important;
    }}

    section[data-testid="stSidebar"] {{
        background: {COLORS['bg_sidebar']} !important;
        border-right: 2px solid {COLORS['border']} !important;
    }}

    .pn-card {{
        background: {COLORS['bg_card']};
        border: 2px solid {COLORS['border']};
        border-radius: 14px;
        padding: 24px;
        box-shadow: 4px 4px 0px {COLORS['border_light']};
    }}
</style>
""", unsafe_allow_html=True)

# ============================================================
# DATABASE AND PASSWORD FUNCTIONS
# ============================================================
def get_db():
    return sqlite3.connect(
        "infosys_portal.db",
        check_same_thread=False
    )

def hash_txt(text):
    return bcrypt.hashpw(
        text.encode(),
        bcrypt.gensalt()
    ).decode()

def check_txt(text, hashed_text):
    return (
        bcrypt.checkpw(text.encode(), hashed_text.encode())
        if hashed_text else False
    )

@st.cache_resource
def dummy_hash():
    # Used so a login for an unknown email takes about as long as a real one.
    return hash_txt("dummy-password-for-timing")

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                email TEXT UNIQUE,
                password_hash TEXT,
                security_question TEXT,
                security_answer_hash TEXT
            )
        """)

        # Migration: add the is_admin flag to older databases.
        cols = [row[1] for row in conn.execute("PRAGMA table_info(users)")]
        if "is_admin" not in cols:
            conn.execute(
                "ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0"
            )

        # Failed-attempt counters and lockouts.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS attempts (
                key TEXT PRIMARY KEY,
                count INTEGER DEFAULT 0,
                locked_until REAL DEFAULT 0
            )
        """)

        # Join date (backfilled for old users, auto-set for new ones).
        if "created_at" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN created_at TEXT")
            conn.execute(
                "UPDATE users SET created_at = datetime('now') "
                "WHERE created_at IS NULL"
            )
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS set_created_at
            AFTER INSERT ON users
            WHEN NEW.created_at IS NULL
            BEGIN
                UPDATE users SET created_at = datetime('now')
                WHERE id = NEW.id;
            END
        """)

        # New profile / status columns.
        if "is_active" not in cols:
            conn.execute(
                "ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1"
            )
        if "phone" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN phone TEXT DEFAULT ''")
        if "bio" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN bio TEXT DEFAULT ''")

        # Admin announcements shown on user dashboards.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT,
                ts TEXT DEFAULT (datetime('now'))
            )
        """)

        # Personal notes per user.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT,
                text TEXT,
                ts TEXT DEFAULT (datetime('now'))
            )
        """)

        # Per-user activity log (times are UTC).
        conn.execute("""
            CREATE TABLE IF NOT EXISTS activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT,
                event TEXT,
                ts TEXT DEFAULT (datetime('now'))
            )
        """)

        # Remove the old hardcoded admin account, if it still exists.
        if ADMIN_EMAIL != "infosys@ai":
            conn.execute("DELETE FROM users WHERE email = ?", ("infosys@ai",))

        # Create the admin from environment variables (never hardcoded).
        if ADMIN_EMAIL and ADMIN_PASSWORD:
            exists = conn.execute(
                "SELECT id FROM users WHERE email = ?", (ADMIN_EMAIL,)
            ).fetchone()

            if exists:
                conn.execute(
                    "UPDATE users SET is_admin = 1 WHERE email = ?",
                    (ADMIN_EMAIL,)
                )
            else:
                conn.execute(
                    """INSERT INTO users
                    (username, email, password_hash, security_question,
                     security_answer_hash, is_admin)
                    VALUES (?, ?, ?, ?, ?, 1)""",
                    (
                        "Administrator",
                        ADMIN_EMAIL,
                        hash_txt(ADMIN_PASSWORD),
                        SECURITY_QUESTIONS[0],
                        hash_txt(secrets.token_hex(16))  # unguessable
                    )
                )

init_db()

# ============================================================
# VALIDATION
# ============================================================
def password_error(pwd):
    if len(pwd) < 8:
        return "Password must be at least 8 characters."
    if not re.search(r"[A-Za-z]", pwd) or not re.search(r"\d", pwd):
        return "Password must contain at least one letter and one number."
    return None

def password_strength(pwd):
    score = sum([
        len(pwd) >= 8,
        len(pwd) >= 12,
        bool(re.search(r"[a-z]", pwd)) and bool(re.search(r"[A-Z]", pwd)),
        bool(re.search(r"\d", pwd)),
        bool(re.search(r"[^A-Za-z0-9]", pwd)),
    ])
    labels = ["Very weak", "Weak", "Fair", "Good", "Strong", "Very strong"]
    return score, labels[score]

def show_strength(pwd):
    if pwd:
        score, label = password_strength(pwd)
        st.progress(score / 5, text=f"Password strength: {label}")

# ============================================================
# BRUTE-FORCE PROTECTION
# ============================================================
def lock_remaining(key):
    with get_db() as conn:
        row = conn.execute(
            "SELECT locked_until FROM attempts WHERE key = ?", (key,)
        ).fetchone()
    if row and row[0] and row[0] > time.time():
        return int(row[0] - time.time())
    return 0

def record_fail(key):
    with get_db() as conn:
        row = conn.execute(
            "SELECT count FROM attempts WHERE key = ?", (key,)
        ).fetchone()
        count = (row[0] if row else 0) + 1
        locked_until = 0
        if count >= MAX_FAILS:
            locked_until = time.time() + LOCK_SECONDS
            count = 0
        conn.execute(
            """INSERT INTO attempts (key, count, locked_until)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                count = excluded.count,
                locked_until = excluded.locked_until""",
            (key, count, locked_until)
        )

def clear_fails(key):
    with get_db() as conn:
        conn.execute("DELETE FROM attempts WHERE key = ?", (key,))

def lock_message(seconds):
    minutes = max(1, -(-seconds // 60))
    return f"🔒 Too many failed attempts. Try again in {minutes} minute(s)."

# ============================================================
# ACTIVITY LOG
# ============================================================
def log_event(email, event):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO activity (email, event) VALUES (?, ?)",
            (email, event)
        )

# ============================================================
# EMAIL OTP
# ============================================================
def smtp_configured():
    return all(
        os.environ.get(k)
        for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD")
    )

def send_otp_email(to_email, code):
    try:
        host = os.environ["SMTP_HOST"]
        port = int(os.environ.get("SMTP_PORT", "465"))
        user = os.environ["SMTP_USER"]
        password = os.environ["SMTP_PASSWORD"]
        sender = os.environ.get("SMTP_FROM", user)

        msg = EmailMessage()
        msg["Subject"] = "Your Authentication Portal verification code"
        msg["From"] = sender
        msg["To"] = to_email
        msg.set_content(
            f"Your one-time code is {code}.\n"
            f"It expires in {OTP_VALID_SECONDS // 60} minutes.\n\n"
            "If you did not request this, you can ignore this email."
        )

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=context) as server:
            server.login(user, password)
            server.send_message(msg)
        return True
    except Exception:
        return False

# ============================================================
# JWT FUNCTIONS
# ============================================================
def make_jwt(email):
    expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=2)

    return jwt.encode(
        {
            "email": email,
            "exp": expiry
        },
        JWT_SECRET,
        algorithm="HS256"
    )

def verify_jwt(token):
    try:
        return jwt.decode(
            token,
            JWT_SECRET,
            algorithms=["HS256"]
        )
    except jwt.PyJWTError:
        return None

# ============================================================
# SESSION STATE
# ============================================================
for key, value in [
    ("token", None),
    ("page", "Login"),
    ("reset_email", None),
    ("reset_mode", None),
    ("sq_p", None),
    ("otp_hash", None),
    ("otp_expiry", 0)
]:
    if key not in st.session_state:
        st.session_state[key] = value

def navigate(page):
    st.session_state.page = page
    st.rerun()

def clear_reset_state():
    st.session_state.reset_email = None
    st.session_state.reset_mode = None
    st.session_state.sq_p = None
    st.session_state.otp_hash = None
    st.session_state.otp_expiry = 0

# ============================================================
# AUTHENTICATION PAGE HEADER
# ============================================================
def auth_header(title, sub="Secure User Authentication System"):
    st.markdown(f"""
    <div style="text-align:center;padding:1.5rem 0 1rem;">
        <div style="font-size:40px;margin-bottom:10px;">🔐</div>
        <h1 style="font-size:2rem !important;margin:0;">
            Authentication Portal
        </h1>
        <p style="color:{COLORS['text_muted']};font-size:14px;margin:4px 0 0;">
            {sub}
        </p>
    </div>
    <div style="text-align:center;margin-bottom:1.5rem;">
        <span style="font-size:1.1rem;font-weight:700;color:{COLORS['text_heading']};">
            {title}
        </span>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# PASSWORD RESET VERIFICATION
# ============================================================
def verify_reset(email, mode, answer):
    """Returns 'ok', 'bad' or 'locked'."""
    key = f"reset:{email}"

    if lock_remaining(key):
        return "locked"

    ok = False

    if mode == "sq":
        with get_db() as conn:
            row = conn.execute(
                "SELECT security_answer_hash FROM users WHERE email = ?",
                (email,)
            ).fetchone()
        ok = bool(row) and check_txt(answer, row[0])

    elif mode == "otp":
        otp_hash = st.session_state.otp_hash
        ok = (
            bool(otp_hash)
            and time.time() < st.session_state.otp_expiry
            and check_txt(answer, otp_hash)
        )

    if ok:
        clear_fails(key)
        return "ok"

    record_fail(key)
    return "bad"

# ============================================================
# PAGE ROUTING: LOGIN, SIGNUP, FORGOT PASSWORD
# ============================================================
if not st.session_state.token:

    if st.session_state.page not in ["Login", "Signup", "Forgot"]:
        st.session_state.page = "Login"

    _, mid, _ = st.columns([1, 1.45, 1])

    with mid:

        # ---------------- LOGIN ----------------
        if st.session_state.page == "Login":
            admin_mode = st.session_state.get(
                "login_role", "👤 User"
            ).endswith("Admin")

            if admin_mode:
                auth_header(
                    "Admin sign in",
                    "Administrator access only"
                )
            else:
                auth_header("Sign in to your account")

            st.radio(
                "Sign in as",
                ["👤 User", "🛡️ Admin"],
                horizontal=True,
                key="login_role"
            )

            email = st.text_input(
                "Admin email address" if admin_mode else "Email address",
                placeholder="admin@example.com" if admin_mode
                else "you@example.com"
            ).strip().lower()

            pwd = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password"
            )

            if admin_mode:
                st.caption(
                    "Admin accounts are set up by the portal owner. "
                    "Regular users should choose 'User' above."
                )

            st.markdown("<br>", unsafe_allow_html=True)

            if admin_mode:
                col_l, col_r = st.columns(2)
                col_c = None
            else:
                col_l, col_c, col_r = st.columns([1, 1.15, 1.3])

            if col_l.button("Sign In →", use_container_width=True):
                key = f"login:{email}"
                wait = lock_remaining(key)

                if wait:
                    st.error(lock_message(wait))
                else:
                    with get_db() as conn:
                        user = conn.execute(
                            "SELECT password_hash, is_active, is_admin "
                            "FROM users WHERE email = ?",
                            (email,)
                        ).fetchone()

                    # Always run a bcrypt check so timing doesn't reveal
                    # whether the email exists.
                    stored = user[0] if user else dummy_hash()
                    valid = check_txt(pwd, stored) and bool(user)

                    if admin_mode and valid and not user[2]:
                        # Right password, but not an admin: give the same
                        # generic error as a wrong password.
                        record_fail(key)
                        log_event(email, "Blocked admin sign-in (not an admin)")
                        st.error("❌ Invalid admin email or password.")

                    elif valid and user[1] == 0:
                        log_event(email, "Blocked sign-in (suspended)")
                        st.error(
                            "🚫 This account is suspended. "
                            "Please contact an administrator."
                        )

                    elif valid:
                        clear_fails(key)
                        log_event(email, "Signed in")
                        st.session_state.token = make_jwt(email)
                        navigate("Dashboard")

                    else:
                        record_fail(key)
                        if user:  # only log real accounts, not random emails
                            log_event(email, "Failed sign-in")
                        st.error(
                            "❌ Invalid admin email or password."
                            if admin_mode
                            else "❌ Invalid email address or password."
                        )

            if col_c is not None and col_c.button(
                "Create Account", use_container_width=True
            ):
                navigate("Signup")

            if col_r.button("Forgot Password", use_container_width=True):
                navigate("Forgot")

        # ---------------- SIGNUP ----------------
        elif st.session_state.page == "Signup":
            auth_header(
                "Create an account",
                "Join Authentication Portal today"
            )

            uname = st.text_input(
                "Full name / Username",
                placeholder="Enter your full name"
            ).strip()

            email = st.text_input(
                "Email address",
                placeholder="you@example.com"
            ).lower().strip()

            pwd = st.text_input(
                "Password",
                type="password",
                placeholder="Minimum 8 characters, letters and numbers"
            )
            show_strength(pwd)

            confirm_pwd = st.text_input(
                "Confirm password",
                type="password",
                placeholder="Re-enter your password"
            )

            sq = st.selectbox("Security Question", SECURITY_QUESTIONS)

            sa = st.text_input(
                "Your answer",
                placeholder="Enter your security answer"
            )

            st.markdown("<br>", unsafe_allow_html=True)

            if st.button(
                "Create Account & Login →",
                use_container_width=True
            ):
                if not uname or not email or not pwd or not sa.strip():
                    st.error("⚠️ Please fill in all fields.")

                elif len(uname) < 2 or len(uname) > 50:
                    st.error("⚠️ Name must be between 2 and 50 characters.")

                elif not EMAIL_RE.match(email):
                    st.error("⚠️ Please enter a valid email address.")

                elif password_error(pwd):
                    st.error(f"⚠️ {password_error(pwd)}")

                elif pwd != confirm_pwd:
                    st.error("❌ Passwords do not match.")

                else:
                    try:
                        with get_db() as conn:
                            conn.execute(
                                """INSERT INTO users
                                (username, email, password_hash,
                                 security_question, security_answer_hash,
                                 is_admin)
                                VALUES (?, ?, ?, ?, ?, 0)""",
                                (
                                    uname,
                                    email,
                                    hash_txt(pwd),
                                    sq,
                                    hash_txt(sa.lower().strip())
                                )
                            )

                        log_event(email, "Account created")
                        st.session_state.token = make_jwt(email)
                        st.success("✅ Account created successfully!")
                        time.sleep(1)
                        navigate("Dashboard")

                    except sqlite3.IntegrityError:
                        st.error(
                            "❌ Could not create the account. The email or "
                            "username may already be registered."
                        )

            st.markdown("<br>", unsafe_allow_html=True)

            if st.button("← Back to Sign In", use_container_width=True):
                navigate("Login")

        # ---------------- FORGOT PASSWORD ----------------
        elif st.session_state.page == "Forgot":
            auth_header(
                "Reset your password",
                "Choose your verification method"
            )

            if not st.session_state.reset_email:
                email = st.text_input(
                    "Registered email address",
                    placeholder="you@example.com"
                ).lower().strip()

                st.markdown("<br>", unsafe_allow_html=True)

                col_sq, col_otp = st.columns(2)

                # ---- Via security question ----
                if col_sq.button(
                    "Via Security Question",
                    use_container_width=True
                ):
                    if not email:
                        st.error("⚠️ Please enter your email address.")
                    else:
                        with get_db() as conn:
                            user = conn.execute(
                                "SELECT security_question FROM users WHERE email = ?",
                                (email,)
                            ).fetchone()

                        # Unknown emails get a stable decoy question so the
                        # response doesn't reveal who is registered.
                        question = (
                            user[0] if user
                            else SECURITY_QUESTIONS[
                                sum(email.encode()) % len(SECURITY_QUESTIONS)
                            ]
                        )

                        st.session_state.reset_email = email
                        st.session_state.sq_p = question
                        st.session_state.reset_mode = "sq"
                        st.rerun()

                # ---- Via email OTP ----
                if col_otp.button(
                    "Via OTP",
                    use_container_width=True
                ):
                    if not smtp_configured():
                        st.info(
                            "Email OTP is not configured. "
                            "Please use Via Security Question."
                        )
                    elif not email:
                        st.error("⚠️ Please enter your email address.")
                    elif lock_remaining(f"otpsend:{email}"):
                        st.error(
                            "🔒 Too many requests. Please try again later."
                        )
                    else:
                        record_fail(f"otpsend:{email}")  # throttles sending

                        with get_db() as conn:
                            user = conn.execute(
                                "SELECT id FROM users WHERE email = ?",
                                (email,)
                            ).fetchone()

                        st.session_state.otp_hash = None
                        st.session_state.otp_expiry = 0

                        if user:
                            code = f"{secrets.randbelow(10**6):06d}"
                            if send_otp_email(email, code):
                                st.session_state.otp_hash = hash_txt(code)
                                st.session_state.otp_expiry = (
                                    time.time() + OTP_VALID_SECONDS
                                )

                        # Same response whether or not the email exists.
                        st.session_state.reset_email = email
                        st.session_state.reset_mode = "otp"
                        st.rerun()

            else:
                mode = st.session_state.reset_mode

                if mode == "sq":
                    st.info(
                        f"❓ **Security Question:** {st.session_state.sq_p}"
                    )
                    ans_label = "Your answer"
                else:
                    st.info(
                        "If that email is registered, a 6-digit code has "
                        f"been sent. It expires in {OTP_VALID_SECONDS // 60} "
                        "minutes."
                    )
                    ans_label = "One-time code"

                ans = st.text_input(ans_label).lower().strip()

                npw = st.text_input(
                    "New password (minimum 8 characters, letters and numbers)",
                    type="password"
                )

                confirm_npw = st.text_input(
                    "Confirm new password",
                    type="password"
                )

                st.markdown("<br>", unsafe_allow_html=True)

                if st.button(
                    "Reset Password →",
                    use_container_width=True
                ):
                    reset_email = st.session_state.reset_email

                    if password_error(npw):
                        st.error(f"⚠️ {password_error(npw)}")

                    elif npw != confirm_npw:
                        st.error("❌ Passwords do not match.")

                    else:
                        result = verify_reset(reset_email, mode, ans)

                        if result == "locked":
                            st.error(
                                lock_message(
                                    lock_remaining(f"reset:{reset_email}")
                                )
                            )

                        elif result == "ok":
                            with get_db() as conn:
                                conn.execute(
                                    """UPDATE users
                                    SET password_hash = ?
                                    WHERE email = ?""",
                                    (hash_txt(npw), reset_email)
                                )

                            clear_fails(f"login:{reset_email}")
                            log_event(reset_email, "Password reset")
                            st.success("✅ Password updated successfully!")
                            time.sleep(1)
                            clear_reset_state()
                            navigate("Login")

                        else:
                            st.error(
                                "❌ Verification failed. Check your details "
                                "and try again."
                            )

            st.markdown("<br>", unsafe_allow_html=True)

            if st.button("← Cancel", use_container_width=True):
                clear_reset_state()
                navigate("Login")

# ============================================================
# DASHBOARDS
# ============================================================
else:
    payload = verify_jwt(st.session_state.token)

    if not payload:
        st.session_state.token = None
        st.session_state.page = "Login"
        st.rerun()

    email = payload["email"]

    with get_db() as conn:
        user = conn.execute(
            "SELECT username, is_admin, is_active FROM users WHERE email = ?",
            (email,)
        ).fetchone()

    if not user or user[2] == 0:
        st.session_state.token = None
        st.session_state.page = "Login"
        st.rerun()

    uname = html.escape(user[0])
    is_admin = bool(user[1])

    # ========================================================
    # SIDEBAR MENU
    # ========================================================
    with st.sidebar:
        st.markdown(f"""
        <div style="padding:16px 8px;text-align:center;">
            <div style="font-size:28px;">🔐</div>
            <div style="font-weight:700;font-size:16px;color:{COLORS['text_heading']};">
                Authentication Portal
            </div>
            <div style="font-size:11px;color:{COLORS['text_muted']};">
                {"Admin Panel" if is_admin else "User Account"}
            </div>
        </div>
        <hr style="border-color:{COLORS['border_light']};">
        """, unsafe_allow_html=True)

        if is_admin:
            opts = ["Dashboard", "Profile", "Settings", "Logout"]
            icons = ["house", "person", "gear", "box-arrow-right"]
        else:
            opts = ["Dashboard", "Analytics", "Reports", "Profile",
                    "Settings", "Logout"]
            icons = ["house", "graph-up", "file-text", "person",
                     "gear", "box-arrow-right"]

        menu = option_menu(
            None,
            opts,
            icons=icons,
            styles={
                "container": {
                    "background-color": COLORS["bg_sidebar"]
                },
                "nav-link-selected": {
                    "background-color": COLORS["accent"],
                    "color": COLORS["accent_text"]
                }
            }
        )

        if menu == "Logout":
            st.session_state.token = None
            st.session_state.page = "Login"
            st.rerun()

    # ========================================================
    # SHARED HEADER
    # ========================================================
    def dash_header(subtitle, badge):
        st.markdown(f"""
        <div style="background:{COLORS['text_heading']};
                    border-radius:16px;padding:24px 32px;
                    display:flex;justify-content:space-between;
                    align-items:center;margin-bottom:24px;">
            <div>
                <h1 style="color:{COLORS['accent']} !important;
                           margin:0;font-size:24px !important;">
                    🔐 Authentication Portal
                </h1>
                <div style="color:{COLORS['bg_card_alt']};font-size:13px;">
                    {subtitle}
                </div>
            </div>
            <div style="background:{COLORS['accent']};
                        padding:8px 18px;border-radius:30px;
                        font-weight:700;color:{COLORS['text_heading']};">
                {badge} {uname}
            </div>
        </div>
        """, unsafe_allow_html=True)

    def stat_card(col, icon, label, value):
        col.markdown(f"""
        <div class="pn-card" style="text-align:center;">
            <div style="font-size:28px;">{icon}</div>
            <div style="font-size:26px;font-weight:700;
                        color:{COLORS['text_heading']};">
                {value}
            </div>
            <div style="color:{COLORS['text_muted']};
                        font-size:12px;font-weight:600;">
                {label}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ========================================================
    # SETTINGS PAGE (all roles): change password
    # ========================================================
    if menu == "Settings":
        dash_header(
            "Settings",
            "🛡️" if is_admin else "👤"
        )

        st.subheader("Change password")

        cur_pwd = st.text_input("Current password", type="password")
        new_pwd = st.text_input(
            "New password (minimum 8 characters, letters and numbers)",
            type="password"
        )
        show_strength(new_pwd)
        confirm_new = st.text_input("Confirm new password", type="password")

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("Update Password →"):
            key = f"chg:{email}"
            wait = lock_remaining(key)

            if wait:
                st.error(lock_message(wait))

            elif password_error(new_pwd):
                st.error(f"⚠️ {password_error(new_pwd)}")

            elif new_pwd != confirm_new:
                st.error("❌ Passwords do not match.")

            else:
                with get_db() as conn:
                    row = conn.execute(
                        "SELECT password_hash FROM users WHERE email = ?",
                        (email,)
                    ).fetchone()

                if row and check_txt(cur_pwd, row[0]):
                    clear_fails(key)
                    with get_db() as conn:
                        conn.execute(
                            "UPDATE users SET password_hash = ? WHERE email = ?",
                            (hash_txt(new_pwd), email)
                        )
                    log_event(email, "Password changed")
                    st.success("✅ Password updated successfully!")
                else:
                    record_fail(key)
                    st.error("❌ Current password is incorrect.")

    # ========================================================
    # PROFILE PAGE (all roles)
    # ========================================================
    elif menu == "Profile":
        dash_header("My Profile", "🛡️" if is_admin else "👤")

        with get_db() as conn:
            created, phone, bio = conn.execute(
                "SELECT created_at, phone, bio FROM users WHERE email = ?",
                (email,)
            ).fetchone()
            last_login = conn.execute(
                "SELECT MAX(ts) FROM activity "
                "WHERE email = ? AND event = 'Signed in'", (email,)
            ).fetchone()[0]
            my_logs = conn.execute(
                "SELECT event, ts FROM activity WHERE email = ? "
                "ORDER BY id DESC LIMIT 100", (email,)
            ).fetchall()

        initials = html.escape(
            "".join(w[0] for w in user[0].split()[:2]).upper() or "U"
        )

        st.markdown(f"""
        <div class="pn-card" style="display:flex;align-items:center;gap:20px;
                                    margin-bottom:20px;">
            <div style="width:72px;height:72px;border-radius:50%;
                        background:{COLORS['accent']};
                        border:2px solid {COLORS['border']};
                        display:flex;align-items:center;justify-content:center;
                        font-size:28px;font-weight:700;
                        color:{COLORS['text_heading']};">
                {initials}
            </div>
            <div>
                <div style="font-size:20px;font-weight:700;
                            color:{COLORS['text_heading']};">{uname}</div>
                <div style="color:{COLORS['text_muted']};font-size:13px;">
                    {html.escape(email)}</div>
                <div style="font-size:12px;margin-top:4px;">
                    {"🛡️ Administrator" if is_admin else "👤 User"}
                    &nbsp;•&nbsp; Member since {(created or "unknown")[:10]}
                    &nbsp;•&nbsp; Last sign-in {last_login or "n/a"} UTC
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        t_det, t_sec, t_act, t_del = st.tabs(
            ["📝 Details", "🔑 Security", "🧾 My Activity", "⚠️ Danger Zone"]
        )

        # ---------------- DETAILS ----------------
        with t_det:
            st.text_input("Email address", value=email, disabled=True)
            new_name = st.text_input(
                "Full name / Username", value=user[0]
            ).strip()
            new_phone = st.text_input(
                "Phone number (optional)", value=phone or ""
            ).strip()
            new_bio = st.text_area(
                "About me (optional, max 200 characters)",
                value=bio or "", max_chars=200
            ).strip()

            st.markdown("<br>", unsafe_allow_html=True)

            if st.button("Save Profile →"):
                if len(new_name) < 2 or len(new_name) > 50:
                    st.error("⚠️ Name must be between 2 and 50 characters.")
                elif new_phone and not re.fullmatch(r"[0-9+\-\s()]{7,20}", new_phone):
                    st.error("⚠️ Please enter a valid phone number.")
                else:
                    try:
                        with get_db() as conn:
                            conn.execute(
                                "UPDATE users SET username = ?, phone = ?, "
                                "bio = ? WHERE email = ?",
                                (new_name, new_phone, new_bio, email)
                            )
                        log_event(email, "Profile updated")
                        st.success("✅ Profile updated!")
                        time.sleep(1)
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("❌ That name is already taken.")

        # ---------------- SECURITY ----------------
        with t_sec:
            st.subheader("Change security question")
            st.caption(
                "Used for password reset. Your current password is required."
            )

            new_sq = st.selectbox(
                "New security question", SECURITY_QUESTIONS, key="prof_sq"
            )
            new_sa = st.text_input("New answer", key="prof_sa")
            sec_pwd = st.text_input(
                "Current password", type="password", key="prof_sec_pwd"
            )

            st.markdown("<br>", unsafe_allow_html=True)

            if st.button("Update Security Question →"):
                key = f"sec:{email}"
                wait = lock_remaining(key)

                if wait:
                    st.error(lock_message(wait))
                elif not new_sa.strip():
                    st.error("⚠️ Please enter an answer.")
                else:
                    with get_db() as conn:
                        row = conn.execute(
                            "SELECT password_hash FROM users WHERE email = ?",
                            (email,)
                        ).fetchone()

                    if row and check_txt(sec_pwd, row[0]):
                        clear_fails(key)
                        with get_db() as conn:
                            conn.execute(
                                "UPDATE users SET security_question = ?, "
                                "security_answer_hash = ? WHERE email = ?",
                                (new_sq, hash_txt(new_sa.lower().strip()), email)
                            )
                        log_event(email, "Security question changed")
                        st.success("✅ Security question updated!")
                    else:
                        record_fail(key)
                        st.error("❌ Current password is incorrect.")

            st.markdown("---")
            st.caption("To change your password, open **Settings** in the menu.")

        # ---------------- MY ACTIVITY ----------------
        with t_act:
            if my_logs:
                my_df = pd.DataFrame(my_logs, columns=["Event", "Time (UTC)"])
                st.dataframe(my_df, use_container_width=True, hide_index=True)
                st.download_button(
                    "⬇ Download my activity",
                    data=my_df.to_csv(index=False).encode(),
                    file_name="my_activity.csv",
                    mime="text/csv"
                )
            else:
                st.caption("No activity yet.")

        # ---------------- DANGER ZONE ----------------
        with t_del:
            st.subheader("Delete my account")

            if is_admin:
                st.info(
                    "Admin accounts can't be deleted here. Ask another "
                    "administrator to remove or demote this account."
                )
            else:
                st.warning(
                    "This permanently deletes your account, notes and "
                    "activity. It cannot be undone."
                )
                del_pwd = st.text_input(
                    "Confirm with your password", type="password", key="del_pwd"
                )
                del_ok = st.checkbox("I understand this cannot be undone")

                if st.button("Delete my account", disabled=not del_ok):
                    key = f"del:{email}"
                    wait = lock_remaining(key)

                    if wait:
                        st.error(lock_message(wait))
                    else:
                        with get_db() as conn:
                            row = conn.execute(
                                "SELECT password_hash FROM users WHERE email = ?",
                                (email,)
                            ).fetchone()

                        if row and check_txt(del_pwd, row[0]):
                            with get_db() as conn:
                                for tbl in ("users", "activity", "notes"):
                                    conn.execute(
                                        f"DELETE FROM {tbl} WHERE email = ?",
                                        (email,)
                                    )
                            clear_fails(key)
                            st.session_state.token = None
                            st.session_state.page = "Login"
                            st.rerun()
                        else:
                            record_fail(key)
                            st.error("❌ Password is incorrect.")

    # ========================================================
    # ADMIN DASHBOARD
    # ========================================================
    elif is_admin:
        dash_header("Admin Control Panel", "🛡️")

        with get_db() as conn:
            rows = conn.execute(
                """SELECT u.username, u.email, u.is_admin, u.created_at,
                          u.is_active,
                          (SELECT MAX(ts) FROM activity a
                           WHERE a.email = u.email AND a.event = 'Signed in')
                   FROM users u ORDER BY u.id"""
            ).fetchall()
            locked = conn.execute(
                "SELECT COUNT(*) FROM attempts WHERE locked_until > ?",
                (time.time(),)
            ).fetchone()[0]
            trend = conn.execute(
                "SELECT substr(ts, 1, 10), event, COUNT(*) FROM activity "
                "WHERE event IN ('Signed in', 'Failed sign-in') "
                "AND ts >= date('now', '-13 days') GROUP BY 1, 2"
            ).fetchall()
            event_types = [
                r[0] for r in conn.execute(
                    "SELECT DISTINCT event FROM activity ORDER BY event"
                )
            ]
            announcements = conn.execute(
                "SELECT id, message, ts FROM announcements ORDER BY id DESC"
            ).fetchall()

        week_ago = (
            datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(days=7)
        ).strftime("%Y-%m-%d %H:%M:%S")

        tab_ov, tab_us, tab_ac, tab_an = st.tabs([
            "📊 Overview", "👥 Users", "🧾 Activity", "📢 Announcements"
        ])

        # ======================= OVERVIEW =======================
        with tab_ov:
            c1, c2, c3 = st.columns(3)
            stat_card(c1, "👥", "Total Users", len(rows))
            stat_card(c2, "✅", "Active Accounts",
                      sum(1 for r in rows if r[4] != 0))
            stat_card(c3, "🚫", "Suspended",
                      sum(1 for r in rows if r[4] == 0))

            st.markdown("<br>", unsafe_allow_html=True)

            c4, c5, c6 = st.columns(3)
            stat_card(c4, "🛡️", "Admins", sum(1 for r in rows if r[2]))
            stat_card(c5, "🆕", "New (7 days)",
                      sum(1 for r in rows if r[3] and r[3] >= week_ago))
            stat_card(c6, "🔒", "Locked Keys", locked)

            st.markdown("<br>", unsafe_allow_html=True)

            st.subheader("Sign-ins vs failed attempts (14 days)")
            today = datetime.datetime.now(datetime.timezone.utc).date()
            days = [today - datetime.timedelta(days=i) for i in range(13, -1, -1)]
            ok_map = {d: n for d, e, n in trend if e == "Signed in"}
            bad_map = {d: n for d, e, n in trend if e == "Failed sign-in"}

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=[d.strftime("%d %b") for d in days],
                y=[ok_map.get(d.isoformat(), 0) for d in days],
                name="Sign-ins",
                marker_color=COLORS["accent"],
                marker_line_color=COLORS["border"],
                marker_line_width=2
            ))
            fig.add_trace(go.Bar(
                x=[d.strftime("%d %b") for d in days],
                y=[bad_map.get(d.isoformat(), 0) for d in days],
                name="Failed",
                marker_color=COLORS["danger"],
                marker_line_color=COLORS["border"],
                marker_line_width=2
            ))
            fig.update_layout(
                barmode="group",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font={"color": COLORS["text_main"], "family": "Inter"},
                height=320,
                margin=dict(l=10, r=10, t=10, b=10),
                legend=dict(orientation="h", y=1.12)
            )
            st.plotly_chart(fig, use_container_width=True)

            joined = pd.Series([r[3][:10] for r in rows if r[3]])
            if not joined.empty:
                st.subheader("Signups per day")
                st.bar_chart(joined.value_counts().sort_index())

        # ========================= USERS ========================
        with tab_us:
            f1, f2 = st.columns([2, 1])
            q = f1.text_input(
                "Search users", placeholder="Name or email"
            ).lower().strip()
            role_f = f2.selectbox(
                "Filter", ["All", "Admins", "Users", "Suspended"]
            )

            def keep(r):
                if q and q not in r[0].lower() and q not in r[1]:
                    return False
                if role_f == "Admins":
                    return bool(r[2])
                if role_f == "Users":
                    return not r[2]
                if role_f == "Suspended":
                    return r[4] == 0
                return True

            users_df = pd.DataFrame(
                [
                    {
                        "Username": r[0],
                        "Email": r[1],
                        "Role": "Admin" if r[2] else "User",
                        "Status": "Suspended" if r[4] == 0 else "Active",
                        "Joined (UTC)": r[3],
                        "Last sign-in (UTC)": r[5]
                    }
                    for r in rows if keep(r)
                ],
                columns=["Username", "Email", "Role", "Status",
                         "Joined (UTC)", "Last sign-in (UTC)"]
            )
            st.dataframe(users_df, use_container_width=True, hide_index=True)

            st.download_button(
                "⬇ Export users CSV",
                data=users_df.to_csv(index=False).encode(),
                file_name="users.csv",
                mime="text/csv"
            )

            st.markdown("---")
            st.subheader("Manage a user")

            others = [r for r in rows if r[1] != email]

            if not others:
                st.info("No other users to manage yet.")
            else:
                target = st.selectbox("Select user", [r[1] for r in others])
                t = next(r for r in others if r[1] == target)
                t_active = t[4] != 0

                a, b, c = st.columns(3)

                if a.button("Remove admin" if t[2] else "Make admin"):
                    with get_db() as conn:
                        conn.execute(
                            "UPDATE users SET is_admin = ? WHERE email = ?",
                            (0 if t[2] else 1, target)
                        )
                    log_event(target, "Role changed by admin")
                    st.rerun()

                if b.button("Suspend" if t_active else "Activate"):
                    with get_db() as conn:
                        conn.execute(
                            "UPDATE users SET is_active = ? WHERE email = ?",
                            (0 if t_active else 1, target)
                        )
                    log_event(
                        target,
                        "Suspended by admin" if t_active
                        else "Activated by admin"
                    )
                    st.rerun()

                if c.button("Unlock account"):
                    with get_db() as conn:
                        for p in ("login", "reset", "chg", "otpsend",
                                  "sec", "del"):
                            conn.execute(
                                "DELETE FROM attempts WHERE key = ?",
                                (f"{p}:{target}",)
                            )
                    st.success("✅ Account unlocked.")

                st.markdown("<br>", unsafe_allow_html=True)

                tmp = st.text_input(
                    "Set a temporary password for this user",
                    type="password",
                    key="admin_tmp_pwd"
                )
                show_strength(tmp)

                if st.button("Set temporary password"):
                    if password_error(tmp):
                        st.error(f"⚠️ {password_error(tmp)}")
                    else:
                        with get_db() as conn:
                            conn.execute(
                                "UPDATE users SET password_hash = ? "
                                "WHERE email = ?",
                                (hash_txt(tmp), target)
                            )
                        clear_fails(f"login:{target}")
                        log_event(target, "Password set by admin")
                        st.success(
                            "✅ Password updated. Share it with the user "
                            "securely and ask them to change it."
                        )

                st.markdown("<br>", unsafe_allow_html=True)

                confirm = st.checkbox(f"Confirm deleting {target}")
                if st.button("Delete user", disabled=not confirm):
                    with get_db() as conn:
                        for tbl in ("users", "activity", "notes"):
                            conn.execute(
                                f"DELETE FROM {tbl} WHERE email = ?", (target,)
                            )
                    st.rerun()

        # ======================= ACTIVITY =======================
        with tab_ac:
            g1, g2, g3 = st.columns([2, 2, 1])
            sel = g1.multiselect("Event types", event_types)
            qa = g2.text_input(
                "Email contains", placeholder="user@example.com"
            ).lower().strip()
            limit = g3.selectbox("Rows", [50, 100, 500])

            sql = "SELECT email, event, ts FROM activity WHERE 1 = 1"
            params = []
            if sel:
                sql += " AND event IN (%s)" % ",".join("?" * len(sel))
                params += sel
            if qa:
                sql += " AND email LIKE ?"
                params.append(f"%{qa}%")
            sql += " ORDER BY id DESC LIMIT ?"
            params.append(limit)

            with get_db() as conn:
                logs = conn.execute(sql, params).fetchall()

            logs_df = pd.DataFrame(logs, columns=["Email", "Event", "Time (UTC)"])
            st.dataframe(logs_df, use_container_width=True, hide_index=True)

            st.download_button(
                "⬇ Export activity CSV",
                data=logs_df.to_csv(index=False).encode(),
                file_name="activity_log.csv",
                mime="text/csv"
            )

        # ===================== ANNOUNCEMENTS ====================
        with tab_an:
            st.caption("Announcements appear at the top of every user's dashboard.")

            with st.form("ann_form", clear_on_submit=True):
                msg = st.text_area("New announcement", max_chars=300)
                posted = st.form_submit_button("Post announcement →")

            if posted:
                if not msg.strip():
                    st.error("⚠️ Please write a message.")
                else:
                    with get_db() as conn:
                        conn.execute(
                            "INSERT INTO announcements (message) VALUES (?)",
                            (msg.strip(),)
                        )
                    st.rerun()

            st.subheader("Posted announcements")
            if not announcements:
                st.caption("Nothing posted yet.")
            for aid, amsg, ats in announcements:
                col_m, col_b = st.columns([5, 1])
                col_m.info(f"{amsg}\n\n*{ats[:16]} UTC*")
                if col_b.button("Delete", key=f"ann_del_{aid}"):
                    with get_db() as conn:
                        conn.execute(
                            "DELETE FROM announcements WHERE id = ?", (aid,)
                        )
                    st.rerun()

    # ========================================================
    # REGULAR USER: ANALYTICS
    # ========================================================
    elif menu == "Analytics":
        dash_header("Analytics", "👤")

        st.caption("Sample data for demonstration.")

        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        searches = [32, 45, 38, 52, 47, 21, 18]
        documents = [110, 114, 119, 121, 126, 127, 128]

        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=days,
                y=searches,
                name="Searches",
                marker_color=COLORS["accent"],
                marker_line_color=COLORS["border"],
                marker_line_width=2
            )
        )
        fig.add_trace(
            go.Scatter(
                x=days,
                y=documents,
                name="Documents indexed",
                mode="lines+markers",
                line=dict(color=COLORS["text_heading"], width=3),
                yaxis="y2"
            )
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"color": COLORS["text_main"], "family": "Inter"},
            height=400,
            margin=dict(l=10, r=10, t=30, b=10),
            legend=dict(orientation="h", y=1.1),
            yaxis=dict(title="Searches"),
            yaxis2=dict(
                title="Documents",
                overlaying="y",
                side="right",
                showgrid=False
            )
        )

        st.plotly_chart(fig, use_container_width=True)

    # ========================================================
    # REGULAR USER: REPORTS
    # ========================================================
    elif menu == "Reports":
        dash_header("Reports", "👤")

        st.caption("Sample data for demonstration.")

        report_df = pd.DataFrame(
            {
                "Date": [
                    "2026-10-13", "2026-10-14", "2026-10-15",
                    "2026-10-16", "2026-10-17", "2026-10-18",
                    "2026-10-19"
                ],
                "Searches": [32, 45, 38, 52, 47, 21, 18],
                "Documents indexed": [110, 114, 119, 121, 126, 127, 128],
                "Efficiency (%)": [96.8, 97.2, 97.9, 98.1, 98.4, 98.2, 98.4]
            }
        )

        st.dataframe(report_df, use_container_width=True, hide_index=True)

        st.markdown("<br>", unsafe_allow_html=True)

        st.download_button(
            "⬇ Download CSV",
            data=report_df.to_csv(index=False).encode(),
            file_name="weekly_report.csv",
            mime="text/csv"
        )

    # ========================================================
    # REGULAR USER: DASHBOARD
    # ========================================================
    else:
        dash_header("User Dashboard", "👤")

        with get_db() as conn:
            created, phone, bio = conn.execute(
                "SELECT created_at, phone, bio FROM users WHERE email = ?",
                (email,)
            ).fetchone()
            logins = conn.execute(
                "SELECT COUNT(*) FROM activity "
                "WHERE email = ? AND event = 'Signed in'", (email,)
            ).fetchone()[0]
            fails = conn.execute(
                "SELECT COUNT(*) FROM activity "
                "WHERE email = ? AND event = 'Failed sign-in'", (email,)
            ).fetchone()[0]
            recent = conn.execute(
                "SELECT event, ts FROM activity WHERE email = ? "
                "ORDER BY id DESC LIMIT 8", (email,)
            ).fetchall()
            daily = dict(conn.execute(
                "SELECT substr(ts, 1, 10), COUNT(*) FROM activity "
                "WHERE email = ? AND event = 'Signed in' "
                "AND ts >= date('now', '-6 days') GROUP BY 1", (email,)
            ).fetchall())
            anns = conn.execute(
                "SELECT message, ts FROM announcements "
                "ORDER BY id DESC LIMIT 3"
            ).fetchall()
            notes = conn.execute(
                "SELECT id, text, ts FROM notes WHERE email = ? "
                "ORDER BY id DESC", (email,)
            ).fetchall()

        for amsg, ats in anns:
            st.info(f"📢 {amsg}\n\n*{ats[:10]}*")

        today = datetime.datetime.now(datetime.timezone.utc).date()
        member_days = (
            (today - datetime.date.fromisoformat(created[:10])).days
            if created else 0
        )
        mins_left = max(0, int((payload["exp"] - time.time()) // 60))

        c1, c2, c3, c4 = st.columns(4)
        stat_card(c1, "🔑", "Total Sign-ins", logins)
        stat_card(c2, "⚠️", "Failed Attempts", fails)
        stat_card(c3, "📅", "Member For", f"{member_days} days")
        stat_card(c4, "⏳", "Session Left", f"{mins_left} min")

        st.markdown("<br>", unsafe_allow_html=True)

        tab_ov, tab_notes = st.tabs(["📊 Overview", "📝 My Notes"])

        # ======================= OVERVIEW =======================
        with tab_ov:
            checks = [
                ("Strong password enforced", True),
                ("Security question set", True),
                ("Email OTP recovery available", smtp_configured()),
                ("No failed sign-ins", fails == 0),
                ("Profile completed (phone and bio)",
                 bool((phone or "").strip() and (bio or "").strip())),
            ]
            health = int(100 * sum(1 for _, ok in checks if ok) / len(checks))

            left, right = st.columns([1.6, 1])

            with left:
                st.subheader("Sign-ins (last 7 days)")
                days = [today - datetime.timedelta(days=i) for i in range(6, -1, -1)]
                fig = go.Figure(
                    go.Bar(
                        x=[d.strftime("%a") for d in days],
                        y=[daily.get(d.isoformat(), 0) for d in days],
                        marker_color=COLORS["accent"],
                        marker_line_color=COLORS["border"],
                        marker_line_width=2
                    )
                )
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font={"color": COLORS["text_main"], "family": "Inter"},
                    height=280,
                    margin=dict(l=10, r=10, t=10, b=10)
                )
                st.plotly_chart(fig, use_container_width=True)

            with right:
                st.subheader("Account health")
                gauge = go.Figure(
                    go.Indicator(
                        mode="gauge+number",
                        value=health,
                        number={"suffix": "%"},
                        gauge={
                            "axis": {"range": [0, 100]},
                            "bar": {"color": COLORS["accent"]},
                            "bgcolor": COLORS["bg_card_alt"],
                            "borderwidth": 1,
                            "bordercolor": COLORS["border"]
                        }
                    )
                )
                gauge.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    font={"color": COLORS["text_main"], "family": "Inter"},
                    height=200,
                    margin=dict(l=10, r=10, t=10, b=10)
                )
                st.plotly_chart(gauge, use_container_width=True)

                for label, ok in checks:
                    st.markdown(f"{'✅' if ok else '⚠️'} {label}")

            st.subheader("Recent activity")
            if recent:
                st.dataframe(
                    pd.DataFrame(recent, columns=["Event", "Time (UTC)"]),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.caption("No activity yet.")

        # ========================= NOTES ========================
        with tab_notes:
            with st.form("note_form", clear_on_submit=True):
                new_note = st.text_input(
                    "Add a note", max_chars=200,
                    placeholder="Write something to remember..."
                )
                added = st.form_submit_button("Add note →")

            if added:
                if new_note.strip():
                    with get_db() as conn:
                        conn.execute(
                            "INSERT INTO notes (email, text) VALUES (?, ?)",
                            (email, new_note.strip())
                        )
                    st.rerun()
                else:
                    st.error("⚠️ Please write a note first.")

            if not notes:
                st.caption("No notes yet.")

            for nid, ntext, nts in notes:
                col_n, col_d = st.columns([6, 1])
                col_n.text(f"{ntext}\n({nts[:16]} UTC)")
                if col_d.button("Delete", key=f"note_del_{nid}"):
                    with get_db() as conn:
                        conn.execute(
                            "DELETE FROM notes WHERE id = ? AND email = ?",
                            (nid, email)
                        )
                    st.rerun()
  
