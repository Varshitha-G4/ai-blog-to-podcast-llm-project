import os
from dotenv import load_dotenv
from agno.agent import Agent
from agno.run.agent import RunOutput
import google.generativeai as genai
from agno.tools.firecrawl import FirecrawlTools
from elevenlabs import ElevenLabs
import streamlit as st
from firecrawl import FirecrawlApp

# Load environment variables
load_dotenv()

# Get API keys from .env
gemini_key = os.getenv("GEMINI_API_KEY")
elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")
firecrawl_key = os.getenv("FIRECRAWL_API_KEY")

genai.configure(api_key=gemini_key)

# Streamlit Setup
st.set_page_config(page_title="📰 ➡️ 🎙️ Blog to Podcast", page_icon="🎙️")
st.title("📰 ➡️ 🎙️ Blog to Podcast Agent")

# Validate API keys
if not all([gemini_key, elevenlabs_key, firecrawl_key]):
    st.error("❌ Missing API keys! Please check your .env file.")
    st.stop()

# Blog URL Input
url = st.text_input("Enter Blog URL:", "")

# Generate Button
if st.button("🎙️ Generate Podcast"):
    if not url.strip():
        st.warning("⚠️ Please enter a blog URL")
    else:
        with st.spinner("Scraping blog and generating podcast..."):
            try:
                # 🔥 Step 1: Scrape blog using Firecrawl
                app = FirecrawlApp(api_key=firecrawl_key)

                scraped_data = app.scrape(url)
                blog_text = ""

                if hasattr(scraped_data, "markdown"):
                    blog_text = scraped_data.markdown
                elif isinstance(scraped_data, dict):
                    blog_text = scraped_data.get("markdown", "")

                if not blog_text:
                    st.error("❌ Could not extract blog content from Firecrawl response")
                    st.stop()

                # 🔥 Step 2: Gemini summarization (IMPROVED PROMPT)
                model = genai.GenerativeModel("gemini-2.5-flash")

                prompt = f"""
Convert this blog into a natural, engaging podcast conversation between two people.

Rules:
- DO NOT include labels like "Speaker A", "Speaker B", "Host", etc in final speech
- Write dialogue line by line
- Keep it conversational and natural
- Each line should be short (1-2 sentences)
- Alternate speakers naturally

FORMAT STRICTLY:
Speaker A: ...
Speaker B: ...

Blog:
{blog_text[:5000]}
"""

                response = model.generate_content(prompt)
                summary = response.text

                # 🔥 Step 3: Convert to audio (NEW LOGIC)

                client = ElevenLabs(api_key=elevenlabs_key)

                male_voice = "JBFqnCBsd6RMkjVDRZzb"
                female_voice = "EXAVITQu4vr4xnSDxMaL"

                lines = summary.split("\n")
                audio_chunks = []

                for line in lines:
                    line = line.strip()

                    if not line:
                        continue

                    if line.startswith("Speaker A:"):
                        text = line.replace("Speaker A:", "").strip()
                        voice_id = male_voice

                    elif line.startswith("Speaker B:"):
                        text = line.replace("Speaker B:", "").strip()
                        voice_id = female_voice

                    else:
                        continue

                    audio = client.text_to_speech.convert(
                        text=text,
                        voice_id=voice_id,
                        model_id="eleven_multilingual_v2"
                    )

                    audio_bytes = b"".join([chunk for chunk in audio if chunk])
                    audio_chunks.append(audio_bytes)

                final_audio = b"".join(audio_chunks)

                # Output
                st.success("🎧 Podcast generated successfully!")
                st.audio(final_audio, format="audio/mp3")

                st.download_button(
                    label="⬇️ Download Podcast",
                    data=final_audio,
                    file_name="podcast.mp3",
                    mime="audio/mp3"
                )

                with st.expander("📄 Podcast Summary"):
                    st.write(summary)

            except Exception as e:
                st.error(f"❌ Error: {e}")