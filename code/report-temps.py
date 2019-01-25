import urllib
import json
import ast
import rrdtool
import datetime
import uuid
import os
import glob
import sys
import ConfigParser
from logging.config import dictConfig

"""
# Flask application
# Read servers to connect to from a server-config file
# call each server in turn concatenating each sensor name and temperature
# value into a HTML document
#
"""
from flask import Flask
app = Flask(__name__)


def read_server_config():
    """
    Load the server configuration
    A file with the address and name

    :return: array of server configurations
    """
    config = ConfigParser.SafeConfigParser(
        {'name': '',
         'address': ''
         })

    try:
        config.readfp(open(root_folder + '/server.config'))
    except IOError:
        app.logger.error('Unable to read sensor configuration: %s', sys.exc_info()[1])
        ret = []
    else:
        ret = []
        for section in config.sections():
            server_def = {
                'name': section,
                'address': config.get(section, 'address')
                }
            if config.get(section, 'name') != '':
                server_def['name'] = config.get(section, 'name')

            if server_def['address'] == '':
                app.logger.warn(
                    'sensor configuration [%s] skipped because it must have an id and address', section)
            else:
                ret.append(server_def)
    return ret


def get_sensor_data(server_address):

    sensor_url = server_address + '/sensor/readall'
    try:
        uh = urllib.urlopen(sensor_url)
        data = uh.read()
        js = json.loads(str(data))
    except Exception:
        app.logger.warn(
            'Could not read sensor data from %s', server_address)
        js = []

    return js


def get_sensor_names(server_address):
    try:
        sensor_url = server_address + '/sensor/names'
        uh = urllib.urlopen(sensor_url)
        data = uh.read()
        js = json.loads(str(data))
    except Exception:
        app.logger.warn(
            'Could not read sensor names %s', sys.exc_info()[1])
        js =[]
    return js


def get_last_updated(sensor_name):
    ret = ''
    dbname = str(sensor_name).lower().replace(' ', '')
    db_file = '%s/%s.rrd' % (root_folder, dbname)
    try:
        r = str(rrdtool.lastupdate(db_file))
    except Exception:
        app.logger.warn(
            'Could not read last update: %s', sys.exc_info()[1])
    else:
        d = r.replace('datetime.datetime', '')
        ret = ast.literal_eval('[' + d + ']')

    return ret


def make_multi_graph(period, sensor_names, title):
    # save as a gif so that they can be found and deleted
    # without affecting the png images the individual sensors draw
    file_name = str(uuid.uuid4()) + ".gif"

    colors = ['#0000ff', '#008000', '#800000', '#ff0000', '#ffff00',
              '#800080', '#ffa500', '#00ffff', '#ff00ff',
              '#00ff00', '#000080', '#808000', '#808080', '#c0c0c0', '#008080']

    color_idx = 0
    graph_def_params = [
        root_folder + "/static/" + file_name,
        "-t",
        str(title) + " for the last " + str(period)[1:],
        "--start",
        str(period),
        "-w 600"]

    graph_line_params = []
    temp_idx = 0;
    for sensor in sensor_names:
        name = str(sensor)
        dbname = name.lower().replace(' ', '')
        graph_def_params.append("DEF:Value" + str(temp_idx) + "=" + dbname + ".rrd:" + dbname + ":AVERAGE")
        graph_line_params.append("LINE1:Value" + str(temp_idx) + colors[color_idx] + ":" + name)
        color_idx = color_idx + 1
        temp_idx = temp_idx + 1
        if color_idx > len(colors):
            color_idx = 1

    try:
        rrdtool.graph(graph_def_params,  graph_line_params)
    except Exception:
        app.logger.warn(
            'Could not create graph: %s', sys.exc_info()[1])

    return file_name


def format_for_html(sensor):
    div = '<div><p style="margin:2px;padding:2px"><span style="display: inline-block;width:100px">\
            %s</span><span>%s</span></p></div>' % (sensor['name'], sensor['value'])
    return div


