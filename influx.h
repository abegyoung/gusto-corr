#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <curl/curl.h>


// global variable to be returned by worker from callback fn
//extern double influx_return;

// struct for the influxDB worker to return
struct influxStruct
{
  float    value;
  int16_t  scanID;
  uint64_t time;
};
extern struct influxStruct influxReturn;


// InfluxDB parameters
#define INFLUXDB_URL "http://localhost:8086/query?&db=gustoDBlp"

// Callback function to handle the response from the InfluxDB server
struct influxStruct write_callback(void *contents, size_t size, size_t nmemb, void *userp);

// Initialization function to connect to the Influx DB.
// Returns: The curl handle to pass to the handler function
CURL *init_influx();

struct influxStruct influxWorker(CURL *curl, char *query);
