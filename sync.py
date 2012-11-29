#!/usr/bin/env python
from withings import *
from fitbit import *
import sys
import os
import time
import ConfigParser
from optparse import OptionParser


parser = OptionParser()
parser.add_option('-l', '--lastupdate', dest='lastupdate', type='int', help="UNIX Timestamp since last update")
parser.add_option('-d', '--daemon', dest='daemon', action="store_true", default=False, help="Run as daemon")
parser.add_option('-i', '--interval', dest='interval', type='int', default=86400, help="Interval between syncs in seconds when in daemon mode")
parser.add_option('-c', '--config', dest='config', default='config.cfg', help="Config file")
parser.add_option('-t', '--test', dest='test', action="store_true", default=False, help="Test mode, do not send data to Fitbit")
parser.add_option('-s', '--setup', dest='setup', action="store_true", default=False, help="Setup mode, only setup authentification")

(options, args) = parser.parse_args()

config = ConfigParser.ConfigParser()
if os.path.exists(options.config):
    config.read(options.config)


# Configuring Withings

if not config.has_section('withings'):
    config.add_section('withings')

if not config.has_option('withings', 'consumer_key') or not config.has_option('withings', 'consumer_secret'):
    print "You must provide a consumer key and consumer secret for Withings"
    print "Create an Oauth application here: https://oauth.withings.com/partner/add"
    config.set('withings', 'consumer_key', raw_input('Consumer key: '))
    config.set('withings', 'consumer_secret', raw_input('Consumer secret: '))

if not config.has_option('withings', 'access_token') or not config.has_option('withings', 'access_token_secret') or not config.has_option('withings', 'user_id'):
    print "Starting authentification process for Withings..."
    withings_auth = WithingsAuth(config.get('withings', 'consumer_key'), config.get('withings', 'consumer_secret'))
    authorize_url = withings_auth.get_authorize_url()
    print "Goto %s" % authorize_url
    withings_creds = withings_auth.get_credentials(raw_input('PIN: '))
    config.set('withings', 'access_token', withings_creds.access_token)
    config.set('withings', 'access_token_secret', withings_creds.access_token_secret)
    config.set('withings', 'user_id', withings_creds.user_id)
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

if not config.has_option('fitbit', 'access_token') or not config.has_option('fitbit', 'access_token_secret'):
    print "Starting authentification process for Fitbit..."
    fitbit_auth = FitbitAuth(config.get('fitbit', 'consumer_key'), config.get('fitbit', 'consumer_secret'))
    authorize_url = fitbit_auth.get_authorize_url()
    print "Goto %s" % authorize_url
    fitbit_creds = fitbit_auth.get_credentials(raw_input('PIN: '))
    config.set('fitbit', 'access_token', fitbit_creds.access_token)
    config.set('fitbit', 'access_token_secret', fitbit_creds.access_token_secret)
    print ""
else:
    fitbit_creds = FitbitCredentials(config.get('fitbit', 'access_token'), config.get('fitbit', 'access_token_secret'),
                                         config.get('fitbit', 'consumer_key'), config.get('fitbit', 'consumer_secret'))


with open(options.config, 'wb') as f:
    config.write(f)

if options.setup:
    sys.exit(0)

# Sync

withings_client = WithingsApi(withings_creds)
fitbit_client = FitbitApi(fitbit_creds)

def do_sync(since):
    print "Starting sync for measures since %s" % since
    measures = withings_client.get_measures(lastupdate=since)
    measures.reverse()

    for m in measures:
        if not m.is_measure() or m.data['date'] <= since:
            continue
        print "%s timestamp=%s weight=%s" % (m.date.isoformat(' '), m.data['date'], m.weight)
        if not options.test and not m.weight is None:
            fitbit_client.post('/user/-/body/log/weight', {
                'weight': unicode(m.weight),
                'date': unicode(m.date.date().isoformat()),
                'time': unicode(m.date.time().isoformat())})
        since = m.data['date']

    print "Sync done until %s" % since
    print ""
    if not options.test:
        if not config.has_section('sync'):
            config.add_section('sync')
        config.set('sync', 'lastupdate', since)
        with open(options.config, 'wb') as f:
            config.write(f)
    return since

lastupdate=0
if not options.lastupdate is None:
    lastupdate = options.lastupdate
elif config.has_option('sync', 'lastupdate'):
    lastupdate = config.getint('sync', 'lastupdate')

if options.test:
    print "Test mode, data WILL NOT be sent to Fitbit"

if options.daemon:
    print "Starting daemon mode, syncing every %s seconds" % options.interval
    while True:
        lastupdate = do_sync(lastupdate)
        time.sleep(options.interval)
else:
    do_sync(lastupdate)
