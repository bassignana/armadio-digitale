import streamlit as st

def page_armadio():
    st.header("👕 Il mio Armadio")
    
    uploaded_file = st.file_uploader(
        "Carica una foto del capo",
        type=["jpg", "jpeg", "png", "webp"]
    )
    
    if uploaded_file is not None:
        st.image(uploaded_file, caption="Immagine caricata", width=250)

def page_outfit():
    st.header("✨ Crea un Outfit")
    st.write("Questa pagina è in costruzione!")

# Struttura Principale dell'App
def main():
    
    st.set_page_config(page_title="Armadio Digitale", page_icon="👗", layout="centered")

    st.title("👗 Armadio Digitale")

    st.sidebar.title("Navigazione")
    
    pagina_selezionata = st.sidebar.radio(
        "Scegli una pagina:",
        ["👕 Armadio", "✨ Outfit"]
    )

    if pagina_selezionata == "👕 Armadio":
        page_armadio()
    elif pagina_selezionata == "✨ Outfit":
        page_outfit()


main()