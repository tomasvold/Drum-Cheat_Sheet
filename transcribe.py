import streamlit as st
import google.generativeai as genai
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import os
import json
import time
import tempfile
from io import BytesIO

# --- PAGE CONFIG ---
st.set_page_config(page_title="AI Drum Charter", page_icon="🥁", layout="centered")

st.title("🥁 AI Drum Charter")
st.write("Upload a song, get a gig-ready cheat sheet.")

# --- SIDEBAR: API KEY ---
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Google API Key", type="password")
    if not api_key and "GOOGLE_API_KEY" in os.environ:
        api_key = os.environ["GOOGLE_API_KEY"]
    
    st.info("Get your key from [Google AI Studio](https://aistudio.google.com/)")

# --- FUNCTIONS ---
def upload_to_gemini(filepath, api_key):
    """Uploads file to Gemini."""
    genai.configure(api_key=api_key)
    file = genai.upload_file(filepath, mime_type="audio/mp3")
    return file

def wait_for_processing(file):
    """Waits for Gemini to finish processing audio."""
    with st.spinner("Gemini is listening to the track..."):
        while file.state.name == "PROCESSING":
            time.sleep(2)
            file = genai.get_file(file.name)
    return file

def analyze_audio(file):
    # SWITCH 1: Use the "Pro" model for better reasoning
    # (We use 1.5-pro because it is extremely stable for audio reasoning)
    model = genai.GenerativeModel("gemini-2.5-pro") 
    
    # SWITCH 2: The "Golden Example" (Few-Shot Prompting)
    # This teaches the AI your specific vocabulary.
    example_prompt = """
    EXAMPLE OF A PERFECT CHART:
    User Input: [Audio File]
    AI Output: 
    [
        {"section": "Intro", "bars": "4x", "feel": "Snare March (Rolls)", "notes": "Crescendo last bar"},
        {"section": "Verse 1", "bars": "8x", "feel": "Tight Hi-Hat Groove", "notes": "Rimshot on 2 & 4"},
        {"section": "Chorus 1", "bars": "8x", "feel": "Open Washy Ride", "notes": "Driving, crash on 1"},
        {"section": "Interlude", "bars": "2x", "feel": "Stop / Break", "notes": "Tacet (Silence)"},
        {"section": "Bridge", "bars": "16x", "feel": "Tom Groove (Floor)", "notes": "Build with kick"}
    ]
    """

    system_instruction = """
    You are a professional session drummer creating a gig 'cheat sheet'.
    Your goal is to listen to the audio and produce a structured road map.
    
    CRITICAL INSTRUCTIONS:
    1. **Listen for the '1'**: Count bars precisely. Do not guess standard 8-bar phrases if it's actually 9 or 7.
    2. **Identify the Groove**: Use terms like "Half-time", "Double-time", "Train beat", "Four on the floor", "Syncopated".
    3. **Notes**: Explicitly mention "Stops", "Hits", "Flams", or "No Drums".
    4. **Structure**: Break it down by musical section (Intro, V1, C1, V2, C2, Solo, Bridge, Outro).
    
    Format: Return ONLY valid JSON.
    """
    
    # Send the "System rules" + "Example" + "Actual Audio"
    response = model.generate_content(
        [system_instruction, example_prompt, "Now analyze this track and output the JSON:", file],
        generation_config={"response_mime_type": "application/json"}
    )
    return json.loads(response.text)

def create_pdf(structure_data, song_title):
    """Generates PDF in memory."""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=LETTER)
    width, height = LETTER
    
    # Header
    c.setFont("Helvetica-Bold", 24)
    c.drawString(50, height - 50, "Drum Chart")
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 70, f"Track: {song_title}")
    
    # Table Header
    y = height - 120
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "SECTION")
    c.drawString(200, y, "BARS")
    c.drawString(300, y, "FEEL / GROOVE")
    c.drawString(450, y, "NOTES")
    
    y -= 10
    c.line(50, y, width - 50, y)
    y -= 30
    
    c.setFont("Helvetica", 12)
    
    for item in structure_data:
        if y < 50:
            c.showPage()
            y = height - 50
        
        c.drawString(50, y, item.get('section', ''))
        c.drawString(200, y, str(item.get('bars', '')))
        c.drawString(300, y, item.get('feel', ''))
        
        c.setFillColor(colors.darkred)
        c.drawString(450, y, item.get('notes', ''))
        c.setFillColor(colors.black)
        
        y -= 15
        c.setStrokeColor(colors.lightgrey)
        c.line(50, y, width - 50, y)
        c.setStrokeColor(colors.black)
        y -= 25
        
    c.save()
    buffer.seek(0)
    return buffer

# --- MAIN UI ---
uploaded_file = st.file_uploader("Upload Audio (MP3/WAV)", type=["mp3", "wav", "m4a"])

if uploaded_file and api_key:
    if st.button("Generate Chart"):
        try:
            # 1. Save uploaded file temporarily (Gemini needs a path)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name

            # 2. Upload & Process
            with st.status("Processing...", expanded=True) as status:
                st.write("Uploading to Gemini...")
                g_file = upload_to_gemini(tmp_path, api_key)
                
                st.write("Listening & counting bars...")
                g_file = wait_for_processing(g_file)
                
                st.write("Generating chart...")
                structure_data = analyze_audio(g_file)
                
                status.update(label="Done!", state="complete", expanded=False)

            # 3. Show Preview
            st.subheader("Chart Preview")
            st.table(structure_data) # Shows the data nicely on the web page
            
            # 4. Create PDF Download
            pdf_bytes = create_pdf(structure_data, uploaded_file.name)
            
            st.download_button(
                label="Download PDF Chart 📄",
                data=pdf_bytes,
                file_name=f"{uploaded_file.name}_chart.pdf",
                mime="application/pdf"
            )
            
            # Cleanup temp file
            os.remove(tmp_path)

        except Exception as e:
            st.error(f"An error occurred: {e}")

elif not api_key:
    st.warning("👈 Please enter your Google API Key in the sidebar to start.")