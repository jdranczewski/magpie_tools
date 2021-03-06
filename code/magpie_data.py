import numpy as np
import scipy as sp
import matplotlib.pyplot as plt
#from scipy.ndimage.interpolation import rotate
from skimage.transform import rotate
from scipy.ndimage import zoom
import os
from skimage.measure import profile_line
import imreg_dft as ird
import imageio
import pickle
from ipywidgets import interact, interactive, fixed
import ipywidgets as widgets
from IPython.display import display
import cv2


class DataMap:
    def __init__(self, flip_lr, rot_angle, multiply_by, scale):
        if flip_lr is True:
            self.d=np.fliplr(self.d)
        if rot_angle is not None:
            self.d=rotate(self.d, rot_angle)
        self.rot_angle=rot_angle
        self.data=self.d*multiply_by
        self.scale=scale
        self.s_name=os.path.basename(self.fn)[:8]
    def plot_data_px(self, clim=None, multiply_by=1, ax=None):
        if ax is None:
            fig, ax=plt.subplots(figsize=(12,8))
        d=self.data*multiply_by
        return ax.imshow(d, clim=clim, cmap=self.cmap)
    def set_origin(self, origin, extent):
        self.origin=origin
        self.extent=extent
        ymin=int(origin[0]-extent[1]*self.scale)
        ymax=int(origin[0]-extent[0]*self.scale)
        xmin=int(origin[1]+extent[2]*self.scale)
        xmax=int(origin[1]+extent[3]*self.scale)
        self.origin_crop=(extent[1]*self.scale,-extent[2]*self.scale)
        self.data_c=self.data[ymin:ymax, xmin:xmax]
        self.extent=extent[2:4]+extent[0:2]
    def plot_data_mm(self, clim=None, multiply_by=1, ax=None):
        if ax is None:
            fig, ax=plt.subplots(figsize=(12,8))
        d=self.data_c*multiply_by
        return ax.imshow(d, cmap=self.cmap, interpolation='none', clim=clim, extent=self.extent, aspect=1)
    def create_lineout(self, start=(0,0), end=(0,0), lineout_width_mm=1, verbose=False):
        '''
        start and end are in mm on the grid defined by the origin you just set
        '''
        #find coordinates in pixels
        start_px=self.mm_to_px(start)
        end_px=self.mm_to_px(end)
        if verbose is True:
            print(start_px,end_px)
        #use scikit image to do a nice lineout on the cropped array
        self.lo=profile_line(self.data_c, start_px,end_px,linewidth=lineout_width_mm*self.scale)
        #set up a mm scale centred on 0
        px_range=self.lo.size/2
        self.mm=np.linspace(-px_range, px_range, 2*px_range)/self.scale #flip range to match images
    def plot_lineout(self, ax=None, label='', multiply_by=1):
        if ax is None:
            fig, ax=plt.subplots(figsize=(12,8))
        ax.plot(self.mm, self.lo*multiply_by, label=label, lw=4)
    def mm_to_px(self,mm):
        scale=self.scale
        px_origin=self.origin_crop
        return (int(-mm[0]*scale+px_origin[0]),int(mm[1]*scale+px_origin[1]))

    #Functions for transforms - not every child class uses these, but they are reused often enough
    def register(self, constraints=None, transform=None):
        if transform is None:
            t=ird.similarity(self.R0, self.R1, numiter=3, constraints=constraints)
            transform = { your_key: t[your_key] for your_key in ['angle','scale','tvec'] }
        self.transform=transform
    def nudge_transform(self, xlim=100, ylim=100):
        def plot_transform(scale, angle, tx, ty, limits):
            imT=ird.imreg.transform_img(self.R1, scale=scale, angle=angle, tvec=(ty,tx))
            diff=self.R0-imT
            fig, ax=plt.subplots(figsize=(10,8))
            ax.imshow(diff, cmap='bwr', clim=[-limits,limits])

        ty=widgets.FloatSlider(min=self.transform['tvec'][0]-ylim,
                               max=self.transform['tvec'][0]+ylim,
                               step=1,
                               description='Translate in y:',
                               value=self.transform['tvec'][0],
                                continuous_update=False)

        tx=widgets.FloatSlider(min=self.transform['tvec'][1]-xlim,
                       max=self.transform['tvec'][1]+xlim,
                       step=1,
                       description='Translate in x:',
                       value=self.transform['tvec'][1],
                               continuous_update=False)
        scale=widgets.FloatSlider(min=0,
                               max=2,
                               step=0.05,
                               description='Scale:',
                               value=self.transform['scale'],
                                  continuous_update=False)
        angle=widgets.FloatSlider(min=self.transform['angle']-10,
                       max=self.transform['angle']+10,
                       step=0.1,
                       description='Angle (radians):',
                       value=self.transform['angle'],
                                  continuous_update=False)

        limits=widgets.FloatSlider(min=0,
                                  max=1,
                                  step=0.01,
                                  value=0.1,
                                   description='Colourbar limits:',
                                   continuous_update=False)

        self.w=interactive(plot_transform,
                      scale=scale,
                      angle=angle,
                      tx=tx,
                      ty=ty,
                      limits=limits
                      )

        display(self.w)

    def confirm_nudge(self):
        wargs=self.w.kwargs
        self.transform['scale']=wargs['scale']
        self.transform['angle']=wargs['angle']
        self.transform['tvec']=(wargs['ty'],wargs['tx'])
    def transform_images(self):
        self.RT=ird.transform_img_dict(self.R1, self.transform)
        self.DT=ird.transform_img_dict(self.D1, self.transform)
    def save_transform(self, fn):
        try:
            pickle.dump(self.transform, open(fn, 'wb'))
        except:
            print('No Transform found!')
    def load_transform(self, fn=None):
        if fn is None:
            self.transform=pickle.load(open(self.transform_fn, "rb" ))
        else:
            self.transform=pickle.load(open(fn, "rb" ))
    def duplicate_extent(self, image=None):
        if image is None:
            self.scale=self.pm.scale
            self.set_origin(self.pm.origin, extent=self.pm.extent[2:4]+self.pm.extent[0:2])
        else:
            self.scale=image.scale
            self.set_origin(image.origin, extent=image.extent[2:4]+image.extent[0:2])



