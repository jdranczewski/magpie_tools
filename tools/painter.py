from fringe_tracing import *
from skimage.filters import gaussian
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
interferogram = imread(interferogram_path)[1500:1600, 1500:1600]
interferogram = rgb2gray(interferogram)

print("File opened")

blur = 30
blurred_interferogram = gaussian(interferogram, blur)
normalised_interferogram = interferogram/blurred_interferogram
axes[0, 0].imshow(normalised_interferogram, cmap='gray', clim=[0.95, 1.05])

print("Normalised")

fft_filter = np.zeros_like(np.abs(interferogram))
fftim = (np.fft.fftshift(np.fft.fft2(normalised_interferogram)))
axes[0, 1].imshow(abs(fftim) + 100000*fft_filter/2, clim=[0, 1000])

print("Fouriered")

ifftim = abs((np.fft.ifft2(fftim*fft_filter)))
axes[1, 0].imshow(ifftim, cmap='gray', clim=[-1, 0.5])

control = False

def onclick(event):
    global fft_filter
    if control and event.inaxes == axes[0, 1]:
        centre = fftim.shape
        x, y = int(event.xdata), int(event.ydata)
        size = 3
        fft_filter[y-size:y+size+1, x-size:x+size+1] = 1
        x, y = int(-x+centre[1]), int(-y+centre[0])
        fft_filter[y-size:y+size+1, x-size:x+size+1] = 1
        fft_filter=gaussian(fft_filter, size/5)
        axes[0, 1].imshow(abs(fftim) + 1000*fft_filter/2, clim=[0, 1000])
        refourier()
        fig.canvas.draw()

def onpress(event):
    global control
    if event.key == 'control':
        control = True

def onrelease(event):
    global control
    if event.key == 'control':
        control = False

fig.canvas.mpl_connect('button_press_event', onclick)
fig.canvas.mpl_connect('key_press_event', onpress)
fig.canvas.mpl_connect('key_release_event', onrelease)
canvas.mpl_connect('button_press_event',
                        lambda event: fig.canvas._tkcanvas.focus_set())

def refourier():
    ifftim = abs((np.fft.ifft2(fftim*fft_filter)))
    axes[1, 0].imshow(ifftim, cmap='gray', clim=[0, 0.5])
    fig.canvas.draw()

b = ttk.Button(root, text="Refourier", command=refourier)
b.pack(side=Tk.BOTTOM)

root.mainloop()
