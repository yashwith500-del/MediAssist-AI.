
import os
import time
import logging
from pathlib import Path

from dotenv import load_dotenv
from google import genai

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = genai.Client(api_key=API_KEY) if API_KEY else None

REQUEST_TIMEOUT_SECONDS = 30
POLL_INTERVAL_SECONDS = 5
MAX_WAIT_SECONDS = 120


# --------------------------------------------------
# MEDICAL EDUCATIONAL INSTRUCTIONS
# --------------------------------------------------

SYSTEM_INSTRUCTIONS = """
You are MediAssist AI, an educational health information assistant.

Your purpose is to provide clear, accurate, systematic,
and understandable general health information.

GENERAL RESPONSE RULES:

1. Understand the complete question before answering.
2. Generate relevant, dynamic answers using Gemini.
3. Never use hardcoded answers for individual medical questions.
4. Use clear headings, numbered sections, and bullet points.
5. Explain medical terminology in simple language.
6. Avoid repeating the same information.
7. Do not invent medical facts, readings, or references.

MEDICAL SAFETY:

1. Provide educational information only.
2. Do not claim to diagnose a person's medical condition.
3. Do not prescribe medicines or personalized dosages.
4. Do not replace advice from a qualified healthcare professional.
5. Explain when professional medical assessment is appropriate.
6. For potentially urgent symptoms, advise seeking immediate
   help from a trusted adult and qualified medical services.

SYSTEMATIC MEDICAL ANSWER FORMAT:

Use these sections when relevant:

1. UNDERSTANDING
   Explain what the question means.

2. GENERAL MEDICAL INFORMATION
   Explain the relevant medical concept.

3. POSSIBLE EXPLANATIONS
   Describe general factors or possibilities without diagnosing.

4. IMPORTANT WARNING SIGNS
   Mention relevant warning signs when appropriate.

5. RECOMMENDED NEXT STEPS
   Give safe, general educational guidance.

6. LIMITATIONS
   Explain what cannot be concluded from the information provided.

Do not force irrelevant sections into simple questions.

BLOOD PRESSURE AND HEART RATE:

When discussing blood pressure:
- Explain systolic pressure.
- Explain diastolic pressure.
- Explain the measurement and its general significance.
- Do not diagnose from one reading.

When discussing heart rate:
- Explain what heart rate measures.
- Explain general factors that can influence it.
- Avoid diagnosing from one measurement.

When discussing blood pressure and heart rate together:
- Explain each measurement separately.
- Explain how they relate to cardiovascular function.
- Do not assume that one measurement directly determines the other.
- Do not diagnose based only on these values.

SENSOR DATA:

- Clearly distinguish real sensor readings from simulated values.
- Never describe sample or simulated readings as real measurements.
- Explain the limitations of readings when relevant.

RESPONSE QUALITY:

- Answer the exact question asked.
- Be systematic, informative, and easy to understand.
- Use appropriate medical terminology with explanations.
- Do not add unrelated information.
"""


# --------------------------------------------------
# AI STATUS
# --------------------------------------------------

def is_ai_ready():
    return client is not None


# --------------------------------------------------
# BACKGROUND INTERACTION POLLING
# --------------------------------------------------

def wait_for_interaction(interaction):

    interaction_id = interaction.id
    deadline = time.monotonic() + MAX_WAIT_SECONDS

    logger.info(
        "Gemini background interaction started."
    )

    while interaction.status == "in_progress":

        remaining = deadline - time.monotonic()

        if remaining <= 0:
            break

        time.sleep(
            min(POLL_INTERVAL_SECONDS, remaining)
        )

        interaction = client.interactions.get(
            id=interaction_id,
            timeout=REQUEST_TIMEOUT_SECONDS
        )

        logger.info(
            "Gemini interaction status: %s",
            interaction.status
        )

    return interaction


# --------------------------------------------------
# GEMINI AI RESPONSE
# --------------------------------------------------

def get_ai_response(question, history=None):

    if not isinstance(question, str) or not question.strip():
        return "Please enter a valid question."

    if client is None:
        return (
            "Gemini API is not configured. "
            "Please check GEMINI_API_KEY in your .env file."
        )

    interaction = None

    try:

        # Build conversation history.
        prompt_parts = []

        if isinstance(history, list):

            for item in history[-12:]:

                if not isinstance(item, dict):
                    continue

                role = item.get("role")
                message = item.get("text")

                if role not in ("user", "model"):
                    continue

                if not isinstance(message, str) or not message.strip():
                    continue

                role_name = (
                    "User" if role == "user" else "MediAssist AI"
                )

                prompt_parts.append(
                    f"{role_name}: {message[:4000]}"
                )

        # Add the latest question.
        prompt_parts.append(
            f"User: {question.strip()}"
        )

        complete_prompt = (
            "Continue the following conversation. "
            "Answer the latest user question.\n\n"
            + "\n\n".join(prompt_parts)
        )

        # Start background generation.
        interaction = client.interactions.create(
            model=MODEL,
            input=complete_prompt,
            system_instruction=SYSTEM_INSTRUCTIONS,
            background=True,
            timeout=REQUEST_TIMEOUT_SECONDS
        )

        logger.info(
            "Gemini interaction created: %s",
            interaction.id
        )

        # Wait for the completed result.
        if interaction.status == "in_progress":
            interaction = wait_for_interaction(interaction)

        # Check final status.
        if interaction.status == "completed":

            answer = (interaction.output_text or "").strip()

            if not answer:
                logger.warning(
                    "Gemini returned an empty response."
                )

                return (
                    "MediAssist AI received an empty response. "
                    "Please try asking again."
                )

            return answer

        if interaction.status == "failed":

            logger.error(
                "Gemini interaction failed: %s",
                getattr(interaction, "error", None)
            )

            return (
                "Gemini could not complete your request. "
                "Please try again."
            )

        if interaction.status == "cancelled":

            return (
                "The Gemini request was cancelled. "
                "Please try again."
            )

        if interaction.status == "requires_action":

            logger.warning(
                "Gemini interaction requires additional action."
            )

            return (
                "The request requires an action that is not "
                "configured in MediAssist AI."
            )

        # Handle requests that exceed the maximum wait time.
        logger.warning(
            "Gemini interaction did not finish within the time limit."
        )

        try:
            if interaction.status == "in_progress":
                client.interactions.cancel(
                    id=interaction.id,
                    timeout=REQUEST_TIMEOUT_SECONDS
                )
        except Exception:
            logger.exception(
                "Could not cancel the unfinished interaction."
            )

        return (
            "MediAssist AI is taking longer than expected. "
            "Please try your question again."
        )

    except Exception as error:

        logger.exception(
            "Gemini Interactions API failed: %s",
            type(error).__name__
        )

        return (
            "MediAssist AI could not generate an answer right now. "
            "Please check your internet connection, API configuration, "
            "model availability, and backend terminal."
        )
