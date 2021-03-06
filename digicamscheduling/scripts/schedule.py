"""
Plot catalog

Usage:
  digicamscheduling-schedule [options]

Options:
 -h --help                    Show this screen.
 --start_date=DATE            Starting date (UTC) YYYY-MM-DD HH:MM:SS
 --end_date=DATE              Ending date (UTC) YYYY-MM-DD HH:MM:SS
 --time_step=MINUTES          Time steps in minutes
                              [default: 30]
 --location_filename=PATH     PATH for location config file
 --sources_filename=PATH      PATH for catalog
 --environment_filename=PATH  PATH for environmental limitations
 --output_path=PATH           PATH to write the schedule
                              [default: .]
 --use_moon                   Choose to use Moon elevation and phase into
                              source visibility computation
"""
from docopt import docopt
import numpy as np
import astropy.units as u
from astropy.coordinates import EarthLocation
from astropy.time import Time
from digicamscheduling.io import reader
from digicamscheduling.core import gamma_source, moon, sun
from digicamscheduling.core.environement import \
    interpolate_environmental_limits, is_above_environmental_limits,\
    compute_observability
from digicamscheduling.utils import time
from digicamscheduling.core.scheduler import find_quality_schedule
from tqdm import tqdm
from digicamscheduling.io.writer import write_schedule
from digicamscheduling.utils.docopt import convert_commandline_arguments
import os


def main(sources_filename, location_filename, environment_filename,
         start_date, end_date, time_step, output_path, use_moon):

    sources = reader.read_catalog(sources_filename)
    coordinates = reader.read_location(filename=location_filename)
    location = EarthLocation(**coordinates)

    alt_trees, az_trees = reader.read_environmental_limits(
        environment_filename)
    alt_trees = alt_trees * u.deg
    az_trees = az_trees * u.deg
    env_limits = interpolate_environmental_limits(alt_trees,
                                                  az_trees)

    start_date = Time(start_date)  # time should be 00:00
    end_date = Time(end_date)  # time should be 00:00

    date = time.compute_time(date_start=start_date, date_end=end_date,
                             time_step=time_step, location=location,
                             only_night=True)

    moon_position = moon.compute_moon_position(date=date, location=location)
    moon_elevation = moon_position.alt
    moon_phase = moon.compute_moon_phase(date=date)
    sun_position = sun.compute_sun_position(date=date, location=location)
    sun_elevation = sun_position.alt

    observability = compute_observability(sun_elevation, moon_elevation,
                                          moon_phase, use_moon=use_moon)

    source_visibility = np.zeros((len(sources), len(date)))

    for i, source in tqdm(enumerate(sources), total=len(sources),
                          desc='Source'):

        temp = gamma_source.compute_source_position(date=date,
                                                    location=location,
                                                    ra=source['ra'],
                                                    dec=source['dec'])
        source_elevation = temp.alt
        source_azimuth = temp.az
        is_above_trees = is_above_environmental_limits(
            source_elevation, source_azimuth, env_limits)
        moon_separation = temp.separation(moon_position)

        temp = is_above_trees * np.sin(source_elevation)
        temp *= observability * (moon_separation > 10 * u.deg)
        temp *= source['weight']

        source_visibility[i] = temp

    availability, schedule = find_quality_schedule(source_visibility)
    filename = os.path.join(output_path, 'schedule_{}_{}.txt'.format(
        start_date.isot, end_date.isot))
    write_schedule(schedule, sources, date, filename)


def entry():

    kwargs = docopt(__doc__)
    kwargs = convert_commandline_arguments(kwargs)

    main(**kwargs)
