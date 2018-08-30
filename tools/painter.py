from fringe_tracing import *
from skimage.filters import gaussian
import matplotlib.pyplot as plt
import numpy as np

fig, axes = plt.subplots(2, 2)
plt.tight_layout()

print("Imported")

interferogram_path = "C:\\Users\\User\\Documents\\pendrive\\Sample interferograms\\test2.png"
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
axes[0, 1].imshow(abs(fftim) + 100000*fft_filter/2, clim=[0, 100000])

print("Fouriered")

ifftim = abs((np.fft.ifft2(fftim*fft_filter)))
axes[1, 0].imshow(ifftim, cmap='gray', clim=[-1, 0.5])

control = False

def onclick(event):
    global fft_filter
    if control and event.inaxes == axes[0, 1]:
        centre = fftim.shape
        x, y = int(event.xdata), int(event.ydata)
        fft_filter[y-20:y+20, x-20:x+20] = 1
        x, y = int(-x+centre[1]), int(-y+centre[0])
        fft_filter[y-20:y+20, x-20:x+20] = 1
        fft_filter=gaussian(fft_filter, 4)
        ifftim = abs((np.fft.ifft2(fftim*fft_filter)))
        axes[0, 1].imshow(abs(fftim) + 100000*fft_filter/2, clim=[0, 100000])
        axes[1, 0].imshow(ifftim, cmap='gray', clim=[0, 0.5])
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

plt.show()
