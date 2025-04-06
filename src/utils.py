# -*- coding: utf-8 -*-
# Copyright (c) 2025 Johannes Mäkinen
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import numpy_financial as npf


def get_latest_euribor():
    # Get the html webpage from https://www.euribor365.fi/
    url_ = 'https://www.euribor365.fi/'

    response = requests.get(url_)
    soup = BeautifulSoup(response.text, 'html.parser')
    # Find the relevant meta tag
    meta_tag = soup.find('meta', content=re.compile(r'Euribor 12 kk, 6 kk ja 3 kk -viitekorot tänään'))
    days_to_find = [
        datetime.today(),
        datetime.today() - pd.DateOffset(days=1),
        datetime.today() - pd.DateOffset(days=2),
    ]
    days_to_find = [d.strftime('%d.%m.%Y') for d in days_to_find]
    # Try to find the date in the content, then take the next 10 characters
    euribor = None
    if meta_tag:
        content = meta_tag['content']
        for d in days_to_find:
            if d in content:
                match = re.search(r'{}.*?(\d+,\d+)%'.format(d), content)
                if match:
                    euribor = float(match.group(1).replace(',', '.'))
                    print(f'Euribor for {d}: {euribor:.3f}%')
    return euribor


def get_apartment_info(url_):
    response = requests.get(url_)
    soup = BeautifulSoup(response.text, 'html.parser')
    street_address = soup.find('meta', property='og:street-address')['content']
    street_address
    price = soup.find('dt', string='Velaton hinta').find_next('dd').string
    price = float(re.sub(r'\D', '', price))
    vastike = soup.find('dt', string='Hoitovastike').find_next('dd').string
    vastike = vastike.replace(',', '.')
    vastike = float(re.sub(r'[^\d.,]', '', vastike))
    size = soup.find('dt', string='Asuinpinta-ala').find_next('dd').string
    size = float(re.sub(r'\D', '', size))
    room_count = soup.find('dt', string='Huoneita').find_next('dd').string
    room_count = int(room_count)
    floor = soup.find('dt', string='Kerros')
    if floor:
        floor = floor.find_next('dd').string
        floor = floor.split(' / ')[0]
        floor = int(floor)
    else:
        floor = 1

    building_year = soup.find('dt', string='Rakennusvuosi').find_next('dd').string
    building_year = int(building_year)
    building_type = soup.find('dt', string='Rakennuksen tyyppi').find_next('dd').string
    city_part = soup.find('dt', string='Kaupunginosa').find_next('dd').string
    muut_maksut = soup.find(string='Muut maksut					').find_next('dl')
    # find all numbers that have 'kk' in the string. Keep dt as the explanation, dd as the value
    muut_maksut = muut_maksut.find_all('div', class_='info-table__row')
    muut_maksut = [
        (m.find('dd').string, m.find('dt').string)
        for m in muut_maksut
        if 'kk' in m.find('dd').string or 'kuukau' in m.find('dd').string
    ]
    muut_splitted = []
    for m in muut_maksut:
        if '\n' in m[0]:
            # Split by \n
            split = m[0].split('\n')
            # Split by space
            split = [s.split(' ') for s in split]
            # Take the first and last element
            split = [(re.sub(r'\D', '', s[-1]), ' '.join(s[:-1])) for s in split]
            muut_splitted.extend(split)
        else:
            muut_splitted.append(m)
    # Format values (0) to floats, use regex
    muut_splitted = [(float(re.sub(r'\D', '', m[0])), m[1]) for m in muut_splitted if m[0] != '']

    # All costs to dict.
    costs = {
        'Vastike': vastike,
        'Velaton hinta': price,
        'Pinta-ala': size,
        'Huoneita': room_count,
        'Kerros': floor,
        'Rakennusvuosi': building_year,
        'Rakennuksen tyyppi': building_type,
        'Kaupunginosa': city_part,
        'Osoite': street_address,
    }
    for m in muut_splitted:
        costs["add_" + m[1]] = m[0]

    return costs


def plot_vakuus_tarve(cash=0):
    ylim_vakuus_tarve_list = []
    price_list = np.linspace(280000, 380000, 10000)
    for price in price_list:
        asunnon_hinta = price
        lainamäärä = asunnon_hinta - cash
        asu_vakuus_arvo = 0.7 * asunnon_hinta
        vakuus_tarve = lainamäärä - asu_vakuus_arvo
        valtiontakaus = min(0.2 * lainamäärä, 60000)
        ylim_vakuus_tarve = max(vakuus_tarve - valtiontakaus, 0)
        ylim_vakuus_tarve_list.append(ylim_vakuus_tarve)
    ylim_vakuus_tarve = np.array(ylim_vakuus_tarve_list)
    # find the first point where ylim_vakuus_tarve is not zero
    closest_index = np.where(ylim_vakuus_tarve > 0)[0][0] - 1
    # Take +- 20 points around the closest index
    N = 5000
    start_index = max(0, closest_index - N)
    end_index = min(len(ylim_vakuus_tarve), closest_index + N)
    ylim_vakuus_tarve = ylim_vakuus_tarve[start_index:end_index]
    closest_index = np.where(ylim_vakuus_tarve > 0)[0][0] - 1
    price_list = price_list[start_index:end_index]
    fig, ax = plt.subplots()
    ax.plot(price_list, ylim_vakuus_tarve)
    # Annotate the price where ylim_vakuus_tarve is zero
    ax.annotate(
        f'{price_list[closest_index]:,.0f} €',
        xy=(price_list[closest_index], ylim_vakuus_tarve[closest_index]),
        xytext=(price_list[closest_index], ylim_vakuus_tarve[closest_index] + 5000),
        arrowprops=dict(facecolor='black', arrowstyle='->'),
    )
    ax.axhline(0, color='red', linestyle='--')
    ax.set_xlabel('Asunnon hinta')
    ax.set_ylabel('Tarvitaan vakuuksia')
    return fig, closest_index, ylim_vakuus_tarve
