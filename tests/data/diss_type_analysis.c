#include <stdint.h>
#include <stdlib.h>
int funccall() {return 2;}
int main() {
    int arr[4] = {1,  2,  3,  4};
    typedef float* decimal;
    float three = 3.333f;
    struct thing { decimal x; int *y; } *item = malloc(sizeof(struct thing *));
    item->x = &three;
    {   uint32_t three = 3;
        return (float) (*(item->x) + ((three -= 3) * arr[2])) / funccall(); }
}
