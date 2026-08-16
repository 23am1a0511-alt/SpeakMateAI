import os
from dotenv import load_dotenv
from groq import Groq


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError(
        "GROQ_API_KEY was not found. Make sure your .env file contains "
        "GROQ_API_KEY=your_api_key"
    )


# ============================================================
# CREATE GROQ CLIENT
# ============================================================

client = Groq(api_key=api_key)


# ============================================================
# TEXT AI
# ============================================================

def get_ai_response(user_text, user_answer=None):
    """
    Analyze a user's written answer and provide English feedback.
    """

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",

        messages=[
            {
                "role": "system",
                "content": (
                    "You are SpeakMateAI, a friendly English speaking "
                    "and writing coach. "
                    "Analyze the user's answer and help them improve "
                    "their English. "
                    "Give clear, concise and encouraging feedback. "
                    "Do not give separate percentage scores."
                )
            },

            {
                "role": "user",
                "content": (
                    f"Question or topic:\n{user_text}\n\n"
                    f"User's answer:\n{user_answer}"
                )
            }
        ],

        max_tokens=500,
        temperature=0.7
    )

    return response.choices[0].message.content


# ============================================================
# VOICE AI
# ============================================================

def analyze_voice(audio_data, context=None):
    """
    1. Convert recorded audio into text using Whisper.
    2. Send the transcript to Llama.
    3. Return ONE overall speaking percentage and feedback.
    """

    # --------------------------------------------------------
    # STEP 1: GET TRANSCRIPT
    # --------------------------------------------------------

    if isinstance(audio_data, str):

        # Audio data is already text
        transcript = audio_data

    else:

        # ----------------------------------------------------
        # Convert Streamlit uploaded/recorded audio to bytes
        # ----------------------------------------------------

        if hasattr(audio_data, "getvalue"):
            audio_bytes = audio_data.getvalue()

        elif isinstance(audio_data, bytes):
            audio_bytes = audio_data

        elif hasattr(audio_data, "read"):
            audio_bytes = audio_data.read()

        else:
            audio_bytes = bytes(audio_data)

        # ----------------------------------------------------
        # SPEECH TO TEXT USING WHISPER
        # ----------------------------------------------------

        transcription = client.audio.transcriptions.create(
            file=("recording.wav", audio_bytes),
            model="whisper-large-v3-turbo",
            language="en",
            response_format="json",
            temperature=0.0
        )

        transcript = transcription.text


    # --------------------------------------------------------
    # LIMIT TEXT LENGTH
    # --------------------------------------------------------

    transcript = str(transcript).strip()[:4000]

    if not transcript:
        return (
            "🎤 Overall Speaking Score: 0%\n\n"
            "I could not understand the recording. "
            "Please record your answer again."
        )


    # --------------------------------------------------------
    # CONTEXT
    # --------------------------------------------------------

    if context:
        context = str(context)[:1000]
    else:
        context = "No additional context provided."


    # --------------------------------------------------------
    # STEP 2: AI SPEAKING ANALYSIS
    # --------------------------------------------------------

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",

        messages=[
            {
                "role": "system",
                "content": (
                    "You are SpeakMateAI, a professional but friendly "
                    "English speaking coach.\n\n"

                    "Analyze the user's spoken English transcript.\n\n"

                    "Give EXACTLY ONE overall speaking score from 0 to 100. "
                    "The score should consider grammar, vocabulary, "
                    "fluency, clarity, sentence structure and naturalness.\n\n"

                    "DO NOT give separate scores for grammar, vocabulary, "
                    "fluency or clarity.\n\n"

                    "Your response MUST start with:\n"
                    "🎤 Overall Speaking Score: [number]%\n\n"

                    "Then provide:\n"
                    "1. Brief feedback\n"
                    "2. Corrected version\n"
                    "3. Exactly 2 improvement tips\n\n"

                    "Keep the response concise and encouraging."
                )
            },

            {
                "role": "user",
                "content": (
                    f"Spoken English transcript:\n"
                    f"{transcript}\n\n"
                    f"Question or context:\n"
                    f"{context}"
                )
            }
        ],

        max_tokens=500,
        temperature=0.5
    )

    return response.choices[0].message.content