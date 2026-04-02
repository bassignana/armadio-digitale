import streamlit as st
import json
import uuid
import torch
from datetime import datetime
from pathlib import Path
from PIL import Image
from transformers import CLIPProcessor, CLIPModel

# ── 1. DEFINIZIONE DEI PERCORSI E DELLE COSTANTI ──────────────────────────────
DATA_DIR = Path("wardrobe_data")
IMG_DIR = DATA_DIR / "images"
WARDROBE_F = DATA_DIR / "wardrobe.json"
OUTFITS_F  = DATA_DIR / "outfits.json"

DATA_DIR.mkdir(exist_ok=True)
IMG_DIR.mkdir(exist_ok=True)

ALL_CATEGORIES = [
    "Maglietta / Top", "Camicia / Blusa", "Maglione / Felpa",
    "Giacca / Cappotto", "Pantaloni", "Gonna", "Abito / Tuta",
    "Scarpe", "Borsa / Accessori", "Altro",
]

# ── 2. FUNZIONI HELPER (DA MODULI 2 & 3) ──────────────────────────────────────
# ... (le funzioni load_json, save_json, save_uploaded_image rimangono invariate)
def load_json(path, default):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    return default
def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f: json.dump(data, f, indent=2, ensure_ascii=False)
def save_uploaded_image(uploaded_file) -> str:
    img = Image.open(uploaded_file)
    ext = Path(uploaded_file.name).suffix or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    path = IMG_DIR / filename
    img = img.convert("RGB")
    img.thumbnail((600, 600))
    img.save(path)
    return filename

# ── 3. CLASSIFICATORE FASHION-CLIP (NUOVA SEZIONE!) ──────────────────────────
# Definiamo i prompt in inglese per ogni categoria.
# Il modello confronterà l'immagine con queste descrizioni.
CLIP_PROMPTS: dict[str, list[str]] = {
    "Maglietta / Top":   ["a t-shirt", "a top", "a tank top", "a crop top"],
    "Camicia / Blusa":   ["a shirt", "a blouse", "a button-up shirt", "a dress shirt"],
    "Maglione / Felpa":  ["a sweater", "a hoodie", "a sweatshirt", "a knit pullover", "a cardigan"],
    "Giacca / Cappotto": ["a jacket", "a coat", "a blazer", "a trench coat", "a parka"],
    "Pantaloni":         ["a pair of jeans", "trousers", "pants", "shorts", "leggings"],
    "Gonna":             ["a skirt", "a miniskirt", "a maxi skirt"],
    "Abito / Tuta":      ["a dress", "a gown", "a jumpsuit", "an overall"],
    "Scarpe":            ["a pair of shoes", "sneakers", "boots", "sandals", "loafers"],
    "Borsa / Accessori": ["a handbag", "a backpack", "a belt", "a scarf", "a hat", "sunglasses"],
}

# Creiamo una lista piatta di tutti i prompt e una lista corrispondente
# che mappa ogni prompt alla sua categoria italiana. Questo ci servirà dopo.
_PROMPTS: list[str] = []
_PROMPT_TO_CAT: list[str] = []
for _cat, _prompts in CLIP_PROMPTS.items():
    for _p in _prompts:
        _PROMPTS.append(_p)
        _PROMPT_TO_CAT.append(_cat)

@st.cache_resource(show_spinner="Caricamento modello AI... (solo al primo avvio)")
def _load_clip():
    """Carica il modello fashion-clip e il processore. Viene messo in cache da Streamlit."""

    model_id = "patrickjohncyh/fashion-clip"
    # Il processore prepara immagini e testi per il modello
    processor = CLIPProcessor.from_pretrained(model_id)
    # Il modello è la rete neurale vera e propria
    model = CLIPModel.from_pretrained(model_id)
    # Impostiamo il modello in modalità "valutazione" (non addestramento)
    model.eval()
    return model, processor

