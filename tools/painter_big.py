from fringe_tracing import *
from skimage.filters import gaussian
from skimage.draw import circle
from skimage.morphology import thin as sthin
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2TkAgg)
import numpy as np
import tkinter as Tk
import tkinter.ttk as ttk

root = Tk.Tk()

fig, axes = plt.subplots(2, 2)
plt.tight_layout()

canvas = FigureCanvasTkAgg(fig, master=root)  # A tk.DrawingArea.
canvas.draw()
canvas.get_tk_widget().pack(side=Tk.TOP, fill=Tk.BOTH, expand=1)

toolbar = NavigationToolbar2TkAgg(canvas, root)
toolbar.update()
canvas._tkcanvas.pack(side=Tk.TOP, fill=Tk.BOTH, expand=1)

print("Imported")

interferogram_path = "C:\\Users\\User\\Documents\\pendrive\\Sample interferograms\\s0920_17 355 nm end on interferometry (1).JPG"
interferogram = imread(interferogram_path)
interferogram = rgb2gray(interferogram)

print("File opened")

blur = 30
blurred_interferogram = gaussian(interferogram, blur)
normalised_interferogram = interferogram/blurred_interferogram
axes[0, 0].imshow(normalised_interferogram, cmap='gray', clim=[0.95, 1.05])

print("Normalised")

fft_filter = np.zeros_like(np.abs(interferogram))
fftim = (np.fft.fftshift(np.fft.fft2(normalised_interferogram)))
axes[0, 1].imshow(abs(fftim) + 100000*fft_filter/2, clim=[0, 10000])

print("Fouriered")

ifftim = abs((np.fft.ifft2(fftim*fft_filter)))
axes[1, 0].imshow(ifftim, cmap='gray', clim=[-1, 0.5])

control = False
alt = False
R1 = 0
R2 = 0

def onclick(event):
    global fft_filter, R1, R2
    fft_filter = np.zeros_like(np.abs(interferogram))
    centre = fftim.shape
    if control and event.inaxes == axes[0, 1]:
        R2 = np.sqrt((event.xdata-centre[1]/2)**2 + (event.ydata-centre[0]/2)**2)
    elif alt and event.inaxes == axes[0, 1]:
        R1 = np.sqrt((event.xdata-centre[1]/2)**2 + (event.ydata-centre[0]/2)**2)
    if (control or alt) and event.inaxes == axes[0, 1]:
        rr, cc = circle(r=centre[0]/2, c=centre[1]/2, radius=R2, shape=fft_filter.shape)
        fft_filter[rr, cc] = 1
        rr, cc = circle(r=centre[0]/2, c=centre[1]/2, radius=R1, shape=fft_filter.shape)
        fft_filter[rr, cc] = 0
        axes[0, 1].imshow(abs(fftim) + 1000*fft_filter/2, clim=[0, 10000])
        # refourier()
        fig.canvas.draw()


def onpress(event):
    global control, alt
    if event.key == 'control':
        control = True
    elif event.key == 'alt':
        alt = True


def onrelease(event):
    global control, alt
    if event.key == 'control':
        control = False
    elif event.key == 'alt':
        alt = True


fig.canvas.mpl_connect('button_press_event', onclick)
fig.canvas.mpl_connect('key_press_event', onpress)
fig.canvas.mpl_connect('key_release_event', onrelease)
canvas.mpl_connect('button_press_event',
                        lambda event: fig.canvas._tkcanvas.focus_set())

def refourier():
    global ifftim
    ifftim = abs((np.fft.ifft2(fftim*fft_filter)))
    axes[1, 0].imshow(ifftim, cmap='gray', clim=[0, 0.5])
    fig.canvas.draw()

def clean():
    global fft_filter
    fft_filter = np.zeros_like(fft_filter)
    axes[0, 1].imshow(abs(fftim) + 1000*fft_filter/2, clim=[0, 1000])
    fig.canvas.draw()

def threshold():
    global fft_filter
    fft_filter = fftim != 0


def thin():
    imthin=sthin(ifftim>0.3)
    axes[1, 1].imshow(imthin, max_iter=1000)
    fig.canvas.draw()

b = ttk.Button(root, text="Refourier", command=refourier)
b.pack(side=Tk.BOTTOM)
b = ttk.Button(root, text="Clean", command=clean)
b.pack(side=Tk.BOTTOM)
b = ttk.Button(root, text="Threshold", command=threshold)
b.pack(side=Tk.BOTTOM)
b = ttk.Button(root, text="Thin", command=thin)
b.pack(side=Tk.BOTTOM)

root.mainloop()
