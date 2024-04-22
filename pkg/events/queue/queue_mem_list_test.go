package queue

import (
	"sync"
	"testing"

	"github.com/stretchr/testify/assert"

	"github.com/aquasecurity/tracee/types/trace"
)

func BenchmarkEnqueueDequeue(b *testing.B) {
	q := NewEventQueueMem[trace.Event](1024)
	defer q.Teardown()

	wg := sync.WaitGroup{}
	wg.Add(1)
	go func() {
		i := 0
		for {
			e := q.Dequeue()
			assert.NotNil(b, e)
			assert.Equal(b, i, e.Timestamp)
			i++

			if i >= b.N {
				break
			}
		}
		wg.Done()
	}()
	go func() {
		for i := 0; i < b.N; i++ {
			e := trace.Event{Timestamp: i}
			q.Enqueue(&e)
		}
	}()
	wg.Wait()
}

func TestEnqueueDequeue(t *testing.T) {
	t.Parallel()

	q := NewEventQueueMem[trace.Event](1024)
	wg := sync.WaitGroup{}
	wg.Add(1)
	go func() {
		i := 0
		for {
			e := q.Dequeue()
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
