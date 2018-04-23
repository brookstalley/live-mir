# Live MIR

Live MIR is designed to be a platform for providing realtime rich metadata about music. Currently, Live MIR supports this fairly narrow scenario:

1. Receive song metadata from Shairport Sync over UDP Multicast
2. Find Metabrainz recording ID from song metadata
3. Find Acousticbrainz low- and high-level data from recording ID
4. Provide key and scale info to external systems via OSC
5. Provide realtime beat indications to external systems via OSC

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

### Prerequisites

* Python 3.5 or greater
* Asyncio and aiohttp
* osc4py3
* Cement

```
Give examples
```

### Running

Live MIR can be started like so:

```
python3 live-mir.py
```

Options for multicast listening port, OSC target IP address and port, and Musicbrainz and Acousticbrainz servers can be found in live-mir.conf. These same variables may be set from the command line; try the --help parameter for more info.

### Syncronizing

Usually, Shairport Sync knows the metadata for a song about 2 seconds before it starts playing, and that is enough time to do the Musicbrainz and Acousticbrainz lookups. For higher performance, you can run a local copy of one or both services and use live-mir.conf to instruct Live MIR to use your local servers.

Acousticbrainz provides beat information. Live MIR sends OSC messages at the times specified in this information, but between Asyncio scheduling, OSC transmission, and processing by the OSC target, there is some latency. The preschedule_ms config file and command like parameter will instruct Live MIR to send beat events a bit sooner to compensate. Default is 50ms.

## Authors

* **Brooks Talley** - *Initial work* - [BrooksTalley](https://github.com/brookstalley)

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details


