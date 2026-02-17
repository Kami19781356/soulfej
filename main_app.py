import streamlit as st
import pandas as pd
import sqlite3
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import io
import time
import base64
from scipy.io import wavfile

# --- 1. Database Configuration ---
DB_NAME = 'phd_kamran_final.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS interactions 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  timestamp TEXT, 
                  user_input TEXT, 
                  valence REAL, 
                  arousal REAL, 
                  intent TEXT, 
                  dwell_time_sec REAL, 
                  satisfaction TEXT)''')
    conn.commit()
    conn.close()

def log_interaction(text, v, a, intent, dwell=0, sat="N/A"):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO interactions (timestamp, user_input, valence, arousal, intent, dwell_time_sec, satisfaction) VALUES (?,?,?,?,?,?,?)",
              (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), text, v, a, intent, dwell, sat))
    conn.commit()
    conn.close()

# --- 2. Piano Synthesis ---
def generate_advanced_piano(v, a, intensity_multiplier=1.0):
    sr = 44100
    duration = 20.0
    t = np.linspace(0, duration, int(sr * duration))
    if v > 0.5:
        base_notes = [261.63, 329.63, 392.00, 493.88] 
    else:
        base_notes = [130.81, 155.56, 196.00, 233.08] if intensity_multiplier > 1.2 else [174.61, 207.65, 261.63, 311.13]
    audio = np.zeros_like(t)
    note_speed = max(0.1, 0.5 - (a * 0.4 * intensity_multiplier))
    for i in range(int(duration / note_speed)):
        start_idx = int(i * note_speed * sr)
        freq = base_notes[i % len(base_notes)]
        n_len = int(sr * 2.0) 
        if start_idx + n_len < len(t):
            time_chunk = np.linspace(0, 2.0, n_len)
            envelope = np.exp(-4.0 * time_chunk)
            note = np.sin(2 * np.pi * freq * time_chunk) * envelope
            audio[start_idx:start_idx+n_len] += note * 0.5
    audio = (audio / (np.max(np.abs(audio)) + 1e-9) * 0.8 * 32767).astype(np.int16)
    byte_io = io.BytesIO()
    wavfile.write(byte_io, sr, audio)
    return byte_io

# تابع کمکی برای ایجاد پلیر با قابلیت Autoplay
def st_autoplay(audio_bytes):
    b64 = base64.b64encode(audio_bytes.read()).decode()
    md = f"""
        <audio controls autoplay="true">
        <source src="data:audio/wav;base64,{b64}" type="audio/wav">
        </audio>
    """
    st.markdown(md, unsafe_allow_html=True)

# --- 3. UI Logic ---
st.set_page_config(page_title="PhD Thesis - Kamran Rasoolzadeh", layout="wide")
init_db()

if "last_click_time" not in st.session_state:
    st.session_state.last_click_time = None

st.sidebar.title("🎓 Admin Panel")
st.sidebar.info("Researcher: Kamran Rasoolzadeh")
if st.sidebar.button("🗑 Reset Database"):
    conn = sqlite3.connect(DB_NAME)
    conn.cursor().execute("DELETE FROM interactions")
    conn.commit()
    conn.close()
    st.sidebar.success("Database Cleared!")
    st.rerun()

st.title("🎹 Multimodal Emotional Mediation Framework")
st.markdown("### PhD Researcher: **Kamran Rasoolzadeh**")

st.sidebar.markdown("---")
st.sidebar.subheader("Feedback Loop")
sat_input = st.sidebar.selectbox("Music Accuracy:", ["N/A", "Yes - Accurate", "No - Inaccurate"])
if st.sidebar.button("Save Feedback"):
    conn = sqlite3.connect(DB_NAME)
    conn.cursor().execute("UPDATE interactions SET satisfaction = ? WHERE id = (SELECT MAX(id) FROM interactions)", (sat_input,))
    conn.commit()
    conn.close()
    st.sidebar.success("Recorded.")

user_text = st.text_area("How are you feeling?", placeholder="e.g., I am very sad...", height=100)

if st.button("Analyze & Mediate"):
    if user_text:
        current_now = time.time()
        
        # محاسبه زمان دقیق از لحظه کلیک قبلی (بر حسب ثانیه)
        if st.session_state.last_click_time is None:
            actual_dwell = 0.0
        else:
            actual_dwell = round(current_now - st.session_state.last_click_time, 2)
        
        st.session_state.last_click_time = current_now 
        
        intensity = 1.5 if any(word in user_text.lower() for word in ["very", "extremely", "خیلی", "بسیار"]) else 1.0
        v = max(0.1, min(0.9, 0.5 + (len(user_text) % 10 - 5) / 10))
        a = max(0.1, min(0.9, 0.4 + (len(user_text) % 7 - 3) / 10))
        
        low_t = user_text.lower()
        if "happy" in low_t or "شاد" in low_t: 
            v, a = (0.95, 0.8) if intensity > 1.2 else (0.8, 0.7)
        elif "sad" in low_t or "غم" in low_t:
            v, a = (0.1, 0.2) if intensity > 1.2 else (0.3, 0.2)

        mood = "Happy" if v >= 0.5 and a >= 0.5 else "Calm" if v >= 0.5 else "Tense" if a >= 0.5 else "Sad"
        
        log_interaction(user_text, v, a, mood, dwell=actual_dwell)

        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🤖 AI Generative Output (Autoplay)")
            audio_data = generate_advanced_piano(v, a, intensity)
            st_autoplay(audio_data) # استفاده از پلیر اتوپلی
        
        with c2:
            st.subheader("👤 Human Artist Selection")
            drive_id = {"Happy":"1Lw1MYHlFHxDYNaMyp7YywGj1JaiEP5po", "Calm":"1SToozs1JPW2ft6yNUFvs30Qf-PNdgw6q", 
                        "Sad":"1Z6sHysLQs8TblMpfrwO4IAWNJEt8Wk3R", "Tense":"1KlwK6rNDuDzKbv77c21g25-MlUU5-32d"}
            dl_url = f"https://docs.google.com/uc?export=download&id={drive_id[mood]}"
            st.markdown(f"**[📥 Download Composition]({dl_url})**")
            st.audio(dl_url)

        fig = go.Figure(go.Scatter(x=[v], y=[a], mode='markers+text', text=[f"{mood}"], marker=dict(size=25, color='orange')))
        fig.update_layout(xaxis=dict(title="Valence", range=[0,1]), yaxis=dict(title="Arousal", range=[0,1]), height=350)
        st.plotly_chart(fig)

st.markdown("---")
st.subheader("📊 Research Logs (Experimental Data)")
try:
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM interactions ORDER BY id DESC", conn)
    st.table(df.head(5))
    if not df.empty:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export Final CSV Report", csv, "phd_results_kamran.csv", "text/csv")
    conn.close()
except:
    st.write("No entries.")
