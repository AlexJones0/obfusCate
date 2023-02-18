//////
#include <stdio.h>

void selection_sort(int *arr, const int n) {
    for (int i = 0; i < n; i++) {
        int min_found = arr[i];
        int min_index = i;
        for (int j = n; j > i; j--) {
            if (arr[j] < min_found) {
                min_found = arr[j];
                min_index = j;
            }
        }
        int temp = arr[i];
        arr[i] = arr[min_index];
        arr[min_index] = temp;
    }
}

int main() {
    int my_arr[100] = {0, 70, 10, 7, 61, 63, 86, 83, 87, 66, 78, 68, 6, 42, 1, 33, 67, 49, 38, 5, 31, 73, 27, 20, 94, 77, 13, 96, 23, 53, 48, 9, 74, 57, 46, 16, 14, 92, 43, 24, 64, 44, 62, 2, 21, 3, 50, 34, 8, 69, 25, 91, 51, 54, 55, 80, 81, 17, 22, 95, 60, 72, 85, 84, 93, 28, 76, 58, 45, 65, 75, 47, 88, 89, 59, 19, 37, 40, 56, 79, 18, 97, 11, 35, 29, 26, 15, 32, 30, 82, 52, 4, 39, 36, 98, 12, 90, 71, 99, 41};
    selection_sort(my_arr, 100);
    int wrong_order_count = 0;
    for (int i = 0; i < 99; i++) {
        if (my_arr[i] > my_arr[i+1])
            wrong_order_count++;
    }
    printf("%d\n", wrong_order_count);
}