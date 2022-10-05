######################################################################################################################
#
#   Copyright (c) 2022 Newport Electric Boats, LLC. All rights reserved.
#   Electric Vessel Management System (EVMS)
#   Filename: mapPlots.py
#
######################################################################################################################



import os
import sys
import math
import numpy as np
#import decimal as dc
import plotly.express as px
import pandas as pd
import logging
import sys

max_pwr = 12

maps_dir = '/home/neb/evms2/maps/'
#maps_dir = '/home/walt/evms2/maps/'

class mapPlots():
    def __init__(self, applog, buffer):
        self.sw_ver_maps = '0.4.2'
        self.applog = applog
        self.buffer = buffer
        logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO, handlers=[
            logging.FileHandler(applog),
            logging.StreamHandler(sys.stdout)])

    def is_str_Float(self, string):
        try:
            float(string)
            return True
        except ValueError:
            return False

    def log(self, message):
        self.buffer += message + '\n'
        logging.info(message)


    def usage(self):
        self.log('USAGE: python3 mapPlots.py ../../self.logs/test_evms_system.self.log')

    def plot_coords(self, filename, stat):
        #needed for input into the gmplot tool, as it takes DDmmmmm format (RMC outputs DDmmmmm)
        base_name = filename.split('/')[-1]
        image_name = base_name + '_trip_map_'+ stat +'.png'
        # if os.path.isfile(maps_dir + image_name):
        #     return maps_dir + image_name
        try:
            f = open(filename, 'r+')
            f.readline()
            sw_ver = 11 #FIXME... int(f.readline().split(' ')[-1].rstrip().split('.')[1])
            if sw_ver < 10:
                table = np.genfromtxt(filename, dtype=str, delimiter=',', skip_header=4, invalid_raise=False)
                lats = table[:, 14]
                lons = table[:, 15]
                ibats = table[:, 4]
                vbats = table[:, 5]
                socs = table[:, 13]
                spds = table[:, 16]
                pack_amp_hrs_list = table[:, 12]
                convert_to_DDmmmmm = True
            else:
                tmp = filename + '_tmp'
                file = open(filename, 'r+')
                tmp_file = open(tmp, 'w+')
                line = file.readline()
                count = 0
                while line != '':
                    if count >= 9:
                        if line[0] == 'a':
                            l = len(line.split(','))
                            if  l == 21:
                                tmp_file.write(line)
                    line = file.readline()
                    count+=1
                tmp_file.close()
                file.close()
                convert_to_DDmmmmm = False

            #convert_to_DDmmmmm = True # until May 14th at noon, the self.logs have been written using DD mm.mmmm
        except Exception as e:
            return 'plot_coords part 1 - File access ERROR: ' + str(e)

        try:
            table = np.genfromtxt(tmp, dtype=str, delimiter=',', skip_header=1, invalid_raise=False)
            # table = np.delete(table, np.where(
            # (table[:, 0] == 'b') | (table[:, 0] == 'c')), axis=0)
            lats = table[:, 3]
            lons = table[:, 4]
            ibats = table[:, 9]
            vbats = table[:, 10]
            socs = table[:, 8]
            spds = table[:, 5]
            pack_amp_hrs_list = table[:, 13]

            for idx, lat in enumerate(lats):
                if self.is_str_Float(lat):
                    lat = float(lat)
                    if convert_to_DDmmmmm == True:
                        lat = float(lat) / 100
                        DD = math.trunc(lat)
                        mmmmm = lat - DD
                        ddddd = mmmmm * 100 / 60
                        lats[idx] = DD + ddddd
                    else:
                        lats[idx] = float(lat) #/ 100

            for idx, lon in enumerate(lons):
                if self.is_str_Float(lon):
                    lon = float(lon)
                    if convert_to_DDmmmmm == True:
                        lon = float(lon) / 100
                        DD = math.trunc(lon)
                        mmmmm = lon - DD
                        ddddd = mmmmm * 100 / 60
                        lons[idx] = (DD + ddddd) * -1
                    else:
                        lons[idx] = float(lon) #/ -100
        except Exception as e:
            return 'plot_coords part 2 - ERROR: ' + str(e)

        try:
            colors = []
            if stat == 'pwr':
                stat_symbol = "kW"
                stat_name = "Power"
                for idx, ibat in enumerate(ibats):
                    if self.is_str_Float(ibat):
                        ibat = float(ibat)
                        pwr = abs((float(ibat) * float(vbats[idx])) / 1000) #we don't want to show charging as a negitive power....
                        colors.append(pwr) # power color selection could be improved here.
                    else:
                        colors.append(0)
            elif stat == 'soc':
                stat_symbol = "%"
                stat_name = "State of Charge"
                colors.append(0.0) #set min for color scale
                lons = np.append(lons, lons[-1])
                lats = np.append(lats, lats[-1])
                colors.append(100.0) #set max for color scale
                lons = np.append(lons, lons[-1])
                lats = np.append(lats, lats[-1])
                for idx, soc in enumerate(socs):
                    if self.is_str_Float(soc):
                        soc = float(soc)
                        colors.append(float(soc))
                    else:
                        colors.append(0)
            elif stat == 'pack_amp_hrs':
                stat_symbol = "Ah"
                stat_name = "Pack Amp Hrs"
                for idx, pack_amp_hrs in enumerate(pack_amp_hrs_list):
                    if self.is_str_Float(pack_amp_hrs):
                        pack_amp_hrs = float(pack_amp_hrs)
                        colors.append(float(pack_amp_hrs))
                    else:
                        colors.append(0)
            elif stat == 'spd':
                stat_symbol = "kts"
                stat_name = "Speed"
                for idx, spd in enumerate(spds):
                    if self.is_str_Float(spd):
                        spd = float(spd)
                        colors.append(float(spd))
                    else:
                        colors.append(0)

        except Exception as e:
            return 'plot_coords part 3 - ERROR: ' + str(e)

        try:
            df = pd.DataFrame({'lats': lats, 'lons': lons, stat_symbol: colors})
            df = df.dropna()
            df = df[df.lats != '']
            df = df[df.lons != '']
            df = df[df.lats != 0.0]
            df = df[df.lons != 0.0]
            df = df[df.lats != 'None']
            df = df[df.lons != 'None']
            df = df[df.lats != 'lat']
            df = df[df.lons != 'lon']
            df.lats = df.lats.astype(float)
            df.lons = df.lons.astype(float)
            df[stat_symbol] = df[stat_symbol].astype(float)

            #down sample before plotting
            df=df.iloc[2::10, :]

            max_bound = max(abs(df.lats.max() - df.lats.min()), abs(df.lons.min() - df.lons.max())) * 111 #todo: change this const to a variable with a discription of what it is
            zoom = 14 - np.log(max_bound)
            y1 = df.lats.min()
            y2 = df.lats.max()
            x1 = df.lons.min()
            x2 = df.lons.max()
            xspan = x2- x1
            yspan = y2 - y1
            center_lon = (xspan/2) + x1
            center_lat = (yspan/2) + y1

            if stat == 'soc':
                fig = px.scatter_mapbox(df, lat=df.lats, lon=df.lons, color=df[stat_symbol], color_continuous_scale='aggrnyl')  # 'rainbow')
            else:
                fig = px.scatter_mapbox(df, lat=df.lats, lon=df.lons, color=df[stat_symbol], color_continuous_scale='rainbow')

            #for zoom in range(12,13,1): #TODO zero in on good zoom level
            zoom=12
            fig.update_mapboxes(zoom=zoom, center_lat=center_lat, center_lon=center_lon)
            fig.update_layout(title='Trip Map: ' + stat_name, title_x=0.5, mapbox_style='carto-positron',
                              font_family='Helvetica',
                              font_size=10,
                              font_color='blue',
                              title_font_family='Helvetica',
                              title_font_size=20,
                              title_font_color='blue',
                              )
       #     fig.data[0].update(zmin=0.0, zmax=100)
            fig.write_image(maps_dir + image_name, width=1280, height=640)
        except Exception as e:
            return 'plot_coords part 4 - ERROR: ' + str(e)
            self.usage()
        #image_name = 'zoomlevel_' + str(zoom) + '_' + image_name
        return maps_dir + image_name


