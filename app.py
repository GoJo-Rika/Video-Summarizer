import tempfile
import time
from pathlib import Path

import google.generativeai as genai
import streamlit as st
from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.duckduckgo import DuckDuckGoTools
from dotenv import load_dotenv
from google.generativeai import get_file, upload_file

load_dotenv()

import os

API_KEY = os.getenv("GOOGLE_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)

# Page configuration
st.set_page_config(
    page_title="Multimodal AI Agent- Video Summarizer", page_icon="🎥", layout="wide"
)

st.title("Agno Video AI Summarizer Agent 🎥🎤")
st.header("Powered by Gemini")


@st.cache_resource
def initialize_agent():
    return Agent(
        name="Video AI Summarizer",
        model=Gemini(id="gemini-2.0-flash-lite"),
        tools=[DuckDuckGoTools()],
        markdown=True,
    )


## Initialize the agent
multimodal_Agent = initialize_agent()

# File uploader
video_file = st.file_uploader(
    "Upload a video file",
    type=["mp4", "mov", "avi"],
    help="Upload a video for AI analysis",
)

if video_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video:
        temp_video.write(video_file.read())
        video_path = temp_video.name

    st.video(video_path, format="video/mp4", start_time=0)

    user_query = st.text_area(
        "What insights are you seeking from the video?",
        placeholder="Ask anything about the video content. The AI agent will analyze and gather additional context if needed.",
        help="Provide specific questions or insights you want from the video.",
    )

    if st.button("🔍 Analyze Video", key="analyze_video_button"):
        if not user_query:
            st.warning("Please enter a question or insight to analyze the video.")
        else:
            try:
                with st.spinner("Processing video and gathering insights..."):
                    # Upload and process video file
                    processed_video = upload_file(video_path)
                    while processed_video.state.name == "PROCESSING":
                        time.sleep(1)
                        processed_video = get_file(processed_video.name)

                    # Prompt generation for analysis
                    analysis_prompt = f"""
                        Analyze the uploaded video for content and context.
                        Respond to the following query using video insights and supplementary web research:
                        {user_query}

                        Provide a detailed, user-friendly, and actionable response.
                        """

                    print("Processed Video Object:", processed_video)
                    print("Attributes:", dir(processed_video))

                    # AI agent processing
                    response = multimodal_Agent.run(
                        analysis_prompt, videos=[{"filepath": video_path}]
                    )

                # Display the result
                st.subheader("Analysis Result")
                st.markdown(response.content)

            except Exception as error:
                st.error(f"An error occurred during analysis: {error}")
            finally:
                # Clean up temporary video file
                Path(video_path).unlink(missing_ok=True)
else:
    st.info("Upload a video file to begin analysis.")

# Customize text area height
st.markdown(
    """
    <style>
    .stTextArea textarea {
        height: 100px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
