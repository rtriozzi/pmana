import numpy
import scipy

from pmana.utils.fitting import Gaus

def PlotTimeSeriesWithErrors(
    ax,
    Date,
    Peak,
    PeakError,
    LABEL = '',
    XLABELS = True
):

    """
        Plot a time series with errors on y.

        ---
        Input:

        ax: matplotlib axes obj
            Axes whose settings need to be tweaked.
        
        Date: array-like
              Data for the x axis.

        Peak: array-like
              Data for the y axis.

        PeakError: array-like
                   Errors for data for the y axis.
              
        ---
        Output:     

        Updated matplotlib axes.           
    """

    ax.plot(
        Date, Peak, 
        lw=1
    )
    ax.fill_between(
        Date, Peak-PeakError, Peak+PeakError, 
        alpha=0.3, label=LABEL
    )
    if not XLABELS:
        ax.set_xticklabels([])

    return ax

def PlotTimeSeries(
    ax,
    Date,
    Peak,
    LABEL = '',
    XLABELS = True
):

    """
        Plot a time series with errors on y.

        ---
        Input:

        ax: matplotlib axes obj
            Axes whose settings need to be tweaked.
        
        Date: array-like
              Data for the x axis.

        Peak: array-like
              Data for the y axis.
              
        ---
        Output:     

        Updated matplotlib axes.           
    """

    ax.plot(
        Date, Peak, 
        lw=1, label=LABEL
    )
    if not XLABELS:
        ax.set_xticklabels([])

    return ax

def UpdateMatplotlibStyle(
    ax,
    xlabel,
    ylabel
):
    
    """
        Tweak matplotlib settings.

        ---
        Input:

        ax: matplotlib axes obj
            Axes whose settings need to be tweaked.
        
        xlabel: str
                Label for the x axis.

        ylabel: str
                Label for the y axis.

        ---
        Output:     

        Updated matplotlib axes.           
    """

    # labels
    ax.set_xlabel(xlabel, fontsize=14, loc='right')
    ax.set_ylabel(ylabel, fontsize=14, loc='top')
    ax.legend(frameon=True, fancybox=False, handlelength=1, loc='best')

    # ticks
    ax.minorticks_on()
    ax.tick_params(which='major', length=6, direction='in', labelsize=12, right=True, top=True)
    ax.tick_params(which='minor', length=3, direction='in', right=True, top=True)

    return ax
    

def PlotSingleChannel(
    CHData,
    ax,
    channel = 0,
    rebin = False,
    debug = False,
    DISPLAY_FIT = True,
    SKIP_NROWS = 0,
    BINNAME = 'BinCenter',
    COUNTNAME = 'Population'
):
    """
        Plot the content of a channel, 
        given the parsed channel data.

        ---
        Input:

        CHData: dataframe-like
                Parsed channel data, coming from an oscilloscope
                or a multi channel analyzer.
                Data is already binned.

        ax: matplotlib axes obj

        channel: int, optional
                 Channel number. Useful to get
                 consistent color-coding for plots
                 with multiple channels.

        ---
        Output:

        Plot the channel data. Returns None.
    """

    if SKIP_NROWS > 0:
        print(f"Skipping the first {SKIP_NROWS} rows.")
        CHData = CHData.iloc[SKIP_NROWS:].reset_index(drop=True)

    # adaptively extract bin edges
    Diffs = numpy.diff(sorted(CHData[BINNAME]))
    BinWidth = round(numpy.median(Diffs), 6)
    BinEdges = numpy.append(CHData[BINNAME] - BinWidth / 2, CHData[BINNAME].iloc[-1] + BinWidth / 2)
    if rebin:
        BinEdges = BinEdges[::2]
    
    # plot channel data
    y, bins, _ = ax.hist(
        CHData[BINNAME],
        bins = BinEdges,
        weights = CHData[COUNTNAME],
        alpha=0.5,
        histtype='stepfilled',
        label=f'CH{channel}',
        fc=f'C{channel}',
        ec=f'C{channel}'
    )
    x = (bins[:-1] + bins[1:]) / 2

    if DISPLAY_FIT:
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
        except RuntimeError:
            print(f"Could not perform fit for channel {channel}.")
            print(f"Initial guesses: {idxMax}, {std}")
            pars = numpy.ones(3)
            errs = numpy.ones(3)
        
        if debug:
            print(f"Peak position: {posMax}")
            print(f"Candidate std. deviation: {std}")
            print(f"Fit parameters: {pars}")

        # plot fit
        ax.plot(
            x,
            Gaus(x, *pars),
            c=f'C{channel}'
        )

    return None