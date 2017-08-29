import numpy as np


def write_schedule(schedule, sources, start_date, time_bins, filename):

    observing = False

    with open(filename, 'w') as file:

        for t, time_bin in enumerate(time_bins):

            date = start_date + time_bin
            date_string = '%s' % date.iso[0:-4]

            if np.any(schedule[..., t] == True):

                if not observing:

                    command_string = 'STARTUP'
                    file.write(date_string + '  ' + command_string + '\n')
                    observing = True

                source_id = np.where(schedule[..., t] == True)[0][0]
                source = sources[source_id]
                command_string = 'OBSERVING  ={"source": "%s", "dec": "%f", "ra": "%f"}'
                command_string = command_string % (source['name'], source['dec'].to('rad').value, source['ra'].to('rad').value)
                file.write(date_string + '  ' + command_string + '\n')

            else:

                if observing:
                    command_string = 'SHUTDOWN'
                    file.write(date_string + '  ' + command_string + '\n')
                observing = False

        date += (time_bins[-1] - time_bins[-2])
        date_string = '%s' % date.iso[0:-4]
        command_string = 'SHUTDOWN'
        file.write(date_string + '  ' + command_string)