class NeLMap(DataMap):
    def __init__(self, filename, scale, multiply_by=1, flip_lr=False, rot_angle=None):
        self.fn=filename[:8]
        d=np.loadtxt(open(filename,"r"),delimiter=",")
        d=d-np.nan_to_num(d).min()
        d=np.nan_to_num(d)
        if flip_lr is True:
            d=np.fliplr(d)
        if rot_angle is not None:
            d=rotate(d, rot_angle)
        self.data=d*multiply_by
        self.scale=scale
        self.cmap='inferno'

class Interferogram(DataMap):
    def __init__(self, filename, scale, flip_lr=False, rot_angle=None):
        self.fn=filename[:8]
        d=plt.imread(filename)
        if flip_lr is True:
            d=np.fliplr(d)
        if rot_angle is not None:
            d=rotate(d, rot_angle)
        self.data=d
        self.scale=scale
    def plot_data_px(self, ax=None):
        if ax is None:
            fig, ax=plt.subplots(figsize=(12,8))
        return ax.imshow(self.data)
    def plot_data_mm(self, ax=None):
        if ax is None:
            fig, ax=plt.subplots(figsize=(12,8))
        d=self.data_c
        return ax.imshow(d, interpolation='none', extent=self.extent, aspect=1)
    
class Shadowgram(DataMap):
    def __init__(self, filename, scale, flip_lr=False, rot_angle=None, colour='g'):
        self.fn=filename[:8]
        d=plt.imread(filename)
        if colour is 'g': #implement other colours as necessary
            d=d[:,:,1]
        if flip_lr is True:
            d=np.fliplr(d)
        if rot_angle is not None:
            d=rotate(d, rot_angle)
        self.data=d
        self.scale=scale
    def plot_data_px(self, ax=None):
        if ax is None:
            fig, ax=plt.subplots(figsize=(12,8))
        return ax.imshow(self.data)
    def plot_data_mm(self, ax=None):
        if ax is None:
            fig, ax=plt.subplots(figsize=(12,8))
        d=self.data_c
        return ax.imshow(d, interpolation='none', extent=self.extent, aspect=1)

