#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <glob.h>
#include <regex.h>
#include <stdbool.h>
#include "search_glob.h"

int search_glob_results(glob_t glob_result, int scan_to_check) {
    int isREFHOT = 0;
    regex_t regex_digit, regex_string;
    int hasDigit, hasString;

    char *pattern_digit = malloc(6*sizeof(char));
    sprintf(pattern_digit, "%d", scan_to_check); //scanID
    char *pattern_string = "REF";		 //scan_type

    // Compile regular expressions
    hasDigit  = regcomp(&regex_digit,  pattern_digit,  REG_EXTENDED);
    hasString = regcomp(&regex_string, pattern_string, REG_EXTENDED);

    // Iterate over the glob_result.gl_pathv[] array
    for (int i = 0; i<glob_result.gl_pathc; i++) {
        const char *filename = glob_result.gl_pathv[i];

        // Check if filename contains 5-digit integer scanID
        hasDigit = regexec(&regex_digit, filename, 0, NULL, 0);
        // Check if filename contains 3-character string scan_type
        hasString = regexec(&regex_string, filename, 0, NULL, 0);

        // If both patterns match, AND the file is a REF, it's a REF HOT!
        if (!hasDigit && !hasString) {
	    isREFHOT = 1;
        }
    }

    // Free compiled regular expressions
    regfree(&regex_digit);
    regfree(&regex_string);

    return isREFHOT;

}

bool file_exists(const char *filename) {
    FILE *file = fopen(filename, "r");
    if (file) {
        fclose(file);
        return true;
    }
    return false;
}

