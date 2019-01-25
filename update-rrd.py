import rrdtool
import urllib
import json
import ConfigParser
import sys
"""
Update RRD database with sensor readings
This script should be called from a scheduled task (cron job) every 5 minutes
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


def get_sensor_data(server_address):
    """
    Call the sensor server details of the sensors it has

    :param server_url: the url of the server
    :return: JSON array of sensor information
    """

    try:
        sensor_url = server_address + '/sensor/readall'
        uh = urllib.urlopen(sensor_url)
        data = uh.read()
        js = json.loads(str(data))
    except Exception:
        print('Could not make a connection to the server: %s' % sys.exc_info()[1])
        js = []

    return js


def update_rrd(sensor):

    update_value = 'N:' + str(sensor['value'])
    dbname = str(sensor['name']).lower().replace(' ', '')
    db_file = '%s/%s.rrd' % (root_folder, dbname)

    try:
        rrdtool.update(db_file, update_value)
    except Exception:
        print('Could not update rrd: %s' % sys.exc_info()[1])


def make_graph(sensor):
    name = str(sensor['name'])
    units = str(sensor['units'])
    dbname = name.lower().replace(' ', '')
    try:
        rrdtool.graph(root_folder + '/static/' + dbname + ".png",
                      "-t", name,
                      "--start", "-2days", "-w 400",
                      "DEF:value=" + dbname + ".rrd:" + dbname + ":AVERAGE",
                      "LINE1:value#ff0000:" + units)
    except Exception:
        print('Could not create graph: %s' % sys.exc_info()[1])


if __name__ == '__main__':
    root_folder = '.'
    if len(sys.argv) > 1:
        root_folder = str(sys.argv[1])

    servers = read_server_config()

    for server in servers:
        sensor_list = get_sensor_data(server['address'])
        for sensor in sensor_list:
            if sensor['error'] != '':
                print('Sensor: %s reported error: %s' % (sensor['name'], sensor['error']))
            else:
                update_rrd(sensor)
                make_graph(sensor)