class PolarimetryMap(DataMap):
    def __init__(self, R0fn, R1fn, B0fn, B1fn, S0fn, S1fn, rot_angle=None):
        self.fn=R0fn[:8]
        self.transform_fn=self.fn[:8]+' faraday registration.p'
        self.rot_angle=rot_angle
        self.R0=plt.imread(R0fn)
        self.R1=np.fliplr(plt.imread(R1fn))
        self.B0=plt.imread(B0fn)
        self.B1=np.fliplr(plt.imread(B1fn))
        self.S0=plt.imread(S0fn)
        self.S1=np.fliplr(plt.imread(S1fn))
        if rot_angle is not None:
            self.R0=rotate(self.R0, rot_angle)
            self.R1=rotate(self.R1, rot_angle)
            self.B0=rotate(self.B0, rot_angle)
            self.B1=rotate(self.B1, rot_angle)
            self.S0=rotate(self.S0, rot_angle)
            self.S1=rotate(self.S1, rot_angle)
        #normalise registration images
        R0s=self.R0.sum()
        R1s=self.R1.sum()
        self.R0=self.R0*R1s/R0s
        self.D0=self.S0/self.B0
        self.D1=self.S1/self.B1
        self.cmap='seismic'
    def convert_to_alpha(self, beta, beta0=None, beta1=None, power_ratio=1):
        '''
        If you have two polarisers set to the same angle, use beta
        If you know your polarisers were not at the same angle, and you know what that angle is, use beta1 and beta 2
        Optionally, if you know the power ratio, IS/IB 
        (say from comparing a region of the reference beam in the background and shot interferograms)
        you can provide it
        '''
        if beta1 is None: #simple version when polarisers are at the same angle
            diff=self.D0-self.DT
            self.diff=np.nan_to_num(diff)
            beta=beta*np.pi/180
            self.data=-(180/np.pi)*0.5*np.arcsin(self.diff*np.tan(beta)/2.0)
        else:#polarisers set at different angles
            bp=beta0*np.pi/180
            bm=beta1*np.pi/180
            self.diff=self.D0*np.sin(bp)**2-self.DT*np.sin(bm)**2
            
            app=0.5*(np.arcsin(1/power_ratio*self.diff/np.sin(bp+bm))-bp+bm)
            self.data=app*180/np.pi
                        
    def single_channel_analysis(self, beta0, beta1):
        beta0=beta0*np.pi/180
        beta1=beta1*np.pi/180
        self.alpha0=180/np.pi*(np.arcsin(self.D0**0.5*np.sin(beta0))-beta0)
        self.alpha1=180/np.pi*(-np.arcsin(self.D1**0.5*np.sin(beta1))+beta1)



