#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>

#define PORT 1718
#define BUFFER_SIZE 160
#define RAD2DEG (180./3.14159)
#define DEG2RAD (3.14159/180.)

char *rad2hms(double value){

  char *result = (char *) malloc(sizeof(char)*16);

  double hr  = floor(          value * (24./(2.*M_PI)));
  double min = floor(     60.*(value * (24./(2.*M_PI)) - hr));
  double sec =       60.*(60.*(value * (24./(2.*M_PI)) - hr) - min);

  sprintf(result, "%.0fh %.0fm %.2fs", hr, min, sec);

  return result;

}

char *rad2dms(double radians){

  char *result = (char *) malloc(sizeof(char)*16);

  double degreesDouble = radians * (180.0 / M_PI);
  int degrees = (int)degreesDouble;
  double remainingMinutes = (degreesDouble - degrees) * 60.0;
  int minutes = (int)remainingMinutes;
  double seconds = (remainingMinutes - minutes) * 60.0;

  sprintf(result, "%d° %d' %.2f\"", degrees, minutes, seconds);

  return result;

}

void correctPrecession(float *ra, float *dec, uint32_t timeInSeconds){

    // Convert time from UTC seconds since 1970 to Julian years since the year 2000
    double T = (timeInSeconds-946638000) / (365.24 * 24 * 60 * 60 * 100);

    // Coefficients for precession (rad)
    double M = 0.022361722*T + 0.0000067701322*pow(T,2) + 0.00000017627825*pow(T,3);
    double N = 0.009717173*T + 0.0000020682152*pow(T,2) + 0.00000020245819*pow(T,3);

    // Calculate the corrections in right ascension and declination
    double deltaRA = M + N * sin(*ra) * tan(*dec);
    double deltaDec = N * cos(*ra);

    // Apply the corrections to the J2000 coordinates
    *ra += deltaRA;   // correction in radians
    *dec += deltaDec; // correction in radians
}


// Make struct to store data
struct radec_t {
  struct timespec now;
  float altitude;
  float longitude;
  float latitude;
  float ra;
  float dec;
};

struct vec_t {
  double x, y, z;
};

struct quat_t {
  double i, j, k;
  double r;
};

struct starFix_t {
  int32_t fixNum;
  int32_t starCount;
  struct quat_t adjustment;
  struct quat_t attitudeTaken;
};

struct position_t {
  struct radec_t here;
  struct starFix_t fix;
  struct quat_t attitude;
  struct vec_t telescope;
};

int main(int argc, char **argv) {
    struct position_t pos;

    int sockfd;
    struct sockaddr_in server_addr, client_addr;
    socklen_t client_len = sizeof(client_addr);
    char buffer[BUFFER_SIZE];

    // Create UDP socket
    if ((sockfd = socket(AF_INET, SOCK_DGRAM, 0)) == -1) {
        perror("Error creating socket");
        exit(EXIT_FAILURE);
    }

    // Configure server address structure
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(PORT);
    server_addr.sin_addr.s_addr = INADDR_ANY;

    // Bind socket to the specified port
    if (bind(sockfd, (struct sockaddr*)&server_addr, sizeof(server_addr)) == -1) {
        perror("Error binding socket");
        close(sockfd);
        exit(EXIT_FAILURE);
    }

    printf("Waiting for data on port %d...\n", PORT);

    while (1) {
        // Receive data from the client
        ssize_t received_bytes = recvfrom(sockfd, buffer, sizeof(buffer), 0, 
                                          (struct sockaddr*)&client_addr, &client_len);

        if (received_bytes == -1) {
            perror("Error receiving data");
            close(sockfd);
            exit(EXIT_FAILURE);
        }

        printf("Received %zd bytes from %s:%d:\n", received_bytes, 
               inet_ntoa(client_addr.sin_addr), ntohs(client_addr.sin_port));

	memcpy(&pos.here.now.tv_sec,     buffer,     sizeof(uint32_t));
	memcpy(&pos.here.now.tv_nsec,    buffer+4 ,  sizeof(float));
	memcpy(&pos.here.altitude,       buffer+8 ,  sizeof(float));
	memcpy(&pos.here.longitude,      buffer+12,  sizeof(float));
	memcpy(&pos.here.latitude,       buffer+16,  sizeof(float));
	memcpy(&pos.here.ra,             buffer+20,  sizeof(float));
	memcpy(&pos.here.dec,            buffer+24,  sizeof(float));

	memcpy(&pos.fix.fixNum,          buffer+28,  sizeof(uint32_t));
	memcpy(&pos.fix.starCount,       buffer+32,  sizeof(uint32_t));
        memcpy(&pos.fix.adjustment.i,    buffer+36,  sizeof(double));
        memcpy(&pos.fix.adjustment.j,    buffer+44,  sizeof(double));
        memcpy(&pos.fix.adjustment.k,    buffer+52,  sizeof(double));
        memcpy(&pos.fix.adjustment.r,    buffer+60,  sizeof(double));
        memcpy(&pos.fix.attitudeTaken.i, buffer+68,  sizeof(double));
        memcpy(&pos.fix.attitudeTaken.j, buffer+76,  sizeof(double));
        memcpy(&pos.fix.attitudeTaken.k, buffer+84,  sizeof(double));
        memcpy(&pos.fix.attitudeTaken.r, buffer+92,  sizeof(double));

        memcpy(&pos.attitude.i,          buffer+100, sizeof(double));
        memcpy(&pos.attitude.j,          buffer+108, sizeof(double));
        memcpy(&pos.attitude.k,          buffer+116, sizeof(double));
        memcpy(&pos.attitude.r,          buffer+124, sizeof(double));

        memcpy(&pos.telescope.x,         buffer+132, sizeof(double));
        memcpy(&pos.telescope.y,         buffer+140, sizeof(double));
        memcpy(&pos.telescope.z,         buffer+148, sizeof(double));

        printf("sec= %ld.%ld\n",   pos.here.now.tv_sec, pos.here.now.tv_nsec);
        printf("GONDOLA_ALT= %f\n",pos.here.altitude);
        printf("LONG= %f\n", RAD2DEG*pos.here.longitude);
        printf("LAT= %f\n",  RAD2DEG*pos.here.latitude);
        correctPrecession(&pos.here.ra, &pos.here.dec, pos.here.now.tv_sec);
        printf("RA= %s\n",   rad2hms(pos.here.ra));
        printf("DEC= %s\n\n",rad2dms(pos.here.dec));

        printf("fixNum= %d\n",  (pos.fix.fixNum));
        printf("StrCnt= %d\n\n",(pos.fix.starCount));

        printf("adj i= %f\n",  pos.fix.adjustment.i);
        printf("adj j= %f\n",  pos.fix.adjustment.j);
        printf("adj k= %f\n",  pos.fix.adjustment.k);
        printf("adj r= %f\n\n",pos.fix.adjustment.r);

        printf("attTaken i= %f\n",  pos.fix.attitudeTaken.i);
        printf("attTaken j= %f\n",  pos.fix.attitudeTaken.j);
        printf("attTaken k= %f\n",  pos.fix.attitudeTaken.k);
        printf("attTaken r= %f\n\n",pos.fix.attitudeTaken.r);

        printf("att i= %f\n",  pos.attitude.i);
        printf("att j= %f\n",  pos.attitude.j);
        printf("att k= %f\n",  pos.attitude.k);
        printf("att r= %f\n\n",pos.attitude.r);

        printf("tel x= %f\n",  pos.telescope.x);
        printf("tel y= %f\n",  pos.telescope.y);
        printf("tel z= %f\n\n",pos.telescope.z);

    }

    // Close the socket
    close(sockfd);

    return 0;
}

