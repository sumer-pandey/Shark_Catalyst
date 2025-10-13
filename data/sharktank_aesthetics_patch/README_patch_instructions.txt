Shark Tank Aesthetics Patch
===========================

Files included:
- .streamlit/config.toml          -> Streamlit theme config
- assets/custom.css               -> CSS overrides & accessibility tweaks
- patches/updated_utils.py        -> Replacement utils.py (adds Plotly theme helper)
- patches/updated_app.py          -> Replacement app.py (injects CSS & applies Plotly theme)

Instructions (exact steps):
1) Backup your repo:
   - Copy your current files (app.py, utils.py) before replacing.
     e.g.: cp app.py app.py.bak
            cp utils.py utils.py.bak

2) Copy files from the patch into your project root:
   - Move .streamlit/config.toml to the .streamlit/ folder at repo root.
   - Move assets/custom.css to assets/custom.css at repo root.
   - Replace utils.py with patches/updated_utils.py (overwrite).
   - Replace app.py with patches/updated_app.py (overwrite).

   Example commands (run from your repo root):
   mkdir -p .streamlit assets
   cp /path/to/patch/.streamlit/config.toml .streamlit/config.toml
   cp /path/to/patch/assets/custom.css assets/custom.css
   cp /path/to/patch/patches/updated_utils.py utils.py
   cp /path/to/patch/patches/updated_app.py app.py

3) Install font (optional):
   - The theme uses 'Inter'. If you want exact font locally, install Inter or let browser fallback.

4) Restart the app:
   streamlit run app.py

5) Verify:
   - Header + CTA styling, KPI card visuals, plotly theme, and footer should reflect the new theme.
   - If you see errors, restore backups and paste the error message here.

Notes:
- These are presentation-only changes. No database alterations.
- If your project structure differs (e.g., app entrypoint is not app.py), adapt accordingly.

If you want, I can create a zip of this patch and provide a download link — tell me and I'll provide it.