class InterferogramOntoPolarimetry(DataMap):
    def __init__(self, polmap, I0, I1):
        self.fn=I0[:8]
        self.transform_fn=self.fn[:8]+' interferometry registration.p'
        #load the registration and interferometry images
        I0=plt.imread(I0)
        I0s=np.sum(I0,2)
        I1=plt.imread(I1)
        I1s=np.sum(I1,2)
        #flip cos interferometry camera images are upside down wrt faraday
        self.I0s=np.flipud(I0s)
        self.I1=np.flipud(I1s)

        self.pm=polmap
        #rotate data to match polarisation map
        if self.pm.rot_angle is not None:
            self.I0s=rotate(self.I0s,self.pm.rot_angle)
            self.I1=rotate(self.I1,self.pm.rot_angle)
        #in order to perform image registration, the two images must be the same size
        #here we work out whether to rescale based on the x or y size of the image
        self.R0=self.pm.R0
        R0=self.R0
        scale_y=R0.shape[0]/self.I0s.shape[0]
        scale_x=R0.shape[1]/self.I0s.shape[1]
        if scale_y>scale_x:
            scale=scale_y
            I0z=zoom(self.I0s, scale)
            I1z=zoom(self.I1, scale)
            crop=(I0z.shape[1]-R0.shape[1])//2
            I0zc=I0z[:,crop:crop+R0.shape[1]]
            I1zc=I1z[:,crop:crop+R0.shape[1]]
        if scale_x>scale_y:
            scale=scale_x
            I0z=zoom(self.I0s, scale)
            I1z=zoom(self.I1, scale)
            crop=(I0z.shape[0]-R0.shape[0])//2
            I0zc=I0z[crop:crop+R0.shape[0],:]
            I1zc=I1z[crop:crop+R0.shape[0],:]
        self.R1=I0zc*(R0.max()/I0zc.max()) #normalise
        self.D1=I1zc
        self.cmap='gray'
    def transform_images(self):
        DataMap.transform_images(self)
        self.data=self.DT

class FaradayMap(DataMap):
    def __init__(self, polmap, I0, ne, flip_ne=False):
        self.fn=polmap.fn[:8]
        self.transform_fn=self.fn[:8]+' interferometry registration.p'

        I0=plt.imread(I0)
        self.I0s=np.sum(I0,2)
        I1=np.loadtxt(ne, delimiter=',')
        I1=I1-np.nan_to_num(I1).min()
        self.I1=np.nan_to_num(I1)
        self.pm=polmap
        #flip cos interferometry camera images are upside down wrt faraday
        self.I0s=np.flipud(self.I0s)
        self.I1=np.flipud(self.I1)
        #rotate data to match polarisation map
        if self.pm.rot_angle is not None:
            self.I0s=rotate(self.I0s,self.pm.rot_angle)
            self.I1=rotate(self.I1,self.pm.rot_angle)
        #in order to perform image registration, the two images must be the same size
        #scale and flip to data
        self.R0=self.pm.R0
        R0=self.R0
        scale_y=R0.shape[0]/self.I0s.shape[0]
        scale_x=R0.shape[1]/self.I0s.shape[1]

        if scale_y>scale_x:
            scale=scale_y
            I0z=zoom(self.I0s, scale)
            I1z=zoom(self.I1, scale)
            crop=(I0z.shape[1]-R0.shape[1])//2
            I0zc=I0z[:,crop:crop+R0.shape[1]]
            I1zc=I1z[:,crop:crop+R0.shape[1]]
        if scale_x>scale_y:
            scale=scale_x
            I0z=zoom(self.I0s, scale)
            I1z=zoom(self.I1, scale)
            crop=(I0z.shape[0]-R0.shape[0])//2
            I0zc=I0z[crop:crop+R0.shape[0],:]
            I1zc=I1z[crop:crop+R0.shape[0],:]
        self.R1=I0zc*(R0.max()/I0zc.max())
        self.D1=I1zc
        if flip_ne is True:
            self.D1=np.flipud(I1zc)
        self.cmap='seismic'

    def convert_to_magnetic_field(self):
        self.B=5.99e18*self.pm.data/self.DT
        self.data=self.B


class OpticalFrame(DataMap):
    def __init__(self, data, shot, scale, flip_lr, rot_angle):
        self.fn=shot
        if flip_lr is True:
            data=np.fliplr(data)
        if rot_angle is not None:
            data=rotate(data, rot_angle)
        self.data=data
        self.scale=scale
        self.cmap='afmhot'

