import streamlit as st
import json
import uuid
from datetime import datetime
from pathlib import Path
from PIL import Image

DATA_DIR = Path("wardrobe_data")
IMG_DIR = DATA_DIR / "images"
WARDROBE_F = DATA_DIR / "wardrobe.json"

DATA_DIR.mkdir(exist_ok=True)
IMG_DIR.mkdir(exist_ok=True)

# Definiamo le categorie che l'utente potrà scegliere.
ALL_CATEGORIES = [
    "Maglietta / Top", "Camicia / Blusa", "Maglione / Felpa",
    "Giacca / Cappotto", "Pantaloni", "Gonna", "Abito / Tuta",
    "Scarpe", "Borsa / Accessori", "Altro",
]

# FUNZIONI HELPER (DA MODULI 2 & 3) 

def load_json(path, default):
    """Carica dati da un file JSON. Se non esiste, restituisce il default."""
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(path, data):
    """Salva dati in un file JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def save_uploaded_image(uploaded_file) -> str:
    """
    Salva un'immagine caricata, la ridimensiona e restituisce il suo nome univoco.
    """
    # Apriamo l'immagine con Pillow
    img = Image.open(uploaded_file)
    
    # Creiamo un nome file univoco basato su UUID e manteniamo l'estensione originale
    ext = Path(uploaded_file.name).suffix or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    path = IMG_DIR / filename
    
    # Convertiamo in RGB, creiamo una thumbnail e salviamo
    img = img.convert("RGB")
    img.thumbnail((600, 600))
    img.save(path)
    return filename

# Aggiungiamo la logica nella pagina armadio, pattern load, modify, save.
def page_armadio():
    st.header("👕 Il mio Armadio")
    
    # PATTERN: LOAD
    wardrobe = load_json(WARDROBE_F, [])

    # Logica: carichiamo la foto
    st.subheader("Aggiungi un capo")
    uploaded = st.file_uploader("Carica una foto del capo", type=["jpg", "jpeg", "png", "webp"])

    # NB: osservate come è semplice gestire la logica dell'applicazione
    if uploaded:
        # Usiamo le colonne per affiancare immagine e form
        col_img, col_info = st.columns([1, 2])
        
        with col_img:
            st.image(uploaded, width=200)
            
        with col_info:
            categoria = st.selectbox("Categoria", ALL_CATEGORIES)
            note = st.text_input("Note (colore, marca, stagione…)", placeholder="es. blu navy, estate")
            
            if st.button("💾 Salva nell'armadio"):
                # Salviamo l'immagine e otteniamo il suo nome univoco
                filename = save_uploaded_image(uploaded)
                
                # Creiamo il dizionario per il nuovo capo
                item = {
                    "id": uuid.uuid4().hex,
                    "filename": filename,
                    "categoria": categoria,
                    "note": note,
                    "aggiunto": datetime.now().strftime("%Y-%m-%d"),
                }
                
                # PATTERN: MODIFICA
                wardrobe.append(item)
                
                # PATTERN: SAVE
                save_json(WARDROBE_F, wardrobe)
                st.success("Capo aggiunto con successo!")
                
                # Ricarica la pagina per mostrare il nuovo stato
                st.rerun()

    st.divider()

    # Sezione di Visualizzazione Armadio
    if not wardrobe:
        st.info("Il tuo armadio è vuoto. Carica il primo capo!")
        return

    st.subheader(f"Capi nell'armadio ({len(wardrobe)})")
    
    # Creiamo le colonne per la griglia. Il numero può essere cambiato.
    cols = st.columns(3)
    for i, item in enumerate(wardrobe):
        # Truecchetto: uso il modulo (%) per distribuire gli elementi nelle colonne a rotazione
        with cols[i % 3]:
        
            # Mostriamo l'immagine
            img_path = IMG_DIR / item["filename"]
            if img_path.exists():
                st.image(str(img_path))
            
            # Mostriamo le informazioni
            st.caption(f"**{item['categoria']}**")
            if item.get("note"): # .get() è un modo sicuro per accedere a una chiave che potrebbe non esistere
                st.caption(item["note"])

            # Pulsante di rimozione
            if st.button("🗑️ Rimuovi", key=f"del_{item['id']}"):
                # PATTERN: MODIFICA
                # Creiamo una nuova lista escludendo l'elemento da rimuovere
                wardrobe = [it for it in wardrobe if it["id"] != item["id"]]
                
                # PATTERN: SAVE
                save_json(WARDROBE_F, wardrobe)
                
                # Cancelliamo anche il file dell'immagine dal disco
                if img_path.exists():
                    img_path.unlink()
                    
                st.success("Capo rimosso!")

                st.rerun()


# STRUTTURA PRINCIPALE (INVARIATA)
def page_outfit():
    st.header("✨ Crea un Outfit")
    st.write("Questa pagina è in costruzione!")

def main():
    st.set_page_config(page_title="Armadio Digitale", page_icon="👗", layout="wide")
    st.title("👗 Armadio Digitale")
    pagina = st.sidebar.radio("Navigazione", ["👕 Armadio", "✨ Outfit"])
    if pagina == "👕 Armadio":
        page_armadio()
    else:
        page_outfit()

if __name__ == "__main__":
    main()