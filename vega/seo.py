"""Deterministic, offline content suggestions. No external AI is called."""
import re
from .store import MODELS

PLATFORM = {
    "Instagram": ("Descoperă", "Salvează ideea pentru mai târziu."),
    "TikTok": ("Uite", "Spune-mi în comentarii ce alegi."),
    "X": ("O idee despre", "Tu ce părere ai?"),
    "Reddit": ("Întrebare deschisă despre", "Sunt curioasă cum vedeți voi subiectul."),
    "Fanvue": ("Din culise:", "Vezi noutățile și spune-mi ce ți-ar plăcea să vezi în continuare."),
}

def suggest(model, platform, topic):
    label = " ".join(topic.split()).strip()[:140]
    if not label: raise ValueError("Completează un subiect")
    action, cta = PLATFORM[platform]
    identity = model["name"]
    niche = model["niche"]
    if platform == "Reddit":
        hooks = [f"Ce recomandări aveți pentru {label}?", f"Ce ați schimba la {label}?", f"Experiențe reale cu {label}?"]
    else:
        hooks = [f"{action} {label} — într-un stil diferit.",
                 f"3 detalii despre {label} pe care merită să le observi.",
                 f"Cum aleg eu {label}: simplu, personal și fără grabă."]
    words = re.findall(r"[\wăâîșțĂÂÎȘȚ]{3,}", label, re.UNICODE)[:4]
    tags = list(dict.fromkeys(["#AIModel", "#DigitalCreator"] +
                              ["#"+re.sub(r"\W", "", w).title() for w in words]))
    caption = (f"{label.capitalize()} — o nouă idee din universul {identity}. "
               f"Explorăm {niche.lower()} cu o perspectivă personală. "
               f"Personaj virtual creat cu AI. {cta}")
    return {"hooks":hooks, "title":label[:90], "caption":caption,
            "hashtags":" ".join(tags), "cta":cta,
            "note":"Propuneri editoriale locale (șabloane), nu rezultate ale analizei trendurilor live."}
