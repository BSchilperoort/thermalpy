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
ncams = 2
plot_data = [0] * 2

for cam in cams.cam_list:
    cam.Init()
    del cam

for jj, cam in enumerate(cams.cam_list):
    nodemap = cam.GetNodeMap()
    raw_data = \
        thermalpy.grab.acquire_images(cam, nodemap, silent=True)

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

fig, (ax1, ax2) = plt.subplots(ncols=2)

figManager = plt.get_current_fig_manager()
figManager.window.showMaximized()

im1 = ax1.imshow(
    plot_data[0],
    cmap='inferno'
)
im2 = ax2.imshow(
    plot_data[1],
    cmap='inferno'
)

ax1.set_title('ID: ' + cams.cam_ids[0])
ax2.set_title('ID: ' + cams.cam_ids[1])

cax1 = make_axes_locatable(ax1).append_axes("right", size="5%", pad=0.05)
cax2 = make_axes_locatable(ax2).append_axes("right", size="5%", pad=0.05)

fig.colorbar(
    im1,
    cax=cax1,
)
fig.colorbar(
    im2,
    cax=cax2,
)

ax1.axes.get_xaxis().set_visible(False)
ax1.axes.get_yaxis().set_visible(False)
ax2.axes.get_xaxis().set_visible(False)
ax2.axes.get_yaxis().set_visible(False)

fig.tight_layout()
fig.subplots_adjust(
    wspace=0.080
)

vmin1 = [np.percentile(plot_data[0], 1)]*10
vmax1 = [np.percentile(plot_data[0], 99)]*10
vmin2 = [np.percentile(plot_data[1], 1)]*10
vmax2 = [np.percentile(plot_data[1], 99)]*10

while True:
    for jj, cam in enumerate(cams.cam_list):
        nodemap = cam.GetNodeMap()
        raw_data = \
            thermalpy.grab.acquire_images(cam, nodemap, silent=True)

        temps, RFBO = thermalpy.grab.acquire_parameters(nodemap)
        temp_data = thermalpy.grab.sig_to_temp(raw_data, RFBO)

        thermalpy.write.writeappend_netcdf(
            directory=output_dir,
            camera_id=cams.cam_ids[jj],
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

        plot_data[jj] = temp_data

    im1.set_data(plot_data[0])
    im2.set_data(plot_data[1])

    vmin1.pop(0)
    vmin1.append(np.percentile(plot_data[0], 1))
    vmax1.pop(0)
    vmax1.append(np.percentile(plot_data[0], 99))

    vmin2.pop(0)
    vmin2.append(np.percentile(plot_data[1], 1))
    vmax2.pop(0)
    vmax2.append(np.percentile(plot_data[1], 99))

    im1.set_clim(
        (np.mean(vmin1), np.mean(vmax1))
    )
    im2.set_clim(
        (np.mean(vmin2), np.mean(vmax2))
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
