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


def check_year_interval(start_year, end_year):
    """
    Check if given interval is within year range for which snow depth data is available

    Raises:
        ValueError: If start_year and end_year do not form a valid interval within 1961-2022
    """
    if start_year < 1961 or end_year < start_year:
        raise ValueError("start_year and end_year do not form a valid interval within 1961-2022")


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
    # check if given interval is valid
    check_year_interval(start_year, end_year)

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


def xmas_average_snow(year_raster):
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


def xmas_avg_snow_rasters(snow_rasters):
    """"Return dictionary with Christmas average snow rasters given snow rasters dictionary"""

    xmas_snow = dict()

    for year in snow_rasters.keys():
        xmas_snow[year] = xmas_average_snow(snow_rasters[year])
    
    return xmas_snow


def classify_white_day(snow_day_raster, snow_threshold=1):
    """
    Classify day as white given snow raster for single day (or day average)

    Args:
        snow_day_raster (DataArray): raster with snow depth cover for that day (or day average)
        snow_threshold (int, optional): Snow depth threshold (in cm) for day to be considered white.
            Defaults to 1.

    Returns:
        DataArray: Reclassified raster with classes 0 for no-snow and 1 for white day 

    """
    if snow_threshold <= 0:
        raise ValueError("snow_threshold must be bigger than 0")

    # Define 2 bins: no-snow and white day
    bins = [0, snow_threshold, np.inf]

    # Reclassify the raster with 2 snow categories
    reclassified = reclassify_raster(snow_day_raster, bins)

    # change classification values from [1,2] to [0,1]
    reclassified -= 1
    
    return reclassified


def classify_all_white_xmas(year_raster, snow_threshold=1):
    """
    Classify Christmas (24.-26.12) as white if all 3 days are white

    Args:
        year_raster (DataArray): raster with year snow depth cover
        snow_threshold (int, optional): Snow depth threshold (in cm) for day to be considered white.
            Defaults to 1.

    Returns:
        DataArray: Reclassified raster with class 1 for all white christmas and class 0 otherwise 
    """

    xmas_days_indices = [-8, -7, -6] # indices for 24-26 December

    xmas_rasters = []
    for i in xmas_days_indices:
        xmas_day_raster = year_raster.isel(band=i)
        white_xmas_day = classify_white_day(xmas_day_raster, snow_threshold)
        xmas_rasters.append(white_xmas_day)

    return xmas_rasters[0] * xmas_rasters[1] * xmas_rasters[2]


def white_xmas_avg_sum(xmas_avg_snow, start_year=1991, end_year=2020, snow_threshold=1):
    """
    Classify and sum white christmas occurrences over given year period.
    Christmas is classified as white if average snow depth
    of 3 christmas days (24-26) is bigger than given threshold.

    Args:
        xmas_avg_snow (dict[int, DataArray]): dictionary keyed by year with christmas average snow depth rasters as values.
        start_year (int, optional): Start year of the interval, minimum is 1961. Defaults to 1991.
        end_year (int, optional): End year of the interval. Defaults to 2020.
        snow_threshold (int, optional): Snow depth threshold (in cm) for day to be considered white.
            Defaults to 1.

    Returns:
        DataArray: raster containing the sum of white christmas over given period
    """
    # check if given interval is valid
    check_year_interval(start_year, end_year)

    white_xmas_sum = classify_white_day(xmas_avg_snow[start_year], snow_threshold)
    for year in range(start_year+1, end_year+1):
       white_xmas_sum += classify_white_day(xmas_avg_snow[year], snow_threshold)

    return white_xmas_sum
    

def white_xmas_all3_sum(snow_rasters, start_year=1991, end_year=2020, snow_threshold=1):
    """
    Classify and sum white christmas occurrences over given year period.
    Christmas is classified as white only if all 3 christmas days (24-26) were white.

    Args:
        snow_rasters (dict[int, DataArray]): dictionary keyed by year with snow depth rasters as values.
        start_year (int, optional): Start year of the interval, minimum is 1961. Defaults to 1991.
        end_year (int, optional): End year of the interval. Defaults to 2020.
        snow_threshold (int, optional): Snow depth threshold in cm for day to be considered white.
            Defaults to 1.

    Returns:
        DataArray: raster containing the sum of white christmas over given period
    """
    # check if given interval is valid
    check_year_interval(start_year, end_year)

    white_xmas_sum = classify_all_white_xmas(snow_rasters[start_year], snow_threshold)
    for year in range(start_year+1, end_year+1):
       white_xmas_sum += classify_all_white_xmas(snow_rasters[year], snow_threshold)

    return white_xmas_sum


def classify_prob_white_xmas(xmas_sum_raster):
    """
    Classify probability of white Christmas over 10 years

    This classification mimics the one used in the first map of this FMI statistics:
    https://en.ilmatieteenlaitos.fi/christmas-weather 
    
    Args:
        xmas_sum_raster (DataArray): raster containing the counts of white christmas over 10-year period

    Returns:
        DataArray: reclassified raster with 5 probability classes of white Christmas ocurrence
    """
    
    # Define the bins
    bins = [0, 6, 8.3, 9.3, 9.7, 10]

    return reclassify_raster(xmas_sum_raster, bins)


def reclassify_raster(raster, bins):

    # Apply the reclassification
    reclassified = np.digitize(raster, bins)

    # Retain NaN values by ensuring they are not reclassified
    reclassified = np.where(~np.isnan(raster), reclassified, np.nan)

    # Convert to an xarray DataArray
    reclassified = xr.DataArray(
        reclassified,
        dims=raster.dims,  # Keep the same dimensions
        coords=raster.coords,  # Retain the spatial coordinates
        attrs=raster.attrs  # Preserve the original attributes
    )
    return reclassified


def plot_prob_white_xmas(reclassified_raster, start_year, end_year):

    # Reproject raster for better map visualisation
    plot_raster = reproject_map(reclassified_raster)
    
    # create custom cmap
    custom_cmap = plt.matplotlib.colors.ListedColormap(['yellow', 'lightblue', "tab:blue", 'darkslateblue', 'midnightblue'])
    
    # Plot using xarray's plot method
    plot = plot_raster.plot(cmap=custom_cmap, figsize=(6,6))
    plt.axis('off')
    plt.title(f"Probability of White Christmas in Finland {start_year}-{end_year}")
    plt.show()


def plot_white_xmas(reclassified_raster, year, snow_threshold=1):
    """
    Plot White Christmas map given reclassified raster for that year
    """

    # Reproject raster for better map visualisation
    plot_raster = plot_raster = reproject_map(reclassified_raster)

    # create custom cmap
    snow_cmap = plt.matplotlib.colors.ListedColormap(['dimgray', 'lightblue'])
    
    # Plot using xarray's plot method
    plot = plot_raster.plot(cmap=snow_cmap, figsize=(6,6))

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


def reproject_map(raster, crs="EPSG:3857"):
    return raster.rio.reproject(dst_crs=crs)


def get_tick_locations(ticks):
    """Calculate tick locations at 1/4 and 3/4 of the classification scale"""
    start = ticks[0]
    end = ticks[-1]
    diff = end - start

    return [start + diff/4, end - diff/4]