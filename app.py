import streamlit as st
import asyncio
import os
from video_engine import generate_final_video

st.set_page_config(page_title="Premium Video Engine", page_icon="🎥", layout="centered")

# Visual Polish via Custom Minimalist CSS 
st.markdown("""
    <style>
    h1 { color: #ff4b4b; }
    .stButton>button { background-color: #ff4b4b; color: white; border-radius: 6px; font-weight: bold; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

st.title("🎥 AI Premium Video Studio")
st.caption("Your internal asset generation framework for automated faceless video campaigns.")
st.divider()

# API Key inputs — clean, secure, and customizable
gemini_key = st.text_input("Enter Gemini API Key", type="password")
pexels_key = st.text_input("Enter Pexels API Key", type="password")

st.subheader("🎬 Video Parameters")
topic = st.text_input("Video Topic Prompt", placeholder="e.g., Why constraints breed massive creativity")
voice_selection = st.selectbox(
    "Choose Narration Persona",
    [
        "En-US-Christopher (Deep Professional Male)", 
        "En-US-Emma (Clear Fluent Female)"
    ]
)

# Convert selection option strings to Edge-TTS voice keys
voice_id = "en-US-ChristopherNeural" if "Christopher" in voice_selection else "en-US-EmmaNeural"

if st.button("Generate Master Asset Video 🚀"):
    if not gemini_key or not pexels_key or not topic:
        st.error("Please fill out all API Keys and the Target Topic prompt!")
    else:
        with st.status("🛠️ Studio processing master track arrays...", expanded=True) as status:
            try:
                # Trigger the rendering orchestrator
                output_file = asyncio.run(generate_final_video(topic, gemini_key, pexels_key, voice_id))
                
                if output_file and os.path.exists(output_file):
                    status.update(label="✅ Master Asset Render Completed!", state="complete")
                    st.success("Your video has compiled successfully.")
                    
                    # Display the final output video inside the UI panel
                    with open(output_file, "rb") as f:
                        st.video(f.read())
                    
                    # File downloader attachment
                    with open(output_file, "rb") as file:
                        st.download_button(
                            label="📥 Download High-Quality MP4",
                            data=file,
                            file_name="ai_studio_render.mp4",
                            mime="video/mp4"
                        )
                else:
                    status.update(label="❌ Generation Failure", state="error")
                    st.error("The system was unable to safely export valid file binaries.")
            except Exception as global_error:
                status.update(label="❌ System Exception Intercepted", state="error")
                st.error(f"Error: {global_error}")
