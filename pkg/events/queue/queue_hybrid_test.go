package queue

import (
	"strconv"
	"sync"
	"testing"

	"github.com/stretchr/testify/assert"

	"github.com/aquasecurity/tracee/pkg/logger"
	"github.com/aquasecurity/tracee/types/trace"
)

func BenchmarkHybridEnqueueDequeue(b *testing.B) {
	q, err := NewEventQueueHybrid[trace.Event](512, 512)
	assert.NoError(b, err, "Failed to initialize event queue")
	defer q.Teardown()

	wg := sync.WaitGroup{}
	wg.Add(1)
	go func() {
		i := 0
		for {
			// b.Logf("i: %v before dequeue", i)
			e := q.Dequeue()
			// b.Logf("i: %v after dequeue", i)
			assert.NotNil(b, e)
			assert.Equal(b, i, e.Timestamp)
			i++

			if i >= b.N {
				// b.Logf("i: %v finished dequeue", i)
				break
			}
		}
		wg.Done()
	}()
	go func() {
		for i := 0; i < b.N; i++ {
			e := trace.Event{Timestamp: i}
			// b.Logf("i: %v before enqueue", i)
			q.Enqueue(&e)
			// b.Logf("i: %v after enqueue", i)
		}
		// b.Logf(" finished enqueue")
	}()
	wg.Wait()
}

func TestHybridEnqueueDequeue(t *testing.T) {
	t.Parallel()

	q, err := NewEventQueueHybrid[trace.Event](512, 512)
	assert.NoError(t, err, "Failed to initialize event queue")
	defer q.Teardown()

	wg := sync.WaitGroup{}
	wg.Add(1)
	go func() {
		i := 0
		for {
			e := q.Dequeue()
			assert.NotNil(t, e)
			assert.Equal(t, i, e.Timestamp)
			i++
			if i == 999 {
				break
			}
		}
		wg.Done()
	}()
	go func() {
		for i := 0; i < 1000; i++ {
			e := trace.Event{Timestamp: i}
			q.Enqueue(&e)
		}
	}()
	wg.Wait()
}

func TestHybridSize(t *testing.T) {
	t.Parallel()

	q, err := NewEventQueueHybrid[trace.Event](512, 512)
	defer q.Teardown()

	assert.NoError(t, err, "Failed to initialize event queue")

	assert.Equal(t, q.Capacity(), 524288)
	hybridQueue := q.(*eventQueueHybrid[trace.Event])

	itemsPerSegment := hybridQueue.getItemsPerSegment()
	queueMemorySizeMb := hybridQueue.getQueueMemorySizeInMb()
	queueDiskSizeMb := hybridQueue.eventsCacheDiskSizeMB

	logger.Debugw("Queue items per segment: " + strconv.Itoa(itemsPerSegment))
	logger.Debugw("Queue memory size: " + strconv.Itoa(queueMemorySizeMb))

	// Memory is 256 and not 512 since it's assigned based on
	// the host memory capacity heuristics
	assert.Equal(t, queueMemorySizeMb, 256)
	assert.Equal(t, itemsPerSegment, 131072)
	assert.Equal(t, queueDiskSizeMb, 512)
}
