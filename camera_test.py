# Script to test thermalpy code

# %%
from src import thermalpy
from time import time
from time import sleep
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
from datetime import datetime

#matplotlib.use('TkAgg')
matplotlib.use('Qt5Agg')
# %matplotlib Qt5

output_dir = 'C:\\Data\\FLIR_2020_11_04'

# %%
cams = thermalpy.cams()

# %%
plot_data = [0] * cams.num_cameras

for cam in cams.cam_list:
    cam.Init()
    del cam

for jj, cam in enumerate(cams.cam_list):
    nodemap = cam.GetNodeMap()
    raw_data = \
        thermalpy.grab.acquire_images(cam, nodemap, silent=True)

    if (type(raw_data) == bool) and (raw_data == False):
        raise ValueError('Image incomplete')
    else:
        temps, RFBO = thermalpy.grab.acquire_parameters(nodemap)
        temp_data = thermalpy.grab.sig_to_temp(raw_data, RFBO)

    del nodemap
    del cam

    plot_data[jj] = temp_data

for cam in cams.cam_list:
    cam.DeInit()
    del cam

# %%
for cam in cams.cam_list:
    cam.Init()
    del cam

if cams.num_cameras == 1:
    fig, axes = plt.subplots()
    axes = [axes]
elif cams.num_cameras == 2:
    fig, axes = plt.subplots(ncols=2)
elif cams.num_cameras <= 4:
    fig, axes = plt.subplots(ncols=2, nrows=2)
    axes = axes.flatten()
else:
    raise ValueError('script is made for up to 4 simultaneous cameras')

figManager = plt.get_current_fig_manager()
figManager.window.showMaximized()

im = [0]*cams.num_cameras
vmin = [0]*cams.num_cameras
vmax = [0]*cams.num_cameras

for ii, ax in enumerate(axes):
    im[ii] = ax.imshow(
        plot_data[ii],
        cmap='inferno'
    )

    ax.set_title('ID: ' + cams.cam_ids[ii])

    cax = make_axes_locatable(ax).append_axes("right", size="5%", pad=0.05)

    fig.colorbar(
        im[ii],
        cax=cax,
    )

    ax.axes.get_xaxis().set_visible(False)
    ax.axes.get_yaxis().set_visible(False)

    fig.tight_layout()
    fig.subplots_adjust(
        wspace=0.080
    )

    vmin[ii] = [np.percentile(plot_data[ii], 1)]*10
    vmax[ii] = [np.percentile(plot_data[ii], 99)]*10

while True:
    for ii, cam in enumerate(cams.cam_list):
        nodemap = cam.GetNodeMap()
        raw_data = \
            thermalpy.grab.acquire_images(cam, nodemap, silent=True)

        if (type(raw_data) == bool) and (raw_data == False):
            raw_data = np.ones(np.shape(plot_data[ii])) * np.nan
            temp_data = np.ones(np.shape(plot_data[ii])) * np.nan
        else:
            temp_data = thermalpy.grab.sig_to_temp(raw_data, RFBO)

        temps, RFBO = thermalpy.grab.acquire_parameters(nodemap)

        thermalpy.write.writeappend_netcdf(
            directory=output_dir,
            camera_id=cams.cam_ids[ii],
            image_datetime=datetime.now(),
            raw_data=raw_data,
            temperature_data=temp_data,
            temps=temps,
            RFBO=RFBO,
            freq='hourly',
            silent=True
        )

        del nodemap
        del cam

        plot_data[ii] = temp_data

    for ii in range(cams.num_cameras):
        im[ii].set_data(plot_data[ii])
        
        vmin[ii].pop(0)
        vmin[ii].append(np.percentile(plot_data[ii], 1))
        vmax[ii].pop(0)
        vmax[ii].append(np.percentile(plot_data[ii], 99))

        im[ii].set_clim(
            (np.nanmean(vmin[ii]), np.nanmean(vmax[ii]))
        )

    #plt.pause(0.05)
    plt.gcf().canvas.draw_idle()
    plt.gcf().canvas.start_event_loop(0.05)

    if plt.waitforbuttonpress(timeout=0.05):
        break

plt.close()
sleep(0.2)

for cam in cams.cam_list:
    cam.DeInit()
    del cam

sleep(0.2)

# %%
cams.close()

# %%
