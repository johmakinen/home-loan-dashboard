# Streamlit app
# -*- coding: utf-8 -*-
# Copyright (c) 2025 Johannes Mäkinen

import streamlit as st
import sys, os
import numpy as np
import pandas as pd
import altair as alt
from pathlib import Path
import matplotlib.pyplot as plt
import numpy_financial as npf

# Add the src directory to the Python path
sys.path.append(os.path.abspath('src'))
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
from src.utils import get_latest_euribor, get_apartment_info, plot_vakuus_tarve

from collections import defaultdict

if 'known_apartments' not in st.session_state:
    # Initialize the known_apartments dictionary in session state
    st.session_state.known_apartments = defaultdict()


@st.cache_resource
def get_apartment_info_st(url_):
    return get_apartment_info(url_)


@st.cache_resource
def get_latest_euribor_st():
    return get_latest_euribor()


def click_button():
    st.session_state.clicked = True


if 'clicked' not in st.session_state:
    st.session_state.clicked = False
# Page configuration and styling
st.set_page_config(
    page_title="Home Loan Calculator",
    page_icon="🏠",
    layout="wide",
)


# Custom CSS for better styling
st.markdown(
    """
<style>
    .title {
        font-size: 42px;
        font-weight: bold;
        color: #1E88E5;
        margin-bottom: 20px;
    }
    .subtitle {
        font-size: 20px;
        color: #424242;
        margin-bottom: 30px;
    }
    .info-box {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .highlight {
        font-weight: bold;
        color: #1E88E5;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="title">Home Loan Calculator</div>
<div class="subtitle">Calculate your home loan details and monthly payments</div>
<div style='text-align: right; color: gray; font-size: 12px;'>© Johannes Mäkinen 2025</div>
""",
    unsafe_allow_html=True,
)


# Sidebar for inputs
with st.sidebar:
    st.header("Loan Parameters")
    url_to_apartment = st.text_input("🏠 URL to apartment listing")
    # Show known apartments
    with st.expander("Known Apartments", expanded=False):
        if st.session_state.known_apartments:
            for url, info in st.session_state.known_apartments.items():
                # Display the Osoite (address) and Velaton hinta (price)
                st.markdown(f"**{info.get('Osoite', 'N/A')}**: {info.get('Velaton hinta', '-9999'):.0f} €")
                st.markdown(f"****[Link]({url})***")

        else:
            st.markdown("No known apartments yet.")
    st.divider()
    # Manual override options
    manual_override_cost = st.checkbox("Manually enter apartment cost")
    manual_override_euribor = st.checkbox("Manually enter Euribor rate")

    if manual_override_cost:
        apartment_cost_manual = st.number_input("🏢 Apartment cost (€)", value=250000, min_value=0, step=1000)
        st.info("Manual values will override data fetched from URL")
    if manual_override_euribor:
        euribor_manual = st.number_input(
            "📊 Euribor rate (%)", value=3.5, min_value=0.0, max_value=20.0, step=0.1, format="%.2f"
        )
        st.info("Manual values will override data fetched from URL")
    col1, col2 = st.columns(2)
    with col1:
        cash = st.number_input(
            "💰 Cash available (€)", value=int(os.getenv('CURRENT_CASH', '10000')), min_value=0, step=100
        )
    with col2:
        marginal = st.number_input("💹 Loan margin (%)", value=0.4, min_value=0.0, step=0.01, format="%.2f")

    loan_time = st.slider("⏱️ Loan term (years)", min_value=5, max_value=30, value=25, step=1)

    st.info("Enter the URL to an apartment listing to automatically fetch property details.")

    calculate_button = st.button("Refresh", type="primary", on_click=click_button)


