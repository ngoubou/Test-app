import streamlit as st
import pandas as pd
import networkx as nx
import plotly.graph_objects as go

# --- 1. Définir les données fictives temporelles ---
years = list(range(2020, 2026))
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

df_time = []
for action, inds in actions_time.items():
    for ind, vals in inds.items():
        for year, val in zip(years, vals):
            df_time.append({"action": action, "indicateur": ind, "année": year, "valeur": val})
df_time = pd.DataFrame(df_time)

# --- 2. UI ---
st.title("Démo interactive Climat")
actions = df_time["action"].unique()
action = st.selectbox("Choisissez une action", actions)
years_selected = st.multiselect("Années à afficher", years, default=years)

# Filtrer données
subset = df_time[(df_time["action"] == action) & (df_time["année"].isin(years_selected))]

# --- 3. Visualisation temporelle ---
st.subheader(f"Évolution sur la période (action = {action})")
for ind in subset["indicateur"].unique():
    df_ind = subset[subset["indicateur"] == ind]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_ind["année"], y=df_ind["valeur"], mode="lines+markers", name=ind))
    fig.update_layout(title=ind, height=300)
    st.plotly_chart(fig)

# --- 4. Slider pour scénario (intensité future) ---
intensite = st.slider("Projection future (intensité % pour année supplémentaire)", 50, 200, 100)
last_year = max(years_selected)
proj_vals = []
for ind in actions_time[action]:
    base = actions_time[action][ind][-1]
    new = base * intensite / 100
    proj_vals.append({"indicateur": ind, "valeur projetée": new})

df_proj = pd.DataFrame(proj_vals)
st.table(df_proj)

# --- 5. Insight Network pour dernière année + projection ---
G = nx.DiGraph()
for _, row in df_proj.iterrows():
    G.add_edge(action, row["indicateur"], weight=row["valeur projetée"])

pos = nx.spring_layout(G, seed=42)
edge_x, edge_y = [], []
for u, v in G.edges():
    x0, y0 = pos[u]; x1, y1 = pos[v]
    edge_x += [x0, x1, None]; edge_y += [y0, y1, None]

edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=2, color="gray"), hoverinfo="none", mode="lines")
node_x, node_y, labels = [], [], []
for node, coords in pos.items():
    node_x.append(coords[0]); node_y.append(coords[1]); labels.append(node)

node_trace = go.Scatter(x=node_x, y=node_y, mode="markers+text", text=labels, textposition="bottom center",
                        marker=dict(size=30, color="lightgreen"))
fig_net = go.Figure(data=[edge_trace, node_trace], layout=go.Layout(title="Insight Network", height=400, showlegend=False))
st.plotly_chart(fig_net)

st.markdown("""
**Et après ?**  
- Ajouter données réelles (énergie, CO₂, végétalisation…) depuis open data.  
- Permettre la sélection de **scénarios combinés d'actions**.  
- Rendre l'apparence plus professionnelle (layout, visuels, badges impact).
""")