def format_for_json(sensor):
    div = '{"id":"%s","name":"%s","temp":"%s"}' % (sensor['id'], sensor['name'], sensor['value'])
    return div


def make_image_html(sensor_name):
    name = str(sensor_name)
    img_name = name.lower().replace(' ', '') + ".png"
    return ' <img src="static/' + img_name + '" alt="' + name + '" >'


@app.route("/history/<period>")
def make_period_graph(period):
    return make_period_graph_int(period, 'all')


@app.route("/history/<sensor>/<period>")
def make_period_graph_sensor(sensor, period):
    # sensor can be a csv list of sensor names
    return make_period_graph_int(period, sensor)


def make_period_graph_int(period, sensor_to_plot):

    gifs = glob.glob('static/*.gif')
    for f in gifs:
        os.remove(f)

    if period[0:1] != '-':
        period = '-' + period

    sensor_to_plot = sensor_to_plot + ","

    # get sensors from all the servers
    cxerror = ''
    all_sensor_names = []
    for server in servers:
        try:
            sensor_list = get_sensor_names(server['address'])
        except IOError:
            cxerror = cxerror + '<p style="color:red">Unable to connect to: %s</p>' % server['name']
        else:
            for sensor in sensor_list:
                sensor_name = str(sensor['name']).lower() + ","
                if sensor_to_plot == 'all,' or str(sensor_to_plot).lower().find(sensor_name) != -1:
                    all_sensor_names.append(sensor['name'])

    image_file_name = make_multi_graph(period, all_sensor_names, sensor_to_plot)

    r = '<!DOCTYPE html>'
    r = r + '<html lang="en-US">'
    r = r + '<head>'
    r = r + '<title>Temperatures Over Period</title>'
    r = r + '</head>'
    r = r + '<body>'
    r = r + '<p>Temperatures from ' + sensor_to_plot + ' for the last ' + period[1:] + ' until now</p>'
    r = r + cxerror
    r = r + ' <img src="/static/' + image_file_name + '" alt="Last' + period[1:] + '" >'
    r = r + '</body>'
    r = r + '</html>'
    return r


@app.route("/")
def home():
    txthtml = ''
    imghtml = ''
    cxerror = ''
    date_read = datetime.datetime.now()

    for server in servers:
        try:
            sensor_list = get_sensor_names(server['address'])
        except IOError:
            cxerror = cxerror + '<p style="color:red">Unable to connect to %s</p>' % server['name']
        else:
            for sensor in sensor_list:
                last_updated_list = get_last_updated(sensor['name'])
                sensor_value = last_updated_list[0]
                txthtml = txthtml + format_for_html({
                    'name': sensor['name'],
                    'value': sensor_value['ds'].values()[0]
                })
                imghtml = imghtml + make_image_html(sensor['name'])

                date_read = datetime.datetime(
                    sensor_value['date'][0],
                    sensor_value['date'][1],
                    sensor_value['date'][2],
                    sensor_value['date'][3],
                    sensor_value['date'][4],
                    0)

    r = '<!DOCTYPE html>'
    r = r + '<html lang="en-US">'
    r = r + '<head>'
    r = r + '<title>Temperatures</title>'
    r = r + '</head>'
    r = r + '<body>'
    r = r + txthtml
    r = r + '<p>Last read at ' + date_read.strftime("%A, %d. %B %Y %I:%M%p") + "</p>"
    r = r + cxerror
    r = r + imghtml
    r = r + '</body>'
    r = r + '</html>'
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
                    'filename': '%s/report-temps.log' % root_folder,
                    'when': 'midnight',
                    'backupCount': 4
                }
        },
        'root': {'level': 'DEBUG', 'handlers': ['file']}
    })

    servers = read_server_config()
    app.run(debug=True, host='0.0.0.0')
