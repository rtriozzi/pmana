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