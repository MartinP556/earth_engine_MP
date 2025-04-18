import ee
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import geetools
import eemont
import geemap
from ee_extra.TimeSeries.core import getTimeSeriesByRegion

from masks import mask_MODIS_clouds, MODIS_Mask_QC, mask_s2_clouds, mask_s2_clouds_collection, csPlus_mask_collection
import masks

root_directory = ''

def get_image_index(image_collection, index):
    imgList = image_collection.toList(999)
    return ee.Image(ee.List(imgList).get(index))
def box_around_point(coord, box_width):
    '''
    coord: coordinate in (lat, lon) (?)
    '''
    return ee.Geometry.BBox(coord[1] - box_width, coord[0] - box_width, coord[1] + box_width, coord[0] + box_width)

def mask_other(img):
    return img.updateMask(img.neq(0))

def initialise_comparison(instrument = 'COPERNICUS/S2_SR_HARMONIZED',
                          coord = np.loadtxt(root_directory + "Saved_files/station_coords.csv", delimiter=',')[0],
                          country = 'DE', crop_type = 'M', year = 2019, root_directory = '', 
                          combine_eujrc = False, just_eujrc = False,
                          buffer_size = 1500, mask_scale = 10, indices = True, spectral_indices = ['EVI','NDVI', 'SAVI', 'NDWI', 'CIG']):
    country_codes = {'DE': 93,
                     'KEN': 133}
    product_codes = {'M': 'product == "maize"',
                     'ww': 'product == "wintercereals"'}
    grid_cell_lon = coord[1]
    grid_cell_lat = coord[0]
    f1 = ee.Feature(ee.Geometry.Point([coord[1],coord[0]]).buffer(buffer_size),{'ID':'A'})
    f1c = ee.FeatureCollection([f1])
    IC = (ee.ImageCollection(instrument)
         .filterBounds(f1c)
         .filterDate(f'{year}-01-01',f'{year}-12-31'))
    if indices:
        IC = IC.spectralIndices(spectral_indices)
    if instrument == 'COPERNICUS/S1_GRD':
        IC = IC.filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV')) # Ensure VV polarization is available
        IC = IC.filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH')) # Ensure VH polarization is available
        IC = IC.filter(ee.Filter.eq('instrumentMode', 'IW')) # Select only Interferometric Wide (IW) mode images
        IC = IC.filter(ee.Filter.eq('orbitProperties_pass', 'ASCENDING')) # Filter ascending orbit images
    grid_cell = ee.Geometry.Point(grid_cell_lon, grid_cell_lat).buffer(buffer_size).bounds()
    world_cereals = ee.ImageCollection('ESA/WorldCereal/2021/MODELS/v100').map(mask_other)
    if just_eujrc:
        eujrc = ee.ImageCollection('JRC/D5/EUCROPMAP/V1').select(['classification']).filterDate('2018-01-01', '2023-01-01').mosaic()
        crop = eujrc.select('classification').eq(216)
        crop = crop.updateMask(crop)
    elif combine_eujrc:
        eujrc = ee.ImageCollection('JRC/D5/EUCROPMAP/V1').select(['classification']).filterDate('2018-01-01', '2023-01-01').mosaic()
        eujrc_maize = eujrc.select('classification').eq(216)
        #Take out update mask if you want just worldcereals
        crop = world_cereals.filter(product_codes[crop_type]).mosaic().updateMask(eujrc_maize).select('classification').gt(0)
    else:
        crop = world_cereals.filter(product_codes[crop_type]).mosaic().select('classification').gt(0)
    region = crop.clip(grid_cell).geometry()
    vectors = crop.reduceToVectors(**{
        'geometry': region,
        'scale': mask_scale,
        'maxPixels': 1e13,
        'bestEffort':True,
        'eightConnected': False,
        })#.map(lambda x: x.buffer(-20))
    return IC, vectors