import streamlit as st
import pandas as pd
import sqlite3
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import io
import time
from scipy.io import wavfile

# --- 1. Database Configuration ---
DB_NAME = 'phd_thesis_final.db'

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
                  satisfaction_download TEXT)''')
    conn.commit()
    conn.close()

def log_interaction(text, v, a, intent, dwell=0, satisfaction="N/A"):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO interactions (timestamp, user_input, valence, arousal, intent, dwell_time_sec, satisfaction_download) VALUES (?,?,?,?,?,?,?)",
              (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), text, v, a, intent, dwell, satisfaction))
    conn.commit()
    conn.close()

# --- 2. Enhanced MIDI-Style Piano Synthesis ---
def generate_pro_piano(v, a):
    sr = 44100
    duration = 20.0
    t = np.linspace(0, duration, int(sr * duration))
    if v > 0.5:
        base_notes = [261.63, 329.63, 392.00, 493.88, 587.33] # C Maj 9
    else:
        base_notes = [174.61, 207.65, 261.63, 311.13, 349.23] # F Min 11
    audio = np.zeros_like(t)
    note_speed = 0.18 if a > 0.6 else 0.45
    for i in range(int(duration / note_speed)):
        start_idx = int(i * note_speed * sr)
        freq = base_notes[i % len(base_notes)]
        if v < 0.5 and i % 4 == 0: freq /= 2
        n_len = int(sr * 2.5) 
        if start_idx + n_len < len(t):
            time_chunk = np.linspace(0, 2.5, n_len)
            envelope = np.exp(-3.5 * time_chunk)
            note = (np.sin(2 * np.pi * freq * time_chunk) + 0.3 * np.sin(2 * np.pi * 2 * freq * time_chunk)) * envelope
            audio[start_idx:start_idx+n_len] += note * 0.4
    audio = (audio / (np.max(np.abs(audio)) + 1e-9) * 0.8 * 32767).astype(np.int16)
    byte_io = io.BytesIO()
    wavfile.write(byte_io, sr, audio)
    return byte_io

# --- 3. UI logic ---
st.set_page_config(page_title="PhD Thesis - Emotional Mediation", layout="wide")
init_db()

# Session States
if "last_play_time" not in st.session_state: st.session_state.last_play_time = None
if "prev_mood" not in st.session_state: st.session_state.prev_mood = None

# Sidebar
st.sidebar.title("🎓 PhD Thesis Controls")
if st.sidebar.button("🗑 Reset Research Database"):
    conn = sqlite3.connect(DB_NAME)
    conn.cursor().execute("DELETE FROM interactions")
    conn.commit()
    conn.close()
    st.sidebar.success("Database Reset Successful!")
    st.rerun()

st.title("🎼 Emotional Mediation Framework for Personalized Music Synthesis")
st.markdown("### *PhD Research Project - Interactive Human-AI Affective Loop*")

personal_library = {
    "Calm": "1SToozs1JPW2ft6yNUFvs30Qf-PNdgw6q",
    "Sad": "1Z6sHysLQs8TblMpfrwO4IAWNJEt8Wk3R",
    "Happy": "1Lw1MYHlFHxDYNaMyp7YywGj1JaiEP5po",
    "Tense": "1KlwK6rNDuDzKbv77c21g25-MlUU5-32d"
}

# --- بخش نظرسنجی مرحله قبلی ---
if st.session_state.prev_mood:
    st.info(f"Reflecting on the previous **{st.session_state.prev_mood}** session:")
    satisfied = st.radio("Were you satisfied with the previous download/track?", ["Yes", "No", "N/A"], index=2, horizontal=True)
    if st.button("Submit Feedback"):
        conn = sqlite3.connect(DB_NAME)
        conn.cursor().execute("UPDATE interactions SET satisfaction_download = ? WHERE id = (SELECT MAX(id) FROM interactions)", (satisfied,))
        conn.commit()
        conn.close()
        st.success("Feedback recorded for the previous session!")

st.markdown("---")
user_text = st.text_area("Express your current emotional state:", placeholder="e.g., I feel a sense of deep calm and serenity...", height=100)

if st.button("Execute Framework & Synthesize"):
    if user_text:
        # ۱. محاسبه زمان (Dwell Time)
        dwell = 0
        if st.session_state.last_play_time:
            dwell = round(time.time() - st.session_state.last_play_time, 2)
        st.session_state.last_play_time = time.time()
        
        # ۲. منطق VAD
        v = max(0.1, min(0.9, 0.5 + (len(user_text) % 10 - 5) / 10))
        a = max(0.1, min(0.9, 0.4 + (len(user_text) % 7 - 3) / 10))
        
        low_t = user_text.lower()
        if any(w in low_t for w in ["happy", "شاد"]): v, a = 0.9, 0.8
        elif any(w in low_t for w in ["sad", "غم"]): v, a = 0.15, 0.2
        
        mood = "Happy" if v >= 0.5 and a >= 0.5 else "Calm" if v >= 0.5 else "Tense" if a >= 0.5 else "Sad"
        st.session_state.prev_mood = mood
        
        # ۳. لاگ اولیه
        log_interaction(user_text, v, a, mood, dwell=dwell)

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🤖 AI Generative Synthesis")
            st.audio(generate_pro_piano(v, a), format="audio/wav")
        with c2:
            st.subheader("👤 Human Artist Reference")
            dl_url = f"https://docs.google.com/uc?export=download&id={personal_library[mood]}"
            st.markdown(f"**[📥 Download {mood} Composition]({dl_url})**")
            st.audio(dl_url) # پلیر مستقیم

        # Visualization
        fig = go.Figure(go.Scatter(x=[v], y=[a], mode='markers+text', text=[mood], marker=dict(size=25, color='orange')))
        fig.update_layout(xaxis=dict(title="Valence", range=[0,1]), yaxis=dict(title="Arousal", range=[0,1]), height=350)
        st.plotly_chart(fig)

# --- 4. Report ---
st.markdown("---")
st.subheader("📊 Experimental Data Logs (PhD Research Report)")
try:
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM interactions ORDER BY id DESC", conn)
    st.table(df.head(5))
    if not df.empty:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export Research CSV", csv, "phd_research_results.csv", "text/csv")
    conn.close()
except:
    st.write("No data recorded.")
