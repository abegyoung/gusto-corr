#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <curl/curl.h>

#define BUFSIZE 128

// InfluxDB parameters
#define INFLUXDB_URL "http://localhost:8086/query?&db=gustoDBlp"

// Callback function to handle the response from the InfluxDB server
size_t write_callback(void *contents, size_t size, size_t nmemb, void *userp) {

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

    return realsize;
}

int main(int argc, char **argv) {
    CURL *curl;
    CURLcode res;
    char *query = malloc(BUFSIZ);
    sprintf(query, "&q=SELECT * FROM \"%s\" WHERE \"scanID\"='%d' ORDER BY time DESC LIMIT 1", argv[1], atoi(argv[2]));

    // Initialize libcurl
    curl_global_init(CURL_GLOBAL_DEFAULT);

    // Create a CURL handle
    curl = curl_easy_init();
    if (curl) {
        // Set the InfluxDB URL
        curl_easy_setopt(curl, CURLOPT_URL, INFLUXDB_URL);

        // Set the POST data (query)
        curl_easy_setopt(curl, CURLOPT_POSTFIELDS, query);

        // Set the callback function to handle the response
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_callback);

        // Make the HTTP POST request
        res = curl_easy_perform(curl);

        // Check for errors
        if (res != CURLE_OK)
            fprintf(stderr, "curl_easy_perform() failed: %s\n", curl_easy_strerror(res));

        // Cleanup
        curl_easy_cleanup(curl);
    }

    // Cleanup libcurl
    curl_global_cleanup();

    return 0;
}

