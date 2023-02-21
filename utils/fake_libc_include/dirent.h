#include "_fake_defines.h"
#include "_fake_typedefs.h"

typedef struct {
    /* Always zero */
    long d_ino;

    /* File position within stream */
    long d_off;

    /* Structure size */
    unsigned short d_reclen;

    /* Length of name without \0 */
    size_t d_namlen;

    /* File type */
    int d_type;

    /* File name */
    char d_name[PATH_MAX+1];
} dirent;

typedef struct {
    struct dirent ent;
    struct _WDIR *wdirp;
} DIR;