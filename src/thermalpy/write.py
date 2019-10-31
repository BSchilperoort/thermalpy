import os
import xarray as xr
import numpy as np
from netCDF4 import Dataset as NetCDF4_Dataset
from netCDF4 import date2num as NetCDF4_date2num

def writeappend_netcdf(directory, camera_id, image_datetime,
                       raw_data, temperature_data, temps, RFBO,
                       freq='hourly'):
    '''
    Function that writes away the retrieved data to netcdf

        Parameters
        ----------
        directory : string
            Path to directory to write to
        camera_id : string
            ID number of the camera
        image_datetime : datetime object
            Datetime of when the image was taken
        raw_data : np.array
            2d array of raw measurement data
        temperature_data : np.array
            2d array of temperature data
        temps : dict
            Dictionary containing the sensor & housing temperatures
        RFBO : tuple
            Tuple containing the R F B & O parameters used to convert the image

        Returns
        -------

    '''
    if freq == 'hourly':
        ftime = image_datetime.strftime('%Y_%m_%d_%H00')
    elif freq == 'daily':
        ftime = image_datetime.strftime('%Y_%m_%d')

    filename = directory + '\\' + 'FLIR_' + camera_id + '__' + ftime + '.nc'

    if not os.path.isfile(filename):
        print('Creating new dataset...')
        ds = xr.Dataset(
            data_vars={'temperature': (('time', 'y', 'x'),
                                       [temperature_data]),
                       'sensor_temperature': ('time', [temps['sensor_temperature']]),
                       'housing_temperature': ('time', [temps['housing_temperature']]),
                       'R': ('time', [RFBO[0]]),
                       'F': ('time', [RFBO[1]]),
                       'B': ('time', [RFBO[2]]),
                       'O': ('time', [RFBO[3]])},
            coords={'time': [image_datetime],
                    'y': np.arange(temperature_data.shape[0], 0, -1),
                    'x': np.arange(temperature_data.shape[1])}
                )

        ds.time.encoding['units'] = 'days since 1900-01-01'

        # Generate encoding
        encoding = {}
        for key in ds.keys():
            encoding[key] = {'zlib': True,
                             'complevel': 4}
        encoding['temperature']['least_significant_digit'] = 4

        ds.to_netcdf(filename, encoding=encoding, unlimited_dims='time')

    else:
        print('Appending dataset...')
        dataset = NetCDF4_Dataset(filename, 'a')
        ii = len(dataset.variables['time'])

        dataset.variables['time'][ii] = NetCDF4_date2num(image_datetime,
                                             'days since 1900-01-01',
                                             dataset.variables['time'].calendar,
                                             )

        dataset.variables['sensor_temperature'][ii] = (temps['sensor_temperature'])
        dataset.variables['housing_temperature'][ii] = (temps['housing_temperature'])
        dataset.variables['R'][ii] = (RFBO[0])
        dataset.variables['F'][ii] = (RFBO[1])
        dataset.variables['B'][ii] = (RFBO[2])
        dataset.variables['O'][ii] = (RFBO[3])

        dataset.variables['temperature'][ii,:,:] = temperature_data

        dataset.close()
