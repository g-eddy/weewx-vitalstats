# weewx-vitalstats
<pre>
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
</pre>
