import streamlit as st
import google.generativeai as genai
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_RIGHT
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
    """Generates a professional PDF with Side-by-Side Header."""
    buffer = BytesIO()
    # Margins: 0.5 inch on sides to maximize space
    doc = SimpleDocTemplate(buffer, pagesize=LETTER, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()

    # --- 1. HEADER SECTION (Side-by-Side) ---
    
    # A. Clean up the title (Remove .mp3/.wav for the big header)
    clean_title = song_title
    for ext in [".mp3", ".wav", ".m4a"]:
        clean_title = clean_title.replace(ext, "")
        
    # B. Define Styles
    # Create a custom "Big Title" style
    title_style = styles['Heading1']
    title_style.fontSize = 24
    title_style.leading = 28 # Line height
    title_style.textColor = colors.black
    
    # Create a "Subtitle" style
    subtitle_style = styles['Normal']
    subtitle_style.fontSize = 12
    subtitle_style.textColor = colors.gray

    # C. Create Elements
    # Left Side: Title + "Drum Chart" text
    header_text = [
        Paragraph(f"<b>{clean_title}</b>", title_style),
        Paragraph("Drum Chart / Road Map", subtitle_style)
    ]
    
    # Right Side: Logo
    header_logo = []
    if os.path.exists("logo.png"):
        # Adjust these numbers to fit your specific logo shape
        img = Image("logo.png", width=2*inch, height=0.66*inch)
        img.hAlign = 'RIGHT'
        header_logo.append(img)
    
    # D. Build the Header Table (2 Columns)
    # Col 1 (Text) gets 60% width, Col 2 (Logo) gets 40% width
    header_table_data = [[header_text, header_logo]]
    
    header_table = Table(header_table_data, colWidths=[5*inch, 2.5*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'), # Align text and logo to top
        ('ALIGN', (0,0), (0,0), 'LEFT'),   # Title aligns Left
        ('ALIGN', (1,0), (1,0), 'RIGHT'),  # Logo aligns Right
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    
    story.append(header_table)
    story.append(Spacer(1, 30)) # Add space before the chart starts

    # --- 2. CHART DATA ---
    table_data = [['SECTION', 'BARS', 'FEEL / GROOVE', 'NOTES']]
    
    for item in structure_data:
        # Style the Notes in Red
        notes_text = f"<font color='#8B0000'>{item.get('notes', '')}</font>"
        notes_cell = Paragraph(notes_text, styles['BodyText'])
        
        # Style the Feel (Standard text)
        feel_cell = Paragraph(item.get('feel', ''), styles['BodyText'])
        
        row = [
            item.get('section', ''),
            item.get('bars', ''),
            feel_cell,
            notes_cell
        ]
        table_data.append(row)

    # --- 3. CHART STYLING ---
    # Adjusted widths to fit the new margins (Total ~7.5 inches)
    col_widths = [1.3*inch, 0.7*inch, 2.2*inch, 3.3*inch]
    
    chart_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    
    chart_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 11), # Slightly smaller header to fit more
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