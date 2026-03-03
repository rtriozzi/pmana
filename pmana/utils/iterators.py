import pathlib
import os
import datetime

def IterateCERN_CSV(
    CampaignPath,
    Analyze,
    START_FROM = None,
    EXCLUDE_DATE = None
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
    MONTH_ABBR = {
        'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
        'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
    }

    for FilePath in sorted(CampaignPath.glob("Record_*.csv")):

        # parse filename: Record_2026_Mar_02_18_22.csv
        _, year, month, day, hour, minute = FilePath.stem.split("_")

        # extract date
        t = datetime.datetime(
            year = int(year), 
            month = int(MONTH_ABBR[month]), 
            day = int(day), 
            hour = int(hour), 
            minute = int(minute))
        
        # skip everything before the cutoff...
        if START_FROM is not None and t < START_FROM:
            continue  

        # skip problematic dates...
        if EXCLUDE_DATE is not None and t in EXCLUDE_DATE:
            continue
        
        # analyze the measurement
        CHOutput = Analyze(FilePath)

        # add date
        CHOutput.extend([t])

        Output.append(CHOutput)
      
    return Output