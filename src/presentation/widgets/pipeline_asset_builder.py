import os

class PipelineAssetBuilder:
    """
    Utility for assembling the Modularized HTML/CSS/JS for the QWebEngineView.
    Injects the initial state JSON so the flowchart paints its status on load.
    """
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.pipeline_dir = os.path.join(self.base_dir, "web_assets", "pipeline")

    def build_html(self, state_json: str) -> str:
        """Reads the modular templates and injects the runtime state."""
        try:
            with open(os.path.join(self.pipeline_dir, "pipeline.css"), "r", encoding="utf-8") as f:
                css_content = f.read()
            with open(os.path.join(self.pipeline_dir, "pipeline.js"), "r", encoding="utf-8") as f:
                js_content = f.read()
            with open(os.path.join(self.pipeline_dir, "pipeline_template.html"), "r", encoding="utf-8") as f:
                html_template = f.read()
        except Exception as e:
            return f"<html><body>Error loading pipeline assets: {e}</body></html>"

        # The state injection script
        state_injection = f"""
        const INITIAL_STATE = {state_json if state_json else "{}"};
        document.addEventListener('DOMContentLoaded', () => {{
            if (window.setPipelineState) {{
                window.setPipelineState(INITIAL_STATE);
            }}
        }});
        """

        # Replace placeholders in template
        combined_html = html_template.replace("/* INJECT_CSS */", css_content)
        combined_js = js_content + "\n" + state_injection
        combined_html = combined_html.replace("/* INJECT_JS */", combined_js)

        return combined_html
