#!/usr/bin/env python
from withings import *
from fitbit import *
import sys
import os
import time
import ConfigParser
from optparse import OptionParser
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
import urlparse


parser = OptionParser()
parser.add_option('-a', '--startdate', dest='startdate', type='int', help="UNIX Timestamp")
parser.add_option('-b', '--enddate', dest='enddate', type='int', help="UNIX Timestamp")
parser.add_option('-r', '--reset', dest='reset', action="store_true", default=False, help="Resync all data")
parser.add_option('-d', '--daemon', dest='daemon', action="store_true", default=False, help="Run as daemon")
parser.add_option('-i', '--interval', dest='interval', type='int', default=86400, help="Interval between syncs in seconds when in daemon mode")
parser.add_option('-c', '--config', dest='config', default='config.cfg', help="Config file")
parser.add_option('-t', '--test', dest='test', action="store_true", default=False, help="Test mode, do not send data to Fitbit")
parser.add_option('-u', '--setup', dest='setup', action="store_true", default=False, help="Setup mode, only setup authentification")
parser.add_option('-s', '--server', dest='server', action="store_true", default=False, help="Server mode, sync when notified")
parser.add_option('-p', '--port', dest='port', type='int', default=8000, help="Server port, default 8000")
parser.add_option('-w', '--weight-only', dest='weight_only', action="store_true", default=False, help="Only sync your weight")
parser.add_option('-f', '--fat-only', dest='fat_only', action="store_true", default=False, help="Only sync your fat weight")

(options, args) = parser.parse_args()

config = ConfigParser.ConfigParser()
if os.path.exists(options.config):
    config.read(options.config)
auth_config_changed = False

# Configuring Withings

if not config.has_section('withings'):
    config.add_section('withings')

if not config.has_option('withings', 'consumer_key') or not config.has_option('withings', 'consumer_secret'):
    print "You must provide a consumer key and consumer secret for Withings"
    print "Create an Oauth application here: https://oauth.withings.com/partner/add"
    config.set('withings', 'consumer_key', raw_input('Consumer key: '))
    config.set('withings', 'consumer_secret', raw_input('Consumer secret: '))
    auth_config_changed = True

if not config.has_option('withings', 'access_token') or not config.has_option('withings', 'access_token_secret') or not config.has_option('withings', 'user_id'):
    print "Starting authentification process for Withings..."
    withings_auth = WithingsAuth(config.get('withings', 'consumer_key'), config.get('withings', 'consumer_secret'))
    authorize_url = withings_auth.get_authorize_url()
    print "Goto %s" % authorize_url
    withings_creds = withings_auth.get_credentials(raw_input('PIN: '))
    config.set('withings', 'access_token', withings_creds.access_token)
    config.set('withings', 'access_token_secret', withings_creds.access_token_secret)
    config.set('withings', 'user_id', withings_creds.user_id)
    auth_config_changed = True
    print ""
else:
    withings_creds = WithingsCredentials(config.get('withings', 'access_token'), config.get('withings', 'access_token_secret'),
                                         config.get('withings', 'consumer_key'), config.get('withings', 'consumer_secret'),
                                         config.get('withings', 'user_id'))

# Configuring Fitbit

if not config.has_section('fitbit'):
    config.add_section('fitbit')

if not config.has_option('fitbit', 'consumer_key') or not config.has_option('fitbit', 'consumer_secret'):
    print "You must provide a consumer key and consumer secret for Fitbit"
    print "Create an Oauth application here: https://dev.fitbit.com/apps/new"
    config.set('fitbit', 'consumer_key', raw_input('Consumer key: '))
    config.set('fitbit', 'consumer_secret', raw_input('Consumer secret: '))
    auth_config_changed = True

if not config.has_option('fitbit', 'access_token') or not config.has_option('fitbit', 'access_token_secret'):
    print "Starting authentification process for Fitbit..."
    fitbit_auth = FitbitAuth(config.get('fitbit', 'consumer_key'), config.get('fitbit', 'consumer_secret'))
    authorize_url = fitbit_auth.get_authorize_url()
    print "Goto %s" % authorize_url
    fitbit_creds = fitbit_auth.get_credentials(raw_input('PIN: '))
    config.set('fitbit', 'access_token', fitbit_creds.access_token)
    config.set('fitbit', 'access_token_secret', fitbit_creds.access_token_secret)
    auth_config_changed = True
    print ""
else:
    fitbit_creds = FitbitCredentials(config.get('fitbit', 'access_token'), config.get('fitbit', 'access_token_secret'),
                                         config.get('fitbit', 'consumer_key'), config.get('fitbit', 'consumer_secret'))


if auth_config_changed:
    print "Saving authentification configuration in %s" % options.config
    with open(options.config, 'wb') as f:
        config.write(f)

if options.setup:
    sys.exit(0)


# Logic

withings_client = WithingsApi(withings_creds)
fitbit_client = FitbitApi(fitbit_creds)

if not config.has_section('sync'):
    config.add_section('sync')


def do_sync(startdate=None, enddate=None):
    params = {}
    if startdate and enddate:
        print "Syncing measures between %s and %s" % (startdate, enddate)
        params = {'startdate': startdate, 'enddate': enddate}
    elif startdate:
        print "Syncing measures since %s" % startdate
        params = {'startdate': startdate}
    elif enddate:
        print "Syncing measures until %s" % enddate
        params = {'enddate': enddate}
    else:
        print "Syncing all measures"

    try:
        measures = withings_client.get_measures(**params)
    except Exception as e:
        print "An error occured while fetching data from Withings: %s" % e
        return None

    print "Withings returned %s new measures" % len(measures)

    measures.reverse()
    lastupdate = None
    nb_measures = 0
    for m in measures:
        if not m.is_measure():
            continue

        print "%s timestamp=%s weight=%s fat=%s" % (m.date.isoformat(' '), m.data['date'], 
                                                    m.weight, m.fat_mass_weight)

        try:
            if not options.test and not options.fat_only and not m.weight is None:
                fitbit_client.post('/user/-/body/log/weight', {
                    'weight': unicode(m.weight),
                    'date': unicode(m.date.date().isoformat()),
                    'time': unicode(m.date.time().isoformat())})
            if not options.test and not options.weight_only and not m.fat_mass_weight is None:
                fitbit_client.post('/user/-/body/log/fat', {
                    'fat': unicode(m.fat_mass_weight),
                    'date': unicode(m.date.date().isoformat()),
                    'time': unicode(m.date.time().isoformat())})
        except Exception as e:
            print "An error occured while sending data to Fitbit: %s" % e
            break
        lastupdate = m.data['date']
        nb_measures += 1

    print "Synced %s measures (lastupdate=%s)" % (nb_measures, lastupdate)
    return lastupdate


class NotifyRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.do_POST()

    def do_POST(self):
        path = urlparse.urlparse(self.path)
        qs = urlparse.parse_qs(path.query)
        startdate = int(qs['startdate'][0])
        enddate = int(qs['enddate'][0])
        print "Notification: new measures between %s and %s" % (startdate, enddate)
        do_sync(startdate, enddate)
        self.send_response(200)


def start_server(port):
    if not config.has_option('sync', 'server_url'):
        server_url = raw_input('URL through which the server will be reachable: ')
        config.set('sync', 'server_url', server_url)
    else:
        server_url = config.get('sync', 'server_url') 
    print "Subscribing to notifications from Withings (url: %s)" % server_url
    withings_client.subscribe(server_url, 'Wiscale to Fibit Sync')
    server = HTTPServer(("localhost", port), NotifyRequestHandler)
    try:
        print "Starting server on port %s" % port
        server.serve_forever()
    except (KeyboardInterrupt, SystemExit):
        server.server_close()
    print "Unsubscribing to notifications from Withings"
    withings_client.unsubscribe(server_url)
    return None


def start_daemon(startdate, interval):
    print "Starting daemon mode, syncing since %s every %s seconds" % (startdate, interval)
    while True:
        r = do_sync(startdate)
        if not r is None:
            lastupdate = r
        try:
            time.sleep(interval)
        except (KeyboardInterrupt, SystemExit):
            break
    return lastupdate


# Sync

if not options.reset and options.startdate is None and options.enddate is None:
    if config.has_option('sync', 'lastupdate'):
        options.startdate = config.getint('sync', 'lastupdate') + 1

if options.test:
    print "Test mode, data WILL NOT be sent to Fitbit"

if options.weight_only:
    print "Only syncing weight measurements"
elif options.fat_only:
    print "Only tracking fat measurements"

lastupdate = None
if options.server:
    lastupdate = start_server(options.port)
elif options.daemon:
    lastupdate = start_daemon(options.startdate, options.interval)
elif options.reset:
    lastupdate = do_sync()
else:
    lastupdate = do_sync(options.startdate, options.enddate)

if not options.test:
    print "Writing configuration file in %s" % options.config
    if not lastupdate is None:
        config.set('sync', 'lastupdate', lastupdate)
    with open(options.config, 'wb') as f:
        config.write(f)
