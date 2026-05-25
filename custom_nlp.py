from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

audience_profiles = {
    "investor": "ROI market size scalability monetization exit strategy revenue growth",
    "customer": "usability features pricing benefits pain points ease of use experience",
    "partner": "collaboration integrations long-term value synergy ecosystem partnership"
}

def audience_alignment(pitch):
    texts = [pitch] + list(audience_profiles.values())
    tfidf = TfidfVectorizer().fit(texts)
    vectors = tfidf.transform(texts)
    scores = cosine_similarity(vectors[0:1], vectors[1:])[0]
    return {k: round(float(s) * 100, 1) for k, s in zip(audience_profiles.keys(), scores)}

buzzwords = {
    "synergy", "innovative", "disruptive", "cutting-edge", "revolutionary",
    "scalable", "paradigm", "leverage", "ecosystem", "bleeding-edge",
    "game-changer", "next-generation", "world-class", "transformative"
}

def buzzword_density(pitch):
    words = pitch.lower().split()
    if not words:
        return {"density": 0.0, "found": []}
    found = [w.strip(".,!?") for w in words if w.strip(".,!?") in buzzwords]
    return {"density": round((len(found) / len(words)) * 100, 1), "found": found}

def rewrite_in_persona(pitch):
    return {
        "vc": f"From a funding perspective: {pitch} — Scalable model with clear exit opportunities.",
        "genz": f"Okay so basically - {pitch.lower().replace('solution', 'fix')} - and it actually slaps",
        "jobs": f"It's not just a product. It's a revolution. {pitch} — One more thing: the world needed this."
    }