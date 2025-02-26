#! /usr/bin/env python
from chemPackage import collect, dressedT
from numpy import linspace, savetxt, array
from chemPackage.constants import PI
import argparse
import matplotlib.pyplot as plt


def main():
    """\
    extract and plot data from an output file. There are two options
     as of now:
    The Raman spectrum of a free molecule or DIM/QM system
    The Raman spectrum calculated with Dressed tensors
    """

    parser = argparse.ArgumentParser(description="This script is used to plot Raman spectra either from "
            "Dressed Tensors or from numerical differentiation of the normal modes for both free "
            "molecule Raman scattering or DIM/QM SERS.")

    parser.add_argument("--dressed", "-d", nargs=2, metavar=("dim.out", "freq.out"),
            type=str, help="Plot the raman spectrum using dressed tensors formalism. "
            "Requires the output from a DIM calculation for the field, and the output "
            "of a frequency calculation. ", dest="dressed", default=None)

    parser.add_argument("--raman", "-r", metavar="freq.out", type=str, 
            help="Plot the raman spectrum directly from the polarizability derivatives. "
            "Requires the output of a frequency calculation", dest="raman", default=None)

    parser.add_argument("--IR", "-i", metavar="freq.out", type=str, 
            help="Plot the IR spectrum directly. "
            "Requires the output of a frequency calculation", dest="IR", default=None)
    # the rest are optional 
    parser.add_argument("--translation","-t", metavar=("x.x","y.y","z.z"), nargs=3,
            default=[0.0,0.0,0.0], type=float, help="Translation of molecule. "
            "Only used for dressed tensors." )

    parser.add_argument("--fwhm", metavar="20", default=20, type=float,
            help="Full width at half max for the peaks in the spectrum")
    
    parser.add_argument("--component", "-c", metavar="xx", default="all", type=str,
            help="Supply the component of the tensor's derivative to calculate Raman intensity")

    parser.add_argument("--scalefactor", metavar="30", default=30,
            type=float, help="This is a scale factor for the y axis.")

    parser.add_argument("--xaxis", metavar=("lower","upper"), nargs=2, type=float,
            help="Supply the range for the x axis of the plot, if not specified "
                 "the range will be automatically selected.", default=[0,2000])

    parser.add_argument("--yaxis", metavar=("lower","upper"), nargs=2, type=float,
            help="Supply the range for the y axis of the plot, if not specified "
                 "the range will be automatically selected.", default=None)

    parser.add_argument("--figname", default=None, type=str, metavar="fig.png",
            help="Supply a name for the figure if it is to be saved") 

    parser.add_argument("--specname", default=None, type=str, metavar="spectrum.txt",
            help="Supply a name for the spectrum file if it is to be saved in xy format") 

    parser.add_argument("--no-sticks", default=True, action='store_false',dest='lsticks',
            help="If included sticks will not be plotted")

    args = parser.parse_args()

    # sanity check: did they choose raman or dressed tensors. If not, give up on them
    #  in a condescending manner, well not really but I would if I could...
    if args.dressed==None and args.raman==None and args.IR == None:
        print("You didn't choose whether this is for dressed tensors or not.")
        exit("Please use the --help option for more information")
    # sanity check: They choose both... Why tho?
    elif args.dressed != None and args.raman != None:
        print("This script is not formatted in a way that allows you to plot multipule "
              "things at once. So you will be forced to run this script twice.")
        exit("Please use the --help option for more information")

    # The first real condition: Dressed Tensors
    #  Because I'm kind (sorta) make it so the order of the file names doesn't effect anything
    #  aren't I the best?
    elif args.dressed != None and args.raman == None:
        temp = collect(args.dressed[0])
        if "DIM" in temp.calctype:
            freqout = collect(args.dressed[1])
            if "FREQUENCIES" in freqout.calctype:
                dimout = temp
            else:
                print("You did not supply a DIM output file and frequency output file.")
                exit("Please use the --help option for more information")
        elif "FREQUENCIES" in temp.calctype:
            dimout = collect(args.dressed[1])
            if "DIM" in dimout.calctype:
                freqout = temp
            else:
                print("You did not supply a DIM output file and frequency output file.")
                exit("Please use the --help option for more information")

        # plot that spectrum 
        dressedTensors(dimout, freqout, args.translation, args.fwhm, args.scalefactor, 
                        args.xaxis, args.yaxis,args.lsticks, args.figname, args.specname)


            
    # The second real condition: Raman by numerical differentiation.
    elif args.raman != None and args.dressed == None:
        freqout = collect(args.raman)
        if "FREQUENCIES" not in freqout.calctype:
            print("You did not supply a frequency output file.")
            exit("Please use the --help option for more information")

        # plot the spectrum
        plotRaman(freqout, args.fwhm, args.scalefactor, args.xaxis, args.yaxis, args.component, 
                  args.lsticks, args.figname, args.specname)

   # The second real condition: Raman by numerical differentiation.
    elif args.IR != None and args.dressed == None:
        freqout = collect(args.IR)
        if "FREQUENCIES" not in freqout.calctype:
            print("You did not supply a frequency output file.")
            exit("Please use the --help option for more information")

        # plot the spectrum
        plotIR(freqout, args.fwhm, args.xaxis, args.yaxis, args.lsticks, args.figname, args.specname)

    else:
        exit("This shouldn't even be possible, I guess I'm not as intellegent as I thought I was."
             " Life sucks, you win.")

        

        

