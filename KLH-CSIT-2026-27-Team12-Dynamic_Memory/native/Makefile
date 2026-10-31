CC ?= gcc
CFLAGS ?= -std=c11 -Wall -Wextra -Wpedantic -O2

all: memory_engine

memory_engine: memory_engine.c
	$(CC) $(CFLAGS) -o $@ $<

clean:
	rm -f memory_engine

.PHONY: all clean
