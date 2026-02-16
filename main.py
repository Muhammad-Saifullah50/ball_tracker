"""
Main entry point for Cricket Ball Tracker application
"""
import sys
from pathlib import Path
import os

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    import streamlit.web.cli as stcli

    # Set the working directory to project root
    os.chdir(project_root)

    # Run the main Streamlit app
    sys.argv = ["streamlit", "run", "src/ui/app.py", "--server.address", "0.0.0.0", "--server.port", "5000"]
    sys.exit(stcli.main())
