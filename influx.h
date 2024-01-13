#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <curl/curl.h>

// InfluxDB parameters
#define INFLUXDB_URL "http://localhost:8086/query?&db=gustoDBlp"

// Callback function to handle the response from the InfluxDB server
double write_callback(void *contents, size_t size, size_t nmemb, void *userp);

// Initialization function to connect to the Influx DB.
// Returns: The curl handle to pass to the handler function
CURL *init_influx();

double influxWorker(CURL *curl, char *query);

// global variable to be returned by worker from callback fn
extern double influx_return;
