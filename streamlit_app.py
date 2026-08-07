"""Root Streamlit launcher.

Keeping this file at the project root lets `streamlit run` resolve the `src`
package without requiring PYTHONPATH tweaks.
"""

from src.main import main


if __name__ == "__main__":
    main()
