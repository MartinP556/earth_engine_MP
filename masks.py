import ee

def MODIS_cloud_mask_from_bits(image):
    qa = image.select('state_1km')
    # Bits 0-1 are cloud, 2 cloud shadow, 8-9 cirrus
    cloud_bit_mask = 3 << 0
    #cloud_bit_mask2 = 1 << 1
    cloud_shadow_bit_mask = 1 << 2
    cirrus_bit_mask = 3 << 8
    #cirrus_bit_mask2 = 1 << 9
    mask = (
        qa.bitwiseAnd(cloud_bit_mask).eq(0)
        .And(qa.bitwiseAnd(cirrus_bit_mask).eq(0)
             .And(qa.bitwiseAnd(cloud_shadow_bit_mask).eq(0)
                 )
            )
    )
    return mask

def MODIS_mask_clouds_250m(image_collection):
    QA_BAND ='state_1km'#'QC_500m'
    MODIS_500m = ee.ImageCollection("MODIS/061/MOD09GA")
    qa = MODIS_500m.select(QA_BAND)
    qa = qa.map(MODIS_cloud_mask_from_bits)
    linked = image_collection.linkCollection(qa, [QA_BAND])#MODIS_500m, [QA_BAND])
    def mask_by_band(image):
        masking_band = image.select(QA_BAND)
        return image.updateMask(masking_band)
    masked = linked.map(mask_by_band)
    return masked

def mask_MODIS_clouds(image):
    """Masks clouds in a Sentinel-2 image using the stateQA band.

    Args:
        image (ee.Image): A Sentinel-2 image.

    Returns:
        ee.Image: A cloud-masked Sentinel-2 image.
    """
    qa = image.select('state_1km')
    # Bits 0-1 are cloud, 2 cloud shadow, 8-9 cirrus
    cloud_bit_mask = 3 << 0
    #cloud_bit_mask2 = 1 << 1
    cloud_shadow_bit_mask = 1 << 2
    cirrus_bit_mask = 3 << 8
    #cirrus_bit_mask2 = 1 << 9
    mask = (
        qa.bitwiseAnd(cloud_bit_mask).eq(0)
        .And(qa.bitwiseAnd(cirrus_bit_mask).eq(0)
             .And(qa.bitwiseAnd(cloud_shadow_bit_mask).eq(0)
                 )
            )
    )
    return image.updateMask(mask)

def MODIS_Mask_QC(image):
    """Masks clouds in a Sentinel-2 image using the stateQA band.

    Args:
        image (ee.Image): A Sentinel-2 image.

    Returns:
        ee.Image: A cloud-masked Sentinel-2 image.
    """
    qa = image.select('QC_500m')
    # Bits 0-1 are cloud, 2 cloud shadow, 8-9 cirrus
    b1_mask = 15 << 2
    b2_mask = 15 << 6
    b3_mask = 15 << 10
    b4_mask = 15 << 14
    mask = (
        qa.bitwiseAnd(b1_mask).eq(0)
        .And(qa.bitwiseAnd(b2_mask).eq(0)
             .And(qa.bitwiseAnd(b3_mask).eq(0)
                  .And(qa.bitwiseAnd(b4_mask).eq(0)
                      )
                 )
            )
    )
    return image.updateMask(mask)

def mask_s2_clouds(image):
    """Masks clouds in a Sentinel-2 image using the QA band.

    Args:
        image (ee.Image): A Sentinel-2 image.

    Returns:
        ee.Image: A cloud-masked Sentinel-2 image.
    """
    qa = image.select('QA60')

    # Bits 10 and 11 are clouds and cirrus, respectively.
    cloud_bit_mask = 1 << 10
    cirrus_bit_mask = 1 << 11

    # Both flags should be set to zero, indicating clear conditions.
    mask = (
        qa.bitwiseAnd(cloud_bit_mask)
        .eq(0)
        .And(qa.bitwiseAnd(cirrus_bit_mask).eq(0))
    )

    return image.updateMask(mask)

def mask_s2_clouds_collection(image_collection):
    """Masks clouds in a Sentinel-2 image collection using the SLC band.

    Args:
        image (ee.ImageCollection): A Sentinel-2 image collection.

    Returns:
        ee.Image: A cloud-masked Sentinel-2 image collection.
    """
    return image_collection.map(mask_s2_clouds)

def mask_other(img):
    return img.updateMask(img.neq(0))
    
def worldcereal_mask(image):
    ESA_mask = ee.ImageCollection("ESA/WorldCereal/2021/MODELS/v100")
    ESA_mask = ESA_mask.map(mask_other)
    AEZ_filter = ee.Filter.Or(ee.Filter.eq('aez_id', 46172), ee.Filter.eq('aez_id', 22190), ee.Filter.eq('aez_id', 12048), ee.Filter.eq('aez_id', 31114))
    ESA_mask_maize = ESA_mask.filter(ee.Filter.eq('season', 'tc-maize-main')).filter(AEZ_filter)#.filterBounds(location) 
    maize_mask = ESA_mask_maize.filter('product == "maize"').select(['classification'])
    return image.updateMask(maize_mask.mosaic())

def csPlus_mask_collection(image_collection):
    QA_BAND = 'cs'
    CLEAR_THRESHOLD = 0.6
    csPlus = ee.ImageCollection('GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED')
    linked = image_collection.linkCollection(csPlus, [QA_BAND])
    masked = linked.map(lambda img: img.updateMask(img.select(QA_BAND).gte(CLEAR_THRESHOLD)))
    return masked

def csPlus_mask_images(image_collection):
    csPlus = ee.ImageCollection('GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED')
    linkedCollection = image_collection.linkCollection(csPlus, ['cs', 'cs_cdf'])
    return linkedCollection.filterMetadata('CLOUDY_PIXEL_PERCENTAGE','less_than',50)

def mask_IC_by_WC(IC, count_threshold):
    world_cereals = ee.ImageCollection('ESA/WorldCereal/2021/MODELS/v100').map(mask_other)
    crop = world_cereals.filter(product_codes[crop_type]).mosaic().select('classification').gt(0)
    crop = crop.updateMask(crop)
    crop = crop.setDefaultProjection(world_cereals.first().select('classification').projection(), scale = 10)
    crop = count_reducer(crop).gt(count_threshold)
    #print(crop.bandNames().getInfo())
    region = mask_other(crop.clip(f1))#.geometry())#.geometry()
    IC = IC.map(lambda img: img.updateMask(region))
    