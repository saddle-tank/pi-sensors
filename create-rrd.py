import rrdtool
import urllib
import json
import ConfigParser
import sys
import os
"""
Create a RRD database file for a sensor(s)
Reads the server.config file to get the servers
Ask each server for the sensors it has
Create RRD database using sensor name as the db name
Only create if the file does not exist
"""

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
        print('Unable to read server configuration: %s' % sys.exc_info()[1])
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
                print('server configuration [%s] skipped because it must have an address' % section)
            else:
                ret.append(server_def)
    return ret


def get_sensor_names(server_url):
    sensor_url = server_url + '/sensor/names'
    print('CONNECTING TO ' + sensor_url)
    try:
        uh = urllib.urlopen(sensor_url)
        data = uh.read()
        js = json.loads(str(data))
    except Exception:
        print('Unable to get sensor names: %s' % sys.exc_info()[1])

    return js


def create_rrd(sensor_name):

    dbname = str(sensor_name).lower().replace(' ', '')
    db_file = '%s/%s.rrd' % (root_folder, dbname)

    if os.path.exists(db_file) is False:
        print('CREATING RRD DATABASE : %s' % dbname)
        try:
            rrdtool.create(
                dbname + '.rrd',
                "--start", "now",
                "--step", "300",
                "DS:" + dbname + ":GAUGE:600:-100:50",
                "RRA:AVERAGE:0.5:12:1344")
        except Exception:
            print('Unable to create database: %s' % sys.exc_info())


if __name__ == '__main__':
    root_folder = '.'
    if len(sys.argv) > 1:
        root_folder = str(sys.argv[1])

    servers = read_server_config()

    for server in servers:
        sensor_list = get_sensor_names(server['address'])
        for sensor in sensor_list:
            create_rrd(sensor['name'])
