package queue

import (
	"fmt"
	"os"
	"path"
	"sync"

	"github.com/joncrlsn/dque"

	"github.com/aquasecurity/tracee/pkg/logger"
	"github.com/aquasecurity/tracee/types/trace"
)

// this usecase implements EventQueue interface with a memory stored queue (FIFO)
type eventQueueHybrid struct {
	mutex                 *sync.Mutex
	cond                  *sync.Cond
	cache                 *dque.DQue
	maxAmountOfEvents     int // max number of cached events possible
	eventsCacheMemSizeMB  int
	eventsCacheDiskSizeMB int
	verbose               string
	itemsPerSegment       int
}

// TODO: parametrize
var storeAt string = "/tmp/tracee/hybrid_cache"

func NewEventQueueHybrid(memorySizeMb int, diskSizeMb int) (CacheConfig, error) {
	q := &eventQueueHybrid{
		eventsCacheMemSizeMB:  memorySizeMb,
		eventsCacheDiskSizeMB: diskSizeMb,
	}
	err := q.setup()
	if err != nil {
		return nil, err
	}
	q.verbose = fmt.Sprintf(
		"Hybrid Event Queue (Size = %d MB in-memory, %d MB on-disk)",
		q.eventsCacheMemSizeMB, q.eventsCacheDiskSizeMB,
	)
	return q, err
}

func (q *eventQueueHybrid) String() string {
	return q.verbose
}

// EventBuilder creates an event and returns a pointer to it.
// This is used when we load a segment of the queue from disk.
func EventBuilder() interface{} {
	return &trace.Event{}
}

func (q *eventQueueHybrid) setup() error {
	q.mutex = new(sync.Mutex)
	q.cond = sync.NewCond(q.mutex)

	// set queue size and init queue
	q.maxAmountOfEvents = q.getQueueSizeInEvents()
	q.itemsPerSegment = q.maxAmountOfEvents / 10

	// TODO: parametrize path
	queuePath := path.Dir(storeAt)
	queueName := path.Base(storeAt)

	// Cleanup queue at the start. In some cases persistence
	// is benefitial (for example, if you want to keep events)
	// even after tracee  restart, however at the testing stage
	// we are interested in clean environment

	// TODO: parametrize whether queue should be cleaned
	_ = os.RemoveAll(storeAt)

	dq, err := dque.NewOrOpen(
		queueName,
		queuePath,
		q.itemsPerSegment,
		func() interface{} {
			return EventBuilder()
		},
	)
	if err != nil {
		return err
	}

	err = dq.TurboOn()
	if err != nil {
		return err
	}

	q.cache = dq

	return nil
}

// Enqueue pushes an event into the queue (may block until queue is available)
func (q *eventQueueHybrid) Enqueue(evt *trace.Event) {
	q.cond.L.Lock()
	// enqueue waits for de-queuing if cache is full (using >= instead of == to be in the safe side...)
	for q.cache.Size() >= q.maxAmountOfEvents {
		q.cond.Wait()
	}

	q.cache.Enqueue(evt)
	q.cond.L.Unlock()
	q.cond.Signal() // unblock dequeue if needed

	evt = nil
}

// Dequeue pops an event from the queue
func (q *eventQueueHybrid) Dequeue() *trace.Event {
	q.cond.L.Lock()

	// dequeue waits for en-queueing if cache is empty
	for q.cache.Size() == 0 {
		q.cond.Wait()
	}

	e, err := q.cache.Dequeue()
	if err != nil {
		q.cond.L.Unlock()
		return nil
	}

	event, ok := e.(*trace.Event)
	q.cond.L.Unlock()
	if !ok {
		return nil
	}

	q.cond.Signal() // unblock enqueue if needed

	return event
}

func (q *eventQueueHybrid) Size() int {
	// TODO: consider using SizeUnsafe()
	if q.cache != nil {

		logger.Debugw("Internal queue size: ", q.cache.Size())
		return q.cache.Size()
	} else {
		logger.Errorw("Cache is undefined")
		return 0
	}
}

func (q *eventQueueHybrid) Capacity() int {
	return q.maxAmountOfEvents
}

// getQueueSizeInEvents returns size of the fifo queue, in # of events, based on
// the host size
func (q *eventQueueHybrid) getQueueSizeInEvents() int {
	// eventSize is the memory footprint per event in bytes. This is NOT the
	// size of a single event, but the overall impact in memory consumption to
	// each cached event (defined by experimentation)
	eventSize := 1024

	kbToB := func(amountInKB int) int {
		return amountInKB * 1024
	}
	mbToKB := func(amountInMB int) int {
		return amountInMB * 1024
	}
	gbToMB := func(amountInGB int) int {
		return amountInGB * 1024
	}
	amountOfEvents := func(amountInMB int) int {
		return kbToB(mbToKB(amountInMB)) / eventSize
	}

	// EventsCacheMemSize was provided, return exact amount of events for it
	if q.eventsCacheMemSizeMB > 0 && q.eventsCacheDiskSizeMB > 0 {
		return amountOfEvents(q.eventsCacheMemSizeMB + q.eventsCacheDiskSizeMB)
	}

	switch {
	case q.eventsCacheMemSizeMB <= gbToMB(1): // up to 1GB, cache = ~256MB in events #
		return amountOfEvents(256)
	case q.eventsCacheMemSizeMB <= gbToMB(4): // up to 4GB, cache = ~512MB in events #
		return amountOfEvents(512)
	case q.eventsCacheMemSizeMB <= gbToMB(8): // up to 8GB, cache = ~1GB in events #
		return amountOfEvents(gbToMB(1))
	case q.eventsCacheMemSizeMB <= gbToMB(16): // up to 16GB, cache = ~2GB in events #
		return amountOfEvents(gbToMB(2))
	}

	// bigger hosts, cache = ~4GB in events #
	return amountOfEvents(gbToMB(4))
}

func (q *eventQueueHybrid) Teardown() error {
	if _, err := os.Stat(storeAt); err == nil {
		return os.RemoveAll(storeAt)
	} else {
		return err
	}
}
