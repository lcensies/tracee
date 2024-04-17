package queue

import (
	"errors"
	"fmt"
	"os"
	"path"
	"path/filepath"
	"sync"

	"github.com/joncrlsn/dque"

	"github.com/aquasecurity/tracee/types/trace"
)

// this usecase implements EventQueue interface with a memory stored queue (FIFO)
type eventQueueHybrid[T trace.Event | []byte] struct {
	mutex                      *sync.Mutex
	cond                       *sync.Cond
	cache                      *dque.DQue
	maxAmountOfEvents          int // max number of cached events possible
	eventsCacheMemSizeMB       int
	eventsCacheDiskSizeMB      int
	eventsCacheItemsPerSegment int
	verbose                    string
}

// eventSize is the memory footprint per event in bytes. This is NOT the
// size of a single event, but the overall impact in memory consumption to
// each cached event (defined by experimentation)
const eventSize int = 1024

// TODO: parametrize
var (
	traceeDir string = "/tmp/tracee"
	storeAt   string = filepath.Join(traceeDir, "hybrid_cache")
)

func NewEventQueueHybrid[T trace.Event | []byte](
	memorySizeMb int,
	diskSizeMb int,
) (EventQueue[T], error) {
	if diskSizeMb < memorySizeMb {
		return nil, errors.New(
			"Queue size on disk should be greater or equal to the in-memory size",
		)
	}

	q := &eventQueueHybrid[T]{
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

func (q *eventQueueHybrid[T]) String() string {
	return q.verbose
}

// EventBuilder creates an event and returns a pointer to it.
// This is used when we load a segment of the queue from disk.
func EventBuilder() interface{} {
	return &trace.Event{}
}

// func (q *eventQueueHybrid[T trace.Event]) BuildEvent() interface{} {
// 	return &trace.Event{}
// }

// Dqueue keeps only it's head and tail in the memory. Hence,
// the allowed memory usage by the queue is equals to the
// size of two segments. In one segment we can have
// kbToB(mbToKB(queueMemSizeMb)) / 2 bytes.
func (q *eventQueueHybrid[T]) getItemsPerSegment() int {
	queueMemSizeMb := q.getQueueMemorySizeInMb()

	return kbToB(mbToKB(queueMemSizeMb)) / 2 / eventSize
}

func (q *eventQueueHybrid[T]) setup() error {
	q.mutex = new(sync.Mutex)
	q.cond = sync.NewCond(q.mutex)

	q.eventsCacheItemsPerSegment = q.getItemsPerSegment()
	q.maxAmountOfEvents = q.getQueueSizeInEvents()

	// TODO: parametrize path
	queuePath := path.Dir(storeAt)
	queueName := path.Base(storeAt)

	// Cleanup queue at the start. In some cases persistence
	// is benefitial (for example, if you want to keep events)
	// even after tracee  restart, however at the testing stage
	// we are interested in clean environment

	// TODO: parametrize whether queue should be cleaned

	err := os.MkdirAll(traceeDir, 0755)
	_ = os.RemoveAll(storeAt)

	var builderFunc func() interface{}
	var sampleEvent T
	switch any(sampleEvent).(type) {
	case trace.Event:
		builderFunc = func() interface{} {
			return &trace.Event{}
		}
	default:
		builderFunc = func() interface{} {
			return make([]byte, 1024)
		}
	}
	// 	}

	// if reflect.TypeOf(T) == sampleEvent.(type) {
	// } else {
	// 	builderFunc = func() interface{} {
	// 		return make([]byte, 1024)
	// 	}
	// }

	// TODO: parametrize max dize of the
	// queue on disk
	dq, err := dque.NewOrOpen(
		queueName,
		queuePath,
		q.eventsCacheItemsPerSegment,
		func() interface{} {
			return builderFunc
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
func (q *eventQueueHybrid[T]) Enqueue(evt *T) {
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
func (q *eventQueueHybrid[T]) Dequeue() *T {
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

	event, ok := e.(*T)
	q.cond.L.Unlock()
	if !ok {
		return nil
	}

	q.cond.Signal() // unblock enqueue if needed

	return event
}

func (q *eventQueueHybrid[T]) Size() int {
	return q.cache.Size()
}

func (q *eventQueueHybrid[T]) Capacity() int {
	return q.maxAmountOfEvents
}

func kbToB(amountInKB int) int {
	return amountInKB * 1024
}

func mbToKB(amountInMB int) int {
	return amountInMB * 1024
}

func gbToMB(amountInGB int) int {
	return amountInGB * 1024
}

// getQueueMemorySizeInMb returns size of the fifo queue, in  megabytes, based on
// the host size
func (q *eventQueueHybrid[T]) getQueueMemorySizeInMb() int {
	switch {
	case q.eventsCacheMemSizeMB <= gbToMB(1): // up to 1GB, cache = ~256MB in events #
		return 256
	case q.eventsCacheMemSizeMB <= gbToMB(4): // up to 4GB, cache = ~512MB in events #
		return 512
	case q.eventsCacheMemSizeMB <= gbToMB(8): // up to 8GB, cache = ~1GB in events #
		return gbToMB(1)
	case q.eventsCacheMemSizeMB <= gbToMB(16): // up to 16GB, cache = ~2GB in events #
		return gbToMB(2)
	}

	// bigger hosts, cache = ~4GB in events #
	return gbToMB(4)
}

// getQueueSizeInEvents returns size of the fifo queue, in # of events, based on
// the host size
func (q *eventQueueHybrid[T]) getQueueSizeInEvents() int {
	amountOfEvents := func(amountInMB int) int {
		return kbToB(mbToKB(amountInMB)) / eventSize
	}

	// Queue is completely duplicated on disk including
	// first and last segments kept in memory.
	return amountOfEvents(q.eventsCacheDiskSizeMB)
}

func (q *eventQueueHybrid[T]) Teardown() error {
	if _, err := os.Stat(storeAt); err == nil {
		return os.RemoveAll(storeAt)
	} else {
		return err
	}
}
