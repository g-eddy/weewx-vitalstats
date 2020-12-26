# weewx-vitalstats
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
GPL licenses apply
