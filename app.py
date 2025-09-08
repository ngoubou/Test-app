import json
from typing import Dict, List
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import networkx as nx
import requests


st.set_page_config(page_title="IA et Transition Écologique – Démo", layout="wide")#st.set_page_config(page_title="Climat & Politiques Publiques – Démo", layout="wide")

# ---------------------------
# --------- THEME -----------
# ---------------------------
PRIMARY = "#0ea5e9"  # bleu doux
ACCENT = "#22c55e"   # vert
MUTED = "#94a3b8"    # gris

# ---------------------------
# ------ SIDEBAR / HELP -----
# ---------------------------
with st.sidebar:
    st.markdown("### Source de données")
    data_mode = st.radio(
        "Choisir la source",
        ["Données fictives", "Données en ligne", "Fichier (CSV/XLSX)"],#["Fictives", "Helsinki – PxWeb", "Fichier (CSV/XLSX)"],
        index=0
    )
    st.markdown("---")
    st.markdown("#### Aide / Docs")
    st.caption("• PxWeb Helsinki – guide API (POST JSON, limites, structure).")
    st.markdown(
        "[Documentation PxWeb Helsinki](https://stat.hel.fi/Resources/Images/PxWebAPI_Help_Helsinki_en.pdf)"
    )
    st.caption("• Indicateurs durables d’Helsinki (VLR, ≈60+ indicateurs).")
    st.markdown(
        "[Sustainable Helsinki – Indicators](https://kestavyys.hel.fi/en/indicators/)"
    )
    st.caption("• Données émissions/énergie HSY (téléchargeables en XLSX).")
    st.markdown(
        "[HSY – GES & bilans énergie/matériaux](https://hri.fi/data/en_GB/dataset/helsingin-seudun-ymparistopalvelujen-hsy-energia-ja-materiaalitaseet-seka-kasvihuonekaasupaastot/)"
    )
    st.markdown("---")
    #st.caption("Astuce : pour une démo, démarre en mode **Fictives**, puis montre "
     #          "comment passer à **Helsinki – PxWeb** ou **Fichier**.")

# ---------------------------
# --- FICTIVE DATA (DEFAULT)
# ---------------------------
def load_fictive_data():
    # Série temporelle 2020–2025 pour 3 actions et leurs indicateurs.
    years = list(range(2019, 2025))
    actions_time = {
        "Plantation d'arbres": {
            "Émissions CO₂ (t/an)": [1000, 980, 960, 940, 920, 900],
            "Surface verte (m²)": [5000, 5100, 5200, 5300, 5400, 5500],
        },
        "Lampadaires LED": {
            "Consommation énergie (kWh/an)": [20000, 18000, 16000, 14000, 13000, 12000],
            "Émissions CO₂ (t/an)": [800, 720, 640, 560, 520, 480],
        },
        "Compostage": {
            "Déchets en décharge (t/an)": [500, 480, 460, 440, 420, 400],
            "Économies (€/an)": [0, 1000, 2000, 3000, 4000, 5000],
        }
    }
    rows = []
    for action, inds in actions_time.items():
        for ind, vals in inds.items():
            for y, v in zip(years, vals):
                rows.append({"source": "Fictif", "action": action, "indicateur": ind, "annee": y, "valeur": v})
    return pd.DataFrame(rows), years, list(actions_time.keys())

# ---------------------------
# ------ PXWEB (HELSINKI) ---
# ---------------------------
@st.cache_data(show_spinner=False)
def pxweb_fetch(url: str, query: Dict) -> pd.DataFrame:
    """
    Interroge une table PxWeb en POST JSON et retourne un DataFrame aplati
    avec colonnes des variables + 'value'.

    NOTE: suivez la doc PxWeb Helsinki (codes variables, filtres).
    """
    r = requests.post(url, json=query, timeout=30)
    r.raise_for_status()
    j = r.json()

    # PxWeb peut renvoyer "json-stat" (liste de values + dimension labels).
    # On reconstruira un tableau long (tidy).
    # Format minimal : j['value'] + j['dimension'] -> catégories.
    values = j.get("value", [])
    dims = j.get("dimension", {})
    # Extraire les catégories (codes et labels) par dimension dans l'ordre
    dim_order = j.get("id", [])
    categories = []
    for dim_id in dim_order:
        dim = dims[dim_id]
        cats = dim["category"]["index"]  # mapping code -> position
        labels = dim["category"].get("label", {})
        # On garde l’ordre d’index
        sorted_codes = sorted(cats, key=lambda k: cats[k])
        categories.append((dim_id, sorted_codes, labels))

    # Produit cartésien des catégories -> chaque combinaison correspond à une valeur
    from itertools import product
    combos = list(product(*[codes for (_, codes, _) in categories]))

    rows = []
    for i, combo in enumerate(combos):
        row = {}
        for (dim_id, codes, labels), code_val in zip(categories, combo):
            row[dim_id] = labels.get(code_val, code_val)
        if i < len(values):
            row["value"] = values[i]
        else:
            row["value"] = None
        rows.append(row)

    return pd.DataFrame(rows)

