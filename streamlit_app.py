import streamlit as st
import pandas as pd
from google.cloud import firestore
from google.oauth2 import service_account
import json

key_dict = json.loads((st.secrets["textkey"]))
creds = service_account.Credentials.from_service_account_info(key_dict)




#-------------------------------------¡¡¡¡¡¡¡¡¡---------------------------------
# El checkbox para mostrar todos los registros esta hasta abajo para tener mayor
# claridad visual en el sidebar  
#-------------------------------------!!!!!!!!!---------------------------------

# ── Usa el cache para definir una funcion que guarda el cliente de Firestore ──
@st.cache_resource
def get_db():
    firestore.Client(credentials=creds, project="dashboardmovies-arturosoto")

# ── Usa el cache para definir una funcion que guarda una parte del csv ────────
@st.cache_data
def load_data(nrows=1000):
    db = get_db()
    docs = db.collection("movies").limit(nrows).stream()
    records = [doc.to_dict() for doc in docs]
    return pd.DataFrame(records)

# ── Usa el cache para definir una funcion que nos ayudara a obtener los ───────
# ── unicos de una columna esto sera usado mas adelante para los select box ────

@st.cache_data
def get_unique_values(column):
    docs = get_db().collection("movies").stream()
    values = sorted(set(
        doc.to_dict().get(column, "")
        for doc in docs
        if doc.to_dict().get(column)
    ))
    return values

# ── Se define el estado default de los filtros para usarlos ───────────────────
# ── en un pandas dataframe ────────────────────────────────────────────────────
def init_state():
    defaults = {
        "filtered_df":     pd.DataFrame(),
        "filters_applied": False,
        "applied_search":  "",
        "applied_director": "Todos",
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

def reset_filters():
    st.session_state.filtered_df     = pd.DataFrame()
    st.session_state.filters_applied = False
    st.session_state.applied_search  = ""
    st.session_state.applied_director = "Todos"

# ── Se inicializa la app ──────────────────────────────────────────────────────
db = get_db()
df_movies = load_data(2000)
df_movies_c = load_data()
init_state()
sidebar = st.sidebar
st.session_state.sidebar_state = 'collapsed'

# ── Se obtienen los unicos de las columnas de Firestore ───────────────────────
directors = ["Todos"] + get_unique_values("director")
companies = ["Seleccionar"] + get_unique_values("company")
genres    = ["Seleccionar"] + get_unique_values("genre")

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR — Filtros
# ─────────────────────────────────────────────────────────────────────────────
sidebar.header("Filtros")

search_query    = sidebar.text_input(
    "Título del filme",
    placeholder="Introduzca el nombre del filme...",
    help="Filtra por la columna 'name' (no distingue mayúsculas)"
)

selected_director = sidebar.selectbox(
    "Director",
    directors,
)

col_btn1, col_btn2 = sidebar.columns(2)
with col_btn1:
    apply = sidebar.button("▶ Buscar", type="primary", use_container_width=True)
with col_btn2:
    reset = sidebar.button("✖ Reset", type="secondary", use_container_width=True)

# ── Se resetean los filtros ───────────────────────────────────────────────────
if reset:
    reset_filters()
    #st.rerun() para quitar los valores escritos en los filtros

# ── Se aplican los filtros ────────────────────────────────────────────────────
if apply:
    filtered_df = df_movies.copy()

    if search_query:
        filtered_df = filtered_df[
            filtered_df["name"].astype(str).str.contains(search_query, case=False, na=False)
        ]

    if selected_director != "Todos":
        filtered_df = filtered_df[
            filtered_df["director"].astype(str) == selected_director
        ]

    st.session_state.filtered_df     = filtered_df
    st.session_state.filters_applied = True
    st.session_state.applied_search   = search_query
    st.session_state.applied_director = selected_director

sidebar.divider()

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR — Formato para nuevo filme
# ─────────────────────────────────────────────────────────────────────────────
sidebar.header("Agregar nuevo filme ")

new_name     = sidebar.text_input("Nombre",    key="input_name")
new_director = sidebar.selectbox("Director",   directors,  key="input_director")
new_company  = sidebar.selectbox("Compañía",   companies,  key="input_company")
new_genre    = sidebar.selectbox("Género",     genres,     key="input_genre")
submit       = sidebar.button("Crear nuevo filme")

if submit:
    if new_name and new_director != "Todos" and new_company != "Seleccionar" and new_genre != "Seleccionar":
        doc_ref = db.collection("movies").document(new_name)
        doc_ref.set({
            "name":     new_name,
            "director": new_director,
            "company":  new_company,
            "genre":    new_genre,
        })
        sidebar.success("Registro insertado correctamente")
        # Invalidate cache so new values appear in dropdowns next load
        get_unique_values.clear()
    else:
        sidebar.warning("¡Por favor completa todos los campos antes de guardar!")

# ─────────────────────────────────────────────────────────────────────────────
# MAIN — Display
# ─────────────────────────────────────────────────────────────────────────────
st.header("🎬 :red[Netflix] App")

# ── Muestra los resultados de los filtros ─────────────────────────────────────
if st.session_state.filters_applied:
    result_df = st.session_state.filtered_df
    st.subheader("Resultados de búsqueda")

    active = []
    if st.session_state.applied_search:
        active.append(f"nombre: **{st.session_state.applied_search}**")
    if st.session_state.applied_director != "Todos":
        active.append(f"director: **{st.session_state.applied_director}**")
    st.caption("Filtros activos — " + " | ".join(active) if active else "Sin filtros activos")

    if result_df.empty:
        st.info("No se encontraron coincidencias.")
    else:
        st.dataframe(result_df, use_container_width=True)
        st.caption(f"Mostrando {len(result_df)} de {len(df_movies)} registros")

st.divider()

# ── Muestra todos los registros ───────────────────────────────────────────────
agree = sidebar.checkbox("Mostrar todos los filmes")
if agree:
    st.subheader("Todos los filmes")
    with st.spinner("Cargando..."):
        st.dataframe(df_movies_c, use_container_width=True)
    st.caption(f"{len(df_movies_c)} registros cargados desde caché (total {len(df_movies_c)})")
