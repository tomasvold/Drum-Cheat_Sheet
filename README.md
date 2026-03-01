# 🥁 ISOMIX | AI Drum Charts

An AI-powered web application designed for session drummers and transcription enthusiasts. This tool leverages the **Gemini 1.5 Pro** multimodal model to analyze audio files or YouTube videos and generate a structured "Road Map" (drum chart) including section labels, bar counts, groove analysis, and performance cues.

**🔗 [Live Demo](https://isomix-ai-drum-charts.streamlit.app/)**

---

## ⚠️ Disclaimer: Highly Experimental
**Please Note:** This project is currently in a **highly experimental** state. 
- The AI's ability to count bars and detect grooves can vary significantly depending on the complexity of the track and audio quality. 
- **Use "As Is":** This tool is intended to provide a "first draft" road map to save time, but results should always be verified by a human ear. 
- Accuracy is not guaranteed; always double-check your bar counts before the gig!

---

## ✨ Features
- **Multi-Source Input:** Upload your own audio files (MP3/WAV/M4A) or simply paste a public YouTube URL.
- **AI Transcription:** Uses a specialized "Session Drummer" persona to identify:
  - Precise bar counts and song structure.
  - Groove orchestration (e.g., "Purdie Shuffle", "Linear patterns").
  - Technical performance cues (stops, builds, kit-specific notes).
- **Interactive Editor:** Tweak the AI-generated data directly in the app before exporting.
- **Professional PDF Export:** Generate a gig-ready, cleanly formatted PDF with your custom notes highlighted.
- **Custom UI:** Built with a sleek, dark-themed "Studio" aesthetic.

## 🛠️ Tech Stack
- **Frontend:** [Streamlit](https://streamlit.io/)
- **LLM:** [Google Gemini 1.5 Pro](https://ai.google.dev/)
- **PDF Generation:** [ReportLab](https://www.reportlab.com/)
- **Language:** Python

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- A Google Gemini API Key (Available at [Google AI Studio](https://aistudio.google.com/))

### Installation
1. Clone the repository:
   ```bash
   git clone [https://github.com/tomasvold/Drum-Cheat_Sheet.git](https://github.com/tomasvold/Drum-Cheat_Sheet.git)
   cd Drum-Cheat-Sheet