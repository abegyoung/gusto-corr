#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <curl/curl.h>
#include <influx.h>
#include <inttypes.h>

#define BUFSIZE 128

// InfluxDB parameters
#define INFLUXDB_URL "http://localhost:8086/query?&db=gustoDBlp"

int main(int argc, char **argv) {
    CURL *curl;
    CURLcode res;
    char *query = malloc(BUFSIZ);

    // example from callback.c getting target, IF, VLSR
    /*
    curl = init_influx();
    sprintf(query, "&q=SELECT last(VLSR),* FROM \"tuning\" WHERE time<=\%" PRIu64 "000000000", (uint64_t) 1706288464);
    influxReturn = influxWorker(curl, query);
    printf("target %s\n", influxReturn->text);
    printf("IF is %d MHz\n", (int) influxReturn->value[1]);
    printf("VLSR is %.0f km/s\n", influxReturn->value[0]);
    */

    // example for getting all HK_TEMP values from a HOT scanID
    curl = init_influx();
    sprintf(query, "&q=SELECT * FROM /^HK_TEMP*/ WHERE scanID=~/10039/");
    influxReturn = influxWorker(curl, query);
    printf("length = %d\n", influxReturn->length);

    for(int i=0; i<influxReturn->length; i++)
      printf("%s %.1f\n", influxReturn->name[i], influxReturn->value[i]);


    return 0;
}

