import streamlit as st
import pandas as pd
import networkx as nx
import plotly.graph_objects as go

# 1. Jeu de données fictives
data = [
    {"action": "Plantation d'arbres", "indicateur": "Émissions de CO₂ (t/an)", "avant": 1000, "apres": 950},
    {"action": "Plantation d'arbres", "indicateur": "Surface verte (m²)", "avant": 5000, "apres": 5100},
    {"action": "LED", "indicateur": "Consommation énergie (kWh/an)", "avant": 20000, "apres": 12000},
    {"action": "LED", "indicateur": "Émissions de CO₂ (t/an)", "avant": 800, "apres": 480},
    {"action": "Compostage", "indicateur": "Déchets mis en décharge (t/an)", "avant": 500, "apres": 400},
    {"action": "Compostage", "indicateur": "Économies coûts (€/an)", "avant": 0, "apres": 5000}
]
df = pd.DataFrame(data)

st.title("Démo : Impact des actions vertes")
action = st.selectbox("Sélectionnez une action", df["action"].unique())

# 2. Filtrer les indicateurs
subset = df[df["action"] == action]

st.subheader(f"Indicateurs pour : {action}")
st.write(subset[["indicateur", "avant", "apres"]])

# Graphique avant/après
fig = go.Figure()
fig.add_trace(go.Bar(name="Avant", x=subset["indicateur"], y=subset["avant"]))
fig.add_trace(go.Bar(name="Après", x=subset["indicateur"], y=subset["apres"]))
fig.update_layout(barmode='group', height=400)
st.plotly_chart(fig)

# 3. Réseau d'impacts
G = nx.DiGraph()
for _, row in subset.iterrows():
    G.add_edge(action, row["indicateur"], weight=row["avant"] - row["apres"])

pos = nx.spring_layout(G)
edge_x, edge_y = [], []
for u, v in G.edges():
    x0, y0 = pos[u]
    x1, y1 = pos[v]
    edge_x.extend([x0, x1, None])
    edge_y.extend([y0, y1, None])
edge_trace = go.Scatter(x=edge_x, y=edge_y, mode='lines', line=dict(width=2), hoverinfo='none')

node_x, node_y, labels = [], [], []
for node, coords in pos.items():
    x, y = coords
    node_x.append(x)
    node_y.append(y)
    labels.append(node)

node_trace = go.Scatter(
    x=node_x, y=node_y, mode='markers+text', text=labels,
    textposition='bottom center', marker=dict(size=20, color='lightgreen')
)

fig2 = go.Figure(data=[edge_trace, node_trace], layout=go.Layout(showlegend=False, height=400, title_text="Réseau d'impacts"))
st.plotly_chart(fig2)
