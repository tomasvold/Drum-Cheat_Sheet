import streamlit as st
import google.generativeai as genai
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
import os
import json
import time
import tempfile
from io import BytesIO

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="ISOMIX | AI Drum Charts",
    page_icon="🥁",
    layout="centered"
)

# --- 2. CUSTOM CSS (The "ISOMIX" Look) ---
# This block is what makes your app look like your Studio site
st.markdown("""
<style>
    /* IMPORT FONTS */
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Roboto:wght@300;400;700&display=swap');

    /* GLOBAL THEME */
    .stApp {
        background: radial-gradient(circle at center, #2c3e50 0%, #000 100%);
        background-attachment: fixed;
        font-family: 'Roboto', sans-serif;
        color: #e0e0e0;
    }

    /* CENTERED HEADERS */
    h1, h2, h3 {
        font-family: 'Orbitron', sans-serif !important;
        color: #00d2ff !important;
        letter-spacing: 2px;
        text-shadow: 0 0 10px rgba(0, 210, 255, 0.3);
        text-align: center; /* <--- ADDED THIS */
    }
    
    /* CENTERED SUBTITLES */
    .subtitle {
        font-size: 1.1rem;
        color: #aaa;
        margin-bottom: 30px;
        line-height: 1.6;
        text-align: center; /* <--- ADDED THIS */
    }

    /* "CARD" LOOK FOR MAIN CONTENT */
    /* This targets the main container to look like your landing page card */
    div.block-container {
        background-color: rgba(30, 30, 30, 0.85); /* Semi-transparent dark bg */
        padding: 3rem;
        border-radius: 16px;
        border: 1px solid #333;
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6);
        max-width: 800px; /* Limits width to look like a card */
        margin-top: 2rem;
    }

    /* BUTTONS */
    div.stButton > button {
        background-color: #ff9900;
        color: #111;
        font-family: 'Orbitron', sans-serif;
        font-weight: 700;
        text-transform: uppercase;
        border-radius: 50px;
        border: none;
        padding: 12px 30px;
        box-shadow: 0 0 15px rgba(255, 153, 0, 0.3);
        transition: all 0.3s ease;
        width: 100%;
    }
    div.stButton > button:hover {
        background-color: #ffaa33;
        color: #000;
        transform: translateY(-2px);
        box-shadow: 0 0 30px rgba(255, 153, 0, 0.6);
        border: none;
    }
    
    /* TABLE STYLING */
    div[data-testid="stTable"] {
        background: transparent; /* Let container bg show through */
    }
</style>
""", unsafe_allow_html=True)

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Google API Key", type="password")
    if not api_key and "GOOGLE_API_KEY" in os.environ:
        api_key = os.environ["GOOGLE_API_KEY"]
    
    st.info("Powered by **Gemini 2.5 Pro**")
    st.markdown("---")
    st.markdown("Created by **Tom Åsvold**")

# --- 4. HEADER UI ---
# Centering logic for the logo using columns
if os.path.exists("logo.png"):
    col1, col2, col3 = st.columns([1, 2, 1]) # Create 3 columns
    with col2: # Put logo in the middle one
        st.image("logo.png", use_container_width=True)

st.title("ISOMIX AI Drum Charts")

# The "Pro" Description
st.markdown("""
<div class="subtitle">
    Instantly turn any audio file into a gig-ready road map. 
    Get bar counts, groove analysis, and performance cues in seconds.
</div>
""", unsafe_allow_html=True)


# --- 5. FUNCTIONS (Logic) ---
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
    # Use the smart model
    model = genai.GenerativeModel("gemini-2.5-pro") 
    
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
    
    response = model.generate_content(
        [system_instruction, example_prompt, "Now analyze this track and output the JSON:", file],
        generation_config={"response_mime_type": "application/json"}
    )
    return json.loads(response.text)

def create_pdf(structure_data, song_title):
    """Generates a professional PDF with Side-by-Side Header."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()

    # --- HEADER ---
    clean_title = song_title
    for ext in [".mp3", ".wav", ".m4a"]:
        clean_title = clean_title.replace(ext, "")
        
    title_style = styles['Heading1']
    title_style.fontSize = 24
    title_style.leading = 28
    title_style.textColor = colors.black
    
    subtitle_style = styles['Normal']
    subtitle_style.fontSize = 12
    subtitle_style.textColor = colors.gray

    header_text = [
        Paragraph(f"<b>{clean_title}</b>", title_style),
        Paragraph("Drum Chart / Road Map", subtitle_style)
    ]
    
    header_logo = []
    if os.path.exists("logo.png"):
        img = Image("logo.png", width=2*inch, height=0.66*inch)
        img.hAlign = 'RIGHT'
        header_logo.append(img)
    
    header_table_data = [[header_text, header_logo]]
    header_table = Table(header_table_data, colWidths=[5*inch, 2.5*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (0,0), (0,0), 'LEFT'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 30))

    # --- CHART DATA ---
    table_data = [['SECTION', 'BARS', 'FEEL / GROOVE', 'NOTES']]
    for item in structure_data:
        notes_text = f"<font color='#8B0000'>{item.get('notes', '')}</font>"
        notes_cell = Paragraph(notes_text, styles['BodyText'])
        feel_cell = Paragraph(item.get('feel', ''), styles['BodyText'])
        row = [item.get('section', ''), item.get('bars', ''), feel_cell, notes_cell]
        table_data.append(row)

    col_widths = [1.3*inch, 0.7*inch, 2.2*inch, 3.3*inch]
    chart_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    chart_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 11),
        ('BOTTOMPADDING', (0,0), (-1,0), 10),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(chart_table)
    doc.build(story)
    buffer.seek(0)
    return buffer

# --- 6. MAIN UI LOGIC ---
uploaded_file = st.file_uploader("Upload Audio (MP3/WAV)", type=["mp3", "wav", "m4a"])

if "chart_data" not in st.session_state:
    st.session_state.chart_data = None

if uploaded_file and api_key:
    # Button Style Trigger (Handled by CSS above)
    if st.button("GENERATE CHART"):
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name

            with st.status("Processing...", expanded=True) as status:
                st.write("Uploading to Gemini...")
                g_file = upload_to_gemini(tmp_path, api_key)
                
                st.write("Listening & counting bars...")
                g_file = wait_for_processing(g_file)
                
                st.write("Generating chart...")
                st.session_state.chart_data = analyze_audio(g_file)
                
                status.update(label="Done!", state="complete", expanded=False)
            
            os.remove(tmp_path)

        except Exception as e:
            st.error(f"An error occurred: {e}")

    # EDITOR & DOWNLOAD
    if st.session_state.chart_data is not None:
        st.markdown("### Edit Your Chart")
        
        edited_data = st.data_editor(
            st.session_state.chart_data,
            column_config={
                "section": "Section",
                "bars": "Bars",
                "feel": "Feel / Groove",
                "notes": st.column_config.TextColumn("Notes", width="large")
            },
            num_rows="dynamic",
            use_container_width=True 
        )

        pdf_bytes = create_pdf(edited_data, uploaded_file.name)
        
        st.download_button(
            label="DOWNLOAD PDF CHART 📄",
            data=pdf_bytes,
            file_name=f"{uploaded_file.name.replace('.mp3', '')}_chart.pdf",
            mime="application/pdf"
        )
        
        if st.button("START OVER"):
            st.session_state.chart_data = None
            st.rerun()

elif not api_key:
    st.warning("👈 Please enter your Google API Key in the sidebar to start.")