package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/prometheus/client_golang/api"
	promv1 "github.com/prometheus/client_golang/api/prometheus/v1"
	"github.com/urfave/cli/v2"
)

const (
	prometheusAddressFlag = "prometheus"
	periodFlag            = "periodLostTotalRatio"
	outputFlag            = "output"
	singleRunFlag         = "single"
	startTimeFlag         = "start"
	endTimeFlag           = "end"
)

type measurement struct {
	AvgEbpfRate         float64 `json:"avgEbpfRate"`
	AvgLostEventsRate   float64 `json:"avgLostEventsRate"`
	TotalEvents         int     `json:"totalEvents"`
	LostEvents          int     `json:"lostEvents"`
	LostTotalRatio      float64 `json:"lostTotalRatio"`
	CacheLoad           float64 `json:"cacheLoad"`
	CachedEvents        int     `json:"cachedEvents"`
	MemoryConsumptionMb int     `json:"memConsumptionMb"`
	CpuPercent          float64 `json:"cpuPercent"`
}

func (m measurement) Print() {
	log.Printf("\n")
	fmt.Printf("Events/Sec:     %f\n", m.AvgEbpfRate)
	fmt.Printf("EventsLost/Sec: %f\n", m.AvgLostEventsRate)
	fmt.Printf("Events Total:    %d\n", m.TotalEvents)
	fmt.Printf("Events Lost:    %d\n", m.LostEvents)
	fmt.Printf("Events cached:  %v\n", m.CachedEvents)
	fmt.Printf("Cache load percentage:  %v\n", m.CacheLoad)
	fmt.Printf("Lost/Total ratio:  %v\n", m.LostTotalRatio)
	fmt.Printf("Memory consumption (MB):  %v\n", m.MemoryConsumptionMb)
	fmt.Printf("CPU percent:  %v\n", m.CpuPercent)
	fmt.Println("===============================================")
}

func (m measurement) PrintJson() {
	res, _ := json.Marshal(m)
	fmt.Println(string(res))
}

type OutputMode string

const (
	jsonOutput   OutputMode = "json"
	prettyOutput OutputMode = "pretty"
)

func main() {
	app := cli.App{
		// TODO: fetch metrics during last periodFlag seconds
		Name:  "tracee-bench",
		Usage: "A prometheus based performance probe for tracee",
		Flags: []cli.Flag{
			&cli.StringFlag{
				Name:  prometheusAddressFlag,
				Usage: "address of a prometheus instance tracking tracee",
				Value: "http://localhost:9090",
			},
			&cli.IntFlag{
				Name:  periodFlag,
				Usage: "period of scraping in seconds",
				Value: 5,
			},
			&cli.StringFlag{
				Name:  outputFlag,
				Usage: "set output format (options: pretty, json)",
				Value: "pretty",
			},
			&cli.BoolFlag{
				Name:  singleRunFlag,
				Usage: "fetch metrics once instead of periodic polling",
				Value: false,
			},
			&cli.TimestampFlag{
				Name:   startTimeFlag,
				Usage:  "start timestamp to fetch metrics",
				Value:  cli.NewTimestamp(time.Now().Add(time.Duration(-60) * time.Second)),
				Layout: time.RFC3339,
			},
			&cli.TimestampFlag{
				Name:   endTimeFlag,
				Usage:  "end timestamp to fetch metrics",
				Value:  cli.NewTimestamp(time.Now()),
				Layout: time.RFC3339,
			},
		},
		Action: func(ctx *cli.Context) error {
			address := ctx.String(prometheusAddressFlag)

			if address == "" {
				return fmt.Errorf("prometheus address required for tracee-er")
			}

			client, err := api.NewClient(api.Config{
				Address: address,
			})
			if err != nil {
				return err
			}

			done := sigHandler()
			prom := promv1.NewAPI(client)
			ticker := time.NewTicker(time.Duration(ctx.Int(periodFlag)) * time.Second)

			outputMode := OutputMode(ctx.String(outputFlag))
			if outputMode == prettyOutput {
				fmt.Println("===================TRACEE-ER===================")
			}
			if ctx.Bool("single") {
				fetchMetrics(prom, time.Now(), outputMode)
				return nil
			}
			go func() {
				for {
					select {
					case <-done:
						{
							return
						}
					case now := <-ticker.C:
						fetchMetrics(prom, now, outputMode)
					}
				}
			}()
			<-done
			return nil
		},
	}
	err := app.Run(os.Args)
	if err != nil {
		log.Fatal(err)
	}
}