# Main content
if url_to_apartment and st.session_state.clicked:
    with st.spinner("Fetching apartment information..."):
        # Get the apartment info
        # Check if the URL is already in the known_apartments dictionary
        if url_to_apartment in st.session_state.known_apartments:
            apartment_info = st.session_state.known_apartments[url_to_apartment]
        else:
            # If not, fetch the info and add it to the dictionary
            apartment_info = get_apartment_info_st(url_to_apartment)
            st.session_state.known_apartments[url_to_apartment] = apartment_info

        euribor = get_latest_euribor_st()

    if apartment_info:
        apartment_cost = apartment_info['Velaton hinta']
        if manual_override_cost:
            apartment_cost = apartment_cost_manual
        korko = euribor
        if manual_override_euribor:
            korko = euribor_manual
        marginaali = marginal
        korko_yht = (korko + marginaali) / 100
        laina_aika = loan_time
        vastike = apartment_info['Vastike']

        # Calculations
        lainamäärä = apartment_cost - cash
        asu_vakuus_arvo = 0.7 * apartment_cost
        vakuus_tarve = lainamäärä - asu_vakuus_arvo
        valtiontakaus = min(0.2 * lainamäärä, 60000)
        ylim_vakuus_tarve = max(vakuus_tarve - valtiontakaus, 0)
        takausmaksu = 0.025 * valtiontakaus
        varainsiirtovero = 0.015 * apartment_cost
        kulut_yht = takausmaksu + varainsiirtovero
        # lisäkorko = extra_interest

        kuukausierä = npf.pmt(korko_yht / 12, laina_aika * 12, -lainamäärä)

        # Display results in a nice layout
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Property Details")
            st.metric("Location", apartment_info.get('Osoite', 'N/A'))
            st.metric("Property Price", f"{apartment_cost:,.0f} €")
            st.metric("Monthly Maintenance Fee", f"{vastike:,.0f} €")

            # Create a compact display of property details
            details = [
                f"**Area:** {apartment_info.get('Pinta-ala', 'N/A')} m²",
                f"**Year Built:** {apartment_info.get('Rakennusvuosi', 'N/A')}",
                f"**Building Type:** {apartment_info.get('Rakennuksen tyyppi', 'N/A')}",
                f"**Rooms:** {apartment_info.get('Huoneita', 'N/A')}",
                f"**Floor:** {apartment_info.get('Kerros', 'N/A')}",
            ]
            st.markdown(" | ".join(details), unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            st.subheader("Loan Information")
            # st.markdown('<div class="info-box">', unsafe_allow_html=True)

            # Display in a more organized way
            data = {
                "Description": [
                    "Purchase Price",
                    "Cash Available",
                    "Loan Amount",
                    "Property Collateral Value",
                    "Additional Collateral Needed",
                    "State Guarantee Amount",
                    "Extra Collateral Required",
                    "Guarantee Fee",
                    "Transfer Tax",
                    "Total Costs",
                ],
                "Amount (€)": [
                    apartment_cost,
                    cash,
                    lainamäärä,
                    asu_vakuus_arvo,
                    vakuus_tarve,
                    valtiontakaus,
                    ylim_vakuus_tarve,
                    takausmaksu,
                    varainsiirtovero,
                    kulut_yht,
                ],
            }

            # Create a styled dataframe
            df = pd.DataFrame(data)
            # Show the dataframe, use 0 decimals
            df['Amount (€)'] = df['Amount (€)'].apply(lambda x: f"{x:,.0f} €")
            df = df.style.set_properties(**{'text-align': 'left'})
            st.dataframe(df)

        # Monthly payment section
        st.subheader("Monthly Payment Details")
        payment_col1, payment_col2, payment_col3 = st.columns(3)

        with payment_col1:
            st.metric(
                "Interest Rate", f"{korko_yht*100:.2f}%", delta=f"Euribor {korko:.2f}% + Margin {marginaali:.2f}%"
            )

        with payment_col2:
            st.metric("Loan Term", f"{laina_aika} years")

        with payment_col3:
            st.metric(
                "Monthly Payment",
                f"{kuukausierä+vastike:,.0f} €",
                delta=f"Loan {kuukausierä:,.0f} € + Maintenance {vastike:,.0f} €",
            )
            # Additionals:
            # These have add_ prefix in the apartment_info dict
            if any(key.startswith("add_") for key in apartment_info):
                st.markdown("<small><b>Additional Monthly Costs:</b></small>", unsafe_allow_html=True)
                for key, value in apartment_info.items():
                    if key.startswith("add_"):
                        st.markdown(f"<small>• {key[4:]}: {value:,.0f} €</small>", unsafe_allow_html=True)

        st.metric("Monthly Payment per Person (2 people), excl. additionals", f"{((kuukausierä+vastike)/2):,.0f} €")
        st.markdown('</div>', unsafe_allow_html=True)

        # Amortization chart
        st.subheader("Loan Amortization Chart")
        periods = np.arange(1, laina_aika * 12 + 1)
        remaining_balance = np.zeros_like(periods, dtype=float)
        principal_payments = np.zeros_like(periods, dtype=float)
        interest_payments = np.zeros_like(periods, dtype=float)

        balance = lainamäärä
        for i, period in enumerate(periods):
            interest = balance * korko_yht / 12
            principal = kuukausierä - interest
            balance -= principal

            remaining_balance[i] = max(0, balance)
            principal_payments[i] = principal
            interest_payments[i] = interest

        chart_data = pd.DataFrame(
            {
                'Month': periods,
                'Remaining Balance': remaining_balance,
                'Principal Payment': principal_payments,
                'Interest Payment': interest_payments,
            }
        )

        # Convert months to years for x-axis
        chart_data['Year'] = chart_data['Month'] / 12

        chart = (
            alt.Chart(chart_data)
            .mark_line()
            .encode(
                x=alt.X('Year:Q', title='Year'),
                y=alt.Y('Remaining Balance:Q', title='Remaining Balance (€)'),
                tooltip=alt.Tooltip(
                    ['Year:Q', 'Remaining Balance:Q', 'Principal Payment:Q', 'Interest Payment:Q'], format='.1f'
                ),
            )
            .properties(width=800, height=400, title='Loan Amortization Schedule')
        )

        st.altair_chart(chart, use_container_width=True)

        # Raw data expander
        with st.expander("Property Raw Data", expanded=False):
            st.json(apartment_info)

    else:
        st.error("Could not retrieve apartment information. Please check the URL and try again.")
else:
    st.info("Enter the apartment listing URL in the sidebar and click 'Calculate Loan' to get started.")

    # Sample demonstration when no URL is provided
    st.subheader("How to use this calculator")
    st.write(
        """
    1. Enter the URL of an apartment listing to automatically fetch property details
    2. Adjust your available cash and other loan parameters
    3. Click 'Calculate Loan' to see detailed loan information
    4. Review monthly payments and other costs
    """
    )
    st.markdown('</div>', unsafe_allow_html=True)
