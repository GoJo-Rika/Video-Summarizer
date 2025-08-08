import os
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

API_KEY = os.getenv("GOOGLE_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)

# Page configuration
st.set_page_config(
    page_title="Multimodal AI Agent- Video Summarizer",
    page_icon="🎥",
    layout="wide", # uses the full width of the screen for a more spacious interface.
)

st.title("Agno Video AI Summarizer Agent 🎥🎤")
st.header("Powered by Gemini")

# Use Streamlit's caching to initialize the AI agent only once.
# '@st.cache_resource' ensures the Agent object is not recreated on every script rerun (e.g., user interaction),
# which significantly improves performance and reduces costs.
@st.cache_resource
def initialize_agent() -> Agent:
    """
    Creates and configures the AI agent.
    This function is cached to ensure it only runs once per session.
    """
    return Agent(
        name="Video AI Summarizer",
        model=Gemini(id="gemini-2.0-flash-lite"),
        tools=[DuckDuckGoTools()], # Perform web searches
        markdown=True, # Enable markdown for formatted output
    )


## Initialize the agent
multimodal_agent = initialize_agent()

# File uploader widget
video_file = st.file_uploader(
    "Upload a video file",
    type=["mp4", "mov", "avi"], # restricts the allowed file extensions
    help="Upload a video for AI analysis", # provides a tooltip for the user
)

# Executes only if a user has successfully uploaded a file.
if video_file:
    # Use a temporary file to safely store the uploaded video on the server's disk.
    # 'delete=False' is essential because it prevents the file from being deleted
    # immediately after the 'with' block, allowing us to use its path.
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video:
        temp_video.write(video_file.read()) # Write the content of the uploaded video into the temporary file.
        video_path = temp_video.name # Get the file path of the temporary file.

    # Display the uploaded video in the Streamlit app for user confirmation.
    st.video(video_path, format="video/mp4", start_time=0)

    # Create a text area for the user to input their analysis query.
    user_query = st.text_area(
        "What insights are you seeking from the video?",
        placeholder="Ask anything about the video content. The AI agent will analyze and gather additional context if needed.",
        help="Provide specific questions or insights you want from the video.",
    )

    # Main button that triggers the analysis.
    if st.button("🔍 Analyze Video", key="analyze_video_button"):
        if not user_query: # To ensure the user has entered a query.
            st.warning("Please enter a question or insight to analyze the video.")
        else:
            try:
                # Use a spinner to provide visual feedback to the user during the long-running process.
                with st.spinner("Processing video and gathering insights..."):
                    # Upload the video file from its path to Google's servers for processing.
                    # This returns a File object that represents the video in Google's system.
                    st.write("Uploading file to Google...")
                    processed_video = upload_file(video_path)
                    st.write(f"File '{processed_video.display_name}' uploaded. Processing...")

                    # Google's File API processes videos asynchronously. We must poll the API
                    # to check the file's status until it is 'ACTIVE' (ready for use).
                    while processed_video.state.name == "PROCESSING":
                        # Wait for a few seconds before checking the status again to avoid excessive polling.
                        time.sleep(5)
                        # Fetch the latest status of the file.
                        processed_video = get_file(processed_video.name)

                    if processed_video.state.name != "ACTIVE":
                         msg = f"Video processing failed. Final state: {processed_video.state.name}"
                         raise ValueError(msg)

                    st.write("Video processing complete. Analyzing with AI...")

                    # Prompt generation for analysis
                    analysis_prompt = f"""
                        Analyze the uploaded video's content and context in detail.
                        Respond to the following query: "{user_query}"

                        Base your answer on insights from the video and supplement it with web research using your available tools.
                        Provide a detailed, user-friendly, and well-structured response.
                        """

                    print("Processed Video Object:", processed_video)
                    print("Attributes:", dir(processed_video))

                    # AI agent processing
                    response = multimodal_agent.run(
                        analysis_prompt, videos=[{"filepath": video_path}],
                    )

                # Display the final result from the AI agent.
                st.subheader("Analysis Result")
                st.markdown(response.content)

            except (FileNotFoundError, ValueError, TimeoutError, ConnectionError) as error:
                st.error(f"An error occurred during analysis: {error}")
            finally:
                # Clean up temporary video file
                # This block ALWAYS runs, whether the process succeeded or failed.
                # It ensures the temporary video file is deleted from the server,
                # preventing disk space from being filled with old uploads.
                Path(video_path).unlink(missing_ok=True)
else:
    # Display a message if no video has been uploaded yet.
    st.info("Upload a video file to begin analysis.") 

# Customize text area height
st.markdown(
    """
    <style>
    .stTextArea textarea {
        height: 150px;
    }
    </style>
    """,
    unsafe_allow_html=True, # render raw HTML/CSS in Streamlit
)
