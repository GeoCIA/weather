import matplotlib.pyplot as plt
import json

from matplotlib.gridspec import GridSpec
from numpy import arange, array, hstack, r_, ones, hanning, convolve
import requests
from random import random
import math

NHOURS = 6
MAX_N = int(3600 * NHOURS / 15.)
DEBUG = True
UPDATE_PERIOD = 0.5 if DEBUG else 15

# WD = iter(xrange(0, 360, 15))


def update(path):
    if DEBUG:
        return {'CurrentWindSpeed': random(),
                'CurrentWindDirection': random() * 360,
                'CurrentWindGust': random(),
                'OutdoorTemperature': random()}

    ret = requests.get('http://192.168.0.141', timeout=10)
    if ret.status_code == 200:
        doc = ret.json()
        var = doc.get('variables')
        write_to_file(path, ret)
        return var
    else:
        print 'Failed {}'.format(ret)


def write_to_file(path, ret):
    with open(path, 'a') as wfile:
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
        max_gust, max_wind, min_wind, wind, outtemp, intemp = [], [], [], [], [], []
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
    def add_plot(ax, scatter=None, line=None, sline=None):
        if scatter is None:
            scatter = {'markersize': 2.5}
        if line is None:
            line = {}
        if sline is None:
            sline = {'color': 'green'}

        s = ax.plot([], [], 'bo', **scatter)[0]
        l = ax.plot([], [], 'b-', **line)[0]
        sl = ax.plot([], [], **sline)[0]
        return l, s, sl

    def add_indicator(ax):
        ps = [ax.plot([0, 0], [0, 1], color='green')[0] for i in xrange(5)]
        return ps

    # def add_polar_plot(ax):
    #     l = ax.plot([], [])
    #     return l

    plots = {}

    g = (4, 2)
    winddir_ax = plt.subplot2grid(g, (0, 0), projection='polar')
    windind_ax = plt.subplot2grid(g, (0, 1), projection='polar')
    wind_ax = plt.subplot2grid(g, (1, 0), colspan=2)
    gust_ax = plt.subplot2grid(g, (2, 0), colspan=2)
    temp_ax = plt.subplot2grid(g, (3, 0), colspan=2)

    plots['CurrentWindSpeed'] = (wind_ax, add_plot(wind_ax))
    plots['CurrentWindGust'] = (gust_ax, add_plot(gust_ax))
    plots['OutdoorTemperature'] = (temp_ax, add_plot(temp_ax))
    plots['windind'] = (windind_ax, add_indicator(windind_ax))
    plots['winddir'] = (winddir_ax, add_plot(winddir_ax))

    axes = (winddir_ax, windind_ax, wind_ax, gust_ax, temp_ax)
    plt.setp([ax.get_xticklabels() for ax in axes[:-1]], visible=False)
    plt.setp([ax.get_yticklabels() for ax in (windind_ax, winddir_ax)], visible=False)

    # f = plt.gcf()
    # f.subplots_adjust(hspace=0)

    wind_ax.set_ylabel('Wind (kph)')
    # ax2.set_ylabel('Direction (Deg)')
    gust_ax.set_ylabel('Gust (kph)')
    temp_ax.set_ylabel('Temp (C)')
    temp_ax.set_xlabel('time (min)')

    plt.pause(0.05)

    return plots


def set_limits(d, axis, axes=None):
    if axis == 'x':
        if axes:
            func = axes.set_xlim
        else:
            func = plt.xlim
    else:
        if axes:
            func = axes.set_ylim
        else:
            func = plt.ylim

    dmi, dma = d.min(), d.max()
    dev = (dma - dmi) * 0.1
    func(dmi - dev, dma + dev)


def add_polar_plot_datum(datum, p):
    ax, (line, scatter, sline) = p
    datum = math.radians(datum)

    theta = line.get_xdata()
    theta = hstack((theta, (datum,)))
    theta = theta[-MAX_N:]
    n = theta.shape[0]
    rad = arange(n) / float(n - 1)
    line.set_xdata(theta)
    line.set_ydata(rad)

    scatter.set_xdata(theta)
    scatter.set_ydata(rad)

    theta = smooth(theta, window_len=20)

    if theta.shape == rad.shape:
        sline.set_xdata(theta)
        sline.set_ydata(rad)

    ax.set_ylim(0, 1)


def add_plot_datum(datum, p):
    ax, (line, scatter, sline) = p
    y = line.get_ydata()
    y = hstack((y, (datum,)))
    y = y[-MAX_N:]
    x = arange(y.shape[0]) * 15 / 60.

    line.set_xdata(x)
    line.set_ydata(y)
    scatter.set_xdata(x)
    scatter.set_ydata(y)

    sy = smooth(y, window_len=20)

    if sy.shape == x.shape:
        sline.set_xdata(x)
        sline.set_ydata(sy)

    set_limits(x, 'x', axes=ax)
    set_limits(y, 'y', axes=ax)


def update_wind_indicator(datum, p):
    ax, plots = p
    n = len(plots)

    prevs = []
    for i, pp in enumerate(plots[1:]):
        po = plots[i]
        # print i,(n-i-1) / float(n), po.get_xdata()
        prevs.append((pp, po.get_xdata(),
                      [0, (n - i - 1) / float(n)]))

    for pp, x, y in prevs:
        pp.set_xdata(x)
        pp.set_ydata(y)
        #     # pp.set_xdata(po.get_xdata())
        #     # print i, (i+1)/float(n), po.get_xdata()
        # pp.set_ydata([0, (i+1)/float(n)])

    p0 = plots[0]
    p0.set_xdata([0, math.radians(datum)])


def plot_update(path):
    plots = plot()
    i = 0
    while 1:
        var = update(path)
        if var:
            wind = var.get('CurrentWindSpeed')
            temp = var.get('OutdoorTemperature')
            gust = var.get('CurrentWindGust')
            winddir = var.get('CurrentWindDirection')
            print 'Current Wind={}, Dir={}, Gust={}, Temp={}'.format(wind, winddir, gust, temp)
            for k in ('OutdoorTemperature', 'CurrentWindGust', 'CurrentWindSpeed'):
                add_plot_datum(var.get(k), plots[k])

            add_polar_plot_datum(winddir, plots['winddir'])
            update_wind_indicator(winddir, plots['windind'])

            plt.pause(UPDATE_PERIOD)


def smooth(x, window='flat', window_len=101):
    s = r_[x[window_len - 1:0:-1], x, x[-1:-window_len:-1]]
    if window == 'flat':  # moving average
        w = ones(window_len, 'd')
    elif window == 'hanning':
        w = hanning(window_len)
    y = convolve(w / w.sum(), s, mode='valid')
    return y[(window_len / 2 - 1):-(window_len / 2)]


def run(path):
    # data=load_data(path)
    # y = data['wind']
    # x= arange(y.shape[0])
    # plt.plot(x, y)

    # sy = smooth(y)
    # sx = arange(sy.shape[0])
    # plt.plot(sx, sy)
    # plt.show()
    print 'asfasf'
    plot_update(path)


if __name__ == '__main__':
    run('ourweather2.txt')
