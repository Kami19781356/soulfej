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
DB_NAME = 'thesis_final_v12.db'

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

# --- 2. Advanced MIDI-like Piano Synthesis ---
def generate_pro_piano(v, a):
    sr = 44100
    duration = 20.0
    t = np.linspace(0, duration, int(sr * duration))
    
    # Chords: Major 9th (Happy) vs Minor 11th (Sad)
    if v > 0.5:
        base_notes = [261.63, 329.63, 392.00, 493.88, 587.33] # C Maj 9
    else:
        base_notes = [174.61, 207.65, 261.63, 311.13, 349.23] # F Min 11
    
    audio = np.zeros_like(t)
    note_speed = 0.18 if a > 0.6 else 0.45
    
    for i in range(int(duration / note_speed)):
        start_idx = int(i * note_speed * sr)
        freq = base_notes[i % len(base_notes)]
        if v < 0.5 and i % 4 == 0: freq /= 2 # Deep Bass for Sadness
        
        n_len = int(sr * 2.5) 
        if start_idx + n_len < len(t):
            time_chunk = np.linspace(0, 2.5, n_len)
            # Piano ADSR Envelope Simulation
            envelope = np.exp(-3.5 * time_chunk)
            note = (np.sin(2 * np.pi * freq * time_chunk) + 
                    0.3 * np.sin(2 * np.pi * 2 * freq * time_chunk) +
                    0.1 * np.sin(2 * np.pi * 3 * freq * time_chunk)) * envelope
            audio[start_idx:start_idx+n_len] += note * 0.4

    audio = (audio / (np.max(np.abs(audio)) + 1e-9) * 0.8 * 32767).astype(np.int16)
    byte_io = io.BytesIO()
    wavfile.write(byte_io, sr, audio)
    return byte_io

# --- 3. UI logic ---
st.set_page_config(page_title="Affective Mediation Pro", layout="wide")
init_db()

# Session States
if "play_start_time" not in st.session_state: st.session_state.play_start_time = None
if "current_mood" not in st.session_state: st.session_state.current_mood = "Neutral"

# Sidebar Reset
if st.sidebar.button("🗑 Reset All Data"):
    conn = sqlite3.connect(DB_NAME)
    conn.cursor().execute("DELETE FROM interactions")
    conn.commit()
    conn.close()
    st.sidebar.success("Database Cleared!")
    st.rerun()

st.title("🎼 Advanced Emotional Mediation Dashboard")

personal_library = {
    "Calm": "1SToozs1JPW2ft6yNUFvs30Qf-PNdgw6q",
    "Sad": "1Z6sHysLQs8TblMpfrwO4IAWNJEt8Wk3R",
    "Happy": "1Lw1MYHlFHxDYPaMyp7YywGj1JaiEP5po",
    "Tense": "1KlwK6rNDuDzKbv77c21g25-MlUU5-32d"
}

user_text = st.text_area("How are you feeling?", placeholder="Example: I feel very peaceful and calm...", height=100)

if st.button("Generate & Play"):
    if user_text:
        # ۱. محاسبه زمان ماندگاری از لحظه Play قبلی
        dwell = 0
        if st.session_state.play_start_time:
            dwell = round(time.time() - st.session_state.play_start_time, 2)
        
        st.session_state.play_start_time = time.time() # شروع تایمر جدید
        
        # ۲. منطق تحلیل حس (VAD)
        v = max(0.1, min(0.9, 0.5 + (len(user_text) % 10 - 5) / 10))
        a = max(0.1, min(0.9, 0.4 + (len(user_text) % 7 - 3) / 10))
        
        low_t = user_text.lower()
        if any(w in low_t for w in ["happy", "شاد"]): v, a = 0.9, 0.8
        elif any(w in low_t for w in ["sad", "غم"]): v, a = 0.15, 0.2
        elif any(w in low_t for w in ["tense", "استرس"]): v, a = 0.2, 0.9
        
        st.session_state.current_mood = "Happy" if v >= 0.5 and a >= 0.5 else "Calm" if v >= 0.5 else "Tense" if a >= 0.5 else "Sad"
        
        # ۳. ثبت در دیتابیس
        log_interaction(user_text, v, a, st.session_state.current_mood, dwell=dwell, dl="No")

        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🤖 Generative Piano (MIDI-Style)")
            st.audio(generate_pro_piano(v, a), format="audio/wav")
            st.info("Direct synthesized output based on VAD trajectory.")

        with col2:
            st.subheader("👤 Human Artist Player (Drive)")
            file_id = personal_library[st.session_state.current_mood]
            # پلیر مستقیم فایل گوگل درایو
            drive_url = f"https://docs.google.com/uc?export=open&id={file_id}"
            st.audio(drive_url) 
            
            if st.button("Confirm Download/Engagement ✅"):
                conn = sqlite3.connect(DB_NAME)
                conn.cursor().execute("UPDATE interactions SET downloaded = 'Yes' WHERE id = (SELECT MAX(id) FROM interactions)")
                conn.commit()
                conn.close()
                st.success("Interaction recorded as 'Downloaded' in CSV!")

        # Visualization
        fig = go.Figure(go.Scatter(x=[v], y=[a], mode='markers+text', text=[st.session_state.current_mood], marker=dict(size=25, color='orange')))
        fig.update_layout(xaxis=dict(title="Valence", range=[0,1]), yaxis=dict(title="Arousal", range=[0,1]), height=350)
        st.plotly_chart(fig)

# --- 4. Live Data & Export ---
st.markdown("---")
st.subheader("📊 Research Logs & CSV Report")
try:
    conn = sqlite3.connect(DB_NAME)
    df_full = pd.read_sql_query("SELECT * FROM interactions ORDER BY id DESC", conn)
    
    # نمایش در جدول صفحه (فقط ستون‌های مهم)
    st.table(df_full[['timestamp', 'user_input', 'intent', 'dwell_time_sec']].head(5))
    
    if not df_full.empty:
        csv_data = df_full.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Final Research CSV", csv_data, "research_results.csv", "text/csv")
    conn.close()
except:
    st.write("No interactions yet.")
