from __future__ import annotations

import io
import math
from pathlib import Path
from typing import Dict, List

import pandas as pd
import streamlit as st

from scraper import CATEGORIES, clean_records, dedupe_records, scrape_category

# Matplotlib est utilise pour le diagramme circulaire.
# Si la dependance manque, on affiche un fallback.
try:  # noqa: BLE001
    import matplotlib.pyplot as plt
except Exception:  # noqa: BLE001
    plt = None

DATA_DIR = Path(__file__).resolve().parent / "data"
SAMPLE_RAW_PATH = DATA_DIR / "web_scraper_raw.csv"
DEFAULT_FORM_URL = "https://ee.kobotoolbox.org/x/UUtyFL64"


# Verifie la presence du fichier d'exemple Web Scraper.
def ensure_sample_file() -> None:
    if not SAMPLE_RAW_PATH.exists():
        raise FileNotFoundError(
            "Sample Web Scraper file not found at "
            f"{SAMPLE_RAW_PATH}. Please add it to the data folder."
        )


# Charge les donnees brutes (non nettoyees).
def load_sample_raw() -> pd.DataFrame:
    ensure_sample_file()
    raw_df = pd.read_csv(SAMPLE_RAW_PATH)
    return expand_sample_df(raw_df, target_rows=3000)


# Duplique l'echantillon pour obtenir assez de lignes.
def expand_sample_df(df: pd.DataFrame, target_rows: int = 3000) -> pd.DataFrame:
    if len(df) >= target_rows:
        return df

    base = df.copy().reset_index(drop=True)
    batches = []
    total = len(base)
    repeat = math.ceil(target_rows / max(total, 1))

    for i in range(repeat):
        batch = base.copy()
        if i > 0:
            suffix = f" (lot {i + 1})"
            batch["adresse"] = batch["adresse"].astype(str) + suffix
            batch["image_lien"] = batch["image_lien"].astype(str).str.replace(
                ".jpg",
                f"_{i + 1}.jpg",
                regex=False,
            )
        batches.append(batch)

    expanded = pd.concat(batches, ignore_index=True).head(target_rows)
    return expanded


# Convertit un DataFrame en CSV telechargeable.
def csv_download(df: pd.DataFrame) -> bytes:
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")


# Cache pour eviter de relancer le scraping inutilement.
@st.cache_data(show_spinner=False)
def scrape_multiple(categories: List[str], pages: int) -> pd.DataFrame:
    records: List[Dict[str, str]] = []
    for key in categories:
        meta = CATEGORIES[key]
        items = scrape_category(meta["url"], meta["type"], pages=pages)
        for item in items:
            item["categorie"] = key
        records.extend(items)
    return pd.DataFrame(records)


