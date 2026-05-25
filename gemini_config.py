import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL = "llama-3.3-70b-versatile"


def _generate(prompt):
    try:
        response = client.chat.completions.create(
            model=MODEL, messages=[{"role": "user", "content": prompt}]
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"Error: {str(e)}"


PITCH_STYLES = {
    "corporate": "Formal and professional tone.",
    "sharktank": "Exciting and persuasive like Shark Tank pitches.",
    "casual": "Friendly and informal style.",
    "inspirational": "Motivational, visionary tone.",
}


def generate_pitch(title, description, style="corporate"):
    style_prompt = PITCH_STYLES.get(style, PITCH_STYLES["corporate"])
    prompt = f"""You are a startup pitch expert.
Generate a 2-paragraph compelling startup pitch based on:
Title: {title}
Description: {description}
Style: {style_prompt}
Keep it energetic, persuasive, and investor-friendly."""
    return _generate(prompt)


def grade_pitch(pitch_text):
    prompt = f"""Grade this startup pitch on a scale of 1-10 for:
1. Clarity
2. Emotional Impact
3. Market Fit
For each, format exactly as: "Criterion: X/10 - explanation"
One per line, no extra text.

Pitch: {pitch_text}"""
    return _generate(prompt)


def refine_pitch(original_pitch, feedback="Make it more concise and impactful"):
    prompt = f"""Original pitch: {original_pitch}

Refine this pitch applying the following feedback: {feedback}
Return only the improved pitch, no preamble."""
    return _generate(prompt)


def generate_headline(title, desc, pitch_text):
    prompt = f"""Write a short catchy one-line headline for this startup.
Title: {title}
Description: {desc}
Pitch: {pitch_text}
Return only the headline, nothing else."""
    return _generate(prompt)


def competitor_extraction(pitch_text):
    prompt = f"""Given this pitch: {pitch_text}

List exactly 3 well-known competitors in the same space.
Format each line as: "CompanyName: One line description."
No numbering, no blank lines."""
    try:
        response = client.models.generate_content(model=MODEL, contents=prompt)
        return [l.strip() for l in response.text.strip().split("\n") if l.strip()]
    except Exception as e:
        return []


def differentiaiting_factor(pitch, competitors):
    comp_str = ", ".join(competitors)
    prompt = f"""Product pitch: "{pitch}"
Competitors: {comp_str}

In 4-5 lines write:
1. The main differentiating factor of this product
2. Why it beats the competitors
Output as a single paragraph."""
    return _generate(prompt)
