import pathlib
import inspect

import numpy
import pandas
import scipy

from pmana.utils.io import ExtractSingleMeasurement
from pmana.utils.fitting import Gaus, GausPlusExp, GausPlusLine

from pmana.purity.config import DEFAULT_TESTPULSE_CONFIGURATION

def ExtractTestPulse(
    MeasurementPath,
    TESTPULSE_CONFIGURATION = DEFAULT_TESTPULSE_CONFIGURATION,
    DEBUG_MODE = False,
):
    """
        Analyze a single measurement, extracting for each channel
        the mean and standard deviation from a Gaussian fit,
        along with their fit errors.

        Input
        ---
        MeasurementPath : str
                        Filesystem path containing measurements.

        EXTRACTION_CONFIGURATION : dict
                                Configuration for data extraction and preprocessing.
                                Use DT5781_EXTRACTION_CONFIGURATION, CSV_EXTRACTION_CONFIGURATION,
                                or DEFAULT_EXTRACTION_CONFIGURATION from config.py,
                                or pass a custom dict.

        DEBUG_MODE : bool, optional

        Output
        ---
        Flat list of [mean, mean_err, sigma, sigma_err, ...] per channel.
    """
    Output = []

    # extract measurement data
    Data = ExtractSingleMeasurement(MeasurementPath, **TESTPULSE_CONFIGURATION['ExtractKwargs'])
    print(f"[ExtractTestPulse] Extracted {len(Data)} channels from {MeasurementPath}.")

    # pre-fill output dict
    Output = {
        key: numpy.nan
        for i in range(len(Data))
        for key in [f"Peak_CH{i+1}", f"Err_Peak_CH{i+1}", f"Width_CH{i+1}", f"Err_Width_CH{i+1}"]
    }

    parss, errss = [], []
    for i, CHData in enumerate(Data):

        # setup fitting function
        TPFitFunction = TESTPULSE_CONFIGURATION['TPFitter']
        NPars = len(inspect.signature(TPFitFunction).parameters) - 1

        if len(CHData) < TESTPULSE_CONFIGURATION['MinNOfMeas']:
            print(f"[ExtractTestPulse] Channel {i}: only {len(CHData)} valid row(s), skipping.")
            continue

        if TESTPULSE_CONFIGURATION['SkipNRows'] > 0:
            CHData = CHData.iloc[TESTPULSE_CONFIGURATION['SkipNRows']:].reset_index(drop=True)

        # mask the test-pulse window
        if TESTPULSE_CONFIGURATION['MaskTestPulse']:
            ShortCHs = [TESTPULSE_CONFIGURATION['InnerShortChannel'], TESTPULSE_CONFIGURATION['OuterShortChannel']]
            LongCHs  = [TESTPULSE_CONFIGURATION['InnerLongChannel'],  TESTPULSE_CONFIGURATION['OuterLongChannel']]
            if i in ShortCHs:
                LowLim, HighLim = TESTPULSE_CONFIGURATION['ShortTestPulseLowLim'], TESTPULSE_CONFIGURATION['ShortTestPulseHighLim']
            elif i in LongCHs:
                LowLim, HighLim = TESTPULSE_CONFIGURATION['LongTestPulseLowLim'],  TESTPULSE_CONFIGURATION['LongTestPulseHighLim']
            else:
                print(f"[ExtractTestPulse] Channel {i}: not mapped to any PrM type, skipping mask.")
                LowLim, HighLim = -numpy.inf, numpy.inf
            CHData = CHData[
                (CHData[TESTPULSE_CONFIGURATION['BinName']] > LowLim) &
                (CHData[TESTPULSE_CONFIGURATION['BinName']] < HighLim)
            ].reset_index(drop=True)

        # not worth to look at this measurement
        # something must have gone really wrong
        if len(CHData) < 10:
            print(f"[ExtractTestPulse] Channel {i+1}: too few rows after masking, skipping.")
            continue

        # adaptively extract bin edges and adjust if you want
        BinWidth = round(numpy.median(numpy.diff(sorted(CHData[TESTPULSE_CONFIGURATION['BinName']]))), 6)
        BinEdges = numpy.append(
            CHData[TESTPULSE_CONFIGURATION['BinName']] - BinWidth / 2,
            CHData[TESTPULSE_CONFIGURATION['BinName']].iloc[-1] + BinWidth / 2
        )
        if TESTPULSE_CONFIGURATION['Rebin']:
            BinEdges = BinEdges[::2]

        y, bins = numpy.histogram(CHData[TESTPULSE_CONFIGURATION['BinName']], bins=BinEdges, weights=CHData[TESTPULSE_CONFIGURATION['CountName']])
        y = numpy.asarray(y, dtype=float)
        x = numpy.asarray((bins[:-1] + bins[1:]) / 2)

        # roughly extract channel features
        idxMax = numpy.argmax(y)
        posMax = x[idxMax]
        indices = numpy.where(y > 0.1 * max(y))[0]
        if len(indices) < 2:
            print(f"[ExtractTestPulse] Channel {i}: insufficient bins above threshold, skipping")
            continue
        std = (x[indices[-1]] - x[indices[0]]) / 2.355

        # properly initialize the fit
        match TPFitFunction:
            case f if f is Gaus:
                p0 = (numpy.max(CHData[TESTPULSE_CONFIGURATION['CountName']]), posMax, std)
                bounds = (-numpy.inf, numpy.inf)
            case f if f is GausPlusExp:
                b0 = -1.0
                a0 = numpy.mean(y[y <= numpy.percentile(y, 10)]) / numpy.exp(b0 * numpy.median(x))
                p0 = (numpy.max(CHData[TESTPULSE_CONFIGURATION['CountName']]), posMax, std, a0, b0)
                bounds = (-numpy.inf, numpy.inf)
            case f if f is GausPlusLine:
                tail_mask = numpy.abs(x - posMax) > 2 * std
                if numpy.sum(tail_mask) > 1:
                    a0, b0 = numpy.polyfit(x[tail_mask], y[tail_mask], 1)
                    if a0 > 0 or numpy.abs(a0) > 500:
                        a0 = -50.
                        b0 = numpy.mean(y[tail_mask]) - a0 * numpy.mean(x[tail_mask])
                else:
                    a0 = -50.
                    b0 = numpy.mean(y)
                p0 = (numpy.max(CHData[TESTPULSE_CONFIGURATION['CountName']]), posMax, std, a0, b0)
                bounds = (
                    [0,    x[0],  0,    -numpy.inf, -numpy.inf],  # lower
                    [numpy.inf, x[-1], numpy.inf,  0, numpy.inf]  # upper: slope a must be < 0
                )
            case _:
                raise ValueError(f"Unsupported TPFitter: {TPFitFunction.__name__}. Add a case block for it.")

        NPars = len(inspect.signature(TPFitFunction).parameters) - 1

        # perform fit
        try:
            pars, covs = scipy.optimize.curve_fit(
                TPFitFunction, x, y,
                p0      = p0,
                bounds  = bounds,
                maxfev  = 4000
            )
            errs = numpy.sqrt(numpy.diag(covs))
        except (RuntimeError, scipy.optimize.OptimizeWarning):
            print(f"[ExtractTestPulse] Could not perform fit properly here: {MeasurementPath}, {i}")
            print(f"[ExtractTestPulse] Initial guesses: {idxMax}, {std}")
            pars = errs = [numpy.nan] * NPars

        # cap non realistic values...
        if numpy.any(numpy.abs(pars) > 1.e5) or numpy.any(numpy.abs(errs) > 1.e3):
            print(f"[ExtractTestPulse] Fit values not good here: {MeasurementPath}, {i}. Capping.")
            pars = errs = [numpy.nan] * NPars

        # accumulate fitting results
        parss.append(pars)
        errss.append(errs)

        if DEBUG_MODE:
            print(f"[ExtractTestPulse] Candidate peak position: {posMax}")
            print(f"[ExtractTestPulse] Candidate std. dev.: {std}")
            print(f"[ExtractTestPulse] Fit parameters: {pars}")

        Output[f"Peak_CH{i+1}"]      = pars[1] # peak mean
        Output[f"Err_Peak_CH{i+1}"]  = errs[1] # peak mean error
        Output[f"Width_CH{i+1}"]     = pars[2] # peak sigma
        Output[f"Err_Width_CH{i+1}"] = errs[2] # peak sigma error

    if not DEBUG_MODE:
        return Output
    else:
        return [parss, errss]

