import dash
from dash import dcc, html, Input, Output, State
import plotly.express as px
import pandas as pd
import base64
import io
from PIL import Image

# Initialize the app
app = dash.Dash(__name__)

# --- STYLING (The "Glass" Look) ---
app.layout = html.Div([
    # This div holds the background image
    html.Div(id='bg-container', style={
        'position': 'fixed', 'top': 0, 'left': 0, 'width': '100vw', 'height': '100vh',
        'zIndex': -1, 'backgroundSize': 'cover', 'backgroundPosition': 'center'
    }),
    
    # Sidebar
    html.Div([
        html.H2("🎨 Design Studio", style={'color': 'white'}),
        dcc.Upload(id='upload-image', children=html.Div(['Upload Scenery'])),
        html.Hr(),
        dcc.Upload(id='upload-data', children=html.Div(['Upload Dataset'])),
    ], id='sidebar', style={
        'width': '300px', 'height': '100vh', 'position': 'fixed', 
        'backgroundColor': '#0E1117', 'padding': '20px', 'color': 'white'
    }),

    # Main Content Area
    html.Div([
        html.Div(id='title-container', children=[
            html.H1("Data Narrative", id='main-title')
        ]),
        
        # The Glass Pane for the Graph
        html.Div(id='graph-pane', children=[
            dcc.Graph(id='main-graph', config={'displayModeBar': False})
        ])
    ], style={'marginLeft': '350px', 'padding': '50px'})
])

# --- LOGIC: Color Extraction & Theme Sync ---
@app.callback(
    [Output('bg-container', 'style'),
     Output('main-title', 'style'),
     Output('main-graph', 'figure')],
    [Input('upload-image', 'contents'),
     Input('upload-data', 'contents')],
    [State('upload-image', 'filename')]
)
def update_app(image_contents, data_contents, img_name):
    # Default fallback values
    bg_style = {'backgroundColor': '#0f172a'}
    title_style = {'color': 'white'}
    accent_color = "#00F2FF"
    
    if image_contents:
        # 1. Process Image and Extract Color
        content_type, content_string = image_contents.split(',')
        decoded = base64.b64decode(content_string)
        img = Image.open(io.BytesIO(decoded)).convert('RGB')
        
        # Get dominant color (Average of 1x1 resize)
        small_img = img.resize((1, 1), Image.Resampling.BILINEAR)
        r, g, b = small_img.getpixel((0, 0))
        accent_color = f'rgb({r}, {g}, {b})'
        
        # 2. Determine Text Color (Black or White)
        luminance = (0.2126*r + 0.7152*g + 0.0722*b) / 255
        text_color = "black" if luminance > 0.5 else "white"
        
        bg_style = {
            'backgroundImage': f'url({image_contents})',
            'backgroundSize': 'cover'
        }
        title_style = {'color': text_color, 'fontSize': '4rem', 'fontWeight': 'bold'}

    # 3. Create Graph
    fig = px.area(title="Upload data to see trend")
    if data_contents:
        # (Insert your pandas reading logic here)
        fig.update_traces(line_color=accent_color, fillcolor=accent_color)
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color="white")
    )

    return bg_style, title_style, fig

if __name__ == '__main__':
    app.run_server(debug=True)
