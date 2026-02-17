import streamlit as st
import pandas as pd
import sqlite3
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import io
from scipy.io import wavfile

# --- ۱. مدیریت دیتابیس و ذخیره گزارش ---
def log_to_db(text, v, a, intent):
    try:
        conn = sqlite3.connect('thesis_final_v5.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS interactions 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT, input TEXT, v REAL, a REAL, intent TEXT)''')
        c.execute("INSERT INTO interactions (time, input, v, a, intent) VALUES (?, ?, ?, ?, ?)",
                  (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), text, v, a, intent))
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Database Error: {e}")

# --- ۲. تولید موسیقی جنریتیو ۲۰ ثانیه‌ای با هارمونی متغیر ---
def generate_advanced_audio_20s(valence, arousal):
    sr = 44100
    duration = 20.0  # ۲۰ ثانیه
    t = np.linspace(0, duration, int(sr * duration))
    
    # تعیین گام بر اساس والانس
    if valence > 0.5:
        base_freqs = [261.63, 329.63, 392.00]  # C Major
    else:
        base_freqs = [261.63, 311.13, 392.00]  # C Minor
    
    tempo = 1 + (arousal * 4)
    audio_signal = np.zeros_like(t)
    
    # ایجاد تغییرات در نت‌ها در طول ۲۰ ثانیه (Arpeggio)
    for i in range(len(base_freqs)):
        # نوسان فرکانس برای اینکه موسیقی زنده به نظر برسد
        freq_mod = base_freqs[i] * (1 + 0.005 * np.sin(2 * np.pi * 0.5 * t))
        # پاکت صوتی ریتمیک
        envelope = np.abs(np.sin(2 * np.pi * (tempo / (i+1)) * t))
        audio_signal += envelope * np.sin(2 * np.pi * freq_mod * t)
    
    # نرمالایز و تبدیل به ۱۶ بیت
    audio_signal = (audio_signal / np.max(np.abs(audio_signal)) * 0.8 * 32767).astype(np.int16)
    
    byte_io = io.BytesIO()
    wavfile.write(byte_io, sr, audio_signal)
    return byte_io

# --- ۳. کتابخانه موسیقی اصلاح شده (آیدی‌های شما) ---
personal_library = {
    "Calm": "1SToozs1JPW2ft6yNUFvs30Qf-PNdgw6q",
    "Sad": "1Z6sHysLQs8TblMpfrwO4IAWNJEt8Wk3R",
    "Happy": "1Lw1MYHlFHxDYNaMyp7YywGj1JaiEP5po",
    "Tense": "1KlwK6rNDuDzKbv77c21g25-MlUU5-32d"
}

# --- ۴. رابط کاربری (UI) ---
st.set_page_config(page_title="Multimodal Mediation Framework v5", layout="wide")
st.title("🎼 Unified Emotional Mediation System")
st.markdown("---")

user_input = st.text_area("ورودی متنی یا توصیف وضعیت عاطفی:", placeholder="بنویسید...")

if st.button("تحلیل و تولید خروجی"):
    if user_input:
        # لایه میانجی (مدل ساده شده برای شبیه‌سازی تراژکتوری)
        v = max(0.1, min(0.9, 0.5 + (len(user_input) % 10 - 5) / 10))
        a = max(0.1, min(0.9, 0.4 + (len(user_input) % 7 - 3) / 10))
        
        if v > 0.5: mood = "Happy" if a > 0.5 else "Calm"
        else: mood = "Tense" if a > 0.5 else "Sad"
        
        log_to_db(user_input, v, a, mood)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🤖 موسیقی جنریتیو (۲۰ ثانیه)")
            audio_gen = generate_advanced_audio_20s(v, a)
            st.audio(audio_gen, format="audio/wav")
            st.write(f"Generated Pattern: {mood} Harmonic Path")

        with col2:
            st.subheader("👤 موسیقی پیشنهادی (کیوریتور انسانی)")
            file_id = personal_library[mood]
            # لینک دانلود مستقیم
            dl_link = f"https://docs.google.com/uc?export=download&id={file_id}"
            st.markdown(f"**[📥 دانلود موسیقی انتخابی ({mood})]({dl_link})**")
            st.info("این قطعه بر اساس انطباق عاطفی با ورودی شما از آرشیو انتخاب شده است.")

        # نمودار فضای VAD
        fig = go.Figure(go.Scatter(x=[v], y=[a], mode='markers+text', text=[mood], marker=dict(size=25, color='orange')))
        fig.update_layout(xaxis=dict(title="Valence", range=[0,1]), yaxis=dict(title="Arousal", range=[0,1]))
        st.plotly_chart(fig)

# --- ۵. بخش گزارش‌گیری برای استاد (CSV Export) ---
st.markdown("---")
st.subheader("📑 گزارش تعاملات و نتایج تجربی")

try:
    conn = sqlite3.connect('thesis_final_v5.db')
    df = pd.read_sql_query("SELECT * FROM interactions ORDER BY id DESC", conn)
    st.dataframe(df)
    
    if not df.empty:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 ذخیره ریپورت نهایی (CSV) برای ارائه به استاد",
            data=csv,
            file_name=f'emotion_report_{datetime.now().strftime("%Y%m%d")}.csv',
            mime='text/csv',
        )
    conn.close()
except:
    st.write("هنوز تعاملی ثبت نشده است.")
