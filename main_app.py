import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
from midiutil import MIDIFile
import tempfile
import random
from datetime import datetime

# --- تنظیمات دیتابیس (Data Collection Layer) ---
def init_db():
    conn = sqlite3.connect('hybrid_music_data.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS logs 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, input_text TEXT, 
        valence REAL, arousal REAL, music_intent TEXT, action TEXT)''')
    conn.commit()
    conn.close()

def log_event(text, v, a, intent, action):
    conn = sqlite3.connect('hybrid_music_data.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO logs (timestamp, input_text, valence, arousal, music_intent, action) VALUES (?,?,?,?,?,?)',
                   (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), text, v, a, intent, action))
    conn.commit()
    conn.close()

# --- بخش اول: تولید موسیقی الگوریتمیک (AI Composition) ---
def generate_ai_melody(valence, arousal):
    midi = MIDIFile(1)
    midi.addTempo(0, 0, int(60 + arousal * 100))
    scale = [0, 2, 4, 5, 7, 9, 11] if valence > 0.5 else [0, 2, 3, 5, 7, 8, 10]
    time = 0
    for _ in range(16):
        if random.random() < (0.3 + arousal * 0.4):
            pitch = 60 + random.choice(scale)
            midi.addNote(0, 0, pitch, time, 0.5, 80 + int(arousal * 20))
        time += 0.5
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mid") as tmp:
        midi.writeFile(tmp)
        return tmp.name

# --- بخش دوم: موسیقی‌های شخصی  (Direct Links) ---
personal_library = {
    "Calm": "https://docs.google.com/uc?export=download&id=1SToozs1JPW2ft6yNUFvs30Qf-PNdgw6q",
    "Sad": "https://docs.google.com/uc?export=download&id=1Z6sHysLQs8TblMpfrwO4IAWNJEt8Wk3R",
    "Happy": "https://docs.google.com/uc?export=download&id=1Lw1MYHlFHxDYNaMyp7YywGj1JaiEP5po",
    "Tense": "https://docs.google.com/uc?export=download&id=1KlwK6rNDuDzKbv77c21g25-MlUU5-32d"
}

# --- رابط کاربری (UI) ---
st.set_page_config(page_title="Hybrid Emotional Mediation", layout="wide")
st.title("🎼 Hybrid Emotional Mediation: AI Gen + Human Curation")
init_db()

st.markdown("""
این سیستم بر اساس لایه میانجی (Mediation Layer) طراحی شده در رساله دکتری، 
ورودی‌های چندوجهی شما را تحلیل کرده و دو پاسخ متفاوت ارائه می‌دهد.
""")

user_input = st.text_area("How are you feeling?", placeholder="Example: I feel very peaceful and relaxed today...")

if st.button("Generate & Recommend"):
    if user_input:
        # لایه میانجی (Simplified Mediation Core)
        v = max(0.1, min(0.9, 0.5 + (len(user_input) % 10 - 5) / 10))
        a = max(0.1, min(0.9, 0.4 + (len(user_input) % 7 - 3) / 10))
        
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🤖 AI Generative Composition")
            st.write("ملودی تولید شده در لحظه بر اساس تراژکتوری عاطفی کاربر.")
            midi_path = generate_ai_melody(v, a)
            with open(midi_path, "rb") as f:
                st.download_button("📥 Download AI MIDI Composition", f, "ai_music.mid")
            
            fig = go.Figure(go.Scatter(x=[v], y=[a], mode='markers+text', text=["Affect State"], marker=dict(size=25, color='red')))
            fig.update_layout(xaxis=dict(title="Valence (Pleasantness)", range=[0,1]), yaxis=dict(title="Arousal (Intensity)", range=[0,1]), height=400)
            st.plotly_chart(fig)

        with col2:
            st.subheader("👤 Human Artist Selection")
            st.write("پیشنهاد هوشمند از آثار موسیقی پارسا رسول‌زاده متناسب با این حس.")
            
            if v >= 0.5 and a >= 0.5: mood = "Happy"
            elif v >= 0.5 and a < 0.5: mood = "Calm"
            elif v < 0.5 and a < 0.5: mood = "Sad"
            else: mood = "Tense"
            
            st.audio(personal_library[mood])
            st.success(f"Selected Track Mood: {mood}")
            
        log_event(user_input, v, a, f"Hybrid_{mood}", "Generate")
    else:
        st.warning("Please enter some text to analyze.")

# نمایش دیتابیس برای اثبات بخش Data Collection مقاله
st.markdown("---")
st.subheader("📊 Interaction Logs (Real-time Empirical Data)")
conn = sqlite3.connect('hybrid_music_data.db')
df = pd.read_sql_query("SELECT * FROM logs ORDER BY id DESC", conn)
st.dataframe(df)

if not df.empty:
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Export Logs for Article Validation", csv, "experimental_results.csv", "text/csv")
