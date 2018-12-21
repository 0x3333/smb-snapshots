# smb-snapshots
Python script to create snapshots for Samba shares using rsync.

## Motivation
I usually create samba servers, Shadow Copy is a really useful feature, this script, create the snapshost to be used by samba ShadowCopy feature.

## Usage

The first snapshot will be a full copy(cp -a) the next ones will be hard link to the first, thus you will need to at least double your storage.

Run `smb-snapshot -h` for help.

## Example

In this example, we have 2 shares, named `Share 1` and `Share 2`. The shares root is `/srv/samba` and the snapshots root is `/srv/snapshots`. There will be 100 snapshots in the store. The snapshots will be created on working days at 8,12,14,16 and 18hs.

In the `smb.conf` file, you must configure the share to have ShadowCopy enabled:
```
[Share 1]
	path = /srv/samba/Share 1
	read only = No
	vfs objects = shadow_copy2
	shadow:basedir = /srv/samba/Share 1
	shadow:snapdir = /srv/snapshots/Share 1
	shadow:sort = desc

[Share 2]
	path = /srv/samba/Share 2
	read only = No
	vfs objects = shadow_copy2
	shadow:basedir = /srv/samba/Share 2
	shadow:snapdir = /srv/snapshots/Share 2
	shadow:sort = desc
```

File: `/etc/smb-snapshot.conf`
```
[Config]
    # How many snapshots to keep(Default: 210)
    SNAP_COUNT = 100

[Cmd]
    # Command that will be executed before snapshots
    PRE_EXEC = /bin/mount -o remount,rw /srv/snapshots
    # Command that will be executed after snapshots(Even after a failure)
    POST_EXEC = /bin/mount -o remount,ro /srv/snapshots

[Directories]
    # Root folder to shares
    SHARES_ROOT = /srv/samba
    # Snapshots root folder
    SNAP_ROOT = /srv/snapshots
    # Shares to create snapshots(Relative to SHARES_ROOT, comma separated)
    SHARES = Share 1, Share 2
```

Configure a crontab job to create the snapshots:
```
# Run snapshots on working days, at 8,12,14,16,18hs.
0 8-20/2 * * 1-5	/usr/sbin/smb-snapshot.py > /dev/null
```

