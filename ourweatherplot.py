import matplotlib.pyplot as plt
import json
from numpy import arange, array, hstack, r_, ones, hanning, convolve
from Queue import Queue, Empty
from threading import Thread, Event
import requests
import time
from random import random
import math

NHOURS = 6
MAX_N = int(3600*NHOURS/15.)
DEBUG = False
UPDATE_PERIOD = 0.5 if DEBUG else 15


def update(path):
    if DEBUG:
        return {'CurrentWindSpeed':random(),
    'CurrentWindDirection':random(),
    'CurrentWindGust':random(),
    'OutdoorTemperature':random()}

    ret = requests.get('http://192.168.0.141', timeout=10)
    if ret.status_code==200:
        doc = ret.json()
        var = doc.get('variables')
        write_to_file(path, ret)
        return var
    else:
        print 'Failed {}'.format(ret)


def write_to_file(path, ret):
    with open(path,'a') as wfile:
        wfile.write(ret.text)


def write_to_db(ret):
    
    conn = connect('localhost', user, password, dbname)
    cursor = conn.cursor()
    
    sql = 'INSERT INTO MeasurementTable'
    cursor.execute(sql, args)
    cursor.commit()
    cursor.close()
    
def load_data(path):
    with open(path, 'r') as rfile:
        max_gust,max_wind,min_wind,wind, outtemp,intemp = [],[],[],[],[],[]
        for line in rfile:
            doc = json.loads(line.strip())
            var = doc.get('variables')

            max_gust.append(var.get('WindGustMax'))
            max_wind.append(var.get('WindSpeedMax'))
            wind.append(var.get('CurrentWindSpeed'))
            min_wind.append(var.get('WindSpeedMin'))
            outtemp.append(var.get('OutdoorTemperature'))
            intemp.append(var.get('IndoorTemperature'))

    return {'max_gust': array(max_gust),
    'max_wind': array(max_wind),
    'min_wind': array(min_wind),
    'outtemp': array(outtemp),
    'intemp': array(intemp),
    'wind': array(wind)}


def plot():
    def add_plot(ax):
        s = ax.plot([],[],'bo', markersize=2.5)[0]
        l = ax.plot([],[], 'b-')[0]
        sl =ax.plot([],[])[0]
        return l,s,sl
        
    def add_polar_plot(ax):
        l = ax.plot([],[])
        return l
        
    f = plt.figure()
   
    #f, axes = plt.subplots(4, 1, sharex=True)
    ax2 = f.add_subplot(4,1,2)
    ax3 = f.add_subplot(4,1,3)
    ax4 = f.add_subplot(4,1,4)
    
    ax1 = f.add_subplot(4,1,1,projection='polar')
    
    axes = (ax1,ax2,ax3,ax4)
    
    windseries = add_plot(ax2)
    gustseries = add_plot(ax3)
    tempseries = add_plot(ax4)
    dirseries = add_polar_plot(ax1)
    
    plt.setp([ax.get_xticklabels() for ax in axes[:-1]], visible=False)
    #f.subplots_adjust(hspace=0)
    
    ax2.set_ylabel('Wind (kph)')
    #ax2.set_ylabel('Direction (Deg)')
    ax3.set_ylabel('Gust (kph)')
    ax4.set_ylabel('Temp (C)')
    ax4.set_xlabel('time (min)')
    
    plt.pause(0.05)
    return axes, windseries, dirseries, gustseries, tempseries


def set_limits(d, axis, axes=None):
    if axis=='x':
    	if axes:
    		func=axes.set_xlim
    	else:
    		func=plt.xlim
    else:
    	if axes:
    		func=axes.set_ylim
    	else:
    		func=plt.ylim

    dmi,dma = d.min(), d.max()
    dev = (dma-dmi)*0.1
    func(dmi-dev, dma+dev)

def add_polar_plot_datum(ax,datum, line):
    datum = math.radians(datum)

    theta = line.get_xdata()
    theta = hstack((theta, (datum,)))
    theta = theta[-MAX_N:]
    n = theta.shape[0]
    rad = arange(n)/float(n-1)
    line.set_xdata(theta)
    line.set_ydata(rad)
    ax.set_ylim(0,1)
    

def add_plot_datum(ax, datum, line, scatter, sline):
    y = line.get_ydata()
    y = hstack((y, (datum,)))
    y = y[-MAX_N:]
    x = arange(y.shape[0])*15/60.
    
    line.set_xdata(x)
    line.set_ydata(y)
    scatter.set_xdata(x)
    scatter.set_ydata(y)
    
    sy = smooth(y, window_len=20)

    if sy.shape == x.shape:
        sline.set_xdata(x)
        sline.set_ydata(sy)
    
    set_limits(x, 'x', axes=ax)
    set_limits(y,'y', axes=ax)
    
    
def plot_update(path):
    axes, windseries, dirseries, gustseries, tempseries = plot()
    while 1:
        var = update(path)
        if var:
            wind = var.get('CurrentWindSpeed')
            temp = var.get('OutdoorTemperature')
            gust = var.get('CurrentWindGust')
            winddir = var.get('CurrentWindDirection')
            print 'Current Wind={}, Dir={}, Gust={}, Temp={}'.format(wind, winddir, gust, temp)
            
            add_plot_datum(axes[3], temp, *tempseries)
            add_plot_datum(axes[2], gust, *gustseries)
            add_polar_plot_datum(axes[0], winddir, *dirseries)
            add_plot_datum(axes[1], wind, *windseries)
            plt.pause(UPDATE_PERIOD)


def smooth(x, window='flat', window_len=101):
	s=r_[x[window_len-1:0:-1],x,x[-1:-window_len:-1]]
	if window == 'flat': #moving average
		w=ones(window_len,'d')
	elif window == 'hanning':
		w= hanning(window_len)
	y=convolve(w/w.sum(),s,mode='valid')
	return y[(window_len/2-1):-(window_len/2)]
	
	
def run(path):
	#data=load_data(path)
	#y = data['wind']
	#x= arange(y.shape[0])
	#plt.plot(x, y)
	
	#sy = smooth(y)
	#sx = arange(sy.shape[0])
	#plt.plot(sx, sy)
	#plt.show()
    
    plot_update(path)

if __name__ == '__main__':
    run('ourweather2.txt')
