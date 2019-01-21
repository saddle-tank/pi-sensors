#
# Read a 1wire sensor via the GPIO and
# make it available via a web page
#
import time
import json
import sys
import ConfigParser
from logging.config import dictConfig


from flask import Flask
app = Flask(__name__)


def read_sensor_definitions():
    """
    Read the file containing the definitions for the sensors

    :return: Array of sensor definitions
    """
    ret = []
    config = ConfigParser.SafeConfigParser(
        {'id': '',
         'type': '',
         'name': '',
         'units': '',
         'datatype': '',
         'address': ''
         })

    try:
        config.readfp(open(root_folder + '/sensor.config'))
    except IOError:
        app.logger.error('Unable to read sensor configuration: %s', sys.exc_info()[1])
    else:
        for section in config.sections():
            sensor_def = {
                'id': config.get(section, 'id'),
                'type': config.get(section, 'type'),
                'name': section,
                'units': config.get(section, 'units'),
                'datatype': config.get(section, 'datatype'),
                'address': config.get(section, 'address'),
                'value': '',
                'error': ''}
            if config.get(section, 'name') != '':
                sensor_def['name'] = config.get(section, 'name')
            if sensor_def['id'] == '' or sensor_def['address'] == '':
                app.logger.warn(
                    'sensor configuration [%s] skipped because it must have an id and address', section)
            else:
                ret.append(sensor_def)
                app.logger.debug(
                    'sensor configuration [%s] read', sensor_def)

    return ret


def read_sensor(sensor):
    """
    Read the sensor
    Will try 5 times before giving up

    :param sensor: the sensor to be read
    """
    sensor_dir = '/sys/bus/w1/devices/%s/w1_slave' % sensor['address']
    sensor['value'] = ''
    sensor['error'] = ''

    attempts = 0
    success = False
    lines = []
    while attempts < 5 and success is False:

        try:
            with open(sensor_dir, 'r') as f:
                lines = f.readlines()
        except Exception:
            app.logger.error('Unable to read sensor [%s] : %s', sensor['name'], sys.exc_info()[1])

        if len(lines) != 2 or lines[0].find('YES') == -1 or lines[1].find('t=') == -1:
            attempts = attempts + 1
            time.sleep(0.5)
        else:
            p = lines[1].find('t=')
            t = lines[1][p+2:]
            sensor['value'] = '{:.2f}'.format(float(t) / 1000.00)
            success = True

    if success is False:
        sensor['error'] = 'Could not read sensor'



def format_for_html(sensor):
    """
    Write the name and value for a sensor to a piece of simple HTML

    :param sensor: the sensor
    :return: HTML <div> block with the name and temp of the sensor
    """
    div = '<div><p style="margin:2px;padding:2px"><span style="display: inline-block;width:100px">\
            %s</span><span>%s</span></p></div>' % (sensor['name'], sensor['value'])
    return div


@app.route("/sensor/readall")
def jsensor_all():
    """
    Builds an array of JSON sensor definitions that include the sensor's value

    :return: array of JSON  sensor definitions
    """
    r = ''
    if len(sensors) > 0:
        for sensor in sensors:
            read_sensor(sensor)
            r = r + json.dumps(sensor) + ','
        r = r[:len(r)-1]

    return '[' + r + ']'


@app.route("/sensor/names")
def jsensor_names():
    """
    Returns the sensor definitions

    :return: array of JSON sensor definitions
    """
    r = ''
    if len(sensors) > 0:
        for sensor in sensors:
            sensor['value'] = ''
            sensor['error'] = ''
            r = r + json.dumps(sensor) + ','
        r = r[:len(r)-1]
    else:
        r = ''
    return '[' + r + ']'


@app.route("/")
def home():
    r = ''

    if len(sensors) > 0:
        for sensor in sensors:
            read_sensor(sensor)
            r = r + format_for_html(sensor)
    else:
        r = format_for_html({'name': 'No sensor configuration available', 'value': ''})

    return r


if __name__ == '__main__':

    root_folder = '.'
    if len(sys.argv) > 1:
        root_folder = str(sys.argv[1])

    dictConfig({
        'version': 1,
        'formatters': {
            'default':
                {'format': '%(asctime)s %(levelname)s %(message)s'}
        },
        'handlers': {
            'file':
                {
                    'class': 'logging.handlers.TimedRotatingFileHandler',
                    'formatter': 'default',
                    'filename': '%s/ws-read-sensors-gpio.log' % root_folder,
                    'when': 'midnight',
                    'backupCount': 4
                }
        },
        'root': {'level': 'DEBUG', 'handlers': ['file']}
    })

    sensors = read_sensor_definitions()
    app.run(debug=True, host='0.0.0.0', port=5000)