def DumpCampaigns(
        DataPath
):
    """
        Input
        ---
        DataPath : str
                   Filesystem path containing measurements and mappings.

        Output
        ---
        Provides an array table with paths from all campaigns.
        Ordering: data, times, temperatures.
    """

    CampaignFiles = []

    # go over measurements
    for MeasurementPath in DataPath.glob("[!.]*"):

        # for each measurement, get the files
        for MeasurementElement in MeasurementPath.glob("[!.]*"):

            if "Time" in MeasurementElement.name:
                TimeMapping        = MeasurementElement
            elif "Temperature" in MeasurementElement.name:
                TemperatureMapping = MeasurementElement
            else:
                Data               = MeasurementElement

        CampaignFiles.append([Data, TimeMapping, TemperatureMapping])

    return CampaignFiles

def MergeCampaigns(
    DataPath,
    AnalyzeTimes,
    AnalyzeTemperatures,
    AnalyzeCampaign,
    AnalyzeMeas
):
    """
        Input
        ---
        DataPath : str
                   Filesystem path containing measurements and mappings.

        AnalyzeTimes : func
                       Module to extract the time mapping.

        AnalyzeTemperatures: func
                             Module to extract the temperatures.

        AnalyzeCampaign : func
                          Module that runs the analysis over a campaign.

        Output
        ---
        Provides an array with all measurements and a pandas DataFrame temperatures.
    """

    MergedOutput       = []
    MergedTemperatures = []

    # get files for each campaign
    # ordering: data, times, temperatures
    DataPath      = pathlib.Path(DataPath)
    CampaignFiles = DumpCampaigns(DataPath)

    for Files in zip(CampaignFiles):

        PATH_CAMPAIGN     = Files[0][0]
        PATH_TIMES        = Files[0][1]
        PATH_TEMPERATURES = Files[0][2]

        # get time mapping
        TimeMapping  = AnalyzeTimes(PATH_TIMES)

        # get temperature mapping
        Temperatures = AnalyzeTemperatures(PATH_TEMPERATURES)

        # analyze campaign
        Output       = AnalyzeCampaign(
            PATH_CAMPAIGN,   ###< path to restructured data
            AnalyzeMeas,     ###< analyzing module 
            TimeMapping      ###< file-to-time mapping
        )

        MergedOutput.extend(Output)
        MergedTemperatures.append(Temperatures)

    MergedTemperatures = pandas.concat(
        MergedTemperatures,
        ignore_index = True
    )

    return MergedOutput, MergedTemperatures