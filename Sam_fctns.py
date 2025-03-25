import ee
import ee.batch
import eemont

import os
import pandas as pd
import numpy as np

def download_ndvi(year, grid_cell_lon, grid_cell_lat, filepath, crop_type='ww', N=10, country = 'DE', crop = 'Winter wheat'):
    ee.Initialize(opt_url='https://earthengine-highvolume.googleapis.com', project='ee-spiruel')
    
    """given a grid of coordinates, download the ndvi data masked to crop type, 
    for a 'representative field' for each grid cell"""
    country_codes = {'DE': 93,
                    'KEN': 133}
    product_codes = {'Maize': 'product == "maize"',
                     'Winter wheat': 'product == "wintercereals"'}
    save_path = filepath #f'ndvi_download/{crop_type}_{year}_{grid_cell_lon:.4f}_{grid_cell_lat:.4f}_s2.csv'
    if os.path.exists(save_path):
        print(f'{crop_type}_{year}_{grid_cell_lon:.2f}_{grid_cell_lat:.2f} already downloaded')
        return
    else:
        #swap for engcrop when on gee
        #uk_outline = ee.FeatureCollection('FAO/GAUL/2015/level0').filterMetadata('ADM0_CODE','equals',256)
        country_outline = ee.FeatureCollection('FAO/GAUL/2015/level0').filterMetadata('ADM0_CODE','equals',country_codes[country])
        
        # cropland = ee.FeatureCollection("users/spiruel/crop_labels/CEH_cropmap2021")
        # crop = cropland.filterMetadata('crop_code','equals',crop_type)
        world_cereals = ee.ImageCollection('ESA/WorldCereal/2021/MODELS/v100')
        # Get a global mosaic for all agro-ecological zone (AEZ) of winter wheat
        crop = world_cereals.filter(product_codes[crop]).mosaic().select('classification').gte(0)

        # proj = ee.Projection('EPSG:27700')

        #for each grid cell, find the representative field
        #buffer each point by 12km (/2) (the scale of the GCM data)
        grid_cell = ee.Geometry.Point(grid_cell_lat, grid_cell_lon).buffer(12000//2).bounds()

        def add_doy(image):
            doy = ee.Date(image.get('system:time_start')).getRelative('day', 'year')
            return image.set('doy', doy)

        #get sentinel 2 ndvi data
        csPlus = ee.ImageCollection('GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED')
        s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
        s2 = s2.spectralIndices(['NDVI'])

        # Link S2 and CS+ results.
        linkedCollection = s2.linkCollection(csPlus, ['cs', 'cs_cdf'])

        s2_filtered = linkedCollection.filterDate(f'{year-1}-10-01', f'{year}-10-01').filterBounds(uk_outline)\
                                    .filterMetadata('CLOUDY_PIXEL_PERCENTAGE','less_than',50)

        print(f'downloading ndvi for {crop_type}_{year}_{grid_cell_lon:.2f}_{grid_cell_lat:.2f}')
        #get the geometry of the field
        # geom = ee.Feature(crop).geometry()
        region = crop.clip(grid_cell).geometry()
        
        vectors = crop.reduceToVectors(**{
            'geometry': region,
            'scale': 100,
            'maxPixels': 1e13,
            'bestEffort':True,
            'eightConnected': False,
            })#.map(lambda x: x.buffer(-20))

        random_points = ee.FeatureCollection.randomPoints(**{'region': vectors, 'points': N, 'seed': 42, 'maxError': 1})

        #get the data for the field by reducing the image collection to the field geometry
        #get NDVI and spectral bands from S2
        s2_bands = ['NDVI','cs','cs_cdf']
        ts_s2 = s2_filtered.select(s2_bands).getTimeSeriesByRegion(**{
          'reducer': ee.Reducer.mean(),
          'geometry': random_points,#.buffer(10),
          'scale': 10,
          'maxPixels': 1e9
        })
        
        task  = ee.batch.Export.table.toDrive(ts_s2, 
                                      description=f'{crop_type}_{year}_{grid_cell_lon:.2f}_{grid_cell_lat:.2f}_s2', 
                                      fileFormat='CSV', 
                                      folder=f'ndvi_download/{year}')
        task.start()
  
        #download the data
        # try:
        #     data_s2 = geemap.ee_to_df(ts_s2)
        # except Exception as e:
        #     print(e)
        #     print(f'failed to download {crop_type}_{year}_{grid_cell_lon:.2f}_{grid_cell_lat:.2f}')
        #     return
        # data_s2 = data_s2[data_s2['NDVI']!=-9999]
        # #save the data
        # data_s2.to_csv(save_path, index=False)
        # print(f'saved {save_path}')
