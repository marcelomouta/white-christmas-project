"""
This module contains helper functions for the snow.py module.
"""
__author__ = "Marcelo Mouta"


def check_year_interval(start_year, end_year):
    """
    Check if given interval is within year range for which snow depth data is available

    Raises:
        ValueError: If start_year and end_year do not form a valid interval within 1961-2022
    """
    if start_year < 1961 or end_year < start_year:
        raise ValueError("start_year and end_year do not form a valid interval within 1961-2022")


def get_tick_locations(ticks):
    """Calculate tick locations at 1/4 and 3/4 of the classification scale"""
    start = ticks[0]
    end = ticks[-1]
    diff = end - start

    return [start + diff/4, end - diff/4]


def reclassify_raster(raster, bins):
    """Reclassify raster according to given bins"""
    
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