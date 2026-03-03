import numpy
import scipy

from pmana.utils.fitting import Gaus
from pmana.utils.io import ExtractSingleMeasurement

ANALYSIS_CONFIGURATION = {
    'InnerLongChannel'          : 0,
    'OuterLongChannel'          : 1,
    'InnerShortChannel'         : 3,
    'OuterShortChannel'         : 2,  
    'ShortGausFitLimits'        : (0.15, 0.15),
    'LongGausFitLimits'         : (0.1, 0.15),
    'ComptonSearchLimits'       : (0.5, 1),
    'MinComptonSearchLowLimit'  : 0.25,
    'ComptonMode'               : 'rising',
    'LongICPeakSearchLimits'    : (0.4, 1),
    'ShortICPeakSearchLimits'   : (0.4, 1),
}

def ExtractICPeak(
    MeasurementPath,
    CALIBRATION_FACTORS,
    PM_TAG = 'Long',
    SAVE_SPECTRA = False,
    ANALYSIS_CONFIGURATION = ANALYSIS_CONFIGURATION
):

    """
        Input
        ---
        Data :  list of dataframes
                list of Pandas dataframes, one for each channel,
                with columns BinCenter and Population.
        
        CALIBRATION_FACTORS : dict
                              Mapping between channels and their calibration factors.

        PM_TAG : str, 'Long' or 'Short'
                 What PrM to process, with varying analysis configurations.

        Output
        ---
        Provides the IC peak position, IC peak width, and inner-outer scaling factor.
    """

    # get data
    Data = ExtractSingleMeasurement(
        MeasurementPath,
        IS_CSV = True,
        COL_NAMES = ['binCenter', 'F1', 'F2', 'F3', 'F4'],
        DELIMITER = ","
    )
    print(f'Analyzing {MeasurementPath}...')

    # get inner anode
    CH_INNER = ANALYSIS_CONFIGURATION[f'Inner{PM_TAG}Channel']
    Interp = scipy.interpolate.interp1d(Data[CH_INNER]['BinCenter'], Data[CH_INNER]['Population'], kind='linear', bounds_error=False, fill_value=0)
    yInner = Interp(Data[CH_INNER]['BinCenter'] / CALIBRATION_FACTORS[CH_INNER])   

    # get outer anode
    CH_OUTER = ANALYSIS_CONFIGURATION[f'Outer{PM_TAG}Channel']
    Interp = scipy.interpolate.interp1d(Data[CH_OUTER]['BinCenter'], Data[CH_OUTER]['Population'], kind='linear', bounds_error=False, fill_value=0)
    yOuter = Interp(Data[CH_OUTER]['BinCenter'] / CALIBRATION_FACTORS[CH_OUTER])     

    # identify the Compton edge on the outer channel
    COMPTON_SEARCH_LIMITS = ANALYSIS_CONFIGURATION[f'ComptonSearchLimits']
    ComptonEdgeIdx = numpy.argmax(yOuter[(Data[CH_OUTER]['BinCenter'] > COMPTON_SEARCH_LIMITS[0]) & (Data[CH_OUTER]['BinCenter'] < COMPTON_SEARCH_LIMITS[1])]) + numpy.where(Data[CH_OUTER]['BinCenter'] > COMPTON_SEARCH_LIMITS[0])[0][0]
    ComptonEdge = Data[CH_OUTER]['BinCenter'][ComptonEdgeIdx]

    # identify the valley before the Compton edge
    MIN_COMPTON_SEARCH_LOW_LIM = ANALYSIS_CONFIGURATION[f'MinComptonSearchLowLimit']
    MinimumComptonIdx = numpy.argmin(yOuter[(Data[CH_OUTER]['BinCenter'] > MIN_COMPTON_SEARCH_LOW_LIM) & (Data[CH_OUTER]['BinCenter'] < ComptonEdge)]) + numpy.where(Data[CH_OUTER]['BinCenter'] > MIN_COMPTON_SEARCH_LOW_LIM)[0][0]
    MinimumComptonEdge = Data[CH_OUTER]['BinCenter'][MinimumComptonIdx]

    # identify the rising edge of the Compton edge
    MiddleComptonEdgeIdx = int((MinimumComptonIdx + ComptonEdgeIdx) / 2)
    MiddleComptonEdge = Data[CH_OUTER]['BinCenter'][MiddleComptonEdgeIdx]

    # normalize the outer spectrum on the inner spectrum, based on the chosen mode...
    MODE = ANALYSIS_CONFIGURATION[f'ComptonMode']
    if MODE == 'rising':
        yComptonEdge_Outer = numpy.mean(yOuter[(Data[CH_OUTER]['BinCenter'] > MiddleComptonEdge - 0.025) & (Data[CH_OUTER]['BinCenter'] < MiddleComptonEdge + 0.025)])
        yComptonEdge_Inner = numpy.mean(yInner[(Data[CH_INNER]['BinCenter'] > MiddleComptonEdge - 0.025) & (Data[CH_INNER]['BinCenter'] < MiddleComptonEdge + 0.025)])
    elif MODE == 'min':
        yComptonEdge_Outer = numpy.mean(yOuter[(Data[CH_OUTER]['BinCenter'] > MinimumComptonEdge - 0.025) & (Data[CH_OUTER]['BinCenter'] < MinimumComptonEdge + 0.025)])
        yComptonEdge_Inner = numpy.mean(yInner[(Data[CH_INNER]['BinCenter'] > MinimumComptonEdge - 0.025) & (Data[CH_INNER]['BinCenter'] < MinimumComptonEdge + 0.025)])
    elif MODE == 'max':
        yComptonEdge_Outer = numpy.mean(yOuter[(Data[CH_OUTER]['BinCenter'] > ComptonEdge - 0.025) & (Data[CH_OUTER]['BinCenter'] < ComptonEdge + 0.025)])
        yComptonEdge_Inner = numpy.mean(yInner[(Data[CH_INNER]['BinCenter'] > ComptonEdge - 0.025) & (Data[CH_INNER]['BinCenter'] < ComptonEdge + 0.025)])
    ScalingFactor = yComptonEdge_Inner / yComptonEdge_Outer 

    # equalize x axis
    xLow = numpy.max([numpy.min(Data[CH_INNER]['BinCenter']), numpy.min(Data[CH_OUTER]['BinCenter'])])
    xHigh = numpy.min([numpy.max(Data[CH_INNER]['BinCenter']), numpy.max(Data[CH_OUTER]['BinCenter'])])

    # get difference between inner spectrum and normalized outer spectrum
    xIC = Data[CH_INNER]['BinCenter'][(Data[CH_INNER]['BinCenter'] > xLow) & (Data[CH_INNER]['BinCenter'] < xHigh)]
    IC = yInner[(Data[CH_INNER]['BinCenter'] > xLow) & (Data[CH_INNER]['BinCenter'] < xHigh)] - yOuter[(Data[CH_OUTER]['BinCenter'] > xLow) & (Data[CH_OUTER]['BinCenter'] < xHigh)] * ScalingFactor
    IC[IC < 0] = 0.

    # extract IC peak
    IC_PEAK_LIMITS = ANALYSIS_CONFIGURATION[f'{PM_TAG}ICPeakSearchLimits']
    IC_Pos_Idx = numpy.where((xIC >= IC_PEAK_LIMITS[0]) & (xIC <= IC_PEAK_LIMITS[1]))[0][numpy.argmax(IC[(xIC >= IC_PEAK_LIMITS[0]) & (xIC <= IC_PEAK_LIMITS[1])])]
    IC_Pos = xIC[IC_Pos_Idx] 

    # fit the IC peak
    GAUS_FIT_LIMITS = ANALYSIS_CONFIGURATION[f'{PM_TAG}GausFitLimits']
    pars, covs = scipy.optimize.curve_fit(
        Gaus, 
        xIC[(xIC > IC_Pos - GAUS_FIT_LIMITS[0]) & (xIC < IC_Pos + GAUS_FIT_LIMITS[1])], 
        IC[(xIC > IC_Pos - GAUS_FIT_LIMITS[0]) & (xIC < IC_Pos + GAUS_FIT_LIMITS[1])], 
        p0 = (IC[IC_Pos_Idx], xIC[IC_Pos_Idx], 0.1),
        maxfev=1000
    ) 
    errs = numpy.sqrt(numpy.diag(covs))

    if not SAVE_SPECTRA:
        return [pars[1], errs[1], ScalingFactor]
    else:
        return [pars[1], errs[1], ScalingFactor, numpy.array(xIC).astype(float), numpy.array(IC).astype(float)]