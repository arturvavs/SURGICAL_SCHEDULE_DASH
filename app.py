import os
from dash import Dash

app = Dash(__name__,pages_folder='pages', use_pages=True, suppress_callback_exceptions=True,  assets_folder='assets')
server=app.server

#FLASK_SERVER_PORT= os.environ.get('FLASK_SERVER_PORT') 
if __name__ == "__main__":
    app.run_server(host='0.0.0.0', port='8051', debug=True, dev_tools_ui=False)