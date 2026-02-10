#!/usr/bin/env python3
"""
Streamlit interface for City Map Poster Generator.

This app reuses the existing CLI rendering pipeline from create_map_poster.py.
"""

from __future__ import annotations

import contextlib
import io
from pathlib import Path

import streamlit as st

import create_map_poster as poster


@st.cache_data(show_spinner=False)
def get_available_themes() -> list[str]:
    """Fetch and cache available theme names from disk."""
    return poster.get_available_themes()


def get_default_theme(themes: list[str]) -> str:
    """Return a sensible default theme."""
    if not themes:
        return ""
    if "terracotta" in themes:
        return "terracotta"
    return themes[0]


def get_mime_type(output_format: str) -> str:
    """Map output format to download MIME type."""
    return {
        "png": "image/png",
        "svg": "image/svg+xml",
        "pdf": "application/pdf",
    }.get(output_format, "application/octet-stream")


def render_result() -> None:
    """Render latest generation result stored in session state."""
    result = st.session_state.get("latest_result")
    if not result:
        return

    output_path = Path(result["path"])
    output_format = result["format"]
    output_bytes = result["bytes"]

    st.success(f"Poster generated: `{output_path}`")

    if output_format == "png":
        st.image(output_bytes, caption=output_path.name, use_container_width=True)
    else:
        st.info("Preview is shown for PNG output. Use download for SVG/PDF.")

    st.download_button(
        label="Download poster",
        data=output_bytes,
        file_name=output_path.name,
        mime=get_mime_type(output_format),
        use_container_width=True,
    )

    logs = st.session_state.get("latest_logs", "")
    if logs:
        with st.expander("Generation logs"):
            st.code(logs)


def main() -> None:
    """Render Streamlit page and handle poster generation."""
    st.set_page_config(page_title="City Map Poster Generator", layout="wide")
    st.title("City Map Poster Generator")
    st.caption(
        "Generate map posters from OpenStreetMap data with the same rendering engine as the CLI script."
    )

    themes = get_available_themes()
    if not themes:
        st.error("No themes found in the `themes/` directory.")
        st.stop()

    default_theme = get_default_theme(themes)
    default_theme_index = themes.index(default_theme) if default_theme in themes else 0

    with st.sidebar:
        st.header("Poster settings")
        city = st.text_input("City", value="Paris")
        country = st.text_input("Country", value="France")

        use_custom_coordinates = st.checkbox("Use custom coordinates", value=False)
        lat = None
        lon = None
        if use_custom_coordinates:
            lat = st.number_input("Latitude", value=48.8566, format="%.6f")
            lon = st.number_input("Longitude", value=2.3522, format="%.6f")

        theme_name = st.selectbox("Theme", options=themes, index=default_theme_index)
        distance = st.slider(
            "Map radius (meters)",
            min_value=1000,
            max_value=50000,
            value=18000,
            step=500,
        )

        dim_col1, dim_col2 = st.columns(2)
        with dim_col1:
            width = st.number_input(
                "Width (inches)",
                min_value=2.0,
                max_value=20.0,
                value=12.0,
                step=0.5,
            )
        with dim_col2:
            height = st.number_input(
                "Height (inches)",
                min_value=2.0,
                max_value=20.0,
                value=16.0,
                step=0.5,
            )

        output_format = st.selectbox("Output format", options=["png", "svg", "pdf"], index=0)

        st.subheader("Optional labels")
        display_city = st.text_input("Display city", value="")
        display_country = st.text_input("Display country", value="")

        st.subheader("Typography")
        font_family = st.text_input("Google Font family", value="", placeholder="Noto Sans JP")

        generate = st.button("Generate poster", type="primary", use_container_width=True)

    st.markdown(
        """
        **Tips**
        - Large radii can take longer and use more memory.
        - Use PNG for a quick preview, SVG/PDF for scalable print output.
        - Non-Latin labels work best with an explicit Google Font family.
        """
    )

    if generate:
        if not city.strip() or not country.strip():
            st.error("City and country are required.")
            st.stop()

        logs_buffer = io.StringIO()

        try:
            with st.spinner("Generating poster..."):
                with contextlib.redirect_stdout(logs_buffer), contextlib.redirect_stderr(logs_buffer):
                    if use_custom_coordinates:
                        point = (float(lat), float(lon))
                    else:
                        point = poster.get_coordinates(city.strip(), country.strip())

                    custom_fonts = None
                    if font_family.strip():
                        custom_fonts = poster.load_fonts(font_family.strip())

                    poster.THEME = poster.load_theme(theme_name)
                    output_file = poster.generate_output_filename(city.strip(), theme_name, output_format)
                    poster.create_poster(
                        city=city.strip(),
                        country=country.strip(),
                        point=point,
                        dist=distance,
                        output_file=output_file,
                        output_format=output_format,
                        width=float(width),
                        height=float(height),
                        display_city=display_city.strip() or None,
                        display_country=display_country.strip() or None,
                        fonts=custom_fonts,
                    )

                output_path = Path(output_file)
                output_bytes = output_path.read_bytes()
                output_path.unlink()  # Clean up the file immediately
                st.session_state["latest_result"] = {
                    "path": str(output_path),
                    "bytes": output_bytes,
                    "format": output_format,
                }
                st.session_state["latest_logs"] = logs_buffer.getvalue()
        except Exception as exc:
            st.error(f"Generation failed: {exc}")
            with st.expander("Error details"):
                st.code(logs_buffer.getvalue())

    render_result()


if __name__ == "__main__":
    main()
