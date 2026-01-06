import pathlib
import re
import shutil
import glob
import os
import pandas
import datetime

def FormatPadovaData(
    InputPath,
    TargetPath,
    REGEXSTRING = r"--(\d{5})\.txt$"
):
    """
        Re-format the flat data structure from the Padova test-stand
        to make it structured as the one from CERN.
        This makes it easier to apply analysis routines, and
        it is better for bookkeeping.

        Input
        ---
        InputPath : str
                    Input filesystem path.

        TargetPath : str
                     Target filesystem path.

        REGEXSTRING : str, optional
                      Regex key to look for measurement numbers.

        Output
        ---
        Creates a structured directory. Returns None.
    """

    InputPath = pathlib.Path(InputPath)
    TargetPath = pathlib.Path(TargetPath)

    if not InputPath.exists() or not InputPath.is_dir():
        print(f"Input path {InputPath} does not exist or you don't have access.")

    # loop over the files in the flat data directory
    for FilePath in InputPath.glob("*.txt"):

        # extract measurement number from filename via regex
        FileName = FilePath.name
        match = re.search(REGEXSTRING, FileName)
        if not match:
            print(f"Skipping unrecognized file: {FileName}")
            continue
        MeasurementNumber = match.group(1) 

        # create directory for the corresponding measurement
        MeasurementDirectory = TargetPath/MeasurementNumber
        MeasurementDirectory.mkdir(parents=True, exist_ok=True)

        # copy the file
        shutil.copy(
            FilePath, 
            MeasurementDirectory/FileName
        )

    return None

def FormatDT5781Data(
    InputPath,
    TargetPath,
    REGEXSTRING = r"_(\d{8}_\d{6})\.txt3$" ###< or r"(?:.*_)?([^_]+_[^_]+)\.txt3$" 
):
    """
        Organize data files from the CAEN DT5781 into 
        folders named by their timestamp.

        Example filename:
        CH0@DT5781_-6842_Espectrum_run_20251124_163026.txt3
                                        ^^^^^^^^^^^^^^^ <- timestamp

        Input
        ---
        InputPath : str
                    Input filesystem path.

        TargetPath : str
                     Target filesystem path.

        REGEXSTRING : str, optional
                      Regex for extracting the timestamp (default matches YYYYMMDD_HHMMSS).

        Output
        ---
        Creates a structured directory. Returns None.
    """

    InputPath = pathlib.Path(InputPath)
    TargetPath = pathlib.Path(TargetPath)

    if not InputPath.exists() or not InputPath.is_dir():
        print(f"Input path {InputPath} does not exist or you don't have access.")

    # loop over the files in the flat data directory
    for FilePath in InputPath.glob("*.txt3"):

        # extract measurement time from filename via regex
        FileName = FilePath.name
        match = re.search(REGEXSTRING, FileName)
        if not match:
            print(f"Skipping unrecognized file: {FileName}")
            continue
        Timestamp = match.group(1)  ###< e.g., "20251124_163026"

        # create directory for the corresponding measurement
        TimestampDir = TargetPath/Timestamp
        TimestampDir.mkdir(parents=True, exist_ok=True)

        # copy the file
        shutil.copy(
            FilePath, 
            TimestampDir / FileName
        )

    return None

def FormatDT5781RawData(
    InputPath,
    TargetPath,
    REGEXSTRING = r"DataR_CH(\d+)@DT5781_.*\.CSV$"
):
    """
        Organize raw CSV data files from the CAEN DT5781 into 
        folders named by their timestamp.
        Raw data files provide an energy measurement and a timestamp 
        in picoseconds per channel, and can be grouped as one wants.
        Since there are a lot of measurements, files are chopped
        at a configurable rate (e.g., every 10 MB).

        Example filename:
        DataR_CH0@DT5781_-6842_run.CSV

        Input
        ---
        InputPath : str
                    Input filesystem path.

        TargetPath : str
                     Target filesystem path.

        REGEXSTRING : str, optional
                      Regex used to extract the channel number.
                      Default extracts the "CHX" from filenames 
                      like DataR_CH1@DT5781_... 

        Output
        ---
        Creates a structured directory. Returns None.
    """

    InputPath = pathlib.Path(InputPath)
    TargetPath = pathlib.Path(TargetPath)

    if not InputPath.exists() or not InputPath.is_dir():
        print(f"Input path {InputPath} does not exist or you don't have access.")

    # loop over the files in the flat data directory
    for FilePath in InputPath.glob("*.CSV"): 

        FileName = FilePath.name

        # extract channel number via regex
        match = re.search(REGEXSTRING, FileName)
        if not match:
            print(f"Skipping unrecognized file: {FileName}")
            continue

        ChannelNumber = match.group(1)  # e.g., "0", "1", ...

        # create directory for this channel
        ChannelDir = TargetPath / f"CH{ChannelNumber}"
        ChannelDir.mkdir(parents=True, exist_ok=True)

        # copy the file
        shutil.copy(
            FilePath,
            ChannelDir / FileName
        )

    return None

