import os
import glob
import numpy
import pandas
import scipy
import pathlib
import datetime

from pmana.utils.io import ExtractSingleMeasurement, ExtractFileTimes
from pmana.utils.fitting import Gaus

def Iterate(
    CampaignPath,
    Analyze,
    TimeMapping,
    DIR_KEY = '0*'
):
    """
        Input
        ---
        CampaignPath :  str
                        Filesystem path containing measurements.
        
        Analyze : function
                  Analyzer function acting on a measurement.

        TimeMapping : dataframe
                      Mapping between times and filenames.

        Output
        ---
        Provides an array with the results.
    """

    CampaignPath = pathlib.Path(CampaignPath)

    Output = []

    # loop over measurements in the campaign
    for MeasurementPath in CampaignPath.glob(DIR_KEY):

        # analyze the measurement
        CHOutput = Analyze(MeasurementPath)

        # get the measurement time
        if TimeMapping is not None: 
            MeasurementPaths = glob.glob(str(MeasurementPath) + "/*")
            if not MeasurementPaths:
                print(f"No time mapping for {MeasurementPath}")
                continue
            t = TimeMapping[TimeMapping['FileName'] == os.path.basename(MeasurementPaths[0])].iloc[0]['Date']
        else:
            t = datetime.datetime.strptime(
                os.path.basename(MeasurementPath), 
                "%Y%m%d_%H%M%S"
            )

        # get measurement number
        n = int(os.path.basename(MeasurementPath))

        CHOutput.extend([t, n])
        Output.append(CHOutput)

    return Output

def IterateCERN(
    CampaignPath,
    Analyze,
    YEAR = 2025,
    MONTH = 12
):
    """
        In the CERN data structure, directory tells the time.
        Measurements are orgainzed in days, hour, minutes.

        Input
        ---
        CampaignPath :  str
                        Filesystem path containing measurements.
        
        Analyze : function
                  Analyzer function acting on a measurement.

        Output
        ---
        Provides an array with the results.
    """

    CampaignPath = pathlib.Path(CampaignPath)

    Output = []

    # days
    for DayPath in CampaignPath.glob('*'):
        if not os.path.basename(DayPath).isnumeric():
            continue 
        Day = int(os.path.basename(DayPath))

        # hours
        for HourPath in DayPath.glob("*"):
            Hour = int(os.path.basename(HourPath))

            # minutes
            for MinutePath in HourPath.glob("*"):
                Minute = int(os.path.basename(MinutePath))

                # analyze the measurement
                CHOutput = Analyze(MinutePath)

                ### extract date
                t = datetime.datetime(
                    year = YEAR, 
                    month = MONTH, 
                    day = Day, 
                    hour = Hour, 
                    minute = Minute)

                CHOutput.extend([t])
                Output.append(CHOutput)
                
    return Output

def GaussianFitToChannel(
    MeasurementPath,
    rebin = False,
    debug = False,
    IS_DT5781 = False,
    DELIMITER = ';',
    MASK_TESTPULSE = False,
    SKIP_NROWS = 0,
    BINNAME = 'BinCenter',
    COUNTNAME = 'Population'
):
    """
        Analyze a single measurement, extracting for each channel
        the mean and the standard deviation from a Gaussian fit,
        along with their fit errors.

        Input
        ---
        MeasurementPath : str
                          Filesystem path containing measurements.
        
        rebin : bool, optional

        debug : bool, optional

        BINNAME : string, optional

        COUNTNAME : string, optional

        Output
        ---
        Provides a Pandas dataframe with the results.
    """

    Output = []

    # extract measurement data
    if IS_DT5781:
        Data = ExtractSingleMeasurement(MeasurementPath,
            CHANNEL_KEY = 'CH*', N_SKIP_LINES = 3, COL_NAMES = ['c0', 'c1', 'c2'], DELIMITER = ' ')
    else:
        Data = ExtractSingleMeasurement(MeasurementPath,
            DELIMITER = DELIMITER)

    if debug:
        print(f"[Analyze] Extracted {len(Data)} channels")

    for i, CHData in enumerate(Data):

        if SKIP_NROWS > 0:
            CHData = CHData.iloc[SKIP_NROWS:].reset_index(drop=True)

        # dedicated test-pulse analysis        
        if MASK_TESTPULSE:
            if i is not 2:
                CHData = CHData[CHData[BINNAME] > 1.25].reset_index(drop=True)

        # avoid empty channels
        if len(CHData) < 10:
            continue
        
        # adaptively extract bin edges
        Diffs = numpy.diff(sorted(CHData[BINNAME]))
        BinWidth = round(numpy.median(Diffs), 6)
        BinEdges = numpy.append(CHData[BINNAME] - BinWidth / 2, CHData[BINNAME].iloc[-1] + BinWidth / 2)
        if rebin:
            BinEdges = BinEdges[::2]

        # binned channel data
        y, bins = numpy.histogram(
            CHData[BINNAME],
            bins = BinEdges,
            weights = CHData[COUNTNAME]
        )
        x = (bins[:-1] + bins[1:]) / 2

        # extract channel features
        idxMax = numpy.argmax(y); posMax = x[idxMax] ###< peak position in ticks
        # std = (max(x) - min(x)) / 2.355
        indices = numpy.where(y > 0.1 * max(y))[0]
        std = (x[indices[-1]] - x[indices[0]]) / 2.355

        # perform Gaussian fit of channel
        try:
            pars, covs = scipy.optimize.curve_fit(
                Gaus, 
                x,
                y,
                p0 = (numpy.max(CHData[COUNTNAME]), posMax, std),
                maxfev=1000
            )
            errs = numpy.sqrt(numpy.diag(covs))
        except RuntimeError:
            print(f"[Analyze] Could not perform fit here: {MeasurementPath}, {i}")
            print(f"[Analyze] Initial guesses: {idxMax}, {std}")
            pars = numpy.ones(3)
            errs = numpy.ones(3)

        if debug:
            print(f"[Analyze] Peak position: {posMax}")
            print(f"[Analyze] Candidate std. deviation: {std}")
            print(f"[Analyze] Fit parameters: {pars}")

        Output.append(pars[1]) ###< peak
        Output.append(errs[1]) ###< peak error
        Output.append(pars[2]) ###< width
        Output.append(errs[2]) ###< peak error

    return Output

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