"""
This module provides functions for loading and analyzing FMI snow cover data

Dataset can be dowloaded from Paituli: https://paituli.csc.fi/download.html?data_id=il_daily_snow_10km_geotiff_euref

This dataset by Finnish Meteorological institute is licensed under a Creative Commons Attribution 4.0
International License (CC BY 4.0)
"""
__author__ = "Marcelo Mouta"


import rioxarray as rxr
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
from rasterio.errors import RasterioIOError


def open_snow_year_raster(raster_dir, year):
    """Open FMI snow depth raster for a given year"""
    
    raster_file = raster_dir /  f"snow_{year}.tif"
    year_raster = rxr.open_rasterio(raster_file, masked=True)

    # CRS should be in ETRS-TM35FIN (EPSG:3067)
    year_raster.rio.write_crs("EPSG:3067", inplace=True)

    return year_raster


def open_snow_rasters(raster_dir, start_year=1961, end_year=2022, missing_data=False):
    """
    Return dictionary with all snow depth rasters in given year interval

    Args:
        raster_dir (str | Path): path for the snow depth rasters
        start_year (int, optional): Start year of the interval, minimum is 1961. Defaults to 1961.
        end_year (int, optional): End year of the interval. Defaults to 2022.
        missing_data (bool): If True, omits IO errors when raster files are missing. Defaults to False.

    Returns:
        dict[int, DataArray]: dictionary keyed by year with snow depth rasters as values

    Raises:
        ValueError: If start_year and end_year do not form a valid interval within 1961-2022
    """

    # year range for which snow depth data is available [1961-2022]
    if start_year < 1961 or end_year < start_year:
        raise ValueError("start_year and end_year do not form a valid interval within 1961-2022")

    # year interval for which snow data will be retrieved
    year_interval = range(start_year, end_year+1)

    # dict of snow rasters keyed by year
    snow_rasters = {}

    for year in year_interval:
        try:
            snow_rasters[year] = open_snow_year_raster(raster_dir, year)
        
        except RasterioIOError as e:
            # If data is not expected to be missing, print IO error
            if not missing_data:
                print(e)
        

    return snow_rasters


def xmas_average(year_raster):
    """
    Returns raster with 24-26 December average snow depth given year raster
    """

    # Get rasters for Christmas days (24-26) December
    xmas_eve = year_raster.isel(band=-8) # day 24.12
    xmas_day = year_raster.isel(band=-7) # day 25.12
    boxing_day = year_raster.isel(band=-6) # day 26.12

    # average snow depth over christmas days
    xmas_average = (xmas_eve + xmas_day + boxing_day) / 3
    return xmas_average


def xmas_snow_rasters(snow_rasters):
    """"Return dictionary with Christmas average snow rasters given snow rasters dictionary"""

    xmas_snow = dict()

    for year in snow_rasters.keys():
        xmas_snow[year] = xmas_average(snow_rasters[year])
    
    return xmas_snow
        

def classify_white_xmas(xmas_year_raster, snow_threshold=1):
    """
    Classify White Christmas given raster with christmas average snow for that year
    """

    if snow_threshold <= 0:
        raise ValueError("snow_threshold must be bigger than 0")

    # Define the bins
    bins = [0, snow_threshold, np.inf]

    # Apply the reclassification
    reclassified_raster = np.digitize(xmas_year_raster, bins)

    # Retain NaN values by ensuring they are not reclassified
    reclassified_raster = np.where(~np.isnan(xmas_year_raster), reclassified_raster, np.nan)

    # Convert to an xarray DataArray
    reclassified_raster = xr.DataArray(
        reclassified_raster,
        dims=xmas_year_raster.dims,  # Keep the same dimensions
        coords=xmas_year_raster.coords,  # Retain the spatial coordinates
        attrs=xmas_year_raster.attrs  # Preserve the original attributes
    )
    return reclassified_raster


def plot_white_xmas(reclassified_raster, year, snow_threshold=1):
    """
    Plot White Christmas map given reclassified raster for that year
    """

    # Reproject raster for better map visualisation
    plot_raster = reclassified_raster.rio.reproject(dst_crs="EPSG:3857")

    # Plot using xarray's plot method
    plot = plot_raster.plot(cmap=plt.matplotlib.colors.ListedColormap(['dimgray', 'lightblue']), figsize=(6,6))

    # Set only the classification ticks on the colorbar
    colorbar = plot.colorbar
    ticks = get_tick_locations(colorbar.get_ticks())
    labels = ['No Snow', f'Snow present \n(at least {snow_threshold}cm)']
    colorbar.set_ticks(ticks, labels=labels)
    colorbar.set_label("Snow Classification")

    # disable all other axis, lines and ticks
    plt.axis('off')

    plt.title(f"White Christmas {year}")
    plt.show()

def get_tick_locations(ticks):
    """Calculate tick locations at 1/4 and 3/4 of the classification scale"""
    start = ticks[0]
    end = ticks[-1]
    diff = end - start

    return [start + diff/4, end - diff/4]