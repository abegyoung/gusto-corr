#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <curl/curl.h>
#include "corrspec.h"
#include "influx.h"

double influx_return;

// Callback function to handle the response from the InfluxDB server
double write_callback(void *contents, size_t size, size_t nmemb, void *userp) {

    char *token;
    int position = 0;
    char time[64]="";
    char ID[12]="";
    int scanID;
    float value;
    size_t realsize = size * nmemb;

    token = strtok(contents, ",");

    // Parse the InfluxDB return string
    while (token != NULL ) {
        token = strtok(NULL, ",");

        if (position == 4)     //get time string from influxdb return
            strncpy(time, token+12, 23);

        if (position == 5){    //get scanID from influxdb return
            strncpy(ID, token+1, strlen(token)-1);
            scanID = atoi(ID);
        }

        if (position == 6)     //get value string from influxdb return
            value = atof(token);
        position++;
    }

    printf("value = %.3f\n", value);
    printf("scanID = %d\n", scanID);
    printf("time = %s\n", time);

    influx_return = value;

    //return realsize;
    return influx_return;
}

// worker for the Influx DB query
// Takes: curl handle
// Operates: makes the function callback( )
double influxWorker(CURL *curl, char *query)
{

    CURLcode res;

    if (curl) {
        // Set the InfluxDB URL
        curl_easy_setopt(curl, CURLOPT_URL, INFLUXDB_URL);

        // Set the POST data (query)
        curl_easy_setopt(curl, CURLOPT_POSTFIELDS, query);

        // Set the callback function to handle the response
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_callback);

        // Make the HTTP POST request
        res = curl_easy_perform(curl);



    }

   // Cleanup Influx DB
   curl_easy_cleanup(curl);
   curl_global_cleanup();

   return influx_return;

}

// Initialization function to connect to the Influx DB.
// Returns: The curl handle to pass to the handler function
CURL *init_influx()
{
    CURL *curl;

    // Initialize libcurl
    curl_global_init(CURL_GLOBAL_DEFAULT);

    // Create a CURL handle
    curl = curl_easy_init();

    return curl;
}

