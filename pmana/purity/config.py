# analysis configutaion, most importantly with
# the mapping between physical channels and readout data;
# some limits for analysis, which should be stable
# but might need tuning based on data
DEFAULT_ANALYSIS_CONFIGURATION = {
    'InnerLongChannel'          : 0,            # mapping between readout channel and physical meaning
    'OuterLongChannel'          : 1,
    'InnerShortChannel'         : 3,
    'OuterShortChannel'         : 2,  
    'InnerLongCalibration'      : 1.,           # multiplicative calibration factors
    'OuterLongCalibration'      : 1.,      
    'InnerShortCalibration'     : 1.,
    'OuterShortCalibration'     : 1.,
    'ShortGausFitLimits'        : (0.15, 0.15), # fitting limits around the peak for the short Pr.M.
    'LongGausFitLimits'         : (0.1, 0.15),  # fitting limits around the peak for the long Pr.M.
    'ComptonSearchLimits'       : (0.5, 1),     # peak height window to look for the Compton edge
    'MinComptonSearchLowLimit'  : 0.25,         # low limit when going backwards from the Compton edge to look for the valley
    'ComptonMode'               : 'rising',     # how we extract the normalization between short and long
                                                # default is `rising` (middle point between valley and Compton edge)
    'LongICPeakSearchLimits'    : (0.4, 1),     # peak height window to look for the IC peak for the short Pr.M.
    'ShortICPeakSearchLimits'   : (0.4, 1),     # peak height window to look for the IC peak for the long Pr.M.
}