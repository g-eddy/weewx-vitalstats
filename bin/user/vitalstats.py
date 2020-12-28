"""
vitalstats module - data service for host's vital stats

provides obs_types:
    cpu_load    cpu load (runq lengths) across all cpus
    cpu_idle    idle (not system or user) collective cpu time
    cpu_temp    cpu core temperature
    mem_avail   physical memory available
    disk_avail  disk space available

configure by adding to data_services in weewx.conf i.e.
    [Engine]
        [[Services]]
            data_services = ..., user.vitalstats.VitalStatsSvc
and configuring service in its own stanza (optional) in weewx.conf:
    [VitalStats]
        # indicate when stat should be included by listing its bindings.
        # 'loop' indicates including in every LOOP packet. similarly,
        # 'archive' in every ARCHIVE record. both are optional (neither
        # means no inclusions).
        # if a stat is not mentioned, by default it is 'archive' only
        cpu_load = loop,archive     # LOOP packets and ARCHIVE records
        cpu_idle = loop             # only LOOP packets
        cpu_temp = archive          # only ARCHIVE records
        mem_avail =                 # never
        #disk_avail                 # not mentioned -> ARCHIVE records (default)

requires python 3.x, psutil module

vitalstats: ©2020 Graham Eddy <graham.eddy@gmail.com>
weewx: Copyright (c) 2020 Tom Keffer <tkeffer@gmail.com>
"""
import logging
import os
import psutil
from dataclasses import dataclass

import weewx
import weewx.units
import weewx.xtypes
from weewx.engine import StdService
from weewx.units import ValueTuple

log = logging.getLogger(__name__)
version = '2.0'

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


def cpu_load_5m():
    """calculate 5min load (runq length) across all cpus"""
    return os.getloadavg()[1] #/psutil.cpu_count() # no longer per-cpu


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


class VitalStatsSvc(StdService):
    """weewx data service to provide VitalStats observations"""

    DEF_BINDINGS = ['archive']

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

    def __init__(self, engine, config_dict):
        super(VitalStatsSvc, self).__init__(engine, config_dict)

        if weewx.debug > 0:
            log.debug(f"{self.__class__.__name__} {version} starting")

        # configuration
        svc_sect = config_dict.get('VitalStats', {})
        self.loop_stats = list()    # list of stats for each LOOP packet
        self.archive_stats = list() # list of stats for each ARCHIVE record
        for obs_type in VitalStatsSvc.STATS:

            # determine bindings for known obs_type
            if obs_type in svc_sect:
                # use provided bindings
                bindings = svc_sect[obs_type]
                if isinstance(bindings, str):
                    # convert string to list - assume possibly comma-separated
                    bindings = [b for b in bindings.split(',')]
                bindings = [b.strip().lower() for b in bindings]
            else:
                # use default bindings
                bindings = VitalStatsSvc.DEF_BINDINGS

            # add to appropriate loop_ or archive_ lists
            if 'loop' in bindings:
                self.loop_stats.append(obs_type)
            if 'archive' in bindings:
                self.archive_stats.append(obs_type)

        # do we have any work to do?
        if weewx.debug > 1:
            log.debug(f"{self.__class__.__name__} loop_stats={self.loop_stats}"
                      f" archive_stats={self.archive_stats}")
        if len(self.loop_stats) <= 0 and len(self.archive_stats) <= 0:
            log.warning(f"{self.__class__.__name__} no stat bindings - exit")
            return      # slip away without binding to any packets

        # bind to LOOP if required
        if len(self.loop_stats) > 0:
            self.bind(weewx.NEW_LOOP_PACKET, self.new_loop_packet)

        # bind to ARCHIVE if required
        if len(self.archive_stats) > 0:
            self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)

    def new_loop_packet(self, event):
        """handle LOOP event by inserting LOOP-related stats"""
        self.augment_packet(event.packet, self.loop_stats)

    def new_archive_record(self, event):
        """handle ARCHIVE event by inserting ARCHIVE-related stats"""
        self.augment_packet(event.record, self.archive_stats)

    def augment_packet(self, packet, stats):
        """evaluate and insert values of stats listed"""

        for obs_type in stats:
        
            # no input to marshall

            # call algorithm
            raw_value = VitalStatsSvc.STATS[obs_type].get_stat()

            # de-marshall into output ValueTuple
            output_vt = ValueTuple(raw_value,
                                   VitalStatsSvc.STATS[obs_type].output_unit,
                                   VitalStatsSvc.STATS[obs_type].output_group)
            if weewx.debug > 2:
                log.debug(f"{self.__class__.__name__}.augment_packet"
                          f" {obs_type} output_vt={output_vt}")

            # convert output ValueTuple to packet's unit system
            pkt_vt = weewx.units.convertStd(output_vt, packet['usUnits'])
            if weewx.debug > 1:
                log.debug(f"{self.__class__.__name__}.augment_packet"
                          f" {obs_type}={pkt_vt[0]}")

            # insert into packet
            if pkt_vt[0] is not None:
                packet[obs_type] = pkt_vt[0]

    def shutDown(self):
        """respond to shutdown request by setting stat lists to empty"""

        if weewx.debug > 0:
            log.debug(f"{self.__class__.__name__} shutdown")
        self.loop_stats = self.archive_stats =[]
