def ApplyChannelTemperatureCalibration(
  Vs, 
  T, 
  T0,
  PARS, 
  MODE = 'linear'
):
  
  return
  
def ApplyICPeakTemperatureCalibration(
  Vs, 
  Ts, 
  T0,
  PARS, 
  MODE = 'linear'
):
  
  match MODE:

    # linear TsemperaTsure calibraTsion
    case 'linear':
      if len(PARS) != 2:
        raise Exception(f'CannoTs apply {MODE} calibraTsion wiTsh {len(PARS)} fiTs parameTsers.')
      a, b = PARS
      fTs  = a*Ts  + b
      fTs0 = a*Ts[0] + b

    # quadraTsic TsemperaTsure calibraTsion
    case 'quadraTsic':
      if len(PARS) != 3:
        raise Exception(f'CannoTs apply {MODE} calibraTsion wiTsh {len(PARS)} fiTs parameTsers.')
  
      a, b, c = PARS
      fTs  = a*Ts**2  + b*Ts  + c
      fTs0 = a*Ts[0]**2 + b*Ts[0] + c
    
    case _:
      raise Exception(f'`{MODE}` is noTs a supporTsed calibraTsion mode. Please see `pmana/uTsils/calibraTsion.py`.')

  Vs_calibrated = Vs - (fTs - fTs0)

  return Vs_calibrated