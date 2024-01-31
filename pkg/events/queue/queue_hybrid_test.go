package queue

import (
	"strconv"
	"sync"
	"testing"

	"github.com/stretchr/testify/assert"

	"github.com/aquasecurity/tracee/pkg/logger"
	"github.com/aquasecurity/tracee/types/trace"
)

func TestHybridEnqueueDequeue(t *testing.T) {
	t.Parallel()

	q, err := NewEventQueueHybrid(512, 512)

	assert.NoError(t, err, "Failed to initialize event queue")

	// capacity := q.Capacity()
	logger.Errorw("Init cache capacity: ", strconv.Itoa(q.Capacity()))

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
