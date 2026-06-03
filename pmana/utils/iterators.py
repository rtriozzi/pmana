import os
import pathlib
import glob

import datetime

import inspect

from pmana.utils.io import GetTimestampFromCSVName 

### filtering
def _apply_time_filters(
    t, 
    START_FROM      = None, 
    END_AT          = None, 
    EXCLUDE_DATE    = None, 
    EXCLUDE_WINDOW  = None
):
    # skip everything before the cutoff...
    if START_FROM is not None and t <= START_FROM:
        return True
    
    # skip everything after the cutoff...
    if END_AT is not None and t >= END_AT:
        return True
    
    # skip problematic dates...
    if EXCLUDE_DATE is not None and t in EXCLUDE_DATE:
        return True
    
    # skip problematic dates in a window...
    if EXCLUDE_WINDOW is not None and any(w[0] <= t <= w[1] for w in EXCLUDE_WINDOW):
        return True
    
    return False

### iterators
def IterateCERN_CSV(
    CampaignPath,
    Analyze,
    START_FROM = None,
    END_AT = None,
    EXCLUDE_DATE = None,
    EXCLUDE_WINDOW = None
):
    """
        In the CERN data structure with CSV files, time can be
        extracted directly from the name.

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

    for FilePath in sorted(CampaignPath.glob("Record_*.csv")):

        # parse filename: Record_2026_Mar_02_18_22.csv
        t = GetTimestampFromCSVName(FilePath)
        
        # apply time filters
        if _apply_time_filters(t, START_FROM, END_AT, EXCLUDE_DATE, EXCLUDE_WINDOW):
            continue

        # analyze the measurement
        if "Timestamp" in inspect.signature(Analyze).parameters:
            CHOutput = Analyze(FilePath, Timestamp=t)
        else:
            CHOutput = Analyze(FilePath)

        # add date and append
        if isinstance(CHOutput, dict):
            CHOutput['Date'] = t
            Output.append(CHOutput)
        else:
            CHOutput.extend([t])
            Output.append(CHOutput)
      
    return Output

def IterateCERN(
    CampaignPath,
    Analyze,
    YEAR = 2025,
    MONTH = 12,
    START_FROM = None,
    END_AT = None,
    EXCLUDE_DATE = None,
    EXCLUDE_WINDOW = None
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

    # remind the user that years and months are hardcoded in this structure...
    print(f'[IterateCERN] Iterating over year {YEAR} and month {MONTH}... did you check the time of the year?')

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

                # extract date
                t = datetime.datetime(
                    year = YEAR, 
                    month = MONTH, 
                    day = Day, 
                    hour = Hour, 
                    minute = Minute)
                                        
                # apply time filters
                if _apply_time_filters(t, START_FROM, END_AT, EXCLUDE_DATE, EXCLUDE_WINDOW):
                    continue

                # analyze the measurement
                if "Timestamp" in inspect.signature(Analyze).parameters:
                    CHOutput = Analyze(MinutePath, Timestamp=t)
                else:
                    CHOutput = Analyze(MinutePath)

                # add date and append
                if isinstance(CHOutput, dict):
                    CHOutput['Date'] = t
                    Output.append(CHOutput)
                else:
                    CHOutput.extend([t])
                    Output.append(CHOutput)
                
    if len(Output) == 0:
        print(f'[IterateCERN] Output length is zero. Did you *really* check the time of the year?')

    return Output

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