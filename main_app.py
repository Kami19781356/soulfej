import streamlit as st
import pandas as pd
import sqlite3
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import io
import time
from scipy.io import wavfile

# --- 1. Database Engine ---
DB_NAME = 'thesis_final_v8.db'

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
                  downloaded TEXT)''')
    conn.commit()
    conn.close()

def log_interaction(text, v, a, intent, dwell=0, dl="No"):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO interactions (timestamp, user_input, valence, arousal, intent, dwell_time_sec, downloaded) VALUES (?,?,?,?,?,?,?)",
              (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), text, v, a, intent, dwell, dl))
    conn.commit()
    conn.close()

# --- 2. Piano Audio Synthesis ---
def generate_piano_20s(v, a):
    sr = 44100
    duration = 20.0
    t = np.linspace(0, duration, int(sr * duration))
    if v > 0.5:
        notes = [261.63, 329.63, 392.00, 523.25] if a > 0.5 else [329.63, 415.30, 493.88]
    else:
        notes = [220.00, 261.63, 329.63] if a < 0.5 else [196.00, 233.08, 293.66]
    
    audio = np.zeros_like(t)
    interval = 0.8 if a > 0.5 else 2.0
    for start in np.arange(0, duration, interval):
        idx = int(start * sr)
        for f in notes:
            n_len = int(interval * sr * 2)
            if idx + n_len < len(t):
                chunk = np.linspace(0, interval * 2, n_len)
                env = np.exp(-4 * chunk)
                audio[idx:idx+n_len] += np.sin(2 * np.pi * f * chunk) * env
    
    audio = (audio / (np.max(np.abs(audio)) + 1e-9) * 0.7 * 32767).astype(np.int16)
    byte_io = io.BytesIO()
    wavfile.write(byte_io, sr, audio)
    return byte_io

# --- 3. App Core ---
st.set_page_config(page_title="Affective Mediation Framework", layout="wide")
init_db()

# Session State for Timing
if "music_start_time" not in st.session_state:
    st.session_state.music_start_time = None
if "last_v" not in st.session_state:
    st.session_state.last_v, st.session_state.last_a, st.session_state.last_mood = 0.5, 0.5, "Neutral"

st.title("🎹 Hybrid Emotional Mediation Interface")

# Sidebar Controls
st.sidebar.header("Admin")
if st.sidebar.button("🗑 Reset Data"):
    conn = sqlite3.connect(DB_NAME)
    conn.cursor().execute("DELETE FROM interactions")
    conn.commit()
    conn.close()
    st.sidebar.success("Cleared!")

personal_library = {
    "Calm": "1SToozs1JPW2ft6yNUFvs30Qf-PNdgw6q",
    "Sad": "1Z6sHysLQs8TblMpfrwO4IAWNJEt8Wk3R",
    "Happy": "1Lw1MYHlFHxDYNaMyp7YywGj1JaiEP5po",
    "Tense": "1KlwK6rNDuDzKbv77c21g25-MlUU5-32d"
}

# Text Box with Placeholder
user_text = st.text_area("How are you feeling?", 
                         placeholder="e.g., I feel very peaceful and relaxed today...",
                         height=100)

if st.button("Generate & Play"):
    if user_text:
        # Calculate how long they listened to the PREVIOUS track
        dwell = 0
        if st.session_state.music_start_time:
            dwell = round(time.time() - st.session_state.music_start_time, 2)
        
        # Start timing for the NEW track
        st.session_state.music_start_time = time.time()
        
        # VAD Logic
        v = max(0.1, min(0.9, 0.5 + (len(user_text) % 10 - 5) / 10))
        a = max(0.1, min(0.9, 0.4 + (len(user_text) % 7 - 3) / 10))
        
        low_text = user_text.lower()
        if any(w in low_text for w in ["happy", "شاد"]): v, a = 0.85, 0.75
        elif any(w in low_text for w in ["sad", "غم"]): v, a = 0.15, 0.25
        elif any(w in low_text for w in ["calm", "آرام"]): v, a = 0.80, 0.15
        elif any(w in low_text for w in ["tense", "استرس"]): v, a = 0.20, 0.85

        mood = "Happy" if v >= 0.5 and a >= 0.5 else "Calm" if v >= 0.5 else "Tense" if a >= 0.5 else "Sad"
        st.session_state.last_v, st.session_state.last_a, st.session_state.last_mood = v, a, mood
        
        # Log this interaction
        log_interaction(user_text, v, a, mood, dwell=dwell, dl="No")

        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🤖 AI Piano (20s)")
            st.audio(generate_piano_20s(v, a), format="audio/wav")
        with c2:
            st.subheader("👤 Human Curation")
            dl_url = f"https://docs.google.com/uc?export=download&id={personal_library[mood]}"
            st.markdown(f"**[📥 Download {mood} Track]({dl_url})**")
            if st.button("Mark as Downloaded ✅"):
                log_interaction("Manual Download Confirm", v, a, mood, dwell=0, dl="Yes")
                st.balloons()

        # Chart
        fig = go.Figure(go.Scatter(x=[v], y=[a], mode='markers+text', text=[mood], marker=dict(size=25, color='orange')))
        fig.update_layout(xaxis=dict(title="Valence", range=[0,1]), yaxis=dict(title="Arousal", range=[0,1]), height=350)
        st.plotly_chart(fig)

# --- 4. Reporting ---
st.markdown("---")
st.subheader("📋 Interaction Table (Live View)")
try:
    conn = sqlite3.connect(DB_NAME)
    # On screen we show everything EXCEPT 'downloaded' to keep it clean
    df_display = pd.read_sql_query("SELECT timestamp, user_input, valence, arousal, intent, dwell_time_sec FROM interactions ORDER BY id DESC", conn)
    st.table(df_display.head(5))
    
    # In CSV we provide the FULL data including download status
    df_full = pd.read_sql_query("SELECT * FROM interactions ORDER BY id DESC", conn)
    if not df_full.empty:
        csv = df_full.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export Research Report (Full CSV)", csv, "thesis_results.csv", "text/csv")
    conn.close()
except:
    st.write("No data.")
