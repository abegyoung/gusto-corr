#include <stdio.h>
#include <stdlib.h>
#include <libfswatch/c/libfswatch.h>
#include <pthread.h>
#include <unistd.h>

int n;

// Define a simple queue structure
struct EventQueue {
    struct fsw_cevent *event;
    struct EventQueue *next;
};

struct EventQueue *event_queue = NULL;
pthread_mutex_t event_queue_mutex = PTHREAD_MUTEX_INITIALIZER;
pthread_cond_t event_queue_cond = PTHREAD_COND_INITIALIZER;

// Enqueue an event
void enqueueEvent(struct fsw_cevent *event) {
    n+=1;
    printf("enqueuing.. %d events in Q now\n", n);

    struct EventQueue *newNode = (struct EventQueue *)malloc(sizeof(struct EventQueue));
    if (newNode == NULL) {
        perror("Error allocating memory");
        exit(EXIT_FAILURE);
    }

    newNode->event = event;
    newNode->next = NULL;

    pthread_mutex_lock(&event_queue_mutex);

    if (event_queue == NULL) {
        event_queue = newNode;
    } else {
        struct EventQueue *current = event_queue;
        while (current->next != NULL) {
            current = current->next;
        }
        current->next = newNode;
    }

    // Signal that a new event is available
    pthread_cond_signal(&event_queue_cond);

    pthread_mutex_unlock(&event_queue_mutex);
}

// Dequeue an event
struct fsw_cevent *dequeueEvent() {

    pthread_mutex_lock(&event_queue_mutex);

    // Wait until a new event is available
    while (event_queue == NULL) {
        pthread_cond_wait(&event_queue_cond, &event_queue_mutex);
    }
    n-=1;
    printf("dequeuing %d events in Q now\n", n);

    struct EventQueue *front = event_queue;
    event_queue = event_queue->next;

    pthread_mutex_unlock(&event_queue_mutex);

    if (front == NULL) {
        fprintf(stderr, "Error: Attempted to dequeue a NULL event.\n");
        return NULL;
    }

    struct fsw_cevent *event = front->event;

    if (event == NULL) {
        fprintf(stderr, "Error: Dequeued event has a NULL fsw_cevent.\n");
        free(front);  // Free the EventQueue node if the event is NULL
        return NULL;
    }

    free(front);  // Free the EventQueue node

    return event;
}

// Callback function to process the file
void callback(const struct fsw_cevent *event, const unsigned int event_num, void *data) {
    // Make a copy of the fsw_cevent structure
    struct fsw_cevent *event_copy = (struct fsw_cevent *)malloc(sizeof(struct fsw_cevent));
    if (event_copy == NULL) {
        perror("Error allocating memory for event copy");
        exit(EXIT_FAILURE);
    }

    *event_copy = *event;

    // Enqueue the copied event for later processing
    enqueueEvent(event_copy);
}


// Function to start the file system monitor in a separate thread
void *startMonitorThread(void *arg) {
    FSW_HANDLE fsw_handle = (FSW_HANDLE)arg;

    // Start the event loop
    if (fsw_start_monitor(fsw_handle) < 0) {
        perror("Error starting monitor");
        exit(EXIT_FAILURE);
    }

    pthread_exit(NULL);
}

int main() {
    n=0;
    setvbuf(stdout, NULL, _IONBF, 0);

    // Set the directory to monitor
    const char *directory = "./dir";

    // Initialize the session with the default monitor type
    FSW_HANDLE fsw_handle = fsw_init_session(system_default_monitor_type);

    // Set the callback function
    fsw_set_callback(fsw_handle, (void (*)(const struct fsw_cevent * const, const unsigned int, void *))callback, NULL);

   // Add event types
   int flag = 1<<6;
   struct fsw_event_type_filter cevent_filter;
   cevent_filter.flag= flag;
   fsw_add_event_type_filter(fsw_handle, cevent_filter);

    // Add a watch to the directory
    if (fsw_add_path(fsw_handle, directory) < 0) {
        perror("Error adding path");
        exit(EXIT_FAILURE);
    }

    // Create a thread for file system monitoring
    pthread_t monitor_thread;
    if (pthread_create(&monitor_thread, NULL, startMonitorThread, (void *)fsw_handle) != 0) {
        perror("Error creating monitor thread");
        exit(EXIT_FAILURE);
    }

    // Process the events one at a time
    while (1) {
        struct fsw_cevent *event = dequeueEvent();
        if (event != NULL) {
            printf("File changed: %s\n", event->path);
            printf("   It's going to take 3 seconds to process this file\n");
            printf("   Incoming events will be queued\n   ");

            for(int i=0; i<30; i++){
              printf("*");
              usleep(100000);
            }

            printf("\n\n");
            // No need to free the event explicitly
        }
    }

    // Clean up
    pthread_join(monitor_thread, NULL);
    fsw_destroy_session(fsw_handle);

    return 0;
}

