import os
import glob
import numpy
import pandas
import scipy

from pmana.utils.io import ExtractSingleMeasurement, ExtractFileTimes
from pmana.utils.fitting import Gaus

def Iterate(
    CampaignPath,
    Analyze,
    TimeMapping
):
    """
        Input
        ---
        CampaignPath :  pathlib.Path-like
                        Filesystem path containing measurements.
        
        Analyze : function
                  Analyzer function acting on a measurement.

        TimeMapping : dataframe
                      Mapping between times and filenames.

        Output
        ---
        Provides a Pandas dataframe with the results.
    """

    Output = []

    # loop over measurements in the campaign
    for MeasurementPath in CampaignPath.glob("0*"):

        # analyze the measurement
        CHOutput = Analyze(MeasurementPath)

        # get the measurement time
        MeasurementPaths = glob.glob(str(MeasurementPath) + "/F*")
        t = TimeMapping[TimeMapping['FileName'] == os.path.basename(MeasurementPaths[0])].iloc[0]['Date']

        # get measurement number
        n = int(os.path.basename(MeasurementPath))

        CHOutput.extend([t, n])
        Output.append(CHOutput)

    Output = pandas.DataFrame(Output)

    return Output

def AnalyzeMeasurement(
    MeasurementPath,
    rebin = False,
    debug = False,
    BINNAME = 'BinCenter',
    COUNTNAME = 'Population'
):
    
    Output = []

    # extract measurement data
    Data = ExtractSingleMeasurement(MeasurementPath)
    NCHs = len(Data) ###< number of channels in this campaign

    for CHData in Data:

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
        std = (max(x) - min(x)) / 2

        # perform Gaussian fit of channel
        pars, covs = scipy.optimize.curve_fit(
            Gaus, 
            x,
            y,
            p0 = (numpy.max(CHData[COUNTNAME]), posMax, std),
            maxfev=1000
        )
        errs = numpy.sqrt(numpy.diag(covs))
        if debug:
            print(f"Peak position: {posMax}")
            print(f"Candidate std. deviation: {std}")
            print(f"Fit parameters: {pars}")

        Output.append(pars[1]) ###< peak
        Output.append(errs[1]) ###< peak error
        Output.append(pars[2]) ###< width
        Output.append(errs[2]) ###< peak error

    return Output