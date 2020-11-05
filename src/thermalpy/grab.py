# coding=utf-8
import PySpin
import numpy as np
import matplotlib.pyplot as plt

class cams():

    def __init__(self):
        # Retrieve singleton reference to system object
        self.system = PySpin.System.GetInstance()

        # Get current library version
        self.version = self.system.GetLibraryVersion()
        print('Spinnaker version: {}.{}.{}.{}'.format(
            self.version.major,
            self.version.minor,
            self.version.type,
            self.version.build))

        if self.version.major > 2:
            print('Warning: thermalpy is not developed for Spinnaker version {}'.
                  format(self.version.major)+' and probably will not work')
        elif self.version.major == 1:
            print('Warning: thermalpy is not developed for Spinnaker version 1.x')
        elif self.version.minor > 2:
            print('Warning: thermalpy is not tested for Spinnaker version 2.{}'.
                  format(self.version.minor))

        # Retrieve list of cameras from the system
        self.cam_list = self.system.GetCameras()

        self.num_cameras = self.cam_list.GetSize()

        print('Number of cameras detected: {}'.format(self.num_cameras))

        self.cam_ids = [get_id(cam) for cam in self.cam_list]

        ## Skip retrieving the entire nodemap for now.
        # self.camera_properties = {}
        #
        # for ii, cam_id in enumerate(self.cam_ids):
        #     self.camera_properties[cam_id] = get_cam_info(self.cam_list[ii])

        print('Configuring cameras...')
        for cam in self.cam_list:
            cam.Init()

            try:
                set_Mono14(cam)
                set_temp_linear(cam)
                set_high_gain(cam)

            except PySpin.SpinnakerException as ex:
                print('Error: %s' % ex)

            cam.DeInit()
            del cam


    def __repr__(self):
        return 'Placeholder repr'


    def listcams(self):
        print('Cameras currently connected:')
        [print('\t',id) for id in self.cam_ids]


    def show_images(self):
        for ii, cam in enumerate(self.cam_list):
            raw_data, _, RFBO = grab_imagedata(cam)
            temp_data = sig_to_temp(raw_data, RFBO)

            plt.figure()
            plt.imshow(temp_data, cmap='inferno')
            cbar = plt.colorbar()
            cbar.set_label('$\\degree$C')
            plt.title('Camera '+self.cam_ids[ii])

            del cam


    def grab_image(self, cam_id, mode='full'):
        for cam in self.cam_list:
            raw_data=False
            if get_id(cam) == cam_id:
                raw_data, temps, RFBO = grab_imagedata(cam)
                del cam

                temperature_data = sig_to_temp(raw_data, RFBO)

                if mode=='full':
                    return temperature_data, raw_data, temps, RFBO
                elif mode=='simple':
                    return temperature_data

            if raw_data==False:
                print('No matching camera ID found')
                del cam
                return False

    def __del__(self):
        self.cam_list.Clear()
        self.system.ReleaseInstance()

    def close(self):
        self.__del__()


def get_id(cam):
    '''
    Function that grabs camera serial numbers for the specified camera object

        Parameters
        ----------
        cam : PySpin cam object

        Returns
        -------
        device_serial_number

    '''

    nodemap_tldevice = cam.GetTLDeviceNodeMap()

    device_serial_number = ''
    node_device_serial_number = PySpin.CStringPtr(nodemap_tldevice.GetNode('DeviceSerialNumber'))
    if PySpin.IsAvailable(node_device_serial_number) and PySpin.IsReadable(node_device_serial_number):
        device_serial_number = node_device_serial_number.GetValue()
    else:
        print('Serial number retrieval failed')
    return device_serial_number

def sig_to_temp(sig, RFBO):
    R, F, B, O = RFBO
    return (B / (np.log(R/(sig-O)+F))-273.15).astype(np.float32)

def grab_imagedata(cam):
    try:
        # Initialize camera
        cam.Init()

        # Retrieve GenICam nodemap
        nodemap = cam.GetNodeMap()

        # Acquire camera parameters
        temps, RFBO = acquire_parameters(nodemap)

        # Acquire images
        raw_data = acquire_images(cam, nodemap)

        # Deinitialize camera
        cam.DeInit()

        return raw_data, temps, RFBO

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        return False