func fetchMetrics(prom promv1.API, now time.Time, outputMode OutputMode) {
	const (
		eventspersec = "events/sec"
		lostpersec   = "lost/sec"
		rulespersec  = "rules/sec"
		lostoverall  = "lost_events"
		total        = "total_events"
		losttototal  = "lost_to_total"
		cached       = "events_cached"
		cacheload    = "cache_load"
		cpuseconds   = "tracee_cpu_seconds"
		memload      = "mem_load_mb"
	)
	queries := map[string]struct {
		queryName string
		query     string
	}{
		eventspersec: {
			queryName: "average ebpf_events/sec",
			query:     "rate(tracee_ebpf_events_total[1m])",
		},
		lostpersec: {
			queryName: "average ebpf_lostevents/sec",
			query:     "rate(tracee_ebpf_lostevents_total[1m])",
		},
		// TODO: parametrize whether to capture only last minute for liot
		lostoverall: {
			queryName: "lost events",
			query:     "tracee_ebpf_lostevents_total",
		},
		total: {
			queryName: "total events",
			query:     "(tracee_ebpf_events_total + tracee_ebpf_lostevents_total)",
		},
		losttototal: {
			queryName: "lost to total events ratio",
			query:     "tracee_ebpf_lostevents_total/(tracee_ebpf_events_total / tracee_ebpf_lostevents_total)",
		},
		cached: {
			queryName: "cached_events",
			query:     "max_over_time(tracee_ebpf_events_cached[5s])",
		},
		cacheload: {
			queryName: "cache_load",
			query:     "max_over_time(tracee_ebpf_cache_load[5s])",
		},
		cpuseconds: {
			queryName: "tracee_cpu_percent",
			query:     "irate(process_cpu_seconds_total{job=\"tracee\"}[5m]) * 100",
		},
		memload: {
			queryName: "memory_consumption",
			query:     "process_resident_memory_bytes{job=\"tracee\"}",
		},
	}

	measurement := measurement{}
	wg := sync.WaitGroup{}
	wg.Add((len(queries)))
	for field, query := range queries {
		go func(queryField string, queryName string, query string) {
			defer wg.Done()
			res, _, err := prom.Query(context.Background(), query, now)
			if err != nil {
				log.Printf("failed to fetch %s: %v\n", queryName, err)
				return
			}

			queryResString := res.String()
			if queryResString == "" {
				log.Printf("failed to fetch %s: empty\n", queryName)
				return
			}
			val, _ := parseQueryResString(queryResString)
			switch queryField {
			case eventspersec:
				measurement.AvgEbpfRate = val
			case lostpersec:
				measurement.AvgLostEventsRate = val
			case lostoverall:
				measurement.LostEvents = int(val)
			case total:
				measurement.TotalEvents = int(val)
			case losttototal:
				measurement.LostTotalRatio = float64(val)
			case cached:
				measurement.CachedEvents = int(val)
			case cacheload:
				measurement.CacheLoad = float64(val)
			case memload:
				measurement.MemoryConsumptionMb = int(val) / 1024 / 1024
			case cpuseconds:
				measurement.CpuPercent = float64(val)
			}
		}(field, query.queryName, query.query)
	}
	wg.Wait()

	// measurement.LostTotalRatio = float64(measurement.LostEvents) /
	// 	float64(measurement.TotalEvents)

	switch outputMode {
	case prettyOutput:
		measurement.Print()
	case jsonOutput:
		measurement.PrintJson()
	}
}

func parseQueryResString(queryRes string) (float64, error) {
	startIndex := strings.LastIndex(queryRes, "=> ") + 3
	lastIndex := strings.LastIndex(queryRes, "@[") - 1
	return strconv.ParseFloat(queryRes[startIndex:lastIndex], 64)
}

func sigHandler() chan bool {
	sigs := make(chan os.Signal, 1)
	done := make(chan bool, 1)
	signal.Notify(sigs, syscall.SIGINT, syscall.SIGTERM)
	go func() {
		<-sigs
		done <- true
	}()
	return done
}