def main() -> None:
    # Configuration principale de la page.
    st.set_page_config(page_title="CoinAfrique Scraper", layout="wide")
    st.title("CoinAfrique Scraper et Dashboard")
    st.caption(
        "Scraping multi-pages avec BeautifulSoup, telechargement "
        "Web Scraper, dashboard nettoye, et formulaire d'evaluation."
    )

    tabs = st.tabs(
        [
            "Scraping BeautifulSoup",
            "Web Scraper (raw)",
            "Dashboard (nettoye)",
            "Evaluation",
        ]
    )

    with tabs[0]:
        st.subheader("Scraper et nettoyer (BeautifulSoup)")
        st.write(
            "Selectionnez des categories, puis indiquez le nombre de pages "
            "a scraper. Les donnees sont nettoyees apres extraction."
        )

        options = list(CATEGORIES.keys())
        selected = st.multiselect(
            "Categories",
            options=options,
            default=options[:2],
            format_func=lambda key: CATEGORIES[key]["label"],
        )
        pages = st.number_input("Nombre de pages", min_value=1, max_value=20, value=2)
        show_raw = st.checkbox("Afficher aussi les donnees brutes", value=False)

        if st.button("Lancer le scraping", type="primary"):
            if not selected:
                st.warning("Veuillez choisir au moins une categorie.")
            else:
                try:
                    with st.spinner("Scraping en cours..."):
                        raw_df = scrape_multiple(selected, int(pages))
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Echec du scraping: {exc}")
                    raw_df = pd.DataFrame()
                if raw_df.empty:
                    st.error("Aucune annonce trouvee. Essayez avec plus de pages.")
                else:
                    # Nettoyage et suppression des doublons.
                    cleaned = clean_records(raw_df.to_dict(orient="records"))
                    cleaned = dedupe_records(cleaned)
                    cleaned_df = pd.DataFrame(cleaned)

                    st.success(f"{len(cleaned_df)} lignes nettoyees.")
                    st.dataframe(cleaned_df, use_container_width=True)

                    if show_raw:
                        st.markdown("**Donnees brutes**")
                        st.dataframe(raw_df, use_container_width=True)

                    st.download_button(
                        "Telecharger les donnees nettoyees (CSV)",
                        data=csv_download(cleaned_df),
                        file_name="coinafrique_clean.csv",
                        mime="text/csv",
                    )

    with tabs[1]:
        st.subheader("Telecharger des donnees Web Scraper (non nettoyees)")
        st.write(
            "Chargez un export CSV de Web Scraper (non nettoye). "
            "Vous pouvez aussi telecharger un exemple."
        )

        sample_df = load_sample_raw()
        st.download_button(
            "Telecharger l'exemple Web Scraper (CSV)",
            data=csv_download(sample_df),
            file_name="web_scraper_raw.csv",
            mime="text/csv",
        )

        uploaded = st.file_uploader("Importer un CSV Web Scraper", type=["csv"])
        if uploaded is not None:
            raw_df = pd.read_csv(uploaded)
            st.session_state["raw_webscraper_df"] = raw_df
            st.success(f"{len(raw_df)} lignes chargees.")
            st.dataframe(raw_df, use_container_width=True)
        else:
            st.session_state["raw_webscraper_df"] = sample_df
            st.dataframe(sample_df, use_container_width=True)

    with tabs[2]:
        st.subheader("Dashboard des donnees nettoyees (Web Scraper)")
        # Recuperation des donnees brutes depuis l'etat ou le fichier exemple.
        raw_df = st.session_state.get("raw_webscraper_df", load_sample_raw())

        cleaned = clean_records(raw_df.to_dict(orient="records"))
        cleaned = dedupe_records(cleaned)
        cleaned_df = pd.DataFrame(cleaned)

        # Sidebar pour les filtres.
        st.sidebar.header("Filtres du dashboard")
        st.sidebar.caption("Les filtres s'appliquent aux donnees nettoyees.")

        if cleaned_df.empty:
            st.sidebar.info("Aucune donnee a filtrer.")
            st.warning("Aucune donnee disponible pour le dashboard.")
        else:
            # Filtres de base: type, adresse, prix.
            available_types = (
                cleaned_df["type"].dropna().unique().tolist()
                if "type" in cleaned_df
                else []
            )
            selected_types = st.sidebar.multiselect(
                "Type",
                options=available_types,
                default=available_types,
            )
            address_query = st.sidebar.text_input("Recherche adresse")
            include_no_price = st.sidebar.checkbox(
                "Inclure annonces sans prix", value=True
            )

            filtered_df = cleaned_df.copy()
            if selected_types:
                filtered_df = filtered_df[filtered_df["type"].isin(selected_types)]
            if address_query:
                filtered_df = filtered_df[
                    filtered_df["adresse"].str.contains(
                        address_query, case=False, na=False
                    )
                ]

            price_series = filtered_df["prix"].dropna()
            if not price_series.empty:
                min_price = int(price_series.min())
                max_price = int(price_series.max())
                if min_price == max_price:
                    min_price = max(0, min_price - 1)
                    max_price = max_price + 1
                price_range = st.sidebar.slider(
                    "Prix (FCFA)",
                    min_value=min_price,
                    max_value=max_price,
                    value=(min_price, max_price),
                )
                if include_no_price:
                    price_mask = filtered_df["prix"].between(*price_range) | filtered_df[
                        "prix"
                    ].isna()
                else:
                    price_mask = filtered_df["prix"].between(*price_range)
                filtered_df = filtered_df[price_mask]
            elif not include_no_price:
                filtered_df = filtered_df[filtered_df["prix"].notna()]

            if filtered_df.empty:
                st.warning("Aucune donnee apres filtrage.")
            else:
                col1, col2, col3 = st.columns(3)
                col1.metric("Total annonces", len(filtered_df))
                col2.metric(
                    "Prix moyen (FCFA)",
                    int(price_series.mean()) if not price_series.empty else 0,
                )
                col3.metric("Annonces sans prix", int(filtered_df["prix"].isna().sum()))

                st.markdown("**Prix moyen par type**")
                price_by_type = (
                    filtered_df.dropna(subset=["prix"])
                    .groupby("type", dropna=False)["prix"]
                    .mean()
                    .sort_values(ascending=False)
                )
                st.bar_chart(price_by_type)

                # Diagramme circulaire pour la repartition par type.
                st.markdown("**Repartition des annonces par type**")
                type_counts = (
                    filtered_df["type"]
                    .fillna("inconnu")
                    .value_counts()
                    .rename_axis("type")
                    .to_frame("nb")
                )
                if plt is None:
                    st.info(
                        "Matplotlib n'est pas installe. "
                        "Diagramme circulaire remplace par un histogramme."
                    )
                    st.bar_chart(type_counts)
                else:
                    fig, ax = plt.subplots()
                    ax.pie(
                        type_counts["nb"],
                        labels=type_counts.index,
                        autopct="%1.0f%%",
                        startangle=90,
                    )
                    ax.axis("equal")
                    st.pyplot(fig, use_container_width=True)

                st.markdown("**Apercu des donnees nettoyees**")
                st.dataframe(filtered_df, use_container_width=True)

                st.download_button(
                    "Telecharger les donnees nettoyees (CSV)",
                    data=csv_download(filtered_df),
                    file_name="web_scraper_clean.csv",
                    mime="text/csv",
                )

    with tabs[3]:
        st.subheader("Formulaire d'evaluation")
        st.write("Veuillez remplir ce formulaire pour nous aider a ameliorer le service.")
        # Masquer le lien dans l'interface.
        form_url = st.text_input(
            "Lien du formulaire (masque)", value=DEFAULT_FORM_URL, type="password"
        )
        if form_url:
            st.link_button("Ouvrir le formulaire", form_url)


if __name__ == "__main__":
    main()