def acquire_parameters(nodemap):
    node_stemp = nodemap.GetNode('SensorTemperature')
    sensor_temp = PySpin.CFloatPtr(node_stemp).GetValue()
    node_htemp = nodemap.GetNode('HousingTemperature')
    housing_temp = PySpin.CFloatPtr(node_htemp).GetValue()
    temps = {'sensor_temperature': sensor_temp,
             'housing_temperature': housing_temp}

    R = PySpin.CIntegerPtr(nodemap.GetNode('R')).GetValue()
    F = PySpin.CFloatPtr(nodemap.GetNode('F')).GetValue()
    B = PySpin.CFloatPtr(nodemap.GetNode('B')).GetValue()
    O = PySpin.CFloatPtr(nodemap.GetNode('O')).GetValue()

    return temps, (R, F, B, O)

def acquire_images(cam, nodemap, silent=False):
    """
    This function acquires and returns a single image from a device.

        Parameters
        ----------
        cam : PySpin cam object
        cam : PySpin Device nodemap

        Returns
        -------
        image data if succesfull, False otherwise
    """
    image_data = False

    try:
        # In order to access the node entries, they have to be casted to a pointer type (CEnumerationPtr here)
        node_acquisition_mode = PySpin.CEnumerationPtr(nodemap.GetNode('AcquisitionMode'))
        if not PySpin.IsAvailable(node_acquisition_mode) or not PySpin.IsWritable(node_acquisition_mode):
            print('Unable to set acquisition mode to continuous (enum retrieval). Aborting...')
            return False

        # Retrieve entry node from enumeration node
        node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName('Continuous')
        if not PySpin.IsAvailable(node_acquisition_mode_continuous) or not PySpin.IsReadable(node_acquisition_mode_continuous):
            print('Unable to set acquisition mode to continuous (entry retrieval). Aborting...')
            return False

        acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()
        node_acquisition_mode.SetIntValue(acquisition_mode_continuous)

        if not silent:
            print('Acquisition mode set to continuous...')

        cam.BeginAcquisition()

        if not silent:
            print('Acquiring images...')

        try:

            image_result = cam.GetNextImage()

            if image_result.IsIncomplete():
                print('Image incomplete with image status %d ...' % image_result.GetImageStatus())

            else:

                width = image_result.GetWidth()
                height = image_result.GetHeight()
                if not silent:
                    print('Grabbed Image, width = %d, height = %d' % (width, height))

                image_converted = image_result.Convert(PySpin.PixelFormat_Mono14, PySpin.HQ_LINEAR)
                image_data = np.reshape(image_converted.GetData(), (height, width))
                image_result.Release()

        except PySpin.SpinnakerException as ex:
            print('Error: %s' % ex)
            return False

        cam.EndAcquisition()

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        return False

    return image_data


def set_Mono14(icam):
    if icam.PixelFormat.GetAccessMode() == PySpin.RW:
        icam.PixelFormat.SetValue(PySpin.PixelFormat_Mono14)
        print('Pixel format set to %s...' % icam.PixelFormat.GetCurrentEntry().GetSymbolic())
    else:
        print('Pixel format not available...')


def set_temp_linear(icam):
    nodemap = icam.GetNodeMap()

    node_templinmode = PySpin.CEnumerationPtr(nodemap.GetNode('TemperatureLinearMode'))
    if not PySpin.IsAvailable(node_templinmode) or not PySpin.IsWritable(node_templinmode):
        print('Unable to set TemperatureLinearMode (enum retrieval). Aborting...')
        return False

    # Retrieve entry node from enumeration node
    node_templinmode_off = node_templinmode.GetEntryByName('Off')
    if not PySpin.IsAvailable(node_templinmode_off) or not PySpin.IsReadable(
            node_templinmode_off):
        print('Unable to set TemperatureLinearMode (entry retrieval). Aborting...')
        return False

    # Retrieve integer value from entry node
    linear_mode_off = node_templinmode_off.GetValue()

    # Set integer value from entry node as new value of enumeration node
    node_templinmode.SetIntValue(linear_mode_off)

    return True


