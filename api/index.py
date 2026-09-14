import os
import sys

# Ensure root directory is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web import flask_app as app

if __name__ == "__main__":
    app.run()
