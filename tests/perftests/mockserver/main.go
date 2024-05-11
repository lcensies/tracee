package main

import (
	"fmt"
	"log"
	"net/http"

	ginprometheus "github.com/mcuadros/go-gin-prometheus"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/rs/zerolog"

	"github.com/lcensies/tracee-mockserv/routes"
	"github.com/lcensies/tracee-mockserv/utils"
)

var opsProcessed = promauto.NewCounter(prometheus.CounterOpts{
	Name: "myapp_processed_ops_total",
	Help: "The total number of processed events",
})

func main() {
	zerolog.SetGlobalLevel(zerolog.InfoLevel)

	router := routes.NewRouter()

	prometheusExporter := ginprometheus.NewPrometheus("gin")
	prometheusExporter.Use(router)

	err := router.Run(fmt.Sprintf(":%v", utils.GetEnv("PORT", "3434")))
	if err != nil {
		log.Fatalf("Router error: %v", err)
	}

	http.Handle("/metrics", promhttp.Handler())
	http.ListenAndServe(":2112", nil)
}
