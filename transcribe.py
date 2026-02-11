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
    """Sends the prompt to Gemini."""
    model = genai.GenerativeModel("gemini-2.0-flash") # Updated to the model that worked for you!
    
    prompt = """
    You are a professional session drummer creating a 'cheat sheet'.
    Listen to the audio and extract the song structure.
    
    RULES:
    1. Ignore lyrics. Focus on drums/structure.
    2. Identify sections (Intro, Verse, Chorus, Bridge, Solo).
    3. Count bars (e.g., "8x", "16x").
    4. Describe 'Feel' in 2-4 words (e.g., 'Tom Groove', 'Half-time').
    5. Note hits/stops.
    
    OUTPUT JSON ONLY:
    [
        {"section": "Intro", "bars": "4x", "feel": "Tom Groove", "notes": "Build"},
        {"section": "Verse 1", "bars": "8x", "feel": "Closed HH", "notes": ""}
    ]
    """
    
    response = model.generate_content(
        [file, prompt],
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