# smb-snapshots
Python script to create snapshots for Samba shares using `cp` `reflinks`.


## Table of Contents

* [Motivation](#motivation)
* [Installation](#installation)
* [Usage](#usage)
* [Example](#example)
* [Logrotate](#logrotate)
* [Breaking changes](#breaking-changes)

## Motivation
I usually create samba servers, Shadow Copy is a really useful feature, this script, create the snapshost to be used by samba ShadowCopy feature.

## Installation

Currently, there is no release or version number, so the easiest installation procedure is to download the script and make it executable:

```bash
rm -f /usr/bin/smb-snapshots && curl -L "https://github.com/0x3333/smb-snapshots/releases/latest/download/smb-snapshots" \
    > /usr/bin/smb-snapshots && chmod +x /usr/bin/smb-snapshots && /usr/bin/smb-snapshots --version
```

The `smb-snapshots` executable will be available in the `/usr/bin` folder, and is ready to go.

I suggest using [Chronic](https://github.com/docwhat/chronic) when using `cron`, it will handle the output in case of failure and you will be notified only when an error has ocurred. Something like this:

```
0 9-20 * * 1-5	chronic /usr/bin/smb-snapshot
```

You can even use verbose output, as it will only be sent if an error occurs:

```
0 9-20 * * 1-5	chronic /usr/bin/smb-snapshot -vvv
```

`smb-snapshots` will create a PID file, so no overlapping instances will run, an error will be issued.

## Usage

The snapshots must reside in the same filesystem as the share folders, this is because we use reflinks to create the snapshot(sharing the file blocks).

Run `smb-snapshot -h` for help.

## Example

In this example, we have 2 shares, named `Share 1` and `Share 2`. The shares root is `/srv/shares` and the snapshots root is `/srv/snapshots`. There will be 720 snapshots in the store. The snapshots will be created on working days every hour from 9am to 8pm, thus 3 months of snapshots.

In the `smb.conf` file, you must configure the share to have ShadowCopy enabled:
```
[Share 1]
	path = /srv/shares/Share 1
	read only = No
	vfs objects = shadow_copy2
	shadow:basedir = /srv/shares/Share 1
	shadow:snapdir = /srv/snapshots/Share 1
	shadow:sort = desc

[Share 2]
	path = /srv/shares/Share 2
	read only = No
	vfs objects = shadow_copy2
	shadow:basedir = /srv/shares/Share 2
	shadow:snapdir = /srv/snapshots/Share 2
	shadow:sort = desc
```

File: `/etc/smb-snapshot.conf`
```
[Config]
    # How many snapshots to keep
    SNAPS_COUNT = 720

[Cmd]
    # Command that will be executed before snapshots(optional)
    PRE_EXEC = /bin/mount /srv/snapshots
    # Command that will be executed after snapshots(Even after a failure, optional)
    POST_EXEC = /bin/mount /srv/snapshots

[Directories]
    # Shares to create snapshots(Relative to SHARES_ROOT, comma separated)
    SHARES = Share 1, Share 2
    # Root folder to shares
    SHARES_ROOT = /srv/samba
    # Snapshots root folder
    SNAPS_ROOT = /srv/snapshots
```

Configure a crontab job to create the snapshots:
```
# Run snapshots on working days, every hour from 9am to 8pm.
0 9-20 * * 1-5	/usr/bin/smb-snapshot -vvv > /dev/null
```

### Logrotate

It's highly recommended to configure `logrotate` to rotate the log files. A configuration is provided in the repo, `logrotate.conf`, just copy to `/etc/logrotate.d` named `smb-snapshots` and you are good to go.

```bash
curl "https://raw.githubusercontent.com/0x3333/smb-snapshots/master/logrotate.conf" \
    > /etc/logrotate.d/smb-snapshots
```

## Breaking changes

Version 1.0.1:

* `SNAP_COUNT` has been renamed to `SNAPS_COUNT`.
* `SNAP_ROOT` has been renamed to `SNAPS_ROOT`.
