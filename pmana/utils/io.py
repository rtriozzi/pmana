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
    DELIMITER = ' ',
    COL_NAMES = ['DateRaw', 'Time', 'T1', 'T2']
):
    """
        Extracts the temperatures from a dedicated monitor,
        and their absolute times.

        Input
        ---
        TemperatureLog: csv-like
                        Temperature log file.
                        Needs a bit of formatting by hand.

        DELIMITER: str, optional
                   Delimiter to extract dataframe from txt file.

        COL_NAMES: array of str, optional
                   The variables in the input txt files.

        Output
        ---
        Returns a Pandas dataframe contaning times and temperatures
        from all available sensors.
    """

    FileTemperatures = pandas.read_csv(
        TemperatureLog,
        delimiter = DELIMITER,
        engine = 'python',
        names = COL_NAMES
    )
    FileTemperatures['Date'] = pandas.to_datetime(FileTemperatures['DateRaw'] + ' ' + FileTemperatures['Time'], format='%d.%m.%Y %H:%M')
    FileTemperatures['Date_Shifted'] = FileTemperatures['Date'] + pandas.Timedelta(minutes=12) ###< Known delay

    return FileTemperatures