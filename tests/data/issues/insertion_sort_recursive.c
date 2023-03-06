//////
#include <stdio.h>

void insertion_sort(int *arr, const int n) {
    if (n <= 0)
        return;
    int i = n - 1;
    insertion_sort(arr, i);
    int cur_val = arr[n];
    while (i >= 0 && arr[i] > cur_val) {
        arr[i+1] = arr[i];
        i--;
    }
    arr[i+1] = cur_val;
}

int main() {
    int my_arr[100] = {0, 70, 10, 7, 61, 63, 86, 83, 87, 66, 78, 68, 6, 42, 1, 33, 67, 49, 38, 5, 31, 73, 27, 20, 94, 77, 13, 96, 23, 53, 48, 9, 74, 57, 46, 16, 14, 92, 43, 24, 64, 44, 62, 2, 21, 3, 50, 34, 8, 69, 25, 91, 51, 54, 55, 80, 81, 17, 22, 95, 60, 72, 85, 84, 93, 28, 76, 58, 45, 65, 75, 47, 88, 89, 59, 19, 37, 40, 56, 79, 18, 97, 11, 35, 29, 26, 15, 32, 30, 82, 52, 4, 39, 36, 98, 12, 90, 71, 99, 41};
    printf("1\n");
    insertion_sort(my_arr, 100);
    printf("2\n");
    int wrong_order_count = 0;
    printf("3\n");
    for (int i = 0; i < 99; i++) {
        if (my_arr[i] > my_arr[i+1])
            wrong_order_count++;
    }
    printf("4\n");
    printf("%d\n", wrong_order_count);
    printf("5\n");
}