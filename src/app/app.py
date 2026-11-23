from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st
from openpyxl import load_workbook


# ============================================================
# CONFIG
# ============================================================

EXCEL_FILE = Path(__file__).parent / "..//..//data//source//Book1.xlsx"

st.set_page_config(
    page_title="SimCompanies Data Manager",
    page_icon="📊",
    layout="wide"
)


# ============================================================
# EXCEL HELPERS
# ============================================================

def load_sheet(sheet_name):
    """Read a sheet from Excel."""
    return pd.read_excel(EXCEL_FILE, sheet_name=sheet_name)


def get_headers(ws):
    return [cell.value for cell in ws[1]]


def get_column_map(ws):
    return {
        name: index + 1
        for index, name in enumerate(get_headers(ws))
    }


def append_row(sheet_name, data):
    """Append one complete record to an Excel sheet."""

    wb = load_workbook(EXCEL_FILE)
    ws = wb[sheet_name]

    columns = get_column_map(ws)

    missing = set(data.keys()) - set(columns.keys())

    if missing:
        raise ValueError(
            f"Brak kolumn w arkuszu '{sheet_name}': {missing}"
        )

    # Calculate the row ONCE, not separately for each column.
    new_row = ws.max_row + 1

    for column_name, value in data.items():
        ws.cell(
            row=new_row,
            column=columns[column_name]
        ).value = value

    wb.save(EXCEL_FILE)

    # Refresh cached product data after changes.
    st.cache_data.clear()


# ============================================================
# PRODUCTS
# ============================================================

@st.cache_data
def load_products(file_modified):

    df = load_sheet("products")

    required = {
        "product_id",
        "name",
        "category"
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Brak kolumn w products: {missing}"
        )

    df = df.dropna(
        subset=["product_id", "name"]
    ).copy()

    df["product_id"] = df["product_id"].astype(int)
    df["name"] = df["name"].astype(str)
    df["category"] = df["category"].fillna("").astype(str)

    return df.sort_values("name")


def product_selector(label, key):

    products = load_products(
        EXCEL_FILE.stat().st_mtime
    )

    if products.empty:
        st.warning("Products sheet is empty.")
        return None

    # Display label -> product ID
    options = {
        f"{row['name']} | {row['category']} | ID {row['product_id']}":
            int(row["product_id"])
        for _, row in products.iterrows()
    }

    selected = st.selectbox(
        label,
        options=list(options.keys()),
        index=None,
        key=key,
        placeholder="Type the name..."
    )

    if selected is None:
        return None

    return options[selected]


def product_name(product_id):

    products = load_products(
        EXCEL_FILE.stat().st_mtime
    )

    result = products[
        products["product_id"] == product_id
    ]

    if result.empty:
        return f"Unknown ({product_id})"

    return result.iloc[0]["name"]


# ============================================================
# BUILDINGS
# ============================================================

def load_buildings():

    df = load_sheet("buildings")

    required = {
        "building_id",
        "name",
        "wage"
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"No columns in buildings: {missing}"
        )

    return df.dropna(subset=["name"]).copy()

def building_selector(label, key):

    buildings = load_buildings()

    if buildings.empty:
        st.warning(
            "Sheet buildings is empty. "
            "First add biuldings in Buildings tab."
        )
        return None

    options = {
        f"{row['name']} | ID {row['building_id']}":
            row["name"]
        for _, row in buildings.iterrows()
    }

    selected = st.selectbox(
        label,
        options=list(options.keys()),
        index=None,
        key=key,
        placeholder="Choose a building..."
    )

    if selected is None:
        return None

    return options[selected]


# ============================================================
# SAVE RECIPE
# ============================================================

def save_recipe(output_id, ingredients, replace_existing):

    wb = load_workbook(EXCEL_FILE)
    ws = wb["recipes"]

    columns = get_column_map(ws)

    required = {
        "product_id",
        "input_product_id",
        "quantity"
    }

    if not required.issubset(columns):
        raise ValueError(
            "recipes must contain: "
            "product_id, input_product_id, quantity"
        )

    # Remove existing recipe for this output product.
    if replace_existing:

        for row in range(ws.max_row, 1, -1):

            current_id = ws.cell(
                row,
                columns["product_id"]
            ).value

            if current_id is not None and int(current_id) == int(output_id):
                ws.delete_rows(row)

    # Add ingredients.
    for ingredient in ingredients:

        new_row = ws.max_row + 1

        ws.cell(
            new_row,
            columns["product_id"]
        ).value = output_id

        ws.cell(
            new_row,
            columns["input_product_id"]
        ).value = ingredient["input_product_id"]

        ws.cell(
            new_row,
            columns["quantity"]
        ).value = ingredient["quantity"]

    wb.save(EXCEL_FILE)
    st.cache_data.clear()


