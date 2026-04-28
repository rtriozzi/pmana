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