def set_high_gain(icam):
    nodemap = icam.GetNodeMap()

    node_gain_mode = PySpin.CEnumerationPtr(nodemap.GetNode('SensorGainMode'))
    if not PySpin.IsAvailable(node_gain_mode) or not PySpin.IsWritable(node_gain_mode):
        print('Unable to set gain mode (enum retrieval). Aborting...')
        return False

    # Retrieve entry node from enumeration node
    node_gain_mode_high = node_gain_mode.GetEntryByName('HighGainMode')
    if (not PySpin.IsAvailable(node_gain_mode_high)
        or not PySpin.IsReadable(node_gain_mode_high)):
        print('Unable to set gain mode (entry retrieval). Aborting...')
        return False

    # Retrieve integer value from entry node
    gain_mode_high = node_gain_mode_high.GetValue()

    # Set integer value from entry node as new value of enumeration node
    node_gain_mode.SetIntValue(gain_mode_high)

    return True

def get_cam_info(cam):
    cam.Init()

    nodemap_applayer = cam.GetNodeMap()
    rootnode = nodemap_applayer.GetNode('Root')
    _, rootdict = return_category_node_and_all_features(rootnode)

    del nodemap_applayer

    cam.DeInit()

    return rootdict

def return_node(node, nodetype):
    if PySpin.IsReadable(node):
        if nodetype == 'string':
            nodeval = PySpin.CStringPtr(node)
        elif nodetype == 'integer':
            nodeval = PySpin.CIntegerPtr(node)
        elif nodetype == 'float':
            nodeval = PySpin.CFloatPtr(node)
        elif nodetype == 'bool':
            nodeval = PySpin.CBooleanPtr(node)
        elif nodetype == 'command':
            nodeval = PySpin.CCategoryPtr(node)
        elif nodetype == 'enumeration':
            nodeval = PySpin.CEnumerationPtr(node)
        else:
            raise ValueError("Invalid node type")
    else:
        nodeval = 'n/a'

    name = nodeval.GetDisplayName()

    if nodetype == 'command':
        value = nodeval.GetToolTip()
    elif nodetype == 'enumeration':
        node_enum_entry = PySpin.CEnumEntryPtr(nodeval.GetCurrentEntry())
        value = node_enum_entry.GetSymbolic()
    else:
        value = nodeval.GetValue()

    return name, value

def return_category_node_and_all_features(node):
    """
    This function retrieves and prints out the display name of a category node
    before printing all child nodes. Child nodes that are also category nodes are
    printed recursively.

    :param node: Category node to get information from.
    :type node: INode
    """
    try:
        #print('ding')
        #Create dictionary to fill with this category node's values
        category_dict = {}

        # Create category node
        node_category = PySpin.CCategoryPtr(node)

        # Get display name
        display_name = node_category.GetDisplayName()

        category_dict = {}

        for node_feature in node_category.GetFeatures():
            try:
                # Ensure node is available and readable
                if (PySpin.IsAvailable(node_feature) and PySpin.IsReadable(node_feature)):
                    # Category nodes must be dealt with separately in order to retrieve subnodes recursively.
                    if node_feature.GetPrincipalInterfaceType() == PySpin.intfICategory:
                        name, value = return_category_node_and_all_features(node_feature)

                    # Cast all non-category nodes as value nodes
                    if node_feature.GetPrincipalInterfaceType() == PySpin.intfIString:
                        name, value = return_node(node_feature, 'string')
                    elif node_feature.GetPrincipalInterfaceType() == PySpin.intfIInteger:
                        name, value = return_node(node_feature, 'integer')
                    elif node_feature.GetPrincipalInterfaceType() == PySpin.intfIFloat:
                        name, value = return_node(node_feature, 'float')
                    elif node_feature.GetPrincipalInterfaceType() == PySpin.intfIBoolean:
                        name, value = return_node(node_feature, 'bool')
                    elif node_feature.GetPrincipalInterfaceType() == PySpin.intfICommand:
                        name, value = return_node(node_feature, 'command')
                    elif node_feature.GetPrincipalInterfaceType() == PySpin.intfIEnumeration:
                        name, value = return_node(node_feature, 'enumeration')

                    category_dict[name] = value

            except TypeError:
                pass

        return display_name, category_dict

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        return False
