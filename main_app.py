import streamlit as st
import pandas as pd
import sqlite3
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import io
import time
from scipy.io import wavfile

# --- ۱. مدیریت دیتابیس ---
DB_NAME = 'thesis_final_v10.db'

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

# --- ۲. تولید موسیقی پیانویی پیشرفته ---
def generate_complex_piano(v, a):
    sr = 44100
    duration = 20.0
    t = np.linspace(0, duration, int(sr * duration))
    
    # آکوردهای پیچیده (Major 7th vs Minor 9th)
    if v > 0.5:
        notes = [261.63, 329.63, 392.00, 493.88, 523.25] # Cmaj7
    else:
        notes = [110.00, 220.00, 261.63, 311.13, 349.23] # Amin9
    
    audio = np.zeros_like(t)
    interval = 0.6 if a > 0.6 else 2.5 
    
    for start in np.arange(0, duration, interval):
        idx = int(start * sr)
        for i, f in enumerate(notes):
            n_len = int(interval * sr * 2.5)
            if idx + n_len < len(t):
                chunk = np.linspace(0, interval * 2.5, n_len)
                env = np.exp(-3.5 * chunk)
                harmonic = np.sin(2 * np.pi * f * chunk) + 0.3 * np.sin(2 * np.pi * 2 * f * chunk)
                audio[idx:idx+n_len] += harmonic * env * (0.8 ** i)
    
    audio = (audio / (np.max(np.abs(audio)) + 1e-9) * 0.8 * 32767).astype(np.int16)
    byte_io = io.BytesIO()
    wavfile.write(byte_io, sr, audio)
    return byte_io

# --- ۳. رابط کاربری و سایدبار ---
st.set_page_config(page_title="Affective Mediation Framework", layout="wide")
init_db()

# زمان‌سنج برای محاسبه Dwell Time
if "music_start_time" not in st.session_state:
    st.session_state.music_start_time = None

# --- سایدبار برای تنظیمات مدیریتی ---
st.sidebar.header("Admin Controls")
if st.sidebar.button("🗑 Reset Database (Clear Table)"):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM interactions")
    conn.commit()
    conn.close()
    st.sidebar.success("تمام داده‌ها پاک شدند!")
    st.rerun() # بازنشانی صفحه برای نمایش جدول خالی

st.title("🎹 Hybrid Emotional Mediation Interface")

personal_library = {
    "Calm": "1SToozs1JPW2ft6yNUFvs30Qf-PNdgw6q",
    "Sad": "1Z6sHysLQs8TblMpfrwO4IAWNJEt8Wk3R",
    "Happy": "1Lw1MYHlFHxDYNaMyp7YywGj1JaiEP5po",
    "Tense": "1KlwK6rNDuDzKbv77c21g25-MlUU5-32d"
}

user_text = st.text_area("How are you feeling?", 
                         placeholder="مثلاً: امروز حس خیلی خوب و آرامی دارم...",
                         height=100)

if st.button("Generate & Mediate"):
    if user_text:
        # محاسبه Dwell Time (زمان ماندگاری روی قطعه قبلی)
        dwell = 0
        if st.session_state.music_start_time:
            dwell = round(time.time() - st.session_state.music_start_time, 2)
        
        st.session_state.music_start_time = time.time()
        
        # منطق VAD
        v = max(0.1, min(0.9, 0.5 + (len(user_text) % 10 - 5) / 10))
        a = max(0.1, min(0.9, 0.4 + (len(user_text) % 7 - 3) / 10))
        
        low_text = user_text.lower()
        if any(w in low_text for w in ["happy", "شاد", "عالی"]): v, a = 0.9, 0.8
        elif any(w in low_text for w in ["sad", "غم", "گریه"]): v, a = 0.1, 0.2
        elif any(w in low_text for w in ["calm", "آرام", "خوب"]): v, a = 0.8, 0.2
        elif any(w in low_text for w in ["tense", "استرس", "فشار"]): v, a = 0.2, 0.9

        mood = "Happy" if v >= 0.5 and a >= 0.5 else "Calm" if v >= 0.5 else "Tense" if a >= 0.5 else "Sad"
        
        # ثبت در دیتابیس
        log_interaction(user_text, v, a, mood, dwell=dwell, dl="No")

        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🤖 AI Piano (Generative)")
            st.audio(generate_complex_piano(v, a), format="audio/wav")
        
        with c2:
            st.subheader("👤 Human Curation")
            dl_url = f"https://docs.google.com/uc?export=download&id={personal_library[mood]}"
            st.link_button(f"📥 Download {mood} Track", dl_url)
            
            if st.button("Confirm Download ✅"):
                log_interaction("User Feedback", v, a, mood, dwell=0, dl="Yes")
                st.success("Download recorded in CSV!")

        # رسم نمودار VAD
        fig = go.Figure(go.Scatter(x=[v], y=[a], mode='markers+text', text=[mood], marker=dict(size=25, color='orange')))
        fig.update_layout(xaxis=dict(title="Valence", range=[0,1]), yaxis=dict(title="Arousal", range=[0,1]), height=350)
        st.plotly_chart(fig)

# --- ۴. نمایش گزارش زنده و خروجی CSV ---
st.markdown("---")
st.subheader("📋 Research Data (English Report)")
try:
    conn = sqlite3.connect(DB_NAME)
    df_full = pd.read_sql_query("SELECT * FROM interactions ORDER BY id DESC", conn)
    
    # نمایش در صفحه (بدون ستون دانلود برای زیبایی)
    st.table(df_full.drop(columns=['downloaded']).head(5))
    
    if not df_full.empty:
        csv = df_full.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export FULL CSV Report", csv, "research_results.csv", "text/csv")
    conn.close()
except:
    st.write("داده‌ای ثبت نشده است.")