def dressedTensors(dimout, freqout, tr, fwhm, scaleexp, xaxis, yaxis, lsticks, figname, specname):
    """ 
    This function plots the Raman spectrum of a system using the Dressed Tensors 
    formulism.

    dimout      ==> collected output file from a DIM calculation. This file must contain
                    the xyz coordinates of the system as well as the calculated dipoles.
    freqout     ==> collected output file from a frequency calculation.
    tr          ==> Translation vector for the molecule, Used to correctly possition the
                    molecule on the surface
    fwhm        ==> full width half max. Determines the width of the peaks
    scaleexp    ==> scale factor to be applied to the y axis to make reading the axis 
                    easier.
    xaxis       ==> gives the lower and upper bounds for the x-axis. It is supplied in
                    the form of a list. ie. [lower, upper] 
    yaxis       ==> gives the lower and upper bounds for the y-axis. It is supplied in
                    the form of a list. ie. [lower, upper] 
    figname     ==> If it isn't None then this function will save the figure to 
                    filename supplied.
    specname    ==> If it isn't None then this function will save the spectrum in the
                    xy format to the filename supplied.
                    
    """

    # collect the dipole-dipole polarizabilities derivatives and 
    #  the higher order polarizability derivatives. 
    freqout.collect_raman_derivatives()
    freqout.collect_tensor_derivatives()
    
    # find the ceter of mass of the qm system to be used in the 
    mcom = freqout.center_of_mass
    
    
    E,FG = dressedT.dressed_func.return_dim_field(dimout, mcom, tr=tr)
    
    scale = 10**scaleexp
    
    fig = plt.figure()
    
    x,y = dressedT.dressed_spectroscopy(freqout, E=E,FG=FG, gradient=True,  lplot=False)
    
    domain = linspace(0, x*1.5, num=2000)
    y2 = sum_lorentzian(domain, x, y, fwhm=fwhm)
    sub = fig.add_subplot(111)
    sub.plot(domain, y2*scale, 'r')
    # Comment the below three lines to not plot the sticks
    if lsticks:
        # fwhm is converted to hwhm. pi is for normalization
        stickscale = scale / ( ( fwhm / 2 ) * PI )
        sub.stem(x, y*stickscale, 'k-', 'k ', 'k ')
    
   #lab = r'$\mathrm{Differential Cross-Section}$ $\frac{d\sigma}{d\Omega}$ '
    lab = r'Raman Intensity '
    lab += r'($\times 10^{-'+str(scaleexp)+r'}\frac{\mathrm{cm}^2}{\mathrm{sr}}$)'
    sub.set_ylabel(lab)
    sub.set_xlabel(r'$\mathrm{Wavenumber}$ ($\mathrm{cm}^{-1}$)')

    # check if ranges for the specturm were given. If given apply them
    sub.set_xlim(xaxis[0], xaxis[1])
    if yaxis != None:
        sub.set_ylim(yaxis[0], yaxis[1])

    
    if figname != None:
        plt.savefig(figname, dpi=300)
    else:
        plt.show()
        
    if specname != None:
        savetxt(specname, array([domain, y2*scale]).T, fmt=['%.2f', '%4.8g'])