def default_pxweb_example():
    """
    Exemple prêt-à-copier depuis la doc PxWeb Helsinki.
    ⚠️ A ADAPTER à ta table environnementale (voir API helper sur stat.hel.fi).

    Ici on montre la structure (Alue/Vuosi). Remplace l'URL et les codes variables
    par ceux de ta table (ex. indicateurs de durabilité / climat).
    """
    url = "https://stat.hel.fi:443/api/v1/fi/Ymparistotilasto/ene/kauen/ymp_kauen_002f.px"
    example_query = {
  "query": [
    {
      "code": "Tiedot",
      "selection": {
        "filter": "item",
        "values": [
          "määkpl"
        ]
      }
    }
  ],
  "response": {
    "format": "json-stat"
  }
}
    return url, example_query

# ---------------------------
# ------ FILE UPLOADER ------
# ---------------------------
def normalize_file(df: pd.DataFrame) -> pd.DataFrame:
    """
    Essaie de normaliser un fichier 'réel' en colonnes
    ['source','action','indicateur','annee','valeur'].
    Si colonnes inconnues, laisse l’utilisateur mapper via l’UI.
    """
    cols = [c.lower() for c in df.columns]
    df.columns = cols
    # Heuristiques fréquentes
    mapping = {}
    for c in df.columns:
        if c.startswith("annee") or c in ("year","annee","vuosi","vuodet"):
            mapping[c] = "annee"
        if c in ("valeur","value","arvo"):
            mapping[c] = "valeur"
        if "action" in c:
            mapping[c] = "action"
        if "indicateur" in c or "indicator" in c or "indik" in c:
            mapping[c] = "indicateur"

    df = df.rename(columns=mapping)
    if "annee" in df.columns and "valeur" in df.columns:
        if "action" not in df.columns:
            df["action"] = "Mesure réelle"
        if "indicateur" not in df.columns:
            # Essaie de trouver une colonne catégorielle pour l’indicateur
            cat_cols = [c for c in df.columns if c not in ("annee","valeur","action")]
            if cat_cols:
                df["indicateur"] = df[cat_cols[0]].astype(str)
            else:
                df["indicateur"] = "Indicateur"
        out = df[["action","indicateur","annee","valeur"]].copy()
        out["source"] = "Réel (fichier)"
        return out
    # sinon, on renverra brut et l’utilisateur mappera via l’UI (non implémenté ici pour aller vite)
    df["source"] = "Réel (fichier – brut)"
    return df

# ---------------------------
# ---- LOAD CHOSEN DATA -----
# ---------------------------
if data_mode == "Données fictives":
    df_long, YEARS, ACTIONS = load_fictive_data()

elif data_mode == "Données en ligne":
    st.info("⚙️ Mode **Helsinki – PxWeb** : adapte l’URL de table et la requête JSON. Tu peux obtenir les deux via le bouton “Ajouter le tableau à votre application / API helper” dans l’interface PxWeb d’Helsinki.", icon="ℹ️")
    url_default, q_default = default_pxweb_example()
    with st.expander("Paramètres de requête PxWeb (exemple)"):
        url_px = st.text_input("URL de la table PxWeb", value=url_default, help="Remplace par une table environnementale/indicateurs durables.")
        q_str = st.text_area("JSON de requête", value=json.dumps(q_default, indent=2))
        fmt = st.selectbox("Format de réponse", ["json-stat"], index=0)
    run = st.button("📡 Interroger PxWeb")
    if run:
        try:
            q = json.loads(q_str)
            q["response"] = {"format": fmt}
            df_px = pxweb_fetch(url_px, q)
            # Heuristique de normalisation : cherche colonnes temps/aire/indicateur
            # On renomme les colonnes les plus probables (Vuosi=année)
            rename_map = {}
            for c in df_px.columns:
                lc = c.lower()
                if "vuosi" in lc or "vuodet" in lc or "vuosi (year)" in lc:
                    rename_map[c] = "annee"
                if "alue" in lc:  # zone
                    rename_map[c] = "action"  # on le pose comme 'action' par défaut
                if "value" == lc:
                    rename_map[c] = "valeur"
            df_px = df_px.rename(columns=rename_map)
            # Ajoute indicateur si manquant
            if "indicateur" not in df_px.columns:
                df_px["indicateur"] = "Indicateur PxWeb"
            # Ajoute année si manquante
            if "annee" not in df_px.columns and "Vuosi" in df_px.columns:
                df_px = df_px.rename(columns={"Vuosi": "annee"})
            # Par sécurité, essaie de caster année
            if "annee" in df_px.columns:
                df_px["annee"] = pd.to_numeric(df_px["annee"], errors="coerce")
            df_px["source"] = "Réel (PxWeb)"
            # Construit df_long
            if not {"action","indicateur","annee","valeur"}.issubset(df_px.columns):
                # On tente une version minimale
                candidate_cols = [c for c in df_px.columns if c not in ("valeur","value")]
                if candidate_cols:
                    df_px["action"] = df_px[candidate_cols[0]].astype(str)
                if "valeur" not in df_px.columns and "value" in df_px.columns:
                    df_px["valeur"] = df_px["value"]
                if "annee" not in df_px.columns:
                    df_px["annee"] = pd.NA
                if "indicateur" not in df_px.columns:
                    df_px["indicateur"] = "Indicateur PxWeb"
            df_long = df_px[["source","action","indicateur","annee","valeur"]].dropna(subset=["valeur"]).copy()
        except Exception as e:
            st.error(f"Erreur PxWeb: {e}")
            st.stop()
    else:
        st.stop()

else:  # Fichier
    up = st.file_uploader("Dépose un CSV/XLSX (HSY ou autre)", type=["csv","xlsx"])
    if up is None:
        st.info("Télécharge un fichier HSY (émissions/énergie) ou tout autre open data en CSV/XLSX, puis re-lance.", icon="📄")
        st.stop()
    try:
        if up.name.lower().endswith(".csv"):
            raw = pd.read_csv(up)
        else:
            raw = pd.read_excel(up)
        df_long = normalize_file(raw)
    except Exception as e:
        st.error(f"Impossible de lire le fichier: {e}")
        st.stop()

# ---------------------------
# ----------- UI ------------
# ---------------------------
st.title("🌱 Démo IA et Transition Écologique")#st.title("🌱 Démo Climat & Politiques Publiques – Version Finale")
st.caption("Mode données : **{}**".format(data_mode))

# Choix actions (multi-sélection -> scénarios combinés)
actions = sorted(df_long["action"].dropna().unique())
default_actions = actions[:2] if len(actions) >= 2 else actions
selected_actions = st.multiselect("Sélectionne une ou plusieurs actions", actions, default=default_actions)

# Filtre années
years_all = sorted(df_long["annee"].dropna().unique())
if len(years_all) == 0:
    years_all = list(range(2019, 2025))
sel_years = st.slider("Plage d'années", int(min(years_all)), int(max(years_all)), (int(min(years_all)), int(max(years_all))))

df_view = df_long[
    df_long["action"].isin(selected_actions) &
    df_long["annee"].between(sel_years[0], sel_years[1], inclusive="both")
].copy()

# ---------------------------
# ---------- KPI ------------
# ---------------------------
def kpi_block(df: pd.DataFrame):
    kpis = []
    for ind in df["indicateur"].unique():
        dfi = df[df["indicateur"] == ind].groupby("annee", as_index=False)["valeur"].sum().sort_values("annee")
        if len(dfi) >= 2:
            v0 = dfi["valeur"].iloc[0]
            v1 = dfi["valeur"].iloc[-1]
            delta = v1 - v0
            pct = (delta / v0 * 100) if (v0 != 0 and pd.notna(v0)) else None
            kpis.append((ind, v0, v1, delta, pct))
    kpis = sorted(kpis, key=lambda t: abs(t[3]), reverse=True)[:3]
    cols = st.columns(max(1, len(kpis)))
    for c, (ind, v0, v1, d, p) in zip(cols, kpis):
        with c:
            trend = "↘︎" if d < 0 else "↗︎"
            color = ACCENT if d < 0 and ("CO₂" in ind or "Déchets" in ind or "Consommation" in ind) else PRIMARY
            # Gérer p None
            if p is None:
                pct_str = "N/A"
                sign = ""
            else:
                pct_str = f"{p:.1f}%"
                sign = "+" if p >= 0 else ""
            st.markdown(f"""
                <div style='padding:12px;border-radius:16px;border:1px solid {MUTED};'>
                    <div style='color:{MUTED};font-size:13px'>{ind}</div>
                    <div style='font-size:26px;font-weight:700'>{trend} {v1:,.0f}</div>
                    <div style='color:{color};font-size:13px'>vs {v0:,.0f} ({sign}{pct_str})</div>
                </div>
            """, unsafe_allow_html=True)


kpi_block(df_view)

# ---------------------------
# ----- TIMELINE CHART ------
# ---------------------------
st.subheader("📈 Évolution temporelle")
for ind in df_view["indicateur"].unique():
    dfi = df_view[df_view["indicateur"] == ind].groupby(["annee","action"], as_index=False)["valeur"].sum()
    fig = go.Figure()
    for act in dfi["action"].unique():
        dfa = dfi[dfi["action"] == act].sort_values("annee")
        fig.add_trace(go.Scatter(x=dfa["annee"], y=dfa["valeur"], mode="lines+markers", name=act))
    fig.update_layout(height=320, margin=dict(l=20,r=20,t=40,b=20), title=ind)
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------
# ---- SCÉNARIO PROJECTION --
# ---------------------------
st.subheader("🧭 Scénario (projection simple)")
colA, colB = st.columns(2)
with colA:
    intensite = st.slider("Intensité (%) appliquée sur la dernière année", 50, 200, 100)
with colB:
    st.caption("👉 Interprétation rapide : <100% = effort réduit, >100% = effort renforcé.")
df_last = df_view[df_view["annee"] == df_view["annee"].max()].copy()
df_last["proj"] = df_last["valeur"] * (intensite / 100.0)

st.dataframe(
    df_last[["action","indicateur","valeur","proj"]]
    .rename(columns={"valeur":"Récent (observé)","proj":"Projeté (scénario)"}),
    use_container_width=True
)


# ---------------------------
# ------ IMPACT NETWORK -----
st.subheader("🕸️ Réseau d’impacts (action → indicateur)")

# 1. Creer le graphe pondéré
G = nx.DiGraph()
for _, r in df_last.iterrows():
    weight = abs((r["proj"] or 0) - (r["valeur"] or 0))
    G.add_edge(r["action"], r["indicateur"], weight=weight)

# 2. Générer la mise en page
pos = nx.spring_layout(G, seed=42)

# 3. Créer une trace pour chaque lien pour permettre une épaisseur variable
edge_traces = []
for u, v, d in G.edges(data=True):
    x0, y0 = pos[u]
    x1, y1 = pos[v]
    thickness = d["weight"] * 5 + 1  # Facteur 5 pour visibilité, minimum 1
    trace = go.Scatter(
        x=[x0, x1], y=[y0, y1],
        mode="lines",
        line=dict(width=thickness, color="#888"),
        hoverinfo="none"
    )
    edge_traces.append(trace)

# 4. Préparer les nœuds avec deux couleurs distinctes
node_x, node_y, labels, node_colors = [], [], [], []
for node, (x, y) in pos.items():
    node_x.append(x)
    node_y.append(y)
    labels.append(node)
    if node in df_last["action"].values:
        node_colors.append('lightgreen')  # actions en vert
    else:
        node_colors.append('skyblue')     # indicateurs en bleu

node_trace = go.Scatter(
    x=node_x, y=node_y,
    mode="markers+text",
    text=labels,
    textposition="bottom center",
    marker=dict(size=28, color=node_colors, line=dict(width=2, color='#555'))
)

# 5. Construire et afficher la figure
fig_net = go.Figure(data=edge_traces + [node_trace])
fig_net.update_layout(
    height=360,
    showlegend=False,
    margin=dict(l=10, r=10, t=10, b=10)
)
st.plotly_chart(fig_net, use_container_width=True)



# ---------------------------
# --------- EXPORT ----------
# ---------------------------
st.download_button(
    "💾 Export CSV (vue filtrée)",
    data=df_view.to_csv(index=False).encode("utf-8"),
    file_name="vue_filtrée_demo_climat.csv",
    mime="text/csv"
)

# ---------------------------
# --------- FOOTER ----------
# ---------------------------
with st.expander("Notes"):#with st.expander("Notes pour la démo (à dire à l’oral)"):
    st.markdown("""
- Cette démo combine **pédagogie** (scénarios simples) et **capacité d’industrialisation** (API PxWeb, fichiers HSY/OD).
- Pour Vincennes : on peut **brancher des capteurs / formulaires / open data** et définir un **plan de collecte** (fréquences, qualité, métadonnées).
- L’outil se décline pour le **pilotage des politiques publiques**, l’**aménagement** (logement, mobilité) etc.
    """)

