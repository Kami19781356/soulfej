import streamlit as st
import pandas as pd
import sqlite3
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import io
from scipy.io import wavfile

# --- ۱. موتور تفسیر هوشمند احساس (VAD Engine) ---
def get_vad_coordinates(text):
    text = text.lower()
    # نگاشت کلمات کلیدی برای دقت بالاتر در تفسیر
    keywords = {
        "happy": (0.8, 0.8), "شاد": (0.9, 0.7), "خوشحال": (0.8, 0.6),
        "sad": (0.2, 0.2), "غم": (0.1, 0.3), "ناراحت": (0.2, 0.3),
        "tense": (0.3, 0.8), "ترس": (0.2, 0.9), "استرس": (0.3, 0.8),
        "calm": (0.8, 0.2), "آرام": (0.9, 0.1), "صلح": (0.8, 0.2)
    }
    for word, coords in keywords.items():
        if word in text:
            return coords[0], coords[1]
    
    # اگر کلمه کلیدی نبود، از فرمول طول رشته استفاده کن (Fallback)
    v = max(0.1, min(0.9, 0.5 + (len(text) % 10 - 5) / 10))
    a = max(0.1, min(0.9, 0.4 + (len(text) % 7 - 3) / 10))
    return v, a

# --- ۲. سنتز پیانوی آکوردی (Piano-style Synthesis) ---
def generate_piano_music(v, a):
    sr = 44100
    duration = 20.0
    t = np.linspace(0, duration, int(sr * duration))
    
    # انتخاب آکوردهای پیانو (فرکانس‌های غنی‌تر)
    if v > 0.5:
        base_notes = [261.63, 329.63, 392.00, 523.25] if a > 0.5 else [329.63, 415.30, 493.88] # C Major / E Major
    else:
        base_notes = [220.00, 261.63, 329.63] if a < 0.5 else [196.00, 233.08, 293.66] # A Minor / G Minor
    
    audio_signal = np.zeros_like(t)
    
    # شبیه‌سازی ضربات پیانو (Attack-Decay)
    beat_duration = 2.0 if a < 0.5 else 0.8
    for start_time in np.arange(0, duration, beat_duration):
        start_idx = int(start_time * sr)
        # تولید آکورد در هر ضربه
        for freq in base_notes:
            note_len = int(beat_duration * sr * 2) # طنین صدا
            if start_idx + note_len < len(t):
                time_chunk = np.linspace(0, beat_duration * 2, note_len)
                # فرمول صدای پیانو (موج سینوسی + هارمونیک‌ها + افت صدا)
                piano_note = (np.sin(2 * np.pi * freq * time_chunk) + 
                             0.5 * np.sin(2 * np.pi * 2 * freq * time_chunk)) * \
                             np.exp(-3 * time_chunk)
                audio_signal[start_idx:start_idx+note_len] += piano_note

    audio_signal = (audio_signal / np.max(np.abs(audio_signal)) * 0.7 * 32767).astype(np.int16)
    byte_io = io.BytesIO()
    wavfile.write(byte_io, sr, audio_signal)
    return byte_io

# --- ۳. دیتابیس نهایی (Interaction Logging) ---
def log_to_db(text, v, a, intent):
    conn = sqlite3.connect('thesis_final_v6.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS interactions 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT, input TEXT, v REAL, a REAL, intent TEXT)''')
    c.execute("INSERT INTO interactions (time, input, v, a, intent) VALUES (?, ?, ?, ?, ?)",
              (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), text, v, a, intent))
    conn.commit()
    conn.close()

# --- ۴. رابط کاربری (Multimodal UI) ---
st.set_page_config(page_title="Multimodal AI Music Mediation", layout="wide")
st.title("🎹 Unified Emotional Mediation: Piano Gen + Human Artist")

personal_library = {
    "Calm": "1SToozs1JPW2ft6yNUFvs30Qf-PNdgw6q",
    "Sad": "1Z6sHysLQs8TblMpfrwO4IAWNJEt8Wk3R",
    "Happy": "1Lw1MYHlFHxDYNaMyp7YywGj1JaiEP5po",
    "Tense": "1KlwK6rNDuDzKbv77c21g25-MlUU5-32d"
}

user_input = st.text_area("توصیف عاطفی خود را وارد کنید:", placeholder="مانند: حس آرامش دارم یا خیلی مضطرب هستم...")

if st.button("تحلیل و اجرای فریمورک میانجی"):
    if user_input:
        v, a = get_vad_coordinates(user_input)
        
        # تشخیص دقیق مود
        if v >= 0.5: mood = "Happy" if a >= 0.5 else "Calm"
        else: mood = "Tense" if a >= 0.5 else "Sad"
        
        log_to_db(user_input, v, a, mood)
        
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🤖 Generative AI: Piano Composition")
            audio_data = generate_piano_music(v, a)
            st.audio(audio_data, format="audio/wav")
            st.caption(f"تولید ۲۰ ثانیه پیانو در گام‌های {mood} بر اساس والانس {v}")

        with col2:
            st.subheader("👤 Artist Selection: Personal Archive")
            dl_link = f"https://docs.google.com/uc?export=download&id={personal_library[mood]}"
            st.markdown(f"**[📥 دانلود موسیقی انتخابی ({mood})]({dl_link})**")
            st.success(f"انطباق با آرشیو هنرمند: {mood}")

        fig = go.Figure(go.Scatter(x=[v], y=[a], mode='markers+text', text=[f"Input: {mood}"], marker=dict(size=30, color='red')))
        fig.update_layout(title="VAD Affective Mapping", xaxis=dict(title="Valence", range=[0,1]), yaxis=dict(title="Arousal", range=[0,1]))
        st.plotly_chart(fig)

# --- بخش گزارش‌گیری نهایی (CSV) ---
st.markdown("---")
st.subheader("📋 گزارش تعاملات و نتایج تجربی (Experimental Results)")
try:
    conn = sqlite3.connect('thesis_final_v6.db')
    df = pd.read_sql_query("SELECT * FROM interactions ORDER BY id DESC", conn)
    st.dataframe(df)
    if not df.empty:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 دریافت ریپورت نهایی برای ارسال به استاد", csv, "final_interaction_report.csv", "text/csv")
    conn.close()
except:
    st.write("داده‌ای ثبت نشده است.")

if st.button("پاکسازی کامل دیتابیس"):
    conn = sqlite3.connect('thesis_final_v6.db')
    c = conn.cursor()
    c.execute("DELETE FROM interactions") # تمام ردیف‌ها را پاک می‌کند
    conn.commit()
    conn.close()
    st.success("تمام داده‌های قبلی با موفقیت پاک شدند.")