def PandasizeDT5781RawData(
    ChannelPath,
    N_SKIP_LINES = 2,
    COL_NAMES = ['board', 'channel', 'timetag', 'energy', 'flags'],
    DELIMITER = ';',
    TIME_VAR = 'timetag'
):
    """
        Extract a pandas dataframe from the raw CSV data files,
        for a given channel.

        Input
        ---
        ChannelPath : str
                      Input filesystem path with raw CSV channel data.

        Output
        ---
        Returns a Pandas dataframe.
    """

    ChannelPath = pathlib.Path(ChannelPath)
    dfs = []

    # merge all chopped raw data files into a df
    for ChannelData in ChannelPath.glob("*.CSV"): 
        df = pandas.read_csv(
            ChannelData, 
            skiprows=N_SKIP_LINES, names=COL_NAMES, delimiter=DELIMITER
        )
        dfs.append(df)
    channel_df = pandas.concat(dfs, ignore_index=True)

    # sort by time and add progressive time in seconds
    channel_df[TIME_VAR] = channel_df[TIME_VAR].astype(int)
    channel_df = channel_df.sort_values(TIME_VAR).reset_index(drop=True)
    channel_df['time'] = (channel_df[TIME_VAR] - channel_df[TIME_VAR].iloc[0]) * 1.e-12 ###< [s]

    # handle types sensibly
    channel_df['flags'] = channel_df['flags'].apply(
        lambda x: int(x, 16) if pandas.notna(x) else -1
    )
    channel_df['energy'] = channel_df['energy'].apply(
        lambda x: int(x) if pandas.notna(x) else -1
    )

    # clean this up, just a bit
    channel_df = channel_df[channel_df['energy'] > -1]

    # create time bins with various flavors
    channel_df['time_bin_1min']  = (channel_df['time'] // 60).astype(int)
    channel_df['time_bin_5min']  = (channel_df['time'] // 300).astype(int)
    channel_df['time_bin_10min'] = (channel_df['time'] // 600).astype(int)
    channel_df['time_bin_30min'] = (channel_df['time'] // 1800).astype(int)

    # pickle this up
    PATH = str(ChannelPath) + "/" + ChannelPath.name + ".pkl"
    channel_df.to_pickle(PATH)
    print(f"Saved merged DataFrame to: {PATH}")

    return channel_df

def ExtractSingleMeasurement(
    FilePath,
    CHANNEL_KEY = 'F*',
    N_SKIP_LINES = 5,
    COL_NAMES = ['BinCenter', 'Population'],
    DELIMITER = ';'
):
    """
        Input
        ---
        FilePath : str
                   File name with path.

        Output
        ---
        Provides channel data to be analyzed or plotted.
        Returns a list of dataframes.
    """

    # Find and sort all files starting with 'F'
    FileList = sorted(glob.glob(os.path.join(FilePath, CHANNEL_KEY)))

    # Read all files into a list of DataFrames
    Data = [
        pandas.read_csv(f, skiprows=N_SKIP_LINES, names=COL_NAMES, delimiter=DELIMITER)
        for f in FileList
    ]

    return Data

def ExtractFileTimes(
    TimeMapping,
    DELIMITER = '  ',
    COL_NAMES = ['Length', 'Date', 'Name']
):
    """
        Extracts a map between directories and files,
        and the time they were created. This is useful to
        make time-based analyses. The map is stored as Pandas
        DataFrame.

        Input
        ---
        TimeMapping: csv-like
                     Time mapping as extracted from:
                     unzip -l <DataSet>.zip > TimeMapping.txt
                     Needs a bit of formatting by hand.

        DELIMITER: str, optional
                   Delimiter to extract dataframe from txt file.

        COL_NAMES: array of str, optional
                   The variables in the input txt files.

        Output
        ---
        Returns a Pandas dataframe contaning directory names, file names,
        and times (e.g., elapsed time, or absolute time).
    """

    FileTimes = pandas.read_csv(
        TimeMapping,
        delimiter = DELIMITER,
        engine = 'python',
        names = COL_NAMES
    )
    FileTimes['FileName'] = FileTimes['Name'].apply(os.path.basename)
    FileTimes['Date'] = FileTimes['Date'].apply(lambda date: datetime.datetime.strptime(date, "%m-%d-%Y %H:%M"))

    return FileTimes

def ExtractTemperatureMonitoring(
    TemperatureLog,
    IsPadova = True,
    **kwargs
):
    """
        Extracts the temperatures from a dedicated monitor,
        and their absolute times.

        Input
        ---
        TemperatureLog: csv-like
                        Temperature log file.
                        Needs a bit of formatting by hand.

        **kwargs: arguments or dict-like
                  Keyword arguments forwarded to pandas.read_csv.
                  Defaults:
                    delimiter = " "
                    names = ["DateRaw", "Time", "T1", "T2"]

        Output
        ---
        Returns a Pandas dataframe contaning times and temperatures
        from all available sensors.
    """

    defaults = dict(
        delimiter = " ",
        names = ["DateRaw", "Time", "T1", "T2"],
        engine = "python",
    )
    kwargs = {**defaults, **kwargs}

    FileTemperatures = pandas.read_csv(
        TemperatureLog,
        **kwargs
    )

    if IsPadova:
        FileTemperatures['Date'] = pandas.to_datetime(
            FileTemperatures['DateRaw'] + ' ' + FileTemperatures['Time'], 
            format='%d.%m.%Y %H:%M'
        )
        FileTemperatures['Date_Shifted'] = FileTemperatures['Date'] + pandas.Timedelta(minutes=12) ###< Known delay

    return FileTemperatures