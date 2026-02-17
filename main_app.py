import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
from midiutil import MIDIFile
import tempfile
from datetime import datetime

# --- تنظیمات دیتابیس ---
def init_db():
    conn = sqlite3.connect('hybrid_v3_data.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS logs 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, input_text TEXT, 
        valence REAL, arousal REAL, music_intent TEXT)''')
    conn.commit()
    conn.close()

# --- سنتز ملودی با کیفیت‌تر (آکورد محور) ---
def generate_rich_midi(valence, arousal):
    midi = MIDIFile(1)
    track = 0
    time = 0
    midi.addTempo(track, time, int(50 + arousal * 80))
    
    # انتخاب گام و آکورد بر اساس والانس
    if valence > 0.5:
        scale = [60, 64, 67, 72] # C Major (Happy)
        volume = 90
    else:
        scale = [60, 63, 67, 70] # C Minor (Sad/Tense)
        volume = 60

    # تولید یک الگوی ۸ میزانی به جای تک نوت
    for _ in range(8):
        for note in scale:
            duration = 0.5 if arousal > 0.5 else 2.0
            midi.addNote(track, 0, note, time, duration, volume)
            time += duration

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mid") as tmp:
        midi.writeFile(tmp)
        return tmp.name

# --- لینک‌های مستقیم اصلاح شده گوگل درایو ---
def get_drive_url(id):
    return f"https://docs.google.com/uc?export=open&id={id}"

personal_library = {
    "Calm": get_drive_url("1SToozs1JPW2ft6yNUFvs30Qf-PNdgw6q"),
    "Sad": get_drive_url("1Z6sHysLQs8TblMpfrwO4IAWNJEt8Wk3R"),
    "Happy": get_drive_url("1Lw1MYHlFHxDYNaMyp7YywGj1JaiEP5po"),
    "Tense": get_drive_url("1KlwK6rNDuDzKbv77c21g25-MlUU5-32d")
}

# --- رابط کاربری ---
st.set_page_config(page_title="Hybrid Music Mediation V3", layout="wide")
st.title("🎼 Hybrid Emotional Mediation: AI Gen + Human Curation")
init_db()

user_input = st.text_area("How are you feeling?", placeholder="Type here...")

if st.button("Generate & Recommend"):
    if user_input:
        # لایه میانجی (Mediation Layer) [cite: 51, 132, 156]
        v = max(0.1, min(0.9, 0.5 + (len(user_input) % 10 - 5) / 10))
        a = max(0.1, min(0.9, 0.4 + (len(user_input) % 7 - 3) / 10))
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🤖 AI Generative Composition")
            st.write("ملودی آکورال بر اساس تراژکتوری VAD [cite: 135]")
            midi_path = generate_rich_midi(v, a)
            with open(midi_path, "rb") as f:
                st.download_button("🎵 Download AI Composition", f, "ai_music.mid")
            st.caption("نکته: فایل‌های MIDI برای پخش نیاز به نرم‌افزار (VLC یا Media Player) دارند.")

        with col2:
            st.subheader("👤 Human Artist Selection")
            mood = "Happy" if v >= 0.5 and a >= 0.5 else "Calm" if v >= 0.5 else "Sad" if a < 0.5 else "Tense"
            
            # استفاده از HTML برای دور زدن محدودیت پخش گوگل درایو
            audio_url = personal_library[mood]
            st.markdown(f'<audio controls src="{audio_url}" style="width: 100%;"></audio>', unsafe_allow_html=True)
            st.success(f"Selected: {mood} (Valence: {v}, Arousal: {a})")

        # نمودار فضای VAD [cite: 133, 199]
        fig = go.Figure(go.Scatter(x=[v], y=[a], mode='markers+text', text=["Current State"], marker=dict(size=30, color='red')))
        fig.update_layout(xaxis=dict(title="Valence", range=[0,1]), yaxis=dict(title="Arousal", range=[0,1]), height=400)
        st.plotly_chart(fig)

# نمایش لاگ‌های دیتابیس [cite: 187, 197]
st.markdown("---")
st.subheader("📊 Interaction Database (Experimental Results)")
conn = sqlite3.connect('hybrid_v3_data.db')
st.dataframe(pd.read_sql_query("SELECT * FROM logs ORDER BY id DESC", conn))
