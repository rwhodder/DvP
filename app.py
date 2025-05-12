import pandas as pd
import dash
from dash import html, dash_table
import dash_bootstrap_components as dbc

# Read & preprocess data
df = pd.read_csv("afl_player_stats.csv", skiprows=3)




# Calculate Disposals
df["disposals"] = df["kicks"] + df["handballs"]

# Fix 'INT' positions using player-wise forward fill (safe handling)
df['namedPosition'] = (
    df['namedPosition']
    .mask(df['namedPosition'] == 'INT')
    .groupby(df['player'])
    .transform('ffill')
)
df = df[df['namedPosition'].notna()]  # Drop rows that were never filled




# Define position groups
position_map = {
    "KeyF": ["FF", "CHF"],
    "GenF": ["HFFR", "HFFL", "FPL", "FPR"],
    "Ruck": ["RK"],
    "InsM": ["C", "RR", "R"],
    "Wing": ["WL", "WR"],
    "GenD": ["HBFL", "HBFR", "BPL", "BPR"],
    "KeyD": ["CHB", "FB"],
}
reverse_map = {pos: group for group, roles in position_map.items() for pos in roles}
df['PosGroup'] = df['namedPosition'].map(reverse_map)
df = df[df['PosGroup'].notna()]  # Drop if position not in map


# Function to build DvP DataFrame for a stat
def build_dvp(stat):
    grp = df.groupby(['opponent', 'PosGroup'])[stat].agg(['mean', 'count'])
    team_pos_counts = df.groupby(['opponent'])['PosGroup'].value_counts(normalize=True).rename("pct")
    merged = grp.join(team_pos_counts).reset_index()
    merged = merged.rename(columns={
        'opponent': 'Team', 'PosGroup': 'Position', 'mean': 'Avg', 'count': 'Count', 'pct': 'Pct'
    })
    merged['Pct'] = (merged['Pct'] * 100).round(0).astype(int)
    return merged

# Filter No-Go Zones for unders
def unders_matrix(dvp_df, stat_name):
    filtered = dvp_df[(dvp_df['Avg'] <= -1.0) & (dvp_df['Pct'] >= 40)].copy()
    filtered['Stat'] = stat_name
    filtered = filtered[['Team', 'Position', 'Avg', 'Pct', 'Stat']]
    return filtered


# Create matrices for each stat
dvp_marks = build_dvp('marks')
dvp_tackles = build_dvp('tackles')
dvp_disposals = build_dvp('disposals')

matrix = pd.concat([
    unders_matrix(dvp_marks, 'Marks'),
    unders_matrix(dvp_tackles, 'Tackles'),
    unders_matrix(dvp_disposals, 'Disposals'),
])


matrix['Avg'] = matrix['Avg'].round(2)
matrix['Pct'] = matrix['Pct'].astype(str) + "%"

# Dash App
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container([
    html.H2("🎯 Unders Targeting Matrix", className="mt-4 mb-3 text-primary"),
    dbc.Card([
        dbc.CardBody([
            dash_table.DataTable(
                columns=[
                    {"name": "Team", "id": "Team"},
                    {"name": "Position", "id": "Position"},
                    {"name": "Stat", "id": "Stat"},
                    {"name": "Avg DvP", "id": "Avg"},
                    {"name": "Sample %", "id": "Pct"},
                ],
                data=matrix.to_dict('records'),
                style_cell={"textAlign": "center", "padding": "8px"},
                style_header={"backgroundColor": "#f8f9fa", "fontWeight": "bold"},
                style_data_conditional=[
                    {
                        'if': {'column_id': 'Avg'},
                        'color': 'red'
                    },
                    {
                        'if': {'column_id': 'Pct'},
                        'color': 'gray'
                    }
                ],
                style_table={"overflowX": "auto"},
            )
        ])
    ], className="shadow p-3 mb-5 bg-white rounded")
], fluid=True)

if __name__ == "__main__":
    app.run(debug=True)
