package flags

import (
	"strconv"
	"strings"

	"github.com/aquasecurity/tracee/pkg/errfmt"
	"github.com/aquasecurity/tracee/pkg/events/queue"
	"github.com/aquasecurity/tracee/pkg/logger"
	"github.com/aquasecurity/tracee/types/trace"
)

func cacheHelp() string {
	return `Select different cache types for the event pipeline queueing.
Possible options:
cache-type={none,mem}                              pick the appropriate cache type.
mem-cache-size=256                                 set memory cache size in MB. only works for cache-type=mem.
Example:
  --cache cache-type=mem                                   | will cache events in memory using default values.
  --cache cache-type=mem --cache mem-cache-size=1024       | will cache events in memory. will set memory cache size to 1024 MB.
  --cache none                                             | no event caching in the pipeline (default).
Use this flag multiple times to choose multiple output options
`
}

func PrepareCache(cacheSlice []string) (*queue.CacheConfig, error) {
	var err error
	cacheTypeMem := false
	cacheTypeHybrid := false
	eventsCacheMemSizeMb := 0
	eventsCacheDiskSizeMb := 8192
	cacheStage := "after-decode"

	logger.Debugw("cache - preparing cache config")

	if strings.Contains(cacheSlice[0], "none") {
		return nil, nil
	}

	for _, o := range cacheSlice {
		cacheParts := strings.SplitN(o, "=", 2)
		if len(cacheParts) != 2 {
			return nil, errfmt.Errorf("unrecognized cache option format: %s", o)
		}
		key := cacheParts[0]
		value := cacheParts[1]

		switch key {
		case "cache-type":
			switch value {
			case "mem":
				cacheTypeMem = true
			case "hybrid":
				cacheTypeHybrid = true
			default:
				return nil, errfmt.Errorf(
					"unrecognized cache-mem option: %s (valid options are: none,mem)",
					o,
				)
			}
		case "mem-cache-size":
			if !cacheTypeMem && !cacheTypeHybrid {
				return nil, errfmt.Errorf(
					"you need to specify cache-type=mem or cache-type=hybrid before setting mem-cache-size",
				)
			}
			eventsCacheMemSizeMb, err = strconv.Atoi(value)
			if err != nil {
				return nil, errfmt.Errorf("could not parse mem-cache-size value: %v", err)
			}
		case "disk-cache-size":
			if !cacheTypeHybrid {
				return nil, errfmt.Errorf(
					"you need to specify cache-type=hybrid before setting disk-cache-size",
				)
			}
			eventsCacheDiskSizeMb, err = strconv.Atoi(value)
			if err != nil {
				return nil, errfmt.Errorf("could not parse disk-cache-size value: %v", err)
			}
		case "cache-stage":
			switch value {
			case "before-decode":
				cacheStage = value
			case "after-decode":
				cacheStage = value
			default:
				return nil, errfmt.Errorf(
					"unrecognized cache-stage option: %s (valid options are: before-decode,after-decode)",
					o,
				)
			}

		default:
			return nil, errfmt.Errorf("unrecognized cache option format: %s", o)
		}
	}

	if err != nil {
		return nil, err
	}

	// TODO: refactor
	if cacheStage == "before-decode" {
		logger.Debugw("cache - stage: before-decode")
		if cacheTypeMem {
			return queue.NewRawEventsCache(
				queue.NewEventQueueMem[[]byte](eventsCacheMemSizeMb),
			), nil
		} else if cacheTypeHybrid {
			rawEventQueue, err := queue.NewEventQueueHybrid[[]byte](eventsCacheMemSizeMb, eventsCacheDiskSizeMb)
			if err != nil {
				return nil, err
			}
			return queue.NewRawEventsCache(rawEventQueue), nil
		}
	} else {
		logger.Debugw("cache - stage: after-decode")
		if cacheTypeMem {
			return queue.NewDefaultCache(queue.NewEventQueueMem[trace.Event](eventsCacheMemSizeMb)), nil
		} else if cacheTypeHybrid {

			rawEventQueue, err := queue.NewEventQueueHybrid[trace.Event](eventsCacheMemSizeMb, eventsCacheDiskSizeMb)
			if err != nil {
				return nil, err
			}
			return queue.NewDefaultCache(rawEventQueue), nil
		}
	}

	return nil, nil
}