class OpticalFrames:
    def __init__(self, start, IF, scale, flip_lr=False, rot_angle=None):
        self.start=start
        self.IF=IF
        self.frame_times=np.arange(start, start+12*IF, IF)
        self.shot=os.path.split(os.getcwd())[-1][0:8] #automatically grab the shot number
        self.scale=scale
        self.rot_angle=rot_angle
        #load images
        b=[]
        s=[]
        for i in range(1,13):
            if i<10:
                st="0"+str(i)
            else:
                st=str(i)
            bk_fn=self.shot+" Background_0"+st+".png"
            bk_im=cv2.imread(bk_fn,-1) #read background image
            #bk_im=np.asarray(np.sum(bk_im,2), dtype=float)
            bb=OpticalFrame(bk_im, self.shot, scale, flip_lr, rot_angle)
            b.append(bb)#np.asarray(np.sum(bk_im,2), dtype=float)) #convert to grrayscale
            sh_fn=self.shot+" Shot_0"+st+".png"
            sh_im=cv2.imread(sh_fn,-1)
            ss=OpticalFrame(sh_im, self.shot, scale, flip_lr, rot_angle)
            s.append(ss)
        self.b=b
        self.s=s
    def crop(self, origin, xcrop, ycrop):
        x0=origin[1]
        y0=origin[0]
        self.origin=[ycrop,xcrop]
        self.s_c=[s_im[y0-ycrop:y0+ycrop,x0-xcrop:x0+xcrop] for s_im in self.s_r]
        self.b_c=[b_im[y0-ycrop:y0+ycrop,x0-xcrop:x0+xcrop] for b_im in self.b_r]
    def set_origins(self, origin, extent):
        self.origin=origin
        ymin=origin[0]-extent[1]*self.scale
        ymax=origin[0]-extent[0]*self.scale
        xmin=origin[1]+extent[2]*self.scale
        xmax=origin[1]+extent[3]*self.scale
        self.origin_crop=(extent[1]*self.scale,-extent[2]*self.scale)
        self.extent=extent[2:4]+extent[0:2]
        for bb in self.b:
            bb.set_origin(origin, extent)
        for ss in self.s:
            ss.set_origin(origin, extent)
    def normalise(self):
        norms=[b_im[100:-100,100:-100].sum() for b_im in self.b]
        n_max=max(norms)
        nn=[n/n_max for n in norms]
        self.s_n=[s_im[100:-100,100:-100]/n for s_im, n in zip(self.s, nn)]
    def logarithm(self, lv_min=-4, lv_max=0.2):
        for ss in self.s:
            s_l=np.log(ss.data_c)
            s_nl=(np.clip(s_l, a_min=lv_min, a_max=lv_max)-lv_min)/(lv_max-lv_min)
            ss.data_log=s_nl
    def save_frames_and_gif(self, clims, filename=None, frames_to_plot=None, width=6, duration=0.2, log=False):
        w=width
        frame=self.s[0].data_c #use this to find shape of canvas
        if frames_to_plot is None: #plot all frames
            frames_to_plot=range(0,len(self.s))
        if filename is None:
            filename=self.shot
        if len(clims) is 1:
            clims=clims*12

        h=w/frame.shape[1]*frame.shape[0]
        fig, ax=plt.subplots(figsize=(w,h))
        for im in frames_to_plot:
            if log is True:
                data=self.s[im].data_log
            else:
                data=self.s[im].data_c
            ax.imshow(data, cmap='afmhot', clim=clims[im])
            plt.axis('off')
            fig.subplots_adjust(left=0, bottom=0, right=1.0, top=1.0,
                wspace=0, hspace=0)
            fig.savefig(filename+'_'+str(im+1)+'.png')
        #now save the gif
        images = []
        for fn in [filename+'_'+str(im+1)+'.png' for im in frames_to_plot]:
            images.append(imageio.imread(fn))
        imageio.mimsave(filename+'.gif', images, duration=duration)

#for backwards compatibility reasons, old notebooks might refer to eg. FaradayMap2, so let's link them here:
FaradayMap2=FaradayMap
PolarimetryMap2=PolarimetryMap
NeLMap2=NeLMap
