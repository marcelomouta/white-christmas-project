"""
This module provides functions for loading and analyzing Finnish Meteorological Institute (FMI) snow cover data.

A special focus is given to "White Christmas" analysis, for which several classification and
plotting functions are included.

Dataset can be dowloaded from Paituli:
    https://paituli.csc.fi/download.html?data_id=il_daily_snow_10km_geotiff_euref

This dataset by Finnish Meteorological institute is licensed under a Creative Commons Attribution 4.0
International License (CC BY 4.0)
"""
__author__ = "Marcelo Mouta"

import snow_utils as utils
import rioxarray as rxr
import numpy as np
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
    # check if given interval is valid
    utils.check_year_interval(start_year, end_year)

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


def average_xmas_snow(year_raster):
    """
    Returns raster with average snow depth in 24-26 December given year raster
    """

    # Get rasters for Christmas days (24-26) December
    xmas_eve = year_raster.isel(band=-8) # day 24.12
    xmas_day = year_raster.isel(band=-7) # day 25.12
    boxing_day = year_raster.isel(band=-6) # day 26.12

    # average snow depth over christmas days
    xmas_average = (xmas_eve + xmas_day + boxing_day) / 3
    return xmas_average


def avg_xmas_snow_rasters(snow_rasters):
    """"Return dictionary with average Christmas snow rasters given snow rasters dictionary"""

    avg_xmas_snow = dict()

    for year in snow_rasters.keys():
        avg_xmas_snow[year] = average_xmas_snow(snow_rasters[year])
    
    return avg_xmas_snow


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
    reclassified = utils.reclassify_raster(snow_day_raster, bins)

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


def white_avg_xmas_sum(avg_xmas_snow, start_year=1991, end_year=2020, snow_threshold=1):
    """
    Classify and sum white christmas occurrences over given year period.
    Christmas is classified as white if average snow depth
    of 3 christmas days (24-26) is bigger than given threshold.

    Args:
        avg_xmas_snow (dict[int, DataArray]): dictionary keyed by year with average christmas snow depth rasters as values.
        start_year (int, optional): Start year of the interval, minimum is 1961. Defaults to 1991.
        end_year (int, optional): End year of the interval. Defaults to 2020.
        snow_threshold (int, optional): Snow depth threshold (in cm) for day to be considered white.
            Defaults to 1.

    Returns:
        DataArray: raster containing the sum of white christmas over given period
    """
    # check if given interval is valid
    utils.check_year_interval(start_year, end_year)

    white_xmas_sum = classify_white_day(avg_xmas_snow[start_year], snow_threshold)
    for year in range(start_year+1, end_year+1):
       white_xmas_sum += classify_white_day(avg_xmas_snow[year], snow_threshold)

    return white_xmas_sum
    

def all3_white_xmas_sum(snow_rasters, start_year=1991, end_year=2020, snow_threshold=1):
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
    utils.check_year_interval(start_year, end_year)

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

    return utils.reclassify_raster(xmas_sum_raster, bins)


def plot_white_xmas(white_xmas_raster, year, snow_threshold=1, borders=None):
    """
    Plot White Christmas map given reclassified raster for that year
    """

    # create custom cmap
    snow_cmap = plt.matplotlib.colors.ListedColormap(['dimgray', 'lightblue'])

    fig, ax = plt.subplots(figsize=(6, 6))
    
    # Plot using xarray's plot method
    plot = white_xmas_raster.plot.imshow(ax=ax, cmap=snow_cmap, vmin=0, vmax=1)

    # If borders vector data is given, plot it too
    if borders is not None:
        borders = borders.to_crs(white_xmas_raster.rio.crs)
        borders.plot(ax=ax, facecolor='none', linewidth=0.3)

    # Set only the classification ticks on the colorbar
    colorbar = plot.colorbar
    ticks = utils.get_tick_locations(colorbar.get_ticks())
    labels = ['No Snow', f'Snow present \n(at least {snow_threshold}cm)']
    colorbar.set_ticks(ticks, labels=labels)
    colorbar.set_label("Snow Classification")

    # disable all other axis, lines and ticks
    plt.axis('off')

    plt.title(f"White Christmas {year}")
    plt.show()


def plot_prob_white_xmas(raster, start_year, end_year, borders=None):
    #TODO: add docstring  
 
    # use custom cmap
    custom_cmap = utils.wxmas_prob_cmap()

    fig, ax = plt.subplots(figsize=(6, 6))
    
    # Plot using xarray's plot method
    plot = raster.plot.imshow(ax=ax, cmap=custom_cmap, vmin=1, vmax=6)

    # If borders vector data is given, plot it too
    if borders is not None:
        borders = borders.to_crs(raster.rio.crs)
        borders.plot(ax=ax, facecolor='none', linewidth=0.3)

    # Set only the classification ticks on the colorbar
    utils.set_wxmas_prob_ticks(plot.colorbar)
    
    # disable all other axis, lines and ticks
    plt.axis('off')

    plt.title(f"Probability of White Christmas in Finland {start_year}-{end_year}")
    plt.show()


def plot_prob_wxmas_side_by_side(raster1, start_year1, end_year1, raster2, start_year2, end_year2, borders=None):
    #TODO: add docstring

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 6))
    
    # use custom cmap
    custom_cmap = utils.wxmas_prob_cmap()

    plot1 = raster1.plot.imshow(ax=ax1, cmap=custom_cmap, vmin=1, vmax=6)
    plot1.colorbar.remove()
    ax1.set_title(f"{start_year1}-{end_year1}")


    plot2 = raster2.plot.imshow(ax=ax2, cmap=custom_cmap, vmin=1, vmax=6)
    plot2.colorbar.remove()
    ax2.set_title(f"{start_year2}-{end_year2}")

    # If borders vector data is given, plot it too
    if borders is not None:
        borders = borders.to_crs(raster1.rio.crs)
        borders.plot(ax=ax1, facecolor='none', linewidth=0.3)
        borders.plot(ax=ax2, facecolor='none', linewidth=0.3)

    # Set only the classification ticks on the colorbar
    cbar = fig.colorbar(plot2, ax=[ax1,ax2])
    utils.set_wxmas_prob_ticks(cbar)

    # disable all other axis, lines and ticks
    ax1.axis('off')
    ax2.axis('off')

    plt.suptitle(f"Probability of White Christmas over distinct time periods")
    plt.show()

    