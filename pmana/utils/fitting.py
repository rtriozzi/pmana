import numpy

def Gaus(
    x, 
    A, 
    Mu, 
    S
):
    """
        Simple Gaussian fitting function.
    """

    return A * numpy.exp(- (x - Mu)**2 / (2 * S**2))

def TripleGaus(
    x, 
    A, 
    Mu, 
    S
):
    """
        Triple Gaussian fitting function, based on the known
        intensity lines for the merged IC peak.
    """

    return A * (
        numpy.exp(- (x - Mu)**2 / (2 * S**2)) + \
        0.262 * numpy.exp(- (x - Mu * 1.0747)**2 / (2 * S**2)) + \
        0.077 * numpy.exp(- (x - Mu * 1.0861)**2 / (2 * S**2))
    )

def GausPlusExp(
    x, 
    A, 
    Mu, 
    S, 
    a, 
    b
):
    """
        Gaussian with exponential background.
    """
    return A * numpy.exp(- (x - Mu)**2 / (2 * S**2)) + a * numpy.exp(b * x)

def GausPlusLine(
    x, 
    A, 
    Mu, 
    S, 
    a, 
    b
):
    """
        Gaussian with exponential background.
    """
    return A * numpy.exp(- (x - Mu)**2 / (2 * S**2)) + a * x + b

def Line(
    x,
    a,
    b
):
    return a * x + b

def LineErrorBand(
    x, 
    cov # covariance matrix from `scipy.optimize.curve_fit`
):
    da2 = cov[0, 0]
    db2 = cov[1, 1]
    dab = cov[0, 1]

    return numpy.sqrt(x**2 * da2 + db2 + 2*x*dab)