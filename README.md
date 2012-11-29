# Sync WiScale weight measurements into Fitbit Dashboard

Withings Scale: http://www.withings.com/en/scales
Fitbit: http://www.fitbit.com/

Synchorize weight measurements done using the Withings Scale
into your Fitbit Dashboard

## Installation

    $ git clone git@github.com:maximebf/wiscale-fitbit-sync.git
    $ cd wiscale-fitbit-sync/
    $ pip install -r requirements.txt

## Usage

Configuration information are stored in a config file. The default
name is *config.cfg* and can be changed using *--config=FILENAME*.

On your first use, it will ask for all the needed authentification
information. To launch the program in setup mode only use:

    $ ./client.py --setup

This will not perform a sync.

If you want to see which measurements will be synced, you can run
the program in test mode, which will NOT send data to Fitbit:

    $ ./client.py --test

To sync the measurements, simply run the program:

    $ ./client.py

The program will automatically sync measurements added since the last
sync. The last synchronization date is stored in the config file.

You can run the program in daemon mode. It will run forever and
perform a sync every 24h (this can be changed using *--interval=SECONDS*).

    $ ./sync.py --daemon --interval=3600

## Server mode and notifications

The Withings API has a notification system where you can register an
url that will be called when a new measure is added.

The program has a builtin http server to receive these notifications,
you only need to provide the url through which the server will be 
reachable.

    $ ./sync.py --server --port=8000
