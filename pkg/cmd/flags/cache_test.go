package flags

import (
	"errors"
	"testing"

	"github.com/stretchr/testify/assert"

	"github.com/aquasecurity/tracee/pkg/events/queue"
	"github.com/aquasecurity/tracee/types/trace"
)

func TestPrepareCache(t *testing.T) {
	t.Parallel()

	testCases := []struct {
		testName      string
		cacheSlice    []string
		expectedCache *queue.CacheConfig
		expectedError error
	}{
		{
			testName:      "invalid cache option",
			cacheSlice:    []string{"foo"},
			expectedCache: nil,
			expectedError: errors.New("unrecognized cache option format: foo"),
		},
		{
			testName:      "invalid cache-type",
			cacheSlice:    []string{"cache-type=bleh"},
			expectedCache: nil,
			expectedError: errors.New(
				"unrecognized cache-mem option: cache-type=bleh (valid options are: none,mem)",
			),
		},
		{
			testName:      "cache-type=none",
			cacheSlice:    []string{"cache-type=none"},
			expectedCache: nil,
		},
		{
			testName:      "cache-type=mem",
			cacheSlice:    []string{"cache-type=mem"},
			expectedCache: queue.NewDefaultCache(queue.NewEventQueueMem[trace.Event](0)),
		},
		{
			testName:      "mem-cache-size=X without cache-type=mem",
			cacheSlice:    []string{"mem-cache-size=256"},
			expectedCache: nil,
			expectedError: errors.New(
				"you need to specify cache-type=mem before setting mem-cache-size",
			),
		},
		{
			testName:      "cache-type=mem with mem-cache-size=512",
			cacheSlice:    []string{"cache-type=mem", "mem-cache-size=512"},
			expectedCache: queue.NewDefaultCache(queue.NewEventQueueMem[trace.Event](512)),
		},
		{
			testName: "cache-type=mem with mem-cache-size=512 with cache-stage=before-decode",
			cacheSlice: []string{
				"cache-type=mem",
				"mem-cache-size=512",
				"cache-stage=before-decode",
			},
			expectedCache: queue.NewRawEventsCache(queue.NewEventQueueMem[[]byte](512)),
		},
	}

	for _, testcase := range testCases {
		testcase := testcase

		t.Run(testcase.testName, func(t *testing.T) {
			t.Parallel()

			cache, err := PrepareCache(testcase.cacheSlice)
			if testcase.expectedError != nil {
				assert.ErrorContains(t, err, testcase.expectedError.Error())
			}
			assert.Equal(t, testcase.expectedCache, cache)
		})
	}
}
