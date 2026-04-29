import datetime

from pmana.utils.fitting import Gaus, TripleGaus

# logger for configuration changes in time:
# this adds support, e.g., for a time-dependent gain calibration,
# which can be useful when there are hardware changes
# in the PrMs within a data taking run
# usage: list of `Tuple(datetime, value)` for each single
# calibration entry, the `value` is taken for measurements
# taken after the specified `datetime`.
CALIBRATION_CHANGES = {
    'OuterLongCalibration': [
        (datetime.datetime(2026, 3, 1, 0, 0), 1.0096),
        (datetime.datetime(2026, 3, 7, 15, 0), 1.),
    ],
    'OuterShortCalibration': [
        (datetime.datetime(2026, 3, 1, 0, 0), 0.9940),
        (datetime.datetime(2026, 3, 7, 15, 0), 1.),
    ],
}

# analysis configutaion, most importantly with
# the mapping between physical channels and readout data;
# some limits for analysis, which should be stable
# but might need tuning based on data and liquid argon purities
DEFAULT_ANALYSIS_CONFIGURATION = {
    'InnerLongChannel'          : 2,            # mapping between readout channel and physical meaning
    'OuterLongChannel'          : 3,
    'InnerShortChannel'         : 0,
    'OuterShortChannel'         : 1,  
    'InnerLongCalibration'      : 1.,           # multiplicative calibration factors, if you feel confident enough
    'OuterLongCalibration'      : 1.,      
    'InnerShortCalibration'     : 1.,
    'OuterShortCalibration'     : 1.,
    'ICFitter'                  : TripleGaus,   # simple Gaussain fit or triple-Gaussian fit currently supported
    'ShortGausFitLimits'        : (0.15, 0.15), # fitting limits around the peak for the short Pr.M.
    'LongGausFitLimits'         : (0.1, 0.15),  # fitting limits around the peak for the long Pr.M.
    'ComptonSearchLimits'       : (0.3, 0.7),   # peak height window to look for the Compton edge
    'MinComptonSearchLowLimit'  : 0.3,          # low limit when going backwards from the Compton edge to look for the valley
    'ComptonMode'               : 'rising',     # how we extract the normalization between short and long
                                                # default is `rising` (middle point between valley and Compton edge)
    'LongICPeakSearchLimits'    : (0.15, 0.5),  # peak height window to look for the IC peak for the short Pr.M.
    'ShortICPeakSearchLimits'   : (0.4, 0.7),   # peak height window to look for the IC peak for the long Pr.M.
    'ShortAsymptoticICPeak'     : 0.60833,      # asymptotic value for the peak of the short-PrM
    'LongAsymptoticICPeak'      : 0.60795,      # asymptotic value for the peak of the long-PrM
    'LongDrift'                 : 405,          # mm
    'ShortDrift'                : 45,           # mm
    # 'DriftVelocity'             : 1.494,       # from Zambelli for 449 V/cm
    'DriftVelocity'             : 1.538,        # from Zambelli, + 3% according for different electric fields
    # 'DriftVelocity'             : 1.568,        # from BNL LAr property tables for 476 V/cm and 87.6 K
}

def ResolveConfiguration(
    Config, 
    Timestamp, 
    CONFIG_CHANGES = CALIBRATION_CHANGES
):
    # grab the configuration
    resolved = dict(Config)

    # update the configuration
    # according for the changes in time
    for key, entries in CONFIG_CHANGES.items():
        for t, value in sorted(entries):
            if Timestamp >= t:
                resolved[key] = value

    return resolved