# ============================================================
# APP START
# ============================================================

if not EXCEL_FILE.exists():

    st.error(f"Could not find a file: {EXCEL_FILE}")
    st.stop()


st.title("📊 SimCompanies Data Manager")

st.caption(
    "Enter and manage gate data."
)


# ============================================================
# TABS
# ============================================================

tabs = st.tabs([
    "🧪 Recipes",
    "🏭 Production",
    "🏪 Retail",
    "🏢 Buildings",
    "🔍 Data Overview"
])


# ============================================================
# RECIPES
# ============================================================

with tabs[0]:

    st.header("Recipe Editor")

    if "recipe_ingredients" not in st.session_state:
        st.session_state.recipe_ingredients = []

    st.subheader("Final product")

    output_id = product_selector(
        "Output product",
        key="recipe_output_product"
    )

    # Prevent ingredients from accidentally being saved
    # for a different output product.
    if "recipe_editor_output_id" not in st.session_state:
        st.session_state.recipe_editor_output_id = output_id

    if output_id != st.session_state.recipe_editor_output_id:

        st.session_state.recipe_ingredients = []
        st.session_state.recipe_editor_output_id = output_id

    if output_id is not None:
        st.caption(f"Product ID: {output_id}")

    st.divider()

    st.subheader("Ingredients")

    col1, col2 = st.columns([3, 1])

    with col1:

        input_id = product_selector(
            "Input product",
            key="recipe_input_product"
        )

    with col2:

        quantity = st.number_input(
            "Quantity",
            min_value=0.001,
            value=1.0,
            step=1.0,
            key="recipe_quantity"
        )

    if st.button(
        "➕ Add ingredient",
        key="recipe_add_ingredient"
    ):

        if output_id is None:
            st.warning("First select final product.")

        elif input_id is None:
            st.warning("Select ingredient.")

        elif input_id == output_id:
            st.warning("Product cannot be itself ingredient.")

        elif any(
            x["input_product_id"] == input_id
            for x in st.session_state.recipe_ingredients
        ):
            st.warning("This ingredient is already choosen.")

        else:

            st.session_state.recipe_ingredients.append({
                "input_product_id": input_id,
                "name": product_name(input_id),
                "quantity": quantity
            })

            st.rerun()

    if st.session_state.recipe_ingredients:

        st.subheader("Current recipe")

        preview = pd.DataFrame([
            {
                "Product": x["name"],
                "Product ID": x["input_product_id"],
                "Quantity": x["quantity"]
            }
            for x in st.session_state.recipe_ingredients
        ])

        st.dataframe(
            preview,
            width="stretch",
            hide_index=True
        )

        if st.button(
            "🗑️ Clear recipe",
            key="recipe_clear"
        ):

            st.session_state.recipe_ingredients = []
            st.rerun()

        replace = st.checkbox(
            "Replace existing recipe",
            key="recipe_replace"
        )

        if st.button(
            "💾 Save recipe",
            type="primary",
            key="recipe_save"
        ):

            if output_id is None:
                st.warning("Select final product.")

            else:

                try:

                    save_recipe(
                        output_id,
                        st.session_state.recipe_ingredients,
                        replace
                    )

                    st.success("Recipe saved!")

                    st.session_state.recipe_ingredients = []

                    st.rerun()

                except PermissionError:
                    st.error("Close Book1.xlsx before save.")

                except Exception as error:
                    st.error(f"Saving error: {error}")


# ============================================================
# PRODUCTION
# ============================================================

with tabs[1]:

    st.header("Production")

    product_id = product_selector(
        "Product",
        key="production_product"
    )

    building = building_selector(
        "Building",
        key="production_building"
    )

    col1, col2 = st.columns(2)

    with col1:

        units_an_hour = st.number_input(
            "Units per hour",
            min_value=0.001,
            value=1.0,
            step=1.0,
            key="production_units_hour"
        )

    transport_unit = st.number_input(
        "Transport units per item",
        min_value=0.0,
        value=0.0,
        step=1.0,
        key="production_transport"
    )

    if st.button(
        "💾 Add production data",
        key="production_save"
    ):

        if product_id is None:
            st.warning("Choose product.")

        elif building is None:
            st.warning("Choose building.")

        else:

            try:

                append_row(
                    "production",
                    {
                        "product_id": product_id,
                        "building": building,
                        "units_an_hour": units_an_hour,
                        "transport_unit": transport_unit
                    }
                )

                st.success("Production data saved!")
                st.rerun()

            except PermissionError:
                st.error("Close Book1.xlsx before save.")

            except Exception as error:
                st.error(f"Saving error: {error}")


# ============================================================
# RETAIL
# ============================================================

with tabs[2]:

    st.header("Retail")

    product_id = product_selector(
        "Product",
        key="retail_product"
    )

    col1, col2 = st.columns(2)

    with col1:

        quality = st.number_input(
            "Quality",
            min_value=0,
            value=0,
            step=1,
            key="retail_quality"
        )

    with col2:

        retail_phase = st.selectbox(
            "Retail phase",
            [1, 2, 3],
            key="retail_phase"
        )

    col1, col2 = st.columns(2)

    with col1:

        price = st.number_input(
            "Retail price",
            min_value=0.0,
            value=0.0,
            step=0.1,
            key="retail_price"
        )

    with col2:

        sales_time = st.number_input(
            "Sales time",
            min_value=0.001,
            value=1.0,
            step=1.0,
            key="retail_sales_time"
        )

    if st.button(
        "💾 Add retail data",
        key="retail_save"
    ):

        if product_id is None:
            st.warning("Choose a product.")

        elif price <= 0:
            st.warning("Price must be greater than 0.")

        else:

            try:

                append_row(
                    "retail",
                    {
                        "product_id": product_id,
                        "quality": quality,
                        "retail_phase": retail_phase,
                        "price": price,
                        "sales_time": sales_time
                    }
                )

                st.success("Retail data saved!")
                st.rerun()

            except PermissionError:
                st.error("Close Book1.xlsx before save.")

            except Exception as error:
                st.error(f"Saving error: {error}")


# ============================================================
# BUILDINGS
# ============================================================

with tabs[3]:

    st.header("Buildings")

    building_name = st.text_input(
        "Building name",
        key="building_name"
    )

    wage = st.number_input(
        "Wage",
        min_value=0.0,
        value=0.0,
        step=0.1,
        key="building_wage"
    )

    if st.button(
        "💾 Add building",
        key="building_save"
    ):

        if not building_name.strip():

            st.warning("Type building name.")

        else:

            try:

                buildings = load_buildings()

                existing_names = (
                    buildings["name"]
                    .astype(str)
                    .str.strip()
                    .str.lower()
                    .values
                )

                if building_name.strip().lower() in existing_names:

                    st.warning("This building already exsists.")

                else:

                    existing_ids = pd.to_numeric(
                        buildings["building_id"],
                        errors="coerce"
                    ).dropna()

                    next_id = (
                        int(existing_ids.max()) + 1
                        if not existing_ids.empty
                        else 1
                    )

                    append_row(
                        "buildings",
                        {
                            "building_id": next_id,
                            "name": building_name.strip(),
                            "wage": wage
                        }
                    )

                    st.success(
                        f"Building saved! ID = {next_id}"
                    )

                    st.rerun()

            except PermissionError:
                st.error("Close Book1.xlsx before save.")

            except Exception as error:
                st.error(f"Saving error: {error}")

# ============================================================
# DATA OVERVIEW
# ============================================================

with tabs[4]:

    st.header("Data Overview")

    sheets = [
        "products",
        "recipes",
        "production",
        "retail",
        "buildings"
    ]

    for sheet in sheets:

        try:

            df = load_sheet(sheet)

            st.subheader(
                f"{sheet} — {len(df)} rows"
            )

            st.dataframe(
                df,
                width="stretch",
                hide_index=True
            )

        except Exception as error:

            st.error(f"{sheet}: {error}")