// package queue defines the interface and and implementation of a queue for events storage.
// the interface is defined by EventQueue while the (currently only) implementation is defined by
// eventQueueMem.
package queue

import (
	"github.com/aquasecurity/tracee/pkg/logger"
	"github.com/aquasecurity/tracee/types/trace"
)

type CacheConfig struct {
	eventQueue    EventQueue[trace.Event]
	rawEventQueue EventQueue[[]byte]
	stage         string

	stringFunc   func() string
	sizeFunc     func() int
	capacityFunc func() int
	teardownFunc func() error
}

func (c *CacheConfig) EnqueueRaw(event *[]byte) {
	// logger.Debugw("cache - enqueue raw event")
	// if c.eventQueue != nil {
	// 	panic("cache - eventQueue is set")
	// }
	// if c.rawEventQueue == nil {
	// 	panic("cache - rawEventQueue not is set")
	// }
	c.rawEventQueue.Enqueue(event)
}

func (c *CacheConfig) DequeueRaw() *[]byte {
	// logger.Debugw("cache - dequeue raw event")
	// if c.eventQueue != nil {
	// 	panic("cache - eventQueue is set")
	// }
	// if c.rawEventQueue == nil {
	// 	panic("cache - rawEventQueue not is set")
	// }
	return c.rawEventQueue.Dequeue()
}

func (c *CacheConfig) Enqueue(event *trace.Event) {
	// logger.Debugw("cache - enqueue event")
	// if c.rawEventQueue != nil {
	// 	panic("cache - rawEventQueue not is set")
	// }
	// if c.eventQueue == nil {
	// 	panic("cache - eventQueue is set")
	// }
	c.eventQueue.Enqueue(event)
}

func (c *CacheConfig) Dequeue() *trace.Event {
	// logger.Debugw("cache - dequeue event")
	//
	// if c.rawEventQueue != nil {
	// 	panic("cache - rawEventQueue not is set")
	// }
	// if c.eventQueue == nil {
	// 	panic("cache - eventQueue is set")
	// }
	return c.eventQueue.Dequeue()
}

func (c *CacheConfig) Stage() string {
	return c.stage
}

func (c *CacheConfig) String() string {
	return c.stringFunc()
}

func (c *CacheConfig) Size() int {
	return c.sizeFunc()
}

func (c *CacheConfig) Capacity() int {
	return c.capacityFunc()
}

func (c *CacheConfig) Teardown() error {
	return c.teardownFunc()
}

func NewDefaultCache(queue EventQueue[trace.Event]) *CacheConfig {
	return &CacheConfig{
		eventQueue:    queue.(EventQueue[trace.Event]),
		rawEventQueue: nil,
		stage:         "after-decode",
		stringFunc:    queue.String,
		sizeFunc:      queue.Size,
		capacityFunc:  queue.Capacity,
		teardownFunc:  queue.Teardown,
	}
}

func NewRawEventsCache(queue EventQueue[[]byte]) *CacheConfig {
	logger.Debugw("queue - constructing new event queue")
	return &CacheConfig{
		eventQueue:    nil,
		rawEventQueue: queue.(EventQueue[[]byte]),
		stage:         "before-decode",
		stringFunc:    queue.String,
		sizeFunc:      queue.Size,
		capacityFunc:  queue.Capacity,
		teardownFunc:  queue.Teardown,
	}
}

type EventQueue[T trace.Event | []byte] interface {
	String() string
	Enqueue(*T)
	Dequeue() *T
	Size() int
	Capacity() int
	Teardown() error
}
