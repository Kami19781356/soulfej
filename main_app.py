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
DB_NAME = 'thesis_final_v11.db'

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

# --- 2. Professional Piano Arpeggio Synthesis ---
def generate_pro_piano(v, a):
    sr = 44100
    duration = 20.0
    t = np.linspace(0, duration, int(sr * duration))
    
    # تعریف گام‌های غنی (Chords: Major 9th vs Minor 11th)
    if v > 0.5:
        base_notes = [261.63, 329.63, 392.00, 493.88, 587.33] # C Maj 9
    else:
        base_notes = [174.61, 207.65, 261.63, 311.13, 349.23] # F Min 11
    
    audio = np.zeros_like(t)
    # سرعت ریتم بر اساس انگیختگی
    note_speed = 0.15 if a > 0.6 else 0.4
    
    for i in range(int(duration / note_speed)):
        start_idx = int(i * note_speed * sr)
        # انتخاب نوت به صورت آرپژ (چرخشی)
        freq = base_notes[i % len(base_notes)]
        if v < 0.5 and i % 4 == 0: freq /= 2 # اضافه کردن باس برای حالت غمگین
        
        n_len = int(sr * 2.0) # طنین طولانی نوت‌ها
        if start_idx + n_len < len(t):
            time_chunk = np.linspace(0, 2.0, n_len)
            # ترکیب هارمونیک‌های پیانو + پاکت صوتی اکسپوننشیال
            envelope = np.exp(-3.0 * time_chunk)
            note = (np.sin(2 * np.pi * freq * time_chunk) + 
                    0.4 * np.sin(2 * np.pi * 2 * freq * time_chunk)) * envelope
            audio[start_idx:start_idx+n_len] += note * 0.5

    # نرمالایز نهایی
    audio = (audio / (np.max(np.abs(audio)) + 1e-9) * 0.8 * 32767).astype(np.int16)
    byte_io = io.BytesIO()
    wavfile.write(byte_io, sr, audio)
    return byte_io

# --- 3. UI logic with Session State ---
st.set_page_config(page_title="Affective Mediation v11", layout="wide")
init_db()

# مدیریت وضعیت‌ها برای جلوگیری از ریست شدن
if "start_time" not in st.session_state: st.session_state.start_time = time.time()
if "is_downloaded" not in st.session_state: st.session_state.is_downloaded = "No"

# سایدبار برای ریست
if st.sidebar.button("🗑 Reset All Data"):
    conn = sqlite3.connect(DB_NAME)
    conn.cursor().execute("DELETE FROM interactions")
    conn.commit()
    conn.close()
    st.sidebar.success("Database Cleared!")
    st.rerun()

st.title("🎹 Hybrid Emotional Mediation Interface (Pro Version)")

personal_library = {
    "Calm": "1SToozs1JPW2ft6yNUFvs30Qf-PNdgw6q",
    "Sad": "1Z6sHysLQs8TblMpfrwO4IAWNJEt8Wk3R",
    "Happy": "1Lw1MYHlFHxDYNaMyp7YywGj1JaiEP5po",
    "Tense": "1KlwK6rNDuDzKbv77c21g25-MlUU5-32d"
}

user_text = st.text_area("How are you feeling?", placeholder="Example: I feel very calm and peaceful today...", height=100)

if st.button("Generate & Play Music"):
    if user_text:
        # ۱. محاسبه زمان ماندگاری واقعی
        current_time = time.time()
        dwell = round(current_time - st.session_state.start_time, 2)
        st.session_state.start_time = current_time # ریست برای حرکت بعد
        st.session_state.is_downloaded = "No" # ریست وضعیت دانلود برای ورودی جدید
        
        # ۲. منطق VAD
        v = max(0.1, min(0.9, 0.5 + (len(user_text) % 10 - 5) / 10))
        a = max(0.1, min(0.9, 0.4 + (len(user_text) % 7 - 3) / 10))
        
        # ۳. بهبود کلمات کلیدی
        low_t = user_text.lower()
        if any(w in low_t for w in ["happy", "شاد"]): v, a = 0.9, 0.8
        elif any(w in low_t for w in ["sad", "غم"]): v, a = 0.15, 0.2
        elif any(w in low_t for w in ["tense", "استرس"]): v, a = 0.2, 0.9
        
        mood = "Happy" if v >= 0.5 and a >= 0.5 else "Calm" if v >= 0.5 else "Tense" if a >= 0.5 else "Sad"
        
        # ۴. ثبت در دیتابیس
        log_interaction(user_text, v, a, mood, dwell=dwell, dl="No")
        st.session_state.last_v, st.session_state.last_a, st.session_state.last_mood = v, a, mood

        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🤖 AI Piano Arpeggio")
            st.audio(generate_pro_piano(v, a), format="audio/wav")
        with col2:
            st.subheader("👤 Human Artist Selection")
            file_id = personal_library[mood]
            dl_url = f"https://docs.google.com/uc?export=download&id={file_id}"
            st.link_button(f"📥 Download {mood} Track", dl_url)
            
            if st.button("Confirm Download ✅"):
                st.session_state.is_downloaded = "Yes"
                # بروزرسانی آخرین ردیف با وضعیت دانلود
                conn = sqlite3.connect(DB_NAME)
                conn.cursor().execute("UPDATE interactions SET downloaded = 'Yes' WHERE id = (SELECT MAX(id) FROM interactions)")
                conn.commit()
                conn.close()
                st.success("Download Status Saved to CSV!")

        # نمودار
        fig = go.Figure(go.Scatter(x=[v], y=[a], mode='markers+text', text=[mood], marker=dict(size=25, color='orange')))
        fig.update_layout(xaxis=dict(title="Valence", range=[0,1]), yaxis=dict(title="Arousal", range=[0,1]), height=350)
        st.plotly_chart(fig)

# --- ۴. بخش گزارش‌گیری ---
st.markdown("---")
st.subheader("📊 Research Report (CSV Output)")
try:
    conn = sqlite3.connect(DB_NAME)
    # نمایش در صفحه بدون ستون دانلود برای سادگی
    df_show = pd.read_sql_query("SELECT timestamp, user_input, valence, arousal, intent, dwell_time_sec FROM interactions ORDER BY id DESC", conn)
    st.table(df_show.head(5))
    
    # خروجی کامل CSV شامل ستون دانلود
    df_full = pd.read_sql_query("SELECT * FROM interactions ORDER BY id DESC", conn)
    if not df_full.empty:
        csv_data = df_full.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export Full CSV for Professor", csv_data, "thesis_results.csv", "text/csv")
    conn.close()
except:
    st.write("No data recorded.")
