//////
#include <stdio.h>

void merge_sort_work(int *arr, int* work_arr, int i, int j) {
    int size = j - i + 1;
    if (size == 1)
        work_arr[i] = arr[i];
    if (size <= 1)
        return;
    int midpoint = (i + j) / 2;
    merge_sort_work(arr, work_arr, i, midpoint);
    merge_sort_work(arr, work_arr, midpoint + 1, j);
    int first_ind = i, second_ind = midpoint + 1;
    for (int k = i; k <= j; k++) {
        if (first_ind <= midpoint && (second_ind > j || arr[first_ind] <= arr[second_ind])) {
            work_arr[k] = arr[first_ind];
            first_ind++;
        } else {
            work_arr[k] = arr[second_ind];
            second_ind++;
        }
    }
    for (int k = i; k <= j; k++) {
        arr[k] = work_arr[k];
    }
}

void merge_sort(int *arr, const int n) {
    int work_arr[n];
    merge_sort_work(arr, work_arr, 0, n-1);
}

int main() {
    int my_arr[100] = {0, 70, 10, 7, 61, 63, 86, 83, 87, 66, 78, 68, 6, 42, 1, 33, 67, 49, 38, 5, 31, 73, 27, 20, 94, 77, 13, 96, 23, 53, 48, 9, 74, 57, 46, 16, 14, 92, 43, 24, 64, 44, 62, 2, 21, 3, 50, 34, 8, 69, 25, 91, 51, 54, 55, 80, 81, 17, 22, 95, 60, 72, 85, 84, 93, 28, 76, 58, 45, 65, 75, 47, 88, 89, 59, 19, 37, 40, 56, 79, 18, 97, 11, 35, 29, 26, 15, 32, 30, 82, 52, 4, 39, 36, 98, 12, 90, 71, 99, 41};
    merge_sort(my_arr, 100);
    int wrong_order_count = 0;
    for (int i = 0; i < 99; i++) {
        if (my_arr[i] > my_arr[i+1])
            wrong_order_count++;
    }
    printf("%d\n", wrong_order_count);
}