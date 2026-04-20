import numpy
import scipy

from pmana.purity.config import DEFAULT_ANALYSIS_CONFIGURATION

from pmana.utils.fitting import Gaus
from pmana.utils.io import ExtractSingleMeasurement

def ExtractICPeak(
    MeasurementPath,
    PM_TAG = 'Long',
    SAVE_SPECTRA = False,
    ANALYSIS_CONFIGURATION = DEFAULT_ANALYSIS_CONFIGURATION
):

    """
        Input
        ---
        MeasurementPath : str
                          Path to data.

        PM_TAG : str, `'Long'` or `'Short'`
                 What Pr.M. to process, with varying analysis configurations.

        SAVE_SPECTRA : bool
                       Whether to save also the IC spectra to dataframe.

        CALIBRATION_FACTORS : dict
                              Mapping between channels and their calibration factors.
                              Look in `pmana.purity.config` for defaults.

        ANALYSIS_CONFIGURATION : dict
                                 Some configuration parameters for analysis.
                                 Look in `pmana.purity.config` for defaults.
        Output
        ---
        Provides the IC peak position, IC peak width, and inner-outer scaling factor.
        Optionally provides the IC spectra.
    """

    # verify Pr.M. tag
    assert PM_TAG == 'Long' or PM_TAG == 'Short', \
           "The PM_TAG you used is not supported. Use 'Long' or 'Short'."

    # get data
    Data = ExtractSingleMeasurement(
        MeasurementPath,
        IS_CSV = True,
        COL_NAMES = ['binCenter', 'F1', 'F2', 'F3', 'F4'],
        DELIMITER = ','
    )
    print(f'Analyzing {MeasurementPath}...')

    # get inner anode
    CH_INNER = ANALYSIS_CONFIGURATION[f'Inner{PM_TAG}Channel']
    Interp = scipy.interpolate.interp1d(Data[CH_INNER]['BinCenter'], Data[CH_INNER]['Population'], kind='linear', bounds_error=False, fill_value=0)
    yInner = Interp(Data[CH_INNER]['BinCenter'] / ANALYSIS_CONFIGURATION[f'Inner{PM_TAG}Calibration'])   

    # get outer anode
    CH_OUTER = ANALYSIS_CONFIGURATION[f'Outer{PM_TAG}Channel']
    Interp = scipy.interpolate.interp1d(Data[CH_OUTER]['BinCenter'], Data[CH_OUTER]['Population'], kind='linear', bounds_error=False, fill_value=0)
    yOuter = Interp(Data[CH_OUTER]['BinCenter'] / ANALYSIS_CONFIGURATION[f'Outer{PM_TAG}Calibration'])     

    # identify the Compton edge on the outer channel
    COMPTON_SEARCH_LIMITS = ANALYSIS_CONFIGURATION[f'ComptonSearchLimits']
    ComptonEdgeIdx = numpy.argmax(yOuter[(Data[CH_OUTER]['BinCenter'] > COMPTON_SEARCH_LIMITS[0]) & (Data[CH_OUTER]['BinCenter'] < COMPTON_SEARCH_LIMITS[1])]) + numpy.where(Data[CH_OUTER]['BinCenter'] > COMPTON_SEARCH_LIMITS[0])[0][0]
    ComptonEdge = Data[CH_OUTER]['BinCenter'].iloc[ComptonEdgeIdx]

    # identify the valley before the Compton edge
    MIN_COMPTON_SEARCH_LOW_LIM = ANALYSIS_CONFIGURATION[f'MinComptonSearchLowLimit']
    MinimumComptonIdx = numpy.argmin(yOuter[(Data[CH_OUTER]['BinCenter'] > MIN_COMPTON_SEARCH_LOW_LIM) & (Data[CH_OUTER]['BinCenter'] < ComptonEdge)]) + numpy.where(Data[CH_OUTER]['BinCenter'] > MIN_COMPTON_SEARCH_LOW_LIM)[0][0]
    MinimumComptonEdge = Data[CH_OUTER]['BinCenter'][MinimumComptonIdx]

    # identify the rising edge of the Compton edge
    MiddleComptonEdgeIdx = int((MinimumComptonIdx + ComptonEdgeIdx) / 2)
    MiddleComptonEdge = Data[CH_OUTER]['BinCenter'][MiddleComptonEdgeIdx]

    # normalize the outer spectrum on the inner spectrum, based on the chosen mode...
    MODE = ANALYSIS_CONFIGURATION[f'ComptonMode']
    match MODE:
        case 'rising':
            yComptonEdge_Outer = numpy.mean(yOuter[(Data[CH_OUTER]['BinCenter'] > MiddleComptonEdge - 0.025) & (Data[CH_OUTER]['BinCenter'] < MiddleComptonEdge + 0.025)])
            yComptonEdge_Inner = numpy.mean(yInner[(Data[CH_INNER]['BinCenter'] > MiddleComptonEdge - 0.025) & (Data[CH_INNER]['BinCenter'] < MiddleComptonEdge + 0.025)])
        case 'min':
            yComptonEdge_Outer = numpy.mean(yOuter[(Data[CH_OUTER]['BinCenter'] > MinimumComptonEdge - 0.025) & (Data[CH_OUTER]['BinCenter'] < MinimumComptonEdge + 0.025)])
            yComptonEdge_Inner = numpy.mean(yInner[(Data[CH_INNER]['BinCenter'] > MinimumComptonEdge - 0.025) & (Data[CH_INNER]['BinCenter'] < MinimumComptonEdge + 0.025)])
        case 'max':
            yComptonEdge_Outer = numpy.mean(yOuter[(Data[CH_OUTER]['BinCenter'] > ComptonEdge - 0.025) & (Data[CH_OUTER]['BinCenter'] < ComptonEdge + 0.025)])
            yComptonEdge_Inner = numpy.mean(yInner[(Data[CH_INNER]['BinCenter'] > ComptonEdge - 0.025) & (Data[CH_INNER]['BinCenter'] < ComptonEdge + 0.025)])
        case _:
            print("Unavailable option, falling back to `rising`.")
            yComptonEdge_Outer = numpy.mean(yOuter[(Data[CH_OUTER]['BinCenter'] > MiddleComptonEdge - 0.025) & (Data[CH_OUTER]['BinCenter'] < MiddleComptonEdge + 0.025)])
            yComptonEdge_Inner = numpy.mean(yInner[(Data[CH_INNER]['BinCenter'] > MiddleComptonEdge - 0.025) & (Data[CH_INNER]['BinCenter'] < MiddleComptonEdge + 0.025)])
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
    IC_Pos = xIC.iloc[IC_Pos_Idx] 

    # fit the IC peak around the identified max
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

def GetAsymptoticPrMVoltage(
    ShortIC,
    LongIC,
    e,
    ANALYSIS_CONFIGURATION = DEFAULT_ANALYSIS_CONFIGURATION
):

    DRIFT_VELOCITY = 1.568
    DRIFT_TIME_SHORT = ANALYSIS_CONFIGURATION['ShortDrift'] / DRIFT_VELOCITY
    DRIFT_TIME_LONG = ANALYSIS_CONFIGURATION['LongDrift']  / DRIFT_VELOCITY

    # asymptotic charges
    ratio    = numpy.log(LongIC / ShortIC) / (DRIFT_TIME_LONG - DRIFT_TIME_SHORT)
    Q_abs_short = ShortIC * numpy.exp((DRIFT_TIME_SHORT + e) * ratio)
    Q_abs_long  = LongIC  * numpy.exp((DRIFT_TIME_LONG  + e) * ratio)

    return Q_abs_short, Q_abs_long

def GetLifetime_SinglePrM(
    ICPeak,
    ICPeak_Asymptotic,
    DRIFT_LENGTH = 200,     # mm
    DRIFT_VELOCITY = 1.547  # mm / us
):
    
    # drift time difference
    dt = DRIFT_LENGTH / DRIFT_VELOCITY

    # electron lifetime
    lifetime = dt / numpy.log(ICPeak_Asymptotic / ICPeak)

    return lifetime

def GetLifetime_DoublePrM(
    ICPeak_Short,
    ICPeak_Long,
    ICPeak_Short_err = None,
    ICPeak_Long_err = None,
    SHORT_DRIFT_LENGTH = 40,    # mm
    LONG_DRIFT_LENGTH = 500,    # mm
    DRIFT_VELOCITY = 1.547      # mm / us
):

    # drift time difference
    dt = (SHORT_DRIFT_LENGTH - LONG_DRIFT_LENGTH) / DRIFT_VELOCITY

    # electron lifetime
    lifetime = dt / numpy.log(ICPeak_Long / ICPeak_Short)

    if ICPeak_Short_err is None or ICPeak_Long_err is None:
        return lifetime

    # error on the lifetime
    lifetime_err = abs(dt) \
        / (numpy.log(ICPeak_Long / ICPeak_Short)**2)  \
        * numpy.sqrt(
            pow(ICPeak_Long_err / ICPeak_Long, 2) +
            pow(ICPeak_Short_err / ICPeak_Short, 2)
        )

    return lifetime, lifetime_err