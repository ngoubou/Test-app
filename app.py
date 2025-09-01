import streamlit as st
import pandas as pd
import networkx as nx
import plotly.graph_objects as go

# --- 1. Charger les données ---
data = [
    {"action": "Plantation d'arbres", "indicateur": "Émissions CO₂ (t/an)", "avant": 1000, "apres": 950},
    {"action": "Plantation d'arbres", "indicateur": "Surface verte (m²)", "avant": 5000, "apres": 5100},
    {"action": "Lampadaires LED", "indicateur": "Consommation énergie (kWh/an)", "avant": 20000, "apres": 12000},
    {"action": "Lampadaires LED", "indicateur": "Émissions CO₂ (t/an)", "avant": 800, "apres": 480},
    {"action": "Compostage", "indicateur": "Déchets mis en décharge (t/an)", "avant": 500, "apres": 400},
    {"action": "Compostage", "indicateur": "Économies (€/an)", "avant": 0, "apres": 5000}
]
df = pd.DataFrame(data)

# --- 2. Titre & sélection ---
st.title("Démo interactive : Impact d'actions écologiques")
action = st.selectbox("Choisissez une action", df["action"].unique())

# --- 3. Slider pour moduler l'intensité de l'action ---
intensite = st.slider("Intensité de l’action (%)", 10, 200, 100)

# --- 4. Calcul des valeurs modifiées en fonction de l’intensité ---
subset = df[df["action"] == action].copy()
subset["apres_mod"] = subset["avant"] - (subset["avant"] - subset["apres"]) * (intensite / 100)

# --- 5. Affichage tableau avant / après modifié ---
st.subheader(f"Indicateurs pour : {action} (intensité {intensite} %)")
st.table(subset[["indicateur", "avant", "apres_mod"]].rename(columns={"apres_mod": "Après (modifié)"}))

# --- 6. Graphique barres ---
fig = go.Figure()
fig.add_trace(go.Bar(name="Avant", x=subset["indicateur"], y=subset["avant"], marker_color='lightblue'))
fig.add_trace(go.Bar(name="Après modifié", x=subset["indicateur"], y=subset["apres_mod"], marker_color='lightgreen'))
fig.update_layout(barmode='group', height=400, title="Avant vs. Après (intensité ajustée)")
st.plotly_chart(fig)

# --- 7. Réseau d'impacts (action → indicateur) ---
G = nx.DiGraph()
for _, row in subset.iterrows():
    G.add_edge(action, row["indicateur"], weight=abs(row["avant"] - row["apres_mod"]))

pos = nx.spring_layout(G, seed=42)
edge_x, edge_y = [], []
for u, v in G.edges():
    x0, y0 = pos[u]
    x1, y1 = pos[v]
    edge_x.extend([x0, x1, None])
    edge_y.extend([y0, y1, None])

edge_trace = go.Scatter(
    x=edge_x, y=edge_y, line=dict(width=2, color="gray"), hoverinfo="none", mode="lines"
)

node_x, node_y, labels = [], [], []
for node, coords in pos.items():
    x, y = coords
    node_x.append(x)
    node_y.append(y)
    labels.append(node)

node_trace = go.Scatter(
    x=node_x, y=node_y, mode="markers+text",
    text=labels, textposition="bottom center",
    marker=dict(size=30, color="lightgreen")
)

fig2 = go.Figure(data=[edge_trace, node_trace],
                 layout=go.Layout(title="Réseau d’impacts", height=400, showlegend=False))
st.plotly_chart(fig2)

# --- 8. Message de conclusion ---
st.markdown("""
**À venir :** intégration de données réelles (open data ville), enrichissement du graphique temporel, et possibilité de combiner plusieurs actions en un scénario global, pour donner un réel aperçu de type *Kausal / Climate Watch*.
""")
