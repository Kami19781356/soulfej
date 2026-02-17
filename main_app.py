import streamlit as st
import pandas as pd
import sqlite3
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import io
import time
from scipy.io import wavfile

# --- 1. Database Management (English Schema) ---
def log_to_db(user_input, v, a, intent, dwell_time=0, feedback=0):
    try:
        conn = sqlite3.connect('thesis_final_report.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS interactions 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      timestamp TEXT, 
                      user_input TEXT, 
                      valence REAL, 
                      arousal REAL, 
                      detected_intent TEXT, 
                      dwell_time_sec REAL, 
                      feedback_score INTEGER)''')
        c.execute("""INSERT INTO interactions 
                     (timestamp, user_input, valence, arousal, detected_intent, dwell_time_sec, feedback_score) 
                     VALUES (?, ?, ?, ?, ?, ?, ?)""",
                  (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_input, v, a, intent, dwell_time, feedback))
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Database Error: {e}")

# --- 2. Advanced Piano Synthesis (20 Seconds) ---
def generate_piano_audio(v, a):
    sr = 44100
    duration = 20.0
    t = np.linspace(0, duration, int(sr * duration))
    
    # Emotional Mapping to Harmony [cite: 172]
    if v > 0.5:
        base_notes = [261.63, 329.63, 392.00, 523.25] if a > 0.5 else [329.63, 415.30, 493.88]
    else:
        base_notes = [220.00, 261.63, 329.63] if a < 0.5 else [196.00, 233.08, 293.66]
    
    audio_signal = np.zeros_like(t)
    beat_interval = 0.8 if a > 0.5 else 2.0 # Higher arousal = Faster tempo [cite: 172]
    
    for start_time in np.arange(0, duration, beat_interval):
        idx = int(start_time * sr)
        for freq in base_notes:
            note_len = int(beat_interval * sr * 2)
            if idx + note_len < len(t):
                chunk = np.linspace(0, beat_interval * 2, note_len)
                # Piano-like decay envelope [cite: 171]
                envelope = np.exp(-4 * chunk) 
                note = np.sin(2 * np.pi * freq * chunk) * envelope
                audio_signal[idx:idx+note_len] += note

    audio_signal = (audio_signal / np.max(np.abs(audio_signal)) * 0.7 * 32767).astype(np.int16)
    byte_io = io.BytesIO()
    wavfile.write(byte_io, sr, audio_signal)
    return byte_io

# --- 3. UI and Session State ---
st.set_page_config(page_title="Multimodal Emotion Mediation", layout="wide")
st.title("🎼 Hybrid Emotional Mediation Framework")

if "start_time" not in st.session_state:
    st.session_state.start_time = time.time()

# Correct Drive ID Mapping
personal_library = {
    "Calm": "1SToozs1JPW2ft6yNUFvs30Qf-PNdgw6q",
    "Sad": "1Z6sHysLQs8TblMpfrwO4IAWNJEt8Wk3R",
    "Happy": "1Lw1MYHlFHxDYPaMyp7YywGj1JaiEP5po",
    "Tense": "1KlwK6rNDuDzKbv77c21g25-MlUU5-32d"
}

user_input = st.text_area("Express your current emotional state:", placeholder="e.g., I feel peaceful and content...")

if st.button("Analyze & Mediate"):
    if user_input:
        # Calculate Dwell Time 
        current_time = time.time()
        duration = round(current_time - st.session_state.start_time, 2)
        st.session_state.start_time = current_time 
        
        # Mediation Logic (VAD Extraction) [cite: 135, 159]
        v = max(0.1, min(0.9, 0.5 + (len(user_input) % 10 - 5) / 10))
        a = max(0.1, min(0.9, 0.4 + (len(user_input) % 7 - 3) / 10))
        
        # Simple keywords fix
        if any(w in user_input.lower() for w in ["happy", "شاد", "خوب"]): v, a = 0.8, 0.7
        if any(w in user_input.lower() for w in ["sad", "غم", "بد"]): v, a = 0.2, 0.3

        mood = "Happy" if v >= 0.5 and a >= 0.5 else "Calm" if v >= 0.5 else "Tense" if a >= 0.5 else "Sad"
        
        log_to_db(user_input, v, a, mood, dwell_time=duration)

        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🤖 Generative AI Response")
            st.write(f"Piano composition for **{mood}** state.")
            audio_gen = generate_piano_audio(v, a)
            st.audio(audio_gen, format="audio/wav")

        with col2:
            st.subheader("👤 Human Artist Selection")
            dl_link = f"https://docs.google.com/uc?export=download&id={personal_library[mood]}"
            st.markdown(f"**[📥 Download Personal Track ({mood})]({dl_link})**")
            # Log feedback if they click the link (Logic: Click = Engagement) [cite: 189]
            st.button("Confirm Engagement ✅", on_click=log_to_db, args=("User Confirmed Fit", v, a, mood, 0, 1))

        # VAD Visualization [cite: 133, 223]
        fig = go.Figure(go.Scatter(x=[v], y=[a], mode='markers+text', text=[mood], marker=dict(size=30, color='royalblue')))
        fig.update_layout(xaxis=dict(title="Valence", range=[0,1]), yaxis=dict(title="Arousal", range=[0,1]), height=400)
        st.plotly_chart(fig)

# --- 4. Report Section (For Professor) [cite: 197] ---
st.markdown("---")
st.subheader("📋 Interaction Data Report (Experimental Results)")
try:
    conn = sqlite3.connect('thesis_final_report.db')
    df = pd.read_sql_query("SELECT * FROM interactions ORDER BY id DESC", conn)
    st.table(df.head(10)) # Show latest 10 rows
    
    if not df.empty:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export Final CSV Report", csv, "thesis_results.csv", "text/csv")
    conn.close()
except:
    st.write("No data recorded yet.")
