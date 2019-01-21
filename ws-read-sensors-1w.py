import ow
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
        ret = []
    else:
        ret = []
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
                print('sensor configuration [%s] skipped because it must have an id and address' % section)
            else:
                ret.append(sensor_def)
    return ret


def read_sensor(sensor):
    """
    Read the sensor

    :param sensor: sensor to read
    """
    ow.init('localhost:4304')

    sensor['value'] = ''
    sensor['error'] = ''
    try:
        sensor_1w = ow.Sensor(str('/%s' % sensor['address']))
    except Exception:
        app.logger.warn(
            'Could not read sensor %s : %s', sensor['name'], sys.exc_info()[1])
        sensor['error'] = 'Could not read sensor'
    else:
        sensor['value'] = '{:.2f}'.format(float(sensor_1w.temperature))


def format_for_html(sensor):
    """
    Write the name and value for a sensor to a piece of simple HTML

    :param sensor: the sensor
    :return: HTML <div> block with the name and temp of the sensor
    """
    div = '<div><p style="margin:2px;padding:2px"><span style="display: inline-block;width:100px">\
            %s</span><span>%s</span></p></div>' % (sensor['name'], sensor['value'])
    return div


@app.route("/")
def home():
    r = ''
    if len(sensors) > 0:
        for sensor in sensors:
            read_sensor(sensor)
            r = r + format_for_html(sensor)
    else:
        r = format_for_html({'name': 'No sensor configuration available', 't': ''})

    return r


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
        r = r[:len(r) - 1]

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
            sensor['error'] = ''
            sensor['value'] = ''
            r = r + json.dumps(sensor) + ','
        r = r[:len(r)-1]
    else:
        r = ''
    return '[' + r + ']'


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
                    'filename': '%s/ws-read-sensors-1w.log' % root_folder,
                    'when': 'midnight',
                    'backupCount': 4
                }
        },
        'root': {'level': 'DEBUG', 'handlers': ['file']}
    })

    sensors = read_sensor_definitions()
    app.run(debug=True, host='0.0.0.0', port=5000)