def classify_image(pil_img: Image.Image) -> tuple:
    """
    Classifica un'immagine usando fashion-clip e la tecnica zero-shot.
    Restituisce (etichetta_categoria, stringa_confidenza).
    """

    try:
        model, processor = _load_clip()
    except Exception as e:
        st.error(f"Errore durante il caricamento del modello: {e}")
        return "Altro", "Modello non disponibile"

    img_rgb = pil_img.convert("RGB")

    # Il processore prende i testi e l'immagine e li converte in "tensori" (matrici numeriche).
    inputs = processor(
        text=_PROMPTS,
        images=img_rgb,
        return_tensors="pt", # PyTorch tensors
        padding=True,
    )

    # Disabilitiamo il calcolo dei gradienti (non stiamo addestrando) per essere più veloci.
    with torch.no_grad():
        outputs = model(**inputs)
        # Otteniamo i "logits", che sono i punteggi di similarità grezzi.
        logits_per_image = outputs.logits_per_image
        # Applichiamo la funzione softmax per convertirli in probabilità (da 0 a 1).
        probs = logits_per_image.softmax(dim=1).numpy()

    # Aggreghiamo le probabilità: sommiamo i punteggi di tutti i prompt di una stessa categoria.
    cat_scores: dict[str, float] = {cat: 0.0 for cat in CLIP_PROMPTS}
    for prob, cat in zip(probs[0], _PROMPT_TO_CAT):
        cat_scores[cat] += float(prob)

    # Troviamo la categoria con il punteggio totale più alto.
    best_cat = max(cat_scores, key=cat_scores.get)
    best_score = cat_scores[best_cat]
    
    # Se la confidenza è molto bassa, forse l'oggetto non è un capo d'abbigliamento.
    if best_score < 0.10:
        return "Altro", "Confidenza troppo bassa per classificare"

    return best_cat, f"confidenza: {best_score:.0%}"

# ── 4. PAGINA ARMADIO (MODIFICATA PER USARE IL CLASSIFICATORE) ────────────────
def page_armadio():
    st.header("👕 Il mio Armadio")
    wardrobe = load_json(WARDROBE_F, [])

    st.subheader("Aggiungi un capo")
    uploaded = st.file_uploader("Carica una foto del capo", type=["jpg", "jpeg", "png", "webp"])

    if uploaded:
        pil_img = Image.open(uploaded)
        col_img, col_info = st.columns([1, 2])
        
        with col_img:
            st.image(pil_img, width=200)
            
        with col_info:
            # --- MODIFICA CHIAVE: USIAMO IL NOSTRO CLASSIFICATORE! ---
            detected_cat, reason = classify_image(pil_img)
            
            st.success(f"Categoria rilevata: **{detected_cat}**")
            st.caption(f"Dettagli: {reason}")
            
            # Troviamo l'indice della categoria rilevata per pre-selezionarla.
            try:
                idx = ALL_CATEGORIES.index(detected_cat)
            except ValueError:
                idx = len(ALL_CATEGORIES) - 1 # Default su "Altro" se non la trova
            
            final_cat = st.selectbox("Conferma o correggi la categoria", ALL_CATEGORIES, index=idx)
            note = st.text_input("Note (colore, marca, stagione…)", placeholder="es. blu navy, estate")
            
            if st.button("💾 Salva nell'armadio"):
                filename = save_uploaded_image(uploaded)
                item = {
                    "id": uuid.uuid4().hex,
                    "filename": filename,
                    "categoria": final_cat, # Salviamo la categoria finale (confermata dall'utente)
                    "note": note,
                    "aggiunto": datetime.now().strftime("%Y-%m-%d"),
                }
                wardrobe.append(item)
                save_json(WARDROBE_F, wardrobe)
                st.success("Capo aggiunto con successo!")
                st.rerun()

    st.divider()

    if not wardrobe:
        st.info("Il tuo armadio è vuoto. Carica il primo capo!")
        return

    st.subheader(f"Capi nell'armadio ({len(wardrobe)})")
    
    # Aggiungiamo un filtro per categoria per rendere la UI più utile
    cats_present = sorted(list(set(it["categoria"] for it in wardrobe)))
    selected_cat = st.selectbox("Filtra per categoria", ["Tutti"] + cats_present)
    
    filtered = wardrobe if selected_cat == "Tutti" else [
        it for it in wardrobe if it["categoria"] == selected_cat
    ]

    cols = st.columns(3)
    for i, item in enumerate(filtered):
        with cols[i % 3]:
            img_path = IMG_DIR / item["filename"]
            if img_path.exists():
                st.image(str(img_path))
            st.caption(f"**{item['categoria']}**")
            if item.get("note"): st.caption(item["note"])
            if st.button("🗑️ Rimuovi", key=f"del_{item['id']}"):
                wardrobe = [it for it in wardrobe if it["id"] != item["id"]]
                save_json(WARDROBE_F, wardrobe)
                if img_path.exists(): img_path.unlink()
                st.rerun()

