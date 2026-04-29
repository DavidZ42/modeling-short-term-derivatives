# Modeling Bitcoin Derivatives

## Setup

Create a python 3.12+ environment using your preferred method and install `requirements.txt`. The versions of all packages we used are the ones specified for compatibility (version are not listed if the package is included in Python's standard library). All data files will be created in the root directory.

## Files

Run `download_daily_asset_1m.py` to download the underlying bitcoin data for a given day (if desired), but run `download_daily_asset_given_days.py` to download the underlying bitcoin data for the day range that we used.  Then run `download_daily_derivative_1m.py` to download the derivative data from polymarket for the days we used.

 `e_m.py` is an Euler Maruyama simulation of bitcoin put into our pricing function, used to demonstrate that changing the volatility parameter is not significant.

`project.py` runs the simulation of our pricing function while updating the d parameter from the real underlying data every minute (and plots this).

 The other files are for the graphs specified in their respective file names.