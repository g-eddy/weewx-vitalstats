"""
vitalstats module - xtypes for host's vital stats

provides obs_types:
    cpu_load    per-cpu load (runq lengths)
    cpu_idle    idle (not system or user) collective cpu time as percentage
    cpu_temp    cpu core temperature as celsius
    mem_avail   physical memory available as bytes
    disk_avail  disk space available as bytes

configure by adding to xtype_services in weewx.conf i.e.
    [Engine]
        [[Services]]
            xtype_services = ...,user.vitalstats.VitalStatsSvc

vitalstats: ©2020 Graham Eddy <graham.eddy@gmail.com>
weewx: Copyright (c) 2020 Tom Keffer <tkeffer@gmail.com>
"""
import logging
import os
import psutil

import weewx
import weewx.units
import weewx.xtypes
from weewx.engine import StdService
from weewx.units import ValueTuple

log = logging.getLogger(__NAME__)

##############################################################################

# inform weewx of units for new obs_types
weewx.units.obs_group_dict['cpu_load'] = 'group_count'
weewx.units.obs_group_dict['cpu_idle'] = 'group_percent'
weewx.units.obs_group_dict['cpu_temp'] = 'group_temperature'
weewx.units.obs_group_dict['mem_avail'] = 'group_data'
weewx.units.obs_group_dict['disk_avail'] = 'group_data'


@dataclass
class Algorithm:
    """define how to calculate stat"""
    #input_unit:    str             # no input
    get_stat:       [[], float]     # calculation
    output_unit:    str             # output unit of measure
    output_group:   str             # output unit group


class VitalStats(weewx.xtypes.XType):
    """xtypes for host's vital statistics"""

    STATS = {
        'cpu_load' : Algorithm(get_stat=cpu_load_5m,
                               output_unit='count',
                               output_group='group_count'),
        'cpu_idle' : Algorithm(get_stat=cpu_idle,
                               output_unit='percent',
                               output_group='group_percent'),
        'cpu_temp' : Algorithm(get_stat=cpu_temp,
                               output_unit='degree_C',
                               output_group='group_temperature'),
        'mem_avail': Algorithm(get_stat=mem_avail,
                               output_unit='byte',
                               output_group='group_data'),
        'disk_avail': Algorithm(get_stat=disk_avail,
                                output_unit='byte',
                                output_group='group_data'),
    }

    def __init__(self):
        super(VitalStats, self).__init__(self)

    def get_scalar(self, obs_type, record, db_manager):
        # can we handle this obs_type?
        if obs_type not in VitalStats.STATS:
            raise weewx.UnknownType(obs_type)

        # no input to marshall

        # call algorithm
        value = VitalStats.STATS[obs_type].get_stat()

        # de-marshall into ValueTuple
        vt = ValueTuple(value, VitalStats.STATS[obs_type].output_unit,
                               VitalStats.STATS[obs_type].output_group)
        if weewx.debug > 2:
            log.debug(f"{self.__class__.__name__} vt={vt}")

        # convert ValueTuple back to the units used by incoming record
        return weewx.units.convertStd(vt, record['usUnits'])


def cpu_load_5m():
    """calculate 5min per-cpu load (runq length)"""
    return os.getloadavg()[1]/psutil.cpu_count()


def cpu_temp():
    """calculate cpu core temperature in celsius"""
    return psutil.sensors_temperatures()['cpu_thermal'][0][1]


def cpu_idle():
    """calculate cpu idle time (exclude system or user) as percentage"""
    ratios = psutil.cpu_times()
    return ratios[3]/(ratios[0] + ratios[2] + ratios[3])*100.0


def mem_avail():
    """calculate available physical memory as bytes"""
    return psutil.virtual_memory()[1]


def disk_avail():
    """calculate available disk space as bytes"""
    return psutil.disk_usage('/')[2]

##############################################################################


class VitalStatsSvc(StdService):
    """weex service to register VitalStats xtypes"""

    def __init__(self, engine, config_dict):
        super(VitalStatsSvc, self).__init__(engine, config_dict)

        if weewx.debug > 0:
            log.debug(f"{self.__class__.__name__} started")
        self.vs = VitalStats()
        weewx.xtypes.xtypes.append(self.vs)

    def shutDown(self):
        """respond to shutdown request by de-registering VitalStats"""

        if weewx.debug > 1:
            log.debug(f"{self.__class__.__name__} shutdown")
        self.vs = VitalStats()
        weewx.xtypes.xtypes.remove(self.vs)
