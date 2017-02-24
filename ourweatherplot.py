# ===============================================================================
# Copyright 2017 ross
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ===============================================================================

# ============= enthought library imports =======================
# ============= standard library imports ========================
# ============= local library imports  ==========================
import matplotlib.pyplot as plt
import json
from numpy import arange, array, hstack
from Queue import Queue, Empty
from threading import Thread, Event
import requests
import time


def get_update(path, host):
    with open(path, 'a') as wfile:
        ret = requests.get('http://{}'.format(host), timeout=10)
        if ret.status_code == 200:
            doc = ret.json()
            var = doc.get('variables')
            print '{} writing max speed={} temp={}'.format(time.time(),
                                                           var.get('WindSpeedMax'),
                                                           var.get('OutdoorTemperature'))
            wfile.write(ret.text)
            return var
        else:
            print 'Failed {}'.format(ret)


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
    s = plt.plot([0], [0], 'bo')[0]
    l = plt.plot([0], [0], 'b-')[0]
    plt.xlim(-10, 110)
    plt.pause(0.05)
    return l, s


def plot_update(path, host):
    line, scatter = plot()
    while 1:
        var = get_update(path, host)
        if var:
            wind = var.get('CurrentWindSpeed')
            y = line.get_ydata()
            y = hstack((y, (wind,)))
            y = y[-100:]
            x = arange(y.shape[0])

            line.set_xdata(x)
            line.set_ydata(y)
            scatter.set_xdata(x)
            scatter.set_ydata(y)

            ymi, yma = y.min(), y.max()
            d = (yma - ymi) * 0.1
            plt.ylim(ymi - d, yma + d)

        plt.pause(5)


def run(path, host):
    plot_update(path, host)


if __name__ == '__main__':
    run('ourweather.txt', '')
# ============= EOF =============================================