def plotRaman(freqout, fwhm, scaleexp, xaxis, yaxis, component, lsticks, figname, specname):
    """ 
    This function plots the Raman spectrum of a system using numerical 
    differentiation around the normal modes. 

    freqout     ==> collected output file from a frequency calculation.
    fwhm        ==> full width half max. Determines the width of the peaks
    scaleexp    ==> scale factor to be applied to the y axis to make reading the axis 
                    easier.
    xaxis       ==> gives the lower and upper bounds for the x-axis. It is supplied in
                    the form of a list. ie. [lower, upper] 
    yaxis       ==> gives the lower and upper bounds for the y-axis. It is supplied in
                    the form of a list. ie. [lower, upper] 
    component   ==> gives the component of the polarizability tensor for which the
                    Raman spectrum is to be calculated
    figname     ==> If it isn't None then this function will save the figure to 
                    filename supplied.
    specname    ==> If it isn't None then this function will save the spectrum in the
                    xy format to the filename supplied.
    """
    # good news, because the chem package is so great this works for both
    #  the Raman of the free molecule and SERS calculated with DIM/QM

    # collect the dipole-dipole polarizabilities derivatives
    freqout.collect_raman_derivatives()
    # calculate the raman cross section for the system.
    raman_intensity = freqout.cross_section(component=component)
    
    scale = 10**scaleexp
    
    fig = plt.figure()
    
    domain = linspace(0, freqout.v_frequencies[-1]*1.5, num=2000)
    y2 = sum_lorentzian(domain, freqout.v_frequencies, raman_intensity, fwhm=fwhm)
    sub = fig.add_subplot(111)
    sub.plot(domain, y2*scale, 'r')
    if lsticks:
        # fwhm is converted to hwhm. pi is for normalization
        stickscale = scale / ( ( fwhm / 2 ) * PI )
        sub.stem(freqout.v_frequencies, raman_intensity*stickscale, 'k-', 'k ', 'k ')
    
   #lab = r'$\mathrm{Differential Cross-Section}$ $\frac{d\sigma}{d\Omega}$ '
    lab = r'Raman Intensity '  
    lab += r'($\times 10^{-'+str(scaleexp)+r'}\frac{\mathrm{cm}^2}{\mathrm{sr}}$)'
    sub.set_ylabel(lab)
    sub.set_xlabel(r'$\mathrm{Wavenumber}$ ($\mathrm{cm}^{-1}$)')

    # check if ranges for the specturm were given. If given apply them
    sub.set_xlim(xaxis[0], xaxis[1])
    if yaxis != None:
        sub.set_ylim(yaxis[0], yaxis[1])
    
    if figname != None:
        plt.savefig(figname, dpi=300)
    else:
        plt.show()
    
    if specname != None:
        savetxt(specname, array([domain, y2*scale]).T, fmt=['%.2f', '%4.8g'])

def plotIR(freqout, fwhm, xaxis, yaxis, lsticks, figname, specname):
    """ 
    This function plots the Raman spectrum of a system using numerical 
    differentiation around the normal modes. 

    freqout     ==> collected output file from a frequency calculation.
    fwhm        ==> full width half max. Determines the width of the peaks
    xaxis       ==> gives the lower and upper bounds for the x-axis. It is supplied in
                    the form of a list. ie. [lower, upper] 
    figname     ==> If it isn't None then this function will save the figure to 
                    filename supplied.
    specname    ==> If it isn't None then this function will save the spectrum in the
                    xy format to the filename supplied.                
    """

    fig = plt.figure()
    sub = fig.add_subplot(111)

    domain = linspace(0, freqout.v_frequencies[-1]*1.5, num=2000)
    y = sum_lorentzian(domain, freqout.v_frequencies, freqout.IR, fwhm=fwhm)
    sub.plot(domain, y)

    if lsticks:
        # fwhm is converted to hwhm. pi is for normalization
        stickscale = 1.0 / ( ( fwhm / 2 ) * PI )
        sub.stem(freqout.v_frequencies, freqout.IR*stickscale, 'k-','k ', 'k ')
        

    # check if ranges for the specturm were given. If given apply them
    sub.set_xlim(xaxis[0], xaxis[1])
    if yaxis != None:
        sub.set_ylim(yaxis[0], yaxis[1])

    if figname != None:
        plt.savefig(figname, dpi=300)
    else:
        plt.show()
    
    if specname != None:
        savetxt(specname, array([domain, y]).T, fmt=['%.2f', '%4.8g'])


def lorentzian(x, peak=0, height=1.0, fwhm=None, hwhm=None):
    '''Calculates a three-parameter lorentzian for a given domain.'''
    if fwhm is not None and hwhm is not None:
        raise ValueError ('lorentzian: Onle one of fwhm or hwhm must be given')
    elif fwhm is not None:
        gamma = fwhm / 2
    elif hwhm is not None:
        gamma = hwhm
    else:
        gamma = 0.1
    # pi is included as a normalization factor
    return  ( height / PI ) * ( gamma / ( ( x - peak )**2 + gamma**2 ) )

def sum_lorentzian(x, peak=None, height=None, fwhm=None, hwhm=None):
    '''Calculates and sums several lorentzians to make a spectrum.

    'peak' and 'height' are numpy arrays of the peaks and heights that
    each component lorentzian has.
    '''
    from numpy import array
    if peak is None or height is None:
        raise ValueError ('Must pass in values for peak and height')
    if peak.shape != height.shape:
        raise ValueError ('peak and height must be the same shape')

    l = lorentzian
    y = array([l(x,peak[i], height[i], fwhm, hwhm) for i in range(len(peak))])
    return y.sum(axis=0)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        import sys
        sys.exit(1)


