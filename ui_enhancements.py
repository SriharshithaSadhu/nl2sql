"""
UI Enhancement Module - Custom CSS, Styling, and Modern Design
"""
import streamlit as st

def inject_custom_css():
    st.markdown("""
    <style>
    :root { --bg:#0b1220; --panel:rgba(16,24,40,0.6); --glass:rgba(17,25,40,0.35); --text:#e6f0ff; --muted:#9db2d4; --neon:#00d4ff; --neon2:#7c5cff; --accent:#18ffb2; --danger:#ff4d6d; --border:rgba(124,92,255,0.35); --glow:0 0 20px rgba(0,212,255,0.25),0 0 40px rgba(124,92,255,0.15); }
    .stApp { background: radial-gradient(1100px circle at 30% 10%, #0c1628 0%, #0b1220 40%, #070d18 100%); color: var(--text); }
    .stApp::before { content:""; position: fixed; inset: 0; background-image: url('https://images.unsplash.com/photo-1526379095098-199f08cb63e3?q=80&w=1600&auto=format&fit=crop'); background-size: cover; background-position: center; opacity: 0.12; pointer-events: none; }
    .main .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
    .app-header { background: linear-gradient(135deg, rgba(124,92,255,0.25), rgba(0,212,255,0.15)); border: 1px solid var(--border); border-radius: 18px; padding: 1.1rem 1.4rem; box-shadow: var(--glow); backdrop-filter: blur(10px); color: var(--text); }
    .app-header h1 { font-size: 2rem; font-weight: 700; margin: 0; letter-spacing: 0.5px; }
    .app-header .logo-emoji { filter: drop-shadow(0 6px 18px rgba(0,212,255,0.25)); }
    .app-header .subtitle { color: var(--muted); font-size: 0.95rem; margin-top: 0.25rem; }
    .feature-card, .query-result-card, .stat-card { background: var(--glass); border: 1px solid var(--border); border-radius: 16px; box-shadow: var(--glow); }
    .feature-card { padding: 1rem; }
    .stat-card { padding: 1rem; }
    .stat-card .stat-value { font-size: 2rem; }
    .stButton > button { background: linear-gradient(135deg, #0ea5e9, #7c5cff); color: #fff; border: 1px solid var(--border); border-radius: 12px; padding: 0.7rem 1.4rem; font-weight: 600; box-shadow: var(--glow); }
    .stButton > button:hover { filter: brightness(1.08); }
    .stTextInput input, .stTextArea textarea { background: var(--panel); color: var(--text); border: 1px solid var(--border); border-radius: 12px; }
    .stTextArea textarea { min-height: 140px; font-size: 1.05rem; }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, rgba(17,25,40,0.6), rgba(17,25,40,0.8)); border-right: 1px solid var(--border); }
    .icon-item { display:flex; align-items:center; gap:10px; padding:10px 12px; border-radius:12px; border:1px solid var(--border); backdrop-filter: blur(6px); box-shadow: var(--glow); cursor:pointer; }
    .icon-item-active { background: linear-gradient(135deg, rgba(124,92,255,0.25), rgba(0,212,255,0.15)); }
    .code-block pre { background:#0c1222 !important; border:1px solid var(--border); border-radius:12px; box-shadow: var(--glow); }
    .tri-panel { display:grid; grid-template-columns:1fr 1fr 1fr; gap:14px; }
    .panel-card { background: var(--glass); border:1px solid var(--border); border-radius:14px; padding:12px; box-shadow: var(--glow); }
    .fab { position:fixed; right:28px; bottom:28px; z-index:9999; }
    .fab .stButton>button { background: linear-gradient(135deg, #00d4ff, #7c5cff); color:#0b1220; border:none; border-radius:30px; padding:0.9rem 1.6rem; font-weight:700; box-shadow:0 8px 30px rgba(0,212,255,0.35); }
    .chat-bubble-user { background: rgba(0,212,255,0.1); border:1px solid var(--border); color:var(--text); padding:10px 12px; border-radius:14px; margin-bottom:8px; }
    .chat-bubble-assistant { background: rgba(124,92,255,0.1); border:1px solid var(--border); color:var(--text); padding:10px 12px; border-radius:14px; margin-bottom:8px; }
    #MainMenu, footer, header { visibility: hidden; }
    ::-webkit-scrollbar { width:8px; }
    ::-webkit-scrollbar-thumb { background: linear-gradient(135deg, #00d4ff, #7c5cff); border-radius:10px; }
    </style>
    """, unsafe_allow_html=True)


def render_app_header(title: str = "AskDB", subtitle: str = "AI-Powered Natural Language to SQL Assistant"):
    """Render beautiful app header with logo"""
    st.markdown(f"""
    <div class="app-header">
        <h1>
            <span class="logo-emoji">🗄️</span>
            {title}
        </h1>
        <div class="subtitle">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)


def render_stat_card(value: str, label: str):
    """Render a statistic card"""
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-value">{value}</div>
        <div class="stat-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def render_feature_card(title: str, description: str, icon: str = "✨"):
    """Render a feature card"""
    st.markdown(f"""
    <div class="feature-card">
        <h3>{icon} {title}</h3>
        <p>{description}</p>
    </div>
    """, unsafe_allow_html=True)


def render_chat_message(message: str, role: str = "user"):
    """Render a chat message"""
    st.markdown(f"""
    <div class="chat-message {role}">
        {message}
    </div>
    """, unsafe_allow_html=True)