# ── 5. PAGINA OUTFIT (ORA COMPLETA!) ──────────────────────────────────────────
def page_outfit():
    st.header("✨ Crea un Outfit")
    
    # Carichiamo sia i dati dell'armadio sia gli outfit esistenti
    wardrobe = load_json(WARDROBE_F, [])
    outfits = load_json(OUTFITS_F, [])

    if not wardrobe:
        st.warning("Aggiungi prima qualche capo nell'armadio!")
        return

    # --- Sezione per creare un nuovo outfit ---
    st.subheader("Nuovo outfit")
    outfit_name = st.text_input("Nome outfit", placeholder="es. Ufficio lunedì")

    # Creiamo un dizionario per accedere facilmente ai dati di un capo dal suo ID
    id_to_item = {it["id"]: it for it in wardrobe}
    # Troviamo le categorie uniche presenti nell'armadio per creare i selettori
    cats_in_wardrobe = sorted({it["categoria"] for it in wardrobe})
    
    selected_ids = []
    for cat in cats_in_wardrobe:
        # Per ogni categoria, troviamo i capi corrispondenti
        items_in_cat = [it for it in wardrobe if it["categoria"] == cat]
        
        # Creiamo etichette leggibili per il multiselect
        # es. "Pantaloni - Jeans blu"
        # Questo gestisce anche capi con note uguali aggiungendo un contatore
        options = {}
        for it in items_in_cat:
            base_label = it.get("note") or it["aggiunto"]
            label = f"{it['categoria']} — {base_label}"
            count = 1
            while label in options:
                label = f"{it['categoria']} — {base_label} ({count})"
                count += 1
            options[label] = it["id"]

        # Mostriamo un multiselect per ogni categoria
        chosen_labels = st.multiselect(cat, list(options.keys()), key=f"ms_{cat}")
        # Aggiungiamo gli ID dei capi scelti alla lista totale
        if chosen_labels:
            selected_ids.extend([options[label] for label in chosen_labels])

    # Anteprima della selezione
    if selected_ids:
        st.subheader("Anteprima selezione")
        cols = st.columns(min(len(selected_ids), 5))
        for i, item_id in enumerate(selected_ids):
            item = id_to_item[item_id]
            with cols[i % 5]:
                st.image(str(IMG_DIR / item["filename"]))
                st.caption(item["categoria"])

    # Bottone per salvare l'outfit
    if st.button("💾 Salva outfit"):
        if not outfit_name.strip():
            st.error("Dai un nome all'outfit!")
        elif not selected_ids:
            st.error("Seleziona almeno un capo!")
        else:
            outfits.append({
                "id": uuid.uuid4().hex,
                "nome": outfit_name.strip(),
                "capi_ids": selected_ids, # Salviamo solo la lista degli ID!
                "creato": datetime.now().strftime("%Y-%m-%d"),
            })
            save_json(OUTFITS_F, outfits)
            st.success(f"Outfit «{outfit_name}» salvato!")
            st.rerun()

    st.divider()

    # --- Sezione per visualizzare gli outfit salvati ---
    if not outfits:
        st.info("Nessun outfit salvato. Creane uno!")
        return

    st.subheader(f"Outfit salvati ({len(outfits)})")
    for outfit in outfits:
        # Usiamo un expander per ogni outfit
        with st.expander(f"👗 {outfit['nome']}  (creato il {outfit['creato']})"):
            # Recuperiamo i dati completi dei capi partendo dai loro ID
            # Gestiamo il caso in cui un capo sia stato cancellato dall'armadio
            capi_in_outfit = [id_to_item[cid] for cid in outfit["capi_ids"] if cid in id_to_item]
            
            if not capi_in_outfit:
                st.caption("I capi di questo outfit sono stati rimossi dall'armadio.")
            else:
                cols = st.columns(min(len(capi_in_outfit), 5))
                for i, item in enumerate(capi_in_outfit):
                    with cols[i % 5]:
                        st.image(str(IMG_DIR / item["filename"]))
                        st.caption(item["categoria"])

            # Bottone per eliminare l'outfit
            if st.button("🗑️ Elimina outfit", key=f"delout_{outfit['id']}"):
                outfits = [o for o in outfits if o["id"] != outfit["id"]]
                save_json(OUTFITS_F, outfits)
                st.rerun()

# ── 6. STRUTTURA PRINCIPALE (INVARIATA) ───────────────────────────────────
def main():
    st.set_page_config(page_title="Armadio Digitale", page_icon="👗", layout="wide")
    st.title("👗 Armadio Digitale")
    pagina = st.sidebar.radio("Navigazione", ["👕 Armadio", "✨ Outfit"])
    if pagina == "👕 Armadio": page_armadio()
    else: page_outfit()

if __name__ == "__main__":
    main()