import datetime

from pmana.utils.fitting import Gaus, GausPlusLine, TripleGaus

# logger for configuration changes in time:
# this adds support, e.g., for a time-dependent gain calibration,
# which can be useful when there are hardware changes
# in the PrMs within a data taking run
# usage: list of `Tuple(datetime, value)` for each single
# calibration entry, the `value` is taken for measurements
# taken after the specified `datetime`
CALIBRATION_CHANGES_DEFAULT = {
}

CALIBRATION_CHANGES_COLDBOX = {
    'OuterLongCalibration': [
        (datetime.datetime(2026, 3, 1, 0, 0), 1. / 1.0096),
        (datetime.datetime(2026, 3, 7, 15, 0), 1.),
    ],
    'OuterShortCalibration': [
        (datetime.datetime(2026, 3, 1, 0, 0), 1. / 0.9940),
        (datetime.datetime(2026, 3, 7, 15, 0), 1.),
    ],
}

CALIBRATION_CHANGES_NP02 = {
    'OuterLongCalibration': [
        (datetime.datetime(2026, 5, 1, 0, 0), 1.034850), # from in/out TP in Long-PrM
    ],
    'OuterShortCalibration': [
        (datetime.datetime(2026, 5, 1, 0, 0), 0.900579 * 1.630957), # from in/out TP in Short-PrM
    ],
    'InnerLongCalibration': [
        (datetime.datetime(2026, 5, 1, 0, 0), 1.),
    ],
    'InnerShortCalibration': [
        (datetime.datetime(2026, 5, 1, 0, 0), 1.630957), # from in-Long-PrM / in-Short-PrM ratio
    ],
}

# analysis configurations, most importantly with
# the mapping between physical channels and readout data;
# some limits for analysis, which should be stable
# but might need tuning based on data and liquid argon purities

# `default`configuration, developed from the Cold Box campaign
DEFAULT_ANALYSIS_CONFIGURATION = {
    'ExtractKwargs'                 : dict(
                                        IS_CSV = True,
                                        COL_NAMES = ['binCenter', 'F1', 'F2', 'F3', 'F4'],
                                        DELIMITER = ','
                                      ),            # parameters for the I/O, working pretty
    'InnerLongChannel'              : 2,            # mapping between readout channel and physical meaning
    'OuterLongChannel'              : 3,
    'InnerShortChannel'             : 0,
    'OuterShortChannel'             : 1,  
    'InnerLongCalibration'          : 1.,           # multiplicative calibration factors, if you feel confident enough
    'OuterLongCalibration'          : 1.,      
    'InnerShortCalibration'         : 1.,
    'OuterShortCalibration'         : 1.,
    'EnableTemperatureCalibration'  : False,        # whether to enable the temperature correction to the each voltage (per channel)
    'ReferenceTemperature'          : 20,           # reference temperature for the calibration, expressed in [°C]
    'TemperatureCalibrationMode'    : 'linear',     # `linear` and `quadratic` currently supported
    'InnerLongTemperaturePars'      : (1., 1.),     # calibration models for the temperature to gains for each channel (e.g., a*x + b for `linear``)
    'OuterLongTemperaturePars'      : (1., 1.),
    'InnerShortTemperaturePars'     : (1., 1.),
    'OuterShortTemperaturePars'     : (1., 1.),   
    'ICFitter'                      : TripleGaus,   # simple Gaussain fit or triple-Gaussian fit currently supported
    'ShortGausFitLimits'            : (0.15, 0.15), # fitting limits around the peak for the short Pr.M.
    'LongGausFitLimits'             : (0.1, 0.15),  # fitting limits around the peak for the long Pr.M.
    'ShortComptonSearchLimits'      : (0.3, 0.7),   # peak height window to look for the Compton edge
    'ShortMinComptonSearchLowLimit' : 0.3,          # low limit when going backwards from the Compton edge to look for the valley
    'LongComptonSearchLimits'       : (0.15, 0.7),  # peak height window to look for the Compton edge
    'LongMinComptonSearchLowLimit'  : 0.15,         # low limit when going backwards from the Compton edge to look for the valley
    'ComptonMode'                   : 'rising',     # how we extract the normalization between short and long
                                                    # default is `rising` (middle point between valley and Compton edge)
    'ComptonEdgeFitter'             : Gaus,
    'ComptonEdgeFitRightThreshold'  : 0.05,
    'ComptonEdgeFitLeftLimit'       : 0.05,
    'ExternalScaleFactorLongMode'   : False,        # whether the scale factor is provided from external considerations, skipping the CE calculations
    'ExternalScaleFactorLong'       : 1.2,          # the external scale factor
    'ExternalScaleFactorShortMode'  : False,        
    'ExternalScaleFactorShort'      : 1.,          
    'LongICPeakSearchLimits'        : (0.15, 0.5),  # peak height window to look for the IC peak for the short Pr.M.
    'ShortICPeakSearchLimits'       : (0.4, 0.7),   # peak height window to look for the IC peak for the long Pr.M.
    'ShortAsymptoticICPeak'         : 0.60833,      # asymptotic value for the peak of the short-PrM
    'LongAsymptoticICPeak'          : 0.60795,      # asymptotic value for the peak of the long-PrM
    'LongDrift'                     : 405,          # mm
    'ShortDrift'                    : 45,           # mm
    # 'DriftVelocity'               : 1.494,         # from Zambelli for 449 V/cm
    'DriftVelocity'                 : 1.538,        # from Zambelli, + 3% according for different electric fields
    # 'DriftVelocity'               : 1.568,         # from BNL LAr property tables for 476 V/cm and 87.6 K
}

# `coldbox`-focused configuration
COLDBOX_ANALYSIS_CONFIGURATION = DEFAULT_ANALYSIS_CONFIGURATION.copy()
# Cold Box channel mapping
COLDBOX_ANALYSIS_CONFIGURATION['InnerLongChannel']  = 2
COLDBOX_ANALYSIS_CONFIGURATION['OuterLongChannel']  = 3
COLDBOX_ANALYSIS_CONFIGURATION['InnerShortChannel'] = 0
COLDBOX_ANALYSIS_CONFIGURATION['OuterShortChannel'] = 1
# tuned Compton search
COLDBOX_ANALYSIS_CONFIGURATION['ShortComptonSearchLimits']        = (0.3, 0.6)
COLDBOX_ANALYSIS_CONFIGURATION['ShortMinComptonSearchLowLimit']   = 0.25
COLDBOX_ANALYSIS_CONFIGURATION['LongComptonSearchLimits']         = (0.1, 0.6)
COLDBOX_ANALYSIS_CONFIGURATION['LongMinComptonSearchLowLimit']    = 0.1
COLDBOX_ANALYSIS_CONFIGURATION['ComptonMode']                     = 'rising'
# switch to external scaling factor for the long-PrM
# this will ignore the derivation of the scaling factor
# from the study of the Compton edge on the outer anode,
# and instead use the fixed `ExternalScaleFactorLong` factor
COLDBOX_ANALYSIS_CONFIGURATION['ExternalScaleFactorLongMode']     = True
COLDBOX_ANALYSIS_CONFIGURATION['ExternalScaleFactorLong']         = 1.2
# limits to search and fit the IC peaks, after outer-to-inner subtraction
COLDBOX_ANALYSIS_CONFIGURATION['LongICPeakSearchLimits']  = (0.1, 0.4)  # long Bi-PrM has a significant tail...
COLDBOX_ANALYSIS_CONFIGURATION['ShortICPeakSearchLimits'] = (0.4, 0.7)  # short Bi-PrM has a significant test pulse...

# configuration presets for the test-pulse-focused analysis
# supported presets: `default`, `DT5781`, `CSV`

# `default`, generic, test pulse configuration
DEFAULT_TESTPULSE_CONFIGURATION = {
    'ExtractKwargs'     : dict(DELIMITER=';'),  # parameters for the I/O
    'InnerLongChannel'  : 2,                    # mapping between readout channel and physical meaning
    'OuterLongChannel'  : 3,
    'InnerShortChannel' : 0,
    'OuterShortChannel' : 1,  
    'BinName'           : 'BinCenter',          # name for binned column
    'CountName'         : 'Population',         # name for counts column
    'MinNOfMeas'        : 5,                    # skip files with less than `MinNOfMeas` lines
    'SkipNRows'         : 0,                    # skip the first `SkipNRows` lines
    'MaskTestPulse'     : True,                 # whether to mask the spectra to isolate the test pulses
    'ShortTestPulseLowLim'   : 0.7,             # low- and high-limits for the test-pulse masks, by PrM
    'ShortTestPulseHighLim'  : 1,
    'LongTestPulseLowLim'    : 0.7,
    'LongTestPulseHighLim'   : 1,
    'Rebin'             : False,                # optionally halve the binning for stability
    'TPFitter'          : GausPlusLine,         # fitter for the test pulse; `GausPlusLine` adds simple background modeling
}

# `DT5781` test pulse configuration
# this was needed for the Padova test-stand
# where there was no physical spectrum other
# than a simple, Gaussian test pulse
DT5781_TESTPULSE_CONFIGURATION = DEFAULT_TESTPULSE_CONFIGURATION.copy()
DT5781_TESTPULSE_CONFIGURATION['ExtractKwargs'] = dict(
    CHANNEL_KEY='CH*', 
    N_SKIP_LINES=3,
    COL_NAMES=['c0','c1','c2'], 
    DELIMITER=' '
)
DT5781_TESTPULSE_CONFIGURATION['MaskTestPulse'] = False

# `csv` test pulse configuration
# supporting the new file format from the 
# oscilloscope-based data acquisition
CSV_TESTPULSE_CONFIGURATION = DEFAULT_TESTPULSE_CONFIGURATION.copy()
CSV_TESTPULSE_CONFIGURATION['ExtractKwargs'] = dict(
    IS_CSV=True,
    COL_NAMES=['binCenter','F1','F2','F3','F4'],
    DELIMITER=','
)

def ResolveConfiguration(
    Config, 
    Timestamp, 
    CONFIG_CHANGES = CALIBRATION_CHANGES_COLDBOX
):
    # grab the configuration
    resolved = dict(Config)

    # update the configuration
    # accounting for changes in time
    for key, entries in CONFIG_CHANGES.items():
        for t, value in sorted(entries):
            if Timestamp >= t:
                resolved[key] = value

    return resolved