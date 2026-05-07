import numpy
import scipy

from pmana.purity.config import DEFAULT_ANALYSIS_CONFIGURATION, ResolveConfiguration

from pmana.utils.fitting import Gaus, TripleGaus
from pmana.utils.io import ExtractSingleMeasurement

def ExtractICPeak(
    MeasurementPath,
    Timestamp = None,
    PM_TAG = 'Long',
    DEBUG_MODE = False,
    ANALYSIS_CONFIGURATION = DEFAULT_ANALYSIS_CONFIGURATION
):

    """
        Input
        ---
        MeasurementPath : str
                          Path to data.
        
        Timestamp : datetime
                    Date corresponding to the measurement.
                    If `None`, it is ignored.
                    In practice, it is needed to have a time-dependent calibration.

        PM_TAG : str, `'Long'` or `'Short'`
                 What Pr.M. to process, with varying analysis configurations.

        DEBUG_MODE :   bool
                       Whether to save also the IC spectra to dataframe, along
                       with the full parameter list of the fitting function.

        ANALYSIS_CONFIGURATION : dict
                                 Some configuration parameters for analysis.
                                 Look in `pmana.purity.config` for defaults.
        Output
        ---
        Provides the IC peak position, IC peak width, and inner-outer scaling factor.
        Optionally provides the IC spectra.
    """

    if Timestamp is not None:
        ANALYSIS_CONFIGURATION = ResolveConfiguration(ANALYSIS_CONFIGURATION, Timestamp)

    # verify Pr.M. tag
    assert PM_TAG == 'Long' or PM_TAG == 'Short', \
           "The `PM_TAG` you used is not supported. Use `'Long'` or `'Short'`."

    # get data
    Data = ExtractSingleMeasurement(
        MeasurementPath,
        IS_CSV = True,
        COL_NAMES = ['binCenter', 'F1', 'F2', 'F3', 'F4'],
        DELIMITER = ','
    )

    # debug
    print(f'[{PM_TAG}] Analyzing {MeasurementPath}...')
    print(f'[{PM_TAG}] Calibration is {ANALYSIS_CONFIGURATION[f'Inner{PM_TAG}Calibration']} on inner and {ANALYSIS_CONFIGURATION[f'Outer{PM_TAG}Calibration']} on outer.')

    # get inner anode
    CH_INNER = ANALYSIS_CONFIGURATION[f'Inner{PM_TAG}Channel']
    xInner = Data[CH_INNER]['BinCenter'] / ANALYSIS_CONFIGURATION[f'Inner{PM_TAG}Calibration']
    yInner = Data[CH_INNER]['Population']

    # get outer anode
    CH_OUTER = ANALYSIS_CONFIGURATION[f'Outer{PM_TAG}Channel']
    xOuter = Data[CH_OUTER]['BinCenter'] / ANALYSIS_CONFIGURATION[f'Outer{PM_TAG}Calibration']
    yOuter = Data[CH_OUTER]['Population']

    # identify the Compton edge on the outer channel
    COMPTON_SEARCH_LIMITS = ANALYSIS_CONFIGURATION[f'{PM_TAG}ComptonSearchLimits']
    mask = (xOuter > COMPTON_SEARCH_LIMITS[0]) & (xOuter < COMPTON_SEARCH_LIMITS[1])
    indices = numpy.where(mask)[0]
    ComptonEdgeIdx = indices[numpy.argmax(yOuter[mask])]
    ComptonEdge = xOuter.iloc[ComptonEdgeIdx]

    # identify the valley before the Compton edge
    MIN_COMPTON_SEARCH_LOW_LIM = ANALYSIS_CONFIGURATION[f'{PM_TAG}MinComptonSearchLowLimit']
    mask = (xOuter > MIN_COMPTON_SEARCH_LOW_LIM) & (xOuter < ComptonEdge)
    indices = numpy.where(mask)[0]
    MinimumComptonIdx = indices[numpy.argmin(yOuter[mask])]
    MinimumComptonEdge = xOuter[MinimumComptonIdx]

    # identify the rising edge of the Compton edge
    MiddleComptonEdgeIdx = int((MinimumComptonIdx + ComptonEdgeIdx) / 2)
    MiddleComptonEdge = xOuter[MiddleComptonEdgeIdx]

    # normalize the outer spectrum on the inner spectrum, based on the chosen mode...
    MODE = ANALYSIS_CONFIGURATION[f'ComptonMode']
    match MODE:
        case 'rising':
            yComptonEdge_Outer = numpy.mean(yOuter[(xOuter > MiddleComptonEdge - 0.025) & (xOuter < MiddleComptonEdge + 0.025)])
            yComptonEdge_Inner = numpy.mean(yInner[(xInner > MiddleComptonEdge - 0.025) & (xInner < MiddleComptonEdge + 0.025)])
            CE = MiddleComptonEdge
        case 'min':
            yComptonEdge_Outer = numpy.mean(yOuter[(xOuter > MinimumComptonEdge - 0.025) & (xOuter < MinimumComptonEdge + 0.025)])
            yComptonEdge_Inner = numpy.mean(yInner[(xInner > MinimumComptonEdge - 0.025) & (xInner < MinimumComptonEdge + 0.025)])
            CE = MinimumComptonEdge
        case 'max':
            yComptonEdge_Outer = numpy.mean(yOuter[(xOuter > ComptonEdge - 0.025) & (xOuter < ComptonEdge + 0.025)])
            yComptonEdge_Inner = numpy.mean(yInner[(xInner > ComptonEdge - 0.025) & (xInner < ComptonEdge + 0.025)])
            CE = ComptonEdge
        case _:
            print("Unavailable option, falling back to `rising`.")
            yComptonEdge_Outer = numpy.mean(yOuter[(xOuter > MiddleComptonEdge - 0.025) & (xOuter < MiddleComptonEdge + 0.025)])
            yComptonEdge_Inner = numpy.mean(yInner[(xInner > MiddleComptonEdge - 0.025) & (xInner < MiddleComptonEdge + 0.025)])
            CE = MiddleComptonEdge
    ScalingFactor = yComptonEdge_Inner / yComptonEdge_Outer 

    # if there's an external scale factor, use that instead...
    if ANALYSIS_CONFIGURATION[f'ExternalScaleFactor{PM_TAG}Mode']:
        ScalingFactor = ANALYSIS_CONFIGURATION[f'ExternalScaleFactor{PM_TAG}']

    # logging...
    print(f"[{PM_TAG}] Inner/outer scale factor is {ScalingFactor}." )

    # equalize x axis
    xLow = numpy.max([numpy.min(xInner), numpy.min(xOuter)])
    xHigh = numpy.min([numpy.max(xInner), numpy.max(xOuter)])

    # get difference between inner spectrum and normalized outer spectrum
    InterpOuter = scipy.interpolate.interp1d(xOuter, yOuter, bounds_error=False, fill_value=0)
    yOuter_interp = InterpOuter(xInner)
    mask = (xInner > xLow) & (xInner < xHigh)
    xIC = xInner[mask]
    IC = yInner[mask] - yOuter_interp[mask] * ScalingFactor
    IC[IC < 0] = 0.

    # extract IC peak
    IC_PEAK_LIMITS = ANALYSIS_CONFIGURATION[f'{PM_TAG}ICPeakSearchLimits']
    IC_Pos_Idx = numpy.where((xIC >= IC_PEAK_LIMITS[0]) & (xIC <= IC_PEAK_LIMITS[1]))[0][numpy.argmax(IC[(xIC >= IC_PEAK_LIMITS[0]) & (xIC <= IC_PEAK_LIMITS[1])])]
    IC_Pos = xIC.iloc[IC_Pos_Idx] 

    # fit the IC peak around the identified max
    ICFitFunction = ANALYSIS_CONFIGURATION[f'ICFitter']
    GAUS_FIT_LIMITS = ANALYSIS_CONFIGURATION[f'{PM_TAG}GausFitLimits']

    try:
        pars, covs = scipy.optimize.curve_fit(
            ICFitFunction, 
            xIC[(xIC > IC_Pos - GAUS_FIT_LIMITS[0]) & (xIC < IC_Pos + GAUS_FIT_LIMITS[1])], 
            IC[(xIC > IC_Pos - GAUS_FIT_LIMITS[0]) & (xIC < IC_Pos + GAUS_FIT_LIMITS[1])], 
            p0 = (IC[IC_Pos_Idx], xIC[IC_Pos_Idx], 0.1),
            maxfev = 2000
        ) 
        errs = numpy.sqrt(numpy.diag(covs))
    except RuntimeError:
        print(f"Catched a fit failure in {MeasurementPath}. Please look into it.")
        pars = numpy.ones(3)
        errs = numpy.ones(3)

    if not DEBUG_MODE:
        return [pars[1], errs[1], ScalingFactor]
    else:
        return [pars, errs, ScalingFactor, CE, numpy.array(xIC).astype(float), numpy.array(IC).astype(float)]

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