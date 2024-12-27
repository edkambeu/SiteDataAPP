import dash
from dash import dcc, html, dash_table, Input, Output, State
import pandas as pd
import io
import base64
import plotly.graph_objs as go
import webbrowser

# Initialize the Dash app
app = dash.Dash(__name__)

# App layout
app.layout = html.Div([
    html.H1("Upload and Visualize Site Data", style={'textAlign': 'center'}),
    
    # Upload and clear buttons on the same line
    html.Div([
        dcc.Upload(
            id='upload-data',
            children=html.Button('Upload Data', style={'fontSize': '16px'}),
            style={
                'marginRight': '10px',  # Space between buttons
            },
            multiple=False
        ),
        html.Button('Clear Data', id='clear-data', style={'fontSize': '16px'}),
    ], style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center', 'marginBottom': '20px'}),
    
    # Layout for data tables and plot
    html.Div([
        # Left side- Raw data and transformed data
        html.Div([
            # Raw Data Section
            html.Div([
                html.H3("Raw Data", style={'textAlign': 'center', 'marginBottom': '10px'}),
                html.Div(id='output-data-table', style={
                    'maxHeight': '200px',
                    'overflowY': 'auto',
                    'border': '1px solid #ccc',
                    'padding': '10px',
                    'backgroundColor': '#f9f9f9'
                }),
            ], style={'marginBottom': '20px'}),  # Space between sections

            # Transformed Data Section
            html.Div([
                html.H3("Transformed Data", style={'textAlign': 'center', 'marginBottom': '10px'}),
                html.Div(id='pivot-table', style={
                    'maxHeight': '200px',
                    'overflowY': 'auto',
                    'border': '1px solid #ccc',
                    'padding': '10px',
                    'backgroundColor': '#f9f9f9'
                }),
            ]),
            html.Button('Download Transformed Data', id='download-button', style={'marginTop': '10px'}),
            dcc.Download(id='download-pivot'),
        ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top', 'paddingRight': '10px'}),
        
        # Right side -Plot and dropdown
        html.Div([
            dcc.Dropdown(
                id='station-selector',
                multi=True,
                placeholder="Select stations to plot",
                style={'marginBottom': '10px'}
            ),
            dcc.Graph(id='line-plot', style={'height': '600px'}),
        ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'})
    ]),
])

# Helper function to parse uploaded files
def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    
    if filename.endswith('.csv'):
        return pd.read_csv(io.StringIO(decoded.decode('utf-8')))
    elif filename.endswith('.xls') or filename.endswith('.xlsx'):
        return pd.read_excel(io.BytesIO(decoded))
    else:
        return None

# Callbacks for uploading, clearing data  and transformation of the data
@app.callback(
    [Output('station-selector', 'options'),
     Output('output-data-table', 'children'),
     Output('pivot-table', 'children'),
     Output('station-selector', 'value'),
     Output('line-plot', 'figure')],
    [Input('upload-data', 'contents'),
     Input('clear-data', 'n_clicks'),
     Input('station-selector', 'value')],
    [State('upload-data', 'filename')]
)
def update_data_and_plot(contents, clear_clicks, selected_stations, filename):
    ctx = dash.callback_context
    trigger = ctx.triggered[0]['prop_id'].split('.')[0]

    # Handle Clear Data button
    if trigger == 'clear-data':
        return [], html.Div(["No file uploaded."]), html.Div(["No transformed data."]), None, go.Figure()

    # Handle Upload Data
    if contents is None:
        return [], html.Div(["No file uploaded yet."]), html.Div(["No transformed data."]), None, go.Figure()

    # Parse uploaded file
    data = parse_contents(contents, filename)
    if data is None:
        return [], html.Div(["Unsupported file type. Please upload a CSV or Excel file."]), html.Div(["No transformed data."]), None, go.Figure()

    # Ensure required columns exist
    if not all(col in data.columns for col in ['Depth', 'Station', 'EPD']):
        return [], html.Div(["File must contain 'Depth', 'Station', and 'EPD' columns."]), html.Div(["No transformed data."]), None, go.Figure()

    # Display raw data
    raw_data_table = dash_table.DataTable(
        data=data.to_dict('records'),
        columns=[{'name': col, 'id': col} for col in data.columns],
        style_table={'maxHeight': '200px', 'overflowY': 'auto'},
        style_header={'backgroundColor': 'lightgrey', 'fontWeight': 'bold'},
        style_cell={'textAlign': 'left'}
    )

    # Create pivot table
    pivot_table = data.pivot(index='Depth', columns='Station', values='EPD')
    pivot_table = pivot_table.sort_index(ascending=True)

    # Convert column names to strings
    pivot_table.columns = pivot_table.columns.map(str)

    transformed_data_table = dash_table.DataTable(
        data=pivot_table.reset_index().to_dict('records'),
        columns=[{'name': str(col), 'id': str(col)} for col in ['Depth'] + list(pivot_table.columns)],
        style_table={'maxHeight': '200px', 'overflowY': 'auto'},
        style_header={'backgroundColor': 'lightgrey', 'fontWeight': 'bold'},
        style_cell={'textAlign': 'left'}
    )

    # Populate dropdown options with station names
    station_options = [{'label': str(col), 'value': col} for col in pivot_table.columns]

    # Handle plotting if stations are selected
    if selected_stations:
        fig = go.Figure()
        for station in selected_stations:
            if station in pivot_table.columns:
                fig.add_trace(go.Scatter(
                    x=pivot_table[station],
                    y=pivot_table.index,
                    mode='lines+markers',
                    name=f'Station {station}',
                    line=dict(
                    shape='spline',  
                    smoothing=1.3,   
                    width=2,         
                )
                ))

        fig.update_layout(
            title='Line Graph of Depth vs EPD for Selected Stations',
            xaxis_title='EPD (mV)',
            yaxis_title='Depth (m)',
            legend_title='Station',
            plot_bgcolor ='white',
            xaxis=dict(
        tickmode='linear',  
        tick0=0,           
        dtick=0.1,         
        showgrid=True,     
        gridcolor='lightgrey', 
        minor=dict(
            ticklen=4,           
            tickcolor="gray",    
            showgrid=False       
        ),
        side = 'top' 
    ),
    yaxis=dict(
        tick0=0,
        dtick = 50,
        minor=dict(
            ticklen=4,           
            tickcolor="gray",    
            showgrid=False       
        ),
        showgrid=True,          
        gridcolor='lightgrey',  
    )

        )
        return station_options, raw_data_table, transformed_data_table, selected_stations, fig

    return station_options, raw_data_table, transformed_data_table, None, go.Figure()

# Callback to handle pivot table download
@app.callback(
    Output('download-pivot', 'data'),
    Input('download-button', 'n_clicks'),
    [State('upload-data', 'contents'), State('upload-data', 'filename')]
)
def download_transformed_data(n_clicks, contents, filename):
    if n_clicks and contents:
        data = parse_contents(contents, filename)
        if data is None:
            return None

        # Create pivot table
        pivot_table = data.pivot(index='Depth', columns='Station', values='EPD')
        pivot_table.columns = pivot_table.columns.map(str)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            pivot_table.to_excel(writer, sheet_name='Pivot Table')

        buffer.seek(0)
        return dcc.send_bytes(buffer.read(), filename="transformed_data.xlsx")
    return None

# Run the app
if __name__ == '__main__':
    webbrowser.open('http://127.0.0.1:8050/', new=2) 
    app.run_server(debug=True)
