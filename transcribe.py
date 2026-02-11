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

from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch

def create_pdf(structure_data, song_title):
    """Generates a professional PDF with text wrapping and logo."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER)
    story = []
    styles = getSampleStyleSheet()

    # --- 1. LOGO SECTION ---
    # If you upload a file named 'logo.png' to your folder, it will render here.
    if os.path.exists("logo.png"):
        # Adjust width/height as needed (e.g., 2*inch wide)
        img = Image("logo.png", width=2*inch, height=0.75*inch)
        img.hAlign = 'RIGHT' # Puts logo in top right
        story.append(img)
        story.append(Spacer(1, 12))

    # --- 2. HEADER ---
    story.append(Paragraph("Drum Chart", styles['Title']))
    story.append(Paragraph(f"<b>Track:</b> {song_title}", styles['Normal']))
    story.append(Spacer(1, 20))

    # --- 3. TABLE DATA SETUP ---
    # We use 'Paragraph' for the Notes column so it wraps automatically
    table_data = [['SECTION', 'BARS', 'FEEL / GROOVE', 'NOTES']]
    
    for item in structure_data:
        # Wrap the notes text so it doesn't run off the page
        notes_paragraph = Paragraph(f"<font color='darkred'>{item.get('notes', '')}</font>", styles['BodyText'])
        
        row = [
            item.get('section', ''),
            item.get('bars', ''),
            item.get('feel', ''),
            notes_paragraph # This is the magic wrapper
        ]
        table_data.append(row)

    # --- 4. TABLE STYLING ---
    # Column widths: Section(1.5"), Bars(0.75"), Feel(2.0"), Notes(3.25")
    col_widths = [1.5*inch, 0.75*inch, 2.0*inch, 3.25*inch]
    
    chart_table = Table(table_data, colWidths=col_widths)
    
    chart_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey), # Header background
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),      # Header text
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),               # Left align everything
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),   # Header font
        ('FONTSIZE', (0,0), (-1,0), 12),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),            # Header padding
        ('BACKGROUND', (0,1), (-1,-1), colors.white),    # Body background
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),      # Grid lines
        ('VALIGN', (0,0), (-1,-1), 'TOP'),               # Align text to top of cell
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))

    story.append(chart_table)
    
    # --- BUILD PDF ---
    doc.build(story)
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