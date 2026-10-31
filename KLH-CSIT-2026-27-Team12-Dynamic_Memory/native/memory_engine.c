#define _GNU_SOURCE
#include <errno.h>
#include <inttypes.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <time.h>
#include <unistd.h>

typedef struct Allocation {
    unsigned long id;
    void *address;
    size_t size;
    char function[8];
    long long created_ms;
    long long released_ms;
    int active;
    struct Allocation *next;
} Allocation;

static Allocation *allocations = NULL;
static unsigned long next_id = 1;
static size_t total_allocated = 0;
static size_t total_freed = 0;
static size_t active_bytes = 0;
static unsigned long total_allocations = 0;
static unsigned long total_deallocations = 0;

static long long now_ms(void) {
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    return (long long)ts.tv_sec * 1000LL + ts.tv_nsec / 1000000LL;
}

static void json_string(const char *value) {
    putchar('"');
    for (const char *p = value; *p; p++) {
        if (*p == '"' || *p == '\\') putchar('\\');
        putchar(*p);
    }
    putchar('"');
}

static Allocation *find_active(unsigned long id) {
    for (Allocation *item = allocations; item; item = item->next)
        if (item->id == id && item->active) return item;
    return NULL;
}

static void print_error(const char *message) {
    printf("{\"ok\":false,\"error\":");
    json_string(message);
    puts("}");
    fflush(stdout);
}

static int valid_size(unsigned long long value) {
    return value > 0 && value <= (unsigned long long)256 * 1024 * 1024;
}

static void print_allocation(const Allocation *item) {
    printf("{\"id\":%lu,\"size\":%zu,\"function\":", item->id, item->size);
    json_string(item->function);
    printf(",\"createdAt\":%lld,\"releasedAt\":%lld,\"status\":", item->created_ms, item->released_ms);
    json_string(item->active ? "active" : "released");
    putchar('}');
}

static void create_allocation(const char *function, size_t size, int zeroed) {
    void *address = zeroed ? calloc(1, size) : malloc(size);
    if (!address) { print_error("allocation failed"); return; }
    Allocation *item = calloc(1, sizeof(*item));
    if (!item) { free(address); print_error("tracker allocation failed"); return; }
    item->id = next_id++;
    item->address = address;
    item->size = size;
    snprintf(item->function, sizeof(item->function), "%s", function);
    item->created_ms = now_ms();
    item->active = 1;
    item->next = allocations;
    allocations = item;
    total_allocated += size;
    active_bytes += size;
    total_allocations++;
    printf("{\"ok\":true,\"allocation\":");
    print_allocation(item);
    printf(",\"metrics\":{\"activeAllocations\":%lu,\"activeBytes\":%zu}}\n", total_allocations - total_deallocations, active_bytes);
    fflush(stdout);
}

static void resize_allocation(unsigned long id, size_t new_size) {
    Allocation *item = find_active(id);
    if (!item) { print_error("active allocation not found"); return; }
    size_t old_size = item->size;
    void *address = realloc(item->address, new_size);
    if (!address) { print_error("reallocation failed"); return; }
    if (new_size > old_size) total_allocated += new_size - old_size;
    else total_freed += old_size - new_size;
    active_bytes = active_bytes - old_size + new_size;
    item->address = address;
    item->size = new_size;
    printf("{\"ok\":true,\"allocation\":");
    print_allocation(item);
    printf(",\"metrics\":{\"activeAllocations\":%lu,\"activeBytes\":%zu}}\n", total_allocations - total_deallocations, active_bytes);
    fflush(stdout);
}

static void release_allocation(unsigned long id) {
    Allocation *item = find_active(id);
    if (!item) { print_error("active allocation not found or already released"); return; }
    free(item->address);
    item->address = NULL;
    item->active = 0;
    item->released_ms = now_ms();
    active_bytes -= item->size;
    total_freed += item->size;
    total_deallocations++;
    printf("{\"ok\":true,\"allocation\":");
    print_allocation(item);
    printf(",\"metrics\":{\"activeAllocations\":%lu,\"activeBytes\":%zu}}\n", total_allocations - total_deallocations, active_bytes);
    fflush(stdout);
}

static void print_state(void) {
    printf("{\"ok\":true,\"metrics\":{\"totalAllocations\":%lu,\"totalDeallocations\":%lu,\"activeAllocations\":%lu,\"totalAllocatedBytes\":%zu,\"totalFreedBytes\":%zu,\"activeBytes\":%zu},\"allocations\":[", total_allocations, total_deallocations, total_allocations - total_deallocations, total_allocated, total_freed, active_bytes);
    int first = 1;
    for (Allocation *item = allocations; item; item = item->next) {
        if (!first) putchar(',');
        print_allocation(item);
        first = 0;
    }
    puts("]}");
    fflush(stdout);
}

static void cleanup(void) {
    for (Allocation *item = allocations; item;) {
        Allocation *next = item->next;
        if (item->active) free(item->address);
        free(item);
        item = next;
    }
}

int main(void) {
    char line[512];
    while (fgets(line, sizeof(line), stdin)) {
        char command[16];
        unsigned long long first = 0, second = 0;
        if (sscanf(line, "%15s %llu %llu", command, &first, &second) < 1) continue;
        if (strcmp(command, "malloc") == 0 && valid_size(first)) create_allocation("malloc", (size_t)first, 0);
        else if (strcmp(command, "calloc") == 0 && valid_size(first) && second <= SIZE_MAX / first && valid_size(first * second)) create_allocation("calloc", (size_t)(first * second), 1);
        else if (strcmp(command, "realloc") == 0 && valid_size(second)) resize_allocation((unsigned long)first, (size_t)second);
        else if (strcmp(command, "free") == 0) release_allocation((unsigned long)first);
        else if (strcmp(command, "state") == 0) print_state();
        else print_error("invalid command or size");
    }
    cleanup();
    return 0;
}
