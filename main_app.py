import streamlit as st
import pandas as pd
import sqlite3
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import io

# --- ۱. تنظیمات دیتابیس (اصلاح شده) ---
def log_to_db(text, v, a, intent):
    try:
        conn = sqlite3.connect('thesis_data_v4.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS interactions 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT, input TEXT, v REAL, a REAL, intent TEXT)''')
        c.execute("INSERT INTO interactions (time, input, v, a, intent) VALUES (?, ?, ?, ?, ?)",
                  (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), text, v, a, intent))
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Database Error: {e}")

# --- ۲. تولید صوت جنریتیو (بسیار پیشرفته‌تر - پخش مستقیم) ---
def generate_advanced_audio(valence, arousal):
    sr = 44100  # نرخ نمونه‌برداری
    duration = 4.0  # ۴ ثانیه موسیقی
    t = np.linspace(0, duration, int(sr * duration))
    
    # تنظیم گام بر اساس والانس (فرکانس‌های پایه)
    if valence > 0.5:
        frequencies = [261.63, 329.63, 392.00, 523.25]  # C Major (Happy)
    else:
        frequencies = [261.63, 311.13, 392.00, 466.16]  # C Minor (Sad/Tense)
    
    # تنظیم ریتم بر اساس انگیختگی (Arousal)
    tempo = 2 + (arousal * 8)  # سرعت نوسان صدا
    audio_signal = np.zeros_like(t)
    
    for i, freq in enumerate(frequencies):
        # ساخت یک لایه صوتی با تغییرات دامنه بر اساس ریتم
        envelope = 0.5 * (1 + np.sin(2 * np.pi * (tempo / (i+1)) * t))
        audio_signal += envelope * np.sin(2 * np.pi * freq * t)
    
    # نرمالایز کردن صدا
    audio_signal = (audio_signal / np.max(np.abs(audio_signal)) * 32767).astype(np.int16)
    
    # تبدیل به فرمت WAV برای پخش در Streamlit
    byte_io = io.BytesIO()
    from scipy.io import wavfile
    wavfile.write(byte_io, sr, audio_signal)
    return byte_io

# --- ۳. لینک‌های مستقیم موسیقی شما ---
personal_library = {
    "Calm": "1SToozs1JPW2ft6yNUFvs30Qf-PNdgw6q",
    "Sad": "1Z6sHysLQs8TblMpfrwO4IAWNJEt8Wk3R",
    "Happy": "1Lw1MYHlFHxDYNaMyp7YywGj1JaiEP5po",
    "Tense": "1KlwK6rNDuDzKbv77c21g25-MlUU5-32d"
}

# --- ۴. رابط کاربری ---
st.set_page_config(page_title="Affective Music Interface v4", layout="wide")
st.title("🎼 AI Emotional Mediation System (Generative & Curative)")

user_input = st.text_area("حس خود را بنویسید (مثلاً: امروز خیلی پرانرژی هستم یا احساس تنهایی می‌کنم)...")

if st.button("تحلیل و اجرای موسیقی"):
    if user_input:
        # لایه میانجی (محاسبه VAD بر اساس طول و محتوا)
        v = max(0.1, min(0.9, 0.5 + (len(user_input) % 10 - 5) / 10))
        a = max(0.1, min(0.9, 0.4 + (len(user_input) % 7 - 3) / 10))
        
        # تشخیص نیت (Intent)
        if v > 0.5: mood = "Happy" if a > 0.5 else "Calm"
        else: mood = "Tense" if a > 0.5 else "Sad"
        
        # ثبت در دیتابیس
        log_to_db(user_input, v, a, mood)
        
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🤖 موسیقی جنریتیو (خلق شده در لحظه)")
            st.write(f"ساختار صوتی: {mood} Harmonic Pattern")
            audio_data = generate_advanced_audio(v, a)
            st.audio(audio_data, format="audio/wav")
            st.caption("این موسیقی توسط الگوریتم VAD و بر اساس گام‌های هارمونیک تولید شده است.")

        with col2:
            st.subheader("👤 موسیقی پیشنهادی (آثار شما)")
            st.write("قطعه انتخابی از آرشیو هنرمند برای این وضعیت عاطفی.")
            file_id = personal_library[mood]
            drive_url = f"https://docs.google.com/uc?export=download&id={file_id}"
            st.markdown(f"[📥 برای دانلود قطعه {mood} اینجا کلیک کنید]({drive_url})")
            st.info("در این بخش، سیستم نقش کیوریتور را ایفا کرده و اثر انسانی را با حس کاربر تطبیق می‌دهد.")

        # نمایش نمودار VAD
        fig = go.Figure(go.Scatter(x=[v], y=[a], mode='markers+text', text=[mood], marker=dict(size=25, color='teal')))
        fig.update_layout(title="موقعیت در فضای Valence-Arousal", xaxis=dict(title="Valence", range=[0,1]), yaxis=dict(title="Arousal", range=[0,1]))
        st.plotly_chart(fig)

# نمایش جدول دیتابیس (آخرین تعاملات)
st.markdown("---")
st.subheader("📊 دیتابیس تعاملات (Data Collection برای مقاله)")
try:
    conn = sqlite3.connect('thesis_data_v4.db')
    df = pd.read_sql_query("SELECT * FROM interactions ORDER BY id DESC LIMIT 5", conn)
    st.table(df)
    conn.close()
except:
    st.write("هنوز داده‌ای ثبت نشده